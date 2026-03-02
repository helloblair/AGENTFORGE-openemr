"""Load transplant reference data into OpenEMR's MySQL database.

This script:
1. Executes agent/sql/transplant_schema.sql to create the 3 tables
2. Loads agent/data/transplant_icd10_codes.csv into transplant_icd10_criteria
3. Loads agent/data/optn_transplant_criteria.json into transplant_organ_criteria

Usage:
    python3 agent/scripts/load_transplant_data.py

Environment variables (or .env file):
    MYSQL_HOST     — default: localhost
    MYSQL_PORT     — default: 3306
    MYSQL_USER     — default: openemr
    MYSQL_PASS     — default: openemr
    MYSQL_DATABASE — default: openemr
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

try:
    import mysql.connector
except ImportError:
    logger.error(
        "mysql-connector-python is required. Install with:\n"
        "  pip install mysql-connector-python"
    )
    sys.exit(1)

# Try to load .env for convenience
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_DIR = SCRIPT_DIR.parent
SQL_FILE = AGENT_DIR / "sql" / "transplant_schema.sql"
CSV_FILE = AGENT_DIR / "data" / "transplant_icd10_codes.csv"
JSON_FILE = AGENT_DIR / "data" / "optn_transplant_criteria.json"

# ── Database config ──────────────────────────────────────────────────────────


def _get_db_config() -> dict:
    """Build MySQL connection config from environment variables."""
    return {
        "host": os.environ.get("MYSQL_HOST", "localhost"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "openemr"),
        "password": os.environ.get("MYSQL_PASS", "openemr"),
        "database": os.environ.get("MYSQL_DATABASE", "openemr"),
    }


# ── Schema creation ──────────────────────────────────────────────────────────


def create_tables(cursor) -> None:
    """Execute the schema SQL file to create tables (idempotent)."""
    logger.info("Creating tables from %s ...", SQL_FILE)
    sql_text = SQL_FILE.read_text(encoding="utf-8")

    # Split on semicolons and execute each statement
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    for stmt in statements:
        # Skip comments-only blocks
        lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
        if not any(l.strip() for l in lines):
            continue
        cursor.execute(stmt)
    logger.info("Tables created (or already exist).")


# ── Load ICD-10 codes ────────────────────────────────────────────────────────


def load_icd10_codes(cursor) -> int:
    """Load transplant_icd10_codes.csv into transplant_icd10_criteria table.

    Uses INSERT IGNORE to skip duplicates on re-run.
    Returns the number of rows inserted.
    """
    logger.info("Loading ICD-10 codes from %s ...", CSV_FILE)

    if not CSV_FILE.exists():
        logger.error("CSV file not found: %s", CSV_FILE)
        logger.error("Run parse_icd10.py first to generate the data files.")
        return 0

    insert_sql = """
        INSERT IGNORE INTO transplant_icd10_criteria
            (icd10_code, short_description, long_description, is_billable,
             organ_system, criteria_type)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    count = 0
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch: list[tuple] = []
        for row in reader:
            is_billable = 1 if row["is_billable"].lower() in ("true", "1", "yes") else 0
            batch.append((
                row["code"],
                row["short_description"][:100],  # Truncate to VARCHAR(100)
                row["long_description"],
                is_billable,
                row["organ_system"],
                row["criteria_type"],
            ))

            # Batch insert every 500 rows
            if len(batch) >= 500:
                cursor.executemany(insert_sql, batch)
                count += len(batch)
                batch = []

        # Insert remaining rows
        if batch:
            cursor.executemany(insert_sql, batch)
            count += len(batch)

    logger.info("Loaded %d ICD-10 codes.", count)
    return count


# ── Load OPTN criteria ───────────────────────────────────────────────────────


def load_optn_criteria(cursor) -> int:
    """Load optn_transplant_criteria.json into transplant_organ_criteria table.

    Creates one row per organ type. Uses INSERT ... ON DUPLICATE KEY UPDATE
    for idempotency.
    Returns the number of rows upserted.
    """
    logger.info("Loading OPTN criteria from %s ...", JSON_FILE)

    if not JSON_FILE.exists():
        logger.error("JSON file not found: %s", JSON_FILE)
        return 0

    with open(JSON_FILE, encoding="utf-8") as f:
        criteria = json.load(f)

    source = criteria.get("source", "OPTN Policy")
    version = criteria.get("version", "unknown")
    organs = criteria.get("organs", {})

    upsert_sql = """
        INSERT INTO transplant_organ_criteria
            (organ_type, criteria_json, source, version)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            criteria_json = VALUES(criteria_json),
            source = VALUES(source),
            version = VALUES(version)
    """

    count = 0
    for organ_type, organ_criteria in organs.items():
        cursor.execute(upsert_sql, (
            organ_type,
            json.dumps(organ_criteria, ensure_ascii=False),
            source,
            version,
        ))
        count += 1

    logger.info("Loaded %d organ criteria records.", count)
    return count


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    config = _get_db_config()
    logger.info(
        "Connecting to MySQL at %s:%s/%s as %s ...",
        config["host"], config["port"], config["database"], config["user"],
    )

    try:
        conn = mysql.connector.connect(**config)
    except mysql.connector.Error as exc:
        logger.error("Failed to connect to MySQL: %s", exc)
        logger.error(
            "Make sure MySQL is running and credentials are set via env vars:\n"
            "  MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASS, MYSQL_DATABASE"
        )
        sys.exit(1)

    cursor = conn.cursor()

    try:
        create_tables(cursor)
        conn.commit()

        icd10_count = load_icd10_codes(cursor)
        conn.commit()

        optn_count = load_optn_criteria(cursor)
        conn.commit()

        # Verify
        cursor.execute("SELECT COUNT(*) FROM transplant_icd10_criteria")
        total_icd10 = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM transplant_organ_criteria")
        total_optn = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM transplant_screenings")
        total_screenings = cursor.fetchone()[0]

        logger.info("Verification:")
        logger.info("  transplant_icd10_criteria: %d rows", total_icd10)
        logger.info("  transplant_organ_criteria: %d rows", total_optn)
        logger.info("  transplant_screenings:     %d rows", total_screenings)
        logger.info("Done.")

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
