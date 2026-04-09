"""Character loading and prompt assembly."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_theater.core.models import CharacterSpec, MemoryBundle, SceneSeed


class YAMLCharacterManager:
    """Loads character definitions from YAML files."""

    def __init__(self, characters: list[CharacterSpec]) -> None:
        if not characters:
            raise ValueError("At least one character is required.")

        self._characters: dict[str, CharacterSpec] = {}
        for character in characters:
            if character.id in self._characters:
                raise ValueError(f"Duplicate character id: {character.id}")
            self._characters[character.id] = character

    @classmethod
    def load_from_file(cls, path: str | Path) -> CharacterSpec:
        file_path = Path(path).expanduser().resolve()
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Character file must contain a mapping: {file_path}")
        return CharacterSpec.model_validate(payload)

    @classmethod
    def load_from_dir(cls, path: str | Path) -> YAMLCharacterManager:
        directory = Path(path).expanduser().resolve()
        files = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
        characters = [cls.load_from_file(file_path) for file_path in files]
        return cls(characters)

    async def get(self, character_id: str) -> CharacterSpec:
        try:
            return self._characters[character_id]
        except KeyError as exc:
            raise KeyError(f"Unknown character id: {character_id}") from exc

    async def list_all(self) -> list[CharacterSpec]:
        return list(self._characters.values())

    async def build_prompt(
        self,
        character: CharacterSpec,
        scene: SceneSeed,
        memory: MemoryBundle,
    ) -> str:
        style_rules = "\n".join(f"- {rule}" for rule in character.style_rules) or "- 自然口語"
        catchphrases = "\n".join(f"- {line}" for line in character.catchphrases) or "- 無"
        recent_events = (
            "\n".join(f"- {line}" for line in memory.recent_events) or "- 目前沒有新記憶"
        )
        grudges = "\n".join(f"- {line}" for line in memory.grudges) or "- 目前沒有明顯恩怨"
        relationship_notes = (
            "\n".join(f"- {line}" for line in memory.relationship_notes)
            or "- 沒有額外關係補充"
        )

        return f"""
你正在參與一個 AI 聊天室即興劇，必須全程保持角色一致。

角色資料
- ID: {character.id}
- 名字: {character.name}
- Persona:
{character.persona.strip()}

說話風格規則
{style_rules}

可自然穿插的口頭禪
{catchphrases}

場景資料
- 標題: {scene.title}
- 調性: {scene.tone}
- 前提:
{scene.premise.strip()}

你的近期記憶
{recent_events}

你的恩怨與執念
{grudges}

關係備忘
{relationship_notes}

輸出規則
- 一律使用繁體中文。
- 保持像聊天室即時回嘴，不要寫旁白、舞台指示、條列、JSON。
- 每次發言控制在 1 到 3 句內，短而有戲。
- 可以點名別人、回應觀眾，但不要脫離你的人設。
- 只輸出你這一輪真正要說的台詞，不要加上名字前綴。
""".strip()
