# Telemetry & Workload Reference Specifications

This document defines the empirical parameters, telemetry traces, and Earth Observation (EO) machine learning workloads sourced from real satellite missions (BUPT-1, Sentinel-2, VIIRS) and validated testbeds.

---

## 1. Spacecraft Platform & Orbit Architecture (BUPT-1 CubeSat)

The standard simulation environment is modeled after **BUPT-1** (Xing et al., ACM MobiCom '24), the first openly documented LEO research satellite running general-purpose COTS edge computing:

| Parameter | Value | Source / Notes |
| :--- | :--- | :--- |
| **Form Factor** | 12U CubeSat | California Polytechnic CubeSat Standard |
| **Orbit Altitude** | $487\text{ km} - 494\text{ km}$ (LEO) | Sun-synchronous orbit, inclination $97.3^\circ$ |
| **Orbital Period** | $\approx 94\text{ minutes}$ | $\approx 15.3$ orbits per 24-hour day |
| **Solar Generation Peak** | $48.59\text{ W}$ | Dual articulated solar arrays |
| **Mean Net Available Power** | $2.950\text{ W}$ ($2950\text{ mW}$) | Mean solar power ($15.59\text{ W}$) minus bus upkeep ($12.64\text{ W}$) |
| **COTS Compute Board** | Raspberry Pi 4B (4-core Cortex-A72 @ 1.5GHz) | Replicated in lab testbeds with matched thermal curves |
| **Base Compute Power ($P_{\text{base}}$)** | $1.518\text{ W}$ | Compute module idle consumption |
| **Battery Nominal Capacity** | $57.5\text{ Wh} = 207,000\text{ J}$ | $1/4$ allocated to compute payload from $115\text{ Wh}$ total |
| **Battery Discharge Floor** | $30\%\text{ SoC}$ (DoD 70%) | Life-cycle protection threshold |
| **Thermal Operating Limit** | $T_{\max} = 50.0^\circ\text{C}$ | Safe boundary for passive radiative dissipation |

---

## 2. Communication Link Architecture

Communication between the satellite and Earth occurs via intermittent passes over polar or mid-latitude ground stations:

- **Ground Station Reference:** Tongchuan Station (China), Latitude $35.0^\circ\text{N}$, Longitude $109.1^\circ\text{E}$.
- **Downlink Bandwidth:** $100\text{ Mbps}$ physical link ($80\text{ Mbps}$ net after 20% Reed-Solomon/FEC and protocol overhead).
- **Uplink Bandwidth:** $1\text{ Mbps}$ ($800\text{ kbps}$ net), primarily allocated for TT&C and function code updates.
- **Pass Frequency & Duration:** Contact window lasts approximately $270\text{ seconds}$ per pass, occurring approximately once every 3–4 orbits ($0.75\%$ contact duty cycle).
- **Transmitter Power Draw:** $20.0\text{ W}$ during active RF amplification.
- **Energy per Downlinked Byte ($E_{\text{sendbyte}}$):**
  $$E_{\text{sendbyte}} = \frac{20\text{ W}}{80\times 10^6\text{ bits/s}} \times 8\text{ bits/Byte} = 2.0\times 10^{-6}\text{ J/Byte} = 2.0\ \mu\text{J/Byte}$$
- **Effective Orbit Downlink Budget ($B_{\text{downlink}}$):**
  $$B_{\text{downlink}} = 80\text{ Mbps} \times 0.0075 \approx 600\text{ kbps}$$

---

## 3. Earth Observation Instrument Pipeline

### Frame Ingestion
- Ground sampling distance (GSD): $10\text{ m/pixel}$.
- Frame dimensions: $256 \times 256\text{ pixels}$.
- Multispectral bands: 13 Sentinel-2 spectral bands ($B1$ through $B12$ + $B8A$).
- Frame raw data size ($S_{\text{raw}}$):
  $$S_{\text{raw}} = 256 \times 256 \times 13 \times 1\text{ Byte} = 851,968\text{ Bytes} \approx 832\text{ KB}$$
- Frame acquisition rate ($R_{\text{frame}}$): $2.5\text{ Hz}$ (1 frame every $400\text{ ms}$).

### Pre-Filtering Stage
- **Algorithm:** Braaten-Cohen-Yang pixel-level cloud detection or `s2cloudless`.
- **Pre-filtering Time ($T_{\text{pre}}$):** $0.038\text{ s}$ per frame.
- **Pre-filtering Energy ($E_{\text{pre}}$):** $0.010\text{ J}$ per frame.
- **Filtering Discard Rate ($R_{\text{filter}}$):** $77.0\%$ of frames are rejected (due to cloud cover $>30\%$ or darkness).
  - Sunlit frames: $40.8\%$ of trajectory.
  - Clear sunlit frames (cloud $<30\%$): $55.6\%$ of sunlit frames ($22.7\%$ overall pass rate).

---

## 4. Workload Benchmark Suite (FaaS Tasks)

All tasks run as isolated micro-services (FaaS processes/containers) using lightweight TensorFlow Lite / ONNX models ($0.5\text{ MB} - 2.8\text{ MB}$):

| Task ID | Application / Model | Input Bands | Output Payload | Energy ($E_{f_i}$) | Time ($T_{f_i}$) | Compression ($C_{f_i}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`func_methane`** | Methane Leak Detection (EuroSat CNN) | RGB (B2, B3, B4) | RGB + 2 SWIR bands if positive | $0.041\text{ J}$ | $0.018\text{ s}$ | $0.051$ ($5.1\%$) |
| **`func_moisture`**| Soil Moisture Multi-label (BigEarthNet CNN) | 12 Bands | RGB + NIR + SWIR bands | $0.092\text{ J}$ | $0.050\text{ s}$ | $0.041$ ($4.1\%$) |
| **`func_segment`** | Urban Feature Segmentation (U-Net) | RGB | RGB + Bitmask | $0.755\text{ J}$ | $0.494\text{ s}$ | $0.047$ ($4.7\%$) |
| **`func_vessel`**  | Marine Vessel Detection (MASATI CNN) | RGB (filtered $<10\%$ cloud) | Cropped RGB bounding boxes | $1.053\text{ J}$ | $0.585\text{ s}$ | $0.026$ ($2.6\%$) |
| **`func_wildfire`**| Wildfire Risk Detection (Wildfire CNN) | All 13 Bands | Full multispectral if prob $>60\%$ | $0.667\text{ J}$ | $0.353\text{ s}$ | $0.026$ ($2.6\%$) |

### Workload Bottleneck Analysis
- If all 5 functions were executed sequentially on every non-filtered frame:
  $$\sum T_{f_i} = 0.018 + 0.050 + 0.494 + 0.585 + 0.353 = 1.500\text{ s} > R_{\text{frame}}^{-1} = 0.400\text{ s} \quad \implies \textbf{System Overloaded!}$$
- Similarly, cumulative power draw would reach $P_{\text{compute}} \approx 3.02\text{ W} > P_{\text{generated}} = 2.95\text{ W}$, depleting the battery.
- **Conclusion:** An intelligent scheduler **must** selectively prioritize tasks, time-shift processing to sunlit orbits, or transmit raw frames based on real-time trade-offs.
