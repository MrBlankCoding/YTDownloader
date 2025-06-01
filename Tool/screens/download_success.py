from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static
from textual.app import ComposeResult

class DownloadSuccessScreen(Screen):
    """Download Success Screen"""

    BINDINGS = [
        Binding("ctrl+n", "new_search", "New Search"),
        Binding("escape", "back_to_welcome", "Home"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, song_title: str, download_path: str):
        super().__init__()
        self.song_title = song_title
        self.download_path = download_path

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            with Vertical(id="success-container"):
                yield Static("Download Complete!!!!!", id="success-title")
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
        from Tool.screens.search import SearchScreen

        self.app.pop_screen()
        self.app.push_screen(SearchScreen())

    def action_back_to_welcome(self) -> None:
        """Go back home"""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit."""
        self.app.exit()
