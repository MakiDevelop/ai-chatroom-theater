import Phaser from "phaser";

import { TheaterScene } from "./scenes/TheaterScene";
import { TitleScene } from "./scenes/TitleScene";

export const GAME_WIDTH = 800;
export const GAME_HEIGHT = 600;
export const DIALOG_BOX_Y = 420;
export const DIALOG_BOX_WIDTH = 760;
export const DIALOG_BOX_HEIGHT = 160;
export const UI_FONT_FAMILY = '"Noto Sans TC", "Microsoft JhengHei", sans-serif';

const gameConfig: Phaser.Types.Core.GameConfig = {
  type: Phaser.CANVAS,
  parent: "game",
  width: GAME_WIDTH,
  height: GAME_HEIGHT,
  backgroundColor: "#1a1a2e",
  scene: [TitleScene, TheaterScene],
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: GAME_WIDTH,
    height: GAME_HEIGHT,
  },
  render: {
    antialias: false,
    pixelArt: true,
    roundPixels: true,
  },
};

export default gameConfig;
