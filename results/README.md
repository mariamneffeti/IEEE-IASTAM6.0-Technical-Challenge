# Generated results

`heuristic_summary.csv` contains mean, sample standard deviation, and 95% Student-t intervals from five seeded three-orbit heuristic episodes (seeds 42–46). Recreate it and the seed-42 trajectory figure from the repository root:

```bash
python -m simulation.eval --episodes 5 --seed 42 --orbits 3 --output results/heuristic_summary.csv
python -m simulation.plot_trajectory
```

These are simulator results for the implemented heuristic, not flight telemetry or a comparison against unimplemented policies.
