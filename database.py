import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL


def run_query(sql: str, params=None) -> list[dict]:
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def run_execute(sql: str, params=None) -> None:
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def run_transaction(statements: list) -> None:
    """Birden fazla (sql, params) ifadesini tek transaction'da çalıştırır."""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for sql, params in statements:
                cur.execute(sql, params)


def init_db() -> None:
    run_execute("""
        CREATE TABLE IF NOT EXISTS t_viewer_node (
            id              SERIAL PRIMARY KEY,
            viewer_name     VARCHAR(100) NOT NULL,
            node_id         VARCHAR(100) NOT NULL,
            management_code VARCHAR(100),
            name            VARCHAR(200),
            created_at      TIMESTAMP DEFAULT NOW()
        )
    """)
