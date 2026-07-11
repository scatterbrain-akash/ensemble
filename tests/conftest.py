import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Prevent local .env from affecting tests and ensure deterministic behavior.
os.environ["DISABLE_DOTENV"] = "1"
for key in ("OPENAI_API_KEY", "GROQ_API_KEY", "AI_STUDIO_API_KEY"):
    os.environ.pop(key, None)

CACHE_FILE = ROOT / "cache" / "cache_store.json"
if CACHE_FILE.exists():
    CACHE_FILE.unlink()
