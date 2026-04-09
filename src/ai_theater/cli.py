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
        max_turns=args.max_turns,
    )
    display = RichTheaterTUI()
    session_id = await engine.start(scene, [character.id for character in characters])

    # Transcript log
    transcript: list[str] = []
    transcript.append(f"# {scene.title}")
    transcript.append(f"> {scene.premise.strip()}")
    transcript.append(f"> 調性: {scene.tone}")
    transcript.append(f"> 演員: {', '.join(c.name for c in characters)}")
    transcript.append("")

    display.render_scene(
        scene=scene,
        characters=characters,
        max_turns=args.max_turns,
        ollama_url=args.ollama_url,
    )
    if scene.opening_hook.strip():
        display.render_audience(scene.opening_hook.strip(), label="開場")
        transcript.append(f"**觀眾（開場）**：{scene.opening_hook.strip()}")
        transcript.append("")

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
                transcript=transcript,
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
            transcript.append(f"**{speaker.name}**（{turn_index}/{args.max_turns}）：{event.text}")
            transcript.append("")
            quit_requested = await _wait_between_turns(
                input_queue=input_queue,
                engine=engine,
                display=display,
                session_id=session_id,
                transcript=transcript,
            )
    finally:
        input_task.cancel()
        await provider.aclose()
        with contextlib.suppress(asyncio.CancelledError):
            await input_task

    end_message = "觀眾要求收尾。" if quit_requested else "已達最大回合數。"
    display.render_end(end_message)

    # Save transcript
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        from datetime import datetime

        output_path = Path(f"transcript-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md")
    transcript.append(f"---\n*{end_message}*")
    output_path.write_text("\n".join(transcript), encoding="utf-8")
    display.console.print(f"\n[bold green]Transcript saved → {output_path}[/]")


async def _wait_between_turns(
    *,
    input_queue: asyncio.Queue[tuple[str, str | None]],
    engine: SimpleConversationEngine,
    display: RichTheaterTUI,
    session_id: str,
    transcript: list[str] | None = None,
    delay: float = 0.4,
) -> bool:
    deadline = asyncio.get_running_loop().time() + delay
    while asyncio.get_running_loop().time() < deadline:
        quit_requested = await _drain_input_queue(
            input_queue=input_queue,
            engine=engine,
            display=display,
            session_id=session_id,
            transcript=transcript,
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
    transcript: list[str] | None = None,
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
            if transcript is not None:
                transcript.append(f"**觀眾**：{event.text}")
                transcript.append("")

    return quit_requested


async def _audience_input_loop(input_queue: asyncio.Queue[tuple[str, str | None]]) -> None:
    import threading

    loop = asyncio.get_running_loop()

    def _thread_reader() -> None:
        try:
            while True:
                raw = input("").strip()
                if raw.lower() == "q":
                    loop.call_soon_threadsafe(input_queue.put_nowait, ("quit", None))
                    return
                if not raw:
                    raw = input("插話 > ").strip()
                    if not raw:
                        continue
                    if raw.lower() == "q":
                        loop.call_soon_threadsafe(input_queue.put_nowait, ("quit", None))
                        return
                loop.call_soon_threadsafe(input_queue.put_nowait, ("say", raw))
        except (EOFError, KeyboardInterrupt):
            loop.call_soon_threadsafe(input_queue.put_nowait, ("quit", None))

    thread = threading.Thread(target=_thread_reader, daemon=True)
    thread.start()

    # Keep the coroutine alive until thread exits
    while thread.is_alive():
        await asyncio.sleep(0.2)


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
    start_parser.add_argument(
        "--output",
        default=None,
        help="Path to save transcript markdown. Defaults to transcript-<timestamp>.md",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "start":
        asyncio.run(run_start(args))


if __name__ == "__main__":
    main()
