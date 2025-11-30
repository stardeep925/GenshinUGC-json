from mido import MidiFile, tick2second


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


def midi_to_sliced_coords(input_path, x_unit="seconds", quant_x=None, subdiv=None):
    midi = MidiFile(input_path)
    tpb = midi.ticks_per_beat
    tempo_changes = [(0, 500000)]
    if midi.tracks:
        abs0 = 0
        for msg in midi.tracks[0]:
            dt = getattr(msg, "time", 0)
            abs0 += dt
            if getattr(msg, "type", "") == "set_tempo":
                tempo_changes.append((abs0, msg.tempo))

    def ticks_to_seconds(T):
        prev_tick = 0
        prev_tempo = tempo_changes[0][1]
        total = 0.0
        for i in range(1, len(tempo_changes)):
            tick_i, tempo_i = tempo_changes[i]
            if T <= tick_i:
                total += tick2second(T - prev_tick, tpb, prev_tempo)
                return total
            total += tick2second(tick_i - prev_tick, tpb, prev_tempo)
            prev_tick = tick_i
            prev_tempo = tempo_i
        total += tick2second(T - prev_tick, tpb, prev_tempo)
        return total

    # Gather note intervals with start/end
    active = {}
    prog_by_tch = {}
    intervals = []
    for ti, track in enumerate(midi.tracks):
        abs_ticks = 0
        for msg in track:
            dt = getattr(msg, "time", 0)
            abs_ticks += dt
            mtype = getattr(msg, "type", "")
            if mtype == "program_change":
                ch = getattr(msg, "channel", 0)
                prog_by_tch[(ti, ch)] = getattr(msg, "program", 0)
                continue
            if mtype == "note_on" and getattr(msg, "velocity", 0) > 0:
                ch = getattr(msg, "channel", 0)
                key = (ti, ch, getattr(msg, "note", 0))
                lst = active.get(key)
                if lst is None:
                    lst = []
                    active[key] = lst
                lst.append({
                    "note": getattr(msg, "note", 0),
                    "start_ticks": abs_ticks,
                    "start_beats": abs_ticks / float(tpb),
                    "start_seconds": ticks_to_seconds(abs_ticks),
                    "track": ti,
                    "channel": ch,
                    "velocity": getattr(msg, "velocity", 0),
                    "program": prog_by_tch.get((ti, ch), 0),
                })
            elif mtype == "note_off" or (mtype == "note_on" and getattr(msg, "velocity", 0) == 0):
                ch = getattr(msg, "channel", 0)
                key = (ti, ch, getattr(msg, "note", 0))
                lst = active.get(key)
                if lst:
                    info = lst.pop(0)
                    end_ticks = abs_ticks
                    start_ticks = int(info["start_ticks"]) 
                    if end_ticks < start_ticks:
                        end_ticks = start_ticks
                    interval = {
                        "note": int(info["note"]),
                        "track": int(info["track"]),
                        "channel": int(info["channel"]),
                        "velocity": int(info.get("velocity", 0)),
                        "program": int(info.get("program", 0)),
                        "start_ticks": int(start_ticks),
                        "end_ticks": int(end_ticks),
                        "start_beats": float(info["start_beats"]),
                        "end_beats": float(end_ticks / float(tpb)),
                        "start_seconds": float(info["start_seconds"]),
                        "end_seconds": float(ticks_to_seconds(end_ticks)),
                    }
                    intervals.append(interval)
    # close lingering actives: make minimal interval
    for key, lst in active.items():
        for info in lst:
            start_ticks = int(info["start_ticks"])
            end_ticks = start_ticks
            interval = {
                "note": int(info["note"]),
                "track": int(info["track"]),
                "channel": int(info["channel"]),
                "velocity": int(info.get("velocity", 0)),
                "program": int(info.get("program", 0)),
                "start_ticks": int(start_ticks),
                "end_ticks": int(end_ticks),
                "start_beats": float(info["start_beats"]),
                "end_beats": float(start_ticks / float(tpb)),
                "start_seconds": float(info["start_seconds"]),
                "end_seconds": float(info["start_seconds"]),
            }
            intervals.append(interval)

    # determine step by unit
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

    # slice intervals into time steps
    winners = {}  # key: (T, x) -> (velocity, track, t_seconds)
    for iv in intervals:
        note = int(iv["note"])  # x
        track = int(iv["track"])  # y
        vel = int(iv.get("velocity", 0))
        if x_unit == "beats":
            z0 = float(iv["start_beats"]) 
            z1 = float(iv["end_beats"]) 
        elif x_unit == "ticks":
            z0 = float(iv["start_ticks"]) 
            z1 = float(iv["end_ticks"]) 
        else:
            z0 = float(iv["start_seconds"]) 
            z1 = float(iv["end_seconds"]) 
        if z1 < z0:
            z1 = z0
        T0 = int(round(z0 / step))
        T1 = int(round(z1 / step))
        if T1 < T0:
            T1 = T0
        for T in range(T0, T1 + 1):
            if x_unit == "beats":
                z_val = T * step
                ticks = int(round(z_val * tpb))
                t_sec = float(ticks_to_seconds(ticks))
            elif x_unit == "ticks":
                ticks = int(round(T * step))
                t_sec = float(ticks_to_seconds(ticks))
            else:
                z_val = T * step
                t_sec = float(z_val)
            key = (int(T), int(note))
            prev = winners.get(key)
            if prev is None or vel > prev[0] or (vel == prev[0] and track < prev[1]):
                winners[key] = (vel, track, t_sec)

    coords = []
    for (T, note), (vel, track, t_sec) in winners.items():
        y_lane = map_note_to_y(note)
        coords.append({
            "x": int(note),
            "y": int(y_lane),
            "z": int(T),
            "t": float(t_sec),
        })
    coords.sort(key=lambda c: (c["z"], c["x"], c["y"]))
    return coords


def get_midi_duration_seconds(input_path):
    midi = MidiFile(input_path)
    tpb = midi.ticks_per_beat
    tempo_changes = [(0, 500000)]
    if midi.tracks:
        abs0 = 0
        for msg in midi.tracks[0]:
            dt = getattr(msg, "time", 0)
            abs0 += dt
            if getattr(msg, "type", "") == "set_tempo":
                tempo_changes.append((abs0, msg.tempo))

    def ticks_to_seconds(T):
        prev_tick = 0
        prev_tempo = tempo_changes[0][1]
        total = 0.0
        for i in range(1, len(tempo_changes)):
            tick_i, tempo_i = tempo_changes[i]
            if T <= tick_i:
                total += tick2second(T - prev_tick, tpb, prev_tempo)
                return total
            total += tick2second(tick_i - prev_tick, tpb, prev_tempo)
            prev_tick = tick_i
            prev_tempo = tempo_i
        total += tick2second(T - prev_tick, tpb, prev_tempo)
        return total

    # compute maximum absolute ticks across tracks
    max_abs_ticks = 0
    for track in midi.tracks:
        abs_ticks = 0
        for msg in track:
            abs_ticks += getattr(msg, "time", 0)
        if abs_ticks > max_abs_ticks:
            max_abs_ticks = abs_ticks
    return float(ticks_to_seconds(max_abs_ticks))
