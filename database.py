import psycopg2
import pymysql
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL
import configparser
from pathlib import Path

_ini = configparser.ConfigParser()
_ini.read(Path(__file__).parent / "config.ini", encoding="utf-8")


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


def get_operator_names() -> dict:
    """MariaDB NTbl_User → {UserID: UserName} eşlemesi döndürür."""
    try:
        cfg = _ini["mariadb"]
        conn = pymysql.connect(
            host=cfg["host"], port=int(cfg["port"]),
            user=cfg["user"], password=cfg["password"],
            database=cfg["database"],
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT `{cfg['id_col']}`, `{cfg['name_col']}` FROM `{cfg['table']}`"
                )
                rows = cur.fetchall()
        return {r[cfg["id_col"]]: r[cfg["name_col"]] for r in rows}
    except Exception:
        return {}


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
