import numpy as np
import librosa


def map_note_to_y(note):
    n = int(note)
    if n <= 47:
        return 1
    if n <= 59:
        return 2
    if n <= 71:
        return 3
    if n <= 83:
        return 4
    return 5


def map_energy_level_to_y(level):
    lv = int(level)
    if lv <= 0:
        return 1
    if lv <= 3:
        return 2
    if lv <= 7:
        return 3
    if lv <= 11:
        return 4
    return 5


def audio_to_sliced_coords(input_path, x_unit="seconds", quant_x=None, subdiv=None, hop_length=512):
    y, sr = librosa.load(input_path, mono=True)
    if x_unit == "seconds" and quant_x is not None and quant_x > 0:
        step = float(quant_x)
        dur = float(len(y) / float(sr))
        n_steps = int(np.floor(dur / step))
        coords = []
        if n_steps <= 0:
            return coords
        energies = np.zeros(n_steps, dtype=float)
        win = int(round(step * sr))
        for i in range(n_steps):
            a = int(i * win)
            b = int((i + 1) * win)
            if a >= len(y):
                e = 0.0
            else:
                seg = y[a:b]
                if seg.size <= 0:
                    e = 0.0
                else:
                    e = float(np.sqrt(np.mean(seg * seg)))
            energies[i] = e
        if np.all(energies <= 0):
            for i in range(n_steps):
                t_sec = (i + 0.5) * step
                level = 0
                y_lane = map_energy_level_to_y(level)
                coords.append({"x": int(level), "y": int(y_lane), "z": int(i), "t": float(t_sec)})
            return coords
        thr = float(np.percentile(energies, 5.0))
        maxe = float(np.max(energies))
        if maxe <= thr:
            for i in range(n_steps):
                t_sec = (i + 0.5) * step
                val = energies[i]
                level = 0 if val <= 0 else 1
                y_lane = map_energy_level_to_y(level)
                coords.append({"x": int(level), "y": int(y_lane), "z": int(i), "t": float(t_sec)})
            return coords
        for i in range(n_steps):
            val = energies[i]
            if val <= thr:
                level = 0
            else:
                s = (val - thr) / (maxe - thr)
                if s < 0:
                    s = 0.0
                if s > 1:
                    s = 1.0
                level = 1 + int(round(s * 14.0))
                if level < 1:
                    level = 1
                if level > 15:
                    level = 15
            t_sec = (i + 0.5) * step
            y_lane = map_energy_level_to_y(level)
            coords.append({"x": int(level), "y": int(y_lane), "z": int(i), "t": float(t_sec)})
        return coords
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=hop_length, units="frames")
    if onset_frames is None or len(onset_frames) == 0:
        tempo_fallback, beat_frames_fb = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
        onset_frames = beat_frames_fb
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
    bps = float(tempo) / 60.0 if tempo and tempo > 0 else 2.0
    if quant_x is not None and quant_x > 0:
        step = float(quant_x)
    else:
        if x_unit == "beats":
            if subdiv is None or subdiv <= 0:
                subdiv = 32
            step = 1.0 / float(subdiv)
        elif x_unit == "ticks":
            step = 1.0
        else:
            step = 0.1
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    winners = {}
    coords = []
    n_frames_ch = chroma.shape[1] if chroma is not None and chroma.ndim == 2 else 0
    for f in onset_frames:
        fi = int(f)
        t_sec = float(librosa.frames_to_time(fi, sr=sr, hop_length=hop_length))
        if x_unit == "beats":
            z_val = t_sec * bps
        else:
            z_val = t_sec
        T = int(round(z_val / step))
        if n_frames_ch > 0:
            idx = fi if fi < n_frames_ch else (n_frames_ch - 1)
            ch = chroma[:, idx]
            if ch.size == 0:
                continue
            vmax = float(np.max(ch)) if np.max(ch) > 0 else 1.0
            vnorm = ch / vmax
            sel = np.where(vnorm >= 0.6)[0]
            if sel.size == 0:
                sel = np.array([int(np.argmax(vnorm))], dtype=int)
            if sel.size > 4:
                topk = np.argsort(-vnorm)[:4]
                sel = topk
            for pc in sel:
                note = int(pc + 60)
                key = (T, note)
                vel = float(ch[pc])
                prev = winners.get(key)
                if prev is None or vel > prev[0]:
                    winners[key] = (vel, 0, t_sec)
        else:
            note = 60
            key = (T, note)
            vel = 1.0
            prev = winners.get(key)
            if prev is None or vel > prev[0]:
                winners[key] = (vel, 0, t_sec)
    for (T, note), (vel, track, t_sec) in winners.items():
        y_lane = map_note_to_y(note)
        coords.append({"x": int(note), "y": int(y_lane), "z": int(T), "t": float(t_sec)})
    coords.sort(key=lambda c: (c["z"], c["x"], c["y"]))
    return coords


def get_audio_duration_seconds(input_path):
    y, sr = librosa.load(input_path, mono=True)
    return float(len(y) / float(sr))
