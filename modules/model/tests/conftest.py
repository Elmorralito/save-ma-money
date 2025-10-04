# papita-transactions-model/tests/conftest.py
"""Pytest configuration file.
"""

import sys
import os


# Add the parent directory of 'tests' (i.e., 'my_project') to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
