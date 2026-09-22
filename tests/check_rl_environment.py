import numpy as np
from gymnasium.utils.env_checker import check_env

from simulation.rl_env import SatelliteEnv

def test_environment():
    print("Initializing SatelliteEnv...")
    env = SatelliteEnv()
    
    print("\n--- Running Gymnasium check_env ---")
    try:
        # check_env runs various validations including random sampling
        check_env(env, warn=True)
        print("check_env passed successfully!")
    except Exception as e:
        raise AssertionError(f"check_env failed: {e}") from e

    print("\n--- Running Custom Masked Action Loop ---")
    # Reset to start a fresh 3-orbit episode
    obs, info = env.reset(seed=123)
    
    steps = 1000
    total_reward = 0.0
    error_count = 0
    
    for i in range(steps):
        # 1. Get the action mask
        mask = env.action_masks()
        
        # 2. Sample valid actions for each payload slot
        action = np.zeros(env.top_k, dtype=int)
        for j in range(env.top_k):
            valid_actions = np.where(mask[j])[0]
            if len(valid_actions) > 0:
                action[j] = env.np_random.choice(valid_actions)
            else:
                action[j] = 0 # fallback
        
        # 3. Step the environment
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        # 4. Assert masks prevent invalid simulator actions.
        feedback = info.get("feedback", [])
        for fb in feedback:
            if fb.get("type") == "error":
                print(f"Step {i} Error Feedback: {fb}")
                error_count += 1
                
        if terminated or truncated:
            print(f"Episode ended early at step {i}")
            break
            
    print(f"\nRan {steps} steps using purely masked random actions.")
    print(f"Total Reward Accumulation: {total_reward:.2f}")
    
    if error_count == 0:
        print("✅ SUCCESS: 0 error feedbacks received. Masking logic perfectly bounded the agent.")
    else:
        print(f"❌ FAILED: Received {error_count} error feedbacks despite masking.")
        raise AssertionError(f"Masked action loop emitted {error_count} error feedbacks")

if __name__ == "__main__":
    test_environment()
