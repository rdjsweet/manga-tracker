from flask import Blueprint, request, redirect, url_for, flash, render_template, session, jsonify, Response, abort
from flask_login import login_required, current_user
from utils.db import db_cursor
from utils.formatting import to_est
from scraper import scrape_manga_details
from datetime import datetime
from urllib.parse import urlparse
import requests
import psycopg2
import pytz

manga_bp = Blueprint("manga", __name__)

MANGAPILL_REFERER = "https://mangapill.com/"


def _is_safe_cover_url(candidate):
    """Guard cover downloads against SSRF: https only, no internal hosts."""
    try:
        parsed = urlparse(candidate)
    except (ValueError, AttributeError):
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if (
        host in ("localhost", "0.0.0.0")
        or host.startswith("127.")
        or host.startswith("10.")
        or host.startswith("192.168.")
        or host.startswith("169.254.")
    ):
        return False
    return True


def _download_cover(cover_url):
    """Fetch cover bytes from the CDN with the Referer it requires.

    Returns (bytes, mime) on success, or (None, None) on any failure.
    """
    if not _is_safe_cover_url(cover_url):
        return None, None
    try:
        resp = requests.get(cover_url, headers={"Referer": MANGAPILL_REFERER}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        return None, None
    return resp.content, resp.headers.get("Content-Type", "image/jpeg")


def _save_cover(cursor, manga_id, cover_url):
    """Record the cover URL and, if downloadable, store the image bytes."""
    if not cover_url:
        return
    data, mime = _download_cover(cover_url)
    if data is None:
        # Keep the URL as a reference even if the download failed this time.
        cursor.execute(
            "UPDATE manga SET cover_url = %s WHERE id = %s", (cover_url, manga_id)
        )
        return
    cursor.execute(
        "UPDATE manga SET cover_url = %s, cover_image = %s, cover_mime = %s WHERE id = %s",
        (cover_url, psycopg2.Binary(data), mime, manga_id),
    )


def _read_state(chapters, last_read_url):
    """Compute read progress for a single series.

    chapters is newest-first (index 0 is the newest). Returns the number of
    unread chapters and the next chapter to read so the UI never sends the
    reader straight to the newest chapter and spoils the ones in between.
    """
    if not chapters:
        return {"unread_count": 0, "continue_url": None, "continue_title": None}

    # Nothing read yet: everything is unread, start from the oldest chapter.
    if not last_read_url:
        oldest = chapters[-1]
        return {
            "unread_count": len(chapters),
            "continue_url": oldest["url"],
            "continue_title": oldest["chapter_title"],
        }

    idx = next((i for i, c in enumerate(chapters) if c["url"] == last_read_url), None)

    # last_read no longer in the list, or already on the newest: treat as
    # caught up rather than risk a false flood of "unread".
    if idx is None or idx == 0:
        return {"unread_count": 0, "continue_url": None, "continue_title": None}

    # The next chapter to read is the one immediately newer than last_read.
    nxt = chapters[idx - 1]
    return {
        "unread_count": idx,
        "continue_url": nxt["url"],
        "continue_title": nxt["chapter_title"],
    }


def _manga_to_json(manga):
    """Serialize a manga dict (as built by _build_manga_list) for the API."""
    return {
        "id": manga["id"],
        "title": manga["title"],
        "url": manga["url"],
        "has_cover": bool(manga.get("has_cover")),
        "latest_chapter_title": manga.get("latest_chapter_title"),
        "unread_count": manga["unread_count"],
        "continue_url": manga["continue_url"],
        "continue_title": manga["continue_title"],
        "caught_up": manga["continue_url"] is None,
        "chapters": manga["chapters"],
    }


def _sort_manga(manga_list):
    """Unread series first, then alphabetically."""
    return sorted(manga_list, key=lambda m: (m["unread_count"] == 0, m["title"].lower()))


def _mark_caught_up(cursor, manga_id):
    """Set a series' last_read to its newest chapter.

    "Newest" is defined by the same `url DESC` ordering the rest of the app
    uses, rather than the scraper's list order, so the two never disagree.
    """
    cursor.execute(
        """
        UPDATE manga SET last_read_url = (
            SELECT url FROM chapters WHERE manga_id = %s ORDER BY url DESC LIMIT 1
        )
        WHERE id = %s
        """,
        (manga_id, manga_id),
    )


def _build_manga_list(cursor, user_id, new_counts=None):
    """Fetch a user's manga and chapters in 2 queries, with read state attached.

    new_counts: optional {manga_id: count} of chapters added in the latest
    check; keys may be int or str (normalised internally).
    """
    counts = {int(k): int(v) for k, v in (new_counts or {}).items()}

    # Select explicit columns and a has_cover flag rather than `m.*`, so the
    # cover_image blobs never get loaded into memory on a list render.
    cursor.execute(
        """
        SELECT m.id, m.title, m.url, m.last_checked, m.last_read_url, m.cover_url,
            (m.cover_image IS NOT NULL) AS has_cover,
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
        chapters = chapters_by_manga.get(manga["id"], [])
        manga["chapters"] = chapters
        manga["new_chapters_count"] = counts.get(manga["id"], 0)
        manga.update(_read_state(chapters, manga.get("last_read_url")))

    return manga_list


@manga_bp.route("/")
@login_required
def index():
    with db_cursor() as cursor:
        new_chapters_dict = session.pop("new_chapters_dict", {})
        manga_list = _sort_manga(_build_manga_list(cursor, current_user.id, new_chapters_dict))

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


def _scan_for_updates(cursor, user_id):
    """Scrape every tracked series, insert new chapters, refresh covers.

    Returns (new_counts, total_new, new_series_count). Shared by the AJAX and
    form-fallback update routes. Does NOT touch last_read_url, so newly found
    chapters naturally become unread.
    """
    cursor.execute(
        "SELECT id, url, cover_url, (cover_image IS NOT NULL) AS has_cover FROM manga WHERE user_id = %s",
        (user_id,),
    )
    manga_list = list(cursor.fetchall())

    new_counts = {}
    total_new = 0
    new_series_count = 0

    for manga in manga_list:
        manga_id = manga["id"]
        title, chapter_titles, chapter_urls, cover_url = scrape_manga_details(manga["url"])
        if title is None or chapter_titles is None:
            new_counts[manga_id] = 0
            continue

        cursor.execute("SELECT url FROM chapters WHERE manga_id = %s", (manga_id,))
        existing_urls = {row["url"] for row in cursor.fetchall()}

        new_count = 0
        for ch_title, ch_url in zip(chapter_titles, chapter_urls):
            if ch_url not in existing_urls:
                cursor.execute(
                    "INSERT INTO chapters (manga_id, chapter_title, url) VALUES (%s, %s, %s)",
                    (manga_id, ch_title, ch_url),
                )
                new_count += 1

        cursor.execute(
            "UPDATE manga SET last_checked = %s WHERE id = %s AND user_id = %s",
            (datetime.now(pytz.utc), manga_id, user_id),
        )

        # Download the cover only when it is new or we don't have one yet, so
        # repeat checks don't re-download every image.
        if cover_url and (cover_url != manga["cover_url"] or not manga["has_cover"]):
            _save_cover(cursor, manga_id, cover_url)

        if new_count > 0:
            cursor.execute(
                "INSERT INTO log (manga_title, chapters_added, date_added, user_id) VALUES (%s, %s, %s, %s)",
                (title, new_count, datetime.now(pytz.utc), user_id),
            )
            new_series_count += 1

        new_counts[manga_id] = new_count
        total_new += new_count

    return new_counts, total_new, new_series_count


@manga_bp.route("/check_updates", methods=["POST"])
@login_required
def check_updates():
    with db_cursor() as cursor:
        new_counts, total_new, _ = _scan_for_updates(cursor, current_user.id)

    flash(f"Update check complete! {total_new} update(s) found.", "info")
    session["new_chapters_dict"] = {str(k): v for k, v in new_counts.items()}
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

    title, chapter_titles, chapter_urls, cover_url = scrape_manga_details(url)
    if title is None or chapter_titles is None:
        flash("Error: Could not retrieve manga details. Please try again.", "error")
        return redirect(url_for("manga.index"))

    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO manga (title, url, last_checked, user_id)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
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
        _mark_caught_up(cursor, manga_id)
        _save_cover(cursor, manga_id, cover_url)

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


@manga_bp.route("/api/check_updates", methods=["POST"])
@login_required
def api_check_updates():
    with db_cursor() as cursor:
        new_counts, total_new, new_series_count = _scan_for_updates(cursor, current_user.id)
        updated_manga = _sort_manga(_build_manga_list(cursor, current_user.id, new_counts))

        cursor.execute(
            "SELECT * FROM log WHERE user_id = %s ORDER BY date_added DESC",
            (current_user.id,),
        )
        logs = list(cursor.fetchall())

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
        "new_series_count": new_series_count,
        "last_checked": last_checked,
        "manga": [_manga_to_json(m) for m in updated_manga],
        "logs": formatted_logs,
    })


@manga_bp.route("/api/add", methods=["POST"])
@login_required
def api_add():
    data = request.get_json() or {}
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

    title, chapter_titles, chapter_urls, cover_url = scrape_manga_details(url)
    if title is None or chapter_titles is None:
        return jsonify({"error": "Could not retrieve manga details. Please check the URL."}), 422

    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO manga (title, url, last_checked, user_id)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (title, url, datetime.now(pytz.utc), current_user.id),
        )
        manga_id = cursor.fetchone()["id"]
        for ch_title, ch_url in zip(chapter_titles, chapter_urls):
            cursor.execute(
                "INSERT INTO chapters (manga_id, chapter_title, url) VALUES (%s, %s, %s)",
                (manga_id, ch_title, ch_url),
            )
        _mark_caught_up(cursor, manga_id)
        _save_cover(cursor, manga_id, cover_url)

        added = next(m for m in _build_manga_list(cursor, current_user.id) if m["id"] == manga_id)

    return jsonify({"manga": _manga_to_json(added)})


@manga_bp.route("/api/manga/<int:id>/read", methods=["POST"])
@login_required
def api_mark_read(id):
    data = request.get_json() or {}
    chapter_url = (data.get("url") or "").strip()
    if not chapter_url:
        return jsonify({"error": "Chapter URL is required."}), 400

    with db_cursor() as cursor:
        cursor.execute(
            "UPDATE manga SET last_read_url = %s WHERE id = %s AND user_id = %s RETURNING id",
            (chapter_url, id, current_user.id),
        )
        if cursor.fetchone() is None:
            return jsonify({"error": "Not found."}), 404

        manga = next(
            (m for m in _build_manga_list(cursor, current_user.id) if m["id"] == id), None
        )

    if manga is None:
        return jsonify({"error": "Not found."}), 404

    return jsonify({"manga": _manga_to_json(manga)})


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


@manga_bp.route("/api/manga/<int:id>/cover")
@login_required
def api_cover(id):
    """Serve a series' stored cover image.

    Covers are downloaded once (with the Referer the CDN requires) and kept in
    the database, so this just streams the stored bytes — no live CDN call.
    """
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT cover_image, cover_mime FROM manga WHERE id = %s AND user_id = %s",
            (id, current_user.id),
        )
        row = cursor.fetchone()

    if not row or row["cover_image"] is None:
        abort(404)

    resp = Response(bytes(row["cover_image"]), content_type=row["cover_mime"] or "image/jpeg")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp
