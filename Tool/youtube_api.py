"""YouTube API functionality."""

import os
import logging
from typing import List, Dict
import requests
import asyncio

from .errors import DownloadError

logger = logging.getLogger(__name__)


class YouTubeAPI:
    """Handle YT API"""

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
            "order": "relevance",
        }

        try:
            response = self.session.get(
                f"{self.base_url}/search", params=params, timeout=10
            )
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

            # Truncate title and add ellipsis if needed, but escape it
            display_title = title[:60]
            if len(title) > 60:
                display_title += "…"  # Using a proper ellipsis character instead of ...

            results.append(
                {
                    "title": title,
                    "channel": channel,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "display": f"♪ {display_title}\n  👤 {channel}",
                }
            )
        return results

    def _clean_html(self, text: str) -> str:
        """Clean any HTML"""
        replacements = {
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#39;": "'",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return " ".join(text.split())
