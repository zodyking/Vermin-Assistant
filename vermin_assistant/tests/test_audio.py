import tempfile
import unittest
import wave
from pathlib import Path

from app.audio import render, write_wav


class AudioTests(unittest.TestCase):
    def test_render_is_audible_and_not_clipped(self):
        samples = render(seconds=0.2, rate=48000)
        self.assertEqual(len(samples), 9600)
        peak = max(abs(sample) for sample in samples)
        self.assertGreater(peak, 1000)
        self.assertLessEqual(peak, 32767)
        self.assertLess(abs(samples[0]), 200)

    def test_phrase_is_not_a_steady_tone(self):
        samples = render(seconds=1.0, edge_fade=False)
        window = 960
        energies = []
        for index in range(0, len(samples) - window, window):
            chunk = samples[index : index + window]
            energies.append(sum(abs(sample) for sample in chunk) / window)
        self.assertGreater(max(energies), min(energies) * 4)

    def test_wav_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tone.wav"
            write_wav(path, render(seconds=0.05, rate=48000))
            with wave.open(str(path), "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getsampwidth(), 2)
                self.assertEqual(handle.getframerate(), 48000)
                self.assertEqual(handle.getnframes(), 2400)


if __name__ == "__main__":
    unittest.main()
