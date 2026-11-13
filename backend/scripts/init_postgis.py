"""
Auto-initialization script for PostgreSQL + PostGIS on Render or cloud hosting.
Runs before Django migrations to ensure the PostGIS extension is installed.
"""
import os
import sys
import time
from urllib.parse import urlparse


def ensure_postgis():
    print("[init_postgis] Checking PostgreSQL / PostGIS extension...")
    use_sqlite = os.environ.get("USE_SQLITE", "false").lower() in ("1", "true", "yes", "on")
    if use_sqlite:
        print("[init_postgis] USE_SQLITE is enabled. Skipping PostgreSQL PostGIS extension check.")
        return

    database_url = os.environ.get("DATABASE_URL")
    
    max_retries = 5
    retry_delay = 3
    last_exc = None

    for attempt in range(1, max_retries + 1):
        try:
            import psycopg2
            if database_url:
                clean_url = database_url
                if clean_url.startswith("postgres://"):
                    clean_url = clean_url.replace("postgres://", "postgresql://", 1)
                print(f"[init_postgis] Connecting via DATABASE_URL (attempt {attempt}/{max_retries})...")
                conn = psycopg2.connect(clean_url, connect_timeout=10)
            else:
                conn_params = {
                    "dbname": os.environ.get("POSTGRES_DB", "geoharmonize"),
                    "user": os.environ.get("POSTGRES_USER", "geoharmonize"),
                    "password": os.environ.get("POSTGRES_PASSWORD", "geoharmonize"),
                    "host": os.environ.get("POSTGRES_HOST", "db"),
                    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
                    "connect_timeout": 10,
                }
                print(f"[init_postgis] Connecting to {conn_params.get('host')}:{conn_params.get('port')}/{conn_params.get('dbname')} (attempt {attempt}/{max_retries})...")
                conn = psycopg2.connect(**conn_params)

            conn.autocommit = True
            with conn.cursor() as cur:
                print("[init_postgis] Ensuring postgis extension...")
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                cur.execute("SELECT PostGIS_Version();")
                ver = cur.fetchone()
                print(f"[init_postgis] PostGIS successfully verified: {ver[0] if ver else 'enabled'}")
            conn.close()
            return
        except Exception as exc:
            last_exc = exc
            print(f"[init_postgis] Connection attempt {attempt} failed: {exc}")
            if attempt < max_retries:
                time.sleep(retry_delay)

    print(f"[init_postgis] ERROR: PostGIS initialization failed after {max_retries} attempts: {last_exc}", file=sys.stderr)
    if database_url or os.environ.get("RENDER", "false").lower() in ("1", "true", "yes", "on"):
        raise SystemExit(1)
    print("[init_postgis] Local environment without PostgreSQL. Proceeding with caution...")


if __name__ == "__main__":
    ensure_postgis()
