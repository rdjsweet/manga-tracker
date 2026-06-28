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