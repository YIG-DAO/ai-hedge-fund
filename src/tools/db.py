import os
import psycopg2
from dotenv import load_dotenv
from typing import List
from contextlib import contextmanager

load_dotenv()

@contextmanager
def get_db_connection():
    """Create a database connection context manager."""
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )
    try:
        yield conn
    finally:
        conn.close()

def get_subscriber_emails() -> List[str]:
    """Fetch verified subscriber emails from the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            subscriber_query = os.getenv('SUBSCRIBER_QUERY')
            if not subscriber_query:
                raise ValueError("SUBSCRIBER_QUERY environment variable is not set")
            
            cur.execute(subscriber_query)
            return [row[0] for row in cur.fetchall()]
