"""Run a paired-seed benchmark across reference and learned ASTRA policies."""

import argparse
import csv
import math
import statistics
from pathlib import Path

from simulation.baseline import heuristic_agent
from simulation.eval import RLAdapterState, run_episode, summarize_episodes
from simulation.policies import greedy_edge_agent, transmit_all_agent
from simulation.satellite_sim import SimConfig


POLICIES = {
    "transmit_all": transmit_all_agent,
    "greedy_edge": greedy_edge_agent,
    "heuristic": heuristic_agent,
}


def load_rl_agent(model_path: str):
    try:
        from sb3_contrib import MaskablePPO
    except ImportError as exc:
        raise RuntimeError(
            "RL comparisons require sb3-contrib and its dependencies; "
            "install repository requirements first."
        ) from exc
    model = MaskablePPO.load(model_path)
    return RLAdapterState(model, cfg=SimConfig())


def _write_csv(path: Path, fieldnames: list, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def paired_difference_rows(episode_rows: list, reference: str) -> list:
    metric_names = [key for key in episode_rows[0]
                    if key not in {"Policy", "Seed"}]
    by_policy_seed = {(row["Policy"], row["Seed"]): row for row in episode_rows}
    seeds = sorted({row["Seed"] for row in episode_rows})
    result = []
    challengers = sorted({row["Policy"] for row in episode_rows} - {reference})
    critical = {
        2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571,
        7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262, 11: 2.228,
        12: 2.201, 13: 2.179, 14: 2.160, 15: 2.145, 16: 2.131,
        17: 2.120, 18: 2.110, 19: 2.101, 20: 2.093, 21: 2.086,
        22: 2.080, 23: 2.074, 24: 2.069, 25: 2.064, 26: 2.060,
        27: 2.056, 28: 2.052, 29: 2.048, 30: 2.045,
    }
    t_value = critical.get(len(seeds), 1.96)
    for challenger in challengers:
        for metric in metric_names:
            differences = [
                by_policy_seed[(challenger, seed)][metric]
                - by_policy_seed[(reference, seed)][metric]
                for seed in seeds
            ]
            mean = statistics.mean(differences)
            std = statistics.stdev(differences) if len(differences) > 1 else 0.0
            half_width = (t_value * std / math.sqrt(len(differences)))
            result.append({
                "Policy": challenger,
                "Reference": reference,
                "Metric": metric,
                "Mean Difference": mean,
                "Paired SD": std,
                "CI95 Low": mean - half_width,
                "CI95 High": mean + half_width,
            })
    return result


def compare(policies: dict, episodes: int, base_seed: int, orbits: int,
            output_dir: str):
    if episodes < 2 or orbits < 1:
        raise ValueError("Use at least 2 episodes and 1 orbit per episode")

    seeds = range(base_seed, base_seed + episodes)
    episode_rows = []
    summaries = []
    for name, agent in policies.items():
        print(f"Evaluating {name} over {episodes} paired seeds...")
        rows = [run_episode(agent, seed, n_orbits=orbits) for seed in seeds]
        for row in rows:
            episode_rows.append({"Policy": name, **row})
        summary = summarize_episodes(rows)
        for metric, values in summary.items():
            summaries.append({"Policy": name, "Metric": metric, **values})

    output = Path(output_dir)
    episode_fields = list(episode_rows[0])
    summary_fields = ["Policy", "Metric", "Mean", "Std", "CI95 Low", "CI95 High"]
    _write_csv(output / "comparison_episodes.csv", episode_fields, episode_rows)
    _write_csv(output / "comparison_summary.csv", summary_fields, summaries)

    paired = paired_difference_rows(episode_rows, reference="heuristic")
    paired_fields = ["Policy", "Reference", "Metric", "Mean Difference",
                     "Paired SD", "CI95 Low", "CI95 High"]
    _write_csv(output / "comparison_paired_vs_heuristic.csv", paired_fields, paired)
    print(f"Saved per-episode results and summaries under {output}")
    return summaries, paired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--policies", nargs="+", choices=sorted(POLICIES),
        default=["transmit_all", "greedy_edge", "heuristic"],
    )
    parser.add_argument("--rl-model", action="append", default=[],
                        help="Optional trained MaskablePPO model; may be repeated")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1001,
                        help="Evaluation seed start; keep separate from RL training seeds")
    parser.add_argument("--orbits", type=int, default=4)
    parser.add_argument("--output-dir", default="results/comparison")
    args = parser.parse_args()

    policies = {name: POLICIES[name] for name in args.policies}
    for model_path in args.rl_model:
        name = f"rl_{Path(model_path).stem}"
        if name in policies:
            parser.error(f"Duplicate policy name: {name}")
        policies[name] = load_rl_agent(model_path)
    if "heuristic" not in policies:
        parser.error("Include --policies heuristic as the paired reference policy")
    compare(policies, args.episodes, args.seed, args.orbits, args.output_dir)


if __name__ == "__main__":
    main()
