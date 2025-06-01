"""Main application module."""

import sys
import logging
from pathlib import Path
import json
from dotenv import load_dotenv

from textual.app import App
from Tool.errors import DownloadError
from Tool.screens import WelcomeScreen

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class Settings:
    """Manage settings"""

    DEFAULT_SETTINGS = {
        "download_path": str(Path("./downloads").resolve()),
        "audio_quality": "0",  # 0 best
        "max_search_results": 10,
    }

    def __init__(self):
        self.settings_file = Path.home() / ".ytdownloader" / "settings.json"
        self.settings = self.load_settings()

    def load_settings(self) -> dict:
        """Load settings from file"""
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
    """Main"""

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
