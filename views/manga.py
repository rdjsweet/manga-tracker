from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from utils.db import get_db_connection
from scraper import scrape_manga_details
from datetime import datetime
import pytz

manga_bp = Blueprint('manga', __name__)

est = pytz.timezone('America/New_York')

def to_est(dt):
    """Convert a UTC datetime to EST."""
    return dt.replace(tzinfo=pytz.utc).astimezone(est)

@manga_bp.route('/')
@login_required
def index():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        'SELECT * FROM manga WHERE user_id = %s ORDER BY title ASC',
        (current_user.id,)
    )
    manga_list = cursor.fetchall()

    last_checked_values = [manga['last_checked'] for manga in manga_list if manga['last_checked']]
    if last_checked_values:
        max_last_checked = max(last_checked_values)
        formatted_last_checked = to_est(max_last_checked).strftime('%A, %B %d, %Y %I:%M:%S %p')
    else:
        formatted_last_checked = "Never Checked"

    cursor.execute(
        'SELECT * FROM log WHERE user_id = %s ORDER BY date_added DESC',
        (current_user.id,)
    )
    logs = cursor.fetchall()

    formatted_logs = [
        {
            'manga_title': log['manga_title'],
            'chapters_added': log['chapters_added'],
            'date_added': to_est(log['date_added']).strftime('%A, %B %d, %Y %I:%M %p')
        }
        for log in logs
    ]

    cursor.close()
    connection.close()
    return render_template('index.html', manga_list=manga_list, last_checked=formatted_last_checked, logs=formatted_logs)

@manga_bp.route('/add', methods=['POST'])
@login_required
def add_manga():
    if request.method == 'POST':
        url = request.form['url']
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            'SELECT * FROM manga WHERE url = %s AND user_id = %s',
            (url, current_user.id)
        )
        existing_manga = cursor.fetchone()

        if existing_manga:
            manga_title = existing_manga['title']
            flash(f'The manga "{manga_title}" is already in your tracker.', 'error')
            cursor.close()
            connection.close()
            return redirect(url_for('manga.index'))

        title, latest_chapter_title, chapter_count = scrape_manga_details(url)

        if title is None or latest_chapter_title is None or chapter_count is None:
            flash('Error: Could not retrieve manga details. Please try again.', 'error')
            cursor.close()
            connection.close()
            return redirect(url_for('manga.index'))

        cursor.execute(
            'INSERT INTO manga (title, url, last_checked, chapter_count, latest_chapter_title, user_id) VALUES (%s, %s, %s, %s, %s, %s)',
            (title, url, datetime.now(pytz.utc), chapter_count, latest_chapter_title, current_user.id)
        )
        connection.commit()
        cursor.close()
        connection.close()
        flash('Manga added successfully!', 'success')
        return redirect(url_for('manga.index'))

@manga_bp.route('/check_updates', methods=['POST'])
@login_required
def check_updates():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM manga WHERE user_id = %s', (current_user.id,))
    manga_list = cursor.fetchall()

    total_new_chapters = 0
    
    for manga in manga_list:
        url = manga['url']
        title, latest_chapter_title, chapter_count = scrape_manga_details(url)

        if title is not None and latest_chapter_title is not None and chapter_count is not None:
            previous_count = manga['chapter_count']
            new_chapters = max(0, chapter_count - previous_count)
            total_new_chapters += new_chapters 
            cursor.execute(
                'UPDATE manga SET latest_chapter_title = %s, chapter_count = %s, last_checked = %s, new_chapters_count = %s WHERE id = %s AND user_id = %s',
                (latest_chapter_title, chapter_count, datetime.now(pytz.utc), new_chapters, manga['id'], current_user.id)
            )
            if new_chapters > 0:
                cursor.execute(
                    'INSERT INTO log (manga_title, chapters_added, date_added, user_id) VALUES (%s, %s, %s, %s)',
                    (title, new_chapters, datetime.now(pytz.utc), current_user.id)
                )

    connection.commit()
    cursor.close()
    connection.close()
    flash(f'Update check complete! {total_new_chapters} update(s) found.', 'info')
    return redirect(url_for('manga.index'))

@manga_bp.route('/delete/<int:id>')
@login_required
def delete_manga(id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('DELETE FROM manga WHERE id = %s AND user_id = %s', (id, current_user.id))
    connection.commit()
    cursor.close()
    connection.close()
    flash('Manga deleted successfully.', 'info')
    return redirect(url_for('manga.index'))