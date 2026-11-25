"""TDD specification tests for the Knot Gemini CLI extension repository."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EM_DASH = "\u2014"

REQUIRED_URLS = (
    "https://connectknot.com",
    "https://connectknot.com/enterprise-brain",
    "https://connectknot.com/whitepaper",
    "https://connectknot.com/quickstart",
    "https://connectknot.com/llms-full.txt",
)

COMMAND_TOOL_REQUIREMENTS = {
    "commands/knot/recover.toml": ("get_context_recovery", "get_relevant_context"),
    "commands/knot/supersede.toml": (
        "get_relevant_context",
        "propose_context",
        "supersedes_context_id",
    ),
    "commands/knot/handoff.toml": ("create_handoff", "check_pending_handoffs"),
}


class TestGeminiExtension(unittest.TestCase):
    """Validates manifest, context docs, slash commands, README, license, and hygiene."""

    def test_manifest_valid(self) -> None:
        manifest_path = REPO_ROOT / "gemini-extension.json"
        self.assertTrue(manifest_path.is_file(), "gemini-extension.json must exist")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("name"), "knot")
        self.assertEqual(data.get("version"), "1.0.0")
        self.assertEqual(data.get("contextFileName"), "GEMINI.md")

        description = data.get("description")
        self.assertIsInstance(description, str)
        self.assertTrue(10 <= len(description.strip()) <= 160)
        self.assertNotIn(EM_DASH, description)

        mcp_servers = data.get("mcpServers")
        self.assertIsInstance(mcp_servers, dict)
        self.assertIn("knot", mcp_servers)

        knot_server = mcp_servers["knot"]
        self.assertIsInstance(knot_server, dict)
        self.assertEqual(knot_server.get("httpUrl"), "https://api.connectknot.com/mcp")
        oauth = knot_server.get("oauth")
        self.assertIsInstance(oauth, dict)
        self.assertIs(oauth.get("enabled"), True)

    def test_gemini_context_file(self) -> None:
        gemini_md = REPO_ROOT / "GEMINI.md"
        self.assertTrue(gemini_md.is_file(), "GEMINI.md must exist")
        content = gemini_md.read_text(encoding="utf-8")

        for required_token in (
            "get_context_recovery",
            "get_relevant_context",
            "propose_context",
            "supersedes_context_id",
            "create_handoff",
            "check_pending_handoffs",
        ):
            self.assertIn(required_token, content)

        lowered = content.lower()
        self.assertIn("v1 -> v2", content)
        self.assertIn("pci", lowered)
        self.assertTrue(
            "secret" in lowered or "credential" in lowered,
            "GEMINI.md must document secret and credential safety boundaries",
        )

    def test_slash_commands_toml(self) -> None:
        for rel_path, expected_tools in COMMAND_TOOL_REQUIREMENTS.items():
            cmd_path = REPO_ROOT / rel_path
            self.assertTrue(cmd_path.is_file(), f"{rel_path} must exist")
            parsed = tomllib.loads(cmd_path.read_text(encoding="utf-8"))

            description = parsed.get("description")
            prompt = parsed.get("prompt")
            self.assertIsInstance(description, str)
            self.assertTrue(description.strip(), f"{rel_path} description cannot be empty")
            self.assertIsInstance(prompt, str)
            self.assertTrue(prompt.strip(), f"{rel_path} prompt cannot be empty")
            self.assertIn("{{args}}", prompt)

            for tool_name in expected_tools:
                self.assertIn(
                    tool_name,
                    prompt,
                    f"{rel_path} prompt must reference {tool_name}",
                )

    def test_validator_script_passes(self) -> None:
        validator = REPO_ROOT / "scripts" / "validate_extension.py"
        self.assertTrue(validator.is_file(), "scripts/validate_extension.py must exist")

        result = subprocess.run(
            [sys.executable, str(validator)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"validate_extension.py failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )

    def test_readme_and_license(self) -> None:
        readme_path = REPO_ROOT / "README.md"
        self.assertTrue(readme_path.is_file(), "README.md must exist")
        readme = readme_path.read_text(encoding="utf-8")

        self.assertIn("## TL;DR", readme)
        self.assertIn("v1 -> v2", readme)
        self.assertIn("OAuth 2.1", readme)
        self.assertIn("Knot EnterpriseBrain", readme)
        self.assertIn("KNOT_DEPLOYMENT_MODE=self_hosted", readme)

        for url in REQUIRED_URLS:
            self.assertIn(url, readme, f"README.md missing required cross-link {url}")

        faq_match = re.search(
            r"^## .*FAQ.*$", readme, flags=re.IGNORECASE | re.MULTILINE
        )
        self.assertIsNotNone(faq_match, "README.md must contain a Security/Privacy/VPC FAQ section")
        faq_tail = readme[faq_match.start() :]
        faq_questions = re.findall(r"^###\s+.+\?$", faq_tail, flags=re.MULTILINE)
        self.assertGreaterEqual(
            len(faq_questions),
            6,
            f"Expected at least 6 FAQ questions, found {len(faq_questions)}",
        )

        license_path = REPO_ROOT / "LICENSE"
        self.assertTrue(license_path.is_file(), "LICENSE must exist")
        license_text = license_path.read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Permission is hereby granted, free of charge", license_text)

    def test_ci_workflow_exists(self) -> None:
        ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(ci_path.is_file(), ".github/workflows/ci.yml must exist")
        ci_text = ci_path.read_text(encoding="utf-8")
        self.assertIn("3.11", ci_text)
        self.assertIn("3.12", ci_text)
        self.assertIn("unittest", ci_text)
        self.assertIn("validate_extension.py", ci_text)

    def test_no_unicode_em_dashes_anywhere(self) -> None:
        checked_suffixes = {".md", ".json", ".toml", ".py", ".yml", ".yaml"}
        offenders: list[str] = []
        for path in sorted(REPO_ROOT.rglob("*")):
            if ".git" in path.parts or not path.is_file():
                continue
            if path.suffix.lower() not in checked_suffixes and path.name != "LICENSE":
                continue
            text = path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if EM_DASH in line:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{line_no}")

        self.assertEqual(
            offenders,
            [],
            f"Found forbidden Unicode em-dash in: {', '.join(offenders)}",
        )


if __name__ == "__main__":
    unittest.main()
