"""CLI entry point for AI Chatroom Theater."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from pathlib import Path

import yaml

from ai_theater.characters.manager import YAMLCharacterManager
from ai_theater.conversation.engine import SimpleConversationEngine
from ai_theater.core.models import SceneSeed
from ai_theater.display.rich_tui import RichTheaterTUI
from ai_theater.memory.in_memory import InMemoryStore
from ai_theater.providers.ollama import OllamaProvider


async def run_start(args: argparse.Namespace) -> None:
    scene = _load_scene(args.scene)
    character_manager = YAMLCharacterManager.load_from_dir(args.characters_dir)
    characters = await character_manager.list_all()

    provider = OllamaProvider(base_url=args.ollama_url)
    memory_store = InMemoryStore()
    engine = SimpleConversationEngine(
        character_manager=character_manager,
        llm_provider=provider,
        memory_store=memory_store,
    )
    display = RichTheaterTUI()
    session_id = await engine.start(scene, [character.id for character in characters])

    display.render_scene(
        scene=scene,
        characters=characters,
        max_turns=args.max_turns,
        ollama_url=args.ollama_url,
    )
    if scene.opening_hook.strip():
        display.render_audience(scene.opening_hook.strip(), label="開場")

    input_queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue()
    input_task = asyncio.create_task(_audience_input_loop(input_queue))

    quit_requested = False
    turn_index = 0
    try:
        while turn_index < args.max_turns and not quit_requested:
            quit_requested = await _drain_input_queue(
                input_queue=input_queue,
                engine=engine,
                display=display,
                session_id=session_id,
            )
            if quit_requested or turn_index >= args.max_turns:
                break

            display.render_status("角色正在接話...")
            event = await engine.step(session_id)
            turn_index += 1
            speaker = await character_manager.get(event.speaker_id)
            display.render_turn(
                event=event,
                speaker_name=speaker.name,
                turn_index=turn_index,
                max_turns=args.max_turns,
            )
            quit_requested = await _wait_between_turns(
                input_queue=input_queue,
                engine=engine,
                display=display,
                session_id=session_id,
            )
    finally:
        input_task.cancel()
        await provider.aclose()
        with contextlib.suppress(asyncio.CancelledError):
            await input_task

    end_message = "觀眾要求收尾。" if quit_requested else "已達最大回合數。"
    display.render_end(end_message)


async def _wait_between_turns(
    *,
    input_queue: asyncio.Queue[tuple[str, str | None]],
    engine: SimpleConversationEngine,
    display: RichTheaterTUI,
    session_id: str,
    delay: float = 0.4,
) -> bool:
    deadline = asyncio.get_running_loop().time() + delay
    while asyncio.get_running_loop().time() < deadline:
        quit_requested = await _drain_input_queue(
            input_queue=input_queue,
            engine=engine,
            display=display,
            session_id=session_id,
        )
        if quit_requested:
            return True
        await asyncio.sleep(0.05)
    return False


async def _drain_input_queue(
    *,
    input_queue: asyncio.Queue[tuple[str, str | None]],
    engine: SimpleConversationEngine,
    display: RichTheaterTUI,
    session_id: str,
) -> bool:
    quit_requested = False
    while True:
        try:
            action, payload = input_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        if action == "quit":
            quit_requested = True
        elif action == "say" and payload:
            event = await engine.inject_audience(session_id, payload)
            display.render_audience(event.text)

    return quit_requested


async def _audience_input_loop(input_queue: asyncio.Queue[tuple[str, str | None]]) -> None:
    try:
        from aioconsole import ainput
    except ImportError as exc:
        raise RuntimeError("aioconsole is required for interactive audience input.") from exc

    try:
        while True:
            raw_input = (await ainput("")).strip()
            if raw_input.lower() == "q":
                await input_queue.put(("quit", None))
                return

            if not raw_input:
                raw_input = (await ainput("插話 > ")).strip()
                if not raw_input:
                    continue
                if raw_input.lower() == "q":
                    await input_queue.put(("quit", None))
                    return

            await input_queue.put(("say", raw_input))
    except (EOFError, KeyboardInterrupt):
        await input_queue.put(("quit", None))


def _load_scene(path: str) -> SceneSeed:
    scene_path = Path(path).expanduser().resolve()
    payload = yaml.safe_load(scene_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Scene file must contain a mapping: {scene_path}")
    return SceneSeed.model_validate(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="theater")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start an AI theater scene.")
    start_parser.add_argument("--scene", required=True, help="Path to a scene YAML file.")
    start_parser.add_argument(
        "--characters-dir",
        default="examples/characters",
        help="Directory containing character YAML files.",
    )
    start_parser.add_argument(
        "--max-turns",
        type=int,
        default=20,
        help="Maximum number of AI turns before ending the scene.",
    )
    start_parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Base URL for the Ollama server.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "start":
        asyncio.run(run_start(args))


if __name__ == "__main__":
    main()
