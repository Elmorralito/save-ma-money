# papita-transactions-api/tests/conftest.py
"""Pytest configuration file."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

os.environ.setdefault("JWT_SECRET_KEY", "ci-test-jwt-secret-key-min-32chars-x")
