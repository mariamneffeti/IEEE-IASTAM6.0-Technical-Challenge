"""Train a MaskablePPO policy on the ASTRA Gymnasium environment."""

import argparse
import json
from pathlib import Path
from dataclasses import asdict

def train(total_timesteps: int, seed: int, output_path: str) -> Path:
    try:
        import gymnasium
        import stable_baselines3
        import torch
        from sb3_contrib import MaskablePPO
        from simulation.rl_env import SatelliteEnv
        from simulation.satellite_sim import SimConfig
    except ImportError as exc:
        raise RuntimeError(
            "RL training requires torch, stable-baselines3, sb3-contrib, and gymnasium; "
            "install repository requirements first."
        ) from exc

    torch.manual_seed(seed)
    env = SatelliteEnv(max_orbits=4)
    model = MaskablePPO(
        "MlpPolicy",
        env,
        seed=seed,
        verbose=1,
        device="auto",
        n_steps=2048,
        batch_size=256,
        gamma=0.99,
        ent_coef=0.01,
    )
    model.learn(total_timesteps=total_timesteps)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(destination))
    env.close()
    model_path = destination.with_suffix(".zip")
    metadata = {
        "algorithm": "MaskablePPO",
        "seed": seed,
        "requested_timesteps": total_timesteps,
        "training_timesteps": model.num_timesteps,
        "training_orbits_per_episode": 4,
        "evaluation_seeds_must_be_disjoint": True,
        "sim_config": asdict(SimConfig()),
        "torch_version": torch.__version__,
        "gymnasium_version": gymnasium.__version__,
        "stable_baselines3_version": stable_baselines3.__version__,
    }
    metadata_path = destination.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved MaskablePPO policy: {model_path}")
    print(f"Saved training metadata: {metadata_path}")
    return model_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", default="results/models/astra_ppo_seed7")
    args = parser.parse_args()
    if args.timesteps < 1:
        parser.error("--timesteps must be positive")
    train(args.timesteps, args.seed, args.output)


if __name__ == "__main__":
    main()
