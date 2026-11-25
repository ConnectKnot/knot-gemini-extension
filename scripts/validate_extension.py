#!/usr/bin/env python3
"""Validate the Knot Gemini CLI extension layout, manifests, TOML commands, and hygiene."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EM_DASH = "\u2014"

REQUIRED_FILES = (
    "gemini-extension.json",
    "GEMINI.md",
    "README.md",
    "LICENSE",
    "commands/knot/recover.toml",
    "commands/knot/supersede.toml",
    "commands/knot/handoff.toml",
    ".github/workflows/ci.yml",
)

REQUIRED_GEMINI_MD_TOKENS = (
    "get_context_recovery",
    "get_relevant_context",
    "propose_context",
    "supersedes_context_id",
    "create_handoff",
    "check_pending_handoffs",
    "v1 -> v2",
)

REQUIRED_README_URLS = (
    "https://connectknot.com",
    "https://connectknot.com/enterprise-brain",
    "https://connectknot.com/whitepaper",
    "https://connectknot.com/quickstart",
    "https://connectknot.com/llms-full.txt",
)

COMMAND_REQUIRED_TOOLS = {
    "commands/knot/recover.toml": ("get_context_recovery", "get_relevant_context"),
    "commands/knot/supersede.toml": (
        "get_relevant_context",
        "propose_context",
        "supersedes_context_id",
    ),
    "commands/knot/handoff.toml": ("create_handoff", "check_pending_handoffs"),
}


def validate_manifest(errors: list[str]) -> None:
    manifest_path = REPO_ROOT / "gemini-extension.json"
    if not manifest_path.is_file():
        errors.append("Missing gemini-extension.json")
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in gemini-extension.json: {exc}")
        return

    if not isinstance(manifest, dict):
        errors.append("gemini-extension.json root must be a JSON object")
        return

    if manifest.get("name") != "knot":
        errors.append(f"Expected name == 'knot', got {manifest.get('name')!r}")

    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"Expected semver version string, got {version!r}")

    if manifest.get("contextFileName") != "GEMINI.md":
        errors.append(
            f"Expected contextFileName == 'GEMINI.md', got {manifest.get('contextFileName')!r}"
        )

    description = manifest.get("description")
    if not isinstance(description, str) or not (10 <= len(description.strip()) <= 160):
        errors.append("Manifest description must be a concise string (10-160 chars)")

    mcp_servers = manifest.get("mcpServers")
    knot_cfg = mcp_servers.get("knot") if isinstance(mcp_servers, dict) else None
    if not isinstance(knot_cfg, dict):
        errors.append("mcpServers.knot must be an object")
        return

    if knot_cfg.get("httpUrl") != "https://api.connectknot.com/mcp":
        errors.append(
            f"Expected mcpServers.knot.httpUrl == 'https://api.connectknot.com/mcp', got {knot_cfg.get('httpUrl')!r}"
        )

    oauth = knot_cfg.get("oauth")
    if not isinstance(oauth, dict) or oauth.get("enabled") is not True:
        errors.append("Expected mcpServers.knot.oauth.enabled == true")


def validate_gemini_md(errors: list[str]) -> None:
    path = REPO_ROOT / "GEMINI.md"
    if not path.is_file():
        errors.append("Missing GEMINI.md")
        return

    content = path.read_text(encoding="utf-8")
    for token in REQUIRED_GEMINI_MD_TOKENS:
        if token not in content:
            errors.append(f"GEMINI.md missing required token: {token}")

    lowered = content.lower()
    if "pci" not in lowered or ("secret" not in lowered and "credential" not in lowered):
        errors.append("GEMINI.md must document PCI and secret safety boundaries")


def validate_commands(errors: list[str]) -> None:
    commands_dir = REPO_ROOT / "commands"
    if not commands_dir.is_dir():
        errors.append("Missing commands/ directory")
        return

    toml_files = sorted(commands_dir.rglob("*.toml"))
    if not toml_files:
        errors.append("No .toml slash commands found under commands/")
        return

    for path in toml_files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"Invalid TOML in {rel}: {exc}")
            continue

        desc = data.get("description")
        prompt = data.get("prompt")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(f"{rel} must define a non-empty description string")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"{rel} must define a non-empty prompt string")
        elif "{{args}}" not in prompt:
            errors.append(f"{rel} prompt must include '{{{{args}}}}'")

        for required_tool in COMMAND_REQUIRED_TOOLS.get(rel, ()):
            if not isinstance(prompt, str) or required_tool not in prompt:
                errors.append(f"{rel} prompt must reference {required_tool}")


def validate_readme_and_license(errors: list[str]) -> None:
    readme_path = REPO_ROOT / "README.md"
    if not readme_path.is_file():
        errors.append("Missing README.md")
    else:
        readme = readme_path.read_text(encoding="utf-8")
        for marker in ("## TL;DR", "KNOT_DEPLOYMENT_MODE=self_hosted", "Knot EnterpriseBrain"):
            if marker not in readme:
                errors.append(f"README.md missing required marker: {marker}")
        for url in REQUIRED_README_URLS:
            if url not in readme:
                errors.append(f"README.md missing required URL: {url}")

        faq_match = re.search(r"^## .*FAQ.*$", readme, flags=re.IGNORECASE | re.MULTILINE)
        if not faq_match:
            errors.append("README.md missing FAQ section")
        else:
            faq_questions = re.findall(
                r"^###\s+.+\?$", readme[faq_match.start() :], flags=re.MULTILINE
            )
            if len(faq_questions) < 6:
                errors.append(f"README.md FAQ must have >= 6 questions, found {len(faq_questions)}")

    license_path = REPO_ROOT / "LICENSE"
    if not license_path.is_file():
        errors.append("Missing LICENSE")
    elif "MIT License" not in license_path.read_text(encoding="utf-8"):
        errors.append("LICENSE must be the MIT License")


def validate_no_em_dashes(errors: list[str]) -> None:
    checked_suffixes = {".md", ".json", ".toml", ".py", ".yml", ".yaml"}
    for path in sorted(REPO_ROOT.rglob("*")):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.suffix.lower() not in checked_suffixes and path.name != "LICENSE":
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if EM_DASH in line:
                errors.append(
                    f"Forbidden Unicode em-dash at {path.relative_to(REPO_ROOT)}:{line_no}"
                )


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (REPO_ROOT / rel).is_file():
            errors.append(f"Missing required file: {rel}")

    validate_manifest(errors)
    validate_gemini_md(errors)
    validate_commands(errors)
    validate_readme_and_license(errors)
    validate_no_em_dashes(errors)

    if errors:
        print("Knot Gemini CLI extension validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("Knot Gemini CLI extension validation PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
