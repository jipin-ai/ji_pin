"""BidSmart regulation skills — loaded by Agent tools.

Each sub-directory contains a SKILL.md with YAML frontmatter.
"""

import os
from pathlib import Path
from typing import Any


SKILLS_DIR = Path(__file__).parent


def list_skills() -> list[dict[str, str]]:
    """Return all available skills with name and description."""
    skills: list[dict[str, str]] = []
    if not SKILLS_DIR.is_dir():
        return skills
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue
        name, desc = _parse_frontmatter(skill_md)
        skills.append({"name": name, "description": desc, "slug": entry.name})
    return skills


def load_skill(slug: str) -> str | None:
    """Load a skill's full SKILL.md content by slug name."""
    path = SKILLS_DIR / slug / "SKILL.md"
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8")
    # Strip frontmatter for cleaner agent consumption
    name, description, body = _parse_frontmatter(path, return_body=True)
    return body


def _parse_frontmatter(path: Path, return_body: bool = False) -> Any:
    """Parse YAML frontmatter from a SKILL.md file."""
    text = path.read_text(encoding="utf-8")
    name = ""
    description = ""
    body = text
    
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            body = parts[2].strip()
            for line in fm.split("\n"):
                line = line.strip()
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("description:"):
                    description = line.split(":", 1)[1].strip()
    
    if return_body:
        return name, description, body
    return (name, description)
