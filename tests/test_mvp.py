from __future__ import annotations

from random import Random

import pytest

from ai_theater.characters.manager import YAMLCharacterManager
from ai_theater.conversation.engine import SimpleConversationEngine
from ai_theater.core.models import MemoryBundle, SceneSeed, TurnEvent
from ai_theater.memory.in_memory import InMemoryStore


class FakeProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[dict[str, object]] = []

    async def generate(
        self,
        *,
        model_profile: str,
        system: str,
        messages: list[dict[str, str]],
    ) -> str:
        self.calls.append(
            {
                "model_profile": model_profile,
                "system": system,
                "messages": messages,
            }
        )
        return self.response_text


@pytest.mark.asyncio
async def test_manager_loads_examples_and_builds_prompt() -> None:
    manager = YAMLCharacterManager.load_from_dir("examples/characters")
    characters = await manager.list_all()

    assert len(characters) == 3

    prompt = await manager.build_prompt(
        characters[0],
        SceneSeed(
            id="demo",
            title="Demo",
            premise="大家在討論筆電。",
            tone="heated",
            opening_hook="要買哪台？",
        ),
        MemoryBundle(
            recent_events=["觀眾：要買哪台？"],
            grudges=["你對 pc-master-race 有火氣。"],
            relationship_notes=["你對 linux-evangelist 的敵意值 1.0。"],
        ),
    )

    assert "繁體中文" in prompt
    assert "你對 pc-master-race 有火氣。" in prompt
    assert characters[0].name in prompt


@pytest.mark.asyncio
async def test_memory_store_tracks_recent_events_and_grudges() -> None:
    store = InMemoryStore(history_limit=4)
    await store.append_turn(
        TurnEvent(
            session_id="session-1",
            speaker_id="apple-fan",
            text="Kevin 你那台破機器根本垃圾。",
            targets=["pc-master-race"],
        )
    )

    bundle = await store.recall(
        speaker_id="apple-fan",
        related_ids=["pc-master-race"],
        session_id="session-1",
    )

    assert bundle.recent_events == ["apple-fan：Kevin 你那台破機器根本垃圾。"]
    assert bundle.grudges == ["你對 pc-master-race 最近有火藥味：Kevin 你那台破機器根本垃圾。"]
    assert "敵意值 1.0" in bundle.relationship_notes[0]


@pytest.mark.asyncio
async def test_engine_prefers_mentioned_speaker() -> None:
    manager = YAMLCharacterManager.load_from_dir("examples/characters")
    provider = FakeProvider("Kevin：規格先拿出來再說。")
    store = InMemoryStore()
    engine = SimpleConversationEngine(
        character_manager=manager,
        llm_provider=provider,
        memory_store=store,
        random_source=Random(0),
    )
    scene = SceneSeed(
        id="demo",
        title="筆電辯論",
        premise="三個人在咖啡廳互嗆。",
        tone="heated",
        opening_hook="要買哪台？",
    )

    session_id = await engine.start(scene, ["apple-fan", "pc-master-race", "linux-evangelist"])
    await engine.inject_audience(session_id, "Kevin，你不是最愛講規格嗎？")

    event = await engine.step(session_id)

    assert event.speaker_id == "pc-master-race"
    assert event.text == "規格先拿出來再說。"
    assert provider.calls[0]["model_profile"] == "ollama/llama3"
