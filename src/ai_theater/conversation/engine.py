"""Conversation engine for the AI theater MVP."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from random import Random
from uuid import uuid4

from ai_theater.core.models import CharacterSpec, SceneSeed, TurnEvent
from ai_theater.core.protocols import CharacterManager, ConversationEngine, LLMProvider, MemoryStore

AUDIENCE_ID = "audience"


@dataclass
class SessionState:
    session_id: str
    scene: SceneSeed
    characters: dict[str, CharacterSpec]
    character_order: list[str]
    events: list[TurnEvent] = field(default_factory=list)
    messages: list[dict[str, str]] = field(default_factory=list)
    last_spoke_turn: dict[str, int] = field(default_factory=dict)
    turn_count: int = 0
    last_speaker_id: str | None = None


class SimpleConversationEngine(ConversationEngine):
    """Coordinates speaker selection, memory recall, and LLM responses."""

    def __init__(
        self,
        *,
        character_manager: CharacterManager,
        llm_provider: LLMProvider,
        memory_store: MemoryStore,
        context_window: int = 12,
        random_source: Random | None = None,
    ) -> None:
        self._character_manager = character_manager
        self._llm_provider = llm_provider
        self._memory_store = memory_store
        self._context_window = context_window
        self._random = random_source or Random()
        self._sessions: dict[str, SessionState] = {}

    async def start(self, scene: SceneSeed, character_ids: list[str]) -> str:
        if not 2 <= len(character_ids) <= 4:
            raise ValueError("The MVP supports between 2 and 4 characters per scene.")

        characters = {
            character_id: await self._character_manager.get(character_id)
            for character_id in character_ids
        }
        session_id = uuid4().hex
        state = SessionState(
            session_id=session_id,
            scene=scene,
            characters=characters,
            character_order=character_ids,
        )
        self._sessions[session_id] = state

        if scene.opening_hook.strip():
            opening_event = TurnEvent(
                session_id=session_id,
                speaker_id=AUDIENCE_ID,
                text=scene.opening_hook.strip(),
                interrupt=True,
            )
            await self._record_event(state, opening_event)

        return session_id

    async def inject_audience(self, session_id: str, text: str) -> TurnEvent:
        state = self._get_state(session_id)
        event = TurnEvent(
            session_id=session_id,
            speaker_id=AUDIENCE_ID,
            text=text.strip(),
            interrupt=True,
        )
        await self._record_event(state, event)
        return event

    async def step(self, session_id: str) -> TurnEvent:
        state = self._get_state(session_id)
        speaker = self._select_speaker(state)
        related_ids = [
            character_id for character_id in state.character_order if character_id != speaker.id
        ]
        memory = await self._memory_store.recall(
            speaker_id=speaker.id,
            related_ids=related_ids,
            session_id=session_id,
        )
        system_prompt = await self._character_manager.build_prompt(speaker, state.scene, memory)
        response_text = await self._llm_provider.generate(
            model_profile=speaker.model_profile,
            system=system_prompt,
            messages=state.messages[-self._context_window :],
        )
        clean_text = self._clean_generated_text(speaker, response_text)
        event = TurnEvent(
            session_id=session_id,
            speaker_id=speaker.id,
            text=clean_text,
            targets=self._extract_targets(clean_text, speaker.id, state.characters),
        )
        await self._record_event(state, event)
        state.turn_count += 1
        state.last_speaker_id = speaker.id
        state.last_spoke_turn[speaker.id] = state.turn_count
        return event

    async def stream(self, session_id: str) -> AsyncIterator[TurnEvent]:
        while True:
            yield await self.step(session_id)

    def _select_speaker(self, state: SessionState) -> CharacterSpec:
        recent_events = state.events[-2:]
        scored_characters: list[tuple[float, str]] = []
        for character_id in state.character_order:
            character = state.characters[character_id]
            mentioned = self._was_mentioned(character, recent_events)
            last_turn = state.last_spoke_turn.get(character.id, 0)
            silence_turns = state.turn_count - last_turn + 1
            just_spoke = 1 if state.last_speaker_id == character.id else 0
            score = (
                3 * mentioned
                + 2 * silence_turns
                + self._random.random()
                - 5 * just_spoke
            )
            scored_characters.append((score, character.id))

        _, selected_id = max(scored_characters, key=lambda item: (item[0], item[1]))
        return state.characters[selected_id]

    def _was_mentioned(self, character: CharacterSpec, recent_events: list[TurnEvent]) -> int:
        tokens = {character.id.lower(), character.name.lower()}
        for event in recent_events:
            if character.id in event.targets:
                return 1
            lowered = event.text.lower()
            if any(token in lowered for token in tokens):
                return 1
        return 0

    async def _record_event(self, state: SessionState, event: TurnEvent) -> None:
        state.events.append(event)
        state.messages.append({"role": "user", "content": self._format_message(state, event)})
        await self._memory_store.append_turn(event)

    @staticmethod
    def _format_message(state: SessionState, event: TurnEvent) -> str:
        if event.speaker_id == AUDIENCE_ID:
            speaker_name = "觀眾"
        else:
            speaker_name = state.characters[event.speaker_id].name
        return f"{speaker_name}：{event.text}"

    @staticmethod
    def _clean_generated_text(speaker: CharacterSpec, text: str) -> str:
        clean_text = text.strip()
        prefixes = (
            f"{speaker.name}：",
            f"{speaker.name}:",
            f"{speaker.id}：",
            f"{speaker.id}:",
        )
        for prefix in prefixes:
            if clean_text.startswith(prefix):
                clean_text = clean_text[len(prefix) :].strip()
        return clean_text or "..."

    @staticmethod
    def _extract_targets(
        text: str,
        speaker_id: str,
        characters: dict[str, CharacterSpec],
    ) -> list[str]:
        lowered = text.lower()
        targets: list[str] = []
        for character_id, character in characters.items():
            if character_id == speaker_id:
                continue
            if character_id.lower() in lowered or character.name.lower() in lowered:
                targets.append(character_id)
        return targets

    def _get_state(self, session_id: str) -> SessionState:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown session id: {session_id}") from exc
