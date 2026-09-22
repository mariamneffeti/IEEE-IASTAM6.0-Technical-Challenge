from typing import List, Dict
from simulation.satellite_sim import Satellite

def heuristic_agent(sat: Satellite) -> List[Dict]:
    """Compress/infer when power is healthy, downlink during GS pass,
    drop stale payloads when storage is tight."""
    actions: List[Dict] = []
    tel = sat.get_telemetry()

    if tel["in_safe_mode"]:
        return actions

    # --- Downlink during ground-station pass ---
    if tel["in_gs_pass"]:
        ranked = sorted(
            sat.mmu_payloads,
            key=lambda p: (p.processed, p.current_value(sat.env.time_step)),
            reverse=True,
        )
        for p in ranked[:3]:
            actions.append({"type": "downlink", "payload_id": p.id})

    # --- Process when battery & thermal headroom exist ---
    if (tel["battery_soc"] > 0.5
            and not tel["is_throttling"]
            and tel["queue_length"] < 2):
        unprocessed = [p for p in sat.mmu_payloads if not p.processed]
        if unprocessed:
            best = max(unprocessed,
                       key=lambda p: p.current_value(sat.env.time_step))
            mode = "inference" if best.size_mb < 50 else "compressed"
            actions.append({"type": "process",
                            "payload_id": best.id, "mode": mode})

    # --- Drop stale data when MMU > 80 % ---
    mmu_pct = tel["mmu_usage_mb"] / sat.cfg.mmu_capacity_mb
    if mmu_pct > 0.8 and sat.mmu_payloads:
        worst = min(sat.mmu_payloads,
                    key=lambda p: p.current_value(sat.env.time_step))
        if worst.current_value(sat.env.time_step) < 5.0:
            actions.append({"type": "drop", "payload_id": worst.id})

    return actions
