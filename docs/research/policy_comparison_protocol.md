# ASTRA policy comparison protocol

## Research question

Under one shared simulator and workload, how do transmission-only, immediate edge processing, the existing threshold heuristic, and a learned MaskablePPO policy compare on delivered utility, task completion, energy, latency, memory use, SEUs, and safe-mode events?

## Policies

| Policy | Implemented behavior | Purpose |
|---|---|---|
| `transmit_all` | FIFO raw downlink during contact; no onboard processing or voluntary drops | Conventional bent-pipe reference |
| `greedy_edge` | Process the oldest eligible payload as soon as queue capacity allows; downlink processed outputs during contact | Immediate-processing reference |
| `heuristic` | Current multi-threshold rule: contact-aware downlink, SoC/temperature-gated processing, stale-data drops under storage pressure | Current ASTRA baseline |
| `rl_<model-name>` | Deterministic actions from a trained MaskablePPO policy with invalid-action masks | Learned policy candidate |

All policies use the same `SimConfig`, simulator safety and resource mechanics, orbit duration, and evaluation seeds. Transmit-all and greedy-edge are operational definitions of comparison baselines, not independently optimized implementations. Greedy-edge still experiences the simulator's shared power, queue, and thermal constraints.

## Training and held-out evaluation

Train PPO independently of the evaluation scenarios. The suggested first run uses seed 7 and 100,000 training steps; its episodes span four orbits. Evaluate on seeds starting at 1001, with at least five four-orbit episodes. Do not tune hyperparameters or select checkpoints using these held-out evaluation seeds. Repeat training with multiple training seeds before making strong claims about RL performance.

```bash
python -m simulation.train_rl --timesteps 100000 --seed 7 \
  --output results/models/astra_ppo_seed7

python -m simulation.compare \
  --policies transmit_all greedy_edge heuristic \
  --rl-model results/models/astra_ppo_seed7.zip \
  --episodes 5 --seed 1001 --orbits 4 \
  --output-dir results/comparison

python -m simulation.plot_comparison
```

The evaluator uses paired episode seeds across policies. It writes one row per policy and seed to `comparison_episodes.csv`, per-policy means, sample SDs, and 95% Student-t intervals to `comparison_summary.csv`, and paired differences from the heuristic to `comparison_paired_vs_heuristic.csv`. The plot shows 95% intervals for four primary outcomes. For small samples and rare events, intervals remain uncertain; report the episode-level data and do not interpret overlapping or clipped intervals as formal proof of equality or safety.

## Current exploratory result

The current run used five evaluation seeds (1001–1005). The threshold heuristic obtained mean decision quality 0.02860; greedy-edge completed 5.17% of generated payloads but obtained decision quality 0.00470. The PPO checkpoint completed zero tasks and consumed 206.0 kJ on average. Since it delivered no output, its lower energy is not an efficiency improvement. PPO used one training seed and only about 4.6 four-orbit episodes at 100,000 requested timesteps; this is insufficient to draw conclusions about RL generally. Treat it as an initial benchmark and diagnose/extend training before making comparative claims.

## Metrics

- **Decision quality:** delivered utility divided by the sum of generated payload base values before processing.
- **Completed-task rate:** fully downlinked payloads divided by generated payloads.
- **Energy:** cumulative modeled base, compute, and communication draw.
- **Latency:** mean capture-to-completion time for fully downlinked payloads only.
- **MMU/RAM use:** time-average occupancy as a percentage of capacity.
- **SEU/safe-mode events:** per-episode event counts.

These metrics characterize the simulator. Its thermal model is a linear proxy, the 50°C value throttles compute but is not a hard cap, and a brownout can occur after a tick's actions have been applied. The workload and processing ratios are synthetic assumptions, not flight-calibrated data.
