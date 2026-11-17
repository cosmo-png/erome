from erome_dl.downloader import download_file
from fakes import FakeResponse


class OneShot:
    def __init__(self, response_factory):
        self.factory = response_factory

    def get(self, url, headers=None, stream=False, timeout=None):
        return self.factory()


def test_download_ok_then_skipped(tmp_path):
    dest = tmp_path / "a.mp4"
    session = OneShot(lambda: FakeResponse(body=b"y" * 50))
    assert download_file(session, "u", dest, retry_delay=0) == "ok"
    assert dest.read_bytes() == b"y" * 50
    assert download_file(session, "u", dest, retry_delay=0) == "skipped"


def test_truncated_download_is_rejected(tmp_path):
    dest = tmp_path / "a.mp4"
    short = lambda: FakeResponse(body=b"y" * 10, headers={"Content-Length": "50"})
    assert download_file(OneShot(short), "u", dest, retry_delay=0) == "failed"
    assert not dest.exists()
