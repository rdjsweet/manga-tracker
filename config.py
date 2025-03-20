import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY')
    DATABASE_URL = os.getenv('DATABASE_URL')
    REMEMBER_COOKIE_DURATION = timedelta(days=30)

config = Config()
