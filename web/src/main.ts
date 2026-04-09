import Phaser from "phaser";

import gameConfig from "./config";

const root = document.getElementById("game");

if (!root) {
  throw new Error("Missing #game mount element.");
}

document.body.style.margin = "0";
document.body.style.minHeight = "100vh";
document.body.style.display = "grid";
document.body.style.placeItems = "center";
document.body.style.background =
  "radial-gradient(circle at top, #2a2f6a 0%, #12152d 45%, #060711 100%)";
document.body.style.fontFamily =
  '"Noto Sans TC", "Microsoft JhengHei", sans-serif';
document.body.style.overflow = "hidden";

root.style.position = "relative";
root.style.width = "min(100vw, 106.666vh)";
root.style.aspectRatio = "4 / 3";
root.style.maxHeight = "100vh";
root.style.maxWidth = "100vw";
root.style.display = "grid";
root.style.placeItems = "center";
root.style.boxShadow = "0 18px 48px rgba(0, 0, 0, 0.45)";

const game = new Phaser.Game(gameConfig);

window.addEventListener("beforeunload", () => {
  game.destroy(true);
});
