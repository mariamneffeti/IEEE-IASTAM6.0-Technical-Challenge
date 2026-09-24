# Simulation package

The package contains the satellite simulator, transmit-all and greedy-edge reference policies, threshold heuristic, Gymnasium environment, MaskablePPO trainer, paired evaluator, plots, and dashboard.

From the repository root:

    python -m simulation.train_rl --timesteps 100000 --seed 7 --output results/models/astra_ppo_seed7
    python -m simulation.compare --policies transmit_all greedy_edge heuristic --rl-model results/models/astra_ppo_seed7.zip --episodes 5 --seed 1001 --orbits 4 --output-dir results/comparison
    python -m simulation.plot_comparison
    python -m simulation.plot_trajectory
    python -m simulation.dashboard

The comparison uses common random seeds across policies. The initial MaskablePPO checkpoint had zero task completions on the held-out episodes. Treat it as a baseline for continued reward/training diagnosis, not as a successful learned controller. Lyapunov and MILP policies are not implemented. See the [comparison protocol](../docs/research/policy_comparison_protocol.md), [root README](../README.md), and [simulator model notes](../docs/design/simulator_model.md).
