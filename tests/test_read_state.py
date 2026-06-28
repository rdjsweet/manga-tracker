from views.manga import _read_state

# Chapters are stored newest-first (index 0 is the newest).
CHAPTERS = [
    {"chapter_title": "Ch 5", "url": "u5"},
    {"chapter_title": "Ch 4", "url": "u4"},
    {"chapter_title": "Ch 3", "url": "u3"},
    {"chapter_title": "Ch 2", "url": "u2"},
    {"chapter_title": "Ch 1", "url": "u1"},
]


def test_caught_up_when_last_read_is_newest():
    state = _read_state(CHAPTERS, "u5")
    assert state["unread_count"] == 0
    assert state["continue_url"] is None
    assert state["continue_title"] is None


def test_some_unread_points_to_next_chapter_not_latest():
    # Read up to Ch 3; the next chapter to read is Ch 4, NOT the newest Ch 5.
    state = _read_state(CHAPTERS, "u3")
    assert state["unread_count"] == 2
    assert state["continue_url"] == "u4"
    assert state["continue_title"] == "Ch 4"


def test_nothing_read_starts_from_oldest():
    state = _read_state(CHAPTERS, None)
    assert state["unread_count"] == 5
    assert state["continue_url"] == "u1"
    assert state["continue_title"] == "Ch 1"


def test_unknown_last_read_treated_as_caught_up():
    state = _read_state(CHAPTERS, "does-not-exist")
    assert state["unread_count"] == 0
    assert state["continue_url"] is None


def test_no_chapters():
    state = _read_state([], "u5")
    assert state["unread_count"] == 0
    assert state["continue_url"] is None
