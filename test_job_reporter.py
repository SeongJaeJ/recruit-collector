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


if __name__ == "__main__":
    unittest.main()
