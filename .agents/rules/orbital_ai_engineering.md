# Orbital AI Engineering & Research Rules

## 1. Domain Physics & Constraints
- **Low Earth Orbit (LEO):** Satellites orbit at ~500 km, ~27,000 km/h, ~90-minute periods (~45 min sunlit, ~45 min eclipse).
- **Communication Asymmetry:** Downlink (~80–100 Mbps) is available only when passing ground stations (~5–10 min per orbit, ~0.75% of total mission time). Uplink is narrowband (~1 Mbps or tens of kbps).
- **Thermal Dissipation:** In space vacuum, convection is zero. Radiative cooling to cold space ($3\text{K}$) is limited by satellite surface area. Compute processors (e.g. Raspberry Pi 4B, NVIDIA Jetson) will overheat if run continuously at 100% CPU/GPU without duty-cycling or throttling ($T_{\text{chip}} \le 50^\circ\text{C}$).
- **Energy Harvesting:** Solar power generation $P_{\text{harvest}}(t) \in [0, 48.59]\text{ W}$. Battery storage capacity is limited, and depth-of-discharge must respect battery lifespan limits ($SoC(t) \ge 30\%$).

## 2. Software Architecture Guidelines
- **Modularity:** Separate the project into clean, independent modules:
  - `sim/`: Orbital mechanics, power harvesting, thermal dissipation, communications, and telemetry replay.
  - `workloads/`: Synthetic or real EO tasks (classification, cloud filtering, segmentation, compression).
  - `policies/`: Decision engines (Transmit-All, Greedy Edge, Rule-Based Heuristic, RL/CMDP, Lyapunov Optimizer, Oracle).
  - `benchmarks/`: Automated comparison pipelines, metrics calculation, and visualization.
- **Stateless & FaaS Ready:** Functions should follow the serverless/FaaS design pattern (Trabant paper) so that unexpected resets (SEU) do not corrupt ongoing jobs. Execution queues must be checkpointable.

## 3. Experimental Integrity
- **Metric Definitions:**
  - **Scientific Utility:** Total value delivered to Earth before task deadlines expire.
  - **Task Completion Ratio:** Fraction of captured events processed or transmitted before expiration.
  - **Energy Efficiency:** Utility delivered per Joule of total harvested energy consumed.
  - **Downlink Utilization:** Percentage of available contact bandwidth successfully utilized with non-redundant insights.
  - **Latency (Time-to-Insight):** Time elapsed between optical capture and insight delivery to ground.
- **Trace Backing:**
  - Use realistic traces: BUPT-1 solar and thermal traces (1-second granularity), Sentinel-2 multispectral bands, VIIRS night captures.
