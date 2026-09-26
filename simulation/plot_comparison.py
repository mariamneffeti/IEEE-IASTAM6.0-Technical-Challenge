"""Plot primary metrics from simulation.compare's long-format CSV summary."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


METRICS = [
    ("Decision Quality", "Decision quality ratio", 1.0),
    ("Completed-Task Rate", "Completed-task rate", 100.0),
    ("Energy Consumption (J)", "Total modeled energy (kJ)", 0.001),
    ("Latency (s)", "Completed-delivery latency (s)", 1.0),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default="results/comparison/comparison_summary.csv")
    parser.add_argument("--output", default="results/figures/policy_comparison.pdf")
    args = parser.parse_args()

    with Path(args.summary).open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    policies = list(dict.fromkeys(row["Policy"] for row in rows))
    labels = {
        "transmit_all": "Transmit-all",
        "greedy_edge": "Greedy-edge",
        "heuristic": "Heuristic",
    }
    labels.update({
        policy: (f"PPO ({policy.removeprefix('rl_astra_ppo_')})"
                 if policy.startswith("rl_astra_ppo_") else policy)
        for policy in policies if policy not in labels
    })

    figure, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for axis, (metric, title, scale) in zip(axes.flat, METRICS):
        metric_rows = [row for row in rows if row["Metric"] == metric]
        means = [float(next(row["Mean"] for row in metric_rows
                            if row["Policy"] == policy)) * scale
                 for policy in policies]
        lows = [float(next(row["CI95 Low"] for row in metric_rows
                           if row["Policy"] == policy)) * scale
                for policy in policies]
        highs = [float(next(row["CI95 High"] for row in metric_rows
                            if row["Policy"] == policy)) * scale
                 for policy in policies]
        errors = [[mean - low for mean, low in zip(means, lows)],
                  [high - mean for mean, high in zip(means, highs)]]
        positions = list(range(len(policies)))
        axis.bar(positions, means, color="#277da1", alpha=0.86)
        axis.errorbar(positions, means, yerr=errors, fmt="none", ecolor="#222",
                      capsize=4, linewidth=1)
        axis.set_xticks(positions, [labels[p] for p in policies])
        axis.set_title(title)
        axis.tick_params(axis="x", labelrotation=20)
        axis.grid(axis="y", alpha=0.25)

    figure.suptitle("ASTRA policy comparison (mean and 95% t interval)")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved comparison plot: {output}")


if __name__ == "__main__":
    main()
