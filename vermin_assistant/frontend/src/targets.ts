export type VerminId = "mouse" | "rat" | "cockroach" | "cricket" | "mosquito" | "moth";

export type TargetSetting = {
  enabled: boolean;
  level: number;
};

export type Targets = Record<VerminId, TargetSetting>;

export type VerminSpec = {
  id: VerminId;
  name: string;
  upper: number;
};

/** Upper hearing limits. The chirp runs up to this, or as high as the output allows. */
export const VERMIN: VerminSpec[] = [
  { id: "mouse", name: "Mouse", upper: 92000 },
  { id: "rat", name: "Rat", upper: 76000 },
  { id: "cockroach", name: "Cockroach", upper: 3000 },
  { id: "cricket", name: "Cricket", upper: 100000 },
  { id: "mosquito", name: "Mosquito", upper: 2000 },
  { id: "moth", name: "Moth", upper: 80000 },
];

export const DEFAULT_TARGETS: Targets = {
  mouse: { enabled: true, level: 80 },
  rat: { enabled: true, level: 100 },
  cockroach: { enabled: false, level: 70 },
  cricket: { enabled: false, level: 70 },
  mosquito: { enabled: false, level: 70 },
  moth: { enabled: false, level: 70 },
};

export function playbackBand(upper: number, sampleRate: number): { low: number; high: number } {
  const high = Math.min(upper, sampleRate * 0.45);
  const low = Math.max(80, high * 0.28);
  return { low, high };
}

export function activeSpecs(targets: Targets): (VerminSpec & TargetSetting)[] {
  return VERMIN.flatMap((spec) => {
    const setting = targets[spec.id];
    if (!setting?.enabled || setting.level <= 0) return [];
    return [{ ...spec, ...setting }];
  });
}

export function formatKhz(freq: number): string {
  const khz = freq / 1000;
  const rounded = Math.round(khz);
  return Math.abs(khz - rounded) < 0.05 ? `${rounded} kHz` : `${khz.toFixed(1)} kHz`;
}
