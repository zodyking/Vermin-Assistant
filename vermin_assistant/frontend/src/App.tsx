import { Badge } from "@astryxdesign/core/Badge";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { Card } from "@astryxdesign/core/Card";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Heading } from "@astryxdesign/core/Heading";
import { Layout, LayoutContent, LayoutFooter, LayoutHeader } from "@astryxdesign/core/Layout";
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl";
import { Selector } from "@astryxdesign/core/Selector";
import { Slider } from "@astryxdesign/core/Slider";
import { StackItem } from "@astryxdesign/core/Stack";
import { StatusDot } from "@astryxdesign/core/StatusDot";
import { Switch } from "@astryxdesign/core/Switch";
import { Tab, TabList } from "@astryxdesign/core/TabList";
import { Text } from "@astryxdesign/core/Text";
import { Theme } from "@astryxdesign/core/theme";
import { VStack } from "@astryxdesign/core/VStack";
import { useCallback, useEffect, useState } from "react";
import { defaultThemeSlug, themes } from "../astryx-themes.js";
import {
  fetchStatus,
  playNow,
  saveSettings,
  stopPlayback,
  type Mode,
  type Player,
  type Settings,
  type Status,
} from "./api";
import { readColorMode, type ColorMode } from "./color-mode";
import { AnimalIcon } from "./icons";
import { Orb } from "./Orb";
import { Spectrum } from "./Spectrum";
import { LiveEngine } from "./synth";
import { DEFAULT_TARGETS, VERMIN, formatKhz, type Targets, type VerminId } from "./targets";

type PanelId = "speakers" | "schedule" | "sound";

const HOURS = Array.from({ length: 24 }, (_, hour) => ({
  value: String(hour),
  label: formatHour(hour),
}));

const MARKS = [0, 6, 12, 18];

const STATE_LABELS: Record<string, string> = {
  idle: "Idle",
  playing: "Playing",
  paused: "Paused",
  off: "Off",
  on: "On",
  unavailable: "Unavailable",
  unknown: "Unknown",
  standby: "Standby",
  buffering: "Buffering",
};

function formatHour(hour: number): string {
  const suffix = hour < 12 ? "AM" : "PM";
  const clock = hour % 12 || 12;
  return `${clock}:00 ${suffix}`;
}

function shortHour(hour: number): string {
  const suffix = hour < 12 ? "AM" : "PM";
  const clock = hour % 12 || 12;
  return `${clock} ${suffix}`;
}

function stateLabel(state: string): string {
  return STATE_LABELS[state] ?? state.charAt(0).toUpperCase() + state.slice(1);
}

function dotVariant(status: Status): "success" | "accent" | "warning" | "neutral" {
  if (!status.settings.enabled) return "neutral";
  if (status.patrol.playing) return "success";
  if (status.patrol.active) return "accent";
  return "warning";
}

function inWindow(hour: number, start: number, end: number): boolean {
  if (start === end) return true;
  if (start < end) return hour >= start && hour < end;
  return hour >= start || hour < end;
}

function clockHour(iso: string): number {
  const match = iso.match(/T(\d{2})/);
  return match ? Number(match[1]) : 0;
}

function scheduleLine(settings: Settings): string {
  if (settings.mode === "away") return "Plays whenever nobody is home.";
  const span =
    settings.start_hour === settings.end_hour
      ? "all day"
      : `${formatHour(settings.start_hour)} – ${formatHour(settings.end_hour)}`;
  if (settings.mode === "hours") return `Plays ${span}.`;
  return `Plays ${span}, when nobody is home.`;
}

function playerDescription(player: Player): string {
  const state = stateLabel(player.state);
  if (!player.area || player.area === player.name) return state;
  return `${player.area} · ${state}`;
}

export function App() {
  const [colorMode, setColorMode] = useState<ColorMode>(() => readColorMode());
  const [status, setStatus] = useState<Status | null>(null);
  const [volume, setVolume] = useState(35);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [panel, setPanel] = useState<PanelId>("sound");
  const [demoing, setDemoing] = useState(false);
  const [pulse, setPulse] = useState(55);
  const [hunt, setHunt] = useState(false);
  const [huntId, setHuntId] = useState<VerminId | null>(null);
  const [peakLabel, setPeakLabel] = useState("—");
  const [engine] = useState(() => new LiveEngine());

  useEffect(() => {
    const apply = () => setColorMode(readColorMode());
    apply();
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", apply);
    const timer = window.setInterval(apply, 2000);
    return () => {
      media.removeEventListener("change", apply);
      window.clearInterval(timer);
    };
  }, []);

  const applyStatus = useCallback((next: Status) => {
    setStatus(next);
    setVolume(Math.round(next.settings.volume * 100));
    setError(next.patrol.last_error);
    engine.setTargets(next.settings.targets ?? DEFAULT_TARGETS);
  }, [engine]);

  useEffect(() => {
    let cancel = false;
    const load = (quiet: boolean) => {
      fetchStatus()
        .then((next) => {
          if (!cancel) applyStatus(next);
        })
        .catch((reason: unknown) => {
          if (!cancel) setError(reason instanceof Error ? reason.message : "Couldn't reach Vermin Assistant");
        })
        .finally(() => {
          if (!cancel && !quiet) setLoading(false);
        });
    };
    load(false);
    const timer = window.setInterval(() => load(true), 10000);
    return () => {
      cancel = true;
      window.clearInterval(timer);
    };
  }, [applyStatus]);

  async function commit(partial: Partial<Settings>) {
    if (!status) return;
    const next = { ...status.settings, ...partial, repeat: "continuous" as const };
    setStatus({ ...status, settings: next });
    try {
      applyStatus(await saveSettings(next));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Couldn't save");
      try {
        applyStatus(await fetchStatus());
      } catch {
        setStatus(status);
      }
    }
  }

  function togglePlayer(entityId: string, checked: boolean) {
    if (!status) return;
    const players = checked
      ? [...status.settings.players, entityId]
      : status.settings.players.filter((id) => id !== entityId);
    void commit({ players });
  }

  function changeTarget(id: VerminId, patch: Partial<Targets[VerminId]>, saveNow: boolean) {
    if (!status) return;
    const current = status.settings.targets ?? DEFAULT_TARGETS;
    const targets = { ...current, [id]: { ...current[id], ...patch } };
    engine.setTargets(targets);
    if (saveNow) {
      void commit({ targets });
      return;
    }
    setStatus({ ...status, settings: { ...status.settings, targets } });
  }

  useEffect(() => {
    engine.setLevel(volume / 100);
  }, [engine, volume]);

  useEffect(() => {
    engine.setIntensity(pulse / 100);
  }, [engine, pulse]);

  useEffect(() => {
    engine.show(Boolean(status?.patrol.playing) || demoing);
  }, [demoing, engine, status?.patrol.playing]);

  useEffect(() => {
    if (!hunt) {
      setHuntId(null);
      return;
    }
    let index = 0;
    setHuntId(VERMIN[0]?.id ?? null);
    const timer = window.setInterval(() => {
      index = (index + 1) % VERMIN.length;
      setHuntId(VERMIN[index]?.id ?? null);
    }, 1600);
    return () => window.clearInterval(timer);
  }, [hunt]);

  useEffect(() => {
    const liveNow = Boolean(status?.patrol.playing) || demoing;
    if (!liveNow) {
      setPeakLabel("—");
      return;
    }
    const timer = window.setInterval(() => {
      const peak = engine.peakFrequency();
      setPeakLabel(peak ? formatKhz(peak) : "—");
    }, 120);
    return () => window.clearInterval(timer);
  }, [demoing, engine, status?.patrol.playing]);

  useEffect(() => () => engine.dispose(), [engine]);

  const settings = status?.settings;
  const targets = settings?.targets ?? DEFAULT_TARGETS;
  const playing = Boolean(status?.patrol.playing);
  const live = playing || demoing;
  const statusLine = status ? (playing ? "Playing" : status.patrol.reason) : "Loading";
  const nowHour = status ? clockHour(status.now) : 0;
  const speakerLine =
    !settings || settings.players.length === 0
      ? "No speaker"
      : settings.players.length === 1
        ? (status?.players.find((player) => player.entity_id === settings.players[0])?.name ?? "1 speaker")
        : `${settings.players.length} speakers`;

  return (
    <Theme theme={themes[defaultThemeSlug]} mode={colorMode}>
      <div className="app" data-mode={colorMode}>
        <Layout
          className="shell"
          height="fill"
          contentWidth={1120}
          defaultHasDividers
          header={
            <LayoutHeader label="Vermin Assistant">
              <div className="topbar">
                <Heading level={1}>Vermin Assistant</Heading>
                <div className="topbar-mid">
                  {status ? (
                    <>
                      <span className="hud-chip" data-live={live}>
                        <StatusDot variant={dotVariant(status)} label={statusLine} isPulsing={live} />
                        {live ? "Neural live" : statusLine}
                      </span>
                      <span className="topbar-presence">
                        <Badge label={presenceLabel(status)} variant={status.presence.someone_home ? "neutral" : "blue"} />
                      </span>
                    </>
                  ) : null}
                </div>
                {settings ? (
                  <Switch
                    label="Active"
                    value={settings.enabled}
                    onChange={(checked) => void commit({ enabled: checked })}
                    labelPosition="start"
                  />
                ) : null}
              </div>
            </LayoutHeader>
          }
          footer={
            settings ? (
              <LayoutFooter label="Playback">
                <div className="deck">
                  <Text type="body">{speakerLine}</Text>
                  <StackItem size="fill">
                    <Slider
                      label="Volume"
                      min={0}
                      max={100}
                      step={1}
                      value={volume}
                      valueDisplay="text"
                      formatValue={(value: number) => `${value}%`}
                      onChange={(value: number) => {
                        setVolume(value);
                        engine.setLevel(value / 100);
                      }}
                      onChangeEnd={(value: number) => void commit({ volume: value / 100 })}
                      width="100%"
                    />
                  </StackItem>
                  <div className="deck-actions">
                    <Button
                      label={demoing ? "Stop demo" : "Demo"}
                      variant="secondary"
                      clickAction={() => {
                        if (demoing) {
                          engine.setAudible(false);
                          if (!playing) engine.stop();
                          setDemoing(false);
                          return;
                        }
                        engine.setTargets(targets);
                        engine.setIntensity(pulse / 100);
                        engine.setLevel(volume / 100);
                        engine.setAudible(true);
                        engine.start();
                        setDemoing(true);
                      }}
                    />
                    <Button
                      label={playing ? "Pause" : "Play"}
                      variant="primary"
                      isDisabled={settings.players.length === 0}
                      clickAction={async () => {
                        try {
                          if (playing) {
                            if (!demoing) engine.stop();
                            applyStatus(await stopPlayback());
                            return;
                          }
                          engine.setTargets(targets);
                          engine.setIntensity(pulse / 100);
                          if (!demoing) engine.setAudible(false);
                          engine.start();
                          applyStatus(await playNow(settings));
                        } catch (reason) {
                          if (!demoing) engine.stop();
                          setError(reason instanceof Error ? reason.message : "Couldn't play");
                        }
                      }}
                    />
                    <Button
                      label="Stop"
                      variant="secondary"
                      isDisabled={settings.players.length === 0 && !demoing}
                      clickAction={async () => {
                        try {
                          engine.setAudible(false);
                          engine.stop();
                          setDemoing(false);
                          if (settings.players.length > 0) applyStatus(await stopPlayback());
                        } catch (reason) {
                          setError(reason instanceof Error ? reason.message : "Couldn't stop");
                        }
                      }}
                    />
                  </div>
                </div>
              </LayoutFooter>
            ) : null
          }
        >
          <LayoutContent label="Vermin Assistant" padding={4}>
            {!status || !settings ? (
              <EmptyState
                headingLevel={2}
                isCompact
                title={loading ? "Loading" : "Couldn't reach Vermin Assistant"}
                actions={
                  loading ? null : (
                    <Button
                      label="Try again"
                      variant="primary"
                      clickAction={async () => {
                        setLoading(true);
                        try {
                          applyStatus(await fetchStatus());
                        } catch (reason) {
                          setError(reason instanceof Error ? reason.message : "Couldn't reach Vermin Assistant");
                        } finally {
                          setLoading(false);
                        }
                      }}
                    />
                  )
                }
              />
            ) : (
              <VStack gap={4}>
                {error ? <Banner status="error" title={error} collapsible={false} /> : null}
                <TabList value={panel} onChange={(value) => setPanel(value as PanelId)} role="tablist" layout="fill" hasDivider>
                  <Tab value="speakers" label="Speakers" panelId="panel-speakers" />
                  <Tab value="schedule" label="Schedule" panelId="panel-schedule" />
                  <Tab value="sound" label="Sound" panelId="panel-sound" />
                </TabList>

                <div key={panel} className="panel" id={`panel-${panel}`} role="tabpanel">
                  {panel === "speakers" ? (
                    status.players.length === 0 ? (
                      <EmptyState headingLevel={2} isCompact title="No speakers yet" />
                    ) : (
                      <div className="speakers">
                        {status.players.map((player) => {
                          const selected = settings.players.includes(player.entity_id);
                          return (
                            <div key={player.entity_id} className="speaker" data-selected={selected}>
                              <CheckboxInput
                                label={player.name}
                                description={playerDescription(player)}
                                value={selected}
                                onChange={(checked) => togglePlayer(player.entity_id, checked)}
                                width="100%"
                              />
                            </div>
                          );
                        })}
                      </div>
                    )
                  ) : null}

                  {panel === "schedule" ? (
                    <VStack gap={4}>
                      <SegmentedControl
                        label="When"
                        layout="fill"
                        value={settings.mode}
                        onChange={(value) => void commit({ mode: value as Mode })}
                      >
                        <SegmentedControlItem value="hours" label="Hours" />
                        <SegmentedControlItem value="away" label="Away" />
                        <SegmentedControlItem value="both" label="Both" />
                      </SegmentedControl>
                      <Card variant="muted" padding={4} width="100%">
                        <VStack gap={4}>
                          {settings.mode !== "away" ? (
                            <div className="day" aria-hidden="true">
                              <div className="rail">
                                {HOURS.map((hour) => {
                                  const value = Number(hour.value);
                                  const on = inWindow(value, settings.start_hour, settings.end_hour);
                                  return <i key={hour.value} data-on={on} data-now={value === nowHour} />;
                                })}
                              </div>
                              <div className="rail-labels">
                                {MARKS.map((hour) => (
                                  <span key={hour} style={{ gridColumn: hour + 1 }}>
                                    {shortHour(hour)}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : null}
                          {settings.mode !== "away" ? (
                            <div className="hours">
                              <Selector
                                label="From"
                                options={HOURS}
                                value={String(settings.start_hour)}
                                onChange={(value) => {
                                  if (value != null) void commit({ start_hour: Number(value) });
                                }}
                                width="100%"
                              />
                              <Selector
                                label="Until"
                                options={HOURS}
                                value={String(settings.end_hour)}
                                onChange={(value) => {
                                  if (value != null) void commit({ end_hour: Number(value) });
                                }}
                                width="100%"
                              />
                            </div>
                          ) : null}
                          <Text type="body" display="block">
                            {scheduleLine(settings)}
                          </Text>
                        </VStack>
                      </Card>
                    </VStack>
                  ) : null}

                  {panel === "sound" ? (
                    <div className="console">
                      <section className="stage" aria-label="Neural core">
                        <Orb
                          active={live}
                          intensity={pulse}
                          label={live ? "Engaged" : "Standby"}
                          peak={live && peakLabel !== "—" ? peakLabel : formatKhz(activeUpper(targets))}
                        />
                        <div className="stage-meta">
                          <h2>Neural deterrent core</h2>
                          <p>
                            Chirps slam the upper hearing edge of every selected pest. Raise pulse for denser fire. Hunt
                            mode sweeps focus across the board.
                          </p>
                          <div className="feature-row">
                            <div className="feature">
                              <label htmlFor="pulse">Neural pulse</label>
                              <Slider
                                label="Neural pulse"
                                isLabelHidden
                                min={15}
                                max={100}
                                step={1}
                                value={pulse}
                                valueDisplay="text"
                                formatValue={(value: number) => `${value}%`}
                                onChange={(value: number) => {
                                  setPulse(value);
                                  engine.setIntensity(value / 100);
                                }}
                                width="100%"
                              />
                            </div>
                            <div className="feature">
                              <label>Hunt sweep</label>
                              <Switch
                                label={hunt ? "Scanning" : "Armed"}
                                value={hunt}
                                onChange={setHunt}
                                labelPosition="start"
                              />
                            </div>
                          </div>
                        </div>
                      </section>
                      <section className="preset" aria-label="Animals">
                        <h2>Target matrix</h2>
                        <div className="strips">
                          {VERMIN.map((spec) => {
                            const setting = targets[spec.id];
                            return (
                              <div
                                key={spec.id}
                                className="strip"
                                data-on={setting.enabled}
                                data-hunt={hunt && huntId === spec.id}
                              >
                                <div className="fader">
                                  <Slider
                                    orientation="vertical"
                                    label={`${spec.name} level`}
                                    isLabelHidden
                                    min={0}
                                    max={100}
                                    step={1}
                                    value={setting.level}
                                    valueDisplay="none"
                                    isDisabled={!setting.enabled}
                                    onChange={(value: number) => changeTarget(spec.id, { level: value }, false)}
                                    onChangeEnd={(value: number) => changeTarget(spec.id, { level: value }, true)}
                                  />
                                </div>
                                <button
                                  type="button"
                                  className="strip-hit"
                                  aria-pressed={setting.enabled}
                                  onClick={() => changeTarget(spec.id, { enabled: !setting.enabled }, true)}
                                >
                                  <AnimalIcon id={spec.id} />
                                  <span>{spec.name}</span>
                                  <small>{formatKhz(spec.upper)}</small>
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      </section>
                      <Spectrum engine={engine} playing={live} targets={targets} />
                    </div>
                  ) : null}
                </div>
              </VStack>
            )}
          </LayoutContent>
        </Layout>
      </div>
    </Theme>
  );
}

function presenceLabel(status: Status): string {
  if (status.presence.unknown) return "Unknown";
  if (!status.presence.someone_home) return "Nobody home";
  return "Someone home";
}

function activeUpper(targets: Targets): number {
  const ranked = VERMIN.filter((spec) => targets[spec.id]?.enabled && targets[spec.id].level > 0).sort(
    (left, right) => right.upper - left.upper,
  );
  return ranked[0]?.upper ?? 0;
}
