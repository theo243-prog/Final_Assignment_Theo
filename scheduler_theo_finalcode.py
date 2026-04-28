import time
import random
import math
import numpy as np

# ─────────────────────────────────────────────
# Task definition
# ─────────────────────────────────────────────

class Task:
    def __init__(self, name, wcet, period, deadline=None):
        self.name = name
        self.wcet = wcet
        self.period = period
        self.deadline = deadline if deadline else period


# ─────────────────────────────────────────────
# Part 1 - Measure WCET of tau1
# ─────────────────────────────────────────────

def measure_tau1(n=1000):
    times = []
    print(f"Measuring tau1 execution time ({n} iterations)...")
    for _ in range(n):
        a = random.getrandbits(10000)
        b = random.getrandbits(10000)
        start = time.perf_counter()
        _ = a * b
        end = time.perf_counter()
        times.append(end - start)

    arr = np.array(times)
    print("-" * 40)
    print(f"Min    : {np.min(arr):.10f} s")
    print(f"Q1     : {np.percentile(arr, 25):.10f} s")
    print(f"Median : {np.percentile(arr, 50):.10f} s")
    print(f"Q3     : {np.percentile(arr, 75):.10f} s")
    print(f"WCET   : {np.max(arr):.10f} s")
    print("-" * 40)
    return float(np.max(arr))


# ─────────────────────────────────────────────
# Part 2 - Schedulability analysis
# ─────────────────────────────────────────────

def compute_utilization(tasks):
    return sum(t.wcet / t.period for t in tasks)

def rm_bound(n):
    return n * (2 ** (1.0 / n) - 1)

def response_time_analysis(tasks):
    # RM priority: shorter period = higher priority
    sorted_tasks = sorted(tasks, key=lambda t: t.period)
    results = []
    for i, task in enumerate(sorted_tasks):
        hp = sorted_tasks[:i]
        R = task.wcet
        for _ in range(500):
            R_new = task.wcet + sum(math.ceil(R / h.period) * h.wcet for h in hp)
            if abs(R_new - R) < 1e-9:
                break
            R = R_new
            if R > task.deadline:
                R = float('inf')
                break
        results.append({
            "name": task.name,
            "C": task.wcet,
            "T": task.period,
            "D": task.deadline,
            "R": R,
            "ok": R <= task.deadline,
        })
    return results


# ─────────────────────────────────────────────
# Part 3 - Non-preemptive EDF scheduler
# ─────────────────────────────────────────────

def lcm(a, b):
    return a * b // math.gcd(a, b)

def get_hyperperiod(tasks):
    H = 1
    for t in tasks:
        H = lcm(H, t.period)
    return H

def run_schedule(tasks, relax_tau5=False):
    H = get_hyperperiod(tasks)
    label = "Scenario 2 - tau5 relaxed" if relax_tau5 else "Scenario 1 - strict"
    print(f"\n{'='*50}")
    print(f"  {label}  |  H = {H} ms")
    print(f"{'='*50}")

    # Generate all jobs
    jobs = []
    for task in tasks:
        n_jobs = H // task.period
        for k in range(n_jobs):
            jobs.append({
                "name":     task.name,
                "release":  k * task.period,
                "deadline": k * task.period + task.deadline,
                "C":        task.wcet,
                "start":    None,
                "finish":   None,
            })

    pending = list(jobs)
    scheduled = []
    clock = 0

    while pending:
        ready = [j for j in pending if j["release"] <= clock]

        if not ready:
            clock = min(j["release"] for j in pending)
            continue

        # EDF key - tau5 deprioritized in scenario 2
        def key(j):
            penalty = 10**9 if (relax_tau5 and j["name"] == "tau5") else 0
            return (penalty, j["deadline"])

        ready.sort(key=key)
        job = ready[0]
        pending.remove(job)

        job["start"]  = clock
        job["finish"] = clock + job["C"]
        clock = job["finish"]

        missed = "MISS" if job["finish"] > job["deadline"] else "ok"
        wait   = job["start"] - job["release"]
        print(f"  t={job['start']:5.1f} -> {job['finish']:5.1f}  "
              f"{job['name']:5}  dl={job['deadline']:4}  wait={wait:.1f}  [{missed}]")
        scheduled.append(job)

    total_wait = sum(j["start"] - j["release"] for j in scheduled)
    total_exec = sum(j["C"] for j in scheduled)
    idle       = H - total_exec
    missed_all = [j for j in scheduled if j["finish"] > j["deadline"]]

    print(f"\n  Total waiting : {total_wait} ms")
    print(f"  Idle time     : {idle} ms")
    print(f"  Missed        : {len(missed_all)}")
    return scheduled, total_wait, idle


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    # 1. Measure tau1
    wcet_s = measure_tau1(1000)
    # Convert to ms and round up, minimum 1 ms
    C1 = max(1, math.ceil(wcet_s * 1000))
    print(f"\nC1 = {C1} ms  (raw WCET = {wcet_s*1e6:.2f} us)")

    # 2. Define task set
    tasks = [
        Task("tau1", C1, 10),
        Task("tau2", 3,  10),
        Task("tau3", 2,  20),
        Task("tau4", 2,  20),
        Task("tau5", 2,  40),
        Task("tau6", 2,  40),
        Task("tau7", 3,  80),
    ]

    print("\nTask set:")
    print(f"  {'Task':6} {'C':>4} {'T':>4} {'D':>4}")
    print("  " + "-"*20)
    for t in tasks:
        print(f"  {t.name:6} {t.wcet:>4} {t.period:>4} {t.deadline:>4}")

    # 3. Schedulability
    U  = compute_utilization(tasks)
    Ub = rm_bound(len(tasks))
    print(f"\nUtilization U = {U:.4f}")
    print(f"RM bound (n=7) = {Ub:.4f}")
    print(f"Sufficient condition: {'YES' if U <= Ub else 'NO -> use RTA'}")

    rta = response_time_analysis(tasks)
    print(f"\nResponse Time Analysis:")
    print(f"  {'Task':6} {'C':>4} {'T':>4} {'D':>4} {'R':>8}  OK?")
    print("  " + "-"*32)
    for r in rta:
        Rs = f"{r['R']:.0f}" if r["R"] != float("inf") else "inf"
        print(f"  {r['name']:6} {r['C']:>4} {r['T']:>4} {r['D']:>4} {Rs:>8}  {'yes' if r['ok'] else 'MISS'}")

    # 4. Run both scenarios
    sched_A, wait_A, idle_A = run_schedule(tasks, relax_tau5=False)
    sched_B, wait_B, idle_B = run_schedule(tasks, relax_tau5=True)

    print(f"\n{'='*40}")
    print(f"  {'Metric':<25} {'Sc.1':>6} {'Sc.2':>6}")
    print(f"  {'-'*38}")
    print(f"  {'Total waiting (ms)':<25} {wait_A:>6} {wait_B:>6}")
    print(f"  {'Idle time (ms)':<25} {idle_A:>6} {idle_B:>6}")
    print(f"{'='*40}")

    # 5. Export results
    import os, json
    os.makedirs("results", exist_ok=True)

    def export(sched, path):
        with open(path, "w") as f:
            f.write(f"{'Job':<8} {'Rel':>5} {'Start':>6} {'Finish':>7} "
                    f"{'DL':>5} {'R':>5} {'Wait':>5} {'Miss':>5}\n")
            f.write("-"*50 + "\n")
            for j in sched:
                R    = j["finish"] - j["release"]
                wait = j["start"]  - j["release"]
                miss = "YES" if j["finish"] > j["deadline"] else "no"
                f.write(f"{j['name']:<8} {j['release']:>5.0f} {j['start']:>6.1f} "
                        f"{j['finish']:>7.1f} {j['deadline']:>5.0f} "
                        f"{R:>5.0f} {wait:>5.0f} {miss:>5}\n")

    export(sched_A, "results/schedule_A.txt")
    export(sched_B, "results/schedule_B.txt")
    print("\nResults saved to results/")

if __name__ == "__main__":
    main()
