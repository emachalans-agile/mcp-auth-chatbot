import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "dbname": "chatbot_db",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def find_user_by_email(email: str):
    """Returns user dict if exists, else None."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, email, name, role FROM users WHERE email = %s", (email,))
            return cur.fetchone()