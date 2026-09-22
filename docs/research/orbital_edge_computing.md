# Earth Observation Satellites, Orbital Edge Computing, and Serverless Edge Computing

## 1. Introduction

When reading research about modern Earth observation systems, you may encounter three terms:

1. **Earth observation satellites**
2. **Orbital edge computing**
3. **Serverless edge computing**

These terms are related, but they describe **different layers of the system**.

A simple way to remember them is:

> **Earth observation satellite = collects the data**  
> **Orbital edge computing = processes the data in or near orbit**  
> **Serverless edge computing = provides a way to run/manage computation without manually managing servers**

They can also be combined into one system.

---

# 2. Earth Observation Satellites

## 2.1 What is an Earth observation satellite?

An **Earth observation (EO) satellite** is a spacecraft equipped with sensors that observe and measure different characteristics of Earth.

The satellite may observe:

- Land
- Oceans
- Atmosphere
- Clouds
- Vegetation
- Cities
- Ice
- Fires
- Floods
- Pollution
- Agricultural areas

The sensors can collect different types of information.

For example:

- **Optical sensors** capture images similar to photographs.
- **Multispectral sensors** capture several wavelengths of light.
- **Hyperspectral sensors** capture many narrow wavelength bands.
- **Synthetic Aperture Radar (SAR)** can observe Earth using radar and can work even when there is no sunlight.

---

## 2.2 The traditional workflow

Traditionally, an EO satellite mainly acts as a **data collector**.

A simplified workflow is:

```text
        Earth
          ↑
          │
     Sensors
          │
          ↓
   ┌───────────────┐
   │ EO Satellite  │
   └───────────────┘
          │
          │ Raw data
          ↓
   Ground Station
          │
          ↓
    Data Center /
       Cloud
          │
          ↓
       Analysis
          │
          ↓
        User
```

For example, imagine that a satellite captures a large image of a forest.

The satellite might send the raw image to a ground station.

The ground infrastructure then performs tasks such as:

- Image processing
- Noise removal
- Classification
- Object detection
- Change detection
- Fire detection
- Vegetation analysis

---

# 3. Why Processing Satellite Data Is Difficult

EO satellites can generate a **large amount of data**.

However, communication between a satellite and Earth is constrained.

There are several important limitations.

## 3.1 Limited communication bandwidth

A satellite cannot continuously send unlimited amounts of data to Earth.

The communication link may have limited bandwidth, and the satellite may only have contact with a particular ground station during certain periods.

For example:

```text
Satellite
   │
   │  Large amount of raw data
   │
   ↓
Ground Station
```

If the satellite produces more data than it can transmit, data may have to wait in onboard storage.

---

## 3.2 Communication latency

The satellite and ground infrastructure are physically separated.

Data must travel through a communication link.

For some applications, waiting to send all the raw data to Earth before processing it may be inefficient.

For example, consider disaster detection.

If a satellite observes a wildfire:

```text
Satellite
   ↓
Send huge image
   ↓
Ground station
   ↓
Process image
   ↓
Detect fire
   ↓
Notify authorities
```

The system may waste time transmitting information that is not relevant.

---

## 3.3 Energy limitations

Satellites have limited energy resources.

They may rely on solar panels and batteries.

Therefore, onboard computing and communication must be carefully managed.

---

## 3.4 Limited computing resources

A satellite cannot necessarily use the same computing infrastructure as a large terrestrial data center.

Its hardware may be constrained by:

- Power consumption
- Weight
- Space
- Radiation tolerance
- Thermal conditions
- Cost
- Hardware reliability

This makes efficient computation particularly important.

---

# 4. What Is Edge Computing?

Before understanding **orbital edge computing**, it helps to understand normal **edge computing**.

## 4.1 Traditional cloud computing

In cloud computing, data is usually sent to a centralized data center.

For example:

```text
Device
  │
  │ Data
  ↓
Internet
  │
  ↓
Cloud Data Center
  │
  ↓
Processing
  │
  ↓
Result
```

The cloud provides powerful computing resources.

However, sending all data to a remote cloud can introduce:

- Network latency
- Bandwidth consumption
- Communication costs
- Privacy concerns
- Dependency on network connectivity

---

## 4.2 Edge computing

**Edge computing** moves computation closer to where data is generated.

Instead of:

```text
Device → Internet → Cloud
```

we can have:

```text
Device → Edge Server → Cloud
```

The edge server processes some of the data locally.

For example, a security camera could detect a person locally rather than continuously sending every video frame to the cloud.

---

# 5. What Is Orbital Edge Computing?

## 5.1 Definition

**Orbital edge computing** applies the edge computing concept to the space environment.

Instead of sending all raw satellite data to Earth, some computation is performed:

- Directly on the satellite
- On another nearby satellite
- On an orbital computing platform

The central idea is:

> **Process data closer to where it is generated, in orbit, before transmitting everything to Earth.**

A simplified system looks like:

```text
              Earth
                │
                │
          Ground Station
                ↑
                │
         Processed results
                │
                │
        ┌───────────────┐
        │ EO Satellite  │
        │               │
        │ Sensors       │
        │      ↓        │
        │ Onboard       │
        │ Computing     │
        └───────────────┘
                ↑
              Earth
```

---

# 6. Example: Wildfire Detection

Suppose an Earth observation satellite captures a large image of a forest.

### Traditional approach

```text
Satellite
   │
   │ Large raw image
   ↓
Ground Station
   │
   ↓
Cloud / Data Center
   │
   ↓
AI Model
   │
   ↓
Wildfire detected
```

The system transmits a large amount of data.

---

### Orbital edge approach

The satellite processes the image first.

```text
Satellite
   │
   ↓
Capture image
   │
   ↓
AI model runs onboard
   │
   ↓
Wildfire detected
   │
   ↓
Send important region / result
   │
   ↓
Ground Station
```

Instead of sending the entire raw image, the satellite could send:

```text
"Possible wildfire detected"

Location:
Latitude = ...
Longitude = ...

Confidence:
94%

Relevant image:
Small cropped region
```

This can significantly reduce the amount of data that needs to be transmitted.

---

# 7. Benefits of Orbital Edge Computing

## 7.1 Reduced communication bandwidth

The satellite can process raw data and transmit only useful information.

For example:

```text
Raw data:
1 GB

After onboard processing:
10 MB
```

The exact reduction depends on the application, but the principle is important:

> **Compute first, transmit later.**

---

## 7.2 Lower latency

Important events can be detected closer to where the data is generated.

For example:

```text
Satellite
   ↓
Fire detection
   ↓
Alert
```

rather than waiting for:

```text
Satellite
   ↓
Huge image
   ↓
Ground
   ↓
Cloud
   ↓
AI processing
   ↓
Alert
```

---

## 7.3 Better use of communication opportunities

Satellites may not always have a communication link with the desired ground station.

Orbital processing allows the satellite to make decisions before a communication opportunity becomes available.

---

## 7.4 Data filtering

Not every captured image or sensor measurement is equally important.

Onboard computation can filter data.

For example:

```text
100 images captured
        ↓
Onboard analysis
        ↓
95 ordinary images
5 important images
        ↓
Transmit only important data
```

---

# 8. Challenges of Orbital Edge Computing

Orbital edge computing also introduces challenges.

## 8.1 Limited hardware

Onboard computers may have fewer resources than cloud servers.

A large AI model that runs easily in a data center may be difficult to execute onboard.

---

## 8.2 Energy consumption

Computing consumes energy.

Therefore:

```text
More computation
       ↓
More energy consumption
```

The system must balance computation and communication.

---

## 8.3 Radiation

Space hardware can be exposed to radiation.

Electronic components therefore need appropriate protection and fault-tolerance mechanisms.

---

## 8.4 Software reliability

Software failures can be difficult to fix once hardware is deployed in orbit.

This makes:

- Testing
- Fault tolerance
- Monitoring
- Recovery
- Secure software updates

very important.

---

# 9. What Is Serverless Computing?

Now we move to a different concept.

**Serverless computing** is primarily a **software and infrastructure model**.

The word "serverless" does **not** mean that servers do not exist.

Servers still exist.

Instead, the developer does not need to manually manage the underlying server infrastructure.

---

# 10. Traditional Server-Based Model

Suppose we create an application that detects fires.

In a traditional architecture, an organization may need to manage:

```text
Server
 ├── Operating system
 ├── Runtime
 ├── Application
 ├── CPU
 ├── Memory
 └── Scaling
```

The team may have to think about:

- Provisioning servers
- CPU allocation
- Memory
- Scaling
- Server failures
- Software environments

---

# 11. Serverless Model

With serverless computing, the developer can focus on functions.

For example:

```text
detectFire(image)
classifyCloud(image)
compressImage(image)
detectFlood(image)
```

The infrastructure platform manages much of the underlying execution environment.

A simplified model is:

```text
Event
  │
  ↓
Serverless Function
  │
  ↓
Result
```

For example:

```text
New satellite image
       ↓
detectFire()
       ↓
AI inference
       ↓
Fire probability = 94%
```

---

# 12. Why Is It Called "Serverless"?

The name can be confusing.

There are still physical servers.

"Serverless" means:

> The application developer does not directly manage the servers responsible for running the function.

The infrastructure provider or platform handles things such as:

- Resource allocation
- Function execution
- Scaling
- Infrastructure management
- Often billing based on execution

---

# 13. What Is Serverless Edge Computing?

Now combine the two concepts:

```text
Serverless
      +
Edge Computing
      =
Serverless Edge Computing
```

The idea is to execute serverless functions **at or near the edge**, instead of only in centralized cloud data centers.

For example:

```text
Sensor
  ↓
Edge node
  ↓
Serverless function
  ↓
AI inference
  ↓
Result
```

The edge node may be:

- A local gateway
- A base station
- A nearby computing device
- A terrestrial edge server
- In some architectures, a satellite or orbital computing node

---

# 14. Serverless Edge Computing in Satellite Systems

This is where the concepts become particularly interesting.

Imagine a satellite with computing capability.

Instead of treating the onboard software as one large application, we can divide processing into functions.

For example:

```text
                 Satellite
                    │
             ┌──────┴──────┐
             │             │
        Sensor data     Sensor data
             │             │
             ↓             ↓
       detectFire()   detectFlood()
             │             │
             └──────┬──────┘
                    ↓
              Important result
                    │
                    ↓
              Ground station
```

The functions could be deployed or triggered depending on the current mission.

---

# 15. The Difference Between Orbital Edge and Serverless Edge

This is the most important distinction.

## Orbital edge computing asks:

> **Where should the computation happen?**

Answer:

> In or near orbit, close to the satellite-generated data.

---

## Serverless edge computing asks:

> **How should the computation be deployed and managed at the edge?**

Answer:

> Using a serverless/function-based execution model.

---

# 16. A Useful Analogy

Imagine a restaurant.

### Earth observation satellite

The satellite is like the **restaurant's kitchen collecting ingredients and preparing food**.

### Orbital edge computing

Instead of transporting all ingredients to another city for processing, the restaurant **processes them locally**.

This answers:

> Where does processing happen?

Locally.

### Serverless computing

Now imagine the restaurant has a system that automatically assigns cooking tasks to available workers whenever an order arrives.

The cook doesn't need to manage the entire restaurant infrastructure.

This answers:

> How are individual tasks executed?

Automatically, as needed.

---

# 17. Side-by-Side Comparison

| Concept | Main purpose | Main question |
|---|---|---|
| Earth observation satellite | Collect Earth data | What is observing Earth? |
| Cloud computing | Centralized computation | Where can large-scale computation happen? |
| Edge computing | Move computation closer to data | How can we reduce distance to the data? |
| Orbital edge computing | Compute in/near orbit | Can we process satellite data before sending it to Earth? |
| Serverless computing | Abstract server management | Can developers run functions without managing servers? |
| Serverless edge computing | Run serverless functions near the data source | Can functions execute dynamically at the edge? |

---

# 18. They Are Not Mutually Exclusive

A common misunderstanding is to think:

> "Orbital edge computing vs serverless edge computing"

as if these are two competing alternatives.

They can actually be **combined**.

For example:

```text
                 EARTH OBSERVATION
                     SATELLITE
                         │
                         │ Sensor data
                         ↓
                ┌─────────────────┐
                │ Orbital Edge    │
                │ Computing       │
                │                 │
                │ Serverless      │
                │ Functions       │
                └────────┬────────┘
                         │
                         │ Processed data
                         ↓
                   Ground Station
                         │
                         ↓
                    Cloud / Data
                      Center
                         │
                         ↓
                       User
```

Here:

- The **satellite** collects the data.
- **Orbital edge computing** determines that processing can happen in orbit.
- **Serverless computing** provides a function-based execution model.
- The **ground/cloud infrastructure** can perform additional heavy processing.

---

# 19. Example: Satellite Image Classification

Imagine a satellite observing agricultural fields.

It captures:

```text
Satellite image
       ↓
10,000 × 10,000 pixels
```

The system wants to detect unhealthy crops.

## Traditional architecture

```text
Satellite
    ↓
Transmit raw image
    ↓
Ground station
    ↓
Cloud
    ↓
AI model
    ↓
Crop health classification
```

Potential problem:

- Large amount of data transmitted
- Communication resources consumed
- Processing waits for data to reach Earth

---

## Orbital edge architecture

```text
Satellite
    ↓
Capture image
    ↓
Onboard preprocessing
    ↓
AI classification
    ↓
Only relevant information transmitted
```

For example:

```text
Field A → Healthy
Field B → Healthy
Field C → Possible crop stress
Field D → Healthy
```

---

## Serverless orbital-edge architecture

The processing can be divided into functions:

```text
Image
  │
  ↓
preprocessImage()
  │
  ↓
detectFields()
  │
  ↓
classifyCropHealth()
  │
  ↓
generateReport()
  │
  ↓
Transmit result
```

Each function represents a separate computational task.

---

# 20. Why Serverless Can Be Useful at the Edge

Serverless approaches can provide several useful properties.

## 20.1 Modularity

Instead of one large application:

```text
Huge application
```

we can have:

```text
Function A
Function B
Function C
Function D
```

This can make applications easier to organize.

---

## 20.2 Dynamic execution

Different functions may be needed for different situations.

For example:

```text
Normal observation
      ↓
Basic preprocessing

Fire detected
      ↓
Run fire-analysis function

Flood detected
      ↓
Run flood-analysis function
```

The system does not necessarily need to execute every function for every image.

---

## 20.3 Resource efficiency

If a function is only needed occasionally, the architecture can potentially avoid continuously dedicating resources to it.

For example:

```text
No fire
   ↓
fireDetection function not needed beyond monitoring

Fire detected
   ↓
activate additional processing
```

The exact implementation depends on the serverless platform and hardware.

---

# 21. Important Difference: Serverless Does Not Automatically Mean Orbital

This distinction is essential.

A serverless function can run in many places.

For example:

```text
Serverless function
       │
       ├── Cloud data center
       │
       ├── Edge server
       │
       ├── Local gateway
       │
       └── Potentially orbital hardware
```

Therefore:

> **Serverless ≠ orbital**

And:

> **Orbital edge ≠ necessarily serverless**

They are independent architectural concepts that can be combined.

---

# 22. Four Possible Architectures

We can visualize the possibilities.

## Architecture 1: Cloud only

```text
Satellite
   ↓
Ground
   ↓
Cloud
   ↓
Processing
```

Little or no processing occurs in orbit.

---

## Architecture 2: Orbital edge without serverless

```text
Satellite
   ↓
Onboard application
   ↓
Processing
   ↓
Ground
```

The satellite processes data onboard, but the software may be a conventional application.

---

## Architecture 3: Terrestrial serverless edge

```text
Device
   ↓
Edge server
   ↓
Serverless functions
   ↓
Cloud
```

Serverless functions execute at the terrestrial edge.

---

## Architecture 4: Orbital serverless edge

```text
EO Satellite
     ↓
Orbital computing
     ↓
Serverless functions
     ↓
Processed result
     ↓
Ground station
     ↓
Cloud
```

This combines both ideas.

---

# 23. What Research on This Topic Usually Investigates

A research project about **serverless edge computing for Earth observation satellites** could investigate questions such as:

### Resource management

- How should limited CPU, memory, storage, and energy be allocated?
- Which functions should execute onboard?
- Which functions should execute on the ground?

### Task scheduling

- When should a function execute?
- How should tasks be prioritized?
- How should the system react to limited communication windows?

### Energy efficiency

- Is it more energy-efficient to compute onboard or transmit raw data?
- How should computation and communication energy be jointly optimized?

### Latency

- How much latency can be reduced by orbital processing?
- Which applications benefit most from onboard processing?

### AI inference

- Can machine-learning models run efficiently on satellite hardware?
- How can models be compressed or optimized for orbital execution?

### Serverless orchestration

- How can functions be deployed dynamically?
- How can functions migrate between satellites, edge nodes, and ground infrastructure?
- How can resources be allocated to functions dynamically?

### Reliability

- How can serverless functions recover from hardware or communication failures?
- How can the system operate when connectivity to Earth is temporarily unavailable?

### Security

- How can functions and data be protected in a distributed space-edge environment?
- How can unauthorized code execution be prevented?

---

# 24. A More Complete Architecture

A realistic future architecture might look like:

```text
                    ┌──────────────────────┐
                    │      Ground / Cloud  │
                    │                      │
                    │ Heavy AI processing  │
                    │ Storage              │
                    │ Global coordination  │
                    └──────────▲───────────┘
                               │
                         Communication
                               │
                               │
              ┌────────────────┴────────────────┐
              │                                 │
       ┌──────┴──────┐                   ┌──────┴──────┐
       │ Satellite 1 │                   │ Satellite 2 │
       │             │                   │             │
       │ Sensors     │                   │ Sensors     │
       │     ↓       │                   │     ↓       │
       │ Edge        │◄───────►          │ Edge        │
       │ Computing   │   Satellite       │ Computing   │
       │     ↓       │   communication   │     ↓       │
       │ Functions   │                   │ Functions   │
       └─────────────┘                   └─────────────┘
```

This creates a distributed computing environment involving:

- Satellites
- Inter-satellite links
- Ground stations
- Edge infrastructure
- Cloud infrastructure

---

# 25. The Key Trade-Off: Compute vs Communication

One of the most important ideas in this field is the trade-off between **computation and communication**.

Suppose a satellite has two choices.

### Option A: Transmit raw data

```text
Raw data
   ↓
Communication
   ↓
Ground
   ↓
Processing
```

Communication consumes resources.

### Option B: Process onboard

```text
Raw data
   ↓
Onboard computation
   ↓
Small result
   ↓
Communication
```

Computation consumes resources.

Therefore, the system has to decide:

> Is it cheaper/faster/better to compute the data here or transmit it elsewhere?

This is one of the central optimization problems in edge computing.

---

# 26. Example of the Trade-Off

Suppose:

```text
Raw image = 500 MB
Processed result = 5 MB
```

The satellite can either:

### Choice 1

Transmit:

```text
500 MB
```

and let the ground system process it.

### Choice 2

Perform onboard processing and transmit:

```text
5 MB
```

Choice 2 saves communication bandwidth, but requires onboard computation and energy.

Therefore, the optimal decision depends on:

- CPU availability
- Energy availability
- Communication bandwidth
- Communication cost
- Processing time
- Required latency
- Importance of the data
- Current satellite state

---

# 27. A Simple Mental Model

Whenever you encounter these terms, ask three questions.

## Question 1: What is collecting the data?

Answer:

> **Earth observation satellite**

---

## Question 2: Where is the data processed?

If it is processed close to the satellite:

> **Orbital edge computing**

If it is processed primarily in a distant data center:

> **Cloud computing**

---

## Question 3: How is the computation organized?

If the system uses independently executable, dynamically managed functions:

> **Serverless computing**

If those functions execute near the data source:

> **Serverless edge computing**

---

# 28. Final Summary

The three concepts operate at different levels.

```text
┌──────────────────────────────────────────┐
│ Earth Observation Satellite              │
│                                          │
│ Collects Earth data                      │
└──────────────────┬───────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────┐
│ Orbital Edge Computing                   │
│                                          │
│ Processes data in/near orbit              │
└──────────────────┬───────────────────────┘
                   │
                   ↓
┌──────────────────────────────────────────┐
│ Serverless Edge Computing                │
│                                          │
│ Executes computation as managed          │
│ functions close to the data              │
└──────────────────┬───────────────────────┘
                   │
                   ↓
             Ground / Cloud
```

The most important distinction is:

> **Orbital edge computing describes the location and architectural idea of performing computation near the satellite/data source.**

> **Serverless edge computing describes an execution and infrastructure model where computational functions are run at the edge without the application developer directly managing the underlying servers.**

And they can be combined:

> **An Earth observation satellite can use orbital edge computing to process sensor data in space, while serverless techniques can be used to organize and dynamically execute individual processing functions.**

This combination is particularly interesting for research because satellites have constrained resources, intermittent communication, limited energy, and potentially large volumes of sensor data. These constraints make decisions about **where, when, and how computation should happen** central to the design of future space-based computing systems.
