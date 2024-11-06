from flask_sqlalchemy import SQLAlchemy
from config import Config

# Create an instance of SQLAlchemy
db = SQLAlchemy()

def init_db(app):
    # Load the configuration from the Config class
    app.config.from_object(Config)
    # Initialize SQLAlchemy with the Flask app
    db.init_app(app)