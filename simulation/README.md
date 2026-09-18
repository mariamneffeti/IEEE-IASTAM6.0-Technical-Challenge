# LEO Satellite Simulation & Interactive Dashboard

This directory contains the physical orbital simulator and real-time dashboard for **IASTAM 6.0 Track 1, Problem 1: "Process or Transmit?"**.

---

## 1. Quick Start

### Install Dependencies
```bash
cd simulation
pip install -r requirements.txt
```

### Launch Interactive Web Dashboard
```bash
python3 dashboard.py
```
Open your browser at: **[http://127.0.0.1:8050](http://127.0.0.1:8050)**

---

## 2. Architecture & Modules

- **`satellite_sim.py`**:
  - Discrete-event LEO satellite simulator modeling orbit kinematics (90 min period, 55 min sunlight, 35 min eclipse).
  - Physical models: Solar power harvesting, battery depth-of-discharge, radiative thermal dissipation ($T_{\text{chip}} \le 50^\circ\text{C}$), MMU/RAM memory hierarchies, SEU fault injection, and ground station visibility windows.
- **`dashboard.py`**:
  - Interactive Dash/Plotly application with 10 Hz UI refresh.
  - Controls for real-time play/pause, time step speed multipliers ($1\times$ to $50\times$), manual task dispatch, and baseline heuristic agent.
  - Telemetry graphs for battery state of charge, power draw vs. generation, thermal curves, queue status, and event logs.
