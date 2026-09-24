# Generated results

The comparison directory contains a paired benchmark of transmit-all, greedy-edge, the threshold heuristic, and one MaskablePPO checkpoint. Five four-orbit episodes use shared evaluation seeds 1001–1005. PPO was trained with seed 7 for 100,000 requested timesteps; its evaluation produced zero completed tasks, so this is an exploratory negative result rather than a competitive policy. Summary CSVs report means, sample standard deviations, and 95% Student-t intervals. The paired CSV reports episode-wise differences from the heuristic. The policy comparison PDF plots four primary metrics.

Recreate the benchmark and figures from the repository root:

    python -m simulation.train_rl --timesteps 100000 --seed 7 --output results/models/astra_ppo_seed7
    python -m simulation.compare --policies transmit_all greedy_edge heuristic --rl-model results/models/astra_ppo_seed7.zip --episodes 5 --seed 1001 --orbits 4 --output-dir results/comparison
    python -m simulation.plot_comparison
    python -m simulation.plot_trajectory

heuristic_summary.csv preserves the earlier standalone heuristic run (seeds 42–46). These are synthetic simulator results, not flight telemetry. The committed PPO checkpoint is about 203 KB; its metadata records the training seed and simulator configuration.
