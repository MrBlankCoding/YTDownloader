import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import timedelta
import vlc
import mutagen.mp3

from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import Header, Footer, Static, ListView, ProgressBar
from textual.timer import Timer
from textual.app import ComposeResult

logger = logging.getLogger(__name__)


class MusicPlayerScreen(Screen):
    """Music player screen with improved UI and code quality"""

    BINDINGS = [
        Binding("escape", "back_to_welcome", "Back"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("s", "stop", "Stop"),
        Binding("r", "refresh", "Refresh"),
        Binding("up", "previous", "Previous"),
        Binding("down", "next", "Next"),
        Binding("q", "quit", "Quit"),
        Binding("f", "refresh", "Refresh"),
        Binding("p", "toggle_play", "Play/Pause"),
        Binding("n", "next", "Next"),
        Binding("b", "previous", "Previous"),
    ]

    # Constants for better maintainability
    DEFAULT_VOLUME = 70
    PROGRESS_UPDATE_INTERVAL = 0.5
    MAX_TITLE_LENGTH = 60

    def __init__(self):
        super().__init__()
        self.songs: List[Dict] = []
        self.current_song_index: Optional[int] = None
        self.is_playing = False
        self.current_time = 0
        self.total_time = 0
        self.update_timer: Optional[Timer] = None

        # Initialize VLC with better error handling
        self.vlc_instance = None
        self.vlc_player = None
        self._initialize_vlc()

    def _initialize_vlc(self) -> None:
        """Initialize VLC player with proper error handling"""
        try:
            self.vlc_instance = vlc.Instance("--no-xlib")
            if self.vlc_instance is not None:
                self.vlc_player = self.vlc_instance.media_player_new()
                self.vlc_player.audio_set_volume(self.DEFAULT_VOLUME)
                logger.info("VLC initialized successfully")
            else:
                self.vlc_player = None
                logger.error("VLC instance is None, cannot create media player")
        except Exception as e:
            logger.error(f"Failed to initialize VLC: {e}")
            self.vlc_instance = None
            self.vlc_player = None

    def compose(self) -> ComposeResult:
        """Compose the UI with improved structure and styling"""
        yield Header()
        with Container(id="main-container"):
            with Vertical(id="player-container"):
                # Title section
                yield Static("🎵 Music Player", id="player-title", classes="title")

                # Playlist section
                with Container(id="playlist-section", classes="section"):
                    yield Static(
                        "📋 Playlist",
                        id="playlist-label",
                        classes="section-title",
                    )
                    yield ScrollableContainer(
                        ListView(id="playlist"),
                        id="playlist-container",
                        classes="playlist-scroll",
                    )

                # Now Playing section
                with Container(id="now-playing-section", classes="section now-playing"):
                    yield Static(
                        "🎧 Now Playing",
                        id="now-playing-label",
                        classes="section-title",
                    )
                    yield Static(
                        "No song selected",
                        id="current-song",
                        classes="current-song",
                    )
                    yield Static(
                        "00:00 / 00:00",
                        id="time-display",
                        classes="time-display",
                    )
                    yield ProgressBar(
                        total=100, id="progress-bar", classes="progress-bar"
                    )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize player on mount"""
        if not self._is_vlc_available():
            self.notify("VLC initialization failed!", severity="error")
            return

        self.refresh_playlist()
        self._focus_playlist()

    def _is_vlc_available(self) -> bool:
        """Check if VLC is properly initialized"""
        return self.vlc_player is not None and self.vlc_instance is not None

    def _focus_playlist(self) -> None:
        """Focus on playlist widget with error handling"""
        try:
            playlist = self.query_one("#playlist", ListView)
            playlist.focus()
        except Exception as e:
            logger.debug(f"Could not focus playlist: {e}")

    def refresh_playlist(self) -> None:
        """Refresh the playlist with improved error handling and performance"""
        try:
            download_path = self._get_download_path()
            if not download_path:
                return

            self._clear_playlist()
            mp3_files = self._get_mp3_files(download_path)

            if not mp3_files:
                self.notify("No music files found!", severity="warning")
                return

            self._load_songs(mp3_files)
            self._update_playlist_ui()

        except Exception as e:
            logger.error(f"Failed to refresh playlist: {e}")
            self.notify(f"Failed to refresh playlist: {str(e)}", severity="error")

    def _get_download_path(self) -> Optional[Path]:
        """Get and validate download path"""
        try:
            # Replace this with the correct way to access your app's download path setting
            download_path_str = getattr(self.app, "download_path", None)
            if not download_path_str:
                self.notify("Download path not configured!", severity="error")
                return None
            download_path = Path(download_path_str)
            if not download_path.exists():
                self.notify("Download directory not found!", severity="error")
                return None
            return download_path
        except KeyError:
            self.notify("Download path not configured!", severity="error")
            return None

    def _clear_playlist(self) -> None:
        """Clear current playlist data"""
        self.songs.clear()
        playlist = self.query_one("#playlist", ListView)
        playlist.clear()

    def _get_mp3_files(self, download_path: Path) -> List[Path]:
        """Get sorted MP3 files from download directory"""
        mp3_files = list(download_path.glob("*.mp3"))
        return sorted(mp3_files, key=lambda x: x.stat().st_mtime, reverse=True)

    def _load_songs(self, mp3_files: List[Path]) -> None:
        """Load song metadata from MP3 files"""
        for file in mp3_files:
            try:
                song_data = self._extract_song_data(file)
                if song_data:
                    self.songs.append(song_data)
            except Exception as e:
                logger.error(f"Error loading {file}: {e}")

    def _extract_song_data(self, file: Path) -> Optional[Dict]:
        """Extract metadata from a single MP3 file"""
        try:
            audio = mutagen.mp3.MP3(file)
            if audio.info.length is None:
                return None

            duration_seconds = int(audio.info.length)
            duration_str = self._format_duration(duration_seconds)
            display_title = self._truncate_title(file.stem)

            return {
                "path": str(file),
                "title": file.stem,
                "duration": duration_str,
                "duration_seconds": duration_seconds,
                "display": f"♪ {display_title}\n  ⏱ {duration_str}",
            }
        except Exception:
            return None

    def _format_duration(self, seconds: int) -> str:
        """Format duration seconds to HH:MM:SS or MM:SS string"""
        duration_str = str(timedelta(seconds=seconds))
        return duration_str.split(".")[0] if "." in duration_str else duration_str

    def _truncate_title(self, title: str) -> str:
        """Truncate title if too long"""
        if len(title) <= self.MAX_TITLE_LENGTH:
            return title
        return title[: self.MAX_TITLE_LENGTH] + "…"

    def _update_playlist_ui(self) -> None:
        """Update playlist UI with loaded songs"""
        playlist = self.query_one("#playlist", ListView)

        from textual.widgets import ListItem  # Ensure ListItem is imported

        for song in self.songs:
            static = Static(song["display"], markup=False)
            item = ListItem(static)
            playlist.append(item)

        if self.songs:
            self.notify(f"Found {len(self.songs)} songs", severity="information")

    def play_song(self, index: int) -> None:
        """Play a song by index with improved error handling"""
        if not self._is_valid_song_index(index) or not self._is_vlc_available():
            return

        try:
            self._stop_current_playback()
            song = self.songs[index]

            if self._start_playback(song, index):
                self._update_now_playing_ui(song)
                self._start_progress_tracking()
                self._highlight_current_song(index)
                self.notify(f"Now playing: {song['title']}", severity="information")

        except Exception as e:
            logger.error(f"Failed to play song: {e}")
            self.notify(f"Failed to play song: {str(e)}", severity="error")

    def _is_valid_song_index(self, index: int) -> bool:
        """Check if song index is valid"""
        return 0 <= index < len(self.songs)

    def _stop_current_playback(self) -> None:
        """Stop current playback if any"""
        if self.current_song_index is not None:
            self.stop()

    def _start_playback(self, song: Dict, index: int) -> bool:
        """Start playback for a song"""
        try:
            if self.vlc_instance is None or self.vlc_player is None:
                logger.error("VLC instance or player is None, cannot start playback")
                return False
            media = self.vlc_instance.media_new(song["path"])
            self.vlc_player.set_media(media)
            self.vlc_player.play()

            self.current_song_index = index
            self.is_playing = True
            self.current_time = 0
            self.total_time = song["duration_seconds"]
            return True
        except Exception as e:
            logger.error(f"Failed to start playback: {e}")
            return False

    def _update_now_playing_ui(self, song: Dict) -> None:
        """Update now playing display"""
        current_song_widget = self.query_one("#current-song", Static)
        current_song_widget.update(f"♪ {song['title']}")
        current_song_widget.add_class("playing")

    def _start_progress_tracking(self) -> None:
        """Start progress tracking timer"""
        if self.update_timer:
            self.update_timer.stop()
        self.update_timer = self.set_interval(
            self.PROGRESS_UPDATE_INTERVAL, self.update_progress
        )

    def _highlight_current_song(self, index: int) -> None:
        """Highlight current song in playlist"""
        playlist = self.query_one("#playlist", ListView)
        playlist.index = index

    def update_progress(self) -> None:
        """Update playback progress with improved state handling"""
        if not self._should_update_progress():
            return

        try:
            if self.vlc_player is not None:
                state = self.vlc_player.get_state()

                if state == 3:  # 3 corresponds to Playing state in VLC
                    self._update_playing_progress()
                elif state == 6:  # 6 corresponds to Ended state in VLC
                    self.auto_next()
                elif state == 6:  # 6 corresponds to Error state in VLC
                    self._handle_playback_error()

        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def _should_update_progress(self) -> bool:
        """Check if progress should be updated"""
        return (
            self.is_playing
            and self.current_song_index is not None
            and self._is_vlc_available()
        )

    def _update_playing_progress(self) -> None:
        """Update progress for currently playing song"""
        if self.vlc_player is not None:
            position_ms = self.vlc_player.get_time()
            if position_ms >= 0:
                self.current_time = min(position_ms // 1000, self.total_time)

                progress = (
                    (self.current_time / self.total_time) * 100
                    if self.total_time > 0
                    else 0
                )

                self._update_progress_display(progress)

    def _update_progress_display(self, progress: float) -> None:
        """Update progress bar and time display"""
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.progress = min(100, progress)

        current_str = self._format_duration(self.current_time)
        total_str = self._format_duration(self.total_time)

        time_display = self.query_one("#time-display", Static)
        time_display.update(f"{current_str} / {total_str}")

    def _handle_playback_error(self) -> None:
        """Handle playback errors"""
        self.notify("Playback error occurred", severity="error")
        self.stop()

    def auto_next(self) -> None:
        """Automatically play next song when current song ends"""
        if self._has_next_song() and self.current_song_index is not None:
            next_index = (
                self.current_song_index + 1
                if self.current_song_index is not None
                else 0
            )
            self.play_song(next_index)
        else:
            self.stop()
            self.notify("Reached end of playlist", severity="information")

    def _has_next_song(self) -> bool:
        """Check if there's a next song to play"""
        return (
            self.current_song_index is not None
            and self.current_song_index < len(self.songs) - 1
        )

    def toggle_play(self) -> None:
        """Toggle play/pause with improved logic"""
        if not self._is_vlc_available():
            return

        if self.current_song_index is None:
            self._play_selected_or_first_song()
        else:
            self._toggle_current_playback()

    def _play_selected_or_first_song(self) -> None:
        """Play selected song or first song if none selected"""
        playlist = self.query_one("#playlist", ListView)
        index = playlist.index if playlist.index is not None else 0
        if index < len(self.songs):
            self.play_song(index)

    def _toggle_current_playback(self) -> None:
        """Toggle playback of current song"""
        if self.is_playing:
            if self.vlc_player is not None:
                self.vlc_player.pause()
            self.is_playing = False
            if self.update_timer:
                self.update_timer.pause()
        else:
            if self.vlc_player is not None:
                self.vlc_player.play()
            self.is_playing = True
            if self.update_timer:
                self.update_timer.resume()

    def stop(self) -> None:
        """Stop playback with complete UI reset"""
        try:
            if self._is_vlc_available() and self.vlc_player is not None:
                self.vlc_player.stop()

            self._reset_playback_state()
            self._reset_ui_state()
            self._stop_progress_timer()

        except Exception as e:
            logger.error(f"Error stopping playback: {e}")

    def _reset_playback_state(self) -> None:
        """Reset internal playback state"""
        self.is_playing = False
        self.current_time = 0

    def _reset_ui_state(self) -> None:
        """Reset UI to stopped state"""
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.progress = 0

        time_display = self.query_one("#time-display", Static)
        time_display.update("00:00 / 00:00")

        current_song_widget = self.query_one("#current-song", Static)
        current_song_widget.update("No song selected")
        current_song_widget.remove_class("playing")

    def _stop_progress_timer(self) -> None:
        """Stop progress update timer"""
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer = None

    def action_previous(self) -> None:
        """Play previous song"""
        if self.current_song_index is not None and self.current_song_index > 0:
            self.play_song(self.current_song_index - 1)
        elif self.songs:
            self.play_song(len(self.songs) - 1)

    def action_next(self) -> None:
        """Play next song"""
        if self._has_next_song() and self.current_song_index is not None:
            self.play_song(self.current_song_index + 1)
        elif self.songs:
            self.play_song(0)

    def action_refresh(self) -> None:
        """Refresh playlist"""
        self.stop()
        self.refresh_playlist()

    def action_toggle_play(self) -> None:
        """Toggle play/pause action"""
        self.toggle_play()

    def action_stop(self) -> None:
        """Stop playback action"""
        self.stop()

    def action_back_to_welcome(self) -> None:
        """Go back to welcome screen with proper cleanup"""
        self.stop()
        self._cleanup_vlc()
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit application with proper cleanup"""
        self.stop()
        self._cleanup_vlc()
        self.app.exit()

    def _cleanup_vlc(self) -> None:
        """Clean up VLC resources"""
        try:
            if self.vlc_player:
                self.vlc_player.release()
            if self.vlc_instance:
                self.vlc_instance.release()
        except Exception as e:
            logger.debug(f"Error during VLC cleanup: {e}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle song selection from playlist"""
        try:
            playlist = self.query_one("#playlist", ListView)
            if playlist.index is not None and self._is_valid_song_index(playlist.index):
                self.play_song(playlist.index)
        except Exception as e:
            logger.error(f"Error handling song selection: {e}")

    def __del__(self) -> None:
        """Cleanup when object is destroyed"""
        try:
            self._stop_progress_timer()
            self._cleanup_vlc()
        except Exception:
            pass
