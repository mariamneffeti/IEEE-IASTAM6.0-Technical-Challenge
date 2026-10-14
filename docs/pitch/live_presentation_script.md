# ASTRA — Live Presentation Script

**Purpose:** Live jury pitch supported by slides

**Target length:** About 4 minutes, plus questions

**Audience:** IASTAM 6.0 Track 1 assessment jury
**Delivery:** Speak to the audience; use the slide headlines and visuals as cues. Do not read slide text aloud.

## Story in One Sentence

ASTRA is a reproducible simulator and policy-comparison prototype for deciding how a resource-constrained Earth-observation satellite should process, queue, transmit, or discard payloads; early synthetic results show a trade-off between delivered utility and task completion, while exposing important thermal and validation gaps.

## Slide-by-Slide Script

### Slide 1 — The Decision in Orbit

**Time:** 0:00–0:30

**Key message:** Limited contact makes every payload decision consequential.

**On-slide text:**

> PROCESS · QUEUE · TRANSMIT · DROP

**Visual:** A simple 90-minute orbit timeline: sunlight and eclipse bands, one short ground-contact window, and a payload stream feeding the four choices. Keep labels to a few words.

**Speaker:**

“An Earth-observation satellite can collect data throughout an orbit, but it only has short opportunities to send data to the ground. At the same time, onboard processing competes for power, storage, and thermal headroom. ASTRA studies the decision for each payload: process it now, queue it, transmit it raw, or discard it.”

**Transition:** “We built a simulator to make those trade-offs measurable.”

### Slide 2 — What ASTRA Implements

**Time:** 0:30–1:10

**Key message:** The prototype connects resource state, policy choices, and measurable outcomes.

**On-slide text:**

> Payload → Scheduler → Process / Buffer / Downlink / Drop

Small secondary labels: `Battery`, `Thermal`, `Storage`, `Ground contact`.

**Visual:** One clean flow diagram. Show telemetry/resource constraints entering the scheduler and outcomes returning to the simulation. Distinguish “implemented” simulator components from future architecture with a small legend.

**Speaker:**

“ASTRA advances in one-second steps and models a 90-minute orbit, solar generation, a battery floor, storage, compute queues, temperature, and intermittent downlink. Those state variables feed four policies: transmit-all, greedy edge processing, a threshold heuristic, and an initial MaskablePPO agent. The FaaS and safety-guard concepts in our architecture are future design targets; this benchmark evaluates the simulator and policies that are actually implemented. That distinction matters when we interpret the results.”

**Transition:** “To interpret the results, it helps to see the experiment scope.”

### Slide 3 — Model and Evaluation

**Time:** 1:10–1:50

**Key message:** Results come from a paired, multi-orbit synthetic benchmark.

**On-slide text:**

> 4 policies · 5 shared seeds · 4 orbits per episode

At the bottom, clearly label: **Synthetic simulation — not flight data**.

**Visual:** A compact experiment card: four policy names, five seed markers, and four orbit loops. Add a small callout “mean, SD, 95% CI”. Avoid listing all simulator parameters.

**Speaker:**

“Each policy ran on the same five random seeds, with four simulated orbits per episode. Shared seeds keep the payload stream and contact schedule paired across policies. The modeled orbit has 55 minutes of sunlight and 35 minutes of eclipse, with randomized 120-to-180-second contact windows and a 20-megabit-per-second downlink. We report means, sample standard deviations, and 95 percent Student-t intervals. These operating parameters and payloads are synthetic, so the figures describe this simulator—not on-orbit performance.”

**Transition:** “The main result is a trade-off, not one policy winning every metric.”

### Slide 4 — Results: Utility Versus Completion

**Time:** 1:50–2:45

**Key message:** The heuristic leads on delivered-utility ratio; greedy edge completes more payloads.

**On-slide text:**

- Heuristic: **2.86%** delivered-utility ratio
- Greedy edge: **5.17%** task completion

Footer caveat: “5 paired episodes; synthetic workload”.

**Visual:** Use the repository’s policy-comparison plot ([PDF](../../results/figures/policy_comparison.pdf)). Highlight only decision quality and completion rate with two callouts. Keep the other metrics visible but de-emphasized; do not redraw values unless regenerated from the CSVs.

**Speaker:**

“The threshold heuristic achieved the highest mean delivered-utility ratio: 2.86 percent. This ratio compares utility delivered with the total base value generated in the episode. Greedy edge completed the largest share of generated payloads, at 5.17 percent, but its delivered-utility ratio was 0.47 percent. So completion count and delivered scientific value tell different stories. The heuristic also had a shorter average latency among the payloads it completed. The completion rates are modest, and only five scenarios were evaluated, so this is an initial comparison—not a general performance guarantee.”

**Transition:** “The learned policy and the thermal trace also show why we are treating this as early evidence.”

### Slide 5 — What the Prototype Has Not Solved

**Time:** 2:45–3:30

**Key message:** The current PPO result is unsuccessful, and the thermal threshold is not a hard safety limit.

**On-slide text:**

- PPO checkpoint: **0 tasks completed**
- Thermal trace: **52.48 °C peak** · threshold: 50 °C

**Visual:** Two side-by-side evidence cards: PPO task completion and the repository’s [two-orbit telemetry plot](../../results/figures/orbit_telemetry.pdf). Mark the 50 °C threshold and the 52.48 °C observed peak. Add “single training seed” near the PPO result.

**Speaker:**

“Our first PPO checkpoint completed no tasks in the held-out episodes. It used about 206 kilojoules, less than the processing-heavy policies, but more than transmit-all. Since it delivered no utility, the lower draw is not an efficiency gain. Separately, the thermal model uses a linear proxy. The 50-degree value pauses compute but does not cap temperature, and one trace reached 52.48 degrees. We therefore make no claim of a safe thermal controller or a successful learned policy.”

**Transition:** “Those findings set the priorities for the next development cycle.”

### Slide 6 — Next Steps and Close

**Time:** 3:30–4:00

**Key message:** ASTRA provides a baseline; realism, safety, and stronger comparisons are the next milestones.

**On-slide text:**

> Calibrate → Add safety guard → Compare → Validate

Small supporting labels: “Thermal model”, “Lyapunov + MILP”, “More seeds + telemetry”.

**Visual:** Four-step horizontal roadmap using the same colors and icons as earlier slides. End with ASTRA, team name, and the challenge name.

**Speaker:**

“Our next steps are to improve and validate the thermal model, add a deterministic safety guard, compare against Lyapunov scheduling and an offline oracle, and expand evaluation across training seeds and documented traces. ASTRA is a working research prototype and a measurement framework; the current results show where the trade-offs are and what evidence we still need. Thank you—we welcome your questions.”

## Slide Design Rules

- **One takeaway per slide.** Use the slide title as a conclusion, not a topic label.
- **Keep slides scannable.** Aim for one headline and no more than three short supporting labels. Put explanations in the spoken script.
- **Use readable type.** For a 16:9 room presentation, target at least 30 pt for titles and 22–24 pt for body labels. Avoid dense footnotes and tiny chart legends.
- **Use a stable visual system.** Keep the same title position, margins, typography, and color meanings throughout. Suggested palette: dark navy for structure, cyan for the ASTRA flow, amber for resource constraints, and coral only for measured risks or caveats.
- **Make evidence legible.** Crop the existing plots to the relevant axes, enlarge the important values, and preserve labels and uncertainty information where shown. Do not put the full benchmark table on a slide.
- **Separate fact from plan.** Mark implemented components as “current prototype” and future items as “next”. Never depict planned FaaS orchestration, Lyapunov/MILP, flight validation, or a hard thermal guard as already implemented.
- **Keep the deck visually homogeneous.** Use consistent icon style, line weight, chart colors, and transitions. Prefer simple reveals over decorative animation.

## Rehearsal and Q&A Preparation

- Rehearse to four minutes with a timer. Leave a pause after the two result callouts and the thermal caveat.
- Each speaker should be ready to explain the policy definitions, simulator assumptions, utility metric, paired seeds, confidence intervals, and why the PPO energy result is not an efficiency win.
- If asked whether ASTRA satisfies the 50 °C limit, answer plainly: **No. The current threshold throttles compute but does not impose a hard cap; the observed trace reaches 52.48 °C.**
- If asked whether the result is flight-validated, answer: **No. These are results from a synthetic simulator.**
- If asked which policy is best, answer by metric: **The heuristic leads on delivered-utility ratio in this run; greedy edge leads on completed-task rate.**
- Do not generalize the five evaluation episodes or single PPO training seed beyond the tested setup.
