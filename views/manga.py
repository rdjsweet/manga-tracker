from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Manga, Log
from utils.db import db
from datetime import datetime
from scraper import scrape_manga_details

# Define the blueprint for manga-related routes
manga_bp = Blueprint('manga', __name__)

# Route to display the manga tracker home page
@manga_bp.route('/')
@login_required
def index():
    manga_list = Manga.query.filter_by(user_id=current_user.id).order_by(Manga.title.asc()).all()
    return render_template('index.html', manga_list=manga_list)

# Route to add a new manga to the user's tracker
@manga_bp.route('/add', methods=['POST'])
@login_required
def add_manga():
    if request.method == 'POST':
        url = request.form['url']
        title, latest_chapter_title, chapter_count = scrape_manga_details(url)

        if title is None:
            flash('Error retrieving manga details. Please try again.', 'error')
            return redirect(url_for('manga.index'))

        new_manga = Manga(
            title=title,
            url=url,
            last_checked=datetime.now(),
            chapter_count=chapter_count,
            latest_chapter_title=latest_chapter_title,
            user_id=current_user.id
        )
        try:
            db.session.add(new_manga)
            db.session.commit()
            flash('Manga added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding manga: {str(e)}', 'error')

    return redirect(url_for('manga.index'))

# Route to check for updates on all mangas in the user's tracker
@manga_bp.route('/check_updates', methods=['POST'])
@login_required
def check_updates():
    manga_list = Manga.query.filter_by(user_id=current_user.id).all()

    for manga in manga_list:
        url = manga.url
        title, latest_chapter_title, chapter_count = scrape_manga_details(url)

        # Update manga details if retrieved successfully
        if title is not None and latest_chapter_title is not None and chapter_count is not None:
            previous_count = manga.chapter_count
            new_chapters = max(0, chapter_count - previous_count)

            # Update the Manga object with new information
            manga.latest_chapter_title = latest_chapter_title
            manga.chapter_count = chapter_count
            manga.last_checked = datetime.now()
            manga.new_chapters_count = new_chapters

            # Log if new chapters have been added
            if new_chapters > 0:
                log = Log(
                    manga_title=title,
                    chapters_added=new_chapters,
                    date_added=datetime.now(),
                    user_id=current_user.id
                )
                db.session.add(log)

    # Commit all updates to the database
    db.session.commit()
    flash('Update check complete!', 'info')
    return redirect(url_for('manga.index'))

@manga_bp.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_manga(id):
    manga = Manga.query.get_or_404(id)

    # Ensure the current user is deleting their own manga
    if manga.user_id != current_user.id:
        flash('You are not authorized to delete this manga.', 'error')
        return redirect(url_for('manga.index'))

    db.session.delete(manga)
    db.session.commit()
    flash('Manga deleted successfully.', 'info')
    return redirect(url_for('manga.index'))
