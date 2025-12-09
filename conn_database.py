import os
import configparser
import mysql.connector
from mysql.connector import Error


def parse_bool(val: str, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def load_db_config(config_path: str = "config.ini") -> dict:
    """
    Load DB config from config.ini, allowing environment overrides.
    Put DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME etc. in config.ini or env vars.
    """
    parser = configparser.ConfigParser()
    parser.read(config_path)
    cfg = parser["database"]

    host = os.getenv("DB_HOST", cfg.get("host", ""))
    host = host.strip().strip("\"'")  # remove accidental quotes

    return {
        "host": host,
        "port": int(os.getenv("DB_PORT", cfg.get("port", fallback="3306"))),
        "user": os.getenv("DB_USER", cfg.get("user")),
        "password": os.getenv("DB_PASSWORD", cfg.get("password")),
        "database": os.getenv("DB_NAME", cfg.get("database")),
        "charset": cfg.get("charset", "utf8mb4"),
        "connect_timeout": int(cfg.get("connect_timeout", 10)),
        "autocommit": parse_bool(cfg.get("autocommit"), True),
    }

def test_connection():
    config = load_db_config()
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION(), NOW()")
        version, now = cursor.fetchone()
        print(f"Connected. MySQL version: {version}, server time: {now}")
    except Error as e:
        print(f"Connection failed: {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    test_connection()
