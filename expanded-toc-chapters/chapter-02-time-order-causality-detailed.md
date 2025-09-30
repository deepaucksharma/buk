# Chapter 2: Time, Order, and Causality
## Exhaustive Detailed Table of Contents

### Chapter Blueprint
```
INVARIANT FOCUS
Primary: ORDER (happened-before relationships preserved)
Supporting: MONOTONICITY (time never goes backward), CAUSALITY (cause precedes effect)

UNCERTAINTY ADDRESSED
Cannot know: Global time instant, exact clock synchronization, message ordering
Cost to know: Network round-trips for clock sync, vector clock overhead
Acceptable doubt: Bounded clock skew, causal but not total order

EVIDENCE GENERATED
Type(s): Timestamps (logical/physical/hybrid), vector clocks, interval bounds
Scope: Per-object to global   Lifetime: Until clock overflow/reset
Binding: Node identity   Transitivity: Causal ordering transitive
Revocation: Clock reset requires new epoch

GUARANTEE VECTOR
Input G: ⟨Object, None, Fractured, EO, None, Unauth⟩
Output G: ⟨Global, Causal, SI, BS(δ), None, Auth(clock)⟩
Upgrades: Physical time + logical → Hybrid (HLC)
Downgrades: Total order → Causal → Concurrent

MODE MATRIX
Floor: Preserve causality (never violate happened-before)
Target: Bounded clock skew with causal consistency
Degraded: Larger uncertainty intervals, causal only
Recovery: Re-synchronize clocks, new epoch

DUALITIES
Local/Global: Local clocks vs global time
Precision/Availability: Tight bounds vs fault tolerance
Physical/Logical: Wall time vs causal time

IRREDUCIBLE SENTENCE
"Time in distributed systems is not a single timeline but a partial order of
causal relationships that we approximate with various clock mechanisms."
```

---

## Part 2.1: Physical Time - NTP and PTP

### 2.1.1 Millisecond vs Microsecond vs Nanosecond
#### 2.1.1.1 The Precision Hierarchy
- **Application Requirements by Precision**
  - Millisecond (10⁻³s): Web applications, logging
  - Microsecond (10⁻⁶s): Distributed databases, trading
  - Nanosecond (10⁻⁹s): High-frequency trading, physics
  - Evidence type: Clock resolution measurements
  - Invariant: MONOTONICITY at each precision level

#### 2.1.1.2 Hardware Clock Sources
- **Clock Types and Characteristics**
  - TSC (Time Stamp Counter): CPU cycles, nanosecond precision
  - HPET (High Precision Event Timer): 100ns resolution
  - RTC (Real Time Clock): Battery-backed, second precision
  - GPS/Atomic: External reference, microsecond accuracy
  - Evidence: Clock drift measurements
  - Context capsule: {invariant: MONOTONICITY, evidence: drift_rate, boundary: node}

#### 2.1.1.3 Clock Drift and Skew Reality
- **Measured Drift Rates**
  ```
  Quartz crystal: 10-50 ppm (1-5 seconds/day)
  TCXO: 1-5 ppm (0.1-0.5 seconds/day)
  OCXO: 0.01-0.1 ppm (1-10 ms/day)
  Atomic: 10⁻¹² ppm (1 ns/day)
  ```
  - Temperature effects: ±10 ppm per 10°C
  - Aging: 1-5 ppm per year
  - Evidence lifecycle: Calibration → Drift → Resync

### 2.1.2 Clock Skew in Distributed Systems
#### 2.1.2.1 Sources of Clock Skew
- **Network-Induced Skew**
  - Asymmetric network paths
  - Variable queueing delays
  - Interrupt coalescing effects
  - Evidence: RTT asymmetry measurements
  - Guarantee degradation: Fresh → BS(δ)

#### 2.1.2.2 The Berkeley Algorithm
- **Coordinator-Based Synchronization**
  ```python
  class BerkeleyAlgorithm:
      def synchronize_clocks(self, nodes):
          """
          Berkeley Algorithm for clock synchronization
          Evidence: Average of clock readings
          Guarantee: Bounded skew within group
          """
          # Coordinator polls all nodes
          time_readings = []
          for node in nodes:
              t_send = time.time()
              t_remote = node.get_time()
              t_recv = time.time()
              rtt = t_recv - t_send
              adjusted = t_remote + rtt/2
              time_readings.append(adjusted)

          # Calculate average (excluding outliers)
          avg_time = self.fault_tolerant_average(time_readings)

          # Send corrections
          for i, node in enumerate(nodes):
              correction = avg_time - time_readings[i]
              node.adjust_clock(correction)

          return avg_time
  ```
  - Evidence generated: Clock offset vectors
  - Mode: Target=coordinated, Degraded=local drift

#### 2.1.2.3 Cristian's Algorithm
- **Client-Server Synchronization**
  ```python
  class CristianAlgorithm:
      def sync_with_server(self, server):
          """
          Cristian's Algorithm for time sync
          Assumes symmetric network delay
          """
          t1 = time.time()  # Client send time
          server_time = server.get_time()
          t2 = time.time()  # Client receive time

          rtt = t2 - t1
          estimated_time = server_time + rtt/2

          # Uncertainty interval
          uncertainty = rtt/2

          # Evidence capsule
          return {
              'time': estimated_time,
              'uncertainty': uncertainty,
              'evidence': 'cristian',
              'boundary': rtt,
              'mode': 'target' if rtt < 10 else 'degraded'
          }
  ```

### 2.1.3 AWS Time Sync Service Architecture
#### 2.1.3.1 Hierarchical Time Distribution
- **Three-Tier Architecture**
  - Stratum 0: GPS/Atomic references
  - Stratum 1: Regional time servers
  - Stratum 2: Availability zone servers
  - Stratum 3: Instance clocks
  - Evidence: Stratum certificates
  - Guarantee: Monotonic within stratum

#### 2.1.3.2 Leap Smearing Implementation
- **Avoiding Leap Second Disruption**
  - 24-hour smear window
  - Linear adjustment: 11.6 ppm
  - No time discontinuity
  - Evidence: Smear epoch number
  - Invariant: MONOTONICITY preserved

#### 2.1.3.3 Production Metrics
- **Real-World Performance**
  - Clock accuracy: ±1ms from UTC
  - Sync frequency: Every 5 minutes
  - Network overhead: <1KB per sync
  - Failure rate: 0.001% sync failures
  - Mode matrix: Auto-degrade on sync failure

---

## Part 2.2: Logical Time - Lamport and Vector Clocks

### 2.2.1 Happened-Before Relationships
#### 2.2.1.1 Lamport's Partial Order
- **Formal Definition**
  ```
  a → b (a happened-before b) if:
  1. a and b on same process, a before b
  2. a is send(m), b is receive(m)
  3. Transitivity: a → b and b → c implies a → c
  ```
  - Evidence: Logical timestamps
  - Invariant: CAUSALITY preserved
  - Not total order: Concurrent events incomparable

#### 2.2.1.2 Logical Clock Rules
- **Lamport Clock Algorithm**
  ```python
  class LamportClock:
      def __init__(self):
          self.clock = 0

      def local_event(self):
          """Rule 1: Increment on local event"""
          self.clock += 1
          return self.clock

      def send_message(self):
          """Rule 2: Attach timestamp to message"""
          self.clock += 1
          return {'timestamp': self.clock}

      def receive_message(self, msg_timestamp):
          """Rule 3: Update to max(local, received) + 1"""
          self.clock = max(self.clock, msg_timestamp) + 1
          return self.clock
  ```
  - Evidence generated: Monotonic timestamps
  - Context capsule: {invariant: ORDER, evidence: timestamp}

#### 2.2.1.3 Limitations of Lamport Clocks
- **Cannot Detect Causality**
  - If L(a) < L(b), doesn't imply a → b
  - Concurrent events get arbitrary order
  - No way to detect independence
  - Evidence insufficient for causal queries
  - Need stronger mechanism: Vector clocks

### 2.2.2 Vector Clock Optimization Techniques
#### 2.2.2.1 Basic Vector Clock Algorithm
- **N-Dimensional Timestamps**
  ```python
  class VectorClock:
      def __init__(self, node_id, num_nodes):
          self.node_id = node_id
          self.clock = [0] * num_nodes

      def increment(self):
          """Increment own component"""
          self.clock[self.node_id] += 1
          return self.clock.copy()

      def update(self, received_clock):
          """Merge: take max of each component"""
          for i in range(len(self.clock)):
              self.clock[i] = max(self.clock[i], received_clock[i])
          self.clock[self.node_id] += 1

      def happens_before(self, other):
          """Check if self → other"""
          return all(s <= o for s, o in zip(self.clock, other)) and \
                 any(s < o for s, o in zip(self.clock, other))

      def concurrent(self, other):
          """Check if self || other"""
          return not self.happens_before(other) and \
                 not other.happens_before(self)
  ```
  - Evidence: Complete causal history
  - Guarantee: Detect all causal relationships

#### 2.2.2.2 Vector Clock Compression
- **Reducing O(n) Overhead**
  - **Pruning**: Remove entries for inactive nodes
  - **Compression**: Delta encoding for sparse updates
  - **Bounded**: Limit to k most recent writers
  - **Probabilistic**: Bloom filters for membership
  - Evidence trade-off: Precision vs space
  - Mode: Target=full vectors, Degraded=compressed

#### 2.2.2.3 Interval Tree Clocks (ITC)
- **Dynamic Node Participation**
  ```python
  class IntervalTreeClock:
      """
      ITC: Handles dynamic node join/leave
      Fork and join operations on ID space
      """
      def __init__(self):
          self.id = (0, 1)  # Interval [0, 1)
          self.event = self.seed()

      def fork(self):
          """Split ID space for new node"""
          left = (self.id[0], (self.id[0] + self.id[1])/2)
          right = ((self.id[0] + self.id[1])/2, self.id[1])
          return IntervalTreeClock(left), IntervalTreeClock(right)

      def join(self, other):
          """Merge ID spaces"""
          self.id = self.merge_intervals(self.id, other.id)
          self.event = self.merge_events(self.event, other.event)
  ```
  - Evidence: Causality without fixed node count
  - Scalability: No need to know all nodes

### 2.2.3 Implementation in Riak and Voldemort
#### 2.2.3.1 Dotted Version Vectors (DVV)
- **Riak's Causality Tracking**
  - Server-side version vectors
  - Client context for updates
  - Sibling detection and merge
  - Evidence: Version vector + actor ID
  - Guarantee: Never lose writes

#### 2.2.3.2 Voldemort's Vector Clock Implementation
- **Optimizations for Performance**
  - Bounded clock size (default: 10 nodes)
  - Timestamp pruning (>1 week old)
  - Read repair on divergence
  - Evidence lifecycle: Generate → Propagate → Prune
  - Mode: Degrade to last-write-wins if overflow

#### 2.2.3.3 Production Lessons
- **Real-World Trade-offs**
  - Vector size vs causality precision
  - Client clock management complexity
  - Sibling explosion under high concurrency
  - Evidence: Production metrics from LinkedIn
  - Cost: 10-50 bytes per version

---

## Part 2.3: Hybrid Logical Clocks (2014)

### 2.3.1 Best of Both Worlds Design
#### 2.3.1.1 The HLC Algorithm
- **Combining Physical and Logical Time**
  ```python
  class HybridLogicalClock:
      def __init__(self):
          self.physical_time = 0
          self.logical_time = 0

      def now(self):
          """Generate HLC timestamp"""
          pt = self.get_physical_time()

          if pt > self.physical_time:
              self.physical_time = pt
              self.logical_time = 0
          else:
              self.logical_time += 1

          return (self.physical_time, self.logical_time)

      def update(self, msg_pt, msg_lt):
          """Update on message receive"""
          pt = self.get_physical_time()

          if pt > max(self.physical_time, msg_pt):
              self.physical_time = pt
              self.logical_time = 0
          elif self.physical_time == msg_pt:
              self.logical_time = max(self.logical_time, msg_lt) + 1
          elif msg_pt > self.physical_time:
              self.physical_time = msg_pt
              self.logical_time = msg_lt + 1
          else:
              self.logical_time += 1

          return (self.physical_time, self.logical_time)
  ```
  - Evidence: 64-bit timestamp (48-bit physical, 16-bit logical)
  - Guarantee: Causal consistency + bounded divergence

#### 2.3.1.2 Bounded Clock Divergence Property
- **Key HLC Properties**
  - |HLC.pt - PT| ≤ ε (bounded from physical)
  - Captures happened-before like Lamport
  - Monotonic and causal
  - Evidence: Mathematical proof of bounds
  - **Correction**: Does not provide linearizability alone

#### 2.3.1.3 HLC vs NTP + Lamport
- **Advantages of HLC**
  - Single 64-bit timestamp
  - No separate logical clock needed
  - Close to wall time for debugging
  - Backwards compatible with NTP
  - Evidence: Same size as traditional timestamp

### 2.3.2 HLC Guarantees and Limitations
#### 2.3.2.1 What HLC Provides
- **Guaranteed Properties**
  - Causality preservation
  - Bounded divergence from physical time
  - Monotonicity per node
  - Total order (with node ID tiebreaker)
  - Evidence: Timestamp comparison sufficient

#### 2.3.2.2 What HLC Does NOT Provide
- **Limitations to Understand**
  - Not linearizable without additional mechanisms
  - Cannot detect all concurrent updates
  - Requires loosely synchronized clocks
  - Evidence: Need additional protocols for strong consistency
  - Context capsule must specify guarantee level

#### 2.3.2.3 When to Use HLC
- **Appropriate Use Cases**
  - Event ordering in logs
  - Causal consistency in databases
  - Distributed tracing timestamps
  - Conflict resolution in CRDTs
  - Mode: Use when causal sufficient

### 2.3.3 CockroachDB's Implementation
#### 2.3.3.1 HLC in Transaction Ordering
- **Transaction Timestamp Assignment**
  ```python
  class CockroachTransaction:
      def begin_transaction(self):
          """Assign transaction timestamp"""
          hlc_timestamp = self.hlc.now()

          # Uncertainty interval for linearizability
          max_offset = self.max_clock_offset  # e.g., 500ms
          uncertainty_interval = (
              hlc_timestamp,
              hlc_timestamp + max_offset
          )

          return {
              'timestamp': hlc_timestamp,
              'uncertainty': uncertainty_interval,
              'evidence': 'hlc',
              'mode': 'target'
          }
  ```
  - Evidence: HLC + uncertainty interval
  - Guarantee: Linearizability with uncertainty

#### 2.3.3.2 Uncertainty Intervals and Restarts
- **Handling Clock Uncertainty**
  - Read at timestamp T
  - Encounter value in (T, T+ε)
  - Must restart at higher timestamp
  - Evidence: Uncertainty interval overlap
  - Cost: Restart rate proportional to ε

#### 2.3.3.3 Production Metrics
- **CockroachDB in Practice**
  - Clock offset limit: 500ms default
  - HLC overhead: 8 bytes per row
  - Transaction restart rate: <0.1% typical
  - Evidence: Production telemetry
  - Mode degradation: Larger ε → more restarts

---

## Part 2.4: Google TrueTime (2012)

### 2.4.1 GPS and Atomic Clock Infrastructure
#### 2.4.1.1 Hardware Architecture
- **Redundant Time References**
  - GPS receivers: Multiple per datacenter
  - Atomic clocks: Rubidium/Cesium
  - Cross-checking: Detect faulty references
  - Evidence: Time master certificates
  - Invariant: Bounded uncertainty always

#### 2.4.1.2 Time Master Hierarchy
- **Distributed Time Service**
  ```
  GPS/Atomic → Time Masters → Time Slaves → Spanservers

  Synchronization intervals:
  - Masters: Every 30 seconds
  - Slaves: Every 30 seconds
  - Uncertainty: 1-7ms typical
  ```
  - Evidence: Marzullo's algorithm for agreement
  - Guarantee: ε bounded globally

#### 2.4.1.3 Failure Handling
- **Resilience Mechanisms**
  - Armageddon masters: Increase uncertainty
  - Local clock drift model
  - Graceful degradation
  - Evidence: Uncertainty interval growth
  - Mode: Target=1ms, Degraded=7ms, Recovery=resync

### 2.4.2 Uncertainty Intervals
#### 2.4.2.1 The TrueTime API
- **Simple but Powerful Interface**
  ```cpp
  class TrueTime {
    TTinterval now();  // Returns [earliest, latest]
  };

  struct TTinterval {
    Timestamp earliest;  // Guaranteed lower bound
    Timestamp latest;    // Guaranteed upper bound

    bool before(Timestamp t) {
      return latest < t;
    }

    bool after(Timestamp t) {
      return earliest > t;
    }
  };
  ```
  - Evidence: Interval containing true time
  - Guarantee: True time ∈ [earliest, latest]

#### 2.4.2.2 Uncertainty Bounds Calculation
- **Sources of Uncertainty**
  - Network delay variation: ±200μs
  - Clock drift since sync: 200ppm × 30s = 6ms
  - Syscall overhead: ±10μs
  - Total ε: 1-7ms typical
  - Evidence: Statistical bounds (6σ)
  - Context capsule includes ε

#### 2.4.2.3 Commit Wait Optimization
- **Reducing Wait Time**
  - Typical wait: ε (1-7ms)
  - Pipeline with replication
  - Overlap with log write
  - Evidence: Wait completion certificate
  - Cost: Latency for consistency

### 2.4.3 Spanner's Commit Wait Protocol
#### 2.4.3.1 The Commit Wait Algorithm
- **Ensuring External Consistency**
  ```python
  class SpannerCommitProtocol:
      def commit_transaction(self, tx):
          """
          Spanner's commit protocol with TrueTime
          """
          # Phase 1: Prepare
          prepare_ts = self.truetime.now().latest

          # Phase 2: Acquire locks
          locks = self.acquire_locks(tx.writes)

          # Phase 3: Pick commit timestamp
          commit_ts = max(
              prepare_ts,
              max(lock.timestamp for lock in locks)
          ) + 1

          # Phase 4: Wait until safe
          commit_wait = commit_ts - self.truetime.now().earliest
          if commit_wait > 0:
              time.sleep(commit_wait / 1000.0)  # Convert to seconds

          # Phase 5: Release locks and apply
          self.apply_writes(tx.writes, commit_ts)
          self.release_locks(locks)

          return {
              'commit_ts': commit_ts,
              'wait_time': commit_wait,
              'evidence': 'truetime_wait',
              'guarantee': 'external_consistency'
          }
  ```
  - Evidence: Commit timestamp + wait proof
  - Guarantee: External consistency (linearizability)

#### 2.4.3.2 Read-Only Transactions
- **Snapshot Reads Without Locks**
  - Pick read timestamp
  - Find safe snapshot
  - No commit wait needed
  - Evidence: Snapshot timestamp
  - Guarantee: Consistent snapshot

#### 2.4.3.3 Performance Impact
- **Production Measurements**
  - Commit wait: 1-7ms average
  - Read-only: No wait
  - Throughput: Millions QPS
  - Evidence: Google production metrics
  - Trade-off: Latency for consistency

---

## Part 2.5: Closed Timestamps and Consistency

### 2.5.1 Closed Timestamp Calculation
#### 2.5.1.1 The Correct Formula
- **Closed Timestamp Definition**
  ```python
  def calculate_closed_timestamp(nodes):
      """
      CT(t) = min(local_clock - max_offset, min(node_clocks))

      Corrected from incorrect formulas in literature
      """
      local_time = get_local_clock()
      max_offset = get_max_clock_offset()  # e.g., 500ms

      # Collect timestamps from all nodes
      node_timestamps = []
      for node in nodes:
          ts = node.get_latest_timestamp()
          node_timestamps.append(ts)

      # Closed timestamp is conservative minimum
      closed_ts = min(
          local_time - max_offset,
          min(node_timestamps)
      )

      return {
          'timestamp': closed_ts,
          'evidence': 'closed',
          'guarantee': 'no_future_writes',
          'boundary': 'range'
      }
  ```
  - Evidence: Minimum across nodes
  - Guarantee: No writes before CT

#### 2.5.1.2 Propagation Mechanisms
- **Broadcasting Closed Timestamps**
  - Piggyback on heartbeats
  - Dedicated control channel
  - Gossip protocol propagation
  - Evidence: Signed CT certificates
  - Latency: Propagation delay

#### 2.5.1.3 Advancement Strategies
- **Moving CT Forward**
  - Periodic advancement (e.g., 100ms)
  - On-demand for reads
  - Adaptive based on workload
  - Evidence: Advancement proof
  - Trade-off: Freshness vs overhead

### 2.5.2 Follower Reads Without Coordination
#### 2.5.2.1 The Follower Read Protocol
- **Reading from Replicas Safely**
  ```python
  class FollowerReadProtocol:
      def read_from_follower(self, key, required_freshness):
          """
          Read from follower without leader coordination
          """
          # Get follower's closed timestamp
          follower_ct = self.get_closed_timestamp()

          # Check freshness requirement
          if follower_ct >= required_freshness:
              # Safe to read
              value = self.local_read(key, follower_ct)
              return {
                  'value': value,
                  'timestamp': follower_ct,
                  'evidence': 'closed_timestamp',
                  'guarantee': 'read_committed'
              }
          else:
              # Must forward to leader or wait
              return self.forward_to_leader(key)
  ```
  - Evidence: CT ≥ read timestamp
  - Guarantee: Consistent reads

#### 2.5.2.2 Bounded Staleness Guarantees
- **Staleness Bounds with CT**
  - Maximum staleness = now - CT
  - Typical: 100-500ms behind leader
  - Configurable per workload
  - Evidence: Staleness measurement
  - Mode: Accept staleness for availability

#### 2.5.2.3 Performance Benefits
- **Avoiding Leader Bottleneck**
  - Read scaling: Linear with replicas
  - Leader CPU reduction: 50-90%
  - Network traffic: Local reads
  - Evidence: Production metrics
  - Cost: Bounded staleness accepted

### 2.5.3 Production Systems: YugabyteDB, CockroachDB
#### 2.5.3.1 YugabyteDB Implementation
- **Hybrid Logical Clocks + CT**
  - HLC for transaction ordering
  - Closed timestamps for follower reads
  - Safe timestamp advancement
  - Evidence: HLC + CT certificates
  - Guarantee: Causal consistency minimum

#### 2.5.3.2 CockroachDB's Approach
- **Closed Timestamps with Ranges**
  - Per-range closed timestamps
  - Side transport for propagation
  - Lease holder coordination
  - Evidence: Range CT maps
  - Mode: Per-range granularity

#### 2.5.3.3 Comparative Analysis
- **Different Design Choices**
  | System | CT Granularity | Advancement | Staleness |
  |--------|---------------|-------------|-----------|
  | YugabyteDB | Table | 100ms | 100-500ms |
  | CockroachDB | Range | Adaptive | 50-250ms |
  | TiDB | Region | 100ms | 100-300ms |
  - Evidence types vary
  - Trade-offs: Granularity vs overhead

---

## Part 2.6: Advanced Time Mechanisms

### 2.6.1 Atomic Broadcast and Time
#### 2.6.1.1 Total Order as Time
- **Broadcast Order Defines Time**
  ```python
  class AtomicBroadcast:
      def __init__(self):
          self.sequence = 0
          self.delivered = set()

      def broadcast(self, message):
          """
          Total order broadcast
          Sequence number acts as logical time
          """
          self.sequence += 1
          ordered_msg = {
              'content': message,
              'sequence': self.sequence,
              'sender': self.node_id
          }

          # Consensus on delivery order
          self.consensus.propose(ordered_msg)

          return {
              'timestamp': self.sequence,
              'evidence': 'total_order',
              'guarantee': 'atomic_delivery'
          }
  ```
  - Evidence: Sequence numbers
  - Invariant: Total order preserved

#### 2.6.1.2 Virtual Synchrony
- **Group Communication Primitives**
  - View changes: Membership epochs
  - Message ordering within views
  - State transfer between views
  - Evidence: View certificates
  - Guarantee: Same view → same messages

### 2.6.2 Time in Blockchain Systems
#### 2.6.2.1 Block Time as Logical Clock
- **Blockchain Temporal Model**
  - Block height = logical time
  - Block timestamp = approximate physical
  - Median time past (MTP) rule
  - Evidence: Block headers
  - Invariant: Monotonic block time

#### 2.6.2.2 Proof of Work and Time
- **Time via Computational Work**
  - Difficulty adjustment
  - Expected block interval
  - Statistical time bounds
  - Evidence: Proof of work
  - Trade-off: Security vs precision

### 2.6.3 Relativistic Time Models
#### 2.6.3.1 Light Cone Causality
- **Space-Time Inspired Models**
  - Past light cone: Can affect
  - Future light cone: Can be affected
  - Elsewhere: Concurrent
  - Evidence: Space-time coordinates
  - Application: Wide-area systems

---

## Part 2.7: Synthesis and Mental Models

### 2.7.1 The Invariant Hierarchy for Time
#### 2.7.1.1 Fundamental Invariants
- **ORDER: Happened-before relationships must be preserved**
  - Threat model: Network delay, message reordering, concurrent operations
  - Protection boundary: Per-node for logical clocks, global for physical synchronization
  - Evidence needed: Timestamps (logical, physical, or hybrid), vector clocks
  - Degradation semantics: Total order → Causal order → Concurrent (no order)
  - Repair pattern: Clock synchronization, causal barrier enforcement, timestamp adjustment

- **MONOTONICITY: Time never goes backward**
  - Threat model: Clock skew, NTP step adjustments, leap seconds, clock resets
  - Protection boundary: Per-node clock, per-process timestamp counter
  - Evidence needed: Monotonic clock readings, leap smearing certificates
  - Degradation semantics: Strict monotonicity → Bounded jumps → Best-effort
  - Repair pattern: Clock discipline algorithms, smearing, epoch increments

#### 2.7.1.2 Derived Invariants (Built on Fundamentals)
- **CAUSALITY: Cause must precede effect**
  - Builds on: ORDER (happened-before) + MONOTONICITY
  - Evidence: Vector clocks capture full causal history
  - Protection: Logical clocks enforce causal order
  - Composition: Causal + Physical time = Hybrid Logical Clocks

- **BOUNDED DIVERGENCE: Clock drift limited by contract δ**
  - Builds on: MONOTONICITY + synchronization
  - Evidence: NTP sync status, clock offset measurements, TrueTime intervals
  - Protection: Periodic synchronization, drift monitoring
  - Composition: Physical bounds + Logical counters = HLC bounded divergence

#### 2.7.1.3 Composite Invariants (User-Visible Properties)
- **FRESHNESS: Order + recency bound**
  - Components: ORDER + BOUNDED DIVERGENCE + timestamp verification
  - Evidence: Closed timestamps, lease certificates with expiry
  - User promise: "Read is at most δ seconds stale"
  - Mode degradation: Fresh(φ) → BS(δ) → EO (eventual only)

- **EXTERNAL CONSISTENCY: Real-time order preserved**
  - Components: ORDER + Physical time + Uncertainty elimination
  - Evidence: TrueTime commit wait, globally synchronized timestamps
  - User promise: "If T1 commits before T2 starts, T1's timestamp < T2's"
  - Implementation: Spanner's commit wait protocol

### 2.7.2 Evidence Lifecycle for Time
#### 2.7.2.1 Generation Phase
- **Creating Temporal Evidence**
  - Physical clock readings: Hardware TSC, HPET, RTC, GPS/Atomic
  - Logical timestamps: Lamport counter increments, vector clock updates
  - Hybrid timestamps: HLC (physical, logical) tuple generation
  - Uncertainty intervals: TrueTime [earliest, latest] calculation
  - Closed timestamps: Conservative minimum across replicas
  - **Lifecycle state**: Generated → Must be validated before use

- **Generation Properties**
  - Scope: Per-node (Lamport), Per-process (vector clock component), Global (TrueTime)
  - Lifetime: Until clock overflow, epoch change, or synchronization reset
  - Binding: Node identity, process ID, datacenter region
  - Cost: TSC read (~10ns), NTP sync (~1-10ms), Consensus (~10-100ms)

#### 2.7.2.2 Validation Phase
- **Checking Temporal Evidence**
  - Monotonicity verification: timestamp_new > timestamp_old
  - Causality checking: Vector clock comparison for happened-before
  - Uncertainty containment: TrueTime interval overlap detection
  - Synchronization status: NTP stratum level, sync age, offset magnitude
  - Certificate validation: Closed timestamp signatures, lease expiry checks
  - **Lifecycle state**: Validated → Active (ready for use)

- **Validation Failures and Downgrades**
  - Clock skew too large → Refuse operation or force resync
  - Uncertainty interval too wide → Wait or degrade to eventual consistency
  - Causality violation detected → Restart transaction (CockroachDB uncertainty)
  - Certificate expired → Revoke evidence, trigger renewal

#### 2.7.2.3 Active Phase
- **Using Temporal Evidence**
  - Transaction timestamp assignment: Begin, commit timestamps with guarantees
  - Ordering decisions: Log entry ordering, event stream sequencing
  - Staleness checks: Comparing read timestamp with closed timestamp
  - Conflict detection: Concurrent writes via vector clock comparison
  - Cache freshness: TTL-based expiration, timestamp-based invalidation
  - **Lifecycle state**: Active → Evidence in use, must track expiry

#### 2.7.2.4 Expiration Phase
- **Temporal Evidence Lifetime Management**
  - Clock sync expiry: NTP sync intervals (every 30-300s), increasing uncertainty
  - Closed timestamp advancement: Periodic updates (100ms-1s), old CT becomes stale
  - Lease expiration: Leader lease timeout, must renew or step down
  - Certificate timeout: Signature validity period, must re-sign
  - Log truncation point: GC old timestamps beyond retention window
  - **Lifecycle state**: Expiring → Must renew or downgrade

- **Expiration Handling**
  - Graceful degradation: Fresh(φ) → BS(δ) with larger δ → EO
  - Mode transitions: Target → Degraded when evidence expires
  - Renewal protocols: NTP resync, lease renewal, CT propagation
  - Evidence rebinding: New epoch, new configuration, new certificates

#### 2.7.2.5 Renewal/Revocation Phase
- **Re-establishing or Invalidating Evidence**
  - NTP resynchronization: Re-establish clock offset bounds
  - HLC clock update: Merge with received timestamps, increment logical
  - Closed timestamp advancement: Coordinate new minimum safe point
  - Lease renewal: Leader re-acquires lease with new expiry
  - Epoch increment: Clock reset, configuration change forces new epoch
  - **Lifecycle state**: Renewed → Back to Generated, or Revoked → Invalid forever

- **Revocation Triggers**
  - Clock reset detected: Monotonicity violation, must start new epoch
  - Split brain: Multiple leaders detected, all leases revoked
  - Configuration change: Membership change invalidates old certificates
  - Manual intervention: Operator forces clock resync or lease revocation

### 2.7.3 The Three-Layer Mental Model for Time
#### 2.7.3.1 Layer 1: Physical Reality (Eternal Truths)
- **What Cannot Be Changed**
  - No global simultaneity exists (relativity)
  - Clocks drift and skew continuously
  - Communication takes time proportional to distance
  - Causality requires ordering mechanism
  - Evidence has cost: generation, propagation, verification
  - Synchronization is probabilistic, never perfect

#### 2.7.3.2 Layer 2: Design Patterns (Navigation Strategies)
- **How We Navigate Reality**
  - Synchronize clocks periodically (NTP, PTP)
  - Use logical time for causality (Lamport, Vector)
  - Combine physical and logical (HLC)
  - Bound uncertainty explicitly (TrueTime intervals)
  - Generate verifiable temporal evidence
  - Degrade predictably when evidence expires

#### 2.7.3.3 Layer 3: Implementation Choices (Tactics)
- **What We Build**
  - NTP/PTP synchronization protocols
  - Lamport/Vector clock implementations
  - Hybrid logical clocks (HLC)
  - Closed timestamp protocols
  - Uncertainty interval APIs (TrueTime)
  - Commit wait mechanisms (Spanner)

### 2.7.2 Evidence Lifecycle for Time
#### 2.7.2.1 Generation
- **Creating Temporal Evidence**
  - Clock readings
  - Timestamps (logical/physical)
  - Uncertainty bounds
  - Closed timestamp certificates
  - Lifecycle: Read → Bind → Propagate

#### 2.7.2.2 Validation
- **Checking Temporal Evidence**
  - Monotonicity checks
  - Causality verification
  - Uncertainty containment
  - Certificate validation
  - Mode: Reject if invalid

#### 2.7.2.3 Expiration
- **Temporal Evidence Lifetime**
  - Clock sync intervals
  - Closed timestamp advancement
  - Lease expiration
  - Certificate timeout
  - Recovery: Re-generate evidence

### 2.7.3 Guarantee Composition with Time
#### 2.7.3.1 Temporal Guarantee Vectors
- **Time Components in Guarantees**
  ```
  G_time = ⟨Scope, Order, Visibility, Recency, Clock_Type⟩

  Examples:
  - Lamport: ⟨Global, Causal, -, -, Logical⟩
  - HLC: ⟨Global, Causal, -, BS(ε), Hybrid⟩
  - TrueTime: ⟨Global, Total, -, Fresh(ε), Physical⟩
  ```
  - Composition: Take weakest
  - Upgrade: Add stronger clock

#### 2.7.3.2 Boundary Crossings
- **Time Evidence at Boundaries**
  - Clock domain transitions
  - Timezone conversions
  - Epoch changes
  - Evidence transformation
  - Context capsule carries type

### 2.7.4 Fifteen Key Insights (Mental Model Builders)

#### 2.7.4.1 Foundational Insights (1-5)
1. **"Now" is a Local Illusion**
   - No global simultaneity exists; each node has its own timeline
   - Implication: Coordination requires explicit communication, not assumed synchrony
   - Evidence: Special relativity, network delays, clock skew measurements
   - Transfer: Applies to any distributed system, including human organizations

2. **Clocks Measure Intervals, Not Instants**
   - Physical clocks drift continuously; accuracy degrades over time
   - Implication: Must bound uncertainty and resynchronize periodically
   - Evidence: ppm drift rates, NTP offset measurements, temperature effects
   - Transfer: Any measurement instrument needs calibration

3. **Causality Is More Fundamental Than Time**
   - Happened-before relationships matter more than wall-clock timestamps
   - Implication: Logical clocks sufficient for many consistency properties
   - Evidence: Lamport's happened-before, vector clocks capture all causal dependencies
   - Transfer: Event ordering in logs, business process workflows, audit trails

4. **Coordination Budget: Time Synchronization Has Cost**
   - Network RTT for sync, CPU for clock reads, uncertainty from delay variation
   - Implication: Choose precision based on actual requirements
   - Evidence: NTP sync = 1-10ms RTT, TrueTime = specialized hardware
   - Transfer: All distributed coordination has measurable cost

5. **Evidence Expiration Drives Mode Transitions**
   - Clock sync ages, leases expire, certificates timeout
   - Implication: Systems must degrade gracefully when evidence becomes stale
   - Evidence: NTP sync intervals, lease timeouts, uncertainty growth over time
   - Transfer: All credentials and certificates have lifecycle management

#### 2.7.4.2 Mechanism Insights (6-10)
6. **Logical Clocks: Causality Without Synchronization**
   - Lamport clocks capture partial order; vector clocks capture full causal history
   - Implication: Can order events without physical clock synchronization
   - Evidence: Lamport timestamp guarantees a→b ⇒ L(a)<L(b)
   - Limitation: Cannot detect concurrency with Lamport; need vector clocks
   - Transfer: Version vectors in distributed databases, causal consistency

7. **Hybrid Clocks: Best of Both Worlds**
   - HLC combines physical time (for humans) with logical counters (for causality)
   - Implication: Single 64-bit timestamp provides both properties
   - Evidence: Bounded divergence from physical time, captures happened-before
   - Cost: Requires loosely synchronized clocks (NTP-class)
   - Transfer: Event timestamps in distributed tracing, transaction ordering

8. **Uncertainty Intervals: Making Ignorance Explicit**
   - TrueTime returns [earliest, latest] instead of single timestamp
   - Implication: Honest about what we don't know; enables wait to eliminate uncertainty
   - Evidence: True time ∈ interval with high confidence (6σ)
   - Cost: Commit wait = ε (1-7ms typical), latency for consistency
   - Transfer: Confidence intervals in any measurement system

9. **Closed Timestamps: Safe Points for Reading**
   - CT(t) = point before which no new writes will occur
   - Implication: Replicas can serve consistent reads without leader coordination
   - Evidence: Minimum timestamp across all nodes, conservative by design
   - Cost: Bounded staleness (reads lag writes by CT advancement period)
   - Transfer: Checkpoints, snapshots, consistent cuts in distributed systems

10. **Commit Wait: Trading Latency for Consistency**
    - Spanner waits until commit_ts < TrueTime().earliest to ensure external consistency
    - Implication: Can achieve linearizability across datacenters at cost of latency
    - Evidence: If T1 commits before T2 starts, T1.ts < T2.ts guaranteed
    - Cost: Median 1-7ms wait, proportional to clock uncertainty ε
    - Transfer: Any protocol that waits for uncertainty to resolve

#### 2.7.4.3 Composition and Operational Insights (11-15)
11. **Time Evidence Is Non-Transitive**
    - Timestamp from Node A + Timestamp from Node B ≠ Global ordering
    - Implication: Must re-verify or rebind evidence at boundaries
    - Evidence: Clock skew between independent NTP-synced systems
    - Solution: Use single time authority (TrueTime) or logical clocks (HLC)
    - Transfer: Trust boundaries in security systems, certificate chains

12. **Monotonicity Violations Break Everything**
    - Time going backward violates causality, corrupts ordering, breaks caches
    - Implication: Must detect clock resets and start new epoch
    - Evidence: NTP step adjustments, VM migrations, manual clock changes
    - Protection: Monotonic clock APIs, leap smearing, epoch numbers
    - Transfer: Sequence numbers, generation numbers, configuration versions

13. **Different Clocks Compose Via Weakest Guarantee**
    - Lamport + Vector = Lamport (weaker), HLC + TrueTime = HLC (weaker)
    - Implication: End-to-end guarantee limited by least precise component
    - Evidence: Guarantee vector composition rules (meet operation)
    - Solution: Upgrade evidence at boundaries or accept degradation
    - Transfer: Security levels, consistency levels, any quality-of-service composition

14. **Timestamp Skew Causes Resurrection Bugs**
    - Fast clock can make old updates appear newer than recent deletes
    - Implication: LWW (last-writer-wins) dangerous without synchronized clocks
    - Evidence: Production bugs in Dynamo-style systems, deleted items reappearing
    - Solution: Tombstones with TTL, vector clocks, or synchronized time
    - Transfer: Cache invalidation, distributed deletion, garbage collection

15. **Geo-Replication: Physics Dominates Design**
    - Cross-region latency (50-250ms) dwarfs local coordination (1-10ms)
    - Implication: Must choose between strong consistency (slow) or eventual (fast)
    - Evidence: Speed of light = 200ms round-trip for half-planet
    - Strategies: Async replication, causal consistency, regional strong consistency
    - Transfer: Any wide-area distributed system, global business processes

### 2.7.5 Ten Essential Diagrams (Visual Grammar)

#### 2.7.5.1 Core Concept Diagrams (1-5)

**Diagram 1: The Invariant Guardian - Time Edition**
```
         Network Delay ⚡
         Clock Skew ⚡
         Message Reorder ⚡
                ↓
         [ORDER Invariant] 🛡️
                ↑
    ┌───────────┴───────────┐
    │                       │
[Logical Clocks]      [Physical Sync]
    │                       │
    ↓                       ↓
📜 Timestamps          📜 Bounded Uncertainty
```
- Colors: Threats (red), Invariant (blue), Mechanisms (green), Evidence (yellow)
- Shows: How different mechanisms protect ORDER invariant
- Transfer: Same pattern for any invariant protection

**Diagram 2: The Evidence Lifecycle - Temporal Proofs**
```
Generate ──→ Validate ──→ Active ──→ Expiring ──→ Expired
   ($)         (✓)          (!)        (⏰)          (✗)
   │           │            │           │            │
 NTP Sync   Check Skew   Use for    Lease      Revoke &
 Lamport++  Monotonic    Ordering   Expires    Resync
 HLC.now()  Causal Check Timestamp  CT Stale   New Epoch
```
- Timeline: Left to right lifecycle progression
- Annotations: Cost, validation, active use, warnings, termination
- Transfer: All evidence follows similar lifecycle

**Diagram 3: Clock Type Comparison Matrix**
```
                Lamport    Vector     HLC        TrueTime
                ────────   ────────   ────────   ────────
Causality       Partial    Full       Full       Implicit
Physical Time   No         No         Yes        Yes
Detect ||       No         Yes        Yes        N/A
Uncertainty     None       None       Bounded    Explicit
Size            8 bytes    8N bytes   8 bytes    16 bytes
Sync Required   None       None       Loose      Tight
Use Case        Order      Conflicts  General    Strong
                ────────   ────────   ────────   ────────
```
- Shows: Trade-offs between clock mechanisms
- Helps: Choose appropriate clock for requirements
- Transfer: Design decision matrix for any component choice

**Diagram 4: The Composition Ladder - Time Guarantees**
```
    Strong (External Consistency)
      ├─── TrueTime Commit Wait ───┐
      │    ε=1-7ms, Linearizable   │
      │                            ↑ Upgrade: Add TrueTime
                                   │
    Bounded (Causal + δ)           │
      ├─── HLC + Closed Timestamps │
      │    δ=100-500ms, RYW        │
      │                            ↑ Upgrade: Add CT
                                   │
    Weak (Causal Only)             │
      ├─── Lamport/Vector Clocks   │
      │    No staleness bound      │
      │                            ↓ Downgrade: Remove sync
                                   │
    Eventual (No Order)            │
      └─── Wall Clock Timestamps ──┘
           No guarantees
```
- Vertical: Increasing guarantee strength
- Horizontal: Evidence required for each level
- Arrows: Upgrade/downgrade paths with evidence changes

**Diagram 5: Mode Compass - Time System States**
```
              Target
           (Bounded Skew)
               ↑
               │ Clock Sync OK
               │ Lease Valid
               │
 Recovery ←────┼────→ Degraded
(New Epoch)    │      (Larger ε)
               │
               │ Evidence Expired
               │ Sync Failed
               ↓
             Floor
        (Causality Only)
```
- Center: Current mode with entry/exit conditions
- Transitions: Evidence-driven (not time-based)
- Floor: Minimum viable correctness (never violate causality)
- Transfer: Mode matrix for any system component

#### 2.7.5.2 Mechanism Diagrams (6-10)

**Diagram 6: NTP Synchronization Flow**
```
Client                               Server
  │                                    │
  │──────── Request (t1) ─────────────→│
  │                                    │ t2 (receive)
  │                                    │ t3 (transmit)
  │←─────── Response (t2,t3) ──────────│
  │ t4 (receive)                       │
  │                                    │
  │ Calculate:                         │
  │ offset = ((t2-t1) + (t3-t4))/2    │
  │ delay = (t4-t1) - (t3-t2)         │
  │ uncertainty = delay/2              │
  └────────────────────────────────────┘
```
- Shows: RTT-based clock synchronization protocol
- Evidence: t1, t2, t3, t4 timestamps, offset calculation
- Limitation: Assumes symmetric network delay

**Diagram 7: Vector Clock Causality Detection**
```
Node A: [1,0,0]    Node B: [0,1,0]    Node C: [0,0,1]
    │                  │                  │
    │ Event a          │                  │
    │ VA=[2,0,0]       │                  │
    │                  │                  │
    │─── msg(VA) ─────→│                  │
    │                  │ Event b          │
    │                  │ VB=[2,2,0]       │
    │                  │                  │
    │                  │─── msg(VB) ─────→│
    │                  │                  │ Event c
    │                  │                  │ VC=[2,2,1]

    Compare VA=[2,0,0] and VC=[2,2,1]:
    - VA ≤ VC component-wise → a → c (happened-before)

    Compare VB=[2,2,0] and VC=[2,2,1]:
    - VB ≤ VC component-wise → b → c (happened-before)
```
- Shows: Full causal history capture with vector clocks
- Demonstrates: Transitivity of happened-before
- Transfer: Dependency tracking in any distributed system

**Diagram 8: HLC Update Rules**
```
Local Event:
─────────────
pt = physical_time()
if pt > hlc.pt:
    hlc.pt = pt, hlc.l = 0
else:
    hlc.l++
─────────────

Message Receive (msg.pt, msg.l):
─────────────────────────────────
pt = physical_time()
hlc.pt = max(pt, hlc.pt, msg.pt)

if hlc.pt == pt > msg.pt:
    hlc.l = 0
elif hlc.pt == msg.pt:
    hlc.l = max(hlc.l, msg.l) + 1
elif hlc.pt == hlc.pt_old:
    hlc.l++
─────────────────────────────────

Property: |hlc.pt - physical_time| ≤ ε
```
- Shows: State machine for HLC updates
- Guarantees: Causality + bounded divergence
- Complexity: Simpler than vector clocks, better than Lamport

**Diagram 9: TrueTime Commit Wait**
```
Timeline:
─────────────────────────────────────────────→
         t_start             t_commit  t_wait_done
            │                    │         │
            │                    │         │
            ▼                    ▼         ▼
Client:  [─────── Transaction ───────][Wait]
                                │      │
                                │      │
TrueTime: [earliest₁  latest₁] │      [earliest₂  latest₂]
            ▲                   │        ▲
            │                   │        │
            t_start            commit_ts│
                                         │
                                    Wait until:
                                    commit_ts < earliest₂

Guarantee: If T1 finishes wait before T2 starts,
           T1.commit_ts < T2.commit_ts
```
- Shows: How commit wait ensures external consistency
- Evidence: TrueTime intervals + wait completion
- Cost: Latency = ε (uncertainty bound)

**Diagram 10: Closed Timestamp Protocol**
```
Replicas:  R1        R2        R3      Leader
Time:      ↓         ↓         ↓         ↓
─────────────────────────────────────────────
           t=10      t=10      t=10      t=10
           write@11  write@12  write@11  write@13

           │         │         │         │
           │←──────── CT Request ────────│
           │         │         │         │
           │         │         │         │ Collect:
           │─────── max_ts=11 ────────→│ R1: 11
           │         │─── 12 ──────────→│ R2: 12
           │         │         │─── 11 ─→│ R3: 11
           │         │         │         │
           │         │         │         │ CT = min(11,12,11)
           │         │         │         │    = 11
           │         │         │         │
           │←──────── CT=11 Broadcast ───│
           │         │         │         │
           │         │         │         │
       [Safe to read @t≤11 without leader]

Property: No writes will occur at timestamp ≤ CT
```
- Shows: How replicas determine safe read point
- Evidence: Conservative minimum timestamp
- Enables: Follower reads without leader coordination

### 2.7.6 Mode Matrix for Time Systems

```
┌─────────────┬──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Mode        │ Floor            │ Target           │ Degraded         │ Recovery         │
├─────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Preserved   │ CAUSALITY        │ ORDER            │ ORDER            │ CAUSALITY        │
│ Invariants  │ (happened-before)│ MONOTONICITY     │ MONOTONICITY     │ (partial)        │
│             │                  │ BOUNDED          │ BOUNDED          │                  │
│             │                  │ DIVERGENCE       │ DIVERGENCE       │                  │
│             │                  │                  │ (relaxed δ)      │                  │
├─────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Evidence    │ Logical          │ HLC timestamps   │ Stale sync       │ Epoch markers    │
│ Accepted    │ timestamps       │ Closed           │ Large ε          │ New leader       │
│             │ Vector clocks    │ timestamps       │ Expired leases   │ certificates     │
│             │                  │ Lease            │ Old CT           │ Resync in        │
│             │                  │ certificates     │                  │ progress         │
├─────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Operations  │ Causal reads     │ Fresh reads      │ Stale reads      │ Read-only        │
│ Allowed     │ Causal writes    │ Linearizable     │ Eventual writes  │ Recovery         │
│             │ (no ordering)    │ writes           │ Bounded          │ operations       │
│             │                  │ Follower reads   │ staleness        │ Rebuild state    │
│             │                  │ (with CT)        │ accepted         │                  │
├─────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Guarantee   │ G = ⟨Global,     │ G = ⟨Global,     │ G = ⟨Global,     │ G = ⟨Object,     │
│ Vector      │ Causal, SI,      │ Total, SI,       │ Total, SI,       │ Causal, RA,      │
│             │ EO, None,        │ Fresh(φ),        │ BS(δ'),          │ BS(∞), None,     │
│             │ Auth(node)⟩      │ None,            │ None,            │ Auth(epoch)⟩     │
│             │                  │ Auth(clock)⟩     │ Auth(clock)⟩     │                  │
├─────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Entry       │ All evidence     │ Clock synced     │ Clock sync age   │ Clock reset      │
│ Triggers    │ expired/invalid  │ NTP offset < ε   │ > threshold      │ detected         │
│             │ Bootstrap state  │ Lease valid      │ Lease expired    │ Leader election  │
│             │ New cluster      │ CT advancing     │ ε > threshold    │ Split brain      │
│             │                  │                  │ CT stale         │ Config change    │
├─────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Exit        │ Evidence         │ (stable state)   │ Sync restored    │ New epoch        │
│ Triggers    │ generated        │ Or: sync fails → │ Lease renewed    │ established      │
│             │ → Target         │ Degraded         │ ε reduced        │ Sync achieved    │
│             │                  │ Or: evidence     │ → Target         │ → Target         │
│             │                  │ expires →        │                  │                  │
│             │                  │ Degraded/Floor   │                  │                  │
├─────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ User-       │ "System          │ "Reads are       │ "Reads may be    │ "System          │
│ Visible     │ operational,     │ fresh (≤δms      │ stale up to      │ recovering,      │
│ Contract    │ causality        │ stale), writes   │ δ'ms; writes     │ read-only mode"  │
│             │ preserved,       │ durable and      │ eventually       │                  │
│             │ no freshness     │ ordered"         │ consistent"      │                  │
│             │ guarantees"      │                  │                  │                  │
├─────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Example     │ New cluster      │ Normal ops:      │ NTP server       │ Clock jumped     │
│ Scenarios   │ startup with     │ NTP synced,      │ unreachable,     │ backward, start  │
│             │ logical clocks   │ δ=100ms,         │ δ grows to       │ new epoch,       │
│             │ only             │ reads from CT    │ 500ms, degrade   │ re-sync clocks   │
│             │                  │                  │ to async         │                  │
├─────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Monitoring  │ Causal order     │ Clock offset     │ Staleness        │ Epoch number     │
│ Metrics     │ violations       │ (<10ms)          │ metric (δ')      │ Sync progress    │
│             │ Logical clock    │ Sync age         │ Operation        │ State transfer   │
│             │ progression      │ (<60s)           │ timeouts         │ completion       │
│             │                  │ CT lag (<200ms)  │ Degraded mode    │                  │
│             │                  │ Lease validity   │ duration         │                  │
└─────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

**Cross-Service Mode Composition Rules:**
- Upstream Target + Downstream Degraded = Downstream Degraded (downstream governs)
- Upstream Floor + Downstream Target = Floor (weakest wins)
- Mode transitions are evidence-triggered, not time-based
- Context capsule must include current mode and evidence state

### 2.7.7 The Learning Spiral for Time

#### 2.7.7.1 Pass 1: Intuition (Felt Need)
- **Story: The Distributed Log That Couldn't Agree**
  - Two nodes logging events with timestamps from system clocks
  - Events appear out of order: "User logged out" before "User logged in"
  - Investigation reveals clock skew: Node A's clock 5 seconds ahead
  - **Felt need**: Need reliable ordering mechanism despite clock differences
  - **Simple fix**: Use sequence numbers instead of timestamps
  - **Invariant at risk**: ORDER (happened-before relationships)
  - **Evidence needed**: Something that preserves causality without synchronization

- **Core Questions Emerge**
  - Why can't we just use wall-clock timestamps?
  - How much clock skew is typical? (Answer: 10-50ms without sync, unbounded without)
  - What breaks when time goes backward? (Answer: caches, ordering, monotonic assumptions)
  - Can we order events without synchronized clocks? (Answer: Yes, logical clocks!)

#### 2.7.7.2 Pass 2: Understanding (Limits and Trade-offs)
- **Why Simple Approaches Fail at Scale**
  - Single-node sequence numbers: Doesn't work across multiple nodes
  - NTP-synced wall clocks: 1-10ms uncertainty, can still violate causality
  - Logical clocks alone: Can't answer "how long ago" questions
  - **Physical reality**: No global "now" exists; clocks drift continuously

- **Evidence-Based Solutions**
  - **Lamport clocks**: Capture partial order with 8-byte counter
    - Evidence: timestamp guarantees a→b ⇒ L(a)<L(b)
    - Limitation: Cannot detect concurrent events
    - Cost: Counter increment per event

  - **Vector clocks**: Capture full causal history with N timestamps
    - Evidence: Can detect all causal and concurrent relationships
    - Limitation: O(N) space per timestamp, grows with nodes
    - Cost: 8N bytes per timestamp, N updates per event

  - **Hybrid Logical Clocks**: Combine physical + logical in 8 bytes
    - Evidence: Bounded divergence |HLC.pt - physical_time| ≤ ε
    - Benefit: Single timestamp provides causality + approximate wall time
    - Cost: Requires loose clock synchronization (NTP-class)

  - **TrueTime**: Explicit uncertainty intervals with specialized hardware
    - Evidence: [earliest, latest] bounds with 6σ confidence
    - Benefit: Can achieve external consistency via commit wait
    - Cost: GPS/atomic clocks, ε=1-7ms commit wait latency

- **Trade-offs Clarified**
  ```
  Causality Precision    ←→    Space Overhead
  (Vector > HLC > Lamport)     (Vector: 8N, HLC: 8, Lamport: 8)

  Freshness Guarantees   ←→    Synchronization Cost
  (TrueTime > HLC > Logical)   (Hardware, NTP, None)

  Strong Consistency     ←→    Latency
  (Commit wait: +1-7ms)        (Eventual: no wait)
  ```

#### 2.7.7.3 Pass 3: Mastery (Composition and Operations)
- **How It Composes: End-to-End Temporal Guarantees**

  **Scenario: Multi-Region Distributed Database**
  ```
  Client → LB → Region A → Region B → Region C
           │      │          │          │
           │    [HLC]      [HLC]      [HLC]
           │      │          │          │
           └──── Compose via Context Capsule:
                 {
                   invariant: "Read-Your-Writes",
                   evidence: hlc_timestamp + session_id,
                   boundary: region_scope,
                   mode: target,
                   fallback: forward_to_leader
                 }
  ```

  - **Boundary 1: Client → Region A**
    - Input: No temporal guarantee
    - Region A assigns: HLC timestamp T_A, session token
    - Output: G = ⟨Global, Causal, SI, BS(100ms), None, Auth(session)⟩

  - **Boundary 2: Region A → Region B (async replication)**
    - Causal metadata propagated with writes
    - Region B: Buffers writes until dependencies satisfied
    - Guarantee maintains: Causal order preserved, BS relaxes to 200ms

  - **Boundary 3: Client reads from Region C**
    - Presents session token with write_set = {T_A}
    - Region C checks: Has T_A been applied? If not, wait or forward
    - Guarantee maintains: Read-Your-Writes via session evidence

  - **Composition rule**: Final guarantee = meet(all_boundaries)
    - G_final = ⟨Global, Causal, SI, BS(200ms), None, Auth(session)⟩
    - Weakest component (BS(200ms)) governs end-to-end

- **Mode Matrix Under Stress**

  **Scenario: NTP Server Failure**
  ```
  Time:  t0            t1            t2            t3
  Mode:  Target   →   Degraded  →   Floor    →   Recovery
         │            │             │             │
         │            │             │             │
  NTP sync OK    Sync age > 60s   Sync failed   New epoch
  δ = 100ms      δ grows to 500ms  δ unbounded   Resync
  HLC valid      HLC degraded      Logical only  Rebuild
         │            │             │             │
  Operations:                                     │
  - Fresh reads  - Stale reads   - Causal only  - Read-only
  - Lin. writes  - Eventual      - No freshness - Rebuild
         │            │             │             │
  Evidence:      Evidence:       Evidence:       Evidence:
  - HLC + CT     - Stale CT      - Lamport       - Epoch ID
  - Lease        - Expired lease - No sync       - New leader
  ```

  **Operator Mental Model (See/Think/Do)**:
  - **See**: Monitoring shows "NTP sync age: 75s, increasing"
  - **Think**: "Approaching degraded threshold (60s), evidence expiring"
  - **Do**:
    1. Alert: "Time sync degraded, staleness bounds relaxing"
    2. Check: Is backup NTP server available?
    3. If not: Accept degraded mode, larger δ, continue operations
    4. If degraded too long: Force recovery, new epoch, re-sync

  - **See**: "Clock jumped backward by 2 seconds"
  - **Think**: "MONOTONICITY violated, must start new epoch"
  - **Do**:
    1. Immediate: Enter recovery mode, reject new writes
    2. Increment epoch number, invalidate all leases
    3. Leader election: Establish new leader with new epoch
    4. Re-sync clocks, rebuild temporal evidence
    5. Exit recovery: Return to target mode with new evidence

- **Debugging with Temporal Evidence**

  **Incident: "Reads returning stale data"**
  ```
  Investigation steps:
  1. Check closed timestamp lag: CT_lag = now - CT_latest
     → Found: CT_lag = 5 seconds (Target: <200ms)

  2. Trace CT propagation:
     Leader: CT = T_leader - max_offset
     Follower: CT_received = T_leader (5s ago)
     → Root cause: CT broadcast blocked by network partition

  3. Check evidence validity:
     Follower lease: Expired 3 seconds ago
     → Should have entered degraded mode, forwarding to leader

  4. Fix:
     - Reduce CT advancement interval: 1s → 100ms
     - Add CT health check: Alert if lag > threshold
     - Fix lease renewal logic: Transition to degraded when expired

  5. Verify:
     - Mode transitions now evidence-triggered
     - CT lag metric green: <150ms
     - Staleness SLO restored
  ```

- **Design Checklist for New Time-Dependent System**
  ```
  □ Which invariant matters most?
    → ORDER for logs, FRESHNESS for reads, EXTERNAL CONSISTENCY for transactions

  □ What uncertainty is acceptable?
    → δ=100ms for most apps, δ=10ms for latency-sensitive, δ=ε for strong consistency

  □ What evidence is available?
    → NTP sync? Logical clocks? HLC? TrueTime? Closed timestamps?

  □ How does guarantee compose?
    → Trace evidence through all boundaries, identify weakest link

  □ What happens when evidence expires?
    → Mode matrix: Target → Degraded → Floor → Recovery

  □ How do operators observe and control?
    → Metrics: Clock offset, sync age, CT lag, staleness, mode
    → Actions: Force sync, new epoch, degrade gracefully
  ```

**Transfer Test (Far Distance)**:
- **Domain: Human Organizations and Processes**
  - "Meeting started late" = Clock skew between participants
  - "Missed deadline due to timezone confusion" = Coordination across time boundaries
  - "Email thread out of order" = Causal order without synchronized timestamps
  - **Insight**: Temporal coordination problems universal, not just distributed systems
  - **Solution**: Explicit evidence (calendar invites), bounded uncertainty (grace periods), causal tracking (reply-to headers)

---

## Exercises and Projects

### Conceptual Exercises
1. **Prove that vector clocks detect all concurrent updates**
2. **Calculate the minimum uncertainty for global time**
3. **Design a clock that combines HLC with uncertainty intervals**
4. **Analyze when closed timestamps are safe for reads**

### Implementation Projects
1. **Build an NTP client**
   - Implement clock synchronization
   - Handle network asymmetry
   - Measure achieved accuracy

2. **Create a vector clock library**
   - Support dynamic nodes
   - Implement compression
   - Benchmark overhead

3. **Implement HLC with CockroachDB semantics**
   - Transaction timestamps
   - Uncertainty intervals
   - Restart logic

### Production Analysis
1. **Measure clock skew in your cluster**
   - Deploy NTP monitoring
   - Graph drift over time
   - Identify problem nodes

2. **Analyze temporal guarantees**
   - What clocks does your system use?
   - What guarantees do they provide?
   - Where do guarantees degrade?

---

## References and Further Reading

### Foundational Papers
- Lamport. "Time, Clocks, and the Ordering of Events" (1978)
- Mattern. "Virtual Time and Global States" (1989)
- Kulkarni et al. "Logical Physical Clocks" (HLC) (2014)
- Corbett et al. "Spanner: Google's Globally-Distributed Database" (2012)

### Clock Synchronization
- Mills. "Network Time Protocol Version 4" (RFC 5905)
- IEEE 1588 "Precision Time Protocol" (PTP)
- Liskov. "Practical Uses of Synchronized Clocks" (1993)

### Production Systems
- "CockroachDB's Time Model" - Technical Documentation
- "YugabyteDB Hybrid Logical Clocks" - Architecture Guide
- "MongoDB Causal Consistency" - Implementation Notes

### Advanced Topics
- Almeida et al. "Interval Tree Clocks" (2008)
- Zawirski et al. "Bounded Counter CRDTs" (2012)
- Du et al. "Clock-SI: Snapshot Isolation for Partitioned Data Stores" (2013)

---

## Chapter Summary

### The Irreducible Truth
**"Time in distributed systems is not a single timeline but a partial order of causal relationships that we approximate with various clock mechanisms, each providing different guarantees with different costs."**

### Key Mental Models
1. **Time is Relative**: No global "now" exists; each node has its own timeline
2. **Causality > Wall Clock**: Preserving happened-before matters more than physical time
3. **Uncertainty is Fundamental**: All time measurements have error bounds
4. **Evidence Has Temporal Scope**: Timestamps are evidence with limited lifetime
5. **Composition Requires Care**: Different time models don't compose automatically

### What's Next
Chapter 3 will explore consensus—how distributed systems reach agreement despite failures, building on our time models to understand how nodes coordinate to maintain consistent state through protocols like Paxos, Raft, and modern Byzantine fault-tolerant algorithms.