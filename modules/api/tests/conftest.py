"""Pytest configuration for papita-transactions-api."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://papita:changeme@localhost:5432/papita_transactions")
