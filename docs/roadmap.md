# IASTAM 6.0 - Problem 1: Project Roadmap & Study Guide

This roadmap breaks down how your team should tackle **Problem 1 (Process or Transmit?)** over the 7-week challenge, along with the core concepts and research papers you need to study.

---

## 🗓️ 7-Week Project Schedule

Align your internal deadlines with the official IASTAM 6.0 Challenge Phases.

### Phase 2: Research & Initial Development (Sept 2 – Sept 26)
* **Week 1: Research & Environment Setup**
  * **Goal:** Understand the physics and constraints.
  * **Tasks:** Read the recommended papers (below). Decide on your programming language (Python is highly recommended). Build a basic "Satellite Simulator" script that models a 90-minute orbit (45m sun, 45m eclipse) and tracks battery percentage, memory usage, and ground station visibility.
* **Week 2: The Baseline Model (Rule-Based)**
  * **Goal:** Get something working immediately.
  * **Tasks:** Write a simple `If-Else` scheduling algorithm. (e.g., *If battery > 80% -> Process Onboard. If battery < 20% -> Store. If Ground Station visible -> Transmit*). Test this against your simulator and record the results.
* **Week 3: Advanced Algorithm Design**
  * **Goal:** Build the "smart" Decision Engine.
  * **Tasks:** Choose your optimization method (e.g., Reinforcement Learning, Integer Linear Programming, or a Genetic Algorithm). Begin integrating this into your simulator to replace the dumb rule-based engine. 
* **Week 4: Paper Writing & Pitch Prep**
  * **Goal:** Prepare for the Mid-Review elimination.
  * **Tasks:** Finalize the **Interim Research Paper**. Compare your advanced algorithm's results against your baseline to prove it's better. Record your **2-Minute Pitch Video**.

### Mid-Review (Sept 26 – Sept 30)
* *Elimination Round: You must score at least 60/100 to proceed.*

### Phase 3: Final Development (Oct 1 – Oct 14)
* **Week 5: Incorporating Jury Feedback**
  * **Goal:** Fix flaws pointed out in the mid-review.
  * **Tasks:** Add edge-cases to your simulation (e.g., what if a solar flare corrupts some memory? What if a high-priority distress signal comes in?). Improve algorithm stability.
* **Week 6: Code Cleanup & Final Report**
  * **Goal:** Prepare deliverables.
  * **Tasks:** Document your source code well (GitHub repository). Write the final technical report outlining your architecture.
* **Week 7: D-Day Prep**
  * **Goal:** Practice the live pitch.
  * **Tasks:** Prepare your slides and scientific poster. Rehearse the live Q&A where you will defend your engineering choices.

---

## 📚 Core Principles & Concepts to Learn

To succeed, split these topics among your team members so you can specialize:

1. **Orbital Mechanics (The Basics):**
   * You don't need to be a rocket scientist, but you must understand **LEO (Low Earth Orbit)**. 
   * Know that a satellite orbits Earth in ~90 minutes. It spends half that time in the sun (charging batteries) and half in the dark (draining batteries). Ground station passes only last about 5 to 10 minutes.
2. **Resource-Constrained Project Scheduling Problem (RCPSP):**
   * This is the mathematical foundation of your problem. Look up how computer scientists solve scheduling problems when CPU, memory, and time are strictly limited.
3. **Edge Computing / Space Edge:**
   * Understand the difference between Cloud Computing (unlimited resources on Earth) and Edge Computing (processing data directly on the sensor/satellite where it's gathered).
4. **Markov Decision Processes (MDP) / Reinforcement Learning:**
   * If you want to use AI to solve this, learn how to frame the satellite's status as a "State", the decisions (Process/Store/Transmit) as an "Action", and the scientific value as a "Reward".

---

## 📄 Must-Read Papers (Official Recommendations)

These are the starting points officially recommended by the challenge for Track 1. Have your team read these in Week 1:

* **A Comprehensive Survey on Orbital Edge Computing: Systems, Applications, and Algorithms**
  * *Why read it:* It will give you the complete picture of what Edge computing in space looks like right now. (arXiv: 2306.00275)
* **Space AI: Leveraging Artificial Intelligence for Space to Improve Life on Earth**
  * *Why read it:* Great for understanding how AI is actually used onboard (e.g., dropping cloudy images so you don't waste bandwidth sending pictures of clouds to Earth). (arXiv: 2512.22399)
* **Advancing Earth Observation: A Survey on AI-Powered Image Processing in Satellites**
  * *Why read it:* Focuses on the trade-offs of image processing (one of the most data-heavy tasks) right on the satellite. (arXiv: 2501.12030)
* **Trabant: A Serverless Architecture for Multi-Tenant Orbital Edge Computing**
  * *Why read it:* Good for understanding how to schedule different tasks (multi-tenancy) dynamically. (arXiv: 2504.08337)
