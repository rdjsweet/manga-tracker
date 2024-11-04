from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, EqualTo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from scraper import scrape_manga_details

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

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
    connection = sqlite3.connect('manga_tracker.sqlite3')
    connection.row_factory = sqlite3.Row  # Allows us to access columns by name
    return connection

@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    user = connection.execute('SELECT * FROM User WHERE id = ?', (user_id,)).fetchone()
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
            connection.execute(
                'INSERT INTO User (username, password_hash) VALUES (?, ?)',
                (username, hashed_password)
            )
            connection.commit()
            connection.close()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
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
        user = connection.execute('SELECT * FROM User WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['username'], user['password_hash'])
            login_user(user_obj)

            # Check if this is the user's first login
            if user['first_login']:
                # Add a welcome message to the log
                connection.execute(
                    'INSERT INTO Log (manga_title, chapters_added, date_added, user_id) VALUES (?, ?, ?, ?)',
                    ("Welcome to the MangaPill Chapter Tracker! All your chapter updates will be logged here, showing the title and date so you can easily track the latest releases.", 0, datetime.now(), user['id'])
                )

                # Set first_login to False after the first login
                connection.execute(
                    'UPDATE User SET first_login = 0 WHERE id = ?', (user['id'],)
                )

            connection.commit()
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

    # Fetch only manga that belongs to the logged-in user
    manga_list = connection.execute(
        'SELECT * FROM Manga WHERE user_id = ? ORDER BY title ASC', 
        (current_user.id,)
    ).fetchall()

    # Get the most recent check time from the database if available
    if manga_list:
        last_checked_values = [manga['last_checked'] for manga in manga_list if manga['last_checked']]
        if last_checked_values:
            most_recent_check = max(last_checked_values)
            formatted_last_checked = datetime.strptime(most_recent_check, '%Y-%m-%d %H:%M:%S.%f').strftime('%A, %B %d, %Y %I:%M:%S %p')
        else:
            formatted_last_checked = "Never Checked"
    else:
        formatted_last_checked = "Never Checked"

    # Fetch logs specific to the logged-in user
    logs = connection.execute(
        'SELECT * FROM Log WHERE user_id = ? ORDER BY date_added DESC', 
        (current_user.id,)
    ).fetchall()

    formatted_logs = [
        {
            'manga_title': log['manga_title'],
            'chapters_added': log['chapters_added'],
            'date_added': datetime.strptime(log['date_added'], '%Y-%m-%d %H:%M:%S.%f').strftime('%A, %B %d, %Y %I:%M %p')
        }
        for log in logs
    ]

    connection.close()
    return render_template('index.html', manga_list=manga_list, last_checked=formatted_last_checked, logs=formatted_logs)

# Add Manga Route
@app.route('/add', methods=['POST'])
@login_required
def add_manga():
    if request.method == 'POST':
        url = request.form['url']
        title, latest_chapter_title, chapter_count = scrape_manga_details(url)

        if title is None or latest_chapter_title is None or chapter_count is None:
            flash('Error: Could not retrieve manga details. Please try again with a valid URL.', 'error')
            return redirect(url_for('index'))

        connection = get_db_connection()
        connection.execute(
            'INSERT INTO Manga (title, url, last_checked, chapter_count, latest_chapter_title, user_id) VALUES (?, ?, ?, ?, ?, ?)',
            (title, url, datetime.now(), chapter_count, latest_chapter_title, current_user.id)
        )
        connection.commit()
        connection.close()
        flash('Manga added successfully!', 'success')
        return redirect(url_for('index'))

# Check for Updates Route
@app.route('/check_updates', methods=['POST'])
@login_required
def check_updates():
    connection = get_db_connection()
    manga_list = connection.execute('SELECT * FROM Manga WHERE user_id = ?', (current_user.id,)).fetchall()

    for manga in manga_list:
        url = manga['url']
        title, latest_chapter_title, chapter_count = scrape_manga_details(url)

        if title is not None and latest_chapter_title is not None and chapter_count is not None:
            previous_count = manga['chapter_count']
            new_chapters = max(0, chapter_count - previous_count)
            connection.execute(
                'UPDATE Manga SET latest_chapter_title = ?, chapter_count = ?, last_checked = ?, new_chapters_count = ? WHERE id = ? AND user_id = ?',
                (latest_chapter_title, chapter_count, datetime.now(), new_chapters, manga['id'], current_user.id)
            )
            # Insert a log entry for new chapters if they exist
            if new_chapters > 0:
                connection.execute(
                    'INSERT INTO Log (manga_title, chapters_added, date_added, user_id) VALUES (?, ?, ?, ?)',
                    (title, new_chapters, datetime.now(), current_user.id)
                )

    connection.commit()
    connection.close()
    flash('Update check complete!', 'info')
    return redirect(url_for('index'))

# Delete Manga Route
@app.route('/delete/<int:id>')
@login_required
def delete_manga(id):
    connection = get_db_connection()
    connection.execute('DELETE FROM Manga WHERE id = ? AND user_id = ?', (id, current_user.id))
    connection.commit()
    connection.close()
    flash('Manga deleted successfully.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)