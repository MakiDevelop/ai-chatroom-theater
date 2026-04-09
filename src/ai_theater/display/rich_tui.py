"""Rich-based terminal display for the theater MVP."""

from __future__ import annotations

from itertools import cycle

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ai_theater.core.models import CharacterSpec, SceneSeed, TurnEvent

AUDIENCE_ID = "audience"
FOOTER_TEXT = "[Enter] 插話 / [q] 結束"


class RichTheaterTUI:
    """Prints the scene and turns with Rich panels."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._speaker_styles: dict[str, str] = {}

    def render_scene(
        self,
        *,
        scene: SceneSeed,
        characters: list[CharacterSpec],
        max_turns: int,
        ollama_url: str,
    ) -> None:
        self._assign_styles(characters)

        meta_table = Table.grid(padding=(0, 1))
        meta_table.add_row("場景", scene.title)
        meta_table.add_row("調性", scene.tone)
        meta_table.add_row("回合上限", str(max_turns))
        meta_table.add_row("Ollama", ollama_url)

        cast = "\n".join(
            f"[{self._speaker_styles[character.id]}]{character.name}[/] ({character.id})"
            for character in characters
        )
        premise = scene.premise.strip()
        body = Table.grid(expand=True)
        body.add_row(meta_table)
        body.add_row("")
        body.add_row(Text(premise))
        body.add_row("")
        body.add_row(Text.from_markup(f"演員：{cast}"))

        self.console.print(
            Panel(
                body,
                title="AI Chatroom Theater",
                border_style="bold cyan",
            )
        )
        self.render_footer()

    def render_turn(
        self,
        *,
        event: TurnEvent,
        speaker_name: str,
        turn_index: int,
        max_turns: int,
    ) -> None:
        style = self._speaker_styles.get(event.speaker_id, "white")
        title = f"Turn {turn_index}/{max_turns} · {speaker_name}"
        self.console.print(
            Panel(
                Text(event.text, style=style),
                title=title,
                border_style=style,
            )
        )
        self.render_footer()

    def render_audience(self, text: str, label: str = "觀眾") -> None:
        self.console.print(
            Panel(
                Text(text, style="bold magenta"),
                title=label,
                border_style="magenta",
            )
        )
        self.render_footer()

    def render_status(self, message: str) -> None:
        self.console.print(Text(message, style="italic bright_black"))

    def render_footer(self) -> None:
        self.console.print(Text(FOOTER_TEXT, style="bold bright_black"))

    def render_end(self, message: str) -> None:
        self.console.print(
            Panel(
                Text(message, justify="center"),
                border_style="bright_black",
            )
        )

    def _assign_styles(self, characters: list[CharacterSpec]) -> None:
        palette = cycle(
            [
                "bright_blue",
                "bright_green",
                "bright_yellow",
                "bright_cyan",
                "bright_red",
                "bright_white",
            ]
        )
        for character in characters:
            self._speaker_styles[character.id] = next(palette)
