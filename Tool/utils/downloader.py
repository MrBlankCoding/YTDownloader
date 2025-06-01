"""Download functionality."""

import os
import asyncio
from pathlib import Path
from typing import Dict
import subprocess

from ..errors import DownloadError


class Downloader:
    """Downloading with DLP"""

    def __init__(self, settings):
        self.settings = settings
        self._check_ytdlp()

    def _check_ytdlp(self):
        """Check for instalation of dlp"""
        try:
            subprocess.run(
                ["yt-dlp", "--version"], capture_output=True, check=True, timeout=5
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise DownloadError("yt-dlp not found. If your running the build make sure its installed in global python environment or in the venv you are using. You can install it with `pip install yt-dlp`.")

    async def download(self, url: str) -> Dict:
        """Download."""
        # Path from settings
        return await asyncio.get_event_loop().run_in_executor(
            None, self._download_sync, url, self.settings.settings["download_path"]
        )

    def _download_sync(self, url: str, output_dir: str) -> Dict:
        """synchronous download"""
        # No need for aync here as its one download at a time
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            self.settings.settings["audio_quality"],
            "--output",
            str(output_path / "%(title)s.%(ext)s"),
            "--embed-metadata",
            "--no-warnings",
            url,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return {
                    "success": True,
                    "path": str(output_path),
                    "message": "Success!",
                }
            else:
                return {
                    "success": False,
                    "path": None,
                    "message": f"Failed: {result.stderr}",
                }
        except subprocess.TimeoutExpired:
            raise DownloadError("Timed out, Check internet?")
        except Exception as e:
            raise DownloadError(f"Failed: {e}")
