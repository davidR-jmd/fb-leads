"""Tests for LinkedIn browser service (TDD)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.linkedin.browser import LinkedInBrowser
from app.linkedin.schemas import LinkedInStatus


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test."""
    LinkedInBrowser.reset_instance()
    yield
    LinkedInBrowser.reset_instance()


class TestLinkedInBrowserSingleton:
    """Test singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """Should return the same instance."""
        browser1 = LinkedInBrowser(profile_path="./test-profile")
        browser2 = LinkedInBrowser(profile_path="./other-profile")

        assert browser1 is browser2

    def test_singleton_preserves_profile_path(self):
        """First profile_path should be preserved."""
        browser1 = LinkedInBrowser(profile_path="./first-profile")
        browser2 = LinkedInBrowser(profile_path="./second-profile")

        assert browser1._profile_path == "./first-profile"
        assert browser2._profile_path == "./first-profile"

    def test_reset_instance_creates_new_instance(self):
        """Reset should allow creating a new instance."""
        browser1 = LinkedInBrowser(profile_path="./test-profile")
        LinkedInBrowser.reset_instance()
        browser2 = LinkedInBrowser(profile_path="./new-profile")

        assert browser1 is not browser2
        assert browser2._profile_path == "./new-profile"


class TestLinkedInBrowser:
    """Test LinkedIn browser service logic."""

    def test_is_running_returns_false_initially(self):
        """Browser should not be running initially."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        assert browser.is_running() is False

    def test_is_busy_returns_false_initially(self):
        """Browser should not be busy initially."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        assert browser.is_busy() is False

    def test_set_busy_changes_state(self):
        """Should be able to set busy state."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        browser.set_busy(True)
        assert browser.is_busy() is True

        browser.set_busy(False)
        assert browser.is_busy() is False


class TestLinkedInBrowserURLDetection:
    """Test URL detection logic for login flow."""

    def test_detect_login_success(self):
        """Should detect successful login from feed URL."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        assert browser._is_feed_url("https://www.linkedin.com/feed/") is True
        assert browser._is_feed_url("https://www.linkedin.com/feed") is True
        assert browser._is_feed_url("https://linkedin.com/feed/") is True

    def test_detect_login_page(self):
        """Should detect login page."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        assert browser._is_login_url("https://www.linkedin.com/login") is True
        assert browser._is_login_url("https://www.linkedin.com/uas/login") is True

    def test_detect_challenge_page(self):
        """Should detect challenge/verification page."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        assert browser._is_challenge_url("https://www.linkedin.com/checkpoint/challenge/123") is True
        assert browser._is_challenge_url("https://www.linkedin.com/checkpoint/lg/login-submit") is True

    def test_feed_url_not_login(self):
        """Feed URL should not be detected as login."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        assert browser._is_login_url("https://www.linkedin.com/feed/") is False


class TestLinkedInBrowserContactParsing:
    """Test contact parsing from search results."""

    def test_parse_contact_data(self):
        """Should parse contact data correctly."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        raw_data = {
            "name": "  John Doe  ",
            "title": "Senior Developer at TechCorp",
            "location": "Paris, France",
            "profile_url": "https://www.linkedin.com/in/johndoe/",
        }

        contact = browser._parse_contact(raw_data)

        assert contact.name == "John Doe"
        assert contact.title == "Senior Developer at TechCorp"
        assert contact.location == "Paris, France"
        assert contact.profile_url == "https://www.linkedin.com/in/johndoe/"

    def test_parse_contact_with_missing_fields(self):
        """Should handle missing fields."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        raw_data = {
            "name": "Jane Doe",
        }

        contact = browser._parse_contact(raw_data)

        assert contact.name == "Jane Doe"
        assert contact.title is None
        assert contact.location is None
        assert contact.profile_url is None

    def test_parse_contact_extracts_company(self):
        """Should extract company from title if present."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        raw_data = {
            "name": "John Doe",
            "title": "Developer",
            "company": "Acme Inc",
        }

        contact = browser._parse_contact(raw_data)

        assert contact.company == "Acme Inc"

    def test_parse_contact_with_empty_values(self):
        """Should handle empty string values."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        raw_data = {
            "name": "",
            "title": "",
            "location": "",
        }

        contact = browser._parse_contact(raw_data)

        assert contact.name is None
        assert contact.title is None
        assert contact.location is None


class TestLinkedInBrowserHumanBehavior:
    """Test human-like behavior settings."""

    def test_random_delay_within_bounds(self):
        """Random delay should be within specified bounds."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        for _ in range(100):
            delay = browser._get_random_delay(min_ms=1000, max_ms=2000)
            assert 1000 <= delay <= 2000

    def test_random_delay_default_values(self):
        """Default delay should be reasonable."""
        browser = LinkedInBrowser(profile_path="./test-profile")

        delay = browser._get_random_delay()
        assert 2000 <= delay <= 5000  # Default 2-5 seconds
