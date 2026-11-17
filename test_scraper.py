from erome_dl.scraper import is_album_url, parse_album, parse_profile, profile_username
from fakes import ALBUMS, PROFILE


def test_is_album_url():
    assert is_album_url("https://www.erome.com/a/AbC123")
    assert not is_album_url("https://www.erome.com/someuser")


def test_profile_username():
    assert profile_username("https://www.erome.com/some.user?page=2") == "some.user"


def test_parse_profile_dedupes_and_prefers_text_titles():
    albums = parse_profile(PROFILE, "https://www.erome.com/user")
    assert [a.id for a in albums] == ["AAA111", "BBB222"]
    assert [a.title for a in albums] == ["First Album", "Second Album"]


def test_parse_album_kinds_and_filters():
    title, media = parse_album(ALBUMS["/a/AAA111"], "https://www.erome.com/a/AAA111")
    assert title == "First Album"
    assert [(m.kind, m.url.rsplit("/", 1)[-1]) for m in media] == [
        ("video", "clip.mp4"),
        ("image", "pic.jpg"),
    ]


def test_parse_album_video_src_attribute():
    _, media = parse_album(ALBUMS["/a/BBB222"], "https://www.erome.com/a/BBB222")
    assert [m.kind for m in media] == ["video"]
