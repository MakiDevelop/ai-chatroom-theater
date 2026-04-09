"""In-memory transcript and relationship storage."""

from __future__ import annotations

from collections import defaultdict

from ai_theater.core.models import MemoryBundle, RelationshipState, TurnEvent

AUDIENCE_ID = "audience"

NEGATIVE_KEYWORDS = ("垃圾", "盤子", "藍屏", "嘴", "爛", "不服", "閉嘴", "笑死", "嗆")
POSITIVE_KEYWORDS = ("同意", "欣賞", "喜歡", "有道理", "認同", "厲害", "尊重")


class InMemoryStore:
    """Stores session events in memory for the MVP."""

    def __init__(self, history_limit: int = 8) -> None:
        self._history_limit = history_limit
        self._events_by_session: dict[str, list[TurnEvent]] = defaultdict(list)
        self._relationships: dict[tuple[str, str], RelationshipState] = {}

    async def recall(
        self,
        *,
        speaker_id: str,
        related_ids: list[str],
        session_id: str,
    ) -> MemoryBundle:
        recent_events = self._events_by_session[session_id][-self._history_limit :]
        formatted_events = [self._format_event(event) for event in recent_events]

        grudges: list[str] = []
        relationship_notes: list[str] = []
        for related_id in related_ids:
            relation = self._relationships.get((speaker_id, related_id))
            if relation is None:
                continue

            if relation.hostility > relation.affinity and relation.unresolved_conflict:
                grudges.append(
                    f"你對 {related_id} 最近有火藥味：{relation.unresolved_conflict}"
                )

            if relation.hostility > 0:
                relationship_notes.append(
                    f"你對 {related_id} 的敵意值 {relation.hostility:.1f}。"
                )
            if relation.affinity > 0:
                relationship_notes.append(
                    f"你對 {related_id} 的好感值 {relation.affinity:.1f}。"
                )

        return MemoryBundle(
            recent_events=formatted_events,
            grudges=grudges,
            relationship_notes=relationship_notes,
        )

    async def append_turn(self, event: TurnEvent) -> None:
        self._events_by_session[event.session_id].append(event)

        if event.speaker_id == AUDIENCE_ID or not event.targets:
            return

        affinity_delta, hostility_delta = self._infer_sentiment(event.text)
        note = event.text.strip()
        for target_id in event.targets:
            relation = self._relationships.setdefault(
                (event.speaker_id, target_id),
                RelationshipState(source_id=event.speaker_id, target_id=target_id),
            )
            relation.affinity += affinity_delta
            relation.hostility += hostility_delta
            if hostility_delta > 0:
                relation.unresolved_conflict = note

    async def update_relationship(
        self,
        *,
        source_id: str,
        target_id: str,
        delta: float,
        reason: str,
    ) -> None:
        relation = self._relationships.setdefault(
            (source_id, target_id),
            RelationshipState(source_id=source_id, target_id=target_id),
        )
        if delta >= 0:
            relation.affinity += delta
        else:
            relation.hostility += abs(delta)
            relation.unresolved_conflict = reason

    @staticmethod
    def _format_event(event: TurnEvent) -> str:
        speaker = "觀眾" if event.speaker_id == AUDIENCE_ID else event.speaker_id
        return f"{speaker}：{event.text}"

    @staticmethod
    def _infer_sentiment(text: str) -> tuple[float, float]:
        lowered = text.lower()
        hostility = 1.0 if any(keyword in lowered for keyword in NEGATIVE_KEYWORDS) else 0.0
        affinity = 1.0 if any(keyword in lowered for keyword in POSITIVE_KEYWORDS) else 0.0
        return affinity, hostility
