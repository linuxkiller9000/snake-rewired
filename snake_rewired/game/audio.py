"""Procedural audio: all SFX and music are synthesized at startup.

No asset files, no numpy. Everything renders into 16-bit PCM buffers fed
to pygame.mixer.Sound. If no audio device exists the game runs silently.
"""

import math
import struct

SAMPLE_RATE = 22050


def _pcm16(samples):
    return b"".join(
        struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
        for s in samples)


def _tone(freq, seconds, shape="square", volume=0.4, slide_to=None,
          decay=True):
    n = int(SAMPLE_RATE * seconds)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        f = freq if slide_to is None else freq + (slide_to - freq) * (i / n)
        phase = (t * f) % 1.0
        if shape == "square":
            v = 1.0 if phase < 0.5 else -1.0
        elif shape == "triangle":
            v = 4 * abs(phase - 0.5) - 1
        else:  # sine
            v = math.sin(2 * math.pi * phase)
        env = (1 - i / n) if decay else 1.0
        out.append(v * volume * env)
    return out


def _noise(seconds, volume=0.3):
    import random
    rng = random.Random(7)
    n = int(SAMPLE_RATE * seconds)
    return [(rng.random() * 2 - 1) * volume * (1 - i / n) for i in range(n)]


def _mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    peak = max(1e-6, max(abs(v) for v in out))
    if peak > 0.95:
        out = [v / peak * 0.95 for v in out]
    return out


def _melody(notes, note_len, shape="square", volume=0.28):
    out = []
    for freq in notes:
        out.extend(_tone(freq, note_len, shape=shape, volume=volume,
                         decay=False))
    return out


def _soft(freq, seconds, shape="sine", volume=0.2, attack=0.06,
          release=0.18, slide_to=None):
    """Tone with a gentle attack/release envelope so notes blend."""
    n = int(SAMPLE_RATE * seconds)
    a = max(1, int(SAMPLE_RATE * attack))
    r = max(1, int(SAMPLE_RATE * release))
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        f = freq if slide_to is None else freq + (slide_to - freq) * (i / n)
        phase = (t * f) % 1.0
        if shape == "square":
            v = 1.0 if phase < 0.5 else -1.0
        elif shape == "triangle":
            v = 4 * abs(phase - 0.5) - 1
        else:
            v = math.sin(2 * math.pi * phase)
        env = min(1.0, i / a, (n - i) / r)
        out.append(v * volume * env)
    return out


SFX_RECIPES = {
    "food":      lambda: _soft(660, 0.09, "triangle", 0.28, slide_to=880),
    "bonus":     lambda: _soft(660, 0.12, "triangle", 0.28, slide_to=1180),
    "golden":    lambda: _mix(_soft(660, 0.14, "sine", 0.24, slide_to=1320),
                              _soft(990, 0.18, "sine", 0.18, slide_to=1760)),
    "speed":     lambda: _soft(520, 0.16, "triangle", 0.24, slide_to=1400),
    "slow":      lambda: _soft(760, 0.20, "triangle", 0.24, slide_to=300),
    "grow":      lambda: _soft(520, 0.07, "sine", 0.24, slide_to=700),
    "death":     lambda: _mix(_soft(300, 0.45, "triangle", 0.3, slide_to=70),
                              _noise(0.22, 0.10)),
    "countdown": lambda: _soft(440, 0.10, "triangle", 0.26),
    "go":        lambda: _soft(740, 0.20, "triangle", 0.3),
    "menu_move": lambda: _soft(330, 0.05, "sine", 0.18),
    "menu_select": lambda: _soft(550, 0.09, "sine", 0.24, slide_to=720),
    "pause":     lambda: _soft(392, 0.12, "sine", 0.24),
    "victory":   lambda: _melody([523, 659, 784, 1047], 0.16, "triangle", 0.24),
}

# Calm generative loop (~32 s): slow sine chord roots with soft fifths and a
# gentle legato pentatonic melody, two alternating phrases over an
# Am - F - C - G progression. No fast square-wave repetition.
_CHORDS = [  # (root, fifth), 4 s each, two passes
    (110.0, 164.8),   # A2, E3
    (87.3, 130.8),    # F2, C3
    (130.8, 196.0),   # C3, G3
    (98.0, 146.8),    # G2, D3
]
# A minor pentatonic phrases, quarter = 0.5 s, 0 = rest. 8 notes per chord.
_PHRASES = [
    [440, 0, 659, 587, 0, 523, 587, 0,
     440, 0, 523, 587, 659, 0, 587, 523,
     523, 0, 659, 784, 0, 659, 587, 0,
     440, 523, 587, 0, 659, 0, 0, 0],
    [659, 0, 784, 659, 0, 587, 523, 0,
     587, 0, 659, 523, 440, 0, 523, 0,
     440, 0, 523, 587, 659, 0, 784, 0,
     659, 587, 523, 0, 440, 0, 0, 0],
]


def _music_loop():
    bass, pad, lead = [], [], []
    beat = 0.5
    for phrase in _PHRASES:
        for ci, (root, fifth) in enumerate(_CHORDS):
            bass.extend(_soft(root, beat * 8, "sine", 0.14, attack=0.4,
                              release=0.6))
            pad.extend(_mix(_soft(fifth, beat * 8, "triangle", 0.07,
                                  attack=0.5, release=0.7),
                            _soft(root * 2, beat * 8, "sine", 0.05,
                                  attack=0.5, release=0.7)))
            for f in phrase[ci * 8:(ci + 1) * 8]:
                if f:
                    lead.extend(_soft(f, beat * 1.05, "triangle", 0.085,
                                      attack=0.05, release=0.25))
                else:
                    lead.extend([0.0] * int(SAMPLE_RATE * beat))
    return _mix(bass, pad, lead)


class AudioManager:
    def __init__(self, settings):
        self.settings = settings
        self.enabled = False
        self.sounds = {}
        self.music = None

    def init(self, pygame_module):
        try:
            pygame_module.mixer.init(frequency=SAMPLE_RATE, size=-16,
                                     channels=1, buffer=512)
            self.pg = pygame_module
            for name, recipe in SFX_RECIPES.items():
                self.sounds[name] = pygame_module.mixer.Sound(
                    buffer=_pcm16(recipe()))
            self.music = pygame_module.mixer.Sound(buffer=_pcm16(_music_loop()))
            self.enabled = True
            self.apply_volumes()
        except Exception:
            self.enabled = False

    def apply_volumes(self):
        if not self.enabled:
            return
        master = 0.0 if self.settings.get("muted") else float(
            self.settings.get("master_volume", 0.8))
        sfx = master * float(self.settings.get("sfx_volume", 0.9))
        mus = master * float(self.settings.get("music_volume", 0.6))
        for s in self.sounds.values():
            s.set_volume(sfx)
        if self.music is not None:
            self.music.set_volume(mus)

    def play(self, name):
        if self.enabled:
            s = self.sounds.get(name)
            if s is not None:
                s.play()

    def start_music(self):
        if self.enabled and self.music is not None:
            self.music.play(loops=-1)

    def stop_music(self):
        if self.enabled and self.music is not None:
            self.music.stop()
