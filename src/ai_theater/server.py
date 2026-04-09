"""FastAPI server for AI Chatroom Theater."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal, cast

import yaml
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, TypeAdapter, ValidationError, field_validator

from ai_theater.characters.manager import YAMLCharacterManager
from ai_theater.conversation.engine import SimpleConversationEngine
from ai_theater.core.models import CharacterSpec, SceneSeed, TurnEvent
from ai_theater.memory.in_memory import InMemoryStore
from ai_theater.providers.ollama import OllamaProvider

STEP_DELAY_SECONDS = 0.5


class SceneSummary(BaseModel):
    """Public scene metadata for the frontend."""

    id: str
    title: str
    premise: str
    tone: str
    opening_hook: str

    @classmethod
    def from_scene(cls, scene: SceneSeed) -> SceneSummary:
        return cls.model_validate(scene.model_dump())


class CharacterSummary(BaseModel):
    """Public character metadata for the frontend."""

    id: str
    name: str
    persona: str
    aggression: float
    humor: float
    emoji_style: str

    @classmethod
    def from_character(cls, character: CharacterSpec) -> CharacterSummary:
        return cls.model_validate(
            {
                "id": character.id,
                "name": character.name,
                "persona": character.persona,
                "aggression": character.aggression,
                "humor": character.humor,
                "emoji_style": character.emoji_style,
            }
        )


class CreateSessionRequest(BaseModel):
    """Payload used to create a conversation session."""

    scene_id: str
    character_ids: list[str]
    max_turns: int = Field(default=20, ge=1)

    @field_validator("character_ids")
    @classmethod
    def validate_character_ids(cls, value: list[str]) -> list[str]:
        if not 2 <= len(value) <= 4:
            raise ValueError("Sessions require between 2 and 4 characters.")
        if len(value) != len(set(value)):
            raise ValueError("character_ids must be unique.")
        return value


class CreateSessionResponse(BaseModel):
    """Response returned after a session is created."""

    session_id: str
    scene: SceneSummary
    characters: list[CharacterSummary]


class TurnMessage(BaseModel):
    """A single streamed character turn."""

    type: Literal["turn"] = "turn"
    speaker_id: str
    speaker_name: str
    text: str
    targets: list[str]
    emotion: str | None
    turn_index: int
    max_turns: int


class AudienceMessage(BaseModel):
    """Audience line broadcast to the client."""

    type: Literal["audience"] = "audience"
    text: str


class SceneEndMessage(BaseModel):
    """Scene termination message."""

    type: Literal["scene_end"] = "scene_end"
    reason: Literal["max_turns", "quit"]


class ErrorMessage(BaseModel):
    """Recoverable WebSocket error payload."""

    type: Literal["error"] = "error"
    message: str


class StartClientMessage(BaseModel):
    """Client request to start the loop."""

    type: Literal["start"]


class QuitClientMessage(BaseModel):
    """Client request to stop the scene."""

    type: Literal["quit"]


class AudienceClientMessage(BaseModel):
    """Client audience interjection."""

    type: Literal["audience"]
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Audience text cannot be empty.")
        return text


ClientMessage = Annotated[
    AudienceClientMessage | QuitClientMessage | StartClientMessage,
    Field(discriminator="type"),
]

CLIENT_MESSAGE_ADAPTER = TypeAdapter(ClientMessage)


@dataclass(slots=True)
class SessionRuntime:
    """Runtime data stored for an active scene session."""

    session_id: str
    scene: SceneSeed
    engine: SimpleConversationEngine
    characters: dict[str, CharacterSpec]
    max_turns: int
    turn_index: int = 0
    opening_hook_sent: bool = False
    finished_reason: Literal["max_turns", "quit"] | None = None


@dataclass(slots=True)
class ServerRuntime:
    """Shared application runtime state."""

    character_manager: YAMLCharacterManager
    characters: dict[str, CharacterSpec]
    provider: OllamaProvider
    scenes: dict[str, SceneSeed]
    sessions: dict[str, SessionRuntime] = field(default_factory=dict)


def create_app(
    *,
    characters_dir: str | Path = "examples/characters",
    scenes_dir: str | Path = "examples/scenes",
    ollama_url: str = "http://localhost:11434",
) -> FastAPI:
    """Create the FastAPI app with configured asset directories."""

    characters_path = Path(characters_dir).expanduser().resolve()
    scenes_path = Path(scenes_dir).expanduser().resolve()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        character_manager = YAMLCharacterManager.load_from_dir(characters_path)
        character_list = await character_manager.list_all()
        provider = OllamaProvider(base_url=ollama_url)
        app.state.runtime = ServerRuntime(
            character_manager=character_manager,
            characters={character.id: character for character in character_list},
            provider=provider,
            scenes=_load_scenes(scenes_path),
        )
        try:
            yield
        finally:
            await provider.aclose()

    app = FastAPI(title="AI Chatroom Theater API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/scenes", response_model=list[SceneSummary])
    async def list_scenes(request: Request) -> list[SceneSummary]:
        runtime = _get_runtime(request.app)
        scenes = sorted(runtime.scenes.values(), key=lambda scene: scene.id)
        return [SceneSummary.from_scene(scene) for scene in scenes]

    @app.get("/api/characters", response_model=list[CharacterSummary])
    async def list_characters(request: Request) -> list[CharacterSummary]:
        runtime = _get_runtime(request.app)
        characters = sorted(runtime.characters.values(), key=lambda character: character.id)
        return [CharacterSummary.from_character(character) for character in characters]

    @app.post("/api/sessions", response_model=CreateSessionResponse)
    async def create_session(
        payload: CreateSessionRequest,
        request: Request,
    ) -> CreateSessionResponse:
        runtime = _get_runtime(request.app)
        scene = runtime.scenes.get(payload.scene_id)
        if scene is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown scene id: {payload.scene_id}",
            )

        missing_character_ids = [
            character_id
            for character_id in payload.character_ids
            if character_id not in runtime.characters
        ]
        if missing_character_ids:
            missing = ", ".join(missing_character_ids)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown character id(s): {missing}",
            )

        engine = SimpleConversationEngine(
            character_manager=runtime.character_manager,
            llm_provider=runtime.provider,
            memory_store=InMemoryStore(),
            max_turns=payload.max_turns,
        )
        session_id = await engine.start(scene, payload.character_ids)
        characters = {
            character_id: runtime.characters[character_id] for character_id in payload.character_ids
        }
        runtime.sessions[session_id] = SessionRuntime(
            session_id=session_id,
            scene=scene,
            engine=engine,
            characters=characters,
            max_turns=payload.max_turns,
        )
        return CreateSessionResponse(
            session_id=session_id,
            scene=SceneSummary.from_scene(scene),
            characters=[
                CharacterSummary.from_character(runtime.characters[character_id])
                for character_id in payload.character_ids
            ],
        )

    @app.websocket("/api/sessions/{session_id}/ws")
    async def session_socket(websocket: WebSocket, session_id: str) -> None:
        runtime = _get_runtime(websocket.app)
        session = runtime.sessions.get(session_id)
        if session is None:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=f"Unknown session id: {session_id}",
            )
            return

        await websocket.accept()
        stop_event = asyncio.Event()
        step_task: asyncio.Task[None] | None = None

        try:
            while True:
                try:
                    payload = await websocket.receive_json()
                except WebSocketDisconnect:
                    break

                try:
                    message = CLIENT_MESSAGE_ADAPTER.validate_python(payload)
                except ValidationError as exc:
                    await _send_message(
                        websocket,
                        ErrorMessage(message=_format_validation_error(exc)),
                    )
                    continue

                if isinstance(message, StartClientMessage):
                    if session.finished_reason is not None:
                        await _send_message(
                            websocket,
                            SceneEndMessage(reason=session.finished_reason),
                        )
                        await websocket.close()
                        break
                    if step_task is not None and not step_task.done():
                        await _send_message(
                            websocket,
                            ErrorMessage(message="Conversation already running."),
                        )
                        continue
                    stop_event = asyncio.Event()
                    step_task = asyncio.create_task(_run_step_loop(websocket, session, stop_event))
                    continue

                if isinstance(message, AudienceClientMessage):
                    event = await session.engine.inject_audience(session.session_id, message.text)
                    await _send_message(websocket, AudienceMessage(text=event.text))
                    continue

                if isinstance(message, QuitClientMessage):
                    session.finished_reason = "quit"
                    stop_event.set()
                    if step_task is not None:
                        step_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await step_task
                    await _send_message(websocket, SceneEndMessage(reason="quit"))
                    await websocket.close()
                    break
        finally:
            if step_task is not None:
                step_task.cancel()
                with suppress(asyncio.CancelledError):
                    await step_task
            if session.finished_reason is not None:
                runtime.sessions.pop(session_id, None)

    return app


def _get_runtime(app: FastAPI) -> ServerRuntime:
    return cast(ServerRuntime, app.state.runtime)


def _load_scenes(directory: Path) -> dict[str, SceneSeed]:
    scenes: dict[str, SceneSeed] = {}
    files = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
    for file_path in files:
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Scene file must contain a mapping: {file_path}")
        scene = SceneSeed.model_validate(payload)
        if scene.id != file_path.stem:
            raise ValueError(f"Scene id must match filename: {file_path}")
        if scene.id in scenes:
            raise ValueError(f"Duplicate scene id: {scene.id}")
        scenes[scene.id] = scene
    return scenes


def _format_validation_error(exc: ValidationError) -> str:
    first_error = exc.errors()[0]
    location = ".".join(str(item) for item in first_error["loc"])
    return f"{location}: {first_error['msg']}"


async def _run_step_loop(
    websocket: WebSocket,
    session: SessionRuntime,
    stop_event: asyncio.Event,
) -> None:
    if session.scene.opening_hook.strip() and not session.opening_hook_sent:
        sent = await _send_message(
            websocket,
            AudienceMessage(text=session.scene.opening_hook.strip()),
        )
        if not sent:
            return
        session.opening_hook_sent = True

    while not stop_event.is_set():
        if session.turn_index >= session.max_turns:
            session.finished_reason = "max_turns"
            await _send_message(websocket, SceneEndMessage(reason="max_turns"))
            await websocket.close()
            return

        try:
            event = await session.engine.step(session.session_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - runtime safety path
            sent = await _send_message(websocket, ErrorMessage(message=str(exc)))
            if not sent or await _wait_for_stop(stop_event, STEP_DELAY_SECONDS):
                return
            continue

        session.turn_index += 1
        speaker = session.characters[event.speaker_id]
        sent = await _send_message(
            websocket,
            _build_turn_message(event, speaker, session.turn_index, session.max_turns),
        )
        if not sent:
            return

        if session.turn_index >= session.max_turns:
            session.finished_reason = "max_turns"
            await _send_message(websocket, SceneEndMessage(reason="max_turns"))
            await websocket.close()
            return

        if await _wait_for_stop(stop_event, STEP_DELAY_SECONDS):
            return


def _build_turn_message(
    event: TurnEvent,
    speaker: CharacterSpec,
    turn_index: int,
    max_turns: int,
) -> TurnMessage:
    return TurnMessage(
        speaker_id=event.speaker_id,
        speaker_name=speaker.name,
        text=event.text,
        targets=event.targets,
        emotion=event.emotion,
        turn_index=turn_index,
        max_turns=max_turns,
    )


async def _send_message(
    websocket: WebSocket,
    message: TurnMessage | AudienceMessage | SceneEndMessage | ErrorMessage,
) -> bool:
    try:
        await websocket.send_json(message.model_dump())
    except RuntimeError:
        return False
    return True


async def _wait_for_stop(stop_event: asyncio.Event, delay: float) -> bool:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=delay)
    except TimeoutError:
        return False
    return True


_REPO_ROOT = Path(__file__).resolve().parents[2]

app = create_app(
    characters_dir=_REPO_ROOT / "examples/characters",
    scenes_dir=_REPO_ROOT / "examples/scenes",
)
