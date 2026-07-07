"""Vercel serverless entry point.

Vercel's Python runtime looks for a WSGI `app` in this file. We reuse the
same Flask app defined in app.py at the project root, so local dev and
production run identical code.
"""
import os
import sys

# Ensure the project root (one level up) is importable for `app` and `validator`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402

# Vercel invokes this WSGI callable.
app = app
