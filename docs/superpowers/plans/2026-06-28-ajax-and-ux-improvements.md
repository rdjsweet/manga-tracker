# AJAX & UX Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace full-page form submits with AJAX for Check Updates, Add Manga, and Delete Manga; sort updated manga to the top after a check; fix several UI/UX issues; and eliminate repeated DB connection boilerplate across the backend.

**Architecture:** Three JSON API endpoints (`/api/check_updates`, `/api/add`, `/api/manga/<id>`) added alongside existing form routes. A `db_cursor()` context manager in `utils/db.py` centralises connection lifecycle. A `static/app.js` handles all `fetch()` calls, a full-page spinner overlay, and in-page flash messages.

**Tech Stack:** Python 3.14, Flask 3.x, psycopg2-binary, Jinja2, vanilla JS (ES2020 fetch API), pytest

## Global Constraints

- Canadian English in comments and docs; American English in all identifiers
- No new third-party JS libraries
- Existing form-based routes (`/check_updates`, `/add`, `/delete/<id>`) kept for graceful degradation
- All new DB access uses `db_cursor()` context manager from `utils.db`
- `pytest` for all tests; test files live in `tests/`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `utils/db.py` | Add `db_cursor()` context manager |
| Create | `utils/formatting.py` | `to_est()` datetime helper |
| Modify | `scraper.py` | Normalise all return paths to 4-tuple |
| Modify | `app.py` | Use `db_cursor()` in `load_user` |
| Modify | `views/auth.py` | Use `db_cursor()` in register/login |
| Modify | `views/manga.py` | Fix N+1, add API endpoints, remove dead route |
| Create | `static/app.js` | All AJAX, spinner, inline flash, card rendering |
| Modify | `templates/index.html` | Wire `app.js`, add spinner div, fix structure, add `data-manga-id` |
| Modify | `static/styles.css` | Spinner CSS, dropdown width, modal cancel button |
| Create | `tests/__init__.py` | pytest package marker |
| Create | `tests/conftest.py` | Flask test client + mock DB fixtures |
| Create | `tests/test_db_utils.py` | Tests for `db_cursor()` |
| Create | `tests/test_scraper.py` | Tests for scraper return values |
| Create | `tests/test_api.py` | Tests for JSON API endpoints |

---

### Task 1: `db_cursor()` context manager and `utils/formatting.py`

**Files:**
- Modify: `utils/db.py`
- Create: `utils/formatting.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db_utils.py`

**Interfaces:**
- Produces: `db_cursor()` contextmanager in `utils.db` — yields a psycopg2 `RealDictCursor`, commits on clean exit, rolls back and re-raises on exception, always closes cursor and connection
- Produces: `to_est(dt: datetime) -> datetime` in `utils.formatting` — converts a naive UTC datetime to Eastern Time

- [ ] **Step 1: Add pytest to a dev requirements file**

Create `requirements-dev.txt`:
```
pytest==8.3.0
```

Install it:
```bash
source .venv/bin/activate && pip install pytest
```

- [ ] **Step 2: Create `tests/__init__.py`**

```bash
touch /Users/rsweet/manga-tracker/tests/__init__.py
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
import pytest
from unittest.mock import MagicMock, patch
from app import app as flask_app
from models import User


@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(app, client):
    test_user = User(id=1, username='testuser', password_hash='hash')
    with patch('app.load_user', return_value=test_user):
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'
            sess['_fresh'] = True
        yield client
```

- [ ] **Step 4: Write failing tests for `db_cursor()`**

Create `tests/test_db_utils.py`:
```python
import pytest
from unittest.mock import MagicMock, patch


def test_db_cursor_commits_on_success():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch('utils.db.get_db_connection', return_value=mock_conn):
        from utils.db import db_cursor
        with db_cursor() as cursor:
            cursor.execute('SELECT 1')

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


def test_db_cursor_rolls_back_on_exception():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch('utils.db.get_db_connection', return_value=mock_conn):
        from utils.db import db_cursor
        with pytest.raises(ValueError):
            with db_cursor() as cursor:
                raise ValueError('test error')

    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
cd /Users/rsweet/manga-tracker && source .venv/bin/activate && python -m pytest tests/test_db_utils.py -v
```

Expected: `ImportError` or `AttributeError: module 'utils.db' has no attribute 'db_cursor'`

- [ ] **Step 6: Add `db_cursor()` to `utils/db.py`**

```python
import psycopg2
from psycopg2.extras import RealDictCursor
from config import config
from contextlib import contextmanager


def get_db_connection():
    db_url = config.DATABASE_URL
    if not db_url:
        raise Exception("DATABASE_URL environment variable not set")
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


@contextmanager
def db_cursor():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
python -m pytest tests/test_db_utils.py -v
```

Expected: `2 passed`

- [ ] **Step 8: Create `utils/formatting.py`**

```python
import pytz

_est = pytz.timezone("America/New_York")


def to_est(dt):
    return dt.replace(tzinfo=pytz.utc).astimezone(_est)
```

- [ ] **Step 9: Commit**

```bash
git add utils/db.py utils/formatting.py tests/__init__.py tests/conftest.py tests/test_db_utils.py requirements-dev.txt
git commit -m "feat: add db_cursor context manager and formatting utility"
```

---

### Task 2: Fix `scraper.py` return value bug

**Files:**
- Modify: `scraper.py`
- Create: `tests/test_scraper.py`

**Interfaces:**
- Produces: `scrape_manga_details(url: str) -> tuple` — always exactly 4 values: `(title|None, chapter_titles|None, chapter_urls|None, chapter_count|None)`

- [ ] **Step 1: Write failing tests**

Create `tests/test_scraper.py`:
```python
from unittest.mock import patch, MagicMock
import pytest
import requests as req_lib


def _mock_response(html):
    mock_resp = MagicMock()
    mock_resp.content = html.encode('utf-8')
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_returns_four_values_on_missing_title():
    html = '<html><body><p>No title</p></body></html>'
    with patch('scraper.requests.get', return_value=_mock_response(html)):
        from scraper import scrape_manga_details
        result = scrape_manga_details('https://example.com')
    assert len(result) == 4


def test_returns_four_values_on_request_error():
    with patch('scraper.requests.get', side_effect=req_lib.exceptions.RequestException('fail')):
        from scraper import scrape_manga_details
        result = scrape_manga_details('https://example.com')
    assert len(result) == 4


def test_returns_four_values_on_missing_chapters_div():
    html = '<html><body><h1 class="font-bold text-lg md:text-2xl">My Manga</h1></body></html>'
    with patch('scraper.requests.get', return_value=_mock_response(html)):
        from scraper import scrape_manga_details
        result = scrape_manga_details('https://example.com')
    assert len(result) == 4


def test_first_value_is_none_on_request_error():
    with patch('scraper.requests.get', side_effect=req_lib.exceptions.RequestException('fail')):
        from scraper import scrape_manga_details
        title, _, __, ___ = scrape_manga_details('https://example.com')
    assert title is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_scraper.py -v
```

Expected: `ValueError: too many values to unpack` on the error-path tests

- [ ] **Step 3: Fix all return paths in `scraper.py` to return exactly 4 values**

```python
import requests
from bs4 import BeautifulSoup


def scrape_manga_details(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        title_tag = soup.find("h1", class_="font-bold text-lg md:text-2xl")
        if not title_tag:
            print("Could not find the manga title element on the page.")
            return None, None, None, None

        title = title_tag.text.strip()

        chapters_div = soup.find("div", id="chapters")
        if not chapters_div:
            print("Could not find the 'chapters' element on the page.")
            return title, None, None, None

        chapter_links = chapters_div.find_all(
            "a", class_="border border-border p-1 hover:bg-brand hover:text-white"
        )

        chapter_titles = [link.text.strip() for link in chapter_links]
        chapter_urls = ["https://www.mangapill.com" + link["href"] for link in chapter_links]

        chapter_titles.reverse()
        chapter_urls.reverse()

        if not chapter_titles:
            print("No chapters found on the page.")
            return title, [], [], 0

        return title, chapter_titles, chapter_urls, len(chapter_links)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None, None, None, None


if __name__ == "__main__":
    manga_url = "https://www.mangapill.com/manga/8/kingdom"
    title, chapter_titles, chapter_urls, chapter_count = scrape_manga_details(manga_url)

    if title:
        print(f"Title: {title}")
        print(f"Chapter Count: {chapter_count}")
        for chap_title, chap_url in zip(chapter_titles, chapter_urls):
            print(f"{chap_title} -> {chap_url}")
    else:
        print("Failed to get manga details.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_scraper.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "fix: normalise scraper.py to always return a 4-tuple"
```

---

### Task 3: Migrate `app.py` and `views/auth.py` to `db_cursor()`

**Files:**
- Modify: `app.py`
- Modify: `views/auth.py`

**Interfaces:**
- Consumes: `db_cursor()` from `utils.db`

- [ ] **Step 1: Update `load_user` in `app.py`**

```python
from flask import Flask
from config import config
from flask_login import LoginManager
from views.auth import auth_bp
from views.manga import manga_bp
from views.halloween import halloween_bp
from models import User
from utils.db import db_cursor

app = Flask(__name__)
app.config.from_object(config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'


@login_manager.user_loader
def load_user(user_id):
    with db_cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
    if user:
        return User(user['id'], user['username'], user['password_hash'])
    return None


app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(manga_bp)
app.register_blueprint(halloween_bp)

if __name__ == '__main__':
    app.run(debug=True)
```

- [ ] **Step 2: Update `views/auth.py`**

```python
from dotenv import load_dotenv
from flask import Blueprint, request, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from models import User
from utils.db import db_cursor
import requests
import psycopg2
from config import config
from datetime import datetime

load_dotenv()

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').lower()
        password = request.form.get('password')
        recaptcha_response = request.form.get("g-recaptcha-response")

        recaptcha_verify_url = "https://www.google.com/recaptcha/api/siteverify"
        recaptcha_payload = {
            "secret": config.RECAPTCHA_SECRET_KEY,
            "response": recaptcha_response
        }
        recaptcha_result = requests.post(recaptcha_verify_url, data=recaptcha_payload)
        recaptcha_data = recaptcha_result.json()

        if not recaptcha_data.get("success"):
            flash("reCAPTCHA verification failed. Please try again.", "error")
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        try:
            with db_cursor() as cursor:
                cursor.execute(
                    'INSERT INTO users (username, password_hash) VALUES (%s, %s)',
                    (username, hashed_password)
                )
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except psycopg2.IntegrityError:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('auth.register'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = None
        login_succeeded = False

        with db_cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                if user['first_login']:
                    cursor.execute(
                        'INSERT INTO log (manga_title, chapters_added, date_added, user_id) VALUES (%s, %s, %s, %s)',
                        ("Welcome to the MangaPill Chapter Tracker!", 0, datetime.now(), user['id'])
                    )
                    cursor.execute(
                        'UPDATE users SET first_login = false WHERE id = %s', (user['id'],)
                    )
                login_succeeded = True

        if login_succeeded:
            user_obj = User(user['id'], user['username'], user['password_hash'])
            login_user(user_obj, remember=(request.form.get("remember") == "on"))
            flash("Login successful! Let's read some manga!", 'success')
            return redirect(url_for('manga.index'))

        flash('Invalid username or password. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
```

- [ ] **Step 3: Smoke-test manually**

```bash
source .venv/bin/activate && python app.py
```

Navigate to `http://localhost:5000`. Log in — verify it succeeds.

- [ ] **Step 4: Commit**

```bash
git add app.py views/auth.py
git commit -m "refactor: migrate app.py and auth.py to db_cursor context manager"
```

---

### Task 4: Fix N+1 query and rewrite `views/manga.py` base routes

**Files:**
- Modify: `views/manga.py`

**Interfaces:**
- Consumes: `db_cursor()` from `utils.db`, `to_est()` from `utils.formatting`, `scrape_manga_details()` from `scraper`
- Produces: `_build_manga_list(cursor, user_id, new_counts=None) -> list` — shared helper for both the index route and API endpoints

**Note:** The `select_chapter` route (which referenced a non-existent template) is removed in this rewrite.

- [ ] **Step 1: Replace `views/manga.py` with the following**

This is a full-file replacement. The API endpoints will be appended in Tasks 5 and 6.

```python
from flask import Blueprint, request, redirect, url_for, flash, render_template, session, jsonify
from flask_login import login_required, current_user
from utils.db import db_cursor
from utils.formatting import to_est
from scraper import scrape_manga_details
from datetime import datetime
import pytz

manga_bp = Blueprint("manga", __name__)


def _build_manga_list(cursor, user_id, new_counts=None):
    """
    Fetch manga and their chapters for a user in 2 queries instead of N+1.
    new_counts: dict of {manga_id: count} — keys may be int or str (normalised internally).
    """
    counts = {int(k): int(v) for k, v in (new_counts or {}).items()}

    cursor.execute(
        """
        SELECT m.*,
            (SELECT chapter_title FROM chapters WHERE manga_id = m.id ORDER BY url DESC LIMIT 1)
            AS latest_chapter_title
        FROM manga m
        WHERE m.user_id = %s
        ORDER BY m.title ASC
        """,
        (user_id,),
    )
    manga_list = list(cursor.fetchall())

    manga_ids = [m["id"] for m in manga_list]
    chapters_by_manga = {}
    if manga_ids:
        cursor.execute(
            "SELECT manga_id, chapter_title, url FROM chapters WHERE manga_id = ANY(%s) ORDER BY url DESC",
            (manga_ids,),
        )
        for ch in cursor.fetchall():
            chapters_by_manga.setdefault(ch["manga_id"], []).append(
                {"chapter_title": ch["chapter_title"], "url": ch["url"]}
            )

    for manga in manga_list:
        manga["chapters"] = chapters_by_manga.get(manga["id"], [])
        manga["new_chapters_count"] = counts.get(manga["id"], 0)

    return manga_list


@manga_bp.route("/")
@login_required
def index():
    with db_cursor() as cursor:
        new_chapters_dict = session.pop("new_chapters_dict", {})
        manga_list = _build_manga_list(cursor, current_user.id, new_chapters_dict)

        last_checked_values = [m["last_checked"] for m in manga_list if m["last_checked"]]
        formatted_last_checked = (
            to_est(max(last_checked_values)).strftime("%A, %B %d, %Y %I:%M:%S %p")
            if last_checked_values
            else "Never Checked"
        )

        cursor.execute(
            "SELECT * FROM log WHERE user_id = %s ORDER BY date_added DESC",
            (current_user.id,),
        )
        logs = cursor.fetchall()

    formatted_logs = [
        {
            "manga_title": log["manga_title"],
            "chapters_added": log["chapters_added"],
            "date_added": to_est(log["date_added"]).strftime("%A, %B %d, %Y %I:%M %p"),
        }
        for log in logs
    ]

    return render_template(
        "index.html",
        manga_list=manga_list,
        last_checked=formatted_last_checked,
        logs=formatted_logs,
    )


@manga_bp.route("/check_updates", methods=["POST"])
@login_required
def check_updates():
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM manga WHERE user_id = %s", (current_user.id,))
        manga_list = list(cursor.fetchall())

        total_new_chapters = 0
        new_chapters_dict = {}

        for manga in manga_list:
            title, chapter_titles, chapter_urls, _ = scrape_manga_details(manga["url"])
            if title is None or chapter_titles is None:
                continue

            manga_id = manga["id"]
            cursor.execute("SELECT url FROM chapters WHERE manga_id = %s", (manga_id,))
            existing_urls = {row["url"] for row in cursor.fetchall()}

            new_count = 0
            for chapter_title, chapter_url in zip(chapter_titles, chapter_urls):
                if chapter_url not in existing_urls:
                    try:
                        cursor.execute(
                            "INSERT INTO chapters (manga_id, chapter_title, url) VALUES (%s, %s, %s)",
                            (manga_id, chapter_title, chapter_url),
                        )
                        new_count += 1
                    except Exception as e:
                        flash(f"Error adding chapter '{chapter_title}': {str(e)}", "error")

            new_chapters_dict[str(manga_id)] = new_count
            total_new_chapters += new_count

            cursor.execute(
                "UPDATE manga SET last_checked = %s WHERE id = %s AND user_id = %s",
                (datetime.now(pytz.utc), manga_id, current_user.id),
            )

            if new_count > 0:
                cursor.execute(
                    "INSERT INTO log (manga_title, chapters_added, date_added, user_id) VALUES (%s, %s, %s, %s)",
                    (title, new_count, datetime.now(pytz.utc), current_user.id),
                )

    flash(f"Update check complete! {total_new_chapters} update(s) found.", "info")
    session["new_chapters_dict"] = new_chapters_dict
    return redirect(url_for("manga.index"))


@manga_bp.route("/add", methods=["POST"])
@login_required
def add_manga():
    url = request.form["url"]

    with db_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM manga WHERE url = %s AND user_id = %s",
            (url, current_user.id),
        )
        existing_manga = cursor.fetchone()

    if existing_manga:
        flash(f'The manga "{existing_manga["title"]}" is already in your tracker.', "error")
        return redirect(url_for("manga.index"))

    title, chapter_titles, chapter_urls, _ = scrape_manga_details(url)
    if title is None or chapter_titles is None:
        flash("Error: Could not retrieve manga details. Please try again.", "error")
        return redirect(url_for("manga.index"))

    with db_cursor() as cursor:
        cursor.execute(
            "INSERT INTO manga (title, url, last_checked, user_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (title, url, datetime.now(pytz.utc), current_user.id),
        )
        row = cursor.fetchone()
        if row is None:
            flash("Error: Failed to add manga to the database.", "error")
            return redirect(url_for("manga.index"))

        manga_id = row["id"]
        for chapter_title, chapter_url in zip(chapter_titles, chapter_urls):
            cursor.execute(
                "INSERT INTO chapters (manga_id, chapter_title, url) VALUES (%s, %s, %s)",
                (manga_id, chapter_title, chapter_url),
            )

    flash("Manga added successfully!", "success")
    return redirect(url_for("manga.index"))


@manga_bp.route("/delete/<int:id>")
@login_required
def delete_manga(id):
    with db_cursor() as cursor:
        cursor.execute(
            "DELETE FROM manga WHERE id = %s AND user_id = %s", (id, current_user.id)
        )
    flash("Manga deleted successfully.", "info")
    return redirect(url_for("manga.index"))
```

- [ ] **Step 2: Smoke-test manually**

```bash
python app.py
```

Navigate to `http://localhost:5000`. Verify the manga list loads, "Last Checked" shows, and the activity log appears.

- [ ] **Step 3: Commit**

```bash
git add views/manga.py
git commit -m "refactor: fix N+1 query, add _build_manga_list helper, migrate to db_cursor, remove dead select_chapter route"
```

---

### Task 5: Add `/api/check_updates` endpoint

**Files:**
- Modify: `views/manga.py`
- Create: `tests/test_api.py`

**Interfaces:**
- Consumes: `_build_manga_list(cursor, user_id, new_counts)`, `scrape_manga_details()`, `to_est()`
- Produces: `POST /api/check_updates` → JSON `{ total_new: int, last_checked: str, manga: list[MangaDict], logs: list[LogDict] }`
  - `MangaDict`: `{ id, title, url, latest_chapter_title, new_chapters_count, chapters: [{chapter_title, url}] }`
  - `LogDict`: `{ manga_title, chapters_added, date_added }`
  - Manga list is sorted: updated items (`new_chapters_count > 0`) first, then alphabetically by title

- [ ] **Step 1: Write failing test**

Create `tests/test_api.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


def test_api_check_updates_returns_json(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn

        resp = logged_in_client.post('/api/check_updates')

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'manga' in data
    assert 'total_new' in data
    assert 'logs' in data
    assert 'last_checked' in data
    assert isinstance(data['manga'], list)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_api.py::test_api_check_updates_returns_json -v
```

Expected: 404 — route does not exist yet

- [ ] **Step 3: Append `/api/check_updates` to `views/manga.py`**

Add after `delete_manga`:

```python
@manga_bp.route("/api/check_updates", methods=["POST"])
@login_required
def api_check_updates():
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM manga WHERE user_id = %s", (current_user.id,))
        manga_list = list(cursor.fetchall())

        total_new = 0
        new_counts = {}

        for manga in manga_list:
            title, chapter_titles, chapter_urls, _ = scrape_manga_details(manga["url"])
            if title is None or chapter_titles is None:
                new_counts[manga["id"]] = 0
                continue

            cursor.execute("SELECT url FROM chapters WHERE manga_id = %s", (manga["id"],))
            existing_urls = {row["url"] for row in cursor.fetchall()}

            new_count = 0
            for ch_title, ch_url in zip(chapter_titles, chapter_urls):
                if ch_url not in existing_urls:
                    cursor.execute(
                        "INSERT INTO chapters (manga_id, chapter_title, url) VALUES (%s, %s, %s)",
                        (manga["id"], ch_title, ch_url),
                    )
                    new_count += 1

            cursor.execute(
                "UPDATE manga SET last_checked = %s WHERE id = %s AND user_id = %s",
                (datetime.now(pytz.utc), manga["id"], current_user.id),
            )

            if new_count > 0:
                cursor.execute(
                    "INSERT INTO log (manga_title, chapters_added, date_added, user_id) VALUES (%s, %s, %s, %s)",
                    (title, new_count, datetime.now(pytz.utc), current_user.id),
                )

            new_counts[manga["id"]] = new_count
            total_new += new_count

        updated_manga = _build_manga_list(cursor, current_user.id, new_counts)

        cursor.execute(
            "SELECT * FROM log WHERE user_id = %s ORDER BY date_added DESC",
            (current_user.id,),
        )
        logs = list(cursor.fetchall())

    manga_response = [
        {
            "id": m["id"],
            "title": m["title"],
            "url": m["url"],
            "latest_chapter_title": m["latest_chapter_title"],
            "new_chapters_count": m["new_chapters_count"],
            "chapters": m["chapters"],
        }
        for m in updated_manga
    ]
    manga_response.sort(key=lambda x: (x["new_chapters_count"] == 0, x["title"].lower()))

    last_checked_values = [m["last_checked"] for m in updated_manga if m.get("last_checked")]
    last_checked = (
        to_est(max(last_checked_values)).strftime("%A, %B %d, %Y %I:%M:%S %p")
        if last_checked_values
        else "Never Checked"
    )

    formatted_logs = [
        {
            "manga_title": log["manga_title"],
            "chapters_added": log["chapters_added"],
            "date_added": to_est(log["date_added"]).strftime("%A, %B %d, %Y %I:%M %p"),
        }
        for log in logs
    ]

    return jsonify({
        "total_new": total_new,
        "last_checked": last_checked,
        "manga": manga_response,
        "logs": formatted_logs,
    })
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_api.py::test_api_check_updates_returns_json -v
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add views/manga.py tests/test_api.py
git commit -m "feat: add /api/check_updates JSON endpoint"
```

---

### Task 6: Add `/api/add` and `/api/manga/<id>` endpoints

**Files:**
- Modify: `views/manga.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `POST /api/add` — body: `{ url: str }` → `{ manga: MangaDict }` (200) or `{ error: str }` (409 duplicate, 422 scrape failure, 400 missing url)
- Produces: `DELETE /api/manga/<id>` → `{ ok: true }` (200) or `{ error: str }` (404)
- `MangaDict` shape same as Task 5: `{ id, title, url, latest_chapter_title, new_chapters_count, chapters }`; chapters ordered newest-first to match the dropdown

- [ ] **Step 1: Write failing tests**

Append to `tests/test_api.py`:

```python
def test_api_delete_returns_ok(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'id': 42}

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn

        resp = logged_in_client.delete('/api/manga/42')

    assert resp.status_code == 200
    assert resp.get_json() == {'ok': True}


def test_api_delete_returns_404_when_not_found(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn

        resp = logged_in_client.delete('/api/manga/999')

    assert resp.status_code == 404


def test_api_add_duplicate_returns_409(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'id': 1, 'title': 'Naruto', 'url': 'https://example.com', 'user_id': 1}

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn

        resp = logged_in_client.post(
            '/api/add',
            json={'url': 'https://example.com'},
        )

    assert resp.status_code == 409
    assert 'error' in resp.get_json()


def test_api_add_bad_url_returns_422(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn
        with patch('views.manga.scrape_manga_details', return_value=(None, None, None, None)):
            resp = logged_in_client.post(
                '/api/add',
                json={'url': 'https://bad-url.com'},
            )

    assert resp.status_code == 422
    assert 'error' in resp.get_json()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_api.py -v -k "delete or api_add"
```

Expected: 404 errors — routes don't exist yet

- [ ] **Step 3: Append `/api/add` and `/api/manga/<id>` to `views/manga.py`**

Add after `api_check_updates`:

```python
@manga_bp.route("/api/add", methods=["POST"])
@login_required
def api_add():
    data = request.get_json()
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required."}), 400

    with db_cursor() as cursor:
        cursor.execute(
            "SELECT * FROM manga WHERE url = %s AND user_id = %s",
            (url, current_user.id),
        )
        existing = cursor.fetchone()

    if existing:
        return jsonify({"error": f'The manga "{existing["title"]}" is already in your tracker.'}), 409

    title, chapter_titles, chapter_urls, _ = scrape_manga_details(url)
    if title is None or chapter_titles is None:
        return jsonify({"error": "Could not retrieve manga details. Please check the URL."}), 422

    with db_cursor() as cursor:
        cursor.execute(
            "INSERT INTO manga (title, url, last_checked, user_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (title, url, datetime.now(pytz.utc), current_user.id),
        )
        manga_id = cursor.fetchone()["id"]
        for ch_title, ch_url in zip(chapter_titles, chapter_urls):
            cursor.execute(
                "INSERT INTO chapters (manga_id, chapter_title, url) VALUES (%s, %s, %s)",
                (manga_id, ch_title, ch_url),
            )

    # Return chapters newest-first to match the dropdown (ORDER BY url DESC)
    chapters = [
        {"chapter_title": t, "url": u}
        for t, u in zip(reversed(chapter_titles), reversed(chapter_urls))
    ]
    latest = chapter_titles[-1] if chapter_titles else None

    return jsonify({
        "manga": {
            "id": manga_id,
            "title": title,
            "url": url,
            "latest_chapter_title": latest,
            "new_chapters_count": 0,
            "chapters": chapters,
        }
    })


@manga_bp.route("/api/manga/<int:id>", methods=["DELETE"])
@login_required
def api_delete_manga(id):
    with db_cursor() as cursor:
        cursor.execute(
            "DELETE FROM manga WHERE id = %s AND user_id = %s RETURNING id",
            (id, current_user.id),
        )
        deleted = cursor.fetchone()

    if not deleted:
        return jsonify({"error": "Not found."}), 404

    return jsonify({"ok": True})
```

- [ ] **Step 4: Run all API tests**

```bash
python -m pytest tests/test_api.py -v
```

Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add views/manga.py tests/test_api.py
git commit -m "feat: add /api/add and DELETE /api/manga/<id> endpoints"
```

---

### Task 7: Create `static/app.js`

**Files:**
- Create: `static/app.js`

**Interfaces:**
- Consumes: `POST /api/check_updates`, `POST /api/add`, `DELETE /api/manga/<id>`
- Consumes from DOM: `.form-inline` (add form), `form[action*="check_updates"]`, `#spinner-overlay`, `.scroll-box-manga ul`, `.scroll-box-logs ul`, `#last-checked`, `#deleteModal`, `#modal-text`, `#confirmDeleteBtn`, `.flashes` (or `.content` as parent)
- Produces: `renderMangaCard(manga)`, `confirmDelete(mangaId, mangaTitle)`, `updateChapterLink(mangaId)`, `closeModal()` as globals (used by inline `onchange`/`onclick` in the template)
- Produces: `data-manga-id` on rendered `<li>` elements (used by delete to locate the card)

- [ ] **Step 1: Create `static/app.js`**

```javascript
/* -------------------------------------------------------
   Inline flash messages
------------------------------------------------------- */
function showFlash(message, category) {
  let container = document.querySelector('.flashes');
  if (!container) {
    container = document.createElement('div');
    container.className = 'flashes';
    document.querySelector('.content').appendChild(container);
  }
  const alert = document.createElement('div');
  alert.className = `alert alert-${category} flash-message`;
  alert.textContent = message;
  container.appendChild(alert);
  setTimeout(() => alert.remove(), 4000);
}

/* -------------------------------------------------------
   Chapter link sync
------------------------------------------------------- */
function updateChapterLink(mangaId) {
  const select = document.getElementById(`chapter_select_${mangaId}`);
  const link = document.getElementById(`read_link_${mangaId}`);
  if (select && link) link.href = select.value;
}

/* -------------------------------------------------------
   Render a single manga card <li>
------------------------------------------------------- */
function renderMangaCard(manga) {
  const li = document.createElement('li');
  li.dataset.mangaId = manga.id;
  if (manga.new_chapters_count > 0) li.classList.add('updated-chapters');

  const firstUrl = manga.chapters.length > 0 ? manga.chapters[0].url : '#';
  const chapterOptions = manga.chapters
    .map((ch, i) => `<option value="${ch.url}"${i === 0 ? ' selected' : ''}>${ch.chapter_title}</option>`)
    .join('');

  const newBadge = manga.new_chapters_count > 0
    ? `<span class="new-chapters"># ${manga.new_chapters_count} new chapter(s)!</span><br>`
    : '';

  li.innerHTML = `
    <strong>${manga.title}</strong><br>
    Latest Chapter: ${manga.latest_chapter_title || 'N/A'}<br>
    <label for="chapter_select_${manga.id}">Read Chapter:</label>
    <select id="chapter_select_${manga.id}" name="chapter"
      onchange="updateChapterLink(${manga.id})">
      ${chapterOptions}
    </select><br>
    ${newBadge}
    <div class="manga-links">
      <a id="read_link_${manga.id}" href="${firstUrl}" target="_blank">Read on MangaPill</a>
      <a href="#" data-manga-id="${manga.id}" data-manga-title="${manga.title}"
         onclick="confirmDelete(this.dataset.mangaId, this.dataset.mangaTitle)">Delete</a>
    </div>
  `;
  return li;
}

/* -------------------------------------------------------
   Re-render the full manga list
------------------------------------------------------- */
function renderMangaList(mangaArray) {
  const ul = document.querySelector('.scroll-box-manga ul');
  ul.innerHTML = '';
  mangaArray.forEach(manga => ul.appendChild(renderMangaCard(manga)));
}

/* -------------------------------------------------------
   Re-render the activity log
------------------------------------------------------- */
function renderLogs(logs) {
  const ul = document.querySelector('.scroll-box-logs ul');
  ul.innerHTML = '';
  logs.forEach(log => {
    const li = document.createElement('li');
    li.innerHTML = `${log.date_added}<br><strong>${log.manga_title}</strong>${log.chapters_added > 0 ? `: ${log.chapters_added} new chapter(s) added!` : ''}`;
    ul.appendChild(li);
  });
}

/* -------------------------------------------------------
   Check for updates
------------------------------------------------------- */
document.querySelector('form[action*="check_updates"]').addEventListener('submit', async (e) => {
  e.preventDefault();
  const overlay = document.getElementById('spinner-overlay');
  overlay.style.display = 'flex';

  try {
    const resp = await fetch('/api/check_updates', { method: 'POST' });
    if (!resp.ok) throw new Error('Server error');
    const data = await resp.json();
    renderMangaList(data.manga);
    renderLogs(data.logs);
    document.getElementById('last-checked').textContent = `Last Checked: ${data.last_checked}`;
    showFlash(`Update check complete! ${data.total_new} update(s) found.`, 'info');
  } catch {
    showFlash('Error checking for updates. Please try again.', 'error');
  } finally {
    overlay.style.display = 'none';
  }
});

/* -------------------------------------------------------
   Add manga
------------------------------------------------------- */
document.querySelector('.form-inline').addEventListener('submit', async (e) => {
  e.preventDefault();
  const urlInput = document.getElementById('url');
  const btn = e.target.querySelector('button');
  const originalText = btn.textContent;
  btn.textContent = 'Adding...';
  btn.disabled = true;

  try {
    const resp = await fetch('/api/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: urlInput.value.trim() }),
    });
    const data = await resp.json();
    if (data.error) {
      showFlash(data.error, 'error');
    } else {
      document.querySelector('.scroll-box-manga ul').prepend(renderMangaCard(data.manga));
      urlInput.value = '';
      showFlash('Manga added successfully!', 'success');
    }
  } catch {
    showFlash('Error: Could not add manga. Please try again.', 'error');
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

/* -------------------------------------------------------
   Delete modal
------------------------------------------------------- */
function confirmDelete(mangaId, mangaTitle) {
  document.getElementById('deleteModal').style.display = 'block';
  document.getElementById('modal-text').innerText = `Are you sure you want to delete "${mangaTitle}"?`;

  document.getElementById('confirmDeleteBtn').onclick = async function () {
    closeModal();
    try {
      const resp = await fetch(`/api/manga/${mangaId}`, { method: 'DELETE' });
      const data = await resp.json();
      if (data.ok) {
        const li = document.querySelector(`[data-manga-id="${mangaId}"]`);
        if (li) {
          li.style.transition = 'opacity 0.3s, max-height 0.4s';
          li.style.overflow = 'hidden';
          li.style.opacity = '0';
          li.style.maxHeight = '0';
          setTimeout(() => li.remove(), 400);
        }
        showFlash('Manga deleted successfully.', 'info');
      } else {
        showFlash(data.error || 'Error deleting manga.', 'error');
      }
    } catch {
      showFlash('Error: Could not delete manga. Please try again.', 'error');
    }
  };
}

function closeModal() {
  document.getElementById('deleteModal').style.display = 'none';
}

window.onclick = function (event) {
  const modal = document.getElementById('deleteModal');
  if (event.target === modal) closeModal();
};
```

- [ ] **Step 2: Commit**

```bash
git add static/app.js
git commit -m "feat: create app.js with AJAX for check_updates, add, and delete"
```

---

### Task 8: Update `templates/index.html` and fix CSS

**Files:**
- Modify: `templates/index.html`
- Modify: `static/styles.css`

**Interfaces:**
- Consumes: `static/app.js` (loaded via `<script defer>`)
- Requires in DOM: `id="spinner-overlay"`, `id="last-checked"` on the Last Checked `<p>`, `data-manga-id` on every `<li>`, `data-manga-id`/`data-manga-title` on the Delete `<a>`

- [ ] **Step 1: Replace `templates/index.html`**

```html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" type="text/css" href="{{ url_for('static', filename='styles.css') }}">
    <link href="https://fonts.googleapis.com/css2?family=Bangers:wght@400;700&display=swap" rel="stylesheet">
    <title>MangaPill Chapter Tracker - Home</title>
</head>

<body>
    <div id="spinner-overlay" class="spinner-overlay">
        <div class="spinner-box">
            <div class="spinner"></div>
            <p>Checking for updates...</p>
        </div>
    </div>

    <div class="wrap">
        <a href="{{ url_for('auth.logout') }}" class="logout-btn">Log Out</a>
        <div class="title">
            <img src="../static/images/ryangit.png">
            <h1>MangaPill Chapter Tracker</h1>
        </div>

        {% if current_user.is_authenticated and current_user.username in ["sarahsweet", "rdjsweet"] %}
        <nav class="quick-links">
            <a href="{{ url_for('halloween.index') }}">🎃 Halloween</a>
        </nav>
        {% endif %}

        <div class="container">
            <div class="content">
                <p>Paste URL from <u><strong>Manga Chapter List</strong></u> Below to Add</p>
                <form action="{{ url_for('manga.add_manga') }}" method="POST" class="form-inline">
                    <input type="text" name="url" id="url" placeholder="Enter manga URL here" required>
                    <button type="submit">Add</button>
                </form>

                {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                <div class="flashes">
                    {% for category, message in messages %}
                    <div class="alert alert-{{ category }} flash-message">{{ message }}</div>
                    {% endfor %}
                </div>
                {% endif %}
                {% endwith %}

                <form action="{{ url_for('manga.check_updates') }}" method="post">
                    <button type="submit" class="check-updates-btn">Check for Updates</button>
                </form>
                <br>
                <p id="last-checked">Last Checked: {{ last_checked }}</p>
            </div>

            <div class="scrollables">
                <div class="scroll-box-manga">
                    <h2>Manga List</h2>
                    <ul>
                        {% for manga in manga_list %}
                        <li data-manga-id="{{ manga['id'] }}"
                            class="{% if manga['new_chapters_count'] > 0 %}updated-chapters{% endif %}">
                            <strong>{{ manga['title'] }}</strong><br>
                            Latest Chapter: {{ manga['latest_chapter_title'] }}<br>

                            <label for="chapter_select_{{ manga['id'] }}">Read Chapter:</label>
                            <select id="chapter_select_{{ manga['id'] }}" name="chapter"
                                onchange="updateChapterLink({{ manga['id'] }})">
                                {% for chapter in manga['chapters'] %}
                                <option value="{{ chapter['url'] }}" {% if loop.first %}selected{% endif %}>
                                    {{ chapter['chapter_title'] }}
                                </option>
                                {% endfor %}
                            </select><br>

                            {% if manga['new_chapters_count'] > 0 %}
                            <span class="new-chapters"># {{ manga['new_chapters_count'] }} new chapter(s)!</span><br>
                            {% endif %}

                            <div class="manga-links">
                                <a id="read_link_{{ manga['id'] }}"
                                   href="{{ manga['chapters'][0]['url'] if manga['chapters'] else '#' }}"
                                   target="_blank">Read on MangaPill</a>
                                <a href="#"
                                   data-manga-id="{{ manga['id'] }}"
                                   data-manga-title="{{ manga['title'] }}"
                                   onclick="confirmDelete(this.dataset.mangaId, this.dataset.mangaTitle)">Delete</a>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>

                <div class="scroll-box-logs">
                    <div class="logs">
                        <h2>Activity Log</h2>
                        <ul>
                            {% for log in logs %}
                            <li>{{ log['date_added'] }}<br>
                                <strong>{{ log['manga_title'] }}</strong>
                                {% if log['chapters_added'] > 0 %}
                                : {{ log['chapters_added'] }} new chapter(s) added!
                                {% endif %}
                            </li>
                            {% endfor %}
                        </ul>
                    </div>
                </div>
            </div>
        </div>

        <div id="deleteModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeModal()">&times;</span>
                <h2>Confirm Deletion</h2>
                <p id="modal-text">Are you sure you want to delete this manga?</p>
                <button id="confirmDeleteBtn">✓</button>
                <button class="modal-cancel-btn" onclick="closeModal()">✕</button>
            </div>
        </div>

        <footer class="site-footer">
            &copy; 2025 SweetSoft, Ryan Sweet. All Rights Reserved.
        </footer>
    </div>

    <script src="{{ url_for('static', filename='app.js') }}" defer></script>
</body>

</html>
```

- [ ] **Step 2: Add spinner CSS to `static/styles.css`**

Append at the end of the file:

```css
/* Spinner overlay */
.spinner-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 100;
    align-items: center;
    justify-content: center;
}

.spinner-box {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.spinner-box p {
    margin: 0;
    font-size: 1.1em;
    color: #333;
}

.spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #ccc;
    border-top-color: #3498db;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 1rem;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Modal cancel button */
.modal-cancel-btn {
    background-color: #888 !important;
}

.modal-cancel-btn:hover {
    background-color: #666 !important;
}
```

- [ ] **Step 3: Fix the chapter `select` width in `static/styles.css`**

Find and replace the `select` rule (around line 265):

Old:
```css
select {
    font-size: 1em;
    border: 1px solid #ccc;
    border-radius: 8px;
    box-sizing: border-box;
    width: 10vw;
    height: 3vh;
}
```

New:
```css
select {
    font-size: 1em;
    border: 1px solid #ccc;
    border-radius: 8px;
    box-sizing: border-box;
    width: auto;
    min-width: 8rem;
    max-width: 100%;
    height: 3vh;
}
```

Also update the mobile override (around line 497):

Old:
```css
    select {
        width: 34vw;
    }
```

New:
```css
    select {
        min-width: 40vw;
        max-width: 100%;
        width: auto;
    }
```

- [ ] **Step 4: Full smoke test**

```bash
python app.py
```

Verify all of the following:
- Page loads with manga list
- "Check for Updates" button shows spinner, list and log update without page reload
- Updated manga appear at the top with green highlight and new chapter count
- "Add" form adds a manga card inline, clears the input, shows success flash
- Delete confirm modal opens, clicking confirm fades the card out, shows flash
- Flash messages auto-dismiss after 4 seconds
- Chapter dropdown is wide enough to read chapter names
- "Read on MangaPill" link is correct on initial load (no `#` href)

- [ ] **Step 5: Run the full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests passed

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/styles.css
git commit -m "feat: wire AJAX in index.html, add spinner, fix structure and UX issues"
```
