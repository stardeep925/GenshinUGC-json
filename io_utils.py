import json

def save_dictvec(coords, path, per_list_limit=100):
    vecs_all = []
    zs_src = [int(c.get("z", 0)) for c in coords]
    if zs_src:
        z_min = min(zs_src)
        z_max = max(zs_src)
        span = (z_max - z_min + 1)
        center = (z_min + z_max) / 2.0
        scale = 1.0 if span <= 1000 else (1000.0 / float(span))
    else:
        center = 0.0
        scale = 1.0
    for c in coords:
        x = int(c.get("x", 0))
        y = int(c.get("y", 0))
        z0 = int(c.get("z", 0))
        z = int(round((z0 - center) * scale))
        if z < -500:
            z = -500
        if z > 499:
            z = 499
        t = float(c.get("t", 0.0))
        vecs_all.append((t, x, y, z))
    vecs_all.sort(key=lambda r: (r[3], r[1], r[2]))
    entries = []
    chunks = [vecs_all[i:i+per_list_limit] for i in range(0, len(vecs_all), per_list_limit)]
    for idx, chunk in enumerate(chunks, start=1):
        vecs = [f"{x},{y},{z}" for (t, x, y, z) in chunk]
        entries.append({
            "key": {"param_type": "Int32", "value": str(idx)},
            "value": {"param_type": "Vector3List", "value": vecs}
        })
    obj = {
        "type": "Dict",
        "key_type": "Int32",
        "value_type": "Vector3List",
        "value": entries,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
 
def compute_summary(coords, raw_coords, max_jump=None, max_z_gap=2):
    total_raw = len(raw_coords) if raw_coords is not None else 0
    total_out = len(coords) if coords is not None else 0
    xs = [int(c.get("x", 0)) for c in coords] if coords else []
    ys = [int(c.get("y", 0)) for c in coords] if coords else []
    zs = [int(c.get("z", 0)) for c in coords] if coords else []
    ux = sorted(set(xs)) if xs else []
    uz = sorted(set(zs)) if zs else []
    platform_count = sum(int(c.get("x", 0)) for c in (coords or []))
    raw_xs = [int(c.get("x", 0)) for c in (raw_coords or [])]
    raw_tracks = sorted(set(raw_xs)) if raw_xs else []
    per_track = {}
    for x in xs:
        per_track[x] = per_track.get(x, 0) + 1
    per_z = {}
    z_to_xs = {}
    for c in coords or []:
        z = int(c.get("z", 0))
        per_z[z] = per_z.get(z, 0) + 1
        s = z_to_xs.get(z)
        if s is None:
            s = set()
            z_to_xs[z] = s
        s.add(int(c.get("x", 0)))
    z_sorted = sorted(z_to_xs.keys())
    playable_path_reachable = None
    reachable_steps = 0
    if max_jump is not None and z_sorted:
        groups = {}
        for c in coords or []:
            z = int(c.get("z", 0))
            groups.setdefault(z, []).append(c)
        zs = sorted(groups.keys())
        if zs:
            states = []
            for _ in zs:
                states.append([])
            for c in groups[zs[0]]:
                states[0].append({"len": 1})
            for i in range(1, len(zs)):
                zi = zs[i]
                cur_list = groups[zi]
                states[i] = [{"len": 0} for _ in cur_list]
                best_prev_len = 0
                for j in range(max(0, i - (max_z_gap + 1)), i):
                    zj = zs[j]
                    prev_list = groups[zj]
                    for idx_cur, c_cur in enumerate(cur_list):
                        x2 = int(c_cur.get("x", 0)); y2 = int(c_cur.get("y", 0))
                        z2 = int(c_cur.get("z", 0))
                        local_best = states[i][idx_cur]["len"]
                        for idx_prev, c_prev in enumerate(prev_list):
                            if states[j][idx_prev]["len"] <= 0:
                                continue
                            x1 = int(c_prev.get("x", 0)); y1 = int(c_prev.get("y", 0))
                            z1 = int(c_prev.get("z", 0))
                            dx = x2 - x1; dy = y2 - y1; dz = z2 - z1
                            dist2 = dx*dx + dy*dy + dz*dz
                            if dist2 <= float(max_jump) * float(max_jump):
                                cand = states[j][idx_prev]["len"] + 1
                                if cand > local_best:
                                    local_best = cand
                        if local_best > states[i][idx_cur]["len"]:
                            states[i][idx_cur]["len"] = local_best
                        if local_best > best_prev_len:
                            best_prev_len = local_best
                for idx_cur in range(len(cur_list)):
                    if states[i][idx_cur]["len"] == 0:
                        states[i][idx_cur]["len"] = 1
                reachable_steps = max(reachable_steps, max(s.get("len", 0) for s in states[i]))
            last_best = max((s.get("len", 0) for s in states[-1]), default=0)
            playable_path_reachable = bool(last_best >= 1)
    top_z = sorted(per_z.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    far = None
    if coords:
        far = max(coords, key=lambda c: (int(c.get("z", 0)), -int(c.get("x", 0)), -int(c.get("y", 0))))
    summary = {
        "total_raw": int(total_raw),
        "total_out": int(total_out),
        "time_entries": int(len(uz)),
        "platform_count": int(platform_count),
        "note_count": int(total_raw),
        "unique_tracks": int(len(ux)),
        "unique_tracks_raw": int(len(raw_tracks)),
        "unique_steps": int(len(uz)),
        "x_min": int(min(ux)) if ux else 0,
        "x_max": int(max(ux)) if ux else 0,
        "y_min": int(min(ys)) if ys else 0,
        "y_max": int(max(ys)) if ys else 0,
        "z_min": int(min(uz)) if uz else 0,
        "z_max": int(max(uz)) if uz else 0,
        "avg_platforms_per_z": float((total_out / max(1, len(uz)))) if uz else 0.0,
        "per_track_counts": {str(k): int(v) for k, v in sorted(per_track.items(), key=lambda kv: kv[0])},
        "top_z_counts": [{"z": int(k), "count": int(v)} for k, v in top_z],
        "path_reachable_with_max_jump": playable_path_reachable,
        "reachable_steps": int(reachable_steps),
        "farthest_coord": ({
            "x": int(far.get("x", 0)),
            "y": int(far.get("y", 0)),
            "z": int(far.get("z", 0)),
            "t": float(far.get("t", 0.0)),
        } if far else None),
    }
    return summary


def save_summary(path, summary_obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary_obj, f, ensure_ascii=False, indent=2)


def format_summary_cn(summary, max_items=10):
    lines = []
    lines.append(f"生成的坐标数量: {summary.get('platform_count', summary.get('total_out', 0))}")
    lines.append(f"时间条目数量: {summary.get('time_entries', 0)}")
    lines.append(f"音符总数: {summary.get('note_count', summary.get('total_raw', 0))}")
    lines.append(f"轨道数量(生成): {summary.get('unique_tracks', 0)}")
    lines.append(f"轨道数量(原始): {summary.get('unique_tracks_raw', 0)}")
    lines.append(f"Z步数: {summary.get('unique_steps', 0)}")
    lines.append(f"X范围: {summary.get('x_min', 0)} ~ {summary.get('x_max', 0)}")
    lines.append(f"Y范围: {summary.get('y_min', 0)} ~ {summary.get('y_max', 0)}")
    lines.append(f"Z范围: {summary.get('z_min', 0)} ~ {summary.get('z_max', 0)}")
    far = summary.get('farthest_coord')
    if far:
        lines.append(f"最远坐标位置: x={far.get('x')}, y={far.get('y')}, z={far.get('z')} (t={far.get('t'):.2f}s)")
    lines.append(f"每个Z平均平台数: {summary.get('avg_platforms_per_z', 0.0):.2f}")
    pr = summary.get('path_reachable_with_max_jump')
    if pr is not None:
        lines.append(f"在当前最大横跳约束下是否可贯通: {'是' if pr else '否'}")
        lines.append(f"可达连续步数: {summary.get('reachable_steps', 0)}")
    ptc = summary.get('per_track_counts', {})
    if ptc:
        items = sorted(((int(k), v) for k, v in ptc.items()), key=lambda kv: kv[0])
        lines.append("各轨道平台数量:")
        for k, v in items[:max_items]:
            lines.append(f"  轨道 {k}: {v}")
        if len(items) > max_items:
            lines.append(f"  ...(共 {len(items)} 条轨道)" )
    tz = summary.get('top_z_counts', [])
    if tz:
        lines.append("平台最密集的Z位置:")
        for item in tz[:max_items]:
            lines.append(f"  Z={item.get('z')}: {item.get('count')} 平台")
    return "\n".join(lines)


def save_summary_cn(path, summary_text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(summary_text)
