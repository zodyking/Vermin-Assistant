import { useEffect, useRef, useState } from "react";
import { activeSpecs, formatKhz, type Targets } from "./targets";
import type { LiveEngine } from "./synth";

type SpectrumProps = {
  engine: LiveEngine;
  playing: boolean;
  targets: Targets;
};

export function Spectrum({ engine, playing, targets }: SpectrumProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [peak, setPeak] = useState<number | null>(null);
  const ranked = [...activeSpecs(targets)].sort((left, right) => right.level - left.level);
  const shown = (playing ? peak : null) ?? ranked[0]?.upper ?? 0;

  useEffect(() => {
    const node = canvas.current;
    if (!node) return;
    return engine.attach(node);
  }, [engine]);

  useEffect(() => {
    const timer = window.setInterval(() => setPeak(engine.peakFrequency()), 120);
    return () => window.clearInterval(timer);
  }, [engine]);

  return (
    <section className="spectrum" aria-label="Output spectrum">
      <div className="spectrum-head">
        <div>
          <h2>Output spectrum</h2>
          <span className="live" data-on={playing}>
            <i />
            Live
          </span>
        </div>
        <div className="readout">
          <span>{playing && peak ? "Peak" : "Upper range"}</span>
          <strong>{shown ? formatKhz(shown) : "—"}</strong>
        </div>
      </div>
      <canvas ref={canvas} />
    </section>
  );
}
