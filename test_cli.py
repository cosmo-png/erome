import erome_dl.cli as cli
from erome_dl.history import History
from fakes import FakeSession

URL = "https://www.erome.com/someuser"


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("EROME_DL_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(cli, "make_session", lambda *a, **k: FakeSession())


def test_list_only(monkeypatch, tmp_path, capsys):
    _setup(monkeypatch, tmp_path)
    assert cli.main([URL, "--list-only", "--delay", "0"]) == 0
    out = capsys.readouterr().out
    assert "First Album" in out and "Second Album" in out


def test_download_all_then_new_only(monkeypatch, tmp_path, capsys):
    _setup(monkeypatch, tmp_path)
    out_dir = tmp_path / "out"
    assert cli.main([URL, "--all", "-o", str(out_dir), "--delay", "0"]) == 0
    files = sorted(p.name for p in (out_dir / "someuser").rglob("*") if p.is_file())
    assert files == ["001_clip.mp4", "001_other.mp4", "002_pic.jpg"]
    assert History(tmp_path / "home" / "history.db").done_ids() == {"AAA111", "BBB222"}

    capsys.readouterr()
    assert cli.main([URL, "--new-only", "-o", str(out_dir), "--delay", "0"]) == 0
    assert "Nothing new" in capsys.readouterr().out


def test_images_only(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    out_dir = tmp_path / "out"
    cli.main([URL, "--all", "--images-only", "-o", str(out_dir), "--delay", "0"])
    files = [p.name for p in (out_dir / "someuser").rglob("*") if p.is_file()]
    assert files == ["002_pic.jpg"]


def test_rejects_other_domains(monkeypatch, tmp_path, capsys):
    _setup(monkeypatch, tmp_path)
    cli.main(["https://example.com/user", "--list-only"])
    assert "not an erome.com link" in capsys.readouterr().out
