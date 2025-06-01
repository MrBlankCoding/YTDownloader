import logging
from typing import Dict, List, Optional
from pathlib import Path
import vlc
import mutagen.mp3

from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, ListView, ListItem
from textual.timer import Timer
from textual.app import ComposeResult

logger = logging.getLogger(__name__)

#Okay this file is WAYY to long for what it does and it PMO. 
class MusicPlayerScreen(Screen):
    """Music player"""

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

    #Basic config.
    DEFAULT_VOLUME = 70
    PROGRESS_UPDATE_INTERVAL = 0.5
    MAX_TITLE_LENGTH = 50

    #Badd css :(
    CSS = """
    Screen {
        background: #0f0f0f;
        color: #ffffff;
    }

    #main-container {
        width: 100%;
        height: 100%;
        padding: 0;
        margin: 0;
    }

    #content-area {
        width: 100%;
        height: 1fr;
        padding: 1 2;
        margin: 0;
    }

    #library-header {
        width: 100%;
        height: auto;
        text-align: center;
        color: #1db954;
        text-style: bold;
        margin: 1 0;
        padding: 0 1;
    }

    #library-container {
        width: 100%;
        height: 1fr;
        border: round #333333;
        padding: 1;
        margin: 0;
    }

    #library {
        width: 100%;
        height: 100%;
        scrollbar-size: 1 1;
        scrollbar-background: #333333;
        scrollbar-color: #1db954;
    }

    ListItem {
        height: 3;
        padding: 0 1;
        margin: 0;
        border: none;
    }

    ListItem:hover {
        background: #1a1a1a;
    }

    ListItem.-selected {
        background: #1db954 20%;
        border-left: solid #1db954;
    }

    .song-item {
        width: 100%;
        height: 100%;
        padding: 0;
        margin: 0;
    }

    .song-title {
        color: #ffffff;
        text-style: bold;
    }

    .song-duration {
        color: #b3b3b3;
        text-style: dim;
    }

    #now-playing-bar {
        width: 100%;
        height: 4;
        background: #181818;
        border-top: solid #333333;
        padding: 0 2;
    }

    #now-playing-content {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #current-track-info {
        text-align: center;
        color: #ffffff;
    }

    .track-title {
        color: #ffffff;
        text-style: bold;
    }

    .track-time {
        color: #b3b3b3;
        text-style: dim;
    }

    .no-song {
        color: #666666;
        text-style: dim;
        text-align: center;
    }

    .status-message {
        text-align: center;
        color: #b3b3b3;
        text-style: dim;
        margin: 2 0;
    }
    """

    def __init__(self):
        super().__init__()
        self.songs: List[Dict] = []
        self.current_song_index: Optional[int] = None
        self.is_playing = False
        self.current_time = 0
        self.total_time = 0
        self.update_timer: Optional[Timer] = None

        self.vlc_instance = vlc.Instance("--no-xlib")
        if self.vlc_instance is None:
            raise RuntimeError("Failed to initialize VLC instance.")
        self.vlc_player = self.vlc_instance.media_player_new()
        self.vlc_player.audio_set_volume(self.DEFAULT_VOLUME)

    def compose(self) -> ComposeResult:
        """Layout composition."""
        yield Header()

        with Container(id="main-container"):
            with Vertical(id="content-area"):
                yield Static("Your Library!", id="library-header")

                with Container(id="library-container"):
                    yield ScrollableContainer(
                        ListView(id="library"), id="library-scroll"
                    )

            with Container(id="now-playing-bar"):
                with Horizontal(id="now-playing-content"):
                    yield Static(
                        "♪ No track selected",
                        id="current-track-info",
                        classes="no-song",
                    )

        yield Footer()

    def on_mount(self) -> None:
        """Initialization after mount."""
        self.refresh_library()
        self.query_one("#library", ListView).focus()

    def _show_status_message(self, message: str) -> None:
        """Show status messages"""
        library = self.query_one("#library", ListView)
        library.clear()
        status_item = ListItem(Static(message, classes="status-message"))
        library.append(status_item)

    def refresh_library(self) -> None:
        """Refresh the library"""
        download_path = self._get_download_path()
        if not download_path:
            return

        self.songs.clear()
        library = self.query_one("#library", ListView)
        library.clear()

        mp3_files = list(download_path.glob("*.mp3"))
        mp3_files = sorted(mp3_files, key=lambda x: x.stat().st_mtime, reverse=True)

        if not mp3_files:
            self._show_status_message("No music files found. Download some!")
            return

        for file in mp3_files:
            song_data = self._extract_song_data(file)
            if song_data:
                self.songs.append(song_data)

        self._update_library_ui()

    def _get_download_path(self) -> Optional[Path]:
        """get download path froms settings."""
        try:
            app_settings = getattr(self.app, "settings", None)
            if app_settings is None:
                self.notify("App settings not available", severity="error")
                return None

            download_path_str = app_settings.settings.get("download_path")
            if not download_path_str:
                self.notify("Download path not configured!", severity="error")
                return None

            download_path = Path(download_path_str)
            if not download_path.exists():
                self.notify("Download directory not found!", severity="error")
                return None

            return download_path

        except Exception as e:
            logger.error(f"Failed getting download path {e}")
            self.notify("Failed getting download path is it deleted?", severity="error")
            return None

    def _extract_song_data(self, file: Path) -> Optional[Dict]:
        """Extract metadata"""
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
            "display_title": display_title,
        }

    def _format_duration(self, seconds: int) -> str:
        """Format duration"""
        minutes, secs = divmod(seconds, 60)
        return f"{minutes:02d}:{secs:02d}"

    def _truncate_title(self, title: str) -> str:
        """Truncate title"""
        if len(title) <= self.MAX_TITLE_LENGTH:
            return title
        return title[: self.MAX_TITLE_LENGTH] + "…"

    def _update_library_ui(self) -> None:
        """Create songs in library"""
        library = self.query_one("#library", ListView)
        library.clear()

        for song in self.songs:
            song_text = f" {song['display_title']}\n{song['duration']}"
            song_widget = Static(song_text, classes="song-item")
            item = ListItem(song_widget)
            library.append(item)

    def play_song(self, index: int) -> None:
        """play a song by index with VLC"""
        if not (0 <= index < len(self.songs)):
            return

        self.stop()
        song = self.songs[index]

        if self.vlc_instance is None:
            logger.error("VLC instance is not initialized.")
            self._show_status_message("VLC is not available. Cannot play song.")
            return

        media = self.vlc_instance.media_new(song["path"])
        self.vlc_player.set_media(media)
        self.vlc_player.play()

        self.current_song_index = index
        self.is_playing = True
        self.current_time = 0
        self.total_time = song["duration_seconds"]

        self._update_now_playing_ui(song)
        self._start_progress_tracking()
        self._highlight_current_song(index)
        self.notify(f"{song['title']}")

    def _update_now_playing_ui(self, song: Dict) -> None:
        """Display song progress"""
        track_info = self.query_one("#current-track-info", Static)
        track_info.update(f"{song['display_title']}")
        track_info.remove_class("no-song")
        track_info.add_class("track-title")

    def _start_progress_tracking(self) -> None:
        """Start timer"""
        if self.update_timer:
            self.update_timer.stop()
        self.update_timer = self.set_interval(
            self.PROGRESS_UPDATE_INTERVAL, self.update_progress
        )

    def _highlight_current_song(self, index: int) -> None:
        """Highlight the active song."""
        library = self.query_one("#library", ListView)
        if 0 <= index < len(library):
            library.index = index

    def update_progress(self) -> None:
        """Update as song progresses"""
        if not self.is_playing or self.current_song_index is None:
            return

        state = self.vlc_player.get_state()

        if state == 3:  # Playing
            position_ms = self.vlc_player.get_time()
            if position_ms >= 0:
                self.current_time = min(position_ms // 1000, self.total_time)
                self._update_time_display()
        elif state == 6:  # Ended
            self.auto_next()

    def _update_time_display(self) -> None:
        """Update time display"""
        current_str = self._format_duration(self.current_time)
        total_str = self._format_duration(self.total_time)

        track_info = self.query_one("#current-track-info", Static)
        if self.current_song_index is not None:
            song = self.songs[self.current_song_index]
            track_info.update(f"♪ {song['display_title']}\n{current_str} / {total_str}")

    def auto_next(self) -> None:
        """PLay next song after current ends"""
        if (
            self.current_song_index is not None
            and self.current_song_index < len(self.songs) - 1
        ):
            self.play_song(self.current_song_index + 1)
        else:
            self.stop()

    def toggle_play(self) -> None:
        """Play/pause"""
        if self.current_song_index is None:
            library = self.query_one("#library", ListView)
            index = library.index if library.index is not None else 0
            if index < len(self.songs):
                self.play_song(index)
        else:
            if self.is_playing:
                self.vlc_player.pause()
                self.is_playing = False
                if self.update_timer:
                    self.update_timer.pause()
            else:
                self.vlc_player.play()
                self.is_playing = True
                if self.update_timer:
                    self.update_timer.resume()

    def stop(self) -> None:
        """HALT!"""
        self.vlc_player.stop()
        self.is_playing = False
        self.current_time = 0

        track_info = self.query_one("#current-track-info", Static)
        track_info.update("♪ No track selected")
        track_info.add_class("no-song")
        track_info.remove_class("track-title")

        if self.update_timer:
            self.update_timer.stop()
            self.update_timer = None

    def action_previous(self) -> None:
        """Play previous"""
        if self.current_song_index is not None and self.current_song_index > 0:
            self.play_song(self.current_song_index - 1)
        elif self.songs:
            self.play_song(len(self.songs) - 1)

    def action_next(self) -> None:
        """Play next"""
        if (
            self.current_song_index is not None
            and self.current_song_index < len(self.songs) - 1
        ):
            self.play_song(self.current_song_index + 1)
        elif self.songs:
            self.play_song(0)

    def action_refresh(self) -> None:
        """Refresh"""
        self.stop()
        self.refresh_library()

    def action_toggle_play(self) -> None:
        """play/pause"""
        self.toggle_play()

    def action_stop(self) -> None:
        """Stop playback action"""
        self.stop()

    def action_back_to_welcome(self) -> None:
        """Welcome"""
        self.stop()
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit."""
        self.stop()
        self.app.exit()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Simple song select"""
        library = self.query_one("#library", ListView)
        if library.index is not None and 0 <= library.index < len(self.songs):
            self.play_song(library.index)
