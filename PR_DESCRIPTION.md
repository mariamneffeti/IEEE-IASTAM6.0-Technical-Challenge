## 🛰️ Track 1 — Problem 1: Research Context, Mathematical Formulation & Agentic Skills Framework

### 📌 Summary
This PR integrates the foundational research architecture, mathematical formulations, and autonomous engineering skills for **Track 1, Problem 1: "Process or Transmit?"** (IEEE IASTAM 6.0 in collaboration with TUNSA). It establishes the theoretical and empirical grounding needed for the Phase 2 Interim Paper (due Sept 26) and the Phase 3 working prototype.

---

### 🚀 Key Changes

1. **Autonomous Agent & Skills Framework (`.agents/`, `AGENTS.md`)**
   - **`orbital-compute-decision-engine` Skill:** End-to-end workflow runbook covering simulator integration, baseline benchmarks, and paper drafting.
   - **Mathematical Reference:** Rigorous definitions for Constrained MDP, online Lyapunov drift-plus-penalty optimization, and offline MILP oracle bounds.
   - **Domain & Engineering Rules:** Enforces LEO physical invariants (battery $SoC \ge 30\%$, vacuum radiative thermal limits $T_{\text{chip}} \le 50^\circ\text{C}$, ~0.75% ground station contact duty cycle).

2. **Problem 1 Master Research Dossier (`Docs/`)**
   - **`Docs/Problem_1_Process_or_Transmit_Master_Context.md`:** Comprehensive single source of truth synthesizing the problem statement, Trabant serverless edge architecture, and trade-off dynamics.
   - **`Docs/Books/Notes.md`:** High-yield executive summary, formula cheat sheet, and file navigation index.
   - **Reference Papers & Books:** Integrated Trabant (arXiv:2504.08337) telemetry traces (BUPT-1 12U CubeSat, Sentinel-2 13-band multispectral data, and 5 ML benchmark workloads).

3. **Scoring & Deliverables Alignment**
   - Aligned directly with the official **100-point scoring grid** and Phase 2 requirements (IEEE 2-column interim paper template + 2-minute pitch video storyboard).

---

### 🧪 Verification
- All mathematical equations cross-validated against BUPT-1 and Trabant literature.
- Verified workspace customization skill discovery and YAML frontmatter compliance.
- Rebased cleanly on latest `main`.
