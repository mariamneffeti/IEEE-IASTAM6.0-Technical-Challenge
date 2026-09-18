# Mathematical Problem Formulation: "Process or Transmit?"

## 1. System Dynamics & Notation

Let discrete time be indexed by $t \in \{0, 1, 2, \dots, T-1\}$ with step size $\Delta t$ (typically 1 second).

| Symbol | Definition | Nominal Values / Units |
| :--- | :--- | :--- |
| $P_{\text{harvest}}(t)$ | Solar power harvested by arrays | $0.00\text{ W}$ (eclipse) to $48.59\text{ W}$ (sunlit peak) |
| $P_{\text{base}}$ | Baseline housekeeping & avionics power | $1.518\text{ W}$ (compute board idle) to $12.64\text{ W}$ (full bus) |
| $E_{\text{batt}}(t)$ | Available energy stored in battery | Capacity $57.5\text{ Wh} \approx 207,000\text{ J}$ |
| $SoC(t)$ | Battery State of Charge ($E_{\text{batt}}(t) / E_{\text{capacity}}$) | Must remain $\ge 0.30$ (30% minimum floor) |
| $T_{\text{chip}}(t)$ | Processing unit junction/case temperature | Operational threshold $T_{\max} = 50.0^\circ\text{C}$ |
| $G(t)$ | Ground station visibility flag | $G(t) \in \{0, 1\}$, duty cycle $\approx 0.75\%$ |
| $B_{\text{downlink}}$ | Channel downlink transmission rate | $80\text{ Mbps} = 10\text{ MB/s}$ (active contact) |
| $P_{\text{comm}}$ | Active RF transmission power draw | $20.0\text{ W}$ |
| $E_{\text{sendbyte}}$ | Downlink energy cost per byte | $2.0\times 10^{-6}\text{ J/Byte} = 2.0\ \mu\text{J/B}$ |

---

## 2. Workload & Task Model

Incoming frames arrive at rate $R_{\text{frame}}$ (e.g. $2.5\text{ Hz}$ or one frame every $400\text{ ms}$). Each frame $k$ has:
- **Raw size:** $S_{\text{raw}} = 256 \times 256 \times 13 \text{ Bytes} \approx 851.9\text{ KB}$.
- **Preprocessing / Pre-filtering:** Preprocessing time $T_{\text{pre}} \approx 0.038\text{ s}$, energy $E_{\text{pre}} \approx 0.01\text{ J}$. 
  Cloud detection drops uninformative frames with probability $R_{\text{filter}} \approx 0.77$.
- **Downstream Function $f_i$:**
  - Inference computation time: $T_{f_i}$ (seconds).
  - Inference energy consumption: $E_{f_i}$ (Joules).
  - Data compression ratio: $C_{f_i} = \frac{S_{\text{output}}}{S_{\text{raw}}} \in [0.01, 0.06]$.
- **Scientific Utility:** Frame $k$ possesses initial scientific utility $U_{0,k}$ and latency decay factor $\alpha_k$:
  $$U_k(t) = \begin{cases} U_{0,k} \cdot \exp(-\alpha_k (t - t_{\text{capture}})), & \text{if delivered at time } t \le t_{\text{capture}} + \tau_k \\ 0, & \text{if expired or dropped} \end{cases}$$

---

## 3. Physical State Transitions & Invariants

### 3.1 Energy & Battery Dynamics
The total power consumption at time $t$ is:
$$P_{\text{total}}(t) = P_{\text{base}} + P_{\text{compute}}(t) + P_{\text{comm}}(t)$$
Where:
- $P_{\text{compute}}(t) = \sum_{j \in \text{active}} \frac{E_j}{\Delta t}$ (or $P_{\text{active}}$ while computing).
- $P_{\text{comm}}(t) = 20.0\text{ W} \cdot \mathbb{I}(\text{transmitting at } t)$.

The battery energy updates according to:
$$E_{\text{batt}}(t+1) = \min\left(E_{\text{capacity}}, \ E_{\text{batt}}(t) + \eta_{\text{charge}} [P_{\text{harvest}}(t) - P_{\text{total}}(t)]^+ \Delta t - \frac{1}{\eta_{\text{discharge}}} [P_{\text{total}}(t) - P_{\text{harvest}}(t)]^+ \Delta t \right)$$
**Safety Constraint:**
$$E_{\text{batt}}(t) \ge 0.30 \cdot E_{\text{capacity}}, \quad \forall t$$

### 3.2 Thermal Radiative Dissipation in Vacuum
In LEO, convective cooling is absent. The thermal balance of the computing package is governed by radiative dissipation into deep space ($T_{\text{space}} \approx 3\text{ K}$):
$$C_{\text{thermal}} \frac{dT_{\text{chip}}}{dt} = P_{\text{compute}}(t) - \epsilon \sigma A_{\text{rad}} (T_{\text{chip}}^4 - T_{\text{space}}^4) - K_{\text{cond}} (T_{\text{chip}} - T_{\text{chassis}})$$
Linearized for small variations around operating temperatures:
$$T_{\text{chip}}(t+1) = T_{\text{chip}}(t) + \frac{P_{\text{compute}}(t)}{C_{\text{th}}} \Delta t - \frac{(T_{\text{chip}}(t) - T_{\text{ambient}}(t))}{\tau_{\text{cool}}} \Delta t$$
**Safety Constraint:**
$$T_{\text{chip}}(t) \le T_{\max} = 50.0^\circ\text{C}, \quad \forall t$$

---

## 4. Decision Spaces & Queueing Formulation

For each newly captured or queued item $k$, the decision engine selects action $a_k \in \mathcal{A}$:
$$\mathcal{A} = \{\text{PROCESS\_NOW}, \text{STORE\_QUEUE}, \text{TRANSMIT\_RAW}, \text{DISCARD}\}$$

### Buffer State Updates
1. **Execution Queue ($Q_{\text{exec}}$):** Stores pairs of $(f_i, \text{frame}_k)$ waiting for thermal or solar availability.
   $$L_{\text{exec}}(t+1) = \max\left(0, L_{\text{exec}}(t) + \sum_{k} \mathbb{I}(a_k = \text{STORE\_QUEUE}) - \mathbb{I}(\text{dequeued for compute})\right)$$
2. **Downlink Queue ($Q_{\text{dl}}$):** Stores payload bytes waiting for ground station contact.
   $$L_{\text{dl}}(t+1) = \max\left(0, L_{\text{dl}}(t) + \text{Bytes}_{\text{in}}(t) - G(t) \cdot B_{\text{downlink}} \Delta t\right)$$
   Where $\text{Bytes}_{\text{in}}(t) = \sum C_{f_i} S_{\text{raw}} \cdot \mathbb{I}(\text{completed compute}) + \sum S_{\text{raw}} \cdot \mathbb{I}(a_k = \text{TRANSMIT\_RAW})$.

---

## 5. Optimization Formulations

### 5.1 Formulation 1: Global Offline Oracle (MILP)
Given complete, non-causal knowledge of trajectory $P_{\text{harvest}}(t)$ and $G(t)$ over horizon $T$:
$$\max \sum_{k} U_k(t_{\text{delivery}}) - \lambda_E \sum_t P_{\text{total}}(t) \Delta t$$
Subject to:
- Battery $SoC(t) \ge 0.30, \quad \forall t$
- Temperature $T_{\text{chip}}(t) \le 50.0^\circ\text{C}, \quad \forall t$
- Storage bounds $L_{\text{exec}}(t) \le L_{\max}, \quad L_{\text{dl}}(t) \le D_{\max}$
- Communication gating: Transmission only when $G(t) = 1$.

*(This serves as the theoretical upper bound for benchmark comparison).*

### 5.2 Formulation 2: Constrained Markov Decision Process (CMDP)
- **State space:** $s_t = \langle SoC(t), T_{\text{chip}}(t), G(t), P_{\text{harvest}}(t), L_{\text{exec}}(t), L_{\text{dl}}(t), \text{Metadata}(k) \rangle$
- **Reward function:** $R(s_t, a_t) = U_k(t) - c_{\text{energy}} E(a_t) - c_{\text{drop}} \mathbb{I}(\text{drop})$
- **Constraint penalties:** $C_{\text{batt}}(s_t) = \max(0, 0.30 - SoC(t))$, $C_{\text{temp}}(s_t) = \max(0, T_{\text{chip}}(t) - 50.0)$
- **Objective:** Find policy $\pi_\theta(a|s)$ maximizing expected discounted return:
  $$\max_\theta \mathbb{E}_{\tau \sim \pi_\theta} \left[ \sum_{t=0}^T \gamma^t R(s_t, a_t) \right] \quad \text{s.t.} \quad \mathbb{E}\left[\sum_{t=0}^T \gamma^t C_i(s_t)\right] \le \epsilon_i$$

### 5.3 Formulation 3: Online Lyapunov Drift-Plus-Penalty Scheduler
Define Lyapunov function measuring distance from safe boundaries:
$$V(t) = \frac{1}{2} Q_{\text{batt}}(t)^2 + \frac{1}{2} Q_{\text{temp}}(t)^2 + \frac{1}{2} L_{\text{exec}}(t)^2 + \frac{1}{2} L_{\text{dl}}(t)^2$$
At each time $t$, observe current queue states and choose action $a_t$ to minimize the drift-plus-penalty bound:
$$\min_{a_t} \left[ \Delta V(t) - V_{\text{weight}} \cdot \text{Utility}(a_t) \right]$$
This yields an optimal $O(1)$ real-time scheduler requiring **zero offline neural training** and provable queue stability!
