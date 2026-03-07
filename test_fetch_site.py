import tempfile
import unittest
from unittest.mock import patch

from site2skill.fetch_site import build_crawl_constraints, fetch_site


class FakeProcess:
    def __init__(self):
        self.stdout = []
        self.returncode = 0

    def wait(self):
        return self.returncode


class TestFetchSite(unittest.TestCase):
    def test_build_crawl_constraints_for_exact_page(self):
        constraints = build_crawl_constraints(
            "https://developer.android.com/training/data-storage/room"
        )

        self.assertEqual(constraints.domain, "developer.android.com")
        self.assertEqual(constraints.include_directory, "/training/data-storage")
        self.assertEqual(
            constraints.path_description,
            "/training/data-storage/room and descendants",
        )
        self.assertIn(r"training/data\-storage/room", constraints.accept_regex)
        self.assertIn(r"[?&](hl|lang|locale)=", constraints.reject_regex)

    def test_build_crawl_constraints_for_directory(self):
        constraints = build_crawl_constraints("https://docs.astral.sh/uv/")

        self.assertEqual(constraints.domain, "docs.astral.sh")
        self.assertEqual(constraints.include_directory, "/uv/")
        self.assertEqual(constraints.path_description, "/uv/")
        self.assertEqual(
            constraints.accept_regex,
            r"^https://docs\.astral\.sh/uv/.*$",
        )

    @patch("site2skill.fetch_site.subprocess.Popen")
    @patch("site2skill.fetch_site.check_wget_installed", return_value=True)
    def test_fetch_site_applies_crawl_constraints(self, _mock_wget, mock_popen):
        mock_popen.return_value = FakeProcess()

        with tempfile.TemporaryDirectory() as temp_dir:
            fetch_site(
                "https://developer.android.com/training/data-storage/room",
                temp_dir,
            )

        cmd = mock_popen.call_args.args[0]

        self.assertIn("--domains=developer.android.com", cmd)
        self.assertIn("--include-directories=/training/data-storage", cmd)
        self.assertTrue(
            any(arg.startswith("--accept-regex=") for arg in cmd),
            "wget command should include an accept regex",
        )
        self.assertIn("--reject-regex=[?&](hl|lang|locale)=", cmd)
        self.assertEqual(cmd[-2:], ["--", "https://developer.android.com/training/data-storage/room"])


if __name__ == "__main__":
    unittest.main()
