export interface TurnMessage {
  type: "turn";
  speaker_id: string;
  speaker_name: string;
  text: string;
  targets: string[];
  emotion: string | null;
  turn_index: number;
  max_turns: number;
}

export interface AudienceMessage {
  type: "audience";
  text: string;
}

export interface SceneEndMessage {
  type: "scene_end";
  reason: "max_turns" | "quit";
}

export interface ErrorMessage {
  type: "error";
  message: string;
}

export type ServerMessage =
  | TurnMessage
  | AudienceMessage
  | SceneEndMessage
  | ErrorMessage;

export interface SceneSummary {
  id: string;
  title: string;
  premise: string;
  tone: string;
  opening_hook: string;
}

export interface CharacterSummary {
  id: string;
  name: string;
  persona: string;
  aggression: number;
  humor: number;
  emoji_style: string;
}

export interface CreateSessionResponse {
  session_id: string;
  scene: SceneSummary;
  characters: CharacterSummary[];
}

export interface StartClientMessage {
  type: "start";
}

export interface AudienceClientMessage {
  type: "audience";
  text: string;
}

export interface QuitClientMessage {
  type: "quit";
}

export type ClientMessage =
  | StartClientMessage
  | AudienceClientMessage
  | QuitClientMessage;

export type ConnectionEventType =
  | ServerMessage["type"]
  | "open"
  | "close"
  | "reconnecting"
  | "connection_error"
  | "connection_lost"
  | "send_error";

export interface ReconnectEvent {
  attempt: number;
  maxAttempts: number;
}

export interface ConnectionErrorEvent {
  message: string;
}

export interface TheaterSceneData extends CreateSessionResponse {}

export type DialogTone = "speaker" | "audience" | "system" | "error";
