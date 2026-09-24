"""Reference policies used in the common-policy benchmark."""

from typing import Dict, List

from simulation.satellite_sim import Satellite


def transmit_all_agent(sat: Satellite) -> List[Dict]:
    """Transmit raw payloads FIFO during contact; never process or voluntarily drop."""
    tel = sat.get_telemetry()
    if tel["in_safe_mode"] or not tel["in_gs_pass"] or not sat.mmu_payloads:
        return []
    oldest = min(sat.mmu_payloads, key=lambda payload: payload.creation_time)
    return [{"type": "downlink", "payload_id": oldest.id}]


def greedy_edge_agent(sat: Satellite) -> List[Dict]:
    """Process the oldest eligible payload as soon as possible; downlink outputs."""
    tel = sat.get_telemetry()
    if tel["in_safe_mode"]:
        return []

    actions: List[Dict] = []
    downlinked_id = None
    if tel["in_gs_pass"]:
        processed = [payload for payload in sat.mmu_payloads if payload.processed]
        if processed:
            selected = min(processed, key=lambda payload: payload.creation_time)
            actions.append({"type": "downlink", "payload_id": selected.id})
            downlinked_id = selected.id

    if len(sat.processing_queue) < sat.cfg.max_queue_length:
        pending = [
            payload for payload in sat.mmu_payloads
            if not payload.processed
            and not payload.partially_transmitted
            and payload.id != downlinked_id
            and payload.size_mb <= sat.cfg.ram_capacity_mb
        ]
        if pending:
            selected = min(pending, key=lambda payload: payload.creation_time)
            mode = "inference" if selected.size_mb < 50.0 else "compressed"
            actions.append({
                "type": "process",
                "payload_id": selected.id,
                "mode": mode,
            })
    return actions
