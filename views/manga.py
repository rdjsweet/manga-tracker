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
                    cursor.execute(
                        "INSERT INTO chapters (manga_id, chapter_title, url) VALUES (%s, %s, %s)",
                        (manga_id, chapter_title, chapter_url),
                    )
                    new_count += 1

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
