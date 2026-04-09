"""Core domain models for AI Chatroom Theater."""

from __future__ import annotations

from pydantic import BaseModel


class CharacterSpec(BaseModel):
    """Definition of an AI character."""

    id: str
    name: str
    persona: str
    style_rules: list[str] = []
    catchphrases: list[str] = []
    triggers: list[str] = []  # topics that make this character fired up
    weaknesses: list[str] = []  # topics they secretly agree with opponents
    forbidden: list[str] = []  # things this character would never say
    emoji_style: str = ""  # e.g. "heavy", "none", "occasional"
    aggression: float = 0.5  # 0.0=passive, 1.0=always attacking
    humor: float = 0.5  # 0.0=dead serious, 1.0=always joking
    verbosity: str = "normal"  # "terse", "normal", "verbose"
    model_profile: str = "ollama/gemma4:31b"


class SceneSeed(BaseModel):
    """Scene configuration that seeds a conversation."""

    id: str
    title: str
    premise: str
    tone: str = "casual"
    opening_hook: str = ""


class TurnEvent(BaseModel):
    """A single turn in the conversation."""

    session_id: str
    speaker_id: str
    text: str
    targets: list[str] = []
    emotion: str | None = None
    interrupt: bool = False
    end_scene: bool = False


class RelationshipState(BaseModel):
    """Tracks relationship between two characters."""

    source_id: str
    target_id: str
    affinity: float = 0.0
    hostility: float = 0.0
    unresolved_conflict: str | None = None


class MemoryBundle(BaseModel):
    """Memory context provided to a character before speaking."""

    recent_events: list[str] = []
    grudges: list[str] = []
    relationship_notes: list[str] = []
