"""Download functionality."""

import os
import logging
import asyncio
from pathlib import Path
import yt_dlp
from typing import Dict
import subprocess

from .errors import DownloadError

logger = logging.getLogger(__name__)

class Downloader:
    """Audio handling"""
    
    def __init__(self, settings):
        self.settings = settings
        self._check_ytdlp()
    
    def _check_ytdlp(self):
        """Check if YT-DLP is installed"""
        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise DownloadError("yt-dlp not found. Install with: pip install yt-dlp")
    
    async def download(self, url: str) -> Dict:
        """Download audio using settings"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._download_sync, url, self.settings.settings["download_path"]
        )
    
    def _download_sync(self, url: str, output_dir: str) -> Dict:
        """synchronous download"""
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", self.settings.settings["audio_quality"],
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