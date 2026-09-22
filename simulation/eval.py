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
    n_orbits: int = 3,
    output_path: str = None,
):
    print(f"Evaluating {policy_type} over {n_episodes} episodes...")
    seeds = [base_seed + i for i in range(n_episodes)]

    # For RL policies, create the adapter once and reuse across episodes
    rl_adapter = None
    if policy_type == "rl":
        rl_adapter = RLAdapterState(model_or_func)

    results = []

    for seed in seeds:
        sat = Satellite(seed=seed)
        max_steps = sat.cfg.orbit_period_s * n_orbits

        # Bind the RL adapter to this episode's satellite
        if rl_adapter is not None:
            rl_adapter.bind(sat)

        for _ in range(max_steps):
            if policy_type == "heuristic":
                actions = heuristic_adapter(sat, model_or_func)
            elif policy_type == "rl":
                actions = rl_adapter(sat)
            else:
                actions = []

            sat.step(actions)

        tel = sat.get_telemetry()

        decision_quality = 0.0
        if tel["total_generated_value_snapshot"] > 0:
            decision_quality = (
                tel["downlinked_utility"] / tel["total_generated_value_snapshot"]
            )

        completed_task_rate = 0.0
        if tel["payloads_generated"] > 0:
            completed_task_rate = tel["payloads_downlinked"] / tel["payloads_generated"]

        latency = 0.0
        total_payloads = tel["payloads_downlinked"] + len(sat.queued_ages())
        if total_payloads > 0:
            latency_sum = tel["cumulative_latency"] + sum(sat.queued_ages())
            latency = latency_sum / total_payloads

        mmu_utilization = (
            tel["cumulative_mmu_usage_mb"] / (max_steps * sat.cfg.mmu_capacity_mb)
        ) * 100
        ram_utilization = (
            tel["cumulative_ram_usage_mb"] / (max_steps * sat.cfg.ram_capacity_mb)
        ) * 100

        results.append(
            {
                "Decision Quality": decision_quality,
                "Completed-Task Rate": completed_task_rate,
                "Energy Consumption (J)": tel["cumulative_energy_j"],
                "Latency (s)": latency,
                "MMU Utilization (%)": mmu_utilization,
                "RAM Utilization (%)": ram_utilization,
                "SEU Events": tel["seu_events"],
                "Safe Mode Events": tel["safe_mode_events"],
            }
        )

    # Sample standard deviation matches pandas' default (ddof=1).
    metric_names = results[0].keys()
    summary = {
        metric: {
            "Mean": statistics.mean(row[metric] for row in results),
            "Std": statistics.stdev(row[metric] for row in results)
            if len(results) > 1 else 0.0,
        }
        for metric in metric_names
    }

    print("\n--- Evaluation Results (mean ± sample std) ---")
    print(f"{'Metric':<30} {'Mean':>14} {'Std':>14} {'95% CI':>25}")
    for metric, values in summary.items():
        # Two-sided Student-t critical values for common episode counts.
        t_critical = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776,
                      6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306,
                      10: 2.262}.get(len(results), 1.96)
        half_width = t_critical * values["Std"] / math.sqrt(len(results))
        values["CI95 Low"] = values["Mean"] - half_width
        values["CI95 High"] = values["Mean"] + half_width
        print(f"{metric:<30} {values['Mean']:>14.4f} {values['Std']:>14.4f} "
              f"[{values['CI95 Low']:.4f}, {values['CI95 High']:.4f}]")

    if output_path:
        result_path = Path(output_path)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        fields = ["Metric", "Mean", "Std", "CI95 Low", "CI95 High"]
        with result_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fields)
            writer.writeheader()
            for metric, values in summary.items():
                writer.writerow({"Metric": metric, **values})
        print(f"Saved summary CSV: {result_path}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the heuristic policy.")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--orbits", type=int, default=3)
    parser.add_argument("--output", default="results/heuristic_summary.csv")
    args = parser.parse_args()
    evaluate_policy("heuristic", heuristic_agent, n_episodes=args.episodes,
                    base_seed=args.seed, n_orbits=args.orbits,
                    output_path=args.output)
