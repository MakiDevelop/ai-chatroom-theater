import Phaser from "phaser";

import { UI_FONT_FAMILY } from "../config";
import type { DialogTone } from "../types";

interface DialogMessageOptions {
  speakerName: string;
  text: string;
  turnIndex?: number;
  maxTurns?: number;
  tone?: DialogTone;
  instant?: boolean;
}

export class DialogBox extends Phaser.GameObjects.Container {
  private readonly widthPx: number;

  private readonly heightPx: number;

  private readonly panel: Phaser.GameObjects.Graphics;

  private readonly namePlate: Phaser.GameObjects.Graphics;

  private readonly clickZone: Phaser.GameObjects.Zone;

  private readonly speakerText: Phaser.GameObjects.Text;

  private readonly bodyText: Phaser.GameObjects.Text;

  private readonly progressText: Phaser.GameObjects.Text;

  private typeEvent?: Phaser.Time.TimerEvent;

  private currentFullText = "";

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    width: number,
    height: number,
  ) {
    super(scene, x, y);
    this.widthPx = width;
    this.heightPx = height;

    this.panel = scene.add.graphics();
    this.namePlate = scene.add.graphics();
    this.clickZone = scene.add
      .zone(width / 2, height / 2, width, height)
      .setOrigin(0.5)
      .setInteractive({ useHandCursor: true });
    this.clickZone.on("pointerdown", () => {
      this.revealAll();
    });

    this.speakerText = scene.add.text(30, -2, "", {
      color: "#ffffff",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "18px",
      fontStyle: "bold",
    });

    this.bodyText = scene.add.text(24, 30, "", {
      color: "#ffffff",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "20px",
      lineSpacing: 8,
      wordWrap: { width: 712, useAdvancedWrap: true },
    });

    this.progressText = scene.add.text(width - 18, height - 24, "Turn 0/0", {
      color: "#d5d9ff",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "14px",
      fontStyle: "bold",
    });
    this.progressText.setOrigin(1, 1);

    this.add([
      this.panel,
      this.namePlate,
      this.clickZone,
      this.speakerText,
      this.bodyText,
      this.progressText,
    ]);
    this.redrawPanel();
    this.scene.add.existing(this);
  }

  showMessage(options: DialogMessageOptions): void {
    this.stopTyping();
    this.currentFullText = options.text;
    this.configureTone(options.tone ?? "speaker");
    this.bodyText.setPosition(24, 30);
    this.bodyText.setOrigin(0, 0);
    this.bodyText.setAlign("left");
    this.updateNamePlate(options.speakerName);

    if (
      typeof options.turnIndex === "number" &&
      typeof options.maxTurns === "number"
    ) {
      this.progressText.setText(`Turn ${options.turnIndex}/${options.maxTurns}`);
    }

    if (options.instant || options.text.length === 0) {
      this.bodyText.setText(options.text);
      return;
    }

    const characters = Array.from(options.text);
    let index = 0;
    this.bodyText.setText("");

    this.typeEvent = this.scene.time.addEvent({
      delay: 30,
      repeat: Math.max(characters.length - 1, 0),
      callback: () => {
        index += 1;
        this.bodyText.setText(characters.slice(0, index).join(""));
      },
    });
  }

  showEnding(turnIndex?: number, maxTurns?: number): void {
    this.stopTyping();
    this.currentFullText = "— 完 —";
    this.configureTone("system");
    this.updateNamePlate("");
    this.bodyText.setPosition(this.widthPx / 2, 58);
    this.bodyText.setOrigin(0.5, 0);
    this.bodyText.setAlign("center");
    this.bodyText.setText(this.currentFullText);

    if (typeof turnIndex === "number" && typeof maxTurns === "number") {
      this.progressText.setText(`Turn ${turnIndex}/${maxTurns}`);
    }
  }

  revealAll(): void {
    if (!this.typeEvent) {
      return;
    }

    this.stopTyping();
    this.bodyText.setText(this.currentFullText);
  }

  private stopTyping(): void {
    if (!this.typeEvent) {
      return;
    }

    this.typeEvent.remove(false);
    this.typeEvent = undefined;
  }

  private redrawPanel(): void {
    this.panel.clear();
    this.panel.fillStyle(0x0a0a3a, 0.85);
    this.panel.fillRoundedRect(0, 0, this.widthPx, this.heightPx, 14);
    this.panel.lineStyle(2, 0x4444aa, 1);
    this.panel.strokeRoundedRect(0, 0, this.widthPx, this.heightPx, 14);
  }

  private updateNamePlate(name: string): void {
    this.namePlate.clear();

    if (!name) {
      this.speakerText.setText("");
      return;
    }

    this.speakerText.setText(name);
    const plateWidth = Math.max(96, this.speakerText.width + 28);
    this.namePlate.fillStyle(0x0a0a3a, 0.96);
    this.namePlate.fillRoundedRect(16, -12, plateWidth, 32, 10);
    this.namePlate.lineStyle(2, 0x6d78d9, 1);
    this.namePlate.strokeRoundedRect(16, -12, plateWidth, 32, 10);
  }

  private configureTone(tone: DialogTone): void {
    switch (tone) {
      case "audience":
        this.bodyText.setColor("#ffe8a3");
        this.speakerText.setColor("#ffe8a3");
        break;
      case "error":
        this.bodyText.setColor("#ff9aa2");
        this.speakerText.setColor("#ffb3b8");
        break;
      case "system":
        this.bodyText.setColor("#d2d9ff");
        this.speakerText.setColor("#d2d9ff");
        break;
      default:
        this.bodyText.setColor("#ffffff");
        this.speakerText.setColor("#ffffff");
        break;
    }
  }
}
