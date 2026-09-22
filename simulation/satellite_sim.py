import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class SimConfig:
    """All simulation parameters in one place for tuning and reproducibility.

    Override any field at construction time. Derived fields are recomputed
    automatically in __post_init__.
    """

    # --- Orbit ---
    orbit_period_s: int = 90 * 60
    sunlit_duration_s: int = 55 * 60

    # --- Power ---
    battery_capacity_wh: float = 100.0
    min_dod_fraction: float = 0.3
    base_power_w: float = 5.0
    comm_power_w: float = 15.0
    solar_power_base_w: float = 22.5
    solar_power_amplitude_w: float = 7.5
    solar_transition_s: int = 30  # cosine taper at eclipse boundaries

    # --- Compute power draw ---
    compression_power_w: float = 10.0
    inference_active_power_w: float = 20.0
    inference_wake_power_w: float = 30.0

    # --- Processing ---
    compression_duration_s: int = 2
    inference_duration_s: int = 5
    accelerator_wake_time_s: int = 2
    compression_ratio: float = 0.3
    inference_ratio: float = 0.001
    compression_value_ratio: float = 0.9
    inference_value_ratio: float = 0.5
    max_queue_length: int = 4  # max jobs waiting/active in the processing queue

    # --- Communication (megabits per second, converted to MB/s internally) ---
    downlink_bandwidth_mbps: float = 20.0

    # --- Storage ---
    mmu_capacity_mb: float = 32000.0
    ram_capacity_mb: float = 4000.0

    # --- Thermal ---
    thermal_heating_coeff: float = 0.15
    thermal_cooling_coeff: float = 0.1
    thermal_throttle_limit_c: float = 50.0
    thermal_ambient_c: float = 0.0

    # --- SEU ---
    seu_probability: float = 1e-5

    # --- Ground station ---
    gs_start_min: int = 1000
    gs_start_max: int = 3000
    gs_duration_min: int = 120
    gs_duration_max: int = 180

    # --- Data generation ---
    data_gen_interval: int = 15
    optical_weight: float = 0.7
    sar_weight: float = 0.3
    optical_size_min_mb: float = 5.0
    optical_size_max_mb: float = 15.0
    sar_size_min_mb: float = 100.0
    sar_size_max_mb: float = 300.0
    payload_value_min: float = 10.0
    payload_value_max: float = 100.0
    payload_decay_min: float = 0.0001
    payload_decay_max: float = 0.001

    # --- Safe mode ---
    safe_mode_exit_margin: float = 1.05  # exit when battery > min_dod_j * this

    # --- Derived (computed in __post_init__) ---
    battery_capacity_j: float = field(init=False)
    min_dod_j: float = field(init=False)
    safe_mode_exit_j: float = field(init=False)
    downlink_mb_per_s: float = field(init=False)

    def __post_init__(self):
        positive = {
            "orbit_period_s": self.orbit_period_s,
            "battery_capacity_wh": self.battery_capacity_wh,
            "mmu_capacity_mb": self.mmu_capacity_mb,
            "ram_capacity_mb": self.ram_capacity_mb,
            "data_gen_interval": self.data_gen_interval,
            "downlink_bandwidth_mbps": self.downlink_bandwidth_mbps,
            "gs_duration_min": self.gs_duration_min,
            "gs_duration_max": self.gs_duration_max,
        }
        invalid = [name for name, value in positive.items() if value <= 0]
        if invalid:
            raise ValueError(f"Configuration values must be positive: {', '.join(invalid)}")
        if not 0.0 <= self.min_dod_fraction < 1.0:
            raise ValueError("min_dod_fraction must be in [0, 1)")
        if not 0.0 <= self.seu_probability <= 1.0:
            raise ValueError("seu_probability must be in [0, 1]")
        if not 0 < self.sunlit_duration_s < self.orbit_period_s:
            raise ValueError("sunlit_duration_s must be between 0 and orbit_period_s")
        if self.gs_start_min < 0 or self.gs_start_max < self.gs_start_min:
            raise ValueError("ground-station start range must be nonnegative and ordered")
        if self.gs_start_max + self.gs_duration_max >= self.orbit_period_s:
            raise ValueError("ground-station window must end before the orbit boundary")
        if self.gs_duration_max < self.gs_duration_min:
            raise ValueError("ground-station duration range must be ordered")
        if not (0.0 < self.compression_ratio <= 1.0 and 0.0 < self.inference_ratio <= 1.0):
            raise ValueError("processing size ratios must be in (0, 1]")
        if not (0.0 <= self.optical_weight <= 1.0
                and 0.0 <= self.sar_weight <= 1.0
                and math.isclose(self.optical_weight + self.sar_weight, 1.0)):
            raise ValueError("modality weights must be in [0, 1] and sum to 1")
        for name, low, high in (
            ("optical_size", self.optical_size_min_mb, self.optical_size_max_mb),
            ("sar_size", self.sar_size_min_mb, self.sar_size_max_mb),
            ("payload_value", self.payload_value_min, self.payload_value_max),
            ("payload_decay", self.payload_decay_min, self.payload_decay_max),
        ):
            if low < 0 or high < low:
                raise ValueError(f"{name} bounds must be nonnegative and ordered")

        self.battery_capacity_j = self.battery_capacity_wh * 3600
        self.min_dod_j = self.min_dod_fraction * self.battery_capacity_j
        self.safe_mode_exit_j = self.min_dod_j * self.safe_mode_exit_margin
        self.downlink_mb_per_s = self.downlink_bandwidth_mbps / 8.0

        # Guard: overlapping taper windows produce a non-monotonic power curve
        if 2 * self.solar_transition_s > self.sunlit_duration_s:
            raise ValueError(
                f"solar_transition_s ({self.solar_transition_s}) must be at most "
                f"sunlit_duration_s / 2 ({self.sunlit_duration_s // 2})"
            )
        if self.max_queue_length < 1:
            raise ValueError("max_queue_length must be at least 1")


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------

@dataclass
class Payload:
    id: str
    modality: str
    size_mb: float
    cloud_cover: float
    base_value: float
    time_decay: float
    creation_time: int
    processed: bool = False
    processing_mode: str = "raw"  # raw, compressed, inference
    partially_transmitted: bool = False

    def current_value(self, current_time: int) -> float:
        dt = current_time - self.creation_time
        return self.base_value * math.exp(-self.time_decay * dt)

    def __repr__(self) -> str:
        return (f"Payload(id={self.id}, mod={self.modality}, "
                f"size={self.size_mb:.2f}MB, mode={self.processing_mode})")


# ---------------------------------------------------------------------------
# Subsystems
# ---------------------------------------------------------------------------

class Environment:
    def __init__(self, cfg: SimConfig, rng: random.Random):
        self.cfg = cfg
        self.rng = rng
        self.time_step: int = 0
        self.sunlit: bool = True
        self.solar_power: float = 0.0
        self.in_gs_pass: bool = False
        self._current_orbit: int = -1

        self.gs_start: int = 0
        self.gs_duration: int = 0
        self.gs_end: int = 0

        self.next_gs_start: int = 0
        self.next_gs_duration: int = 0
        self.next_gs_end: int = 0

        self._randomize_gs_pass()
        self._current_orbit = 0

    def _randomize_gs_pass(self) -> None:
        """Re-roll ground station pass window for a new orbit."""
        if self.next_gs_start == 0:
            # First time initialization
            self.gs_start = self.rng.randint(self.cfg.gs_start_min, self.cfg.gs_start_max)
            self.gs_duration = self.rng.randint(self.cfg.gs_duration_min, self.cfg.gs_duration_max)
            self.gs_end = self.gs_start + self.gs_duration
        else:
            # Shift next to current
            self.gs_start = self.next_gs_start
            self.gs_duration = self.next_gs_duration
            self.gs_end = self.next_gs_end

        # Roll the next one
        self.next_gs_start = self.rng.randint(self.cfg.gs_start_min, self.cfg.gs_start_max)
        self.next_gs_duration = self.rng.randint(self.cfg.gs_duration_min, self.cfg.gs_duration_max)
        self.next_gs_end = self.next_gs_start + self.next_gs_duration

    def step(self) -> None:
        self.time_step += 1
        orbit_time = self.time_step % self.cfg.orbit_period_s
        orbit_number = self.time_step // self.cfg.orbit_period_s

        # New orbit -> re-roll GS pass
        if orbit_number != self._current_orbit:
            self._current_orbit = orbit_number
            self._randomize_gs_pass()

        # Orbit phase
        self.sunlit = orbit_time < self.cfg.sunlit_duration_s

        # Solar harvesting with smooth cosine taper at eclipse boundaries
        if self.sunlit:
            raw_power = (
                self.cfg.solar_power_base_w
                + self.cfg.solar_power_amplitude_w
                * math.sin(math.pi * orbit_time / self.cfg.sunlit_duration_s)
            )
            t = self.cfg.solar_transition_s
            if t > 0 and orbit_time < t:
                blend = 0.5 * (1.0 - math.cos(math.pi * orbit_time / t))
            elif t > 0 and orbit_time > self.cfg.sunlit_duration_s - t:
                remaining = self.cfg.sunlit_duration_s - orbit_time
                blend = 0.5 * (1.0 - math.cos(math.pi * remaining / t))
            else:
                blend = 1.0
            self.solar_power = raw_power * blend
        else:
            self.solar_power = 0.0

        # Ground station pass
        self.in_gs_pass = self.gs_start <= orbit_time < self.gs_end


class PowerSubsystem:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.battery_j: float = cfg.battery_capacity_j

    def available_energy_j(self) -> float:
        """Energy available above the minimum depth-of-discharge.

        Note: safe-mode transitions use is_critically_low() internally.
        This method is provided for agent policies that need a continuous
        energy margin rather than a binary threshold.
        """
        return max(0.0, self.battery_j - self.cfg.min_dod_j)

    def is_critically_low(self) -> bool:
        """True if battery is at or below the DOD floor."""
        return self.battery_j <= self.cfg.min_dod_j

    def apply_power(self, generated_w: float, draw_w: float) -> bool:
        """Apply one tick of power balance. Returns False on brownout."""
        net_power = generated_w - draw_w
        self.battery_j += net_power  # 1 W for 1 s = 1 J
        self.battery_j = min(self.battery_j, self.cfg.battery_capacity_j)

        if self.battery_j < self.cfg.min_dod_j:
            self.battery_j = self.cfg.min_dod_j
            return False
        return True


class ThermalSubsystem:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.t_chip: float = cfg.thermal_ambient_c

    def step(self, total_power_w: float) -> None:
        """Update chip temperature from *all* power dissipation (compute + comm + base)."""
        heating = self.cfg.thermal_heating_coeff * total_power_w
        cooling = self.cfg.thermal_cooling_coeff * (self.t_chip - self.cfg.thermal_ambient_c)
        self.t_chip += heating - cooling

    def is_throttling(self) -> bool:
        return self.t_chip >= self.cfg.thermal_throttle_limit_c


class StorageMemorySubsystem:
    def __init__(self, cfg: SimConfig, rng: random.Random):
        self.cfg = cfg
        self.rng = rng
        self.mmu_used_mb: float = 0.0
        self.ram_used_mb: float = 0.0
        self.accelerator_state: str = "sleep"  # sleep, waking, active
        self.wake_counter: int = 0

    def check_seu(self) -> bool:
        """Stochastic chance of SEU wiping RAM."""
        if self.rng.random() < self.cfg.seu_probability:
            self.ram_used_mb = 0.0
            self.accelerator_state = "sleep"
            self.wake_counter = 0
            return True
        return False

    def can_store_mmu(self, size_mb: float) -> bool:
        return (self.mmu_used_mb + size_mb) <= self.cfg.mmu_capacity_mb

    def can_load_ram(self, size_mb: float) -> bool:
        return (self.ram_used_mb + size_mb) <= self.cfg.ram_capacity_mb

    def load_to_ram(self, size_mb: float) -> bool:
        """Load data into RAM. Returns False if insufficient space."""
        if not self.can_load_ram(size_mb):
            return False
        self.ram_used_mb += size_mb
        return True

    def free_ram(self, size_mb: float) -> None:
        self.ram_used_mb = max(0.0, self.ram_used_mb - size_mb)


class DataGenerator:
    def __init__(self, cfg: SimConfig, rng: random.Random):
        self.cfg = cfg
        self.rng = rng
        self._counter: int = 0

    def step(self, time_step: int) -> Optional[Payload]:
        if time_step % self.cfg.data_gen_interval == 0:
            self._counter += 1
            modality = self.rng.choices(
                ["Optical", "SAR"],
                weights=[self.cfg.optical_weight, self.cfg.sar_weight],
            )[0]

            if modality == "Optical":
                size = self.rng.uniform(self.cfg.optical_size_min_mb,
                                        self.cfg.optical_size_max_mb)
            else:
                size = self.rng.uniform(self.cfg.sar_size_min_mb,
                                        self.cfg.sar_size_max_mb)

            cloud_cover = self.rng.random()
            base_value = self.rng.uniform(self.cfg.payload_value_min, self.cfg.payload_value_max)
            if modality == "Optical":
                base_value *= (1.0 - cloud_cover)

            return Payload(
                id=f"{self._counter:06d}",
                modality=modality,
                size_mb=size,
                cloud_cover=cloud_cover,
                base_value=base_value,
                time_decay=self.rng.uniform(self.cfg.payload_decay_min,
                                            self.cfg.payload_decay_max),
                creation_time=time_step,
            )
        return None


# ---------------------------------------------------------------------------
# Satellite (top-level simulation)
# ---------------------------------------------------------------------------

class Satellite:
    """Top-level simulation.

    Storage accounting invariant (checked in sanity_check.py):
        mmu_used_mb == sum(size of payloads in mmu_payloads)
                     + sum(size of payloads in processing_queue)

    A payload that is queued for processing leaves ``mmu_payloads`` (so it
    cannot be downlinked or dropped) but STAYS in MMU accounting until its job
    completes: the source data is retained until the output exists. RAM holds
    only a working copy for the active job, so an SEU or safe-mode event loses
    the copy and the progress, never the stored data.
    """

    def __init__(self, cfg: SimConfig = None, seed: int = 42):
        self.cfg = cfg or SimConfig()
        self.rng = random.Random(seed)

        self.env = Environment(self.cfg, self.rng)
        self.power = PowerSubsystem(self.cfg)
        self.thermal = ThermalSubsystem(self.cfg)
        self.storage = StorageMemorySubsystem(self.cfg, self.rng)
        self.data_gen = DataGenerator(self.cfg, self.rng)

        self.mmu_payloads: List[Payload] = []
        self.downlinked_utility: float = 0.0
        self.involuntary_drops: int = 0  # MMU full on ingestion
        self.voluntary_drops: int = 0    # explicit agent "drop" action
        self.processing_queue: List[Dict] = []

        self.active_compute_w: float = 0.0
        self.active_comm_w: float = 0.0
        self._in_safe_mode: bool = False

        self.total_generated_value_snapshot: float = 0.0
        self.payloads_generated: int = 0
        self.payloads_downlinked: int = 0
        self.cumulative_latency: float = 0.0
        self.cumulative_energy_j: float = 0.0
        self.seu_events: int = 0
        self.safe_mode_events: int = 0
        self.cumulative_mmu_usage_mb: float = 0.0
        self.cumulative_ram_usage_mb: float = 0.0

        self.peak_mmu_mb: float = 0.0
        self.peak_ram_mb: float = 0.0
        self.peak_temp_c: float = self.cfg.thermal_ambient_c
        self.peak_queue_len: int = 0
        self.bandwidth_used_mb: float = 0.0
        self.throttle_ticks: int = 0
        self.dropped_value: float = 0.0

    @property
    def dropped_frames(self) -> int:
        """Total drops (backward compat)."""
        return self.involuntary_drops + self.voluntary_drops

    def get_telemetry(self) -> Dict:
        orbit_time = self.env.time_step % self.cfg.orbit_period_s
        if self.env.in_gs_pass:
            time_to_next_gs = 0
        elif orbit_time < self.env.gs_start:
            time_to_next_gs = self.env.gs_start - orbit_time
        else:
            time_to_next_gs = (self.cfg.orbit_period_s - orbit_time) + self.env.next_gs_start

        return {
            "time_step": self.env.time_step,
            "sunlit": self.env.sunlit,
            "solar_power_w": self.env.solar_power,
            "battery_soc": self.power.battery_j / self.cfg.battery_capacity_j,
            "battery_j": self.power.battery_j,
            "temperature_c": self.thermal.t_chip,
            "mmu_usage_mb": self.storage.mmu_used_mb,
            "ram_usage_mb": self.storage.ram_used_mb,
            "in_gs_pass": self.env.in_gs_pass,
            "time_to_next_gs": time_to_next_gs,
            "queue_length": len(self.processing_queue),
            "processing_progress": (
                self.processing_queue[0]["progress"]
                if self.processing_queue else None
            ),
            "processing_required": (
                self.processing_queue[0]["required"]
                if self.processing_queue else None
            ),
            "mmu_files": len(self.mmu_payloads),
            "involuntary_drops": self.involuntary_drops,
            "voluntary_drops": self.voluntary_drops,
            "dropped_frames": self.dropped_frames,
            "downlinked_utility": self.downlinked_utility,
            "accelerator_state": self.storage.accelerator_state,
            "is_throttling": self.thermal.is_throttling(),
            "in_safe_mode": self._in_safe_mode,
            "total_generated_value_snapshot": self.total_generated_value_snapshot,
            "payloads_generated": self.payloads_generated,
            "payloads_downlinked": self.payloads_downlinked,
            "cumulative_latency": self.cumulative_latency,
            "cumulative_energy_j": self.cumulative_energy_j,
            "seu_events": self.seu_events,
            "safe_mode_events": self.safe_mode_events,
            "cumulative_mmu_usage_mb": self.cumulative_mmu_usage_mb,
            "cumulative_ram_usage_mb": self.cumulative_ram_usage_mb,
            "peak_mmu_mb": self.peak_mmu_mb,
            "peak_ram_mb": self.peak_ram_mb,
            "peak_temp_c": self.peak_temp_c,
            "peak_queue_len": self.peak_queue_len,
            "bandwidth_used_mb": self.bandwidth_used_mb,
            "throttle_ticks": self.throttle_ticks,
            "dropped_value": self.dropped_value,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recover_processing_queue(self) -> None:
        """Return all in-progress payloads to the MMU list, free RAM for the
        active job, and reset the accelerator.

        MMU accounting is untouched: queued payloads never left it. Only the
        RAM working copy and the job progress are lost.
        """
        for i, job in enumerate(self.processing_queue):
            payload = job["payload"]
            # Only the active job (index 0) may have been loaded into RAM
            if i == 0 and job.get("ram_loaded", False):
                self.storage.free_ram(job["ram_reserved_mb"])
            # size_mb is still the original pre-processing size
            self.mmu_payloads.append(payload)
        self.processing_queue.clear()
        self.storage.accelerator_state = "sleep"
        self.storage.wake_counter = 0

    # ------------------------------------------------------------------
    # Main simulation tick
    # ------------------------------------------------------------------

    def step(self, actions: List[Dict]) -> List[Dict]:
        """Advance simulation by one second.  Returns per-action feedback."""
        self.env.step()
        feedback: List[Dict] = []

        # -- 1. Generate data ----------------------------------------------
        new_payload = self.data_gen.step(self.env.time_step)
        if new_payload:
            self.total_generated_value_snapshot += new_payload.base_value
            self.payloads_generated += 1
            if self.storage.can_store_mmu(new_payload.size_mb):
                self.mmu_payloads.append(new_payload)
                self.storage.mmu_used_mb += new_payload.size_mb
            else:
                self.involuntary_drops += 1
                self.dropped_value += new_payload.base_value

        # -- 2. SEU check --------------------------------------------------
        if self.storage.check_seu():
            self.seu_events += 1
            self._recover_processing_queue()
            feedback.append({
                "type": "seu",
                "message": "SEU event: RAM wiped, queue recovered to MMU",
            })

        # -- 3. Safe-mode with hysteresis -----------------------------------
        entered_safe_mode = False
        if self._in_safe_mode:
            if self.power.battery_j > self.cfg.safe_mode_exit_j:
                self._in_safe_mode = False
            else:
                entered_safe_mode = True
                self._recover_processing_queue()  # no-op if queue already empty
                actions = []
                feedback.append({
                    "type": "safe_mode",
                    "message": "Remaining in safe mode "
                               "(battery below exit threshold)",
                })
        elif self.power.is_critically_low():
            self._in_safe_mode = True
            entered_safe_mode = True
            self.safe_mode_events += 1
            self._recover_processing_queue()
            actions = []
            feedback.append({
                "type": "safe_mode",
                "message": "Battery critically low, entering safe mode",
            })

        # -- 4. Process agent actions --------------------------------------
        self.active_compute_w = 0.0
        self.active_comm_w = 0.0
        remaining_bw_mb = self.cfg.downlink_mb_per_s  # shared per-tick budget
        any_downlink = False

        for act in actions:
            act_type = act.get("type")

            # -- PROCESS ---------------------------------------------------
            if act_type == "process":
                payload_id = act["payload_id"]
                mode = act["mode"]  # "compressed" | "inference"

                payload = next(
                    (p for p in self.mmu_payloads if p.id == payload_id), None
                )
                if payload is None:
                    feedback.append({"type": "error", "action": "process",
                                     "payload_id": payload_id,
                                     "message": "Payload not found"})
                    continue

                if payload.partially_transmitted and not payload.processed:
                    feedback.append({"type": "error", "action": "process",
                                     "payload_id": payload_id,
                                     "message": "Cannot process a partially transmitted payload"})
                    continue
                if payload.processed:
                    feedback.append({"type": "error", "action": "process",
                                     "payload_id": payload_id,
                                     "message": "Already processed"})
                    continue
                if len(self.processing_queue) >= self.cfg.max_queue_length:
                    feedback.append({"type": "error", "action": "process",
                                     "payload_id": payload_id,
                                     "message": "Queue full"})
                    continue

                # Reject if payload can never fit in RAM (prevents silent
                # deadlock in the processing queue).
                if payload.size_mb > self.cfg.ram_capacity_mb:
                    feedback.append({"type": "error", "action": "process",
                                     "payload_id": payload_id,
                                     "message": "Payload too large for RAM"})
                    continue

                required = (self.cfg.compression_duration_s
                            if mode == "compressed"
                            else self.cfg.inference_duration_s)

                # Reserve the payload for processing. It leaves the MMU *list*
                # (cannot be downlinked or dropped while queued) but STAYS in
                # mmu_used_mb until the job completes: the source data is kept
                # until the output exists.
                self.mmu_payloads.remove(payload)

                self.processing_queue.append({
                    "payload": payload,
                    "mode": mode,
                    "progress": 0,
                    "required": required,
                    "ram_reserved_mb": payload.size_mb,
                    "ram_loaded": False,  # loaded lazily when job becomes active
                })
                feedback.append({"type": "ok", "action": "process",
                                 "payload_id": payload_id, "mode": mode})

            # -- DOWNLINK --------------------------------------------------
            elif act_type == "downlink":
                payload_id = act["payload_id"]
                if not self.env.in_gs_pass:
                    feedback.append({"type": "error", "action": "downlink",
                                     "payload_id": payload_id,
                                     "message": "No ground station pass"})
                    continue
                if remaining_bw_mb <= 0:
                    feedback.append({"type": "error", "action": "downlink",
                                     "payload_id": payload_id,
                                     "message": "Bandwidth exhausted this tick"})
                    continue

                payload = next(
                    (p for p in self.mmu_payloads if p.id == payload_id), None
                )
                if payload is None:
                    feedback.append({"type": "error", "action": "downlink",
                                     "payload_id": payload_id,
                                     "message": "Payload not found"})
                    continue

                transmit_mb = min(payload.size_mb, remaining_bw_mb)
                remaining_bw_mb -= transmit_mb
                self.bandwidth_used_mb += transmit_mb
                payload.size_mb -= transmit_mb
                self.storage.mmu_used_mb -= transmit_mb
                any_downlink = True

                if payload.size_mb <= 0:
                    self.mmu_payloads.remove(payload)
                    self.downlinked_utility += payload.current_value(
                        self.env.time_step
                    )
                    self.payloads_downlinked += 1
                    self.cumulative_latency += (self.env.time_step - payload.creation_time)
                    feedback.append({"type": "ok", "action": "downlink",
                                     "payload_id": payload_id,
                                     "message": "Complete"})
                else:
                    payload.partially_transmitted = True
                    feedback.append({"type": "partial", "action": "downlink",
                                     "payload_id": payload_id,
                                     "remaining_mb": payload.size_mb})

            # -- DROP ------------------------------------------------------
            elif act_type == "drop":
                payload_id = act["payload_id"]
                payload = next(
                    (p for p in self.mmu_payloads if p.id == payload_id), None
                )
                if payload is None:
                    feedback.append({"type": "error", "action": "drop",
                                     "payload_id": payload_id,
                                     "message": "Payload not found"})
                    continue
                self.mmu_payloads.remove(payload)
                self.storage.mmu_used_mb -= payload.size_mb
                self.voluntary_drops += 1
                self.dropped_value += payload.base_value
                feedback.append({"type": "ok", "action": "drop",
                                 "payload_id": payload_id})

            # -- UNKNOWN ---------------------------------------------------
            else:
                feedback.append({"type": "error", "action": act_type,
                                 "message": f"Unknown action type: {act_type!r}"})

        # Comm power is a flat radio cost, applied once if any downlink occurred
        if any_downlink:
            self.active_comm_w = self.cfg.comm_power_w

        # -- 5. Advance processing queue -----------------------------------
        if self.processing_queue and not self.thermal.is_throttling():
            current_job = self.processing_queue[0]

            # Lazy-load a working copy to RAM on first active tick
            if not current_job["ram_loaded"]:
                if self.storage.load_to_ram(current_job["ram_reserved_mb"]):
                    current_job["ram_loaded"] = True
                # else: stall - RAM temporarily full, try again next tick
                # (payloads too large to ever fit are rejected at enqueue time)

            if current_job["ram_loaded"]:
                if current_job["mode"] == "inference":
                    # Accelerator wake-up state machine (elif prevents
                    # same-tick cascade from waking -> active)
                    if self.storage.accelerator_state == "sleep":
                        self.storage.accelerator_state = "waking"
                        self.storage.wake_counter = self.cfg.accelerator_wake_time_s

                    if self.storage.accelerator_state == "waking":
                        self.active_compute_w = self.cfg.inference_wake_power_w
                        self.storage.wake_counter -= 1
                        if self.storage.wake_counter <= 0:
                            self.storage.accelerator_state = "active"
                    elif self.storage.accelerator_state == "active":
                        self.active_compute_w = self.cfg.inference_active_power_w
                        current_job["progress"] += 1
                else:
                    # Compression (CPU)
                    self.active_compute_w = self.cfg.compression_power_w
                    current_job["progress"] += 1

                # Check completion
                if current_job["progress"] >= current_job["required"]:
                    completed_payload = current_job["payload"]
                    completed_payload.processed = True
                    completed_payload.processing_mode = current_job["mode"]

                    old_size = completed_payload.size_mb
                    if current_job["mode"] == "compressed":
                        new_size = old_size * self.cfg.compression_ratio
                        completed_payload.base_value *= self.cfg.compression_value_ratio
                    else:  # inference
                        new_size = old_size * self.cfg.inference_ratio
                        completed_payload.base_value *= self.cfg.inference_value_ratio

                    # Free the RAM working copy, then swap the MMU footprint
                    # from the original size to the (smaller) output size.
                    self.storage.free_ram(current_job["ram_reserved_mb"])
                    completed_payload.size_mb = new_size
                    self.storage.mmu_used_mb += new_size - old_size  # always <= 0
                    self.mmu_payloads.append(completed_payload)
                    self.processing_queue.pop(0)
        else:
            # Nothing to process or thermally throttled - park accelerator
            if self.storage.accelerator_state == "active":
                self.storage.accelerator_state = "sleep"

        # -- 6. Physics ----------------------------------------------------
        total_draw = (self.cfg.base_power_w
                      + self.active_compute_w
                      + self.active_comm_w)
        tick_energy_draw = total_draw

        has_power = self.power.apply_power(self.env.solar_power, total_draw)
        if not has_power:
            self._in_safe_mode = True
            self._recover_processing_queue()
            self.active_compute_w = 0.0
            self.active_comm_w = 0.0
            total_draw = self.cfg.base_power_w  # recalc for thermal
            if not entered_safe_mode:
                self.safe_mode_events += 1
                feedback.append({
                    "type": "safe_mode",
                    "message": "Brownout during tick, entering safe mode",
                })

        self.cumulative_energy_j += tick_energy_draw

        # Thermal model sees total power dissipation (compute + comm + base)
        self.thermal.step(total_draw)

        # Clamp to prevent float drift below zero
        self.storage.mmu_used_mb = max(0.0, self.storage.mmu_used_mb)
        self.storage.ram_used_mb = max(0.0, self.storage.ram_used_mb)

        self.cumulative_mmu_usage_mb += self.storage.mmu_used_mb
        self.cumulative_ram_usage_mb += self.storage.ram_used_mb

        self.peak_mmu_mb = max(self.peak_mmu_mb, self.storage.mmu_used_mb)
        self.peak_ram_mb = max(self.peak_ram_mb, self.storage.ram_used_mb)
        self.peak_temp_c = max(self.peak_temp_c, self.thermal.t_chip)
        self.peak_queue_len = max(self.peak_queue_len, len(self.processing_queue))
        self.throttle_ticks += int(self.thermal.is_throttling())

        return feedback

    def queued_ages(self):
        t = self.env.time_step
        return ([t - p.creation_time for p in self.mmu_payloads]
                + [t - j["payload"].creation_time for j in self.processing_queue])
