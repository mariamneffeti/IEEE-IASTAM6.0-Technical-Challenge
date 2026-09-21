import numpy as np
import pandas as pd
from satellite_sim import Satellite, SimConfig
from baseline import heuristic_agent
from rl_env import SatelliteEnv


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
        max_steps = sat.cfg.orbit_period_s * 3  # 3 orbits

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

    df = pd.DataFrame(results)

    # Calculate mean and std
    summary = pd.DataFrame({"Mean": df.mean(), "Std": df.std()}).T

    print("\n--- Evaluation Results ---")
    print(summary.to_string(float_format="%.2f"))

    return summary


if __name__ == "__main__":
    # Baseline run with heuristic agent
    evaluate_policy("heuristic", heuristic_agent)
