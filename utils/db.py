import psycopg2
from psycopg2.extras import RealDictCursor
from config import config
from contextlib import contextmanager


def get_db_connection():
    db_url = config.DATABASE_URL
    if not db_url:
        raise Exception("DATABASE_URL environment variable not set")

    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


@contextmanager
def db_cursor():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
