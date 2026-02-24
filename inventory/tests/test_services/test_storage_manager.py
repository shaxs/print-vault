"""
Tests for inventory/services/storage_manager.py

Covers the static/pure methods that require no filesystem access
and no Django settings:

- StorageManager.sanitize_filename(): Filename safety sanitization
- StorageManager._format_bytes(): Human-readable byte formatting
"""

import pytest
from inventory.services.storage_manager import StorageManager


# ──────────────────────────────────────────────────────────────────────────────
# StorageManager.sanitize_filename()
# ──────────────────────────────────────────────────────────────────────────────

class TestSanitizeFilename:
    """Tests for sanitize_filename() static method."""

    def test_clean_filename_unchanged(self):
        assert StorageManager.sanitize_filename("model.stl") == "model.stl"

    def test_replaces_backslash(self):
        result = StorageManager.sanitize_filename("my\\file.stl")
        assert "\\" not in result
        assert "_" in result

    def test_replaces_forward_slash(self):
        result = StorageManager.sanitize_filename("path/to/file.stl")
        assert "/" not in result

    def test_replaces_colon(self):
        result = StorageManager.sanitize_filename("C:file.stl")
        assert ":" not in result

    def test_replaces_angle_brackets(self):
        result = StorageManager.sanitize_filename("<file>.stl")
        assert "<" not in result
        assert ">" not in result

    def test_replaces_quotes(self):
        result = StorageManager.sanitize_filename('"file".stl')
        assert '"' not in result

    def test_replaces_pipe(self):
        result = StorageManager.sanitize_filename("file|name.stl")
        assert "|" not in result

    def test_replaces_question_mark(self):
        result = StorageManager.sanitize_filename("what?.stl")
        assert "?" not in result

    def test_replaces_asterisk(self):
        result = StorageManager.sanitize_filename("file*.stl")
        assert "*" not in result

    def test_strips_leading_dot(self):
        result = StorageManager.sanitize_filename(".hidden.stl")
        assert not result.startswith(".")

    def test_strips_trailing_spaces(self):
        result = StorageManager.sanitize_filename("file.stl   ")
        assert result == "file.stl"

    def test_returns_unnamed_file_for_empty_string(self):
        result = StorageManager.sanitize_filename("")
        assert result == "unnamed_file"

    def test_returns_unnamed_file_for_only_dots(self):
        result = StorageManager.sanitize_filename("...")
        assert result == "unnamed_file"

    def test_truncates_long_filename_preserving_extension(self):
        long_name = "a" * 300 + ".stl"
        result = StorageManager.sanitize_filename(long_name, max_length=255)
        assert len(result) <= 255
        assert result.endswith(".stl")

    def test_short_filename_not_truncated(self):
        result = StorageManager.sanitize_filename("short.stl", max_length=255)
        assert result == "short.stl"

    def test_filename_with_spaces_preserved(self):
        # Spaces are allowed in filenames — only dots and spaces at EDGES are stripped
        result = StorageManager.sanitize_filename("my model.stl")
        assert "my model.stl" == result

    def test_custom_max_length(self):
        long_name = "a" * 100 + ".stl"
        result = StorageManager.sanitize_filename(long_name, max_length=20)
        assert len(result) <= 20
        assert result.endswith(".stl")


# ──────────────────────────────────────────────────────────────────────────────
# StorageManager._format_bytes()
# ──────────────────────────────────────────────────────────────────────────────

class TestFormatBytes:
    """Tests for _format_bytes() static method."""

    def test_zero_bytes(self):
        result = StorageManager._format_bytes(0)
        assert result == "0.00 B"

    def test_bytes_under_1kb(self):
        result = StorageManager._format_bytes(512)
        assert "B" in result
        assert "KB" not in result

    def test_exactly_1kb(self):
        result = StorageManager._format_bytes(1024)
        assert "KB" in result

    def test_1mb(self):
        result = StorageManager._format_bytes(1024 * 1024)
        assert "MB" in result

    def test_1gb(self):
        result = StorageManager._format_bytes(1024 * 1024 * 1024)
        assert "GB" in result

    def test_1tb(self):
        result = StorageManager._format_bytes(1024 ** 4)
        assert "TB" in result

    def test_returns_string(self):
        assert isinstance(StorageManager._format_bytes(1000), str)

    def test_includes_two_decimal_places(self):
        result = StorageManager._format_bytes(1500)
        # 1500 B = 1.46 KB
        assert "." in result
        decimal_part = result.split(".")[1].split()[0]
        assert len(decimal_part) == 2

    def test_1_5_kb(self):
        result = StorageManager._format_bytes(1536)  # 1.5 KB
        assert "1.50 KB" == result

    def test_2_5_mb(self):
        result = StorageManager._format_bytes(int(2.5 * 1024 * 1024))
        assert "MB" in result
        assert result.startswith("2.50")
