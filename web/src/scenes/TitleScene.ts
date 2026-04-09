import Phaser from "phaser";

import { GAME_HEIGHT, GAME_WIDTH, UI_FONT_FAMILY } from "../config";
import type {
  CharacterSummary,
  CreateSessionResponse,
  SceneSummary,
} from "../types";

export class TitleScene extends Phaser.Scene {
  private scenes: SceneSummary[] = [];

  private characters: CharacterSummary[] = [];

  private statusText!: Phaser.GameObjects.Text;

  private promptText!: Phaser.GameObjects.Text;

  private readonly optionTexts: Phaser.GameObjects.Text[] = [];

  private isCreatingSession = false;

  constructor() {
    super("TitleScene");
  }

  create(): void {
    this.drawBackdrop();

    this.add.text(GAME_WIDTH / 2, 80, "AI 劇場", {
      color: "#fff7d6",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "44px",
      fontStyle: "bold",
      stroke: "#283159",
      strokeThickness: 6,
    }).setOrigin(0.5);

    this.add.text(GAME_WIDTH / 2, 130, "16-bit 對話劇場選單", {
      color: "#d1d8ff",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "18px",
    }).setOrigin(0.5);

    this.statusText = this.add.text(48, 176, "讀取場景與角色資料中...", {
      color: "#d1d8ff",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "18px",
    });

    this.promptText = this.add.text(
      GAME_WIDTH / 2,
      GAME_HEIGHT - 42,
      "選擇場景開始",
      {
        color: "#f8d66d",
        fontFamily: UI_FONT_FAMILY,
        fontSize: "18px",
        fontStyle: "bold",
      },
    );
    this.promptText.setOrigin(0.5);

    this.tweens.add({
      targets: this.promptText,
      alpha: 0.35,
      duration: 700,
      yoyo: true,
      repeat: -1,
    });

    void this.loadData();
  }

  private async loadData(): Promise<void> {
    try {
      const [scenes, characters] = await Promise.all([
        this.fetchJson<SceneSummary[]>("/api/scenes"),
        this.fetchJson<CharacterSummary[]>("/api/characters"),
      ]);

      this.scenes = scenes;
      this.characters = characters;
      this.statusText.setText("點擊任一場景即可開演。");
      this.renderSceneOptions();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "無法取得場景資料。";
      this.statusText.setText(`載入失敗：${message}`);
      this.statusText.setColor("#ffb3b8");
    }
  }

  private renderSceneOptions(): void {
    this.optionTexts.forEach((text) => text.destroy());
    this.optionTexts.length = 0;

    this.scenes.forEach((scene, index) => {
      const y = 220 + index * 96;
      const title = this.add.text(72, y, `▶ ${scene.title}`, {
        color: "#ffffff",
        fontFamily: UI_FONT_FAMILY,
        fontSize: "28px",
        fontStyle: "bold",
      });
      const detail = this.add.text(
        96,
        y + 36,
        `${scene.id} · ${scene.tone}\n${scene.premise.replace(/\s+/g, " ").trim()}`,
        {
          color: "#c9cff8",
          fontFamily: UI_FONT_FAMILY,
          fontSize: "14px",
          lineSpacing: 6,
          wordWrap: { width: 620, useAdvancedWrap: true },
        },
      );

      title.setInteractive({ useHandCursor: true });
      detail.setInteractive({ useHandCursor: true });

      const activate = (): void => {
        if (this.isCreatingSession) {
          return;
        }
        this.highlightOption(title, detail, true);
      };
      const deactivate = (): void => {
        if (this.isCreatingSession) {
          return;
        }
        this.highlightOption(title, detail, false);
      };
      const choose = (): void => {
        if (this.isCreatingSession) {
          return;
        }
        void this.createSession(scene, title, detail);
      };

      title.on("pointerover", activate);
      title.on("pointerout", deactivate);
      detail.on("pointerover", activate);
      detail.on("pointerout", deactivate);
      title.on("pointerdown", choose);
      detail.on("pointerdown", choose);

      this.optionTexts.push(title, detail);
    });
  }

  private highlightOption(
    title: Phaser.GameObjects.Text,
    detail: Phaser.GameObjects.Text,
    active: boolean,
  ): void {
    title.setColor(active ? "#f8d66d" : "#ffffff");
    detail.setColor(active ? "#fff0bf" : "#c9cff8");
  }

  private async createSession(
    scene: SceneSummary,
    title: Phaser.GameObjects.Text,
    detail: Phaser.GameObjects.Text,
  ): Promise<void> {
    this.isCreatingSession = true;
    this.highlightOption(title, detail, true);
    this.statusText.setColor("#fff7d6");
    this.statusText.setText(`建立場景「${scene.title}」中...`);

    try {
      const payload = await this.fetchJson<CreateSessionResponse>("/api/sessions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          scene_id: scene.id,
          character_ids: this.characters.map((character) => character.id),
          max_turns: 20,
        }),
      });

      this.scene.start("TheaterScene", payload);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "建立 session 失敗。";
      this.statusText.setText(`建立失敗：${message}`);
      this.statusText.setColor("#ffb3b8");
      this.isCreatingSession = false;
      this.highlightOption(title, detail, false);
    }
  }

  private async fetchJson<T>(
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<T> {
    const response = await fetch(input, init);

    if (!response.ok) {
      let message = `${response.status} ${response.statusText}`;

      try {
        const errorPayload = (await response.json()) as { detail?: string };
        if (errorPayload.detail) {
          message = errorPayload.detail;
        }
      } catch {
        // Keep the HTTP status text when the backend does not return JSON.
      }

      throw new Error(message);
    }

    return (await response.json()) as T;
  }

  private drawBackdrop(): void {
    const background = this.add.graphics();

    for (let index = 0; index < 12; index += 1) {
      const ratio = index / 11;
      const color = Phaser.Display.Color.Interpolate.ColorWithColor(
        Phaser.Display.Color.HexStringToColor("#0b1025"),
        Phaser.Display.Color.HexStringToColor("#2c2f63"),
        11,
        index,
      );
      background.fillStyle(
        Phaser.Display.Color.GetColor(color.r, color.g, color.b),
        1,
      );
      background.fillRect(0, (GAME_HEIGHT / 12) * index, GAME_WIDTH, GAME_HEIGHT / 12 + 1);
    }

    for (let index = 0; index < 42; index += 1) {
      const starX = 18 + ((index * 149) % (GAME_WIDTH - 36));
      const starY = 18 + ((index * 61) % 130);
      background.fillStyle(0xffffff, index % 3 === 0 ? 0.45 : 0.2);
      background.fillRect(starX, starY, 2, 2);
    }

    const frame = this.add.graphics();
    frame.lineStyle(4, 0x6d78d9, 0.75);
    frame.strokeRoundedRect(28, 28, GAME_WIDTH - 56, GAME_HEIGHT - 56, 18);
  }
}
