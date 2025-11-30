def aggregate_counts_by_yz(coords, clamp_max=999999):
    if not coords:
        return []
    counts = {}
    for c in coords:
        z = int(c.get("z", 0))
        y = int(c.get("y", 0))
        key = (z, y)
        counts[key] = counts.get(key, 0) + 1
    out = []
    for (z, y), cnt in counts.items():
        if cnt < 0:
            cnt = 0
        if clamp_max is not None:
            try:
                m = int(clamp_max)
                if cnt > m:
                    cnt = m
            except Exception:
                pass
        out.append({"x": int(cnt), "y": int(y), "z": int(z), "t": 0.0})
    out.sort(key=lambda c: (c["z"], c["y"]))
    return out
