"""Find albums and media on erome.com.

Selectors are best-effort; if the site changes its layout, parse_profile and
parse_album are the only two functions that need adjusting.
"""
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.erome.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
ALBUM_RE = re.compile(r"^/a/([A-Za-z0-9]+)")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")
VIDEO_EXT = (".mp4", ".webm", ".mov", ".m4v")
SKIP_PARTS = ("/avatar", "/thumb", "/static", "/logo", "/ads")


@dataclass
class Media:
    url: str
    kind: str  # "image" or "video"
    index: int = 0  # position in the full album, so filenames stay stable


@dataclass
class Album:
    id: str
    url: str
    title: str
    media: list[Media] = field(default_factory=list)
    loaded: bool = False
    error: str | None = None

    @property
    def photos(self) -> int:
        return sum(m.kind == "image" for m in self.media)

    @property
    def videos(self) -> int:
        return sum(m.kind == "video" for m in self.media)


def make_session(proxy: str | None = None, cookies: str | None = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": BASE + "/"})
    if cookies:
        s.headers["Cookie"] = cookies
    if proxy:
        s.proxies.update({"http": proxy, "https": proxy})
    return s


def is_album_url(url: str) -> bool:
    return bool(ALBUM_RE.match(urlparse(url).path))


def profile_username(url: str) -> str:
    parts = [p for p in urlparse(url).path.split("/") if p]
    return clean_name(parts[0]) if parts else "profile"


def clean_name(name: str, limit: int = 80) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:limit].strip(" .")


def get_html(session, url: str, delay: float = 0.0, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
            r.raise_for_status()
            if delay:
                time.sleep(delay * random.uniform(0.7, 1.4))
            return r.text
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def parse_profile(html: str, page_url: str) -> list[Album]:
    """Albums linked on one profile page, in page order."""
    soup = BeautifulSoup(html, "html.parser")
    order: list[str] = []
    titles: dict[str, str] = {}
    alts: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        full = urljoin(page_url, a["href"]).split("#")[0].split("?")[0]
        m = ALBUM_RE.match(urlparse(full).path)
        if not m:
            continue
        aid = m.group(1)
        if aid not in order:
            order.append(aid)
        text = a.get_text(" ", strip=True)
        if text and aid not in titles:
            titles[aid] = clean_name(text)
        img = a.find("img")
        if img and img.get("alt") and aid not in alts:
            alts[aid] = clean_name(img["alt"])
    return [
        Album(aid, f"{BASE}/a/{aid}", titles.get(aid) or alts.get(aid) or aid)
        for aid in order
    ]


def scan_profile(session, url: str, delay: float = 0.0, on_page=None, max_pages: int = 500):
    """Walk ?page=1,2,3... until a page adds nothing new."""
    base = url.split("?")[0].rstrip("/")
    seen: dict[str, Album] = {}
    for page in range(1, max_pages + 1):
        html = get_html(session, f"{base}?page={page}", delay)
        new = [a for a in parse_profile(html, base) if a.id not in seen]
        if not new:
            break
        for album in new:
            seen[album.id] = album
        if on_page:
            on_page(page, len(seen))
    return list(seen.values())


def parse_album(html: str, page_url: str) -> tuple[str, list[Media]]:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = clean_name(h1.get_text(" ", strip=True)) if h1 else ""

    found: list[str] = []
    for block in soup.select(".media-group") or [soup]:
        for v in block.find_all("video"):
            src = v.get("src")
            if not src:
                source = v.find("source")
                src = source.get("src") if source else None
            if src:
                found.append(src)
        for img in block.find_all("img"):
            src = img.get("data-src") or img.get("src")
            if src:
                found.append(src)

    media: list[Media] = []
    seen: set[str] = set()
    for src in found:
        full = urljoin(page_url, src)
        path = urlparse(full).path.lower()
        if any(bad in path for bad in SKIP_PARTS) or full in seen:
            continue
        if path.endswith(VIDEO_EXT):
            kind = "video"
        elif path.endswith(IMAGE_EXT):
            kind = "image"
        else:
            continue
        seen.add(full)
        media.append(Media(full, kind, len(media) + 1))
    return title, media


def album_from_url(url: str) -> Album:
    aid = ALBUM_RE.match(urlparse(url).path).group(1)
    return Album(aid, f"{BASE}/a/{aid}", aid)


def load_album(session, album: Album, delay: float = 0.0) -> None:
    html = get_html(session, album.url, delay)
    title, media = parse_album(html, album.url)
    if title:
        album.title = title
    album.media = media
    album.loaded = True
