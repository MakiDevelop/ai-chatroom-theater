"""Protocol definitions for pluggable components."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .models import CharacterSpec, MemoryBundle, SceneSeed, TurnEvent


class CharacterManager(Protocol):
    async def get(self, character_id: str) -> CharacterSpec: ...
    async def list_all(self) -> list[CharacterSpec]: ...
    async def build_prompt(
        self,
        character: CharacterSpec,
        scene: SceneSeed,
        memory: MemoryBundle,
    ) -> str: ...


class LLMProvider(Protocol):
    async def generate(
        self,
        *,
        model_profile: str,
        system: str,
        messages: Sequence[dict[str, str]],
    ) -> str: ...


class MemoryStore(Protocol):
    async def recall(
        self,
        *,
        speaker_id: str,
        related_ids: list[str],
        session_id: str,
    ) -> MemoryBundle: ...

    async def append_turn(self, event: TurnEvent) -> None: ...

    async def update_relationship(
        self,
        *,
        source_id: str,
        target_id: str,
        delta: float,
        reason: str,
    ) -> None: ...


class SceneDirector(Protocol):
    async def next_constraints(self, session_id: str) -> dict: ...
    async def should_end(self, session_id: str) -> bool: ...


class ConversationEngine(Protocol):
    async def start(self, scene: SceneSeed, character_ids: list[str]) -> str: ...
    async def inject_audience(self, session_id: str, text: str) -> TurnEvent: ...
    async def step(self, session_id: str) -> TurnEvent: ...
    async def stream(self, session_id: str) -> AsyncIterator[TurnEvent]: ...
