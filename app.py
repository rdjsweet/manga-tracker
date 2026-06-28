from flask import Flask
from config import config
from flask_login import LoginManager
from views.auth import auth_bp
from views.manga import manga_bp
from views.halloween import halloween_bp
from models import User
from utils.db import db_cursor

app = Flask(__name__)
app.config.from_object(config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'


@login_manager.user_loader
def load_user(user_id):
    with db_cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
    if user:
        return User(user['id'], user['username'], user['password_hash'])
    return None

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(manga_bp)
app.register_blueprint(halloween_bp)

if __name__ == '__main__':
    app.run(debug=True)