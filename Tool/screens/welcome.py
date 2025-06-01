from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static
from textual.app import ComposeResult

from Tool.screens.search import SearchScreen
from Tool.screens.settings import SettingsScreen
from Tool.screens.music_player import MusicPlayerScreen

class WelcomeScreen(Screen):
    """Home screen"""
    
    BINDINGS = [
        Binding("s", "start_search", "Start"),
        Binding("c", "open_settings", "Settings"),
        Binding("p", "open_player", "Player"),
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
                yield Static("• Play your music with 'p'", id="instruction4")
                yield Static("", id="spacer3")
                yield Static("Controls:", id="controls-title")
                yield Static("• S: Start Search", id="control1")
                yield Static("• C: Settings", id="control2")
                yield Static("• P: Music Player", id="control3")
                yield Static("• Q: Quit", id="control4")
                yield Static("", id="spacer4")
        yield Footer()
    
    def action_start_search(self) -> None:
        """Start search"""
        self.app.push_screen(SearchScreen())
    
    def action_open_settings(self) -> None:
        """Open settings screen"""
        self.app.push_screen(SettingsScreen())
    
    def action_open_player(self) -> None:
        """Open music player"""
        self.app.push_screen(MusicPlayerScreen())
    
    def action_quit(self) -> None:
        """Quit."""
        self.app.exit() 