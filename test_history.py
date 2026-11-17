from erome_dl.history import History


def test_mark_and_reload(tmp_path):
    db = tmp_path / "h.db"
    h = History(db)
    assert h.done_ids() == set()
    h.mark("AAA111", "First", "https://www.erome.com/a/AAA111", 2)
    h.close()
    assert History(db).done_ids() == {"AAA111"}
