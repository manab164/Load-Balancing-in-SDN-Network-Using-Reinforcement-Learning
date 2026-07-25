# Load-Balancing-in-SDN-Network-Using-Reinforcement-Learning
## Overview

This project presents an intelligent **Software-Defined Networking (SDN)** load-balancing framework that uses **Reinforcement Learning (Q-Learning)** to dynamically select optimal routing paths and efficiently distribute network traffic. Unlike traditional static routing methods, the proposed system continuously learns from network conditions and adapts its routing decisions to reduce congestion, improve bandwidth utilization, and enhance overall network performance. The system was implemented using **Mininet**, **Ryu SDN Controller**, **Open vSwitch**, and the **OpenFlow 1.3** protocol.

---

## Key Features

- Intelligent load balancing using the **Q-Learning** algorithm.
- Custom SDN topology with **12 OpenFlow switches** and **10 hosts**.
- Mesh-based architecture providing multiple routing paths.
- Dynamic path selection based on learned network states.
- Real-time monitoring of network statistics through the **Ryu Controller**.
- Automatic Q-table updates using a reward-based learning mechanism.
- MAC learning, ARP proxy handling, loop prevention, and dynamic flow installation.
- Performance evaluation using **Mininet** and **OpenFlow-enabled** switches.

---

## Technologies Used

- Python
- Software-Defined Networking (SDN)
- Reinforcement Learning (Q-Learning)
- Ryu Controller
- Mininet
- Open vSwitch (OVS)
- OpenFlow 1.3
- Ubuntu 20.04 LTS
- Comparative Analysis

---

## Comparative Analysis

This project includes two major comparative studies to evaluate the effectiveness of the proposed approach.

### 1. Network Topology Comparison

Different SDN topologies were analyzed:

- Tree Topology
- Ring Topology
- Mesh Topology

The comparison was performed using **network delay** as the evaluation metric. The **Mesh Topology** demonstrated superior performance by providing multiple routing paths, improved redundancy, lower congestion, and better fault tolerance, making it the most suitable topology for reinforcement learning-based routing.

### 2. Routing Algorithm Comparison

The proposed **Q-Learning-based routing** was compared with the traditional **Shortest Path Routing** approach.

The comparison focused on the following performance metrics:

- Bandwidth
- Throughput
- Network Delay
- Traffic Distribution
- Resource Utilization

Experimental results showed that the Reinforcement Learning approach dynamically adapted to changing network conditions and achieved better traffic distribution than conventional shortest-path routing.

---

## Experimental Results

The proposed Reinforcement Learning-based SDN load-balancing framework demonstrated:

- **Maximum Achieved Bandwidth:** **13.4 Gbps**
- Efficient traffic distribution across multiple available paths.
- Reduced congestion through adaptive routing.
- Improved bandwidth utilization.
- Lower network delay.
- Better utilization of available network resources.
- Continuous learning through Q-value updates based on network conditions.

---

## Project Workflow

1. Build a custom SDN topology using **Mininet**.
2. Deploy the **Ryu Controller** with **OpenFlow 1.3**.
3. Monitor network traffic and collect port statistics.
4. Construct Q-Learning states using network information.
5. Calculate rewards based on network performance.
6. Update the Q-table continuously.
7. Select optimal forwarding paths dynamically.
8. Install flow rules in OpenFlow switches.
9. Evaluate network performance under different traffic scenarios.
