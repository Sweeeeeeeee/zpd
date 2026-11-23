"""Prefill missing frozen scan records with two independent solvers; let the usual runner finalize."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from collections import deque

# Load the immutable experiment checkout selected by the service.
sys.path.insert(0, str(Path.cwd()))
from bench.latvia.scan import prepare, run_case, write_json
from bench.latvia.scan_plan import sha256


def on_external_power():
    for supply in Path("/sys/class/power_supply").iterdir():
        supply_type = supply / "type"
        online = supply / "online"
        if supply_type.is_file() and online.is_file() and supply_type.read_text().strip() in {"Mains", "USB", "USB_C", "USB_PD"}:
            if online.read_text().strip() == "1":
                return True
    return False


def dispatch(jobs, evaluate, powered=on_external_power, poll_seconds=4):
    pending = deque(jobs)
    active = set()
    last_limit = None
    with ThreadPoolExecutor(max_workers=2) as workers:
        while pending or active:
            external = powered()
            limit = 2 if external else 1
            if limit != last_limit:
                print(f"Admitting up to {limit} solver(s), external power={external}", flush=True)
                last_limit = limit
            while pending and len(active) < limit:
                active.add(workers.submit(evaluate, pending.popleft(), external))
            if active:
                done, active = wait(active, timeout=poll_seconds, return_when=FIRST_COMPLETED)
                for future in done:
                    future.result()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("baseline", "retries"))
    parser.add_argument("state", type=Path)
    parser.add_argument("--cpus", required=True)
    args = parser.parse_args()
    args.state = args.state.resolve()
    cpus = {int(s) for s in args.cpus.split(",")}
    if len(cpus) != 2 or not cpus <= os.sched_getaffinity(0):
        raise ValueError("Two available, distinct physical cores are required")
    siblings = [Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list").read_text().strip()
                for cpu in cpus]
    if len(set(siblings)) != len(cpus):
        raise ValueError("CPU IDs share a physical core")
    os.sched_setaffinity(0, cpus)
    baseline = args.state / "latvia-domain-scan"
    is_retry = args.phase == "retries"
    output = args.state / "latvia-merge-retries" if is_retry else baseline
    method = args.state / "latvia-workflow" / f"execution-{args.phase}.json"
    if not (output / "inputs.json").is_file():
        raise ValueError("Expected an existing frozen study")
    with (output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if is_retry:
            from bench.latvia.retry_merges import affected, retry
            if not (baseline / "summary.json").is_file():
                raise ValueError("The original scan must be complete")
            retry(baseline, output, limit=0)
        cases, configs = prepare(output)
        jobs = []
        existing = {}
        for cfg in configs:
            existing[cfg.stem] = []
            for name, problem in cases.items():
                rel = Path("records") / cfg.stem / (name + ".json")
                path = output / rel
                if path.exists():
                    existing[cfg.stem].append(name)
                    continue
                origin = baseline / rel if is_retry else None
                if is_retry and not affected(json.loads(origin.read_text())):
                    continue
                jobs.append((cfg, name, problem, path, origin))
        descriptor = {
            "phase": args.phase, "solver_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "input_sha256": sha256(output / "inputs.json"), "workers": len(cpus), "logical_cpus": sorted(cpus),
            "cpu_model": next(l.split(":", 1)[1].strip() for l in Path("/proc/cpuinfo").read_text().splitlines() if l.startswith("model name")),
            "omp_threads": os.environ["OMP_NUM_THREADS"], "python_hash_seed": os.environ["PYTHONHASHSEED"],
        }
        if method.exists():
            prior = json.loads(method.read_text())
            if any(prior.get(k) != v for k, v in descriptor.items()):
                raise ValueError("The parallel execution settings have changed")
        else:
            write_json(method, {**descriptor, "parallel_start_unix": time.time(), "completed_before_parallel": existing,
                                "timing_note": "Listed cells predate the new scheduler. Subsequent independent cases could overlap on mains power. On battery the scheduler admitted one at a time. Each case kept its own wall-time and memory limits. Elapsed times and near-limit outcomes can depend on contention."})

        def evaluate(job, external):
            cfg, name, problem, path, origin = job
            timing_path = args.state / "latvia-workflow/execution" / args.phase / cfg.stem / (name + ".json")
            interval = {"config": cfg.stem, "name": name, "start_unix": time.time(), "external_power_at_start": external}
            write_json(timing_path, interval)
            row = run_case(path, name, problem, cfg)
            if origin is not None:
                row["baseline_record_sha256"] = sha256(origin)
                write_json(path, row)
            interval["finish_unix"] = time.time()
            write_json(timing_path, interval)
        print(f"Scheduling {len(jobs)} pending {args.phase} cases on CPUs {sorted(cpus)}", flush=True)
        dispatch(jobs, evaluate)
    if is_retry:
        command = ["bench.latvia.retry_merges", str(baseline), str(output)]
    else:
        command = ["bench.latvia.scan", str(output)]
    os.execv(sys.executable, [sys.executable, "-u", "-B", "-m", *command])


if __name__ == "__main__":
    main()
