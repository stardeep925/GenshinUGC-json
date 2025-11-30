import argparse
import os
from midi_reader import midi_to_sliced_coords, get_midi_duration_seconds
from processing import aggregate_counts_by_yz
from io_utils import save_dictvec, compute_summary
from audio_reader import audio_to_sliced_coords, get_audio_duration_seconds as get_audio_duration_seconds_audio
 
 
def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=False)
    parser.add_argument("-x", "--x-unit", choices=["seconds", "beats", "ticks"], default="seconds")
    parser.add_argument("-o", "--output", required=False)
    parser.add_argument("--quant-x", type=float, required=False)
    parser.add_argument("--subdiv", type=int, required=False)
    parser.add_argument("--max-jump", type=int, default=5, help="Maximum lateral step per z step on x axis")
    return parser


def resolve_input_path(args, parser):
    input_path = args.input
    if not input_path:
        default = os.path.join(os.getcwd(), "1.mid")
        if os.path.exists(default):
            input_path = default
        else:
            parser.error("input file required")
    return input_path


def is_midi_file(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in [".mid", ".midi"]


def load_coords_for_input(input_path, args):
    is_midi = is_midi_file(input_path)
    if is_midi:
        coords_raw = midi_to_sliced_coords(
            input_path,
            args.x_unit,
            quant_x=args.quant_x,
            subdiv=args.subdiv,
        )
        counts = aggregate_counts_by_yz(coords_raw, clamp_max=999999)
        coords = counts
    else:
        coords_raw = audio_to_sliced_coords(
            input_path,
            args.x_unit,
            quant_x=args.quant_x,
            subdiv=args.subdiv,
        )
        if args.x_unit == "seconds" and args.quant_x is not None and args.quant_x > 0:
            coords = coords_raw
        else:
            counts = aggregate_counts_by_yz(coords_raw, clamp_max=999999)
            coords = counts
    return coords_raw, coords, is_midi


def get_duration_seconds_safe(input_path, is_midi):
    try:
        if is_midi:
            return get_midi_duration_seconds(input_path)
        return get_audio_duration_seconds_audio(input_path)
    except Exception:
        return None


def resolve_output_path(args, input_path):
    out_path = args.output
    if not out_path:
        base = os.path.splitext(os.path.basename(input_path))[0]
        out_path = os.path.join(os.path.dirname(input_path), f"{base}_xyz.json")
    return out_path


def compute_effective_step(args):
    if args.quant_x is not None and args.quant_x > 0:
        return float(args.quant_x)
    if args.x_unit == "beats":
        return (1.0 / float(args.subdiv)) if args.subdiv and args.subdiv > 0 else (1.0 / 32.0)
    if args.x_unit == "ticks":
        return 1.0
    return 0.1


def build_report_stats(coords, coords_raw, summary, args, input_path, out_path, is_midi, duration_s):
    xs = [int(c.get("x", 0)) for c in coords]
    ys = [int(c.get("y", 0)) for c in coords]
    zs = [int(c.get("z", 0)) for c in coords]
    total_rows = len(coords)
    total_platforms = sum(xs)
    unique_y = sorted(set(ys))
    unique_z = sorted(set(zs))
    per_y_platforms = {}
    for c in coords:
        y = int(c.get("y", 0))
        per_y_platforms[y] = per_y_platforms.get(y, 0) + int(c.get("x", 0))
    per_z_platforms = {}
    for c in coords:
        z = int(c.get("z", 0))
        per_z_platforms[z] = per_z_platforms.get(z, 0) + int(c.get("x", 0))
    top_z = sorted(per_z_platforms.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    x_min = min(xs) if xs else 0
    x_max = max(xs) if xs else 0
    y_min = min(unique_y) if unique_y else 0
    y_max = max(unique_y) if unique_y else 0
    z_min = min(unique_z) if unique_z else 0
    z_max = max(unique_z) if unique_z else 0
    eff_step = compute_effective_step(args)
    entries_written = len(coords)
    avgpz = summary.get("avg_platforms_per_z", 0.0)
    pr = summary.get("path_reachable_with_max_jump")
    rs = summary.get("reachable_steps")
    base = os.path.splitext(os.path.basename(input_path))[0]
    kind = "MIDI" if is_midi else "音频"
    return {
        "kind": kind,
        "base": base,
        "out_path": out_path,
        "duration_s": duration_s,
        "entries_written": entries_written,
        "total_platforms": total_platforms,
        "unique_y": unique_y,
        "unique_z": unique_z,
        "total_rows": total_rows,
        "coords_raw_len": len(coords_raw),
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "z_min": z_min,
        "z_max": z_max,
        "per_y_platforms": per_y_platforms,
        "top_z": top_z,
        "eff_step": eff_step,
        "summary": summary,
        "path_reachable": pr,
        "reachable_steps": rs,
        "avg_platforms_per_z": avgpz,
        "args": args,
    }


def print_report(report):
    reset = "\033[0m"
    bold = "\033[1m"
    cyan = "\033[36m"
    green = "\033[32m"
    yellow = "\033[33m"
    magenta = "\033[35m"
    blue = "\033[34m"
    gray = "\033[90m"

    def line(h, v):
        print(f"{h}{v}{reset}")

    kind = report.get("kind", "")
    base = report.get("base", "")
    out_path = report.get("out_path", "")
    duration_s = report.get("duration_s")
    eff_step = report.get("eff_step", 0.0)
    args = report.get("args")
    summary = report.get("summary", {})

    print(f"{bold}{cyan}=== {kind} 生成报告 ==={reset}")
    line(blue, f"文件: {base}")
    line(blue, f"输出: {out_path}")
    if duration_s is not None:
        line(blue, f"时长: {duration_s:.2f}s")
    print(f"{gray}{'-'*40}{reset}")
    if args is not None:
        line(magenta, f"参数: x_unit={args.x_unit}, quant_x={args.quant_x if args.quant_x is not None else 'auto'}, subdiv={args.subdiv if args.subdiv else 'auto'}, 有效步长={eff_step}")
    print(f"{gray}{'-'*40}{reset}")
    line(green, f"写入 JSON 数据条目: {report.get('entries_written', 0)}")
    line(green, f"生成的平台数量(展开): {report.get('total_platforms', 0)}")
    unique_z = report.get("unique_z", [])
    line(green, f"时间步数量(z 去重): {len(unique_z)}")
    line(green, f"坐标行数(每行 z,y 一条): {report.get('total_rows', 0)}")
    line(green, f"切片坐标条目数(原始): {report.get('coords_raw_len', 0)}")
    print(f"{gray}{'-'*40}{reset}")
    line(yellow, f"计数范围 x: {report.get('x_min', 0)} ~ {report.get('x_max', 0)}")
    unique_y = report.get("unique_y", [])
    line(yellow, f"Y 轨范围: {report.get('y_min', 0)} ~ {report.get('y_max', 0)} (共 {len(unique_y)})")
    line(yellow, f"Z 范围: {report.get('z_min', 0)} ~ {report.get('z_max', 0)}")
    far = summary.get("farthest_coord")
    if far:
        line(yellow, f"最远坐标: x={far.get('x')}, y={far.get('y')}, z={far.get('z')} (t={far.get('t'):.2f}s)")
    print(f"{gray}{'-'*40}{reset}")
    pr = report.get("path_reachable")
    rs = report.get("reachable_steps")
    if pr is not None:
        line(cyan, f"可贯通: {'是' if pr else '否'}  (可达连续步数: {rs})")
    avgpz = report.get("avg_platforms_per_z", 0.0)
    line(cyan, f"平均每 Z 平台数: {avgpz:.2f}")
    print(f"{gray}{'-'*40}{reset}")
    per_y_platforms = report.get("per_y_platforms", {})
    if per_y_platforms:
        top_y = sorted(per_y_platforms.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        print(f"{bold}各 Y 轨平台数 Top10:{reset}")
        for y, v in top_y:
            line(magenta, f"  Y={y}: {v}")
    top_z = report.get("top_z", [])
    if top_z:
        print(f"{bold}平台最密集的 Z Top10:{reset}")
        for z, v in top_z:
            line(magenta, f"  Z={z}: {v}")
    print(f"{gray}{'-'*40}{reset}")


def main():
    parser = build_parser()
    args = parser.parse_args()
    input_path = resolve_input_path(args, parser)
    coords_raw, coords, is_midi = load_coords_for_input(input_path, args)
    duration_s = get_duration_seconds_safe(input_path, is_midi)
    out_path = resolve_output_path(args, input_path)
    save_dictvec(coords, out_path)
    summary = compute_summary(coords, coords_raw, max_jump=args.max_jump)
    report = build_report_stats(coords, coords_raw, summary, args, input_path, out_path, is_midi, duration_s)
    print_report(report)


if __name__ == "__main__":
    main()
