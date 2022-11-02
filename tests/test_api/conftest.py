import pytest


# Global marker for all the tests; items represent all PyTest test
# objects inside the directory. -k marker is marked on test files on the same
# level and below of a conftest.py
def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker("-k")
