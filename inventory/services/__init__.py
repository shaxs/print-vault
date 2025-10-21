"""
Services package for inventory app.
Contains business logic separated from views.
"""
from .github_service import crawl_github_repository

__all__ = ['crawl_github_repository']
