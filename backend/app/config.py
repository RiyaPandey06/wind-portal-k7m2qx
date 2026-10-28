"""Central configuration. Everything is overridable by environment variable."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
STATIC_DIR = Path(os.getenv("STATIC_DIR", ROOT / "backend" / "static"))

ELEXON_BASE = "https://data.elexon.co.uk/bmrs/api/v1"

# Scope: purchase decisions made in January 2026 (decision date D-1, delivery day D).
DECISION_START = os.getenv("DECISION_START", "2026-01-01")
DECISION_END = os.getenv("DECISION_END", "2026-01-31")

# Day-ahead gate: forecasts published after this London-local time on D-1 are NOT
# usable. EPEX/N2EX day-ahead auctions close around 09:20/09:50 UK time; 09:00 is a
# deliberately conservative default (users can change it in the UI).
DEFAULT_CUTOFF = os.getenv("DEFAULT_CUTOFF", "09:00")

# Only forecasts with horizon (startTime - publishTime) <= this are stored.
MAX_HORIZON_H = int(os.getenv("MAX_HORIZON_H", "72"))
