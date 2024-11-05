import psycopg2
from psycopg2.extras import RealDictCursor
from config import config

def get_db_connection():
    db_url = config.DATABASE_URL
    if not db_url:
        raise Exception("DATABASE_URL environment variable not set")

    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
