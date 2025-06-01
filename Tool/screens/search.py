import logging
from typing import Dict
from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem
from textual import work, on
from textual.app import ComposeResult

from Tool.youtube_api import YouTubeAPI
from Tool.downloader import Downloader, DownloadError
from Tool.screens.download_success import DownloadSuccessScreen

logger = logging.getLogger(__name__)


class SearchScreen(Screen):
    """Search screen"""

    BINDINGS = [
        Binding("escape", "back_to_welcome", "Back"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("enter", "search", "Search"),
        Binding("space", "download", "Download"),
        Binding("d", "download", "Download"),
        Binding("ctrl+n", "new_search", "New Search"),
    ]

    def __init__(self):
        super().__init__()
        self.api = YouTubeAPI()
        self.downloader = None
        self.results = []
        self.download_in_progress = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Static("Search", id="title")
            yield Input(placeholder="Type to search...", id="search-input")
            yield Static("", id="status", markup=False)
            yield ScrollableContainer(ListView(id="results"), id="results-container")
        yield Footer()

    def on_mount(self) -> None:
        self.downloader = Downloader(getattr(self.app, "settings", None))
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
        self.update_status("Searching…")
        self.clear_results()

        try:
            # Safely get max_search_results from app settings, with a fallback default
            max_results = 10  # Default value
            app_settings = getattr(self.app, "settings", None)
            if app_settings and hasattr(app_settings, "settings"):
                max_results = app_settings.settings.get("max_search_results", 10)
            self.results = await self.api.search(query, max_results=max_results)
            if not self.results:
                self.update_status("No results found")
                return

            results_list = self.query_one("#results")
            for result in self.results:
                static = Static(result["display"], markup=False)
                results_list.mount(ListItem(static))

            self.update_status(f"Found {len(self.results)} results")
            results_list.focus()

        except DownloadError as e:
            self.update_status(f"Error: {e}")

    def action_download(self) -> None:
        """Download selected"""
        if not self.results or self.download_in_progress:
            return

        results_list = self.query_one("#results")
        index = getattr(results_list, "index", None)
        if index is not None and 0 <= index < len(self.results):
            selected = self.results[index]
            self.download_song(selected)

    @work(exclusive=True)
    async def download_song(self, song: Dict) -> None:
        """Logic for downloading a song"""
        self.download_in_progress = True
        self.update_status(f"Downloading: {song['title'][:50]}…")

        try:
            if self.downloader is None:
                self.downloader = Downloader(getattr(self.app, "settings", None))
            result = await self.downloader.download(song["url"])
            if result["success"]:
                self.app.push_screen(
                    DownloadSuccessScreen(song["title"], result["path"])
                )
            else:
                self.update_status(
                    f"Failed to download {song['title'][:50]} - Check logs"
                )
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
            search_input.value = ""  # not error?
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
