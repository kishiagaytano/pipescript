# api/index.py
# ── Vercel serverless entry point for the PipeScript backend ──────────────
#
# Vercel's Python runtime detects the module-level `app` (an ASGI application)
# and serves it. We reuse the existing FastAPI app from main.py unchanged and
# mount it under /api, so its routes become:
#
#     /api/run   /api/validate   /api/examples   /api/health
#
# vercel.json rewrites every /api/* request to this function.
import os
import sys

# The compiler package (pipescript/), main.py, and models.py live at the repo
# root — one level up from this file. Put that on the import path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI

from main import app as pipescript_api  # existing FastAPI app: /run, /validate, ...

app = FastAPI()
app.mount("/api", pipescript_api)
