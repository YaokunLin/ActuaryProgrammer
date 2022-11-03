import pytest


def pytest_collection_modifyitems(items):
    # Apply a marker for all the tests; items represent all PyTest test objects at this level and below.
    # "all" marker is marked on test files
    # to run: `pytest -k all`
    for item in items:
        item.add_marker("all")
