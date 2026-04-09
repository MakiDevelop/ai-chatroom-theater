# AI Chatroom Theater

> N 個 AI 角色，一齣即興劇。坐下來看戲，或隨時插話。

AI Chatroom Theater 讓你指定多個 AI 角色（各有獨立人設），他們會自動對話、互嗆、接話 — 像一齣停不下來的即興劇，演給你看。

## Features

- **可變角色數**：2~N 個 AI 角色，各有獨立 persona（名字、個性、背景、說話風格）
- **自動對話**：角色之間自動輪流發言，不是死板的輪轉，而是用「發言意願評分」搶話
- **觀眾模式**：主人可以純觀賞，也可以隨時插話介入
- **場景設定**：給一個主題或情境（「辯論 tabs vs spaces」「末日求生」「辦公室八卦」）
- **恩怨記憶**：角色跨 session 記住之前的衝突與關係
- **地端優先**：主力走 Ollama，省 token，隱私安全
- **外部 API 支援**：想請「高級演員」？接 OpenAI / Anthropic / Gemini 都行

## Quick Start

```bash
# 安裝
pip install ai-chatroom-theater

# 啟動一場辯論（使用 Ollama）
theater start --scene examples/scenes/laptop-debate.yaml

# 或用 Docker
docker compose up
```

## Architecture

```
CharacterManager  — 角色載入 / 驗證 / prompt 組裝
ConversationEngine — Session Actor + Speaker Selector（評分制）
LLMProvider       — LiteLLM wrapper，支援 Ollama + 多家 API
MemoryStore       — transcript + episodic summary + relationship state
SceneDirector     — 場景 seed / 節奏控制 / 收尾條件
Display           — Event stream → TUI / Web / 任意 renderer
```

## Speaker Selection

不是無聊的輪流唸稿。每句話結束後，系統為所有候選角色評分：

```
score = w1×被點名 + w2×仇恨值 + w3×沉默時長 + w4×人設相關度 - w5×連續發言懲罰
```

最高分者搶到麥克風。

## Roadmap

### Phase 1 — CLI Theater（✅ Done）
- [x] 核心架構設計（Protocol-based, pluggable）
- [x] MVP：2~4 角色 + Ollama (gemma4) + Rich TUI + 觀眾插話
- [x] Speaker Selection 評分制（mention / silence / aggression）
- [x] 四階段節奏引擎（開場試探→交鋒→露弱點→收尾）
- [x] 角色個性化（triggers / weaknesses / forbidden / emoji / aggression / humor）
- [x] Transcript 輸出（Markdown）

### Phase 2 — 16-bit Visual Theater
- [ ] 超級任天堂 16-bit 風格 Web 前端（Phaser / PixiJS）
- [ ] 像素角色立繪 + 表情變化
- [ ] Typewriter 對話框（一字一字跳出）
- [ ] 場景背景（咖啡廳、便利商店、電梯...）
- [ ] 8-bit 音效 + chiptune BGM
- [ ] FastAPI backend 串接現有對話引擎

### Phase 3 — AI 動畫影集（終極目標）
- [ ] TTS 語音（每角色不同聲線）
- [ ] 自動影片合成 pipeline（Canvas render → ffmpeg → MP4）
- [ ] 自動上字幕
- [ ] 每集 3-5 分鐘，全自動生成
- [ ] 直接上傳 YouTube / Twitter / 社群

### Backlog
- [ ] LLM Director Agent（隱形導演，自動注入戲劇衝突）
- [ ] 角色/場景解耦（場景配角色組合包）
- [ ] SillyTavern 角色卡匯入
- [ ] 電子雞模式（背景跑的數位水族箱）

## Tech Stack

- Python 3.12+ / Pydantic v2（對話引擎）
- Ollama + gemma4（LLM backend）
- Rich（Phase 1 Terminal UI）
- Phaser / PixiJS（Phase 2 Web renderer）
- FastAPI（Phase 2+ API）
- ffmpeg（Phase 3 影片合成）
- SQLite（未來持久化）

## License

MIT
