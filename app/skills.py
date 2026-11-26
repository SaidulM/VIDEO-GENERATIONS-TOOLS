from __future__ import annotations
import re
from .config import SKILLS_DIR

def _metadata(text):
    name = description = ""
    match = re.search(r"(?ms)^---\s*\n(.*?)\n---", text)
    if match:
        for line in match.group(1).splitlines():
            if line.startswith("name:"):
                name = line.split(":",1)[1].strip().strip('"')
            if line.startswith("description:"):
                description = line.split(":",1)[1].strip().strip('"')
    return name, description

def load_skills():
    items = []
    if not SKILLS_DIR.exists():
        return items
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        try:
            content = path.read_text(encoding="utf-8")
            name, description = _metadata(content)
            items.append({"id":path.parent.name,"name":name or path.parent.name,
                          "description":description,"content":content[:10000]})
        except OSError:
            continue
    return items

def skill_context():
    return "\n\n".join(f"### Skill: {item['name']}\n{item['content']}" for item in load_skills())
