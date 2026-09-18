# Project Notes & Quick Reference: Problem 1 ("Process or Transmit?")

**Challenge:** IEEE IASTAM 6.0 Technical Challenge (with TUNSA)  
**Track:** Track 1 — AI & Onboard Computing  
**Problem Statement:** Problem 1 — Process or Transmit?  
**Current Date:** September 18, 2026 | **Next Elimination Deadline:** September 26, 2026 (Phase 2 Mid-Review)

---

## 📌 Master Documentation Map

1. **[Master Research Context Document](file:///Users/habibthegeek/Documents/IAS%20Challenge/IEEE-IASTAM6.0-Technical-Challenge/Docs/Problem_1_Process_or_Transmit_Master_Context.md)**  
   *The complete, single-source-of-truth technical dossier containing satellite physics, Trabant FaaS architecture, mathematical models, ML workloads, and benchmark strategy.*
2. **[Customization Skill: `orbital-compute-decision-engine`](file:///Users/habibthegeek/Documents/IAS%20Challenge/IEEE-IASTAM6.0-Technical-Challenge/.agents/skills/orbital-compute-decision-engine/SKILL.md)**  
   *Workflow runbook for simulator execution, policy development, evaluation pipelines, and paper writing.*
3. **[Mathematical Problem Formulation](file:///Users/habibthegeek/Documents/IAS%20Challenge/IEEE-IASTAM6.0-Technical-Challenge/.agents/skills/orbital-compute-decision-engine/references/mathematical_formulation.md)**  
   *Exact CMDP, Lyapunov drift-plus-penalty, and MILP optimization formulations.*
4. **[Telemetry & Workload Specifications](file:///Users/habibthegeek/Documents/IAS%20Challenge/IEEE-IASTAM6.0-Technical-Challenge/.agents/skills/orbital-compute-decision-engine/references/telemetry_and_workload_specs.md)**  
   *BUPT-1 12U CubeSat parameters, Sentinel-2 instrument specifications, and ML model profiles.*
5. **[IEEE Paper Blueprint & 100-Point Scoring Rubric](file:///Users/habibthegeek/Documents/IAS%20Challenge/IEEE-IASTAM6.0-Technical-Challenge/.agents/skills/orbital-compute-decision-engine/references/ieee_paper_template_and_rubric.md)**  
   *Templates and strategies for the Phase 2 interim paper and 2-minute pitch video.*
6. **[Autonomous Agent Rules (`AGENTS.md`)](file:///Users/habibthegeek/Documents/IAS%20Challenge/IEEE-IASTAM6.0-Technical-Challenge/AGENTS.md)**  
   *Repository-wide engineering guidelines and orbital physics invariants.*

---

## ⚡ Mathematical Formula Cheat Sheet

### 1. Trabant Feasibility Equations (arXiv:2504.08337)
- **Power Invariant:**
  $$P_{\text{harvest}}(t) \ge P_{\text{compute}}(t) + P_{\text{comm}}(t)$$
- **Compute Power Draw:**
  $$P_{\text{compute}} = P_{\text{base}} + E_{\text{pre}} R_{\text{frame}} + \sum_{i=1}^n E_{f_i} R_{\text{frame}} (1 - R_{\text{filter}})$$
- **RF Downlink Communication Power:**
  $$P_{\text{comm}} = E_{\text{sendbyte}} \sum_{i=1}^n C_{f_i} R_{\text{frame}} (1 - R_{\text{filter}}) S_{\text{frame}}$$
- **Downlink Budget Constraint:**
  $$B_{\text{downlink}} \ge \sum_{i=1}^n C_{f_i} R_{\text{frame}} (1 - R_{\text{filter}}) S_{\text{frame}}$$
- **Real-Time Throughput Bound:**
  $$R_{\text{frame}}^{-1} \ge T_{\text{pre}} + \sum_{i=1}^n T_{f_i} (1 - R_{\text{filter}})$$

### 2. Key Physical Constants (BUPT-1 & Sentinel-2 Baseline)
- Frame raw size: $S_{\text{raw}} = 256 \times 256 \times 13\text{ Bytes} \approx 851.9\text{ KB}$
- Pre-filtering: $T_{\text{pre}} = 0.038\text{ s}$, $E_{\text{pre}} = 0.01\text{ J}$, $R_{\text{filter}} = 77\%$
- Downlink transmission energy: $E_{\text{sendbyte}} = 2.0\ \mu\text{J/Byte}$ ($20\text{ W} / 80\text{ Mbps}$)
- Average downlink contact budget: $B_{\text{downlink}} = 600\text{ kbps}$ ($0.75\%$ contact duty cycle)
- Base compute power: $P_{\text{base}} = 1.518\text{ W}$
- Safe battery floor: $SoC(t) \ge 30\%$
- Safe thermal limit: $T_{\text{chip}}(t) \le 50.0^\circ\text{C}$

---

## 🎯 4-Tier Benchmarking Hierarchy
1. **Baseline 0:** Traditional EO (Transmit-All raw data during contact passes).
2. **Baseline 1:** Greedy Edge (Always process onboard; no thermal/battery time-shifting).
3. **Baseline 2:** Multi-Threshold Heuristic (Fixed `if/else` on battery SoC and ground visibility).
4. **Proposed Engine:** Online Lyapunov Drift-Plus-Penalty / Constrained MDP with time-shifted FaaS.
5. **Upper Bound:** Offline MILP Oracle with full future orbital knowledge.
