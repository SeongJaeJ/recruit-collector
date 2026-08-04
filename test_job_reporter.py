import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import job_reporter


class TechStackMatchingTests(unittest.TestCase):
    def test_finds_requested_frontend_stacks(self):
        text = "JavaScript TypeScript HTML5 React Next.js Vue Nuxt"
        self.assertEqual(
            job_reporter.find_tech_stacks(text),
            ["JavaScript", "TypeScript", "HTML", "React", "Next.js", "Vue", "Nuxt"],
        )

    def test_does_not_treat_ordinary_next_as_framework(self):
        self.assertNotIn("Next.js", job_reporter.find_tech_stacks("Read the next section"))

    def test_rejects_javascript_only_backend_role(self):
        self.assertFalse(
            job_reporter.is_frontend_stack_match(
                "Backend Engineer",
                "JavaScript 중 한 가지 이상에 능숙한 분",
                ["JavaScript"],
            )
        )

    def test_accepts_typescript_in_web_role(self):
        self.assertTrue(
            job_reporter.is_frontend_stack_match(
                "Web Engineer",
                "TypeScript 개발 경험",
                ["TypeScript"],
            )
        )

    def test_html_alone_needs_frontend_context(self):
        self.assertFalse(job_reporter.is_frontend_stack_match("교육 과정", "HTML 문서", ["HTML"]))
        self.assertTrue(job_reporter.is_frontend_stack_match("Web Developer", "HTML 문서", ["HTML"]))

    def test_rejects_unrelated_external_detail_url(self):
        self.assertFalse(
            job_reporter.is_allowed_detail_url(
                "https://www.doosanenerbility.com/kr/employment/recruitment",
                "http://www.c-hrd.net/",
            )
        )
        self.assertTrue(
            job_reporter.is_allowed_detail_url(
                "https://www.example.com/careers",
                "https://example.recruiter.co.kr/career/job/1",
            )
        )

    def test_extracts_jobposting_skills(self):
        html = """
        <script type="application/ld+json">
        {"@type":"JobPosting","title":"Software Engineer","skills":"React, TypeScript"}
        </script>
        """
        detail = job_reporter.extract_job_detail_text(html)
        self.assertEqual(job_reporter.find_tech_stacks(detail), ["TypeScript", "React"])

    @patch("job_reporter.fetch_url")
    def test_enriches_generic_role_from_detail_stack(self, fetch_url):
        fetch_url.return_value = (
            "<html><body><h1>Software Engineer</h1><p>프론트엔드 서비스 개발: React, TypeScript</p></body></html>",
            "text/html",
        )
        hit = job_reporter.JobHit(
            company="Hyundai Motor",
            title="Software Engineer",
            url="https://example.com/jobs/1",
            keyword="",
            category="기술스택 후보",
            source_url="https://example.com/jobs",
        )
        enriched = job_reporter.enrich_hit(hit)
        self.assertIsNotNone(enriched)
        self.assertEqual(enriched.category, "기술스택 일치")
        self.assertEqual(enriched.tech_stacks, ["TypeScript", "React"])

    def test_uses_korean_name_only_when_mapped(self):
        self.assertEqual(job_reporter.display_company_name("Hyundai Motor"), "현대자동차")
        self.assertEqual(job_reporter.display_company_name("Unknown Co"), "Unknown Co")

    def test_next_run_at_uses_today_before_schedule_time(self):
        now = datetime(2026, 8, 2, 9, 30, tzinfo=timezone(timedelta(hours=9)))
        self.assertEqual(job_reporter.next_run_at(now), datetime(2026, 8, 2, 10, 0, tzinfo=now.tzinfo))

    def test_next_run_at_uses_tomorrow_after_schedule_time(self):
        now = datetime(2026, 8, 2, 10, 1, tzinfo=timezone(timedelta(hours=9)))
        self.assertEqual(job_reporter.next_run_at(now), datetime(2026, 8, 3, 10, 0, tzinfo=now.tzinfo))

    @patch("job_reporter.now_kst")
    def test_classifies_a_future_date_range_as_open(self, now_kst):
        now_kst.return_value = datetime(2026, 8, 2, 12, 0, tzinfo=timezone(timedelta(hours=9)))
        status = job_reporter.classify_application_status("\uc811\uc218\uae30\uac04: 2026.08.01 ~ 2026.08.03")
        self.assertEqual(status, "\uc811\uc218\uc911 (\ub9c8\uac10 2026-08-03)")

    @patch("job_reporter.now_kst")
    def test_classifies_an_elapsed_deadline_as_closed(self, now_kst):
        now_kst.return_value = datetime(2026, 8, 2, 12, 0, tzinfo=timezone(timedelta(hours=9)))
        self.assertEqual(job_reporter.status_for_deadline("2026-08-01 18:00"), "\ub9c8\uac10 (2026-08-01 18:00 KST)")

    def test_limits_browser_fallback_to_known_hosts(self):
        self.assertTrue(job_reporter.browser_fallback_supported("https://team.daangn.com/jobs/1"))
        self.assertFalse(job_reporter.browser_fallback_supported("https://unrelated.example/jobs/1"))

    def test_recognizes_a_removed_job_page(self):
        self.assertTrue(job_reporter.is_closed_job_page("<html><body>\ud398\uc774\uc9c0\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc5b4\uc694</body></html>"))
        self.assertFalse(job_reporter.is_closed_job_page("<html><body>\uc811\uc218 \uc911\uc778 \uacf5\uace0</body></html>"))

    @patch("job_reporter.fetch_source_url")
    def test_discovers_a_linked_job_board_from_a_landing_page(self, fetch_source_url):
        landing_url = "https://jobs.example.com/"
        listing_url = "https://jobs.example.com/search/"
        fetch_source_url.side_effect = [
            ('<html><a href="/search/">\ucc44\uc6a9\uacf5\uace0 \ubaa8\uc544\ubcf4\uae30</a></html>', "text/html"),
            ('<html><a href="/job/front-end/1">Front-end Engineer \ucc44\uc6a9</a></html>', "text/html"),
        ]
        hits, statuses = job_reporter.scan_company({"name": "Example", "urls": [landing_url]})
        self.assertEqual([status.url for status in statuses], [landing_url, listing_url])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].title, "Front-end Engineer \ucc44\uc6a9")

    @patch("job_reporter.fetch_source_url")
    def test_follows_job_board_navigation_for_four_depths(self, fetch_source_url):
        root = "https://jobs.example.com/"
        pages = {
            root: '<a href="/level-1/">\ucc44\uc6a9\uacf5\uace0</a>',
            "https://jobs.example.com/level-1/": '<a href="/level-2/">\ucc44\uc6a9\uacf5\uace0</a>',
            "https://jobs.example.com/level-2/": '<a href="/level-3/">\ucc44\uc6a9\uacf5\uace0</a>',
            "https://jobs.example.com/level-3/": '<a href="/level-4/">\ucc44\uc6a9\uacf5\uace0</a>',
            "https://jobs.example.com/level-4/": '<a href="/job/front-end/1">Front-end Engineer \ucc44\uc6a9</a>',
        }
        fetch_source_url.side_effect = lambda url: (f"<html>{pages[url]}</html>", "text/html")
        hits, statuses = job_reporter.scan_company({"name": "Example", "urls": [root]})
        self.assertEqual(len(statuses), 5)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].url, "https://jobs.example.com/job/front-end/1")

    @patch("job_reporter.fetch_url_with_browser")
    @patch("job_reporter.fetch_url")
    def test_browser_detail_status_overrides_listing_status(self, fetch_url, fetch_url_with_browser):
        fetch_url.return_value = ("<html><body>Frontend Engineer</body></html>", "text/html")
        fetch_url_with_browser.return_value = (
            '<html><script>window.__DATA__={"deadline":"2099-08-03"}</script><body>Frontend Engineer</body></html>',
            "text/html; browser-rendered",
        )
        hit = job_reporter.JobHit(
            company="Daangn",
            title="Frontend Engineer",
            url="https://team.daangn.com/jobs/1",
            keyword="frontend",
            category="\uc9c1\uc811 \ud504\ub860\ud2b8\uc5d4\ub4dc",
            source_url="https://team.daangn.com/jobs",
            snippet="\ub9c8\uac10",
        )
        enriched = job_reporter.enrich_hit(hit)
        self.assertIsNotNone(enriched)
        self.assertEqual(enriched.deadline, "\uc811\uc218\uc911 (\ub9c8\uac10 2099-08-03)")
        fetch_url_with_browser.assert_called_once()


if __name__ == "__main__":
    unittest.main()
