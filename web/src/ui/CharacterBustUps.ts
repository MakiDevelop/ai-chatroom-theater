import Phaser from "phaser";

import type { CharacterEmotion, CharacterSummary } from "../types";

const SPEAKER_X = 160;
const SPEAKER_Y = 200;
const SPEAKER_SIZE = 280;
const SPEAKER_START_X = -200;
const TARGET_X = 640;
const TARGET_Y = 220;
const TARGET_SIZE = 200;

export class CharacterBustUps {
  private readonly scene: Phaser.Scene;

  private readonly characters: Map<string, CharacterSummary>;

  private speakerSprite: Phaser.GameObjects.Image | null = null;

  private targetSprite: Phaser.GameObjects.Image | null = null;

  private readonly speakerGlow: Phaser.GameObjects.Graphics;

  private currentSpeakerId: string | null = null;

  private currentTargetId: string | null = null;

  constructor(scene: Phaser.Scene, characters: CharacterSummary[]) {
    this.scene = scene;
    this.characters = new Map(characters.map((character) => [character.id, character]));
    this.speakerGlow = this.scene.add.graphics();
    this.speakerGlow.setDepth(3);
    this.speakerGlow.setVisible(false);
    this.redrawSpeakerGlow();
  }

  showDialogue(
    speakerId: string,
    targetId: string | null,
    speakerEmotion: CharacterEmotion,
    targetEmotion: CharacterEmotion,
  ): void {
    if (!this.characters.has(speakerId)) {
      this.clear();
      return;
    }

    this.showSpeaker(speakerId, speakerEmotion);

    if (targetId && this.characters.has(targetId) && targetId !== speakerId) {
      this.showTarget(targetId, targetEmotion);
    } else {
      this.hideTarget();
    }
  }

  clear(): void {
    this.fadeOutSprite(this.speakerSprite, () => {
      this.speakerSprite = null;
    });
    this.fadeOutSprite(this.targetSprite, () => {
      this.targetSprite = null;
    });
    this.scene.tweens.killTweensOf(this.speakerGlow);
    this.scene.tweens.add({
      targets: this.speakerGlow,
      alpha: 0,
      duration: 160,
      ease: "Sine.Out",
      onComplete: () => {
        this.speakerGlow.setVisible(false);
      },
    });
    this.currentSpeakerId = null;
    this.currentTargetId = null;
  }

  private showSpeaker(speakerId: string, emotion: CharacterEmotion): void {
    const textureKey = this.getTextureKey(speakerId, emotion);

    if (this.currentSpeakerId === speakerId && this.speakerSprite) {
      this.speakerSprite.setTexture(textureKey);
      this.speakerSprite.setVisible(true);
      this.speakerSprite.setAlpha(1);
      this.speakerSprite.setPosition(SPEAKER_X, SPEAKER_Y);
      this.speakerGlow.setPosition(SPEAKER_X, SPEAKER_Y);
      this.speakerGlow.setVisible(true);
      this.speakerGlow.setAlpha(1);
      return;
    }

    const outgoingSpeaker = this.speakerSprite;
    if (outgoingSpeaker) {
      this.fadeOutSprite(outgoingSpeaker, () => {
        if (this.speakerSprite === outgoingSpeaker) {
          this.speakerSprite = null;
        }
      });
    }

    const speakerSprite = this.scene.add.image(SPEAKER_START_X, SPEAKER_Y, textureKey);
    speakerSprite.setOrigin(0.5, 0.5);
    speakerSprite.setDisplaySize(SPEAKER_SIZE, SPEAKER_SIZE);
    speakerSprite.setAlpha(0);
    speakerSprite.setDepth(4);

    this.speakerSprite = speakerSprite;
    this.currentSpeakerId = speakerId;

    this.scene.tweens.killTweensOf(this.speakerGlow);
    this.speakerGlow.setPosition(SPEAKER_START_X, SPEAKER_Y);
    this.speakerGlow.setVisible(true);
    this.speakerGlow.setAlpha(0);

    this.scene.tweens.add({
      targets: [speakerSprite, this.speakerGlow],
      x: SPEAKER_X,
      alpha: 1,
      duration: 300,
      ease: "Back.Out",
    });
  }

  private showTarget(targetId: string, emotion: CharacterEmotion): void {
    const textureKey = this.getTextureKey(targetId, emotion);

    if (!this.targetSprite) {
      this.targetSprite = this.scene.add.image(TARGET_X, TARGET_Y, textureKey);
      this.targetSprite.setOrigin(0.5, 0.5);
      this.targetSprite.setDisplaySize(TARGET_SIZE, TARGET_SIZE);
      this.targetSprite.setDepth(2);
      this.targetSprite.setAlpha(0);
    } else {
      this.scene.tweens.killTweensOf(this.targetSprite);
      this.targetSprite.setTexture(textureKey);
    }

    this.targetSprite.setVisible(true);
    this.targetSprite.setPosition(TARGET_X, TARGET_Y);
    this.targetSprite.setDisplaySize(TARGET_SIZE, TARGET_SIZE);

    if (this.currentTargetId !== targetId) {
      this.targetSprite.setScale(0.96);
      this.scene.tweens.add({
        targets: this.targetSprite,
        alpha: 0.85,
        scaleX: 1,
        scaleY: 1,
        duration: 220,
        ease: "Sine.Out",
      });
    } else {
      this.targetSprite.setAlpha(0.85);
      this.targetSprite.setScale(1);
    }

    this.currentTargetId = targetId;
  }

  private hideTarget(): void {
    if (!this.targetSprite) {
      this.currentTargetId = null;
      return;
    }

    this.scene.tweens.killTweensOf(this.targetSprite);
    this.scene.tweens.add({
      targets: this.targetSprite,
      alpha: 0,
      duration: 180,
      ease: "Sine.Out",
      onComplete: () => {
        this.targetSprite?.setVisible(false);
      },
    });
    this.currentTargetId = null;
  }

  private fadeOutSprite(
    sprite: Phaser.GameObjects.Image | null,
    onComplete: () => void,
  ): void {
    if (!sprite) {
      onComplete();
      return;
    }

    this.scene.tweens.killTweensOf(sprite);
    this.scene.tweens.add({
      targets: sprite,
      alpha: 0,
      duration: 200,
      ease: "Sine.Out",
      onComplete: () => {
        sprite.destroy();
        onComplete();
      },
    });
  }

  private redrawSpeakerGlow(): void {
    this.speakerGlow.clear();
    this.speakerGlow.lineStyle(4, 0xffffff, 0.88);
    this.speakerGlow.strokeRoundedRect(-150, -150, 300, 300, 28);
    this.speakerGlow.fillStyle(0xffffff, 0.06);
    this.speakerGlow.fillRoundedRect(-150, -150, 300, 300, 28);
  }

  private getTextureKey(characterId: string, emotion: CharacterEmotion): string {
    const textureKey = `sprite-${characterId}-${emotion}`;

    if (this.scene.textures.exists(textureKey)) {
      return textureKey;
    }

    return `sprite-${characterId}-neutral`;
  }
}
