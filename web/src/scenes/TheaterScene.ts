import Phaser from "phaser";

import {
  DIALOG_BOX_HEIGHT,
  DIALOG_BOX_WIDTH,
  DIALOG_BOX_Y,
  GAME_HEIGHT,
  GAME_WIDTH,
  UI_FONT_FAMILY,
} from "../config";
import { WebSocketClient } from "../network/WebSocketClient";
import type {
  AudienceMessage,
  CharacterEmotion,
  ConnectionErrorEvent,
  ErrorMessage,
  ReconnectEvent,
  SceneEndMessage,
  TheaterSceneData,
  TurnMessage,
} from "../types";
import { CharacterBustUps } from "../ui/CharacterBustUps";
import { DialogBox } from "../ui/DialogBox";

const AUDIENCE_OVERLAY_ID = "audience-overlay";
const CHARACTER_IDS = [
  "apple-fan",
  "pc-master-race",
  "linux-evangelist",
  "normie",
] as const;
const CHARACTER_EMOTIONS: CharacterEmotion[] = [
  "neutral",
  "happy",
  "angry",
  "sad",
  "joy",
];
const ANGRY_KEYWORDS = [
  "垃圾",
  "爛",
  "嗆",
  "盤子",
  "藍屏",
  "閉嘴",
  "滾",
  "廢物",
  "不要臉",
];
const JOY_KEYWORDS = ["哈哈", "笑死", "xd", "haha", "😂", "😆", "lol", "wwww"];
const HAPPY_KEYWORDS = ["讚", "好", "棒", "厲害", "同意", "有道理", "沒錯", "👍", "！"];
const SAD_KEYWORDS = ["唉", "算了", "無奈", "可惜", "嘆", "沒辦法", "qq", "😢"];

function inferCharacterEmotion(text: string): CharacterEmotion {
  const normalizedText = text.toLowerCase();

  if (ANGRY_KEYWORDS.some((keyword) => normalizedText.includes(keyword.toLowerCase()))) {
    return "angry";
  }

  if (JOY_KEYWORDS.some((keyword) => normalizedText.includes(keyword.toLowerCase()))) {
    return "joy";
  }

  if (HAPPY_KEYWORDS.some((keyword) => normalizedText.includes(keyword.toLowerCase()))) {
    return "happy";
  }

  if (SAD_KEYWORDS.some((keyword) => normalizedText.includes(keyword.toLowerCase()))) {
    return "sad";
  }

  return "neutral";
}

function inferTargetEmotion(speakerEmotion: CharacterEmotion): CharacterEmotion {
  if (speakerEmotion === "angry") {
    return "sad";
  }

  if (speakerEmotion === "joy") {
    return "happy";
  }

  return "neutral";
}

export class TheaterScene extends Phaser.Scene {
  private sessionData!: TheaterSceneData;

  private dialogBox!: DialogBox;

  private bustUps!: CharacterBustUps;

  private client: WebSocketClient | null = null;

  private connectionText!: Phaser.GameObjects.Text;

  private sceneTitleText!: Phaser.GameObjects.Text;

  private sceneSubtitleText!: Phaser.GameObjects.Text;

  private audienceButton!: Phaser.GameObjects.Text;

  private returnButton!: Phaser.GameObjects.Text;

  private audienceOverlay: HTMLDivElement | null = null;

  private audienceInput: HTMLInputElement | null = null;

  private lastTurnIndex = 0;

  private maxTurns = 0;

  private sceneEnded = false;

  constructor() {
    super("TheaterScene");
  }

  init(data: TheaterSceneData): void {
    this.sessionData = data;
    this.lastTurnIndex = 0;
    this.maxTurns = 0;
    this.sceneEnded = false;
  }

  preload(): void {
    for (const id of CHARACTER_IDS) {
      for (const emotion of CHARACTER_EMOTIONS) {
        this.load.image(`sprite-${id}-${emotion}`, `/sprites/${id}-${emotion}.png`);
      }
    }
  }

  create(): void {
    if (!this.sessionData?.session_id) {
      this.scene.start("TitleScene");
      return;
    }

    this.drawBackdrop();
    this.createHeader();

    this.bustUps = new CharacterBustUps(this, this.sessionData.characters);
    this.dialogBox = new DialogBox(
      this,
      (GAME_WIDTH - DIALOG_BOX_WIDTH) / 2,
      DIALOG_BOX_Y,
      DIALOG_BOX_WIDTH,
      DIALOG_BOX_HEIGHT,
    );
    this.dialogBox.showMessage({
      speakerName: "系統",
      text: "連線中...",
      tone: "system",
      instant: true,
      turnIndex: 0,
      maxTurns: 0,
    });

    this.connectionText = this.add.text(22, 396, "", {
      color: "#ffe8a3",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "14px",
      fontStyle: "bold",
    });

    this.audienceButton = this.createTextButton(694, 398, "插話", () => {
      this.openAudienceOverlay();
    });

    this.returnButton = this.createTextButton(694, 398, "回到標題", () => {
      this.scene.start("TitleScene");
    });
    this.returnButton.setVisible(false);

    this.setupAudienceOverlay();
    this.registerKeyboardShortcuts();
    this.connectSocket();

    this.events.once(Phaser.Scenes.Events.SHUTDOWN, this.teardown, this);
    this.events.once(Phaser.Scenes.Events.DESTROY, this.teardown, this);
  }

  private drawBackdrop(): void {
    const backdrop = this.add.graphics();

    for (let index = 0; index < 16; index += 1) {
      const color = Phaser.Display.Color.Interpolate.ColorWithColor(
        Phaser.Display.Color.HexStringToColor("#060c17"),
        Phaser.Display.Color.HexStringToColor("#182642"),
        15,
        index,
      );
      backdrop.fillStyle(Phaser.Display.Color.GetColor(color.r, color.g, color.b), 1);
      backdrop.fillRect(0, index * 38, GAME_WIDTH, 40);
    }

    const rays = this.add.graphics();
    const rayOriginX = GAME_WIDTH / 2;
    const rayOriginY = 216;

    rays.lineStyle(3, 0x9aaed8, 0.05);
    for (let index = 0; index < 18; index += 1) {
      const angle = Phaser.Math.DegToRad(-74 + index * 8.7);
      const x = rayOriginX + Math.cos(angle) * 560;
      const y = rayOriginY + Math.sin(angle) * 560;
      rays.beginPath();
      rays.moveTo(rayOriginX, rayOriginY);
      rays.lineTo(x, y);
      rays.strokePath();
    }

    const lowerShade = this.add.graphics();
    lowerShade.fillStyle(0x050913, 0.42);
    lowerShade.fillRect(0, 298, GAME_WIDTH, 120);
  }

  private createHeader(): void {
    this.sceneTitleText = this.add.text(24, 18, this.sessionData.scene.title, {
      color: "#fff7d6",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "24px",
      fontStyle: "bold",
      stroke: "#17284f",
      strokeThickness: 5,
    });

    this.sceneSubtitleText = this.add.text(
      24,
      56,
      this.sessionData.scene.premise.replace(/\s+/g, " ").trim(),
      {
        color: "#cfd8ff",
        fontFamily: UI_FONT_FAMILY,
        fontSize: "14px",
        wordWrap: { width: 560, useAdvancedWrap: true },
      },
    );
  }

  private connectSocket(): void {
    this.client?.close();
    this.client = new WebSocketClient();

    this.client.on("open", () => {
      this.connectionText.setText("");
      this.dialogBox.showMessage({
        speakerName: "系統",
        text: "演出開始。",
        tone: "system",
        instant: true,
        turnIndex: this.lastTurnIndex,
        maxTurns: this.maxTurns,
      });
      this.client?.send({ type: "start" });
    });

    this.client.on("turn", (payload) => {
      this.handleTurn(payload as TurnMessage);
    });

    this.client.on("audience", (payload) => {
      this.handleAudience(payload as AudienceMessage);
    });

    this.client.on("scene_end", (payload) => {
      this.handleSceneEnd(payload as SceneEndMessage);
    });

    this.client.on("error", (payload) => {
      this.handleError(payload as ErrorMessage);
    });

    this.client.on("reconnecting", (payload) => {
      const reconnect = payload as ReconnectEvent;
      this.connectionText.setText(
        `重新連線中 ${reconnect.attempt}/${reconnect.maxAttempts}...`,
      );
    });

    this.client.on("connection_lost", () => {
      if (!this.sceneEnded) {
        this.connectionText.setText("連線中斷");
      }
    });

    this.client.on("connection_error", (payload) => {
      const error = payload as ConnectionErrorEvent;
      this.connectionText.setText(error.message);
    });

    this.client.connect(this.sessionData.session_id);
  }

  private handleTurn(message: TurnMessage): void {
    this.lastTurnIndex = message.turn_index;
    this.maxTurns = message.max_turns;
    const speakerEmotion = inferCharacterEmotion(message.text);
    const targetId = message.targets[0] ?? null;
    const targetEmotion = inferTargetEmotion(speakerEmotion);

    this.bustUps.showDialogue(
      message.speaker_id,
      targetId,
      speakerEmotion,
      targetEmotion,
    );
    this.dialogBox.showMessage({
      speakerName: message.speaker_name,
      text: message.text,
      turnIndex: message.turn_index,
      maxTurns: message.max_turns,
    });
  }

  private handleAudience(message: AudienceMessage): void {
    this.bustUps.clear();
    this.dialogBox.showMessage({
      speakerName: "觀眾",
      text: message.text,
      tone: "audience",
      turnIndex: this.lastTurnIndex,
      maxTurns: this.maxTurns,
    });
  }

  private handleError(message: ErrorMessage): void {
    this.bustUps.clear();
    this.dialogBox.showMessage({
      speakerName: "系統",
      text: message.message,
      tone: "error",
      instant: true,
      turnIndex: this.lastTurnIndex,
      maxTurns: this.maxTurns,
    });
  }

  private handleSceneEnd(_message: SceneEndMessage): void {
    this.sceneEnded = true;
    this.bustUps.clear();
    this.connectionText.setText("");
    this.audienceButton.setVisible(false);
    this.returnButton.setVisible(true);
    this.dialogBox.showEnding(this.lastTurnIndex, this.maxTurns);
    this.client?.close();
  }

  private registerKeyboardShortcuts(): void {
    this.input.keyboard?.on("keydown-ENTER", () => {
      if (!this.sceneEnded) {
        this.openAudienceOverlay();
      }
    });
  }

  private openAudienceOverlay(): void {
    if (this.sceneEnded || !this.audienceOverlay || !this.audienceInput) {
      return;
    }

    this.audienceOverlay.style.display = "flex";
    this.audienceInput.value = "";
    this.input.keyboard!.enabled = false;
    window.setTimeout(() => this.audienceInput?.focus(), 0);
  }

  private hideAudienceOverlay(): void {
    if (!this.audienceOverlay) {
      return;
    }

    this.audienceOverlay.style.display = "none";

    if (this.input.keyboard) {
      this.input.keyboard.enabled = true;
    }
  }

  private setupAudienceOverlay(): void {
    const root = document.getElementById("game");

    if (!root) {
      return;
    }

    this.audienceOverlay?.remove();

    const overlay = document.createElement("div");
    overlay.id = AUDIENCE_OVERLAY_ID;
    overlay.style.position = "absolute";
    overlay.style.inset = "0";
    overlay.style.display = "none";
    overlay.style.alignItems = "flex-end";
    overlay.style.justifyContent = "center";
    overlay.style.padding = "24px";
    overlay.style.background = "rgba(6, 9, 18, 0.18)";
    overlay.style.zIndex = "20";

    const form = document.createElement("form");
    form.style.width = "min(560px, calc(100% - 32px))";
    form.style.display = "grid";
    form.style.gridTemplateColumns = "1fr auto";
    form.style.gap = "12px";
    form.style.padding = "14px";
    form.style.border = "2px solid rgba(135, 155, 255, 0.92)";
    form.style.borderRadius = "14px";
    form.style.background = "rgba(10, 10, 58, 0.96)";
    form.style.boxShadow = "0 12px 28px rgba(0, 0, 0, 0.35)";

    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "觀眾插話...";
    input.maxLength = 200;
    input.style.height = "44px";
    input.style.padding = "0 14px";
    input.style.border = "2px solid rgba(68, 68, 170, 0.9)";
    input.style.borderRadius = "10px";
    input.style.background = "#f7f8ff";
    input.style.color = "#10152a";
    input.style.fontSize = "16px";
    input.style.fontFamily = UI_FONT_FAMILY;
    input.style.outline = "none";

    const sendButton = document.createElement("button");
    sendButton.type = "submit";
    sendButton.textContent = "送出";
    sendButton.style.height = "44px";
    sendButton.style.padding = "0 18px";
    sendButton.style.border = "0";
    sendButton.style.borderRadius = "10px";
    sendButton.style.background = "#f8d66d";
    sendButton.style.color = "#18213f";
    sendButton.style.fontFamily = UI_FONT_FAMILY;
    sendButton.style.fontSize = "16px";
    sendButton.style.fontWeight = "700";
    sendButton.style.cursor = "pointer";

    const hint = document.createElement("div");
    hint.textContent = "Enter 送出 · Esc 取消";
    hint.style.gridColumn = "1 / -1";
    hint.style.color = "#d2d9ff";
    hint.style.fontFamily = UI_FONT_FAMILY;
    hint.style.fontSize = "13px";

    form.append(input, sendButton, hint);
    overlay.appendChild(form);
    root.appendChild(overlay);

    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        this.hideAudienceOverlay();
      }
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        this.hideAudienceOverlay();
      }
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = input.value.trim();

      if (!text) {
        return;
      }

      this.client?.send({ type: "audience", text });
      this.hideAudienceOverlay();
    });

    this.audienceOverlay = overlay;
    this.audienceInput = input;
  }

  private createTextButton(
    x: number,
    y: number,
    label: string,
    onClick: () => void,
  ): Phaser.GameObjects.Text {
    const button = this.add.text(x, y, label, {
      color: "#fff7d6",
      backgroundColor: "#101746",
      fontFamily: UI_FONT_FAMILY,
      fontSize: "16px",
      fontStyle: "bold",
      padding: { left: 14, right: 14, top: 8, bottom: 8 },
    });
    button.setOrigin(1, 0.5);
    button.setInteractive({ useHandCursor: true });
    button.on("pointerdown", onClick);
    button.on("pointerover", () => {
      button.setColor("#f8d66d");
    });
    button.on("pointerout", () => {
      button.setColor("#fff7d6");
    });
    return button;
  }

  private teardown(): void {
    this.client?.close();
    this.client = null;
    this.audienceOverlay?.remove();
    this.audienceOverlay = null;
    this.audienceInput = null;
  }
}
