# ASTRA — Adaptive Satellite Task and Resource Allocator

ASTRA is a research prototype for IASTAM 6.0 Track 1, Problem 1 (“Process or Transmit?”): deciding when a LEO Earth-observation satellite should process, queue, downlink, or drop incoming payloads.

## Current implementation

- **Simulator:** seeded 90-minute orbit clock, 55-minute sunlight / 35-minute eclipse, randomized 120–180 second ground-station windows, 100 Wh battery model, 20 Mbps downlink, synthetic optical/SAR payloads, first-order thermal proxy, and per-second RAM-reset SEU events.
- **Policies:** transmit-all, greedy-edge, and threshold heuristic are implemented; an initial MaskablePPO policy can be trained in the Gymnasium environment.
- **Evaluation:** five paired four-orbit episodes (seeds 1001–1005) compare four policies. The heuristic achieved mean decision quality 0.02860; greedy-edge completed the most tasks (0.05167). The single-seed PPO checkpoint completed no tasks, so its lower energy is an inactivity outcome, not a performance gain. Eight metrics, summary statistics, and paired differences are under results/comparison. These are simulator results, not flight measurements.
- **Not implemented:** Lyapunov scheduling and a MILP oracle remain future comparison targets.
- **Thermal limitation:** the 50°C threshold pauses compute but does not enforce a hard cap. The seed-42 two-orbit trace reaches 52.48°C.

The simulator is a research abstraction, not a flight-calibrated or high-fidelity radiation/thermal model. See [simulator model notes](docs/design/simulator_model.md).

## Repository layout

    simulation/       Simulator, policies, Gymnasium/RL, training, evaluation, plotting
    tests/            Determinism, conservation, and Gymnasium environment checks
    configs/          Configuration-loading support; defaults currently live in SimConfig
    results/          Paired benchmark data, PPO checkpoint, and generated figures
    docs/             Challenge, design, research protocol, and pitch materials
    paper/source/     IEEE LaTeX source and class
    paper/build/      Compiled PDF and LaTeX build files
    AGENTS.md         Research and collaboration requirements
    requirements.txt  Python dependencies

See the guides for [simulation](simulation/README.md), [configuration status](configs/README.md), and [generated results](results/README.md).

## Setup

Use Python 3.10+:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Train and compare policies

Training seed 7 is separate from the held-out evaluation seeds 1001–1005:

    python -m simulation.train_rl --timesteps 100000 --seed 7 --output results/models/astra_ppo_seed7
    python -m simulation.compare --policies transmit_all greedy_edge heuristic --rl-model results/models/astra_ppo_seed7.zip --episodes 5 --seed 1001 --orbits 4 --output-dir results/comparison
    python -m simulation.plot_comparison
    python -m simulation.plot_trajectory

The benchmark outputs per-episode metrics, mean/standard deviation/95% confidence intervals, and paired differences from the heuristic. Read the [comparison protocol](docs/research/policy_comparison_protocol.md) before interpreting the exploratory PPO result.

## Verification

    python -m tests.test_simulation_invariants
    python -m tests.check_rl_environment

Launch the dashboard with python -m simulation.dashboard.

## IEEE paper

Compile from the repository root:

    cd paper/source
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../build Process_or_Transmit_IEEE.tex
    pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../build Process_or_Transmit_IEEE.tex

The draft is available as [Markdown](paper/Process_or_Transmit_IEEE.md) and [IEEE LaTeX](paper/source/Process_or_Transmit_IEEE.tex); the compiled PDF is in [paper/build](paper/build/). Author email and official team/institution metadata still need confirmation. See the [project roadmap](docs/roadmap.md) and [challenge context](docs/challenge/problem_context.md).
