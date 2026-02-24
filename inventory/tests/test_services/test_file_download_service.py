"""
Tests for inventory/services/file_download_service.py

Covers the two most testable units without actual network calls:

- FileDownloadService._format_bytes() – pure static method
- FileDownloadService.validate_url()  – SSRF-protection logic

validate_url() calls socket.getaddrinfo() to resolve hostnames, so all
tests that exercise IP-checking logic mock that call to keep the suite
fast, deterministic, and hermetic.
"""

import socket
from unittest import mock

import pytest

from inventory.services.file_download_service import FileDownloadService


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _getaddrinfo_for(ip_str):
    """
    Return a minimal socket.getaddrinfo response that resolves to ip_str.
    Shape is: list of (family, type, proto, canonname, sockaddr)
    """
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip_str, 0))]


# ──────────────────────────────────────────────────────────────────────────────
# _format_bytes()
# ──────────────────────────────────────────────────────────────────────────────

class TestFormatBytes:
    """Unit tests for FileDownloadService._format_bytes() static method."""

    def test_zero_bytes(self):
        assert FileDownloadService._format_bytes(0) == "0.00 B"

    def test_one_byte(self):
        assert FileDownloadService._format_bytes(1) == "1.00 B"

    def test_1023_bytes_stays_in_bytes(self):
        assert FileDownloadService._format_bytes(1023) == "1023.00 B"

    def test_1024_bytes_becomes_one_kb(self):
        assert FileDownloadService._format_bytes(1024) == "1.00 KB"

    def test_1536_bytes_is_1_5_kb(self):
        assert FileDownloadService._format_bytes(1536) == "1.50 KB"

    def test_one_megabyte(self):
        assert FileDownloadService._format_bytes(1024 ** 2) == "1.00 MB"

    def test_one_gigabyte(self):
        assert FileDownloadService._format_bytes(1024 ** 3) == "1.00 GB"

    def test_one_terabyte(self):
        assert FileDownloadService._format_bytes(1024 ** 4) == "1.00 TB"

    def test_one_petabyte(self):
        assert FileDownloadService._format_bytes(1024 ** 5) == "1.00 PB"

    def test_fractional_megabytes(self):
        result = FileDownloadService._format_bytes(int(2.5 * 1024 ** 2))
        assert result == "2.50 MB"

    def test_large_petabytes(self):
        # Value beyond TB threshold falls through to PB branch
        assert FileDownloadService._format_bytes(1024 ** 5 * 2) == "2.00 PB"


# ──────────────────────────────────────────────────────────────────────────────
# validate_url() – format and scheme validation (no socket calls needed)
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateUrlFormat:
    """Validation failures that are caught before hostname resolution."""

    def setup_method(self):
        self.service = FileDownloadService()

    def test_raises_for_empty_string(self):
        with pytest.raises(ValueError, match="Invalid URL format"):
            self.service.validate_url("")

    def test_raises_for_path_only(self):
        with pytest.raises(ValueError, match="Invalid URL format"):
            self.service.validate_url("/some/path/file.stl")

    def test_raises_for_no_netloc(self):
        with pytest.raises(ValueError, match="Invalid URL format"):
            self.service.validate_url("https://")

    def test_raises_for_ftp_scheme(self):
        with pytest.raises(ValueError, match="Only HTTP and HTTPS"):
            self.service.validate_url("ftp://example.com/file.stl")

    def test_raises_for_file_scheme(self):
        # file:// has no netloc so urlparse triggers the format check first
        with pytest.raises(ValueError, match="Invalid URL format"):
            self.service.validate_url("file:///etc/passwd")

    def test_raises_for_data_scheme(self):
        # data: has no netloc so urlparse triggers the format check first
        with pytest.raises(ValueError, match="Invalid URL format"):
            self.service.validate_url("data:text/plain,hello")

    def test_raises_for_javascript_scheme(self):
        # javascript: has no netloc so urlparse triggers the format check first
        with pytest.raises(ValueError, match="Invalid URL format"):
            self.service.validate_url("javascript:alert(1)")


# ──────────────────────────────────────────────────────────────────────────────
# validate_url() – blocked IP categories (socket mocked)
# ──────────────────────────────────────────────────────────────────────────────

SOCKET_PATH = "inventory.services.file_download_service.socket.getaddrinfo"


class TestValidateUrlBlockedLoopback:
    """Loopback addresses (127.0.0.0/8, ::1) must be blocked."""

    def setup_method(self):
        self.service = FileDownloadService()

    @mock.patch(SOCKET_PATH)
    def test_blocks_ipv4_loopback_via_hostname(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("127.0.0.1")
        with pytest.raises(ValueError, match="loopback"):
            self.service.validate_url("http://localhost/file.stl")

    @mock.patch(SOCKET_PATH)
    def test_blocks_127_0_0_1_direct(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("127.0.0.1")
        with pytest.raises(ValueError, match="loopback"):
            self.service.validate_url("http://127.0.0.1/file.stl")

    @mock.patch(SOCKET_PATH)
    def test_blocks_127_x_x_x_range(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("127.100.200.1")
        with pytest.raises(ValueError, match="loopback"):
            self.service.validate_url("http://127.100.200.1/file.stl")


class TestValidateUrlBlockedPrivate:
    """RFC-1918 private ranges must be blocked."""

    def setup_method(self):
        self.service = FileDownloadService()

    @mock.patch(SOCKET_PATH)
    def test_blocks_10_0_0_0_range(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("10.0.0.1")
        with pytest.raises(ValueError, match="private"):
            self.service.validate_url("http://internal.corp/file.stl")

    @mock.patch(SOCKET_PATH)
    def test_blocks_192_168_range(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("192.168.1.100")
        with pytest.raises(ValueError, match="private"):
            self.service.validate_url("https://router.local/file.stl")

    @mock.patch(SOCKET_PATH)
    def test_blocks_172_16_range(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("172.16.0.1")
        with pytest.raises(ValueError, match="private"):
            self.service.validate_url("http://intranet.local/file.stl")

    @mock.patch(SOCKET_PATH)
    def test_blocks_172_31_range(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("172.31.255.255")
        with pytest.raises(ValueError, match="private"):
            self.service.validate_url("http://vpn.internal/file.stl")


class TestValidateUrlBlockedLinkLocal:
    """Link-local (169.254.0.0/16) must be blocked (e.g. cloud metadata)."""

    def setup_method(self):
        self.service = FileDownloadService()

    @mock.patch(SOCKET_PATH)
    def test_blocks_aws_metadata_ip(self, mock_gai):
        # AWS Instance Metadata Service lives at 169.254.169.254
        # Python 3.14+ reports this as 'private' before 'link-local' — both block it
        mock_gai.return_value = _getaddrinfo_for("169.254.169.254")
        with pytest.raises(ValueError, match="private|link-local"):
            self.service.validate_url("http://169.254.169.254/latest/meta-data/")

    @mock.patch(SOCKET_PATH)
    def test_blocks_generic_link_local(self, mock_gai):
        # Same: Python 3.14+ may classify 169.254.x.x as private
        mock_gai.return_value = _getaddrinfo_for("169.254.0.1")
        with pytest.raises(ValueError, match="private|link-local"):
            self.service.validate_url("http://169.254.0.1/file.stl")


class TestValidateUrlBlockedMulticast:
    """Multicast addresses (224.0.0.0/4) must be blocked."""

    def setup_method(self):
        self.service = FileDownloadService()

    @mock.patch(SOCKET_PATH)
    def test_blocks_multicast_address(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("224.0.0.1")
        with pytest.raises(ValueError, match="reserved/multicast"):
            self.service.validate_url("http://224.0.0.1/file.stl")

    @mock.patch(SOCKET_PATH)
    def test_blocks_multicast_upper_range(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("239.255.255.255")
        with pytest.raises(ValueError, match="reserved/multicast"):
            self.service.validate_url("http://239.255.255.255/file.stl")


# ──────────────────────────────────────────────────────────────────────────────
# validate_url() – hostname resolution failures
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateUrlResolutionFailures:
    """Unresolvable hostnames must raise ValueError."""

    def setup_method(self):
        self.service = FileDownloadService()

    @mock.patch(SOCKET_PATH, side_effect=socket.gaierror("Name or service not known"))
    def test_raises_for_unresolvable_hostname(self, mock_gai):
        with pytest.raises(ValueError, match="Cannot resolve hostname"):
            self.service.validate_url("http://this-does-not-exist.invalid/file.stl")

    @mock.patch(SOCKET_PATH, side_effect=socket.error("Network error"))
    def test_raises_for_socket_error(self, mock_gai):
        with pytest.raises(ValueError, match="Cannot resolve hostname"):
            self.service.validate_url("http://unreachable.example/file.stl")


# ──────────────────────────────────────────────────────────────────────────────
# validate_url() – valid public URLs
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateUrlValidPublic:
    """Public URLs must be accepted and return True."""

    def setup_method(self):
        self.service = FileDownloadService()

    @mock.patch(SOCKET_PATH)
    def test_accepts_https_public_domain(self, mock_gai):
        # 93.184.216.34 is the real IP of example.com – publicly routable
        mock_gai.return_value = _getaddrinfo_for("93.184.216.34")
        result = self.service.validate_url("https://example.com/model.stl")
        assert result is True

    @mock.patch(SOCKET_PATH)
    def test_accepts_http_public_domain(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("93.184.216.34")
        result = self.service.validate_url("http://example.com/model.3mf")
        assert result is True

    @mock.patch(SOCKET_PATH)
    def test_accepts_github_raw_url(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("185.199.108.133")
        result = self.service.validate_url(
            "https://raw.githubusercontent.com/user/repo/main/model.stl"
        )
        assert result is True

    @mock.patch(SOCKET_PATH)
    def test_accepts_url_with_port(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("93.184.216.34")
        result = self.service.validate_url("https://example.com:8443/file.stl")
        assert result is True

    @mock.patch(SOCKET_PATH)
    def test_accepts_url_with_path_and_query(self, mock_gai):
        mock_gai.return_value = _getaddrinfo_for("93.184.216.34")
        result = self.service.validate_url(
            "https://cdn.example.com/files/model.stl?token=abc123"
        )
        assert result is True
