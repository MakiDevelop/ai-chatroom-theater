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
        turn_count: int = 0,
        max_turns: int = 20,
    ) -> str:
        if self._is_small_model(character.model_profile):
            return self._build_compact_prompt(character, scene, memory, turn_count, max_turns)
        style_rules = "\n".join(f"- {rule}" for rule in character.style_rules) or "- 自然口語"
        catchphrases = "\n".join(f"- {line}" for line in character.catchphrases) or "- 無"
        triggers = "\n".join(f"- {t}" for t in character.triggers) if character.triggers else ""
        weaknesses = (
            "\n".join(f"- {w}" for w in character.weaknesses) if character.weaknesses else ""
        )
        forbidden = "\n".join(f"- {f}" for f in character.forbidden) if character.forbidden else ""
        recent_events = (
            "\n".join(f"- {line}" for line in memory.recent_events) or "- 目前沒有新記憶"
        )
        grudges = "\n".join(f"- {line}" for line in memory.grudges) or "- 目前沒有明顯恩怨"
        relationship_notes = (
            "\n".join(f"- {line}" for line in memory.relationship_notes)
            or "- 沒有額外關係補充"
        )

        # Verbosity instruction
        verbosity_map = {
            "terse": "每次只講一句，惜字如金。",
            "normal": "每次發言 1 到 3 句。",
            "verbose": "可以長一點，但不超過 5 句。",
        }
        verbosity_instruction = verbosity_map.get(character.verbosity, verbosity_map["normal"])

        # Emoji instruction
        emoji_instruction = ""
        if character.emoji_style == "heavy":
            emoji_instruction = "- 大量使用 emoji 表情。"
        elif character.emoji_style == "none":
            emoji_instruction = "- 絕對不使用 emoji。"
        elif character.emoji_style == "occasional":
            emoji_instruction = "- 偶爾使用 emoji，但不要太多。"

        # Personality dials
        personality_notes = []
        if character.aggression >= 0.8:
            personality_notes.append("- 你非常好鬥，幾乎每句話都在攻擊別人的觀點。")
        elif character.aggression <= 0.2:
            personality_notes.append("- 你個性溫和，傾向用理性說服而非攻擊。")
        if character.humor >= 0.8:
            personality_notes.append("- 你很愛開玩笑，常用幽默化解衝突或嘲諷。")
        elif character.humor <= 0.2:
            personality_notes.append("- 你說話非常認真，幾乎不開玩笑。")
        personality_block = "\n".join(personality_notes) if personality_notes else ""

        # Build optional sections
        optional_sections = []
        if triggers:
            optional_sections.append(f"碰到這些話題你會特別激動\n{triggers}")
        if weaknesses:
            optional_sections.append(f"你的弱點（內心其實有點認同的點，偶爾可以不小心露出來）\n{weaknesses}")
        if forbidden:
            optional_sections.append(f"你絕對不會說的話\n{forbidden}")
        optional_block = "\n\n".join(optional_sections)

        return f"""
你正在參與一個 AI 聊天室即興劇，必須全程保持角色一致。

角色資料
- ID: {character.id}
- 名字: {character.name}
- Persona:
{character.persona.strip()}

說話風格規則
{style_rules}
{emoji_instruction}

可自然穿插的口頭禪
{catchphrases}

{personality_block}

{optional_block}

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

對話節奏指引（目前第 {turn_count} 回合 / 共 {max_turns} 回合）
{self._phase_instruction(turn_count, max_turns, character)}

輸出規則
- 一律使用繁體中文。
- 保持像聊天室即時回嘴，不要寫旁白、舞台指示、條列、JSON。
- {verbosity_instruction}
- 可以點名別人、回應觀眾，但不要脫離你的人設。
- 只輸出你這一輪真正要說的台詞，不要加上名字前綴。
- 重要：不要每次都用攻擊語氣。
- 可以提問、岔題、自嘲、說故事、突然沉默、提起共同經驗。讓對話有節奏變化。
""".strip()

    @staticmethod
    def _phase_instruction(turn_count: int, max_turns: int, character: CharacterSpec) -> str:
        progress = turn_count / max(max_turns, 1)
        if progress < 0.25:
            return (
                "- 現在是開場階段。先試探，不要一上來就全力攻擊。\n"
                "- 可以先聊聊自己的經驗或最近發生的事。\n"
                "- 用提問展開話題，不要急著下結論。"
            )
        elif progress < 0.5:
            return (
                "- 對話漸入佳境。可以開始表達立場，但也要回應別人說的話。\n"
                "- 試著找到對方觀點裡你（稍微）認同的地方，然後再提出反論。\n"
                "- 可以講一個親身經歷來支持你的觀點。"
            )
        elif progress < 0.75:
            return (
                "- 對話進入中後段。你可以稍微露出弱點或承認一些事。\n"
                "- 不需要每句都反駁。可以岔開話題、開玩笑、或突然聊別的。\n"
                "- 如果你的 weaknesses 清單有東西，現在可以『不小心』說出來。"
            )
        else:
            return (
                "- 快結束了。試著做一個稍微有結論感的發言。\n"
                "- 可以是讓步、總結、或一個出人意料的觀點轉變。\n"
                "- 也可以用一句幽默的話收尾，不一定要嚴肅。"
            )

    @staticmethod
    def _is_small_model(model_profile: str) -> bool:
        small_tags = ("e2b", ":2b", ":3b", ":4b", "1b")
        return any(tag in model_profile.lower() for tag in small_tags)

    @staticmethod
    def _build_compact_prompt(
        character: CharacterSpec,
        scene: SceneSeed,
        memory: MemoryBundle,
        turn_count: int,
        max_turns: int,
    ) -> str:
        catchphrase = character.catchphrases[0] if character.catchphrases else ""
        recent = memory.recent_events[-3:] if memory.recent_events else []
        recent_block = "\n".join(f"- {e}" for e in recent)

        return f"""你是「{character.name}」，{character.persona.strip().split(chr(10))[0]}
口頭禪：{catchphrase}
場景：{scene.title}（{scene.tone}）— {scene.premise.strip().split(chr(10))[0]}
回合 {turn_count}/{max_turns}。

最近對話：
{recent_block}

規則：繁體中文、1-2句、像聊天室回嘴、不要加名字前綴、不要旁白。有個性地回應！""".strip()
