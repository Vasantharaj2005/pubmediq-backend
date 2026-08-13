"""
PubMedIQ — Integration Test Configuration

Integration tests verify interactions between 2+ modules.
They use the in-memory fallback path (no real Redis/PostgreSQL needed).
"""
from __future__ import annotations

import pytest
