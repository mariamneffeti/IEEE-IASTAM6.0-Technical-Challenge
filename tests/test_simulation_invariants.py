import sys
from simulation.satellite_sim import Satellite
from simulation.baseline import heuristic_agent

def assert_identical_telemetry(t1, t2, step):
    for k in t1:
        if t1[k] != t2[k]:
            print(f"Mismatch at step {step} for key {k}: {t1[k]} != {t2[k]}")
            return False
    return True

def do_nothing_policy(sat):
    return []

def main():
    print("--- Running Sanity Checks ---")
    
    # Configuration
    seed = 42
    orbits = 3
    max_steps = 90 * 60 * orbits
    gs_speed_mb = 20.0 / 8.0 # 2.5 MB/s
    
    # ==========================================
    # Check 1: Same seed gives identical telemetry
    # ==========================================
    print("Check 1: Testing identical telemetry on same seed... (simulating 2 runs)")
    sat1 = Satellite(seed=seed)
    sat2 = Satellite(seed=seed)
    
    match = True
    for i in range(max_steps):
        a1 = heuristic_agent(sat1)
        a2 = heuristic_agent(sat2)
        sat1.step(a1)
        sat2.step(a2)
        if not assert_identical_telemetry(sat1.get_telemetry(), sat2.get_telemetry(), i):
            match = False
            break
            
    if match:
        print("✅ Check 1 Passed: The same seed run twice gave identical telemetry tick-by-tick.")
    else:
        print("❌ Check 1 Failed.")

    # ==========================================
    # Check 2: Do-nothing policy
    # ==========================================
    print("\nCheck 2: Testing do-nothing policy... (simulating 1 run)")
    sat_idle = Satellite(seed=seed)
    for _ in range(max_steps):
        sat_idle.step([])
        
    tel_idle = sat_idle.get_telemetry()
    
    c2_pass = True
    if tel_idle["payloads_downlinked"] != 0:
        print(f"❌ Check 2 Failed: Do-nothing policy downlinked {tel_idle['payloads_downlinked']} payloads.")
        c2_pass = False
    if tel_idle["involuntary_drops"] <= 0:
        print(f"❌ Check 2 Failed: Do-nothing policy had {tel_idle['involuntary_drops']} involuntary drops (expected > 0).")
        c2_pass = False
    if tel_idle["cumulative_mmu_usage_mb"] < 0 or tel_idle["cumulative_ram_usage_mb"] < 0:
        print(f"❌ Check 2 Failed: Do-nothing policy had negative RAM or MMU.")
        c2_pass = False
        
    if c2_pass:
        print("✅ Check 2 Passed: Do-nothing policy behaved exactly as expected (0 downlinked, drops > 0, no negative storage).")

    # ==========================================
    # Check 3: Conservation rules
    # ==========================================
    print("\nCheck 3: Testing conservation (downlinks <= generated, bandwidth limit)...")
    # We use sat1 from the first test
    tel1 = sat1.get_telemetry()
    c3_pass = True
    
    if tel1["payloads_downlinked"] > tel1["payloads_generated"]:
        print(f"❌ Check 3 Failed: Downlinked ({tel1['payloads_downlinked']}) > Generated ({tel1['payloads_generated']}).")
        c3_pass = False
        
    # GS Seconds = 3 orbits, each orbit has a GS pass
    # Technically, we should just check the actual GS seconds passed
    # Let's count GS seconds during the simulation
    sat3 = Satellite(seed=seed)
    gs_seconds = 0
    for _ in range(max_steps):
        sat3.step(heuristic_agent(sat3))
        if sat3.env.in_gs_pass:
            gs_seconds += 1
            
    tel3 = sat3.get_telemetry()
    max_possible_bw = gs_seconds * gs_speed_mb
    
    if tel3["bandwidth_used_mb"] > max_possible_bw:
        print(f"❌ Check 3 Failed: Bandwidth used ({tel3['bandwidth_used_mb']:.2f}) > Max theoretical ({max_possible_bw:.2f}).")
        c3_pass = False
        
    if c3_pass:
        print(f"✅ Check 3 Passed: Downlinks ({tel1['payloads_downlinked']}) <= Generated ({tel1['payloads_generated']}). Bandwidth ({tel3['bandwidth_used_mb']:.2f} MB) <= Max GS limit ({max_possible_bw:.2f} MB).")

    # ==========================================
    # Check 4: Policy independence on data generation
    # ==========================================
    print("\nCheck 4: Testing policy independence on data generation...")
    tel_heur = tel1
    
    if tel_idle["payloads_generated"] == tel_heur["payloads_generated"] and \
       abs(tel_idle["total_generated_value_snapshot"] - tel_heur["total_generated_value_snapshot"]) < 1e-6:
        print(f"✅ Check 4 Passed: Do-nothing and Heuristic produced exactly the same generation stats on seed {seed}.")
    else:
        print("❌ Check 4 Failed: Generation logic diverged between policies!")
        print(f"Idle: {tel_idle['payloads_generated']} | Heur: {tel_heur['payloads_generated']}")
        print(f"Idle Val: {tel_idle['total_generated_value_snapshot']} | Heur Val: {tel_heur['total_generated_value_snapshot']}")

if __name__ == "__main__":
    main()
