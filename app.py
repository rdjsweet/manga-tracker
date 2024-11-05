from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, EqualTo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from scraper import scrape_manga_details

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
load_dotenv()

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Helper Class
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

# DB Helper Function
def get_db_connection():
    # Fetch the DATABASE_URL environment variable to connect
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise Exception("DATABASE_URL environment variable not set")

    # Connect to the PostgreSQL database using psycopg2
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM Users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()
    if user:
        return User(user['id'], user['username'], user['password_hash'])
    return None

# User Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        # Insert new user into the database
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (%s, %s)',
                (username, hashed_password)
            )
            connection.commit()
            cursor.close()
            connection.close()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['username'], user['password_hash'])
            login_user(user_obj)

            # Check if this is the user's first login
            if user['first_login']:
                # Add a welcome message to the log
                cursor = connection.cursor()
                cursor.execute(
                    'INSERT INTO log (manga_title, chapters_added, date_added, user_id) VALUES (%s, %s, %s, %s)',
                    ("Welcome to the MangaPill Chapter Tracker! All your chapter updates will be logged here, showing the title and date so you can easily track the latest releases.", 0, datetime.now(), user['id'])
                )

                # Set first_login to False after the first login
                cursor.execute(
                    'UPDATE users SET first_login = false WHERE id = %s', (user['id'],)
                )

                connection.commit()
                cursor.close()

            connection.close()
            flash('Login successful! Welcome back.', 'success')
            return redirect(url_for('index'))
        else:
            connection.close()
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

# User Logout Route
@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Home Route to Display Manga List and Logs
@app.route('/')
@login_required
def index():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch only manga that belongs to the logged-in user
    cursor.execute(
        'SELECT * FROM manga WHERE user_id = %s ORDER BY title ASC',
        (current_user.id,)
    )
    manga_list = cursor.fetchall()

    # Get the most recent check time from the database if available
    if manga_list:
        last_checked_values = [manga['last_checked'] for manga in manga_list if manga['last_checked']]
        if last_checked_values:
            most_recent_check = max(last_checked_values)
            formatted_last_checked = most_recent_check.strftime('%A, %B %d, %Y %I:%M:%S %p')
        else:
            formatted_last_checked = "Never Checked"
    else:
        formatted_last_checked = "Never Checked"

    # Fetch logs specific to the logged-in user
    cursor.execute(
        'SELECT * FROM log WHERE user_id = %s ORDER BY date_added DESC',
        (current_user.id,)
    )
    logs = cursor.fetchall()

    formatted_logs = [
        {
            'manga_title': log['manga_title'],
            'chapters_added': log['chapters_added'],
            'date_added': log['date_added'].strftime('%A, %B %d, %Y %I:%M %p')
        }
        for log in logs
    ]

    cursor.close()
    connection.close()
    return render_template('index.html', manga_list=manga_list, last_checked=formatted_last_checked, logs=formatted_logs)

# Add Manga Route
@app.route('/add', methods=['POST'])
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
            return redirect(url_for('index'))

        title, latest_chapter_title, chapter_count = scrape_manga_details(url)

        if title is None or latest_chapter_title is None or chapter_count is None:
            flash('Error: Could not retrieve manga details. Please try again with a valid URL.', 'error')
            cursor.close()
            connection.close()
            return redirect(url_for('index'))

        cursor.execute(
            'INSERT INTO manga (title, url, last_checked, chapter_count, latest_chapter_title, user_id) VALUES (%s, %s, %s, %s, %s, %s)',
            (title, url, datetime.now(), chapter_count, latest_chapter_title, current_user.id)
        )
        connection.commit()
        cursor.close()
        connection.close()
        flash('Manga added successfully!', 'success')
        return redirect(url_for('index'))

# Check for Updates Route
@app.route('/check_updates', methods=['POST'])
@login_required
def check_updates():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM manga WHERE user_id = %s', (current_user.id,))
    manga_list = cursor.fetchall()

    for manga in manga_list:
        url = manga['url']
        title, latest_chapter_title, chapter_count = scrape_manga_details(url)

        if title is not None and latest_chapter_title is not None and chapter_count is not None:
            previous_count = manga['chapter_count']
            new_chapters = max(0, chapter_count - previous_count)
            cursor.execute(
                'UPDATE manga SET latest_chapter_title = %s, chapter_count = %s, last_checked = %s, new_chapters_count = %s WHERE id = %s AND user_id = %s',
                (latest_chapter_title, chapter_count, datetime.now(), new_chapters, manga['id'], current_user.id)
            )
            # Insert a log entry for new chapters if they exist
            if new_chapters > 0:
                cursor.execute(
                    'INSERT INTO log (manga_title, chapters_added, date_added, user_id) VALUES (%s, %s, %s, %s)',
                    (title, new_chapters, datetime.now(), current_user.id)
                )

    connection.commit()
    cursor.close()
    connection.close()
    flash('Update check complete!', 'info')
    return redirect(url_for('index'))

# Delete Manga Route
@app.route('/delete/<int:id>')
@login_required
def delete_manga(id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('DELETE FROM manga WHERE id = %s AND user_id = %s', (id, current_user.id))
    connection.commit()
    cursor.close()
    connection.close()
    flash('Manga deleted successfully.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)