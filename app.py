from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user, login_required
from config import Config
from models import db, User  # Import only db initially
from views.auth import auth_bp
from views.manga import manga_bp

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database with the app
db.init_app(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import models AFTER db.init_app(app)
from models import User, Manga, Log

@login_manager.user_loader
def load_user(user_id):
    # Ensure user model is queried after db is initialized
    with app.app_context():
        return User.query.get(int(user_id))
    
# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(manga_bp, url_prefix='/manga')

# Conditional redirect from "/" if not logged in
@app.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    else:
        return redirect(url_for('manga.index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This creates tables if they don't exist.
    app.run(debug=True)