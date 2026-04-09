import Phaser from "phaser";

import { UI_FONT_FAMILY } from "../config";
import type { CharacterSummary } from "../types";

interface SpotView {
  container: Phaser.GameObjects.Container;
  body: Phaser.GameObjects.Graphics;
  glow: Phaser.GameObjects.Graphics;
  label: Phaser.GameObjects.Text;
  baseY: number;
  tween?: Phaser.Tweens.Tween;
  color: number;
}

const CHARACTER_COLORS: Record<string, number> = {
  "apple-fan": 0xe74c3c,
  "pc-master-race": 0x3498db,
  "linux-evangelist": 0x2ecc71,
  normie: 0xf39c12,
};

const SPOT_POSITIONS: Record<number, Array<{ x: number; y: number }>> = {
  2: [
    { x: 270, y: 250 },
    { x: 530, y: 250 },
  ],
  3: [
    { x: 210, y: 260 },
    { x: 400, y: 220 },
    { x: 590, y: 260 },
  ],
  4: [
    { x: 160, y: 260 },
    { x: 320, y: 220 },
    { x: 480, y: 220 },
    { x: 640, y: 260 },
  ],
};

export class CharacterSpots extends Phaser.GameObjects.Container {
  private readonly spots = new Map<string, SpotView>();

  constructor(scene: Phaser.Scene, characters: CharacterSummary[]) {
    super(scene, 0, 0);
    this.scene.add.existing(this);

    const positions = SPOT_POSITIONS[characters.length] ?? SPOT_POSITIONS[4];

    characters.forEach((character, index) => {
      const position = positions[index] ?? positions[positions.length - 1];
      const view = this.createSpot(character, position.x, position.y);
      this.spots.set(character.id, view);
      this.add(view.container);
    });
  }

  setActiveSpeaker(speakerId: string | null): void {
    for (const [id, spot] of this.spots.entries()) {
      const isActive = id === speakerId;
      this.drawSpot(spot, isActive);

      if (isActive) {
        if (!spot.tween) {
          spot.tween = this.scene.tweens.add({
            targets: spot.container,
            y: spot.baseY - 8,
            duration: 650,
            yoyo: true,
            repeat: -1,
            ease: "Sine.InOut",
          });
        }
        spot.label.setColor("#ffffff");
        spot.container.setAlpha(1);
      } else {
        spot.tween?.stop();
        spot.tween = undefined;
        spot.container.y = spot.baseY;
        spot.label.setColor("#d8def9");
        spot.container.setAlpha(0.88);
      }
    }
  }

  private createSpot(
    character: CharacterSummary,
    x: number,
    y: number,
  ): SpotView {
    const container = this.scene.add.container(x, y);
    const glow = this.scene.add.graphics();
    const body = this.scene.add.graphics();
    const label = this.scene.add.text(0, 58, character.name, {
      color: "#d8def9",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "14px",
      fontStyle: "bold",
      align: "center",
    });
    label.setOrigin(0.5, 0);

    const view: SpotView = {
      container,
      body,
      glow,
      label,
      baseY: y,
      color: CHARACTER_COLORS[character.id] ?? 0x95a5a6,
    };

    container.add([glow, body, label]);
    this.drawSpot(view, false);
    return view;
  }

  private drawSpot(view: SpotView, active: boolean): void {
    view.glow.clear();
    view.body.clear();

    if (active) {
      view.glow.lineStyle(4, 0xffffff, 0.9);
      view.glow.strokeRoundedRect(-34, -46, 68, 88, 14);
      view.glow.fillStyle(0xffffff, 0.08);
      view.glow.fillRoundedRect(-34, -46, 68, 88, 14);
    }

    view.body.fillStyle(0x081020, 0.36);
    view.body.fillEllipse(0, 44, 78, 20);

    view.body.fillStyle(view.color, 1);
    view.body.fillRoundedRect(-30, -40, 60, 80, 12);
    view.body.lineStyle(2, active ? 0xffffff : 0x0f1633, 0.95);
    view.body.strokeRoundedRect(-30, -40, 60, 80, 12);

    view.body.fillStyle(0xffffff, 0.1);
    view.body.fillRoundedRect(-20, -30, 16, 48, 8);
  }
}
