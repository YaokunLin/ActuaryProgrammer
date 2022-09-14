import logging


def enable_orm_query_logging():
    """
    HEREBEDRAGONS: This causes a tremendous slowdown and logs potentially sensitive information.
    This should be used only for temporary debugging.
    """
    log = logging.getLogger("django.db.backends")
    log.setLevel(logging.DEBUG)
    log.addHandler(logging.StreamHandler())
