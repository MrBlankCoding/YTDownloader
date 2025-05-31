import os
import sys
import logging
import subprocess
import asyncio
from pathlib import Path
from typing import List, Dict
import requests
from dotenv import load_dotenv

from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem
from textual.screen import Screen
from textual.binding import Binding
from textual import work, on

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Handle errors for download operations"""
    pass


class YouTubeAPI:
    """Handle YT API """
    
    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = requests.Session()
    
    def _get_api_key(self) -> str:
        api_key = os.getenv("YT_API_KEY")
        if not api_key:
            raise DownloadError("YT_API_KEY not found.")
        return api_key
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search"""
        if not query.strip():
            raise DownloadError("Search query cannot be empty")
        
        return await asyncio.get_event_loop().run_in_executor(
            None, self._search_sync, query.strip(), max_results
        )
    
    def _search_sync(self, query: str, max_results: int) -> List[Dict]:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(max_results, 25),
            "key": self.api_key,
            "videoCategoryId": "10",  # Music
            "order": "relevance"
        }
        
        try:
            response = self.session.get(f"{self.base_url}/search", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise DownloadError(f"API error: {data['error']['message']}")
            
            return self._format_results(data.get("items", []))
            
        except requests.RequestException as e:
            raise DownloadError(f"Search failed: {e}")
    
    def _format_results(self, items: List[Dict]) -> List[Dict]:
        """Format results"""
        results = []
        for item in items:
            video_id = item["id"]["videoId"]
            title = self._clean_html(item["snippet"]["title"])
            channel = item["snippet"]["channelTitle"]
            
            results.append({
                "title": title,
                "channel": channel,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "display": f"♪ {title[:60]}{'...' if len(title) > 60 else ''}\n  👤 {channel}"
            })
        return results
    
    def _clean_html(self, text: str) -> str:
        """Clean any HTML"""
        replacements = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'"}
        for old, new in replacements.items():
            text = text.replace(old, new)
        return " ".join(text.split())


class Downloader:
    """Audio handling"""
    
    def __init__(self):
        self._check_ytdlp()
    
    def _check_ytdlp(self):
        """Check if YT-DLP is installed"""
        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise DownloadError("yt-dlp not found. Install with: pip install yt-dlp")
    
    async def download(self, url: str, output_dir: str = "./downloads") -> Dict:
        """Donwload audio (Specify output directory)"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._download_sync, url, output_dir
        )
    
    def _download_sync(self, url: str, output_dir: str) -> Dict:
        """synchronous download"""
        #We only are downloading one track at a time 
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--output", str(output_path / "%(title)s.%(ext)s"),
            "--embed-metadata",
            "--no-warnings",
            "--no-playlist",
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"Downloaded: {url}")
                return {
                    "success": True,
                    "path": str(output_path),
                    "message": "Success!"
                }
            else:
                logger.error(f"Failed with {result.stderr}")
                return {
                    "success": False,
                    "path": None,
                    "message": f"Failed: {result.stderr}"
                }
        except subprocess.TimeoutExpired:
            raise DownloadError("Timed out, Check internet?")
        except Exception as e:
            raise DownloadError(f"Failed: {e}")


class WelcomeScreen(Screen):
    """Home screen"""
    
    BINDINGS = [
        Binding("s", "start_search", "Start"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit")
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            with Vertical(id="welcome-container"):
                yield Static("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  ██╗   ██╗████████╗    ██████╗  ██████╗ ██╗    ██╗███╗   ██  ║
    ║  ╚██╗ ██╔╝╚══██╔══╝    ██╔══██╗██╔═══██╗██║    ██║████╗  ██  ║
    ║   ╚████╔╝    ██║       ██║  ██║██║   ██║██║ █╗ ██║██╔██╗ ██  ║
    ║    ╚██╔╝     ██║       ██║  ██║██║   ██║██║███╗██║██║╚██╗██  ║
    ║     ██║      ██║       ██████╔╝╚██████╔╝╚███╔███╔╝██║ ╚████  ║
    ║     ╚═╝      ╚═╝       ╚═════╝  ╚═════╝  ╚══╝╚══╝ ╚═╝  ╚═══╝ ║
    ╚══════════════════════════════════════════════════════════════╝
                """, id="ascii-logo")
                yield Static("", id="spacer1")
                yield Static("YT Down", id="welcome-message")
                yield Static("Download YT videos as MP3 files.", id="welcome-description")
                yield Static("", id="spacer2")
                yield Static("Instructions:", id="instructions-title")
                yield Static("• Search for music on YT", id="instruction1")
                yield Static("• Navigate results with arrow keys", id="instruction2")
                yield Static("• Download with Space or 'd'", id="instruction3")
                yield Static("", id="spacer3")
                yield Static("Press 'S' to Start or 'Q' to Quit", id="controls")
        yield Footer()
    
    def action_start_search(self) -> None:
        """Start search"""
        self.app.push_screen(SearchScreen())
    
    def action_quit(self) -> None:
        """Quit."""
        self.app.exit()


class DownloadSuccessScreen(Screen):
    """Start download success"""
    
    BINDINGS = [
        Binding("ctrl+n", "new_search", "New Search"),
        Binding("escape", "back_to_welcome", "Home"),
        Binding("ctrl+c", "quit", "Quit")
    ]
    
    def __init__(self, song_title: str, download_path: str):
        super().__init__()
        self.song_title = song_title
        self.download_path = download_path
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            with Vertical(id="success-container"):
                yield Static("Download Complete!", id="success-title")
                yield Static("", id="spacer1")
                yield Static("Downloaded Song:", id="song-label")
                yield Static(f"   {self.song_title}", id="song-title")
                yield Static("", id="spacer2")
                yield Static("Saved to:", id="location-label")
                yield Static(f"   {self.download_path}", id="download-path")
                yield Static("", id="spacer3")
                yield Static("Next", id="next-title")
                yield Static("• Ctrl+N: Download another", id="next1")
                yield Static("• ESC: return Home", id="next2")
                yield Static("", id="spacer4")
        yield Footer()
    
    def action_new_search(self) -> None:
        """Start a new search"""
        self.app.pop_screen()
        self.app.push_screen(SearchScreen())
    
    def action_back_to_welcome(self) -> None:
        """Go back home"""
        # Pop all screens to get back to welcome
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()
    
    def action_quit(self) -> None:
        """Quit."""
        self.app.exit()


class SearchScreen(Screen):
    """Search screen"""
    
    BINDINGS = [
        Binding("escape", "back_to_welcome", "Back"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("enter", "search", "Search"),
        Binding("space", "download", "Download"),
        Binding("d", "download", "Download"),
        Binding("ctrl+n", "new_search", "New Search")
    ]
    
    def __init__(self):
        super().__init__()
        self.api = YouTubeAPI()
        self.downloader = Downloader()
        self.results = []
        self.download_in_progress = False
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Static("Search", id="title")
            yield Input(placeholder="Type to search...", id="search-input")
            yield Static("", id="status")
            yield ScrollableContainer(ListView(id="results"), id="results-container")
        yield Footer()
    
    def on_mount(self) -> None:
        self.query_one("#search-input").focus()
        self.update_status("Enter search query")
    
    @on(Input.Submitted, "#search-input")
    def on_search(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query and not self.download_in_progress:
            self.search_videos(query)
    
    @work(exclusive=True)
    async def search_videos(self, query: str) -> None:
        """Search for videos"""
        self.update_status("Searching...")
        self.clear_results()
        
        try:
            self.results = await self.api.search(query)
            if not self.results:
                self.update_status("No results :(")
                return
            
            # Populate results list
            results_list = self.query_one("#results")
            for result in self.results:
                results_list.mount(ListItem(Static(result["display"])))
            
            self.update_status(f"{len(self.results)} results.")
            results_list.focus()
            
        except DownloadError as e:
            self.update_status(f"❌ {e}")
    
    def action_download(self) -> None:
        """Download selected"""
        if not self.results or self.download_in_progress:
            return
        
        results_list = self.query_one("#results")
        # get index from list view. 
        index = getattr(results_list, "index", None)
        if index is not None and 0 <= index < len(self.results):
            selected = self.results[index]
            self.download_song(selected)
    
    @work(exclusive=True)
    async def download_song(self, song: Dict) -> None:
        """Logic for downloading a song"""
        self.download_in_progress = True
        self.update_status(f"Downloading: {song['title'][:50]}...")
        
        try:
            result = await self.downloader.download(song["url"])
            if result["success"]:
                self.app.push_screen(DownloadSuccessScreen(song['title'], result['path']))
            else:
                self.update_status(f"Failed to download {song['title'][:50]} - Check logs!")
        except DownloadError as e:
            self.update_status(f"Failed to download: {e}")
        finally:
            self.download_in_progress = False
    
    def action_search(self) -> None:
        """Focus search"""
        if not self.download_in_progress:
            self.query_one("#search-input").focus()
    
    def action_new_search(self) -> None:
        """Clear current search"""
        if not self.download_in_progress:
            search_input = self.query_one("#search-input")
            search_input.value = ""  #Showing error but works????
            search_input.focus()
            self.clear_results()
            self.update_status("Enter search query")

    def action_back_to_welcome(self) -> None:
        """Go back"""
        if not self.download_in_progress:
            self.app.pop_screen()
    
    def action_quit(self) -> None:
        """Exit"""
        self.app.exit()
    
    def update_status(self, message: str) -> None:
        """Update status"""
        status_widget = self.query_one("#status", Static)
        status_widget.update(message)
    
    def clear_results(self) -> None:
        """Clear results"""
        results_list = self.query_one("#results")
        results_list.remove_children()
        self.results = []


class YouTubeDownloaderApp(App):
    """Main application"""
    
    CSS = """
    #welcome-container {
        align: center middle;
        text-align: center;
    }
    
    #ascii-logo {
        color: $primary;
        text-align: center;
        text-style: bold;
    }
    
    #welcome-message {
        color: $text;
        margin: 1;
        text-align: center;
        text-style: bold;
    }
    
    #welcome-description {
        color: $text-muted;
        margin-bottom: 1;
        text-align: center;
    }
    
    #instructions-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        text-align: center;
    }
    
    #instruction1, #instruction2, #instruction3, #instruction4 {
        color: $text-muted;
        margin-left: 2;
        text-align: center;
    }
    
    #controls {
        text-style: bold;
        color: $success;
        margin: 2;
        text-align: center;
    }
    
    #spacer1, #spacer2, #spacer3, #spacer4 {
        height: 1;
    }
    
    #success-container {
        align: center middle;
        text-align: center;
    }
    
    #success-title {
        text-style: bold;
        color: $success;
        text-align: center;
        margin: 1;
    }
    
    #song-label, #location-label, #next-title {
        text-style: bold;
        color: $accent;
        text-align: center;
        margin: 1;
    }
    
    #song-title, #download-path {
        color: $text;
        text-align: center;
        text-style: italic;
        margin: 1;
    }
    
    #next1, #next2 {
        color: $text-muted;
        text-align: center;
        margin-left: 2;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1;
    }
    
    #search-input {
        margin: 1;
    }
    
    #status {
        text-align: center;
        margin: 1;
        color: $accent;
    }
    
    #results-container {
        height: 20;
        border: solid $primary;
        margin: 1;
    }
    
    #results > ListItem {
        padding: 1;
    }
    
    #results > ListItem:hover {
        background: $accent 20%;
    }
    """
    
    TITLE = "YouTube Download"
    
    def on_mount(self) -> None:
        """init"""
        try:
            self.push_screen(WelcomeScreen())
        except DownloadError as e:
            self.notify(f"Init failed. {e}", severity="error")
            self.exit(1)


def main():
    """entry point"""
    try:
        app = YouTubeDownloaderApp()
        app.run()
    except KeyboardInterrupt:
        print("\nbye")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())