from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import unquote

from db import get_learning_materials

@dataclass(frozen=True)
class LearningMaterial:
    skill: str
    title: str
    description: str
    url: str
    w3_url: str | None = None


def _skill_key(skill: str) -> str:
    normalized = skill.strip().lower().replace("node.js", "nodejs")
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")


def materials_for(skills: list[str]) -> list[LearningMaterial]:
    skill_keys = list(dict.fromkeys(_skill_key(skill) for skill in skills if skill.strip()))
    return [
        LearningMaterial(
            skill=material["skill"],
            title=material["title"],
            description=material["description"],
            url=material["url"],
            w3_url=material.get("w3_url"),
        )
        for material in get_learning_materials(skill_keys)
    ]


def material_for(skill: str) -> LearningMaterial | None:
    materials = materials_for([_skill_key(skill)])
    return materials[0] if materials else None


def learning_callback_data(skills: list[str]) -> str:
    return "learn"


def learning_skills(callback_data: str) -> list[str]:
    return [item for item in unquote(callback_data.split(":", 1)[1]).split(",") if item]
