"""Vercel serverless function entry point."""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

# Vercel expects the app to be named 'app' or 'handler'
handler = app
