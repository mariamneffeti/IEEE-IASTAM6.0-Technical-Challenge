# IASTAM 6.0 Track 1 — Process or Transmit?

A research prototype for deciding when a LEO Earth-observation satellite should process, queue, downlink, or drop incoming payloads. The repository includes a one-second simulator, a rule-based heuristic, a Gymnasium environment, evaluation and plotting scripts, verification scripts, challenge references, and an IEEE paper draft.

## Current implementation

- **Simulator:** seeded 90-minute orbit clock, 55-minute sunlight / 35-minute eclipse, randomized 120–180 second ground-station windows, 100 Wh battery model, 20 Mbps downlink, synthetic optical/SAR payloads, simplified first-order thermal proxy, and per-second RAM-reset SEU events.
- **Policy:** multi-threshold heuristic in `simulation/baseline.py`.
- **Learning environment:** Gymnasium environment in `simulation/rl_env.py`; trained-policy results are not included.
- **Evaluation:** five four-orbit heuristic episodes by default. The current run reports a mean decision-quality ratio of 0.0283, completed-task rate of 0.0153, total modeled energy of 291.414 kJ, and completed-delivery latency of 654.00 s. These are simulator results with five seeds, not flight measurements. This is a single-policy characterization; transmit-all, greedy-edge, Lyapunov, and MILP comparisons are not yet implemented.
- **Thermal limitation:** the 50°C threshold pauses compute but does not enforce a hard cap. The saved seed-42 two-orbit trace reaches 52.48°C.

The simulator is a research abstraction, not a flight-calibrated or high-fidelity radiation/thermal model. See [the simulator model notes](docs/design/simulator_model.md) for assumptions and limitations.

## Repository layout

```text
.
├── simulation/              # Simulator, heuristic, Gymnasium environment, evaluator, dashboard
├── tests/                   # Determinism, conservation, and Gymnasium environment checks
├── configs/                 # Configuration-loading support is planned; defaults are in SimConfig
├── results/                 # Five-seed summary CSV and two-orbit trajectory figures
├── docs/
│   ├── challenge/           # Official specification, context, dates
│   ├── design/              # Architecture diagrams and simulator model notes
│   └── research/            # Literature notes and source papers
├── paper/
│   ├── source/              # IEEE LaTeX source and class
│   ├── build/               # Compiled PDF and LaTeX build files
│   └── Process_or_Transmit_IEEE.md
├── AGENTS.md                # Research and collaboration requirements
└── requirements.txt
```

The main folders also have short guides: [simulation](simulation/README.md), [configuration status](configs/README.md), and [generated results](results/README.md).

## Setup and commands

Use Python 3.10+ and install the dependencies from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the implemented heuristic evaluation and regenerate the two-orbit figure from the repository root:

```bash
python -m simulation.eval --episodes 5 --seed 42 --orbits 4 --output results/heuristic_summary.csv
python -m simulation.plot_trajectory
```

Run the verification scripts when changing the simulator or RL environment:

```bash
python -m tests.test_simulation_invariants
python -m tests.check_rl_environment
```

Launch the dashboard with `python -m simulation.dashboard`.

Compile the IEEE draft from the repository root:

```bash
cd paper/source
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../build Process_or_Transmit_IEEE.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../build Process_or_Transmit_IEEE.tex
```

The paper source is available as [Markdown](paper/Process_or_Transmit_IEEE.md) and [IEEE LaTeX](paper/source/Process_or_Transmit_IEEE.tex); the current [compiled PDF](paper/build/Process_or_Transmit_IEEE.pdf) is in `paper/build/`. Author email and team/institution metadata fields still need confirmation. See [the project roadmap](docs/roadmap.md) and [challenge context](docs/challenge/problem_context.md).
