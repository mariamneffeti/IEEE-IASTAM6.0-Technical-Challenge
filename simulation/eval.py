import argparse
import csv
import statistics
import math
from pathlib import Path
from simulation.satellite_sim import Satellite, SimConfig
from simulation.baseline import heuristic_agent


def heuristic_adapter(sat: Satellite, func) -> list:
    return func(sat)


class RLAdapterState:
    """Persistent adapter that reuses a single SatelliteEnv for observation
    and masking logic, avoiding the cost of re-instantiation on every tick.

    Usage:
        adapter = RLAdapterState(model, cfg)
        adapter.bind(sat)          # call once per episode
        actions = adapter(sat)     # call each tick
    """

    def __init__(self, model, cfg: SimConfig = None):
        from simulation.rl_env import SatelliteEnv

        self.model = model
        self._env = SatelliteEnv(cfg=cfg or SimConfig())

    def bind(self, sat: Satellite):
        """Bind (or rebind) the adapter to a new Satellite instance."""
        self._env.sat = sat

    def __call__(self, sat: Satellite) -> list:
        # Ensure the env always points at the current satellite
        self._env.sat = sat

        obs = self._env._get_obs()
        mask = self._env.action_masks()

        # Predict action
        action, _states = self.model.predict(
            obs, action_masks=mask, deterministic=True
        )

        # Decode action into sim commands
        sorted_payloads = sorted(
            sat.mmu_payloads,
            key=lambda p: p.current_value(sat.env.time_step),
            reverse=True,
        )

        sim_actions = []
        for i in range(self._env.top_k):
            act = action[i]
            if act == 0 or i >= len(sorted_payloads):
                continue

            p = sorted_payloads[i]
            if act == 1:
                sim_actions.append(
                    {"type": "process", "payload_id": p.id, "mode": "compressed"}
                )
            elif act == 2:
                sim_actions.append(
                    {"type": "process", "payload_id": p.id, "mode": "inference"}
                )
            elif act == 3:
                sim_actions.append({"type": "downlink", "payload_id": p.id})
            elif act == 4:
                sim_actions.append({"type": "drop", "payload_id": p.id})

        return sim_actions


def evaluate_policy(
    policy_type: str,
    model_or_func=None,
    n_episodes: int = 5,
    base_seed: int = 42,
    n_orbits: int = 4,
    output_path: str = None,
):
    if n_episodes < 1 or n_orbits < 1:
        raise ValueError("n_episodes and n_orbits must both be at least 1")
    if policy_type not in {"heuristic", "rl"}:
        raise ValueError(f"Unsupported policy_type: {policy_type!r}")
    print(f"Evaluating {policy_type} over {n_episodes} episodes...")
    seeds = [base_seed + i for i in range(n_episodes)]

    # For RL policies, create the adapter once and reuse across episodes
    rl_adapter = None
    if policy_type == "rl":
        rl_adapter = RLAdapterState(model_or_func)

    agent = (heuristic_agent if model_or_func is None else model_or_func)
    if policy_type == "rl":
        agent = rl_adapter
    results = [run_episode(agent, seed=seed, n_orbits=n_orbits) for seed in seeds]
    summary = summarize_episodes(results)

    print_summary(policy_type, summary)

    if output_path:
        result_path = Path(output_path)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        fields = ["Metric", "Mean", "Std", "CI95 Low", "CI95 High"]
        with result_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fields,
                                    lineterminator="\n")
            writer.writeheader()
            for metric, values in summary.items():
                writer.writerow({"Metric": metric, **values})
        print(f"Saved summary CSV: {result_path}")

    return summary


def run_episode(agent, seed: int, n_orbits: int = 4,
                cfg: SimConfig = None) -> dict:
    """Run a callable policy once and return its common benchmark metrics."""
    cfg = cfg or SimConfig()
    sat = Satellite(cfg=cfg, seed=seed)
    if hasattr(agent, "bind"):
        agent.bind(sat)

    max_steps = sat.cfg.orbit_period_s * n_orbits
    for _ in range(max_steps):
        sat.step(agent(sat))

    tel = sat.get_telemetry()
    return {
        "Seed": seed,
        "Decision Quality": (
            tel["downlinked_utility"] / tel["total_generated_value_snapshot"]
            if tel["total_generated_value_snapshot"] > 0 else 0.0
        ),
        "Completed-Task Rate": (
            tel["payloads_downlinked"] / tel["payloads_generated"]
            if tel["payloads_generated"] > 0 else 0.0
        ),
        "Energy Consumption (J)": tel["cumulative_energy_j"],
        "Latency (s)": (
            tel["cumulative_latency"] / tel["payloads_downlinked"]
            if tel["payloads_downlinked"] else 0.0
        ),
        "MMU Utilization (%)": (
            tel["cumulative_mmu_usage_mb"]
            / (max_steps * sat.cfg.mmu_capacity_mb) * 100
        ),
        "RAM Utilization (%)": (
            tel["cumulative_ram_usage_mb"]
            / (max_steps * sat.cfg.ram_capacity_mb) * 100
        ),
        "SEU Events": tel["seu_events"],
        "Safe Mode Events": tel["safe_mode_events"],
    }


def _student_t_critical(n: int) -> float:
    values = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776,
              6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306,
              10: 2.262, 11: 2.228, 12: 2.201, 13: 2.179,
              14: 2.160, 15: 2.145, 16: 2.131, 17: 2.120,
              18: 2.110, 19: 2.101, 20: 2.093, 21: 2.086,
              22: 2.080, 23: 2.074, 24: 2.069, 25: 2.064,
              26: 2.060, 27: 2.056, 28: 2.052, 29: 2.048,
              30: 2.045}
    return values.get(n, 1.96)


def summarize_episodes(results: list) -> dict:
    """Summarize episode metrics with sample SD and two-sided 95% t intervals."""
    metrics = [name for name in results[0] if name != "Seed"]
    summary = {}
    for metric in metrics:
        values = [row[metric] for row in results]
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0
        half_width = _student_t_critical(len(values)) * std / math.sqrt(len(values))
        summary[metric] = {
            "Mean": mean,
            "Std": std,
            "CI95 Low": max(0.0, mean - half_width),
            "CI95 High": mean + half_width,
        }
    return summary


def print_summary(name: str, summary: dict) -> None:
    print(f"\n--- {name} results (mean ± sample std) ---")
    print(f"{'Metric':<30} {'Mean':>14} {'Std':>14} {'95% CI':>25}")
    for metric, values in summary.items():
        print(f"{metric:<30} {values['Mean']:>14.4f} {values['Std']:>14.4f} "
              f"[{values['CI95 Low']:.4f}, {values['CI95 High']:.4f}]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the heuristic policy.")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--orbits", type=int, default=4)
    parser.add_argument("--output", default="results/heuristic_summary.csv")
    args = parser.parse_args()
    evaluate_policy("heuristic", heuristic_agent, n_episodes=args.episodes,
                    base_seed=args.seed, n_orbits=args.orbits,
                    output_path=args.output)
