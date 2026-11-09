"""
Auto-initialization script for PostgreSQL + PostGIS on Render or cloud hosting.
Runs before Django migrations to ensure the PostGIS extension is installed.
"""
import os
import sys
from urllib.parse import urlparse

def ensure_postgis():
    print("[init_postgis] Checking PostgreSQL / PostGIS extension...")
    database_url = os.environ.get("DATABASE_URL")
    
    conn_params = {}
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        parsed = urlparse(database_url)
        conn_params = {
            "dbname": parsed.path.lstrip("/"),
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "connect_timeout": 10,
        }
    else:
        conn_params = {
            "dbname": os.environ.get("POSTGRES_DB", "geoharmonize"),
            "user": os.environ.get("POSTGRES_USER", "geoharmonize"),
            "password": os.environ.get("POSTGRES_PASSWORD", "geoharmonize"),
            "host": os.environ.get("POSTGRES_HOST", "db"),
            "port": int(os.environ.get("POSTGRES_PORT", "5432")),
            "connect_timeout": 10,
        }

    try:
        import psycopg2
        print(f"[init_postgis] Connecting to {conn_params.get('host')}:{conn_params.get('port')}/{conn_params.get('dbname')}...")
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        with conn.cursor() as cur:
            print("[init_postgis] Ensuring postgis extension...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            cur.execute("SELECT PostGIS_Version();")
            ver = cur.fetchone()
            print(f"[init_postgis] PostGIS successfully verified: {ver[0] if ver else 'enabled'}")
        conn.close()
    except Exception as exc:
        print(f"[init_postgis] Notice: PostGIS initialization encountered: {exc}")
        print("[init_postgis] Proceeding to Django migrations...")

if __name__ == "__main__":
    ensure_postgis()
