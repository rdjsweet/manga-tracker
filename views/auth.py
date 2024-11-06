from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Log
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# User Registration Route
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        # Insert new user into the database
        try:
            new_user = User(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except:
            db.session.rollback()
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('auth.register'))

    return render_template('register.html')

# User Login Route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)

            # Check if this is the user's first login
            if user.first_login:
                with db.session.begin(subtransactions=True):
                    # Add a welcome message to the log
                    welcome_log = Log(
                        manga_title="Welcome to the MangaPill Chapter Tracker! All your chapter updates will be logged here, showing the title and date so you can easily track the latest releases.",
                        chapters_added=0,
                        date_added=datetime.now(),
                        user_id=user.id
                    )
                    db.session.add(welcome_log)

                    # Set first_login to False after the first login
                    user.first_login = False

                db.session.commit()

            flash('Login successful! Welcome back.', 'success')
            return redirect(url_for('manga.index'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
            return redirect(url_for('auth.login'))

    return render_template('login.html')

# User Logout Route
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
