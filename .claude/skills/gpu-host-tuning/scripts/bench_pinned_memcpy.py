#!/usr/bin/env python3
"""Pinned-host <-> GPU memcpy micro-benchmark — replicates the LMCache
CPU-tier offload path (torch pin_memory + cudaMemcpyAsync) so we can
ground-truth the actual H2D/D2H ceiling on a given box, independent of
LMCache itself.

Usage (called by collect.sh under different numactl bindings):
    numactl --membind=0 --cpunodebind=0  python3 bench_pinned_memcpy.py \
        --csv out.csv --tag membind0 --all-gpus
    numactl --membind=1 --cpunodebind=0  python3 bench_pinned_memcpy.py \
        --csv out.csv --tag membind1-cpu0 --all-gpus     # cross-NUMA
    numactl --interleave=all              python3 bench_pinned_memcpy.py \
        --csv out.csv --tag interleave --all-gpus

Sizes default to 16/64/256/1024 MiB — the 64–256 MiB band brackets the
LMCache chunk size (~85 MiB for an MLA model at TP=8, prefix=1024+suffix=256).

Output: append-mode CSV with one row per (tag, gpu, size, direction).
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path


def percentile(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * p))
    return sorted_vals[idx]


def measure(gpu, size_mb, direction, reps, warmup):
    import torch

    n_bytes = size_mb * 1024 * 1024
    n_floats = n_bytes // 4
    host = torch.empty(n_floats, dtype=torch.float32, pin_memory=True)
    host.fill_(1.0)
    dev = torch.empty(n_floats, dtype=torch.float32, device=gpu)
    stream = torch.cuda.Stream(device=gpu)
    is_h2d = direction == "H2D"

    # Warmup
    for _ in range(warmup):
        with torch.cuda.stream(stream):
            if is_h2d:
                dev.copy_(host, non_blocking=True)
            else:
                host.copy_(dev, non_blocking=True)
        stream.synchronize()
    torch.cuda.synchronize(gpu)

    # Measure
    latencies_ms = []
    for _ in range(reps):
        t0 = time.perf_counter_ns()
        with torch.cuda.stream(stream):
            if is_h2d:
                dev.copy_(host, non_blocking=True)
            else:
                host.copy_(dev, non_blocking=True)
        stream.synchronize()
        t1 = time.perf_counter_ns()
        latencies_ms.append((t1 - t0) / 1e6)

    del host, dev, stream
    torch.cuda.empty_cache()

    gbps = sorted(n_bytes / (lat * 1e6) for lat in latencies_ms)
    return {
        "throughput_gbps_mean": statistics.mean(gbps),
        "throughput_gbps_p50": percentile(gbps, 0.50),
        "throughput_gbps_p95": percentile(gbps, 0.95),
        "throughput_gbps_min": gbps[0],
        "latency_ms_mean": statistics.mean(latencies_ms),
        "n_reps": reps,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--all-gpus", action="store_true")
    ap.add_argument(
        "--sizes-mb",
        default="16,64,256,1024",
        help="comma-separated buffer sizes in MiB",
    )
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--csv", required=True)
    ap.add_argument(
        "--tag",
        required=True,
        help="free-form label e.g. membind0, membind1, interleave",
    )
    args = ap.parse_args()

    try:
        import torch
    except ImportError:
        print(
            "ERROR: torch not importable; run inside the vllm container "
            "or 'pip install torch'.",
            file=sys.stderr,
        )
        sys.exit(2)
    if not torch.cuda.is_available():
        print("ERROR: no CUDA devices visible.", file=sys.stderr)
        sys.exit(2)

    sizes = [int(s) for s in args.sizes_mb.split(",")]
    gpus = list(range(torch.cuda.device_count())) if args.all_gpus else [args.gpu]

    csv_path = Path(args.csv)
    new_file = not csv_path.exists()
    fh = csv_path.open("a", newline="")
    w = csv.writer(fh)
    if new_file:
        w.writerow(
            [
                "tag",
                "gpu",
                "gpu_name",
                "size_mb",
                "direction",
                "throughput_gbps_mean",
                "throughput_gbps_p50",
                "throughput_gbps_p95",
                "throughput_gbps_min",
                "latency_ms_mean",
                "n_reps",
            ]
        )

    for gpu in gpus:
        torch.cuda.set_device(gpu)
        gpu_name = torch.cuda.get_device_name(gpu)
        for size_mb in sizes:
            for direction in ("H2D", "D2H"):
                try:
                    r = measure(gpu, size_mb, direction, args.reps, args.warmup)
                except Exception as e:
                    print(
                        f"  [{args.tag} gpu{gpu} {size_mb}MB {direction}] FAILED: {e}",
                        file=sys.stderr,
                    )
                    continue
                w.writerow(
                    [
                        args.tag,
                        gpu,
                        gpu_name,
                        size_mb,
                        direction,
                        f"{r['throughput_gbps_mean']:.3f}",
                        f"{r['throughput_gbps_p50']:.3f}",
                        f"{r['throughput_gbps_p95']:.3f}",
                        f"{r['throughput_gbps_min']:.3f}",
                        f"{r['latency_ms_mean']:.3f}",
                        r["n_reps"],
                    ]
                )
                fh.flush()
                print(
                    f"  [{args.tag} gpu{gpu} {size_mb}MB {direction}] "
                    f"mean={r['throughput_gbps_mean']:.2f} GB/s "
                    f"p50={r['throughput_gbps_p50']:.2f} "
                    f"p95={r['throughput_gbps_p95']:.2f} "
                    f"min={r['throughput_gbps_min']:.2f}"
                )

    fh.close()


if __name__ == "__main__":
    main()
