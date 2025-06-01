"""Main application module."""

import os
import sys
import logging
from pathlib import Path
import json
from dotenv import load_dotenv

from textual.app import App
from textual.screen import Screen

from Tool.screens import (
    WelcomeScreen,
    SearchScreen,
    DownloadSuccessScreen,
    MusicPlayerScreen,
    SettingsScreen,
)
from Tool.youtube_api import YouTubeAPI
from Tool.downloader import Downloader
from Tool.errors import DownloadError

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class Settings:
    """Manage application settings"""

    DEFAULT_SETTINGS = {
        "download_path": str(Path("./downloads").resolve()),
        "audio_quality": "0",  # 0 best
        "max_search_results": 10,
    }

    def __init__(self):
        self.settings_file = Path.home() / ".ytdownloader" / "settings.json"
        self.settings = self.load_settings()

    def load_settings(self) -> dict:
        """Load settings from file or return defaults"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r") as f:
                    return {**self.DEFAULT_SETTINGS, **json.load(f)}
            return self.DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return self.DEFAULT_SETTINGS.copy()

    def save_settings(self, settings: dict) -> None:
        """Save settings to file"""
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=4)
            self.settings = settings
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            raise DownloadError(f"Failed to save settings: {e}")


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
    
    #settings-container {
        align: center middle;
        width: 80%;
        height: 80%;
    }
    
    #settings-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        margin: 1;
    }
    
    #path-label, #quality-label, #results-label {
        text-style: bold;
        color: $accent;
        margin-top: 1;
    }
    
    #download-path-input {
        margin: 1;
    }
    
    #quality-select, #results-select {
        margin: 1;
    }
    
    #save-button {
        margin: 2;
        width: 100%;
    }
    
    #controls {
        text-style: bold;
        color: $success;
        margin: 2;
        text-align: center;
    }
    
    #controls-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        text-align: center;
    }
    
    #control1, #control2, #control3, #control4 {
        color: $text-muted;
        margin-left: 2;
        text-align: center;
    }
    
    #player-container {
        align: center middle;
        width: 80%;
        height: 80%;
    }
    
    #player-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        margin: 1;
    }
    
    #now-playing {
        border: solid $primary;
        padding: 1;
        margin: 1;
    }
    
    #now-playing-label {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    #current-song {
        color: $text;
        text-style: italic;
        margin: 1;
    }
    
    #time-display {
        color: $text-muted;
        text-align: center;
        margin: 1;
    }
    
    #progress-bar {
        margin: 1;
    }
    
    #library-label {
        text-style: bold;
        color: $accent;
        margin-top: 1;
    }
    
    #library-container {
        height: 15;
        border: solid $primary;
        margin: 1;
    }
    
    #library > ListItem {
        padding: 1;
    }
    
    #library > ListItem:hover {
        background: $accent 20%;
    }
    
    #controls {
        align: center middle;
        margin: 1;
    }
    
    #controls > Button {
        margin: 0 1;
    }
    
    #controls-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        text-align: center;
    }
    
    #control1, #control2, #control3, #control4, #control5 {
        color: $text-muted;
        margin-left: 2;
        text-align: center;
    }
    """

    TITLE = "YouTube Download"

    def __init__(self):
        super().__init__()
        self.settings = Settings()

    def on_mount(self) -> None:
        """Initialize app"""
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
