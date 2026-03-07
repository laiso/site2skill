"""Tests for site2skill.url_filter – crawl-scope and query-key filtering."""

import unittest

from site2skill.url_filter import DEFAULT_EXCLUDED_QUERY_KEYS, is_url_allowed


class TestDefaultExcludedKeys(unittest.TestCase):
    """Verify the default set of excluded query keys."""

    def test_default_keys(self):
        self.assertEqual(DEFAULT_EXCLUDED_QUERY_KEYS, frozenset({"hl", "lang", "locale"}))


class TestQueryKeyFiltering(unittest.TestCase):
    """Query-parameter filtering per the test plan."""

    START = "https://developer.android.com/training/data-storage/room"

    def test_hl_query_rejected(self):
        """?hl=en is a localization-only param → rejected."""
        url = self.START + "?hl=en"
        self.assertFalse(is_url_allowed(self.START, url))

    def test_lang_query_rejected(self):
        """?lang=ja is a localization-only param → rejected."""
        url = self.START + "?lang=ja"
        self.assertFalse(is_url_allowed(self.START, url))

    def test_locale_query_rejected(self):
        """?locale=fr is a localization-only param → rejected."""
        url = self.START + "?locale=fr"
        self.assertFalse(is_url_allowed(self.START, url))

    def test_version_query_allowed(self):
        """?version=2 changes content → allowed."""
        url = self.START + "?version=2"
        self.assertTrue(is_url_allowed(self.START, url))

    def test_tab_query_allowed(self):
        """?tab=api changes content → allowed."""
        url = self.START + "?tab=api"
        self.assertTrue(is_url_allowed(self.START, url))

    def test_mixed_query_with_excluded_key_allowed(self):
        """?version=2&hl=en has a non-excluded key → allowed."""
        url = self.START + "?version=2&hl=en"
        self.assertTrue(is_url_allowed(self.START, url))

    def test_multiple_excluded_keys_rejected(self):
        """?hl=en&lang=ja – all keys are excluded → rejected."""
        url = self.START + "?hl=en&lang=ja"
        self.assertFalse(is_url_allowed(self.START, url))

    def test_no_query_allowed(self):
        """URL with no query params is allowed as before."""
        self.assertTrue(is_url_allowed(self.START, self.START))


class TestPathScope(unittest.TestCase):
    """Crawl boundary is restricted to the starting URL's subtree."""

    START = "https://developer.android.com/training/data-storage/room"

    def test_exact_start_url_allowed(self):
        self.assertTrue(is_url_allowed(self.START, self.START))

    def test_descendant_path_allowed(self):
        url = "https://developer.android.com/training/data-storage/room/accessing-data"
        self.assertTrue(is_url_allowed(self.START, url))

    def test_sibling_path_rejected(self):
        """A sibling page under data-storage but NOT under room → rejected."""
        url = "https://developer.android.com/training/data-storage/shared-preferences"
        self.assertFalse(is_url_allowed(self.START, url))

    def test_parent_path_rejected(self):
        url = "https://developer.android.com/training/data-storage"
        self.assertFalse(is_url_allowed(self.START, url))

    def test_different_section_rejected(self):
        url = "https://developer.android.com/guide/components"
        self.assertFalse(is_url_allowed(self.START, url))

    def test_different_host_rejected(self):
        url = "https://example.com/training/data-storage/room"
        self.assertFalse(is_url_allowed(self.START, url))

    def test_different_scheme_rejected(self):
        url = "http://developer.android.com/training/data-storage/room"
        self.assertFalse(is_url_allowed(self.START, url))

    def test_sibling_with_query_still_rejected(self):
        """Out-of-scope path is rejected even with valid query params."""
        url = "https://developer.android.com/training/data-storage/shared-preferences?version=2"
        self.assertFalse(is_url_allowed(self.START, url))


class TestCustomExcludedKeys(unittest.TestCase):
    """Future-proofing: callers can supply their own exclusion set."""

    START = "https://example.com/docs"

    def test_custom_key_rejected(self):
        url = self.START + "?utm_source=google"
        self.assertTrue(is_url_allowed(self.START, url))  # not excluded by default
        self.assertFalse(
            is_url_allowed(self.START, url, excluded_query_keys={"utm_source"})
        )

    def test_empty_exclusion_set_allows_all_queries(self):
        url = self.START + "?hl=en"
        self.assertTrue(
            is_url_allowed(self.START, url, excluded_query_keys=set())
        )


class TestTrailingSlashNormalization(unittest.TestCase):
    """URLs with / without trailing slashes should match equivalently."""

    def test_start_with_trailing_slash(self):
        start = "https://example.com/docs/"
        candidate = "https://example.com/docs/api"
        self.assertTrue(is_url_allowed(start, candidate))

    def test_candidate_with_trailing_slash(self):
        start = "https://example.com/docs"
        candidate = "https://example.com/docs/"
        self.assertTrue(is_url_allowed(start, candidate))

    def test_both_trailing_slashes(self):
        start = "https://example.com/docs/"
        candidate = "https://example.com/docs/"
        self.assertTrue(is_url_allowed(start, candidate))


if __name__ == "__main__":
    unittest.main()
