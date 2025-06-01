from pathlib import Path
import logging

from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static, Input, Select, Button
from textual.app import ComposeResult

from .search import SearchScreen

logger = logging.getLogger(__name__)


class SettingsScreen(Screen):
    """Settings screen"""

    BINDINGS = [
        Binding("escape", "back_to_welcome", "Back"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("s", "save_settings", "Save"),
    ]

    def __init__(self):
        super().__init__()
        app_settings = getattr(self.app, "settings", None)
        if app_settings is None:
            raise AttributeError("App instance does not have a 'settings' attribute.")
        self.settings = app_settings

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            with Vertical(id="settings-container"):
                yield Static("Settings", id="settings-title")
                yield Static("", id="spacer1")

                yield Static("Download Path:", id="path-label")
                yield Input(
                    value=self.settings.settings["download_path"],
                    id="download-path-input",
                )

                yield Static("", id="spacer2")

                # Audio Quality
                yield Static("Audio Quality:", id="quality-label")
                yield Select(
                    [
                        ("Best Quality", "0"),
                        ("High Quality", "192"),
                        ("Medium Quality", "128"),
                        ("Low Quality", "64"),
                    ],
                    value=self.settings.settings["audio_quality"],
                    id="quality-select",
                )

                yield Static("", id="spacer3")
                yield Static("Max Search Results:", id="results-label")
                yield Select(
                    [
                        ("5 results", "5"),
                        ("10 results", "10"),
                        ("15 results", "15"),
                        ("20 results", "20"),
                        ("25 results", "25"),
                    ],
                    value=str(self.settings.settings["max_search_results"]),
                    id="results-select",
                )

                yield Static("", id="spacer4")
                yield Button("Save Settings", id="save-button")

                yield Static("", id="spacer5")
                yield Static("Press 'S' to save or 'ESC' to go back", id="controls")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        if event.button.id == "save-button":
            self.save_settings()

    def action_save_settings(self) -> None:
        """Save settings"""
        self.save_settings()

    def save_settings(self) -> None:
        """Save current settings"""
        try:
            new_settings = {
                "download_path": self.query_one("#download-path-input", Input).value,
                "audio_quality": self.query_one("#quality-select", Select).value,
                "max_search_results": (
                    int(value)
                    if (value := self.query_one("#results-select", Select).value) is not None
                    and isinstance(value, str)
                    and value.isdigit()
                    else self.settings.settings.get("max_search_results", 10)
                ),
            }

            path = Path(new_settings["download_path"])
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)

            self.settings.save_settings(new_settings)
            if isinstance(self.app.screen, SearchScreen):
                downloader = getattr(self.app.screen, "downloader", None)
                if downloader is not None:
                    downloader.settings = self.settings

            self.notify("Settings saved successfully!", severity="information")
            self.app.pop_screen()

        except Exception as e:
            self.notify(f"Failed to save settings: {e}", severity="error")

    def action_back_to_welcome(self) -> None:
        """Go back to welcome screen"""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit application"""
        self.app.exit()
