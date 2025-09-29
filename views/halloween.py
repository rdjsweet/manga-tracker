from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from utils.db import get_db_connection
import random

halloween_bp = Blueprint("halloween", __name__, url_prefix="/halloween")

@halloween_bp.route("/")
@login_required
def index():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM halloween_movies
        ORDER BY title ASC;
        """,
        
    )

    movies = cursor.fetchall()

    unwatched = [m for m in movies if not m['watched']]
    random_movie = random.choice(unwatched) if unwatched else None

    cursor.close()
    connection.close()
    return render_template("halloween/index.html", movies=movies, random_movie=random_movie)

@halloween_bp.route("/add", methods=["POST"])
@login_required
def add_movie():
    title = request.form.get("title")
    if not title:
        flash("Title is required!", "error")
        return redirect(url_for("halloween.index"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO halloween_movies (title)
        VALUES (%s);
        """,
        (title,)
    )

    connection.commit()
    cursor.close()
    connection.close()
    flash("Movie added successfully!", "success")
    return redirect(url_for("halloween.index"))

@halloween_bp.route("/update/<int:id>", methods=["POST"])
@login_required
def update_movie(id):
    watched = request.json.get("watched")

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE halloween_movies
        SET watched = %s
        WHERE id = %s;
        """,
        (watched, id)
    )

    connection.commit()
    cursor.close()
    connection.close()
    return "", 204

@halloween_bp.route("/delete/<int:id>")
@login_required
def delete_movie(id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM halloween_movies
        WHERE id = %s;
        """,
        (id,)
    )

    connection.commit()
    cursor.close()
    connection.close()
    flash("Movie deleted successfully!", "success")
    return redirect(url_for("halloween.index"))