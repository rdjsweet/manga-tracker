from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # Single instance of SQLAlchemy to be shared across the entire app

from .user import User
from .manga import Manga
from .log import Log
