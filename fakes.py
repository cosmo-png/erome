from urllib.parse import urlparse

PROFILE = """
<div class="album"><a href="/a/AAA111"><img alt="thumb"></a><a href="/a/AAA111">First Album</a></div>
<div class="album"><a href="/a/BBB222"><img alt="thumb"></a><a href="/a/BBB222">Second Album</a></div>
"""
ALBUMS = {
    "/a/AAA111": """<h1>First Album</h1>
        <div class="media-group"><video><source src="https://v1.erome.com/1/clip.mp4"></video></div>
        <div class="media-group"><img data-src="https://s1.erome.com/1/pic.jpg"></div>
        <img src="/static/logo.png">""",
    "/a/BBB222": """<h1>Second Album</h1>
        <div class="media-group"><video src="https://v1.erome.com/2/other.mp4"></video></div>""",
}


class FakeResponse:
    def __init__(self, body=b"", text="", status=200, headers=None):
        self._body, self.text, self.status_code = body, text, status
        self.headers = headers if headers is not None else {"Content-Length": str(len(body))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise IOError(f"HTTP {self.status_code}")

    def iter_content(self, size):
        for i in range(0, len(self._body), size):
            yield self._body[i : i + size]


class FakeSession:
    """Stands in for requests.Session; no network."""

    def get(self, url, headers=None, stream=False, timeout=None):
        parsed = urlparse(url)
        if not parsed.netloc.endswith("www.erome.com"):
            return FakeResponse(body=b"x" * 100)
        if parsed.path in ALBUMS:
            return FakeResponse(text=ALBUMS[parsed.path])
        return FakeResponse(text=PROFILE)
