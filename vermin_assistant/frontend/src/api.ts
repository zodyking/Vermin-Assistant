import type { Targets } from "./targets";

export type Mode = "hours" | "away" | "both";
export type Repeat = "continuous" | "15" | "30" | "60";

export type Settings = {
  enabled: boolean;
  mode: Mode;
  start_hour: number;
  end_hour: number;
  repeat: Repeat;
  volume: number;
  players: string[];
  targets: Targets;
};

export type Player = {
  entity_id: string;
  name: string;
  area: string;
  state: string;
  supports_volume: boolean;
};

export type Status = {
  settings: Settings;
  players: Player[];
  hidden_incompatible: number;
  presence: {
    someone_home: boolean;
    people_home: number | null;
    unknown: boolean;
    source: string;
  };
  patrol: {
    active: boolean;
    reason: string;
    playing: boolean;
    last_played: string | null;
    next_play: string | null;
    last_error: string | null;
    last_results: { entity_id: string; ok: boolean; error?: string }[];
  };
  audio: { title: string; seconds: number; published: boolean };
  homeassistant: boolean;
  dev: boolean;
  timezone: string;
  now: string;
};

function endpoint(path: string): string {
  return new URL(path, document.baseURI).toString();
}

async function readError(response: Response): Promise<string> {
  const text = (await response.text()).trim();
  if (!text) return "Request failed";
  try {
    const data = JSON.parse(text) as { error?: string };
    if (data.error) return data.error;
  } catch {
    return text;
  }
  return text;
}

async function request(path: string, init?: RequestInit): Promise<Status> {
  const response = await fetch(endpoint(path), {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as Status;
}

export function fetchStatus(): Promise<Status> {
  return request("api/status");
}

export function saveSettings(settings: Settings): Promise<Status> {
  return request("api/settings", { method: "PUT", body: JSON.stringify(settings) });
}

export function playNow(settings: Settings): Promise<Status> {
  return request("api/play", { method: "POST", body: JSON.stringify(settings) });
}

export function stopPlayback(): Promise<Status> {
  return request("api/stop", { method: "POST", body: "{}" });
}

export function setDevPresence(someoneHome: boolean): Promise<Status> {
  return request("api/dev/presence", {
    method: "POST",
    body: JSON.stringify({ someone_home: someoneHome, known: true }),
  });
}

export function previewUrl(): string {
  return endpoint("audio/preview.wav");
}
