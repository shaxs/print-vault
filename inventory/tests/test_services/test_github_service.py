"""
Tests for inventory/services/github_service.py

Covers the pure/stateless functions that require no external API calls,
no Django cache, and no network access:

- parse_github_url(): URL pattern matching and parsing
- get_cache_key(): Cache key normalization
- filter_printable_files(): File size/extension filtering
"""

import pytest
from inventory.services.github_service import (
    parse_github_url,
    get_cache_key,
    filter_printable_files,
    InvalidURLError,
    PRINTABLE_EXTENSIONS,
    FILE_SIZE_WARN_BYTES,
    FILE_SIZE_BLOCK_BYTES,
)


# ──────────────────────────────────────────────────────────────────────────────
# parse_github_url()
# ──────────────────────────────────────────────────────────────────────────────

class TestParseGitHubURL:
    """Tests for parse_github_url() URL parsing."""

    def test_parses_root_repo_url(self):
        result = parse_github_url("https://github.com/octocat/Hello-World")
        assert result["owner"] == "octocat"
        assert result["repo"] == "Hello-World"
        assert result["branch"] is None
        assert result["path"] == ""

    def test_parses_root_repo_with_trailing_slash(self):
        result = parse_github_url("https://github.com/octocat/Hello-World/")
        assert result["owner"] == "octocat"
        assert result["repo"] == "Hello-World"

    def test_parses_tree_url_with_branch_only(self):
        result = parse_github_url("https://github.com/octocat/Hello-World/tree/main")
        assert result["owner"] == "octocat"
        assert result["repo"] == "Hello-World"
        assert result["branch"] == "main"
        assert result["path"] == ""

    def test_parses_tree_url_with_branch_and_path(self):
        result = parse_github_url("https://github.com/octocat/Hello-World/tree/main/src/models")
        assert result["owner"] == "octocat"
        assert result["repo"] == "Hello-World"
        assert result["branch"] == "main"
        assert result["path"] == "src/models"

    def test_parses_http_not_just_https(self):
        result = parse_github_url("http://github.com/octocat/Hello-World")
        assert result["owner"] == "octocat"
        assert result["repo"] == "Hello-World"

    def test_decodes_url_encoded_path(self):
        result = parse_github_url(
            "https://github.com/octocat/Hello-World/tree/main/STL%20Files"
        )
        assert result["path"] == "STL Files"

    def test_raises_invalid_url_for_blob_url(self):
        with pytest.raises(InvalidURLError) as exc_info:
            parse_github_url("https://github.com/octocat/Hello-World/blob/main/file.stl")
        assert "directory" in str(exc_info.value).lower()

    def test_raises_invalid_url_for_non_github_url(self):
        with pytest.raises(InvalidURLError):
            parse_github_url("https://gitlab.com/octocat/Hello-World")

    def test_raises_invalid_url_for_bare_string(self):
        with pytest.raises(InvalidURLError):
            parse_github_url("not-a-url")

    def test_raises_invalid_url_for_github_com_only(self):
        with pytest.raises(InvalidURLError):
            parse_github_url("https://github.com/")

    def test_raises_invalid_url_for_missing_repo(self):
        with pytest.raises(InvalidURLError):
            parse_github_url("https://github.com/octocat")

    def test_preserves_mixed_case_owner_and_repo(self):
        result = parse_github_url("https://github.com/PrinterOwner/My-3D-Models")
        assert result["owner"] == "PrinterOwner"
        assert result["repo"] == "My-3D-Models"


# ──────────────────────────────────────────────────────────────────────────────
# get_cache_key()
# ──────────────────────────────────────────────────────────────────────────────

class TestGetCacheKey:
    """Tests for get_cache_key() normalization."""

    def test_returns_prefixed_key(self):
        key = get_cache_key("octocat", "hello-world", "main", "")
        assert key.startswith("github_tree:")

    def test_normalizes_to_lowercase(self):
        key1 = get_cache_key("OctoCat", "Hello-World", "Main", "")
        key2 = get_cache_key("octocat", "hello-world", "main", "")
        assert key1 == key2

    def test_strips_leading_slash_from_path(self):
        key1 = get_cache_key("a", "b", "main", "/models")
        key2 = get_cache_key("a", "b", "main", "models")
        assert key1 == key2

    def test_strips_trailing_slash_from_path(self):
        key1 = get_cache_key("a", "b", "main", "models/")
        key2 = get_cache_key("a", "b", "main", "models")
        assert key1 == key2

    def test_empty_path_produces_consistent_key(self):
        key = get_cache_key("octocat", "hello-world", "main", "")
        assert "octocat" in key
        assert "hello-world" in key
        assert "main" in key

    def test_different_branches_produce_different_keys(self):
        key1 = get_cache_key("a", "b", "main", "")
        key2 = get_cache_key("a", "b", "develop", "")
        assert key1 != key2

    def test_different_paths_produce_different_keys(self):
        key1 = get_cache_key("a", "b", "main", "models")
        key2 = get_cache_key("a", "b", "main", "stl")
        assert key1 != key2


# ──────────────────────────────────────────────────────────────────────────────
# filter_printable_files()
# ──────────────────────────────────────────────────────────────────────────────

class TestFilterPrintableFiles:
    """Tests for filter_printable_files() extension and size filtering."""

    def _make_file(self, path, size=1024):
        return {"path": path, "size": size}

    def test_returns_tuple_of_three_lists(self):
        result = filter_printable_files([])
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_empty_input_returns_empty_lists(self):
        normal, large, blocked = filter_printable_files([])
        assert normal == []
        assert large == []
        assert blocked == []

    def test_allows_stl_extension(self):
        files = [self._make_file("model.stl")]
        normal, large, blocked = filter_printable_files(files)
        assert len(normal) == 1

    def test_allows_3mf_extension(self):
        files = [self._make_file("model.3mf")]
        normal, large, blocked = filter_printable_files(files)
        assert len(normal) == 1

    def test_allows_all_printable_extensions(self):
        files = [self._make_file(f"model{ext}") for ext in PRINTABLE_EXTENSIONS]
        normal, large, blocked = filter_printable_files(files)
        assert len(normal) == len(PRINTABLE_EXTENSIONS)

    def test_excludes_non_printable_extension(self):
        files = [self._make_file("readme.txt"), self._make_file("notes.pdf")]
        normal, large, blocked = filter_printable_files(files)
        assert normal == []
        assert large == []
        assert blocked == []

    def test_case_insensitive_extension_matching(self):
        files = [self._make_file("MODEL.STL"), self._make_file("model.3MF")]
        normal, large, blocked = filter_printable_files(files)
        assert len(normal) == 2

    def test_small_file_goes_to_normal(self):
        files = [self._make_file("model.stl", size=1024)]  # 1 KB
        normal, large, blocked = filter_printable_files(files)
        assert len(normal) == 1
        assert large == []
        assert blocked == []

    def test_large_file_10mb_goes_to_large(self):
        files = [self._make_file("model.stl", size=FILE_SIZE_WARN_BYTES)]
        normal, large, blocked = filter_printable_files(files)
        assert len(large) == 1
        assert normal == []

    def test_blocked_file_100mb_goes_to_blocked(self):
        files = [self._make_file("model.stl", size=FILE_SIZE_BLOCK_BYTES)]
        normal, large, blocked = filter_printable_files(files)
        assert len(blocked) == 1
        assert normal == []

    def test_filters_by_base_path(self):
        files = [
            self._make_file("models/chair.stl"),
            self._make_file("other/table.stl"),
        ]
        normal, large, blocked = filter_printable_files(files, base_path="models")
        assert len(normal) == 1
        assert normal[0]["path"] == "models/chair.stl"

    def test_no_base_path_includes_all_matching(self):
        files = [
            self._make_file("a/model.stl"),
            self._make_file("b/model.3mf"),
        ]
        normal, large, blocked = filter_printable_files(files)
        assert len(normal) == 2

    def test_mixed_sizes_split_correctly(self):
        files = [
            self._make_file("small.stl", size=1024),
            self._make_file("large.stl", size=FILE_SIZE_WARN_BYTES + 1),
            self._make_file("huge.stl", size=FILE_SIZE_BLOCK_BYTES + 1),
        ]
        normal, large, blocked = filter_printable_files(files)
        assert len(normal) == 1
        assert len(large) == 1
        assert len(blocked) == 1
