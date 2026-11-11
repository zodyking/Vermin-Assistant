import { activeSpecs, playbackBand, type Targets } from "./targets";

type Burst = {
  freq: number;
  until: number;
  mag: number;
};

const LOOKAHEAD = 0.28;

export class LiveEngine {
  private context: AudioContext | null = null;
  private master: GainNode | null = null;
  private monitor: GainNode | null = null;
  private analyser: AnalyserNode | null = null;
  private noise: AudioBuffer | null = null;
  private targets: Targets | null = null;
  private running = false;
  private cursor = 0;
  private timer = 0;
  private frame = 0;
  private canvas: HTMLCanvasElement | null = null;
  private bins = new Uint8Array(0);
  private bursts: Burst[] = [];
  private visual = false;
  private audible = false;
  private level = 0.35;
  private random = Math.random;

  show(active: boolean): void {
    this.visual = active;
  }

  setAudible(on: boolean): void {
    this.audible = on;
    this.applyMonitor();
  }

  setLevel(value: number): void {
    this.level = Math.max(0, Math.min(1, value));
    this.applyMonitor();
  }

  nyquist(): number {
    return (this.context?.sampleRate ?? 48000) / 2;
  }

  setTargets(targets: Targets): void {
    this.targets = targets;
  }

  start(): void {
    const context = this.ensure();
    if (context.state === "suspended") void context.resume();
    if (this.running) return;
    this.running = true;
    this.cursor = context.currentTime + 0.05;
    this.timer = window.setInterval(() => this.schedule(), 70);
    this.schedule();
    this.draw();
  }

  stop(): void {
    this.running = false;
    window.clearInterval(this.timer);
    this.bursts = [];
  }

  attach(canvas: HTMLCanvasElement): () => void {
    this.canvas = canvas;
    this.draw();
    return () => {
      if (this.canvas === canvas) this.canvas = null;
    };
  }

  dispose(): void {
    window.cancelAnimationFrame(this.frame);
    this.stop();
    void this.context?.close();
    this.context = null;
  }

  private ensure(): AudioContext {
    if (this.context) return this.context;
    const context = openContext();
    const master = context.createGain();
    const analyser = context.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.45;
    analyser.minDecibels = -100;
    analyser.maxDecibels = -18;
    master.gain.value = 0.9;
    master.connect(analyser);
    const monitor = context.createGain();
    monitor.gain.value = 0;
    analyser.connect(monitor);
    monitor.connect(context.destination);
    this.monitor = monitor;
    const noise = context.createBuffer(1, context.sampleRate, context.sampleRate);
    const data = noise.getChannelData(0);
    for (let index = 0; index < data.length; index += 1) data[index] = Math.random() * 2 - 1;
    this.context = context;
    this.master = master;
    this.analyser = analyser;
    this.noise = noise;
    this.bins = new Uint8Array(analyser.frequencyBinCount);
    this.applyMonitor();
    return context;
  }

  private applyMonitor(): void {
    const monitor = this.monitor;
    const context = this.context;
    if (!monitor || !context) return;
    const gain = this.audible ? this.level : 0;
    monitor.gain.cancelScheduledValues(context.currentTime);
    monitor.gain.setTargetAtTime(gain, context.currentTime, 0.03);
  }

  private schedule(): void {
    const context = this.context;
    const master = this.master;
    const targets = this.targets;
    if (!context || !master || !targets || !this.running) return;
    const specs = activeSpecs(targets);
    if (specs.length === 0) return;
    const horizon = context.currentTime + LOOKAHEAD;
    while (this.cursor < horizon) {
      const spec = specs[Math.floor(this.random() * specs.length)];
      const band = playbackBand(spec.upper, context.sampleRate);
      const level = spec.level / 100;
      const pop = this.random() < 0.32;
      const duration = pop ? 0.006 + this.random() * 0.014 : 0.04 + this.random() * 0.11;
      const upward = this.random() < 0.5;
      const startFreq = upward ? band.low : band.high;
      const endFreq = upward ? band.high : band.low;
      this.fire(this.cursor, duration, startFreq, endFreq, band.high, level, pop);
      this.bursts.push({
        freq: band.high,
        until: this.cursor + duration,
        mag: level,
      });
      this.cursor += duration + 0.012 + this.random() * 0.07;
    }
    const now = context.currentTime;
    this.bursts = this.bursts.filter((burst) => burst.until > now);
  }

  private fire(
    when: number,
    duration: number,
    startFreq: number,
    endFreq: number,
    center: number,
    level: number,
    pop: boolean,
  ): void {
    const context = this.context;
    const master = this.master;
    if (!context || !master) return;
    const gain = context.createGain();
    gain.connect(master);
    const peak = (pop ? 0.55 : 0.34) * level;
    gain.gain.setValueAtTime(0.0001, when);
    gain.gain.linearRampToValueAtTime(peak, when + 0.003);
    gain.gain.exponentialRampToValueAtTime(0.0001, when + duration);

    const ceiling = context.sampleRate * 0.45;
    if (pop && this.noise) {
      const filter = context.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.value = Math.min(center, ceiling);
      filter.Q.value = 6;
      const source = context.createBufferSource();
      source.buffer = this.noise;
      source.connect(filter);
      filter.connect(gain);
      source.start(when);
      source.stop(when + duration);
      return;
    }

    const voice = context.createOscillator();
    voice.type = "sawtooth";
    const begin = Math.max(40, Math.min(startFreq, ceiling));
    const end = Math.max(40, Math.min(endFreq, ceiling));
    voice.frequency.setValueAtTime(begin, when);
    voice.frequency.exponentialRampToValueAtTime(end, when + duration);
    voice.connect(gain);
    voice.start(when);
    voice.stop(when + duration + 0.02);
  }

  private draw = (): void => {
    this.frame = window.requestAnimationFrame(this.draw);
    const canvas = this.canvas;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (width < 2 || height < 2) return;
    if (canvas.width !== Math.floor(width * ratio) || canvas.height !== Math.floor(height * ratio)) {
      canvas.width = Math.floor(width * ratio);
      canvas.height = Math.floor(height * ratio);
    }
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);
    context.fillStyle = "#071016";
    context.fillRect(0, 0, width, height);

    const plot = { left: 46, right: 12, top: 16, bottom: 28 };
    const plotWidth = width - plot.left - plot.right;
    const plotHeight = height - plot.top - plot.bottom;

    context.strokeStyle = "rgba(3, 169, 244, 0.16)";
    context.lineWidth = 1;
    context.font = "11px system-ui, Segoe UI, sans-serif";
    context.fillStyle = "rgba(225, 225, 225, 0.55)";
    context.textAlign = "right";
    for (let step = 0; step <= 6; step += 1) {
      const y = plot.top + (plotHeight * step) / 6;
      context.beginPath();
      context.moveTo(plot.left, y);
      context.lineTo(width - plot.right, y);
      context.stroke();
      context.fillText(`${-step * 20}`, plot.left - 8, y + 4);
    }
    const span = this.nyquist();
    context.textAlign = "center";
    for (let step = 0; step <= 4; step += 1) {
      const fraction = step / 4;
      const x = plot.left + plotWidth * fraction;
      const khz = Math.round((span * fraction) / 1000);
      context.beginPath();
      context.moveTo(x, plot.top);
      context.lineTo(x, plot.top + plotHeight);
      context.stroke();
      context.fillText(step === 0 ? "0" : `${khz}k`, x, height - 8);
    }

    const bars = 96;
    const values = new Array<number>(bars).fill(this.visual ? 0.05 : 0.02);
    let heard = false;
    if (this.running && this.analyser) {
      this.analyser.getByteFrequencyData(this.bins);
      for (let bin = 0; bin < this.bins.length; bin += 1) {
        if ((this.bins[bin] ?? 0) > 12) {
          heard = true;
          break;
        }
      }
    }
    if (heard) {
      for (let bar = 0; bar < bars; bar += 1) {
        const freq = ((bar + 0.5) / bars) * span;
        const bin = Math.min(this.bins.length - 1, Math.round((freq / span) * this.bins.length));
        values[bar] = (this.bins[bin] ?? 0) / 255;
      }
    } else if (this.visual && this.targets) {
      const now = performance.now() / 1000;
      const rate = this.context?.sampleRate ?? 48000;
      for (const spec of activeSpecs(this.targets)) {
        const band = playbackBand(spec.upper, rate);
        const sweep = 0.5 + 0.5 * Math.sin(now * 6.5 + spec.upper / 8000);
        const freq = band.low + (band.high - band.low) * sweep;
        const centerBar = Math.min(bars - 1, Math.max(0, Math.round((freq / span) * bars)));
        const amount = (0.45 + 0.5 * Math.abs(Math.sin(now * 11 + band.low))) * (spec.level / 100);
        values[centerBar] = Math.max(values[centerBar] ?? 0, amount);
        if (centerBar > 0) values[centerBar - 1] = Math.max(values[centerBar - 1] ?? 0, amount * 0.55);
        if (centerBar < bars - 1) values[centerBar + 1] = Math.max(values[centerBar + 1] ?? 0, amount * 0.55);
      }
    }

    const gap = 1;
    const barWidth = Math.max(1, plotWidth / bars - gap);
    for (let bar = 0; bar < bars; bar += 1) {
      const amount = values[bar] ?? 0;
      const barHeight = Math.max(1, amount * plotHeight);
      const x = plot.left + (bar / bars) * plotWidth;
      context.fillStyle = amount > 0.72 ? "#e8f8ff" : "#03a9f4";
      context.globalAlpha = 0.35 + amount * 0.65;
      context.fillRect(x, plot.top + plotHeight - barHeight, barWidth, barHeight);
    }
    context.globalAlpha = 1;

    if (this.targets) {
      for (const spec of activeSpecs(this.targets)) {
        const played = Math.min(spec.upper, span * 0.9);
        const x = plot.left + (played / span) * plotWidth;
        context.strokeStyle = "rgba(3, 169, 244, 0.85)";
        context.beginPath();
        context.moveTo(x, plot.top);
        context.lineTo(x, plot.top + plotHeight);
        context.stroke();
        context.fillStyle = "#ffffff";
        context.beginPath();
        context.arc(x, plot.top + 6, 3.5, 0, Math.PI * 2);
        context.fill();
      }
    }
  };

  peakFrequency(): number | null {
    if (!this.running || !this.analyser || this.bins.length === 0) return null;
    let loudest = 0;
    let index = 0;
    for (let bin = 2; bin < this.bins.length; bin += 1) {
      const value = this.bins[bin] ?? 0;
      if (value > loudest) {
        loudest = value;
        index = bin;
      }
    }
    if (loudest < 18) return null;
    return (index / this.bins.length) * this.nyquist();
  }
}

function openContext(): AudioContext {
  try {
    return new AudioContext({ sampleRate: 96000 });
  } catch {
    return new AudioContext();
  }
}
