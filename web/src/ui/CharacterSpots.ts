import Phaser from "phaser";

import { UI_FONT_FAMILY } from "../config";
import type { CharacterEmotion, CharacterSummary } from "../types";

interface SpotView {
  container: Phaser.GameObjects.Container;
  shadow: Phaser.GameObjects.Graphics;
  sprite: Phaser.GameObjects.Image;
  glow: Phaser.GameObjects.Graphics;
  label: Phaser.GameObjects.Text;
  baseY: number;
  tween?: Phaser.Tweens.Tween;
  currentEmotion: CharacterEmotion;
}

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
      this.drawGlow(spot, isActive);

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

  setEmotion(characterId: string, emotion: CharacterEmotion): void {
    const spot = this.spots.get(characterId);
    if (!spot || spot.currentEmotion === emotion) {
      return;
    }

    const textureKey = `sprite-${characterId}-${emotion}`;
    if (!this.scene.textures.exists(textureKey)) {
      return;
    }

    spot.sprite.setTexture(textureKey);
    spot.currentEmotion = emotion;
  }

  private createSpot(
    character: CharacterSummary,
    x: number,
    y: number,
  ): SpotView {
    const container = this.scene.add.container(x, y);
    const glow = this.scene.add.graphics();
    const shadow = this.scene.add.graphics();
    shadow.fillStyle(0x081020, 0.36);
    shadow.fillEllipse(0, 44, 78, 20);

    const sprite = this.scene.add.image(0, 0, `sprite-${character.id}-neutral`);
    sprite.setDisplaySize(80, 80);
    sprite.setOrigin(0.5, 0.5);
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
      shadow,
      sprite,
      glow,
      label,
      baseY: y,
      currentEmotion: "neutral",
    };

    container.add([shadow, glow, sprite, label]);
    this.drawGlow(view, false);
    return view;
  }

  private drawGlow(view: SpotView, active: boolean): void {
    view.glow.clear();

    if (active) {
      view.glow.lineStyle(4, 0xffffff, 0.9);
      view.glow.strokeRoundedRect(-44, -44, 88, 88, 16);
      view.glow.fillStyle(0xffffff, 0.08);
      view.glow.fillRoundedRect(-44, -44, 88, 88, 16);
    }
  }
}
