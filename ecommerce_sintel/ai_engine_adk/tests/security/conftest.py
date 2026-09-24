"""HARDENING F11: hace importable `eval.redteam` (ai_engine_adk/eval no viaja en la imagen: se monta con -v)."""
import sys
from pathlib import Path

ADK_DIR = str(Path(__file__).resolve().parents[2])
if ADK_DIR not in sys.path:
    sys.path.append(ADK_DIR)
