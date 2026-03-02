"""Download and parse the ICD-10-CM FY2026 Code Descriptions dataset from CMS.

Filters to transplant-relevant diagnostic codes and outputs:
  - agent/data/transplant_icd10_codes.csv
  - agent/data/transplant_icd10_codes.json

Data source: CMS ICD-10-CM FY2026 Code Descriptions in Tabular Order
https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order.zip

Fixed-width format per line:
  Chars 1-5:   Sequential number
  Chars 6-13:  ICD-10-CM code (no dots, left-justified, space-padded)
  Char  14:    Header flag (0 = billable code, 1 = header/category)
  Chars 15+:   Short description (up to ~60 chars) then long description

Note: The exact column boundaries can vary slightly between CMS releases.
This script uses a robust parser that handles both fixed-width and
space-delimited layouts found in FY2025/FY2026 files.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

CMS_ZIP_URL = (
    "https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order.zip"
)
CDC_ZIP_URL = (
    "https://ftp.cdc.gov/pub/health_statistics/nchs/publications/"
    "ICD10CM/2026/icd10cm-Code%20Descriptions-2026.zip"
)

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DOWNLOAD_DIR = SCRIPT_DIR / "_downloads"

CSV_OUTPUT = DATA_DIR / "transplant_icd10_codes.csv"
JSON_OUTPUT = DATA_DIR / "transplant_icd10_codes.json"

# ── Transplant-relevant ICD-10 code filters ──────────────────────────────────
# Each entry maps a code prefix to (organ_system, criteria_type).
# ALL subcodes under the prefix are included.

TRANSPLANT_FILTERS: list[tuple[str, str, str]] = [
    # ── Kidney / Renal ──
    ("N18", "kidney", "qualifying_diagnosis"),
    ("N19", "kidney", "qualifying_diagnosis"),
    ("Z94.0", "kidney", "transplant_status"),
    ("Z99.2", "kidney", "screening"),
    ("T86.1", "kidney", "complication"),
    # ── Heart ──
    ("I50", "heart", "qualifying_diagnosis"),
    ("I25", "heart", "qualifying_diagnosis"),
    ("I42", "heart", "qualifying_diagnosis"),
    ("Z94.1", "heart", "transplant_status"),
    ("T86.2", "heart", "complication"),
    # ── Lung ──
    ("J43", "lung", "qualifying_diagnosis"),
    ("J44", "lung", "qualifying_diagnosis"),
    ("J84", "lung", "qualifying_diagnosis"),
    ("J96.1", "lung", "qualifying_diagnosis"),
    ("Z94.2", "lung", "transplant_status"),
    ("T86.81", "lung", "complication"),
    # ── Liver ──
    ("K70.4", "liver", "qualifying_diagnosis"),
    ("K72", "liver", "qualifying_diagnosis"),
    ("K74", "liver", "qualifying_diagnosis"),
    ("Z94.4", "liver", "transplant_status"),
    ("T86.4", "liver", "complication"),
    # ── General transplant ──
    ("Z94", "general", "transplant_status"),
    ("T86", "general", "complication"),
    ("Z76.82", "general", "screening"),
    # ── Contraindications ──
    ("F10", "general", "contraindication"),
    ("F11", "general", "contraindication"),
    ("F12", "general", "contraindication"),
    ("F13", "general", "contraindication"),
    ("F14", "general", "contraindication"),
    ("F15", "general", "contraindication"),
    ("F16", "general", "contraindication"),
    ("F17", "general", "contraindication"),
    ("F18", "general", "contraindication"),
    ("F19", "general", "contraindication"),
    ("C0", "general", "contraindication"),
    ("C1", "general", "contraindication"),
    ("C2", "general", "contraindication"),
    ("C3", "general", "contraindication"),
    ("C4", "general", "contraindication"),
    ("C5", "general", "contraindication"),
    ("C6", "general", "contraindication"),
    ("C7", "general", "contraindication"),
    ("C8", "general", "contraindication"),
    ("C9", "general", "contraindication"),
    ("E66", "general", "contraindication"),
    ("F20", "general", "contraindication"),
    ("F21", "general", "contraindication"),
    ("F22", "general", "contraindication"),
    ("F23", "general", "contraindication"),
    ("F24", "general", "contraindication"),
    ("F25", "general", "contraindication"),
    ("F26", "general", "contraindication"),
    ("F27", "general", "contraindication"),
    ("F28", "general", "contraindication"),
    ("F29", "general", "contraindication"),
]


def _add_dot(raw_code: str) -> str:
    """Insert a dot after the 3rd character of an ICD-10 code.

    Examples:
        N186  -> N18.6
        I5021 -> I50.21
        N18   -> N18     (3-char codes stay as-is)
        E669  -> E66.9
    """
    code = raw_code.strip()
    if len(code) <= 3:
        return code
    return code[:3] + "." + code[3:]


def _classify_code(dotted_code: str) -> tuple[str, str] | None:
    """Determine (organ_system, criteria_type) for a dotted ICD-10 code.

    Uses longest-prefix matching against TRANSPLANT_FILTERS.
    Returns None if the code is not transplant-relevant.

    When a code matches multiple filters (e.g. Z94.0 matches both the
    specific kidney entry and the general Z94 entry), the most specific
    (longest prefix) match wins.
    """
    best_match: tuple[str, str] | None = None
    best_len = 0

    # Strip dots for prefix comparison so "N18.6" matches prefix "N18"
    code_nodot = dotted_code.replace(".", "")

    for prefix, organ, criteria in TRANSPLANT_FILTERS:
        prefix_nodot = prefix.replace(".", "")
        if code_nodot.startswith(prefix_nodot) and len(prefix_nodot) > best_len:
            best_match = (organ, criteria)
            best_len = len(prefix_nodot)

    return best_match


# ── Download ─────────────────────────────────────────────────────────────────


def _download_zip(url: str, dest: Path) -> Path:
    """Download a ZIP file if not already cached."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        logger.info("Using cached download: %s", dest)
        return dest
    logger.info("Downloading %s ...", url)
    try:
        urlretrieve(url, dest)
    except Exception as exc:
        logger.warning("Primary URL failed (%s), trying CDC mirror ...", exc)
        urlretrieve(CDC_ZIP_URL, dest)
    logger.info("Saved to %s", dest)
    return dest


# ── Parse ────────────────────────────────────────────────────────────────────


def _find_descriptions_file(zf: zipfile.ZipFile) -> str:
    """Find the code descriptions text file inside the ZIP."""
    for name in zf.namelist():
        lower = name.lower()
        if lower.endswith(".txt") and "order" in lower:
            return name
    # Fallback: any .txt file
    for name in zf.namelist():
        if name.lower().endswith(".txt"):
            return name
    raise FileNotFoundError("No .txt file found in ZIP archive")


def _parse_line(line: str) -> dict | None:
    """Parse a single fixed-width line into a structured dict.

    Returns None for blank lines or unparseable content.
    """
    if len(line) < 15:
        return None

    # Sequential number: chars 0-4 (5 chars)
    # Code: chars 5-12 (8 chars, left-justified, space-padded)
    # Header flag: char 13 (0=billable, 1=header)
    # Descriptions: char 14+
    raw_code = line[5:13].strip()
    if not raw_code:
        return None

    header_flag = line[13:14].strip()
    is_billable = header_flag == "0"

    # The rest is descriptions — short then long, separated by variable spacing
    desc_part = line[14:].strip()

    # Try to split short/long descriptions
    # Short description is typically up to ~60 chars, followed by spaces, then long
    # In practice the boundary is around position 60-62 from the desc start
    short_desc = desc_part[:60].strip() if len(desc_part) > 60 else desc_part.strip()
    long_desc = desc_part[60:].strip() if len(desc_part) > 60 else ""

    # If long_desc is empty, use short_desc as long_desc too
    if not long_desc:
        long_desc = short_desc

    dotted_code = _add_dot(raw_code)

    return {
        "raw_code": raw_code,
        "code": dotted_code,
        "is_billable": is_billable,
        "short_description": short_desc,
        "long_description": long_desc,
    }


def parse_icd10_zip(zip_path: Path) -> list[dict]:
    """Parse the ICD-10-CM ZIP and return all transplant-relevant codes."""
    records: list[dict] = []
    seen_codes: set[str] = set()

    with zipfile.ZipFile(zip_path) as zf:
        txt_name = _find_descriptions_file(zf)
        logger.info("Parsing: %s", txt_name)

        with zf.open(txt_name) as f:
            # Try UTF-8 first, fall back to latin-1
            try:
                text = f.read().decode("utf-8")
            except UnicodeDecodeError:
                f.seek(0)
                text = f.read().decode("latin-1")

            for line in text.splitlines():
                parsed = _parse_line(line)
                if parsed is None:
                    continue

                classification = _classify_code(parsed["code"])
                if classification is None:
                    continue

                # Avoid duplicates from overlapping prefix matches
                if parsed["code"] in seen_codes:
                    continue
                seen_codes.add(parsed["code"])

                organ_system, criteria_type = classification
                records.append({
                    "code": parsed["code"],
                    "short_description": parsed["short_description"],
                    "long_description": parsed["long_description"],
                    "is_billable": parsed["is_billable"],
                    "organ_system": organ_system,
                    "criteria_type": criteria_type,
                })

    # Sort by code for deterministic output
    records.sort(key=lambda r: r["code"])
    return records


# ── Output ───────────────────────────────────────────────────────────────────


def write_csv(records: list[dict], path: Path) -> None:
    """Write records to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "code",
        "short_description",
        "long_description",
        "is_billable",
        "organ_system",
        "criteria_type",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    logger.info("Wrote %d records to %s", len(records), path)


def write_json(records: list[dict], path: Path) -> None:
    """Write records to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %d records to %s", len(records), path)


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    zip_dest = DOWNLOAD_DIR / "icd10cm-2026-code-descriptions.zip"

    # Step 1: Download
    zip_path = _download_zip(CMS_ZIP_URL, zip_dest)

    # Step 2: Parse & filter
    records = parse_icd10_zip(zip_path)
    logger.info("Found %d transplant-relevant ICD-10-CM codes", len(records))

    if not records:
        logger.error("No records found — check the ZIP file format")
        sys.exit(1)

    # Step 3: Output summary by category
    by_organ: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for r in records:
        by_organ[r["organ_system"]] = by_organ.get(r["organ_system"], 0) + 1
        by_type[r["criteria_type"]] = by_type.get(r["criteria_type"], 0) + 1

    logger.info("By organ system: %s", dict(sorted(by_organ.items())))
    logger.info("By criteria type: %s", dict(sorted(by_type.items())))

    # Step 4: Write outputs
    write_csv(records, CSV_OUTPUT)
    write_json(records, JSON_OUTPUT)

    # Step 5: Spot-check critical codes
    code_set = {r["code"] for r in records}
    spot_checks = ["N18.6", "I50.9", "K74.6", "J44.1", "F10.20", "C50.9", "E66.9", "Z94.0"]
    for check in spot_checks:
        status = "FOUND" if check in code_set else "MISSING"
        logger.info("  Spot-check %s: %s", check, status)

    logger.info("Done. Files written to %s", DATA_DIR)


if __name__ == "__main__":
    main()
