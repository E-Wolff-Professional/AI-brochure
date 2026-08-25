from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT_SECONDS = 15
CONTENT_CHAR_LIMIT = 2_000


class Website:
    """Fetch a page once and expose its title, text, and links."""

    def __init__(self, url: str):
        self.url = url
        response = requests.get(
            url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        self.title = (
            soup.title.string.strip()
            if soup.title and soup.title.string
            else "No title found"
        )
        self.links = self._extract_links(soup)
        self.text = self._extract_text(soup)

    def _extract_links(self, soup: BeautifulSoup) -> list[str]:
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            links.append(urljoin(self.url, href))
        return links

    def _extract_text(self, soup: BeautifulSoup) -> str:
        if not soup.body:
            return ""
        for irrelevant in soup.body(["script", "style", "img", "input", "noscript"]):
            irrelevant.decompose()
        return soup.body.get_text(separator="\n", strip=True)

    def contents(self, limit: int = CONTENT_CHAR_LIMIT) -> str:
        """Return title and body text, truncated to a sensible limit."""
        return f"{self.title}\n\n{self.text}"[:limit]


def fetch_website_contents(url: str) -> str:
    """Return the title and contents of the website at the given url."""
    return Website(url).contents()


def fetch_website_links(url: str) -> list[str]:
    """Return the links on the website at the given url."""
    return Website(url).links


""" if __name__ == "__main__":
    site = Website("https://www.google.com")
    print(site.links)
    print(site.contents())
 """