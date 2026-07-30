# pytest configuration for km-poster-generator
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (full render with Playwright)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests requiring Playwright + Chromium"
    )
