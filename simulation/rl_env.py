import gymnasium as gym
from gymnasium import spaces
import numpy as np

from simulation.satellite_sim import Satellite, SimConfig

class SatelliteEnv(gym.Env):
    """
    Gymnasium environment for training RL policies on the satellite simulation.
    Uses sb3-contrib MaskablePPO conventions for invalid action masking.
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, cfg: SimConfig = None, max_orbits: int = 3, top_k_payloads: int = 5):
        super().__init__()
        self.cfg = cfg or SimConfig()
        self.max_steps = self.cfg.orbit_period_s * max_orbits
        self.top_k = top_k_payloads
        
        self.sat = None
        self.step_count = 0
        self.previous_utility = 0.0

        # --- Observation Space ---
        # 13 telemetry features + (5 features * K payloads)
        obs_dim = 13 + (5 * self.top_k)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        # --- Action Space ---
        # MultiDiscrete: For each payload slot, choose one of 5 actions:
        # 0=None, 1=Compress, 2=Inference, 3=Downlink, 4=Drop
        self.action_space = spaces.MultiDiscrete([5] * self.top_k)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Instantiate a fresh satellite with the provided seed for domain randomization
        self.sat = Satellite(cfg=self.cfg, seed=seed if seed is not None else 42)
        
        self.step_count = 0
        self.previous_utility = 0.0
        
        return self._get_obs(), {}

    def _get_obs(self) -> np.ndarray:
        tel = self.sat.get_telemetry()
        
        # Normalize continuous telemetry values
        t_next_gs = tel["time_to_next_gs"] / self.cfg.orbit_period_s
        sunlit = 1.0 if tel["sunlit"] else 0.0
        solar = tel["solar_power_w"] / (self.cfg.solar_power_base_w + self.cfg.solar_power_amplitude_w)
        soc = tel["battery_soc"]
        temp = tel["temperature_c"] / self.cfg.thermal_throttle_limit_c
        mmu = tel["mmu_usage_mb"] / self.cfg.mmu_capacity_mb
        ram = tel["ram_usage_mb"] / self.cfg.ram_capacity_mb
        in_gs = 1.0 if tel["in_gs_pass"] else 0.0
        q_len = min(1.0, tel["queue_length"] / self.cfg.max_queue_length)
        
        prog = 0.0
        if tel["processing_required"] and tel["processing_required"] > 0:
            prog = tel["processing_progress"] / tel["processing_required"]
            
        acc_sleep = 1.0 if tel["accelerator_state"] == "sleep" else 0.0
        acc_waking = 1.0 if tel["accelerator_state"] == "waking" else 0.0
        acc_active = 1.0 if tel["accelerator_state"] == "active" else 0.0

        obs_list = [
            t_next_gs, sunlit, solar, soc, temp, mmu, ram, in_gs, q_len, prog,
            acc_sleep, acc_waking, acc_active
        ]
        
        # Sort payloads by value and take top K
        sorted_payloads = sorted(
            self.sat.mmu_payloads,
            key=lambda p: p.current_value(self.sat.env.time_step),
            reverse=True
        )
        
        for i in range(self.top_k):
            if i < len(sorted_payloads):
                p = sorted_payloads[i]
                obs_list.extend([
                    p.size_mb / self.cfg.mmu_capacity_mb,
                    p.current_value(self.sat.env.time_step) / 100.0,
                    1.0 if p.processed else 0.0,
                    1.0 if p.processing_mode == "compressed" else 0.0,
                    1.0 if p.processing_mode == "inference" else 0.0
                ])
            else:
                # Pad empty slots
                obs_list.extend([0.0, 0.0, 0.0, 0.0, 0.0])

        return np.array(obs_list, dtype=np.float32)

    def action_masks(self) -> np.ndarray:
        """
        Returns a boolean array of shape (K, 5) indicating valid actions.
        Used by sb3-contrib MaskablePPO.
        """
        mask = np.zeros((self.top_k, 5), dtype=bool)
        tel = self.sat.get_telemetry()
        
        # Sort exactly as in _get_obs
        sorted_payloads = sorted(
            self.sat.mmu_payloads,
            key=lambda p: p.current_value(self.sat.env.time_step),
            reverse=True
        )
        
        # Track how many process actions are already allowed in this tick
        # to prevent overflowing the queue when multiple slots select process.
        queue_slots_available = max(
            0, self.cfg.max_queue_length - tel["queue_length"]
        )
        process_slots_granted = 0
        
        for i in range(self.top_k):
            # Action 0 (Do Nothing) is always valid unless we want to force action, 
            # but it is essential for safe mode and empty slots.
            mask[i, 0] = True
            
            if tel["in_safe_mode"]:
                # In safe mode, we can ONLY do nothing.
                continue
                
            if i < len(sorted_payloads):
                p = sorted_payloads[i]
                
                if (not p.processed and not p.partially_transmitted
                        and p.size_mb <= self.cfg.ram_capacity_mb
                        and process_slots_granted < queue_slots_available):
                    # Can process if not already processed AND queue has room
                    mask[i, 1] = True  # Compress
                    mask[i, 2] = True  # Inference
                    process_slots_granted += 1
                
                if tel["in_gs_pass"] and i == 0:
                    # The link budget is shared across the tick; grant one slot.
                    mask[i, 3] = True
                
                # Can always drop an existing payload
                mask[i, 4] = True

        return mask

    def step(self, action: np.ndarray):
        """
        Takes a MultiDiscrete action [a_0, a_1, ..., a_K].
        Translates to satellite actions.
        """
        self.step_count += 1
        
        # Sort exactly as in observation and masking
        sorted_payloads = sorted(
            self.sat.mmu_payloads,
            key=lambda p: p.current_value(self.sat.env.time_step),
            reverse=True
        )
        
        sim_actions = []
        tel_before = self.sat.get_telemetry()
        
        # Action space: 0=None, 1=Compress, 2=Inference, 3=Downlink, 4=Drop
        for i in range(self.top_k):
            act = action[i]
            if act == 0 or i >= len(sorted_payloads):
                continue
                
            p = sorted_payloads[i]
            if act == 1:
                sim_actions.append({"type": "process", "payload_id": p.id, "mode": "compressed"})
            elif act == 2:
                sim_actions.append({"type": "process", "payload_id": p.id, "mode": "inference"})
            elif act == 3:
                sim_actions.append({"type": "downlink", "payload_id": p.id})
            elif act == 4:
                sim_actions.append({"type": "drop", "payload_id": p.id})

        # Capture states before step for reward calculation
        vol_drops_before = tel_before["voluntary_drops"]
        invol_drops_before = tel_before["involuntary_drops"]
        was_safe_mode = tel_before["in_safe_mode"]

        # Step simulation
        feedback = self.sat.step(sim_actions)
        
        # Capture states after step
        tel_after = self.sat.get_telemetry()
        
        new_vol_drops = tel_after["voluntary_drops"] - vol_drops_before
        new_invol_drops = tel_after["involuntary_drops"] - invol_drops_before
        is_safe_mode = tel_after["in_safe_mode"]
        just_entered_safe_mode = is_safe_mode and not was_safe_mode

        # Calculate scaled reward
        reward = 0.0
        
        # Utility gained (usually ~10 to 100 per payload)
        utility_gain = tel_after["downlinked_utility"] - self.previous_utility
        reward += utility_gain
        self.previous_utility = tel_after["downlinked_utility"]
        
        # Penalties scaled to match utility magnitudes
        reward -= (new_vol_drops * 25.0)
        reward -= (new_invol_drops * 50.0)
        
        if just_entered_safe_mode:
            reward -= 500.0

        # Check termination and truncation
        terminated = False  # Continuous task, never "wins" or "dies" physically
        truncated = self.step_count >= self.max_steps
        
        info = {
            "feedback": feedback,
            "utility_gain": utility_gain,
            "safe_mode": is_safe_mode
        }
        
        return self._get_obs(), reward, terminated, truncated, info
