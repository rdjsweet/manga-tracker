from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from flask_login import login_required, current_user
from utils.db import get_db_connection
from scraper import scrape_manga_details
from datetime import datetime
import pytz

manga_bp = Blueprint("manga", __name__)
est = pytz.timezone("America/New_York")

def to_est(dt):
    return dt.replace(tzinfo=pytz.utc).astimezone(est)

@manga_bp.route("/")
@login_required
def index():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT m.*, 
        (SELECT chapter_title 
            FROM chapters 
            WHERE chapters.manga_id = m.id 
            ORDER BY url DESC 
            LIMIT 1) AS latest_chapter_title
        FROM manga AS m
        WHERE m.user_id = %s
        ORDER BY m.title ASC;
        """,
        (current_user.id,),
    )

    manga_list = cursor.fetchall()

    for manga in manga_list:
        cursor.execute(
            "SELECT chapter_title, url FROM chapters WHERE manga_id = %s ORDER BY url DESC",
            (manga["id"],),
        )
        manga["chapters"] = cursor.fetchall()

    new_chapters_dict = session.pop("new_chapters_dict", {})

    for manga in manga_list:
        manga["new_chapters_count"] = int(new_chapters_dict.get(str(manga["id"]), 0))

    last_checked_values = [
        manga["last_checked"] for manga in manga_list if manga["last_checked"]
    ]
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

    cursor.close()
    connection.close()
    return render_template(
        "index.html",
        manga_list=manga_list,
        last_checked=formatted_last_checked,
        logs=formatted_logs,
    )

@manga_bp.route("/check_updates", methods=["POST"])
@login_required
def check_updates():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM manga WHERE user_id = %s", (current_user.id,))
    manga_list = cursor.fetchall()

    total_new_chapters = 0
    new_chapters_dict = {}

    for manga in manga_list:
        url = manga["url"]
        title, chapter_titles, chapter_urls, _ = scrape_manga_details(url)

        if title is not None and chapter_titles is not None:
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

    connection.commit()
    cursor.close()
    connection.close()

    flash(f"Update check complete! {total_new_chapters} update(s) found.", "info")
    session["new_chapters_dict"] = new_chapters_dict
    return redirect(url_for("manga.index"))

@manga_bp.route("/add", methods=["POST"])
@login_required
def add_manga():
    url = request.form["url"]
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM manga WHERE url = %s AND user_id = %s",
        (url, current_user.id),
    )
    existing_manga = cursor.fetchone()

    if existing_manga:
        flash(f'The manga "{existing_manga["title"]}" is already in your tracker.', "error")
        cursor.close()
        connection.close()
        return redirect(url_for("manga.index"))

    title, chapter_titles, chapter_urls, _ = scrape_manga_details(url)

    if title is None or chapter_titles is None:
        flash("Error: Could not retrieve manga details. Please try again.", "error")
        cursor.close()
        connection.close()
        return redirect(url_for("manga.index"))

    cursor.execute(
        "INSERT INTO manga (title, url, last_checked, user_id) VALUES (%s, %s, %s, %s) RETURNING id",
        (title, url, datetime.now(pytz.utc), current_user.id),
    )
    row = cursor.fetchone()

    if row is None:
        flash("Error: Failed to add manga to the database.", "error")
        cursor.close()
        connection.close()
        return redirect(url_for("manga.index"))

    manga_id = row["id"]

    for chapter_title, chapter_url in zip(chapter_titles, chapter_urls):
        cursor.execute(
            "INSERT INTO chapters (manga_id, chapter_title, url) VALUES (%s, %s, %s)",
            (manga_id, chapter_title, chapter_url),
        )

    connection.commit()
    cursor.close()
    connection.close()
    flash("Manga added successfully!", "success")
    return redirect(url_for("manga.index"))

@manga_bp.route("/delete/<int:id>")
@login_required
def delete_manga(id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM manga WHERE id = %s AND user_id = %s", (id, current_user.id)
    )
    connection.commit()
    cursor.close()
    connection.close()
    flash("Manga deleted successfully.", "info")
    return redirect(url_for("manga.index"))

@manga_bp.route("/select_chapter/<int:manga_id>")
def select_chapter(manga_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM chapters WHERE manga_id = %s ORDER BY created_at DESC",
        (manga_id,),
    )
    chapters = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "chapter_dropdown.html", chapters=chapters, manga_id=manga_id
    )