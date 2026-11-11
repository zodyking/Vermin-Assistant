"""Original high-frequency deterrent.

Chirps and pops are synthesized around the hearing bands in targets.py.
This is not a copy of any recording, and it is not a steady sine.
"""

from __future__ import annotations

import math
import os
import random
import struct
import wave
from pathlib import Path

from .targets import active_targets, default_targets, signature

RATE = 48000
SECONDS = 3600
PHRASE_SECONDS = 8.0
PEAK = 0.9

SOUNDS_DIR = Path(__file__).resolve().parent / "sounds"
FILE_NAME = "deterrent.wav"
PREVIEW_NAME = "preview.wav"
KEY_NAME = "deterrent.key"


def _envelope(index: int, count: int, rate: int) -> float:
    attack = max(1, int(rate * 0.003))
    if index < attack:
        return index / attack
    remain = max(1, count - attack)
    progress = (index - attack) / remain
    return math.exp(-4.2 * progress)


def _add_chirp(mix: list[float], start: int, count: int, spec: dict, level: float, rate: int, rng: random.Random) -> None:
    low = spec["low"]
    high = min(spec["high"], rate * 0.45)
    if rng.random() < 0.5:
        low, high = high, low
    # Break the sweep so it lunges instead of gliding.
    split = int(count * rng.uniform(0.35, 0.7))
    mid = spec["center"] * rng.uniform(0.85, 1.12)
    mid = min(max(mid, min(spec["low"], spec["high"])), rate * 0.45)
    phase = rng.random() * math.tau
    for index in range(count):
        at = start + index
        if at >= len(mix):
            return
        if index < split:
            progress = index / max(1, split)
            begin, end = low, mid
        else:
            progress = (index - split) / max(1, count - split)
            begin, end = mid, high
        ratio = end / begin if begin else 1.0
        if ratio <= 0:
            ratio = 1.0
        freq = begin * (ratio**progress)
        freq *= 1.0 + 0.02 * math.sin(index * 0.41)
        phase += math.tau * freq / rate
        env = _envelope(index, count, rate) * level
        sample = math.sin(phase)
        if freq * 2 < rate * 0.46:
            sample += 0.4 * math.sin(phase * 2)
        if index < int(rate * 0.002):
            sample += (rng.random() * 2 - 1) * 1.4
        mix[at] += env * sample * 0.72


def _add_pop(mix: list[float], start: int, count: int, spec: dict, level: float, rate: int, rng: random.Random) -> None:
    phase = rng.random() * math.tau
    freq = min(spec["center"] * rng.uniform(0.92, 1.06), rate * 0.45)
    for index in range(count):
        at = start + index
        if at >= len(mix):
            return
        phase += math.tau * freq / rate
        env = _envelope(index, count, rate) * level
        noise = rng.random() * 2 - 1
        mix[at] += env * (0.35 * math.sin(phase) + 0.9 * noise)


def render_phrase(
    seconds: float,
    targets: list[dict] | None = None,
    rate: int = RATE,
    seed: int = 1,
) -> list[int]:
    chosen = targets or active_targets({"targets": default_targets()}, rate)
    if not chosen:
        chosen = active_targets({"targets": {"mouse": {"enabled": True, "level": 70}}}, rate)
    count = int(seconds * rate)
    mix = [0.0] * count
    rng = random.Random(seed)
    clock = 0.0
    while clock < seconds - 0.02:
        spec = rng.choice(chosen)
        level = spec["level"] / 100
        start = int(clock * rate)
        if rng.random() < 0.32:
            samples = int(rng.uniform(0.006, 0.02) * rate)
            _add_pop(mix, start, samples, spec, level, rate, rng)
            clock += samples / rate
        else:
            samples = int(rng.uniform(0.04, 0.15) * rate)
            _add_chirp(mix, start, samples, spec, level, rate, rng)
            clock += samples / rate
        clock += rng.uniform(0.012, 0.08)
    peak = max((abs(sample) for sample in mix), default=1.0) or 1.0
    scale = PEAK * 32767 / peak
    return [max(-32767, min(32767, int(round(sample * scale)))) for sample in mix]


def render(seconds: float = 0.2, rate: int = RATE, *, edge_fade: bool = True) -> list[int]:
    samples = render_phrase(seconds, rate=rate, seed=2)
    if edge_fade and samples:
        fade = max(1, min(len(samples) // 4, int(rate * 0.015)))
        for index in range(fade):
            weight = index / fade
            samples[index] = int(samples[index] * weight)
            samples[-1 - index] = int(samples[-1 - index] * weight)
    return samples


def write_wav(path: Path, samples: list[int], rate: int = RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(struct.pack("<" + "h" * len(samples), *samples))


def _pack(samples: list[int]) -> bytes:
    return struct.pack("<" + "h" * len(samples), *samples)


def write_hour(path: Path, settings: dict | None = None, rate: int = RATE) -> None:
    chosen = active_targets(settings, rate) or active_targets(
        {"targets": {"mouse": {"enabled": True, "level": 70}}}, rate
    )
    phrases = [render_phrase(PHRASE_SECONDS, chosen, rate, seed=seed) for seed in (1, 2, 3, 4)]
    write_wav(path.parent / PREVIEW_NAME, phrases[0], rate)
    total = rate * SECONDS
    blobs = [_pack(phrase) for phrase in phrases]
    fade = max(1, int(rate * 0.015))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        remaining = total
        first = True
        index = 0
        while remaining:
            phrase = phrases[index % len(phrases)]
            blob = blobs[index % len(blobs)]
            take = min(len(phrase), remaining)
            last = take == remaining
            if first or last or take != len(phrase):
                chunk = list(phrase[:take])
                span = min(fade, len(chunk))
                for step in range(span):
                    weight = step / span
                    if first:
                        chunk[step] = int(chunk[step] * weight)
                    if last:
                        chunk[-1 - step] = int(chunk[-1 - step] * weight)
                handle.writeframes(_pack(chunk))
            else:
                handle.writeframes(blob)
            remaining -= take
            first = False
            index += 1


def duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate() or RATE
    return frames / rate


def default_sound_path() -> Path:
    override = os.environ.get("VERMIN_ASSISTANT_SOUND")
    if override:
        return Path(override)
    return SOUNDS_DIR / FILE_NAME


def preview_path() -> Path:
    override = os.environ.get("VERMIN_ASSISTANT_SOUND")
    if override:
        return Path(override)
    return SOUNDS_DIR / PREVIEW_NAME


def ensure_file(settings: dict | None = None) -> Path:
    override = os.environ.get("VERMIN_ASSISTANT_SOUND")
    if override:
        return Path(override)
    target = SOUNDS_DIR / FILE_NAME
    key_path = SOUNDS_DIR / KEY_NAME
    key = signature(settings)
    if target.exists() and key_path.exists() and preview_path().exists():
        try:
            same_key = key_path.read_text(encoding="utf-8").strip() == key
            same_length = abs(duration_seconds(target) - SECONDS) < 1
            if same_key and same_length:
                return target
        except (OSError, wave.Error, EOFError):
            pass
    write_hour(target, settings)
    key_path.write_text(key + "\n", encoding="utf-8")
    return target


def main() -> None:
    target = ensure_file({"targets": default_targets()})
    print(f"wrote {target} ({duration_seconds(target):.1f}s)")


if __name__ == "__main__":
    main()
