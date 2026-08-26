# =============================================================================
# Website Scraper
# =============================================================================
# Big picture: download one HTML page, parse it once, then expose:
#   - title
#   - readable body text
#   - useful links
#
# brochure.py calls the helpers at the bottom:
#   fetch_website_links(url)     → list of absolute URLs
#   fetch_website_contents(url)  → "title + text" string (truncated)
#
# =============================================================================

from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

# -----------------------------------------------------------------------------
# Shared request settings
# -----------------------------------------------------------------------------
# Many sites reject bare Python requests. A browser-like User-Agent helps.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0.0.0 Safari/537.36"
    )
}
# Don't hang forever if a site is slow or unresponsive.
REQUEST_TIMEOUT_SECONDS = 15
# Keep page text short so brochure prompts stay cheap and focused.
CONTENT_CHAR_LIMIT = 2_000


class Website:
    """Fetch a page once and expose its title, text, and links."""

    def __init__(self, url: str):
        """
        Construction does the real work:
          1. HTTP GET the URL
          2. If the request fails, store a skip message and stop
          3. Parse HTML with BeautifulSoup
          4. Extract title, links, then clean body text
        """
        self.url = url
        # Defaults used when fetch/parse fails — brochure can keep going.
        self.title = "No title found"
        self.links: list[str] = []
        self.text = ""

        # ----- Step 1: download the page -----
        try:
            response = requests.get(
                url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS
            )
            # Raises HTTPError for 4xx/5xx (403 forbidden, 404 missing, etc.).
            response.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            self.title = f"Skipped page (HTTP {status})"
            return
        except requests.RequestException:
            # Timeouts, DNS failures, connection resets, TLS issues, etc.
            self.title = "Skipped page (request failed)"
            return

        # ----- Step 2: parse HTML into a searchable tree -----
        # "html.parser" is Python's built-in parser (no extra install needed).
        soup = BeautifulSoup(response.content, "html.parser")

        # ----- Step 3: pull out the pieces we care about -----
        self.title = (
            soup.title.string.strip()
            if soup.title and soup.title.string
            else "No title found"
        )
        # Extract links BEFORE cleaning text — text cleanup removes tags.
        self.links = self._extract_links(soup)
        self.text = self._extract_text(soup)

    def _extract_links(self, soup: BeautifulSoup) -> list[str]:
        """
        Collect useful hrefs and turn relative paths into absolute URLs.

        Example:
          page = https://example.com/about
          href = /careers  →  https://example.com/careers
        """
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            # Skip empty / non-navigation links that aren't real pages.
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            # urljoin resolves relative links against the page we fetched.
            links.append(urljoin(self.url, href))
        return links

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """
        Return readable page text for the LLM.

        We delete noisy tags (scripts, styles, images, inputs) first so the
        model gets prose instead of code/CSS/UI chrome.
        Note: this mutates soup.body — that's why links were extracted first.
        """
        if not soup.body:
            return ""
        for irrelevant in soup.body(["script", "style", "img", "input", "noscript"]):
            irrelevant.decompose()  # remove the tag from the tree entirely
        # separator="\n" keeps some structure; strip=True drops extra whitespace.
        return soup.body.get_text(separator="\n", strip=True)

    def contents(self, limit: int = CONTENT_CHAR_LIMIT) -> str:
        """Return title + body text, truncated to a sensible limit."""
        return f"{self.title}\n\n{self.text}"[:limit]


# -----------------------------------------------------------------------------
# Convenience helpers used by brochure.py
# Each call creates a Website (one fetch + one parse).
# -----------------------------------------------------------------------------
def fetch_website_contents(url: str) -> str:
    """Return the title and contents of the website at the given url."""
    return Website(url).contents()


def fetch_website_links(url: str) -> list[str]:
    """Return the links on the website at the given url."""
    return Website(url).links


# -----------------------------------------------------------------------------
# Try while learning
# -----------------------------------------------------------------------------
# Uncomment to manually inspect scraper output:
#
# if __name__ == "__main__":
#     site = Website("https://www.google.com")
#     print(site.title)
#     print(site.links)
#     print(site.contents())
