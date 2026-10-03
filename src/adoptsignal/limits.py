"""Data limits: none when the app runs on your own computer; hard caps only in a public demo (``SIGNAL_PUBLIC=1``).

Signal suite contract (Signal Hub ``docs/APP_CONTRACT.md`` § 9): run locally — standalone, a local Signal Hub or an
internal company deployment — Adopt Signal imposes no limit on file size, rows, cells or periods of history; the
computer's memory is the limit, and running out of memory is reported as a plain message. A public demo server sets
``SIGNAL_PUBLIC=1`` (Signal Hub's public Docker image does), and then the caps below protect the shared server.
Every cap lives in this module, and the environment is read at call time.
"""

from __future__ import annotations

import os

from .errors import DataProblem

DEMO_MAX_UPLOAD_MB = 50
DEMO_MAX_UNCOMPRESSED_EXCEL_MB = 400
DEMO_MAX_TABLE_ROWS = 1_000_000
DEMO_MAX_TOTAL_CELLS = 10_000_000
DEMO_MAX_HISTORY_PERIODS = 400
DEMO_NOTE = "This is a limit of the public demo; the downloaded app has no built-in limit."
OUT_OF_MEMORY = (
    "There is not enough memory on this computer for this file or step. Close other programs, keep only the "
    "period and adoption columns, or aggregate the file before upload."
)


def public_demo() -> bool:
    """True on a public demo server (``SIGNAL_PUBLIC=1``); independent of Signal Hub mode (``SIGNAL_HUB``)."""
    return os.environ.get("SIGNAL_PUBLIC") == "1"


def check_upload_bytes(size: int) -> None:
    if public_demo() and size > DEMO_MAX_UPLOAD_MB * 1024 * 1024:
        raise DataProblem(f"Uploads are limited to {DEMO_MAX_UPLOAD_MB} MB. {DEMO_NOTE}")


def check_workbook_expansion(uncompressed_bytes: int) -> None:
    if public_demo() and uncompressed_bytes > DEMO_MAX_UNCOMPRESSED_EXCEL_MB * 1024 * 1024:
        raise DataProblem(
            f"This workbook expands beyond {DEMO_MAX_UNCOMPRESSED_EXCEL_MB} MB. Keep only the sheets and columns "
            f"needed. {DEMO_NOTE}"
        )


def check_table(rows: int, cells: int, name: str = "table") -> None:
    """Rows of one table and cells read so far (all tables of the file); called while reading, so it stops early."""
    if not public_demo():
        return
    if rows > DEMO_MAX_TABLE_ROWS:
        raise DataProblem(f"The {name} has more than {DEMO_MAX_TABLE_ROWS:,} rows. {DEMO_NOTE}")
    if cells > DEMO_MAX_TOTAL_CELLS:
        raise DataProblem(f"The file has more than {DEMO_MAX_TOTAL_CELLS:,} cells. {DEMO_NOTE}")


def check_history_periods(periods: int) -> None:
    if public_demo() and periods > DEMO_MAX_HISTORY_PERIODS:
        raise DataProblem(
            f"The history has {periods:,} periods; the demo fits up to {DEMO_MAX_HISTORY_PERIODS}. Group dates by "
            f"week, month, quarter or year. {DEMO_NOTE}"
        )
