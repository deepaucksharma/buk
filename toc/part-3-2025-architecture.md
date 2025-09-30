# Part III: The 2025 Architecture

## Chapter 8: Hierarchical Systems Design

### 8.1 Hierarchy Principles
* 8.1.1 Coordination Complexity
  - O(n²) communication limits
  - Broadcast storm prevention
  - Full mesh breakdown points
  - Spanning tree alternatives
* 8.1.2 Natural Boundaries
  - Geographic regions
  - Administrative domains
  - Failure domains
  - Security perimeters
  - Compliance boundaries
* 8.1.3 Information Flow
  - Control plane patterns
  - Data plane patterns
  - Aggregation strategies
  - Policy distribution

### 8.2 Multi-Level Architecture
* 8.2.1 Local Tier (Low Single-Digit Milliseconds)
  - Per-shard consensus (1-5ms typical)
    - Raft within single AZ: 1-2ms p50, 3-5ms p99
    - Local Paxos groups: 2-4ms commit latency
    - NVMe persistent state: 100-200μs writes
    - In-memory log replication: 50-100μs network RTT
  - Cache coherence
    - MESI/MOESI protocol overhead
    - Cross-socket latency: 100-300ns
    - NUMA-aware placement
  - Lock managers
    - Deadlock detection cycles
    - Lock table sharding
  - Local transactions
    - Single-replica operations
    - Fast path optimization
* 8.2.2 Regional Tier (Tens of Milliseconds)
  - Cross-AZ coordination (10-50ms)
    - Intra-region network: 1-5ms between AZs
    - Consensus rounds: 2-3 RTT minimum
    - Quorum assembly overhead
  - Regional transactions
    - Multi-AZ commits
    - Coordinated snapshots
  - Witness nodes
    - Tie-breaking without data
    - Lightweight participation
  - Flexible quorums
    - Read vs write quorum tuning
    - Dynamic quorum adjustment
* 8.2.3 Global Tier (Hundreds of Milliseconds to Seconds)
  - Configuration management via CRDTs
    - OR-Set for cluster membership
    - LWW-Register for feature flags
    - Causal broadcast for updates
    - Eventual convergence guarantees
  - Schema changes
    - Multi-phase rollout
    - Backward compatibility
  - Global invariants
    - Cross-region constraints
    - Periodic reconciliation
  - Rare coordination
    - Emergency operations
    - Manual intervention points

### 8.3 Modern Hardware Architecture (2025)
* 8.3.1 Data Processing Units (DPUs)
  - Storage offload patterns
    - NVMe-oF target on DPU
    - Erasure coding acceleration
    - Compression/decompression
    - Checksum computation
  - Network offload
    - TCP/IP stack on DPU
    - RDMA implementation
    - Overlay networking (VXLAN/Geneve)
    - Load balancing in hardware
  - Security functions
    - Encryption/decryption
    - Firewall rules
    - DDoS mitigation
  - Deployment examples
    - AWS Nitro (storage, network, security)
    - Azure SmartNIC (OVS offload)
    - BlueField DPUs (full infrastructure stack)
* 8.3.2 Disaggregated Memory
  - PCIe/CXL coherency protocols
    - CXL.mem: byte-addressable memory expansion
    - CXL.cache: cache-coherent acceleration
    - CXL.io: device discovery and enumeration
  - Memory pooling architectures
    - Shared memory pools across hosts
    - Dynamic memory allocation
    - Capacity vs bandwidth tradeoffs
  - Latency characteristics
    - Local DDR5: 80-100ns
    - CXL memory: 150-300ns (1-hop)
    - Multi-hop: 300-600ns
  - Fault isolation
    - Memory failure domains
    - Poison handling
    - Partial writes
* 8.3.3 Programmable Network
  - SmartNIC deployment patterns
    - OVS/OVN acceleration
    - Connection tracking offload
    - Flow table in hardware
  - In-network aggregation
    - SwitchML for ML training
    - ATP (Aggregation Throughput Protocol)
    - Reduce operations in ToR switches
    - Programmable P4 pipelines
  - RDMA at scale
    - RoCEv2 deployment (lossless DCB)
    - iWARP over TCP (lossy OK)
    - PFC (Priority Flow Control) headaches
      - Congestion spreading
      - Head-of-line blocking
      - PFC storms
    - ECN-based congestion control (DCQCN, TIMELY)
  - Configuration examples
    ```
    # RoCEv2 setup (Mellanox/NVIDIA)
    mlx5_port_config:
      priority_flow_control: "0,0,0,1,0,0,0,0"  # PFC on priority 3
      trust_mode: "dscp"
      dscp_to_prio_map: "0:0,26:3,48:3"  # RDMA on priority 3
      ecn_config:
        enable: true
        min_threshold_kb: 150
        max_threshold_kb: 1500

    # Connection tracking offload
    ovs_offload:
      hardware_offload: true
      ct_offload_timeout: 30s
      max_hw_flows: 1M
      sw_fallback: true
    ```

### 8.4 Production Case Studies
* 8.4.1 Google Spanner
  - Universe structure
  - Zone architecture
  - Paxos groups
  - Directory hierarchy
* 8.4.2 Spanner-Like Multi-Cloud Architecture
  - Cross-cloud challenges
    - Variable network latency (20-100ms)
    - Egress costs ($0.08-0.12/GB)
    - Control plane placement
    - Failure domain independence
  - Quorum placement strategies
    - Majority in primary cloud
    - Witness in third cloud for tie-breaking
    - Read replicas near users
  - Data residency compliance
    - EU data stays in EU
    - Regional constraints
    - Sovereignty requirements
  - Example topology
    ```
    Primary Quorum (5 replicas):
    - AWS us-east-1: Leader + Replica
    - AWS us-west-2: Replica
    - GCP us-central1: Replica (witness)
    - Azure East US: Replica (DR)

    Read Replicas (non-voting):
    - AWS eu-west-1 (GDPR compliance)
    - GCP asia-northeast1 (low latency reads)

    Control Plane (CRDT-based):
    - OR-Set for cluster membership
    - Gossip over TLS mesh
    - Causal stability: 5 minutes
    ```
* 8.4.3 Meta Infrastructure
  - Region architecture
  - TAO caching layers
  - Social graph sharding
  - Cross-region protocols
* 8.4.4 AWS Cell Architecture
  - Shuffle sharding
  - Blast radius control
  - Cell independence
  - Zonal deployment

---

## Chapter 9: Coordination Avoidance Patterns

### 9.1 Invariant Confluence
* 9.1.1 I-Confluence Theory
  - Merge preservation
    - Operation commutativity
    - State convergence
    - Invariant monotonicity
  - Invariant analysis
    - Per-operation vs global invariants
    - Monotonic vs non-monotonic constraints
  - Coordination requirements
    - When merge violates invariants
    - Minimum coordination points
  - Formal proofs
    - CRDTs as i-confluent operations
    - Counter-examples from write skew
* 9.1.2 Step-by-Step I-Confluence Checklist
  1. Identify the invariant
     - Example: "account balance >= 0"
     - Example: "unique usernames"
     - Example: "total inventory <= capacity"
  2. Analyze concurrent operations
     - Can two operations execute independently?
     - What happens when we merge their effects?
  3. Check monotonicity
     - Does the invariant constraint grow/shrink only?
     - Monotonic: "likes >= previous_likes" (i-confluent)
     - Non-monotonic: "balance in range [0, limit]" (needs coordination)
  4. Apply transformations
     - Escrow: Split constraint across replicas
     - Commutativity: Reorder operations without effect
     - Timestamp ordering: Deterministic tie-breaking
  5. Test merge scenarios
     - Concurrent increments: always safe
     - Concurrent decrements: check underflow
     - Mixed operations: analyze case-by-case

  Worked Example: Seat Reservation
  ```
  Invariant: total_sold <= total_seats (100 seats)

  Bad (non-confluent):
    Replica A: if (sold < 100) sold++  // sees 95
    Replica B: if (sold < 100) sold++  // sees 95
    After merge: sold = 97 (both succeeded)
    Possible oversell if 95 was stale

  Good (i-confluent via escrow):
    Replica A: escrow = 50 seats
      if (local_sold < 50) { local_sold++; return OK }
      else { return RETRY_OTHER_REPLICA }
    Replica B: escrow = 50 seats
      if (local_sold < 50) { local_sold++; return OK }

    Invariant preserved: A_sold + B_sold <= 50 + 50 = 100
    No coordination needed during normal operation
    Coordination only for escrow rebalancing
  ```

* 9.1.3 When NOT to Avoid Coordination
  - Strong safety-critical invariants
    - Financial correctness (no overdrafts allowed)
    - Regulatory compliance (audit trails)
    - Life-safety systems (medical device limits)
  - Uniqueness constraints
    - Primary keys
    - Usernames/emails
    - License plate numbers
  - Cross-entity transactions
    - Bank transfers (A + B = constant)
    - Foreign key constraints
    - Referential integrity
  - Low-contention scenarios
    - If coordination is rare, cost is acceptable
    - Don't over-optimize premature bottlenecks
  - Examples requiring coordination
    ```
    // Must coordinate: uniqueness
    INSERT INTO users (username) VALUES ('alice');

    // Must coordinate: cross-entity invariant
    UPDATE accounts SET balance = balance - 100 WHERE id = A;
    UPDATE accounts SET balance = balance + 100 WHERE id = B;

    // Can avoid: per-entity monotonic
    UPDATE posts SET likes = likes + 1 WHERE id = P;
    ```

* 9.1.4 Practical Application Patterns
  - Identifying I-confluent operations
    - Append-only logs (always i-confluent)
    - Counter increments (i-confluent with escrow)
    - Set additions (i-confluent with OR-Set)
  - Redesigning for confluence
    - Replace "read-modify-write" with "merge function"
    - Replace "check-then-act" with "escrow tokens"
    - Replace "last-write-wins" with "multi-value + resolve"
  - Write skew analysis
    - Detect via constraint graph
    - Prevent via predicate locks or coordination
  - Escrow transformations
    - Splitting bounds across replicas
    - Dynamic rebalancing protocols
* 9.1.5 Non-Confluent Handling
  - Minimal coordination
    - Coordinate only on invariant boundaries
    - Fast path for common case
  - Serialized sections
    - Single-writer regions
    - Optimistic locking with retry
  - Hybrid approaches
    - I-confluent for reads
    - Coordinated for critical writes
  - Compensation strategies
    - Detect violation after-the-fact
    - Rollback or reconciliation

### 9.2 CRDT Deep Dive
* 9.2.1 Foundational CRDTs with Implementations
  - G-Counter (Grow-only Counter)
    ```rust
    struct GCounter {
        counts: HashMap<ReplicaID, u64>,
    }

    impl GCounter {
        fn increment(&mut self, replica: ReplicaID) {
            *self.counts.entry(replica).or_insert(0) += 1;
        }

        fn value(&self) -> u64 {
            self.counts.values().sum()
        }

        fn merge(&mut self, other: &GCounter) {
            for (replica, count) in &other.counts {
                let entry = self.counts.entry(*replica).or_insert(0);
                *entry = (*entry).max(*count);
            }
        }
    }
    ```
    Metadata: O(n) space for n replicas

  - PN-Counter (Positive-Negative Counter)
    ```rust
    struct PNCounter {
        increments: GCounter,
        decrements: GCounter,
    }

    impl PNCounter {
        fn increment(&mut self, replica: ReplicaID) {
            self.increments.increment(replica);
        }

        fn decrement(&mut self, replica: ReplicaID) {
            self.decrements.increment(replica);
        }

        fn value(&self) -> i64 {
            self.increments.value() as i64 - self.decrements.value() as i64
        }
    }
    ```
    Metadata: O(2n) space for n replicas

  - OR-Set (Observed-Remove Set)
    ```rust
    struct ORSet<T> {
        elements: HashMap<T, HashSet<(ReplicaID, u64)>>, // (replica, unique_id)
    }

    impl<T: Hash + Eq> ORSet<T> {
        fn add(&mut self, replica: ReplicaID, unique_id: u64, elem: T) {
            self.elements.entry(elem).or_insert_with(HashSet::new)
                .insert((replica, unique_id));
        }

        fn remove(&mut self, elem: &T, observed_ids: HashSet<(ReplicaID, u64)>) {
            if let Some(ids) = self.elements.get_mut(elem) {
                ids.retain(|id| !observed_ids.contains(id));
                if ids.is_empty() {
                    self.elements.remove(elem);
                }
            }
        }

        fn contains(&self, elem: &T) -> bool {
            self.elements.get(elem).map_or(false, |ids| !ids.is_empty())
        }

        fn merge(&mut self, other: &ORSet<T>) {
            for (elem, ids) in &other.elements {
                self.elements.entry(elem.clone()).or_insert_with(HashSet::new)
                    .extend(ids);
            }
        }
    }
    ```
    Metadata: O(n * m) where n = elements, m = add operations per element
    Tombstones: Removed element IDs must be kept until causal stability

  - RGA (Replicated Growable Array) for text editing
    ```rust
    struct RGANode {
        id: (ReplicaID, u64, u64),  // (replica, timestamp, sequence)
        value: char,
        deleted: bool,
    }

    struct RGA {
        nodes: Vec<RGANode>,
        tombstones: Vec<RGANode>,  // deleted nodes
    }

    impl RGA {
        fn insert(&mut self, pos: usize, value: char, id: (ReplicaID, u64, u64)) {
            let node = RGANode { id, value, deleted: false };
            // Find insertion point considering tombstones
            let actual_pos = self.logical_to_physical_pos(pos);
            self.nodes.insert(actual_pos, node);
        }

        fn delete(&mut self, pos: usize) {
            let actual_pos = self.logical_to_physical_pos(pos);
            self.nodes[actual_pos].deleted = true;
            // Move to tombstones after causal stability
        }

        fn to_string(&self) -> String {
            self.nodes.iter()
                .filter(|n| !n.deleted)
                .map(|n| n.value)
                .collect()
        }
    }
    ```

  - LWW-Register (Last-Write-Wins) pitfalls
    ```rust
    struct LWWRegister<T> {
        value: T,
        timestamp: HLC,  // Hybrid Logical Clock
    }

    impl<T> LWWRegister<T> {
        fn set(&mut self, value: T, ts: HLC) {
            if ts > self.timestamp {
                self.value = value;
                self.timestamp = ts;
            }
        }
    }
    ```
    Pitfalls:
    - Lost updates if clocks not synchronized
    - Concurrent writes at same timestamp: need tie-breaker (replica ID)
    - No multi-value conflict resolution
    - Best for: config flags, user preferences (low value updates)
    - Avoid for: critical state, high-frequency writes

* 9.2.2 Advanced CRDTs
  - JSON CRDTs (Automerge)
    - Nested CRDT composition
    - Map: keys use OR-Set semantics
    - List: RGA with tombstones
    - Registers: LWW or MVR
    - Columnar encoding for efficiency
    ```
    Automerge document structure:
    {
      "users": Map<String, Register>,  // OR-Set of keys + LWW values
      "messages": List<Text>,           // RGA of text CRDTs
      "counters": Map<String, Counter>  // PN-Counter per key
    }

    Space overhead:
    - Base JSON: 1 KB
    - With metadata: 3-10 KB (depending on edit history)
    - After GC: 1.5-2 KB
    ```

  - CRDT databases
    - Riak (OR-Set based)
    - Redis CRDT (CRDB)
    - Soundcloud Roshi (LWW event stream)
    - Akka Distributed Data

  - Collaborative editing at scale
    - Yjs: Fast CRDT for editors
    - Operational transformation vs CRDT tradeoffs
    - Rich text formatting challenges
    - Undo/redo with CRDTs

  - Causal stability
    - Definition: All replicas have seen up to timestamp T
    - Detection: Version vector comparison
    - Window: Typically 5-60 minutes in production
    - Uses: Tombstone GC, snapshotting

* 9.2.3 CRDT Limitations and Operational Tradeoffs
  - Metadata explosion patterns
    - OR-Set tombstones: O(adds) until GC
    - Version vectors: O(replicas)
    - RGA edit history: O(characters typed)
    - Mitigation: Aggressive GC policies

  - Tombstone management strategies
    ```
    Strategy 1: Time-based GC
    - Keep tombstones for causal_stability_window
    - Risk: Late-arriving updates cause resurrection
    - Config: window = 2 * max_partition_duration

    Strategy 2: Version vector GC
    - GC when all replicas have seen delete
    - Requires version vector maintenance
    - Overhead: O(n) space per replica

    Strategy 3: Hybrid (production approach)
    - Short window (5 min) for online replicas
    - Long window (7 days) for offline clients
    - Separate tombstone store for long-term
    ```

  - Tombstone GC vs privacy guarantees
    - GDPR right to deletion
    - Problem: Tombstones are anti-deletion
    - Solution: Crypto erasure
      ```
      Encrypted CRDT pattern:
      1. Encrypt element value with key K
      2. Store encrypted value + tombstone metadata
      3. On "forget": destroy key K
      4. Result: value unrecoverable but merge still works
      5. Tombstone can be GC'd after causal stability
      ```
    - Alternative: Global coordination for true deletion

  - Version vector growth
    - Problem: O(n) space for n replicas
    - Mitigation 1: Replica ID reuse after retirement
    - Mitigation 2: Compact encoding (varint)
    - Mitigation 3: Dotted version vectors (only store differences)
    ```rust
    // Standard version vector
    struct VersionVector {
        clocks: HashMap<ReplicaID, u64>,  // O(n) space
    }

    // Dotted version vector (more compact)
    struct DottedVersionVector {
        base: HashMap<ReplicaID, u64>,     // Stable baseline
        dots: HashSet<(ReplicaID, u64)>,   // Recent updates only
    }
    ```

  - Performance impacts
    - Merge cost: O(n) to O(n²) depending on CRDT
    - Memory overhead: 2-10x base data size
    - Network overhead: Sending full state vs deltas
    - CPU cost: Tombstone filtering on read

  - Production metrics (real-world CRDT system)
    ```
    Riak KV with OR-Set (shopping cart):
    - Base cart size: 500 bytes (5 items)
    - With metadata: 2.1 KB (4.2x overhead)
    - After weekly GC: 800 bytes (1.6x overhead)
    - Merge latency: 100μs p50, 500μs p99

    Automerge collaborative doc:
    - Document: 10 KB text, 500 edits
    - Full state: 45 KB (4.5x)
    - Incremental update: 200 bytes/edit
    - Merge: 2ms for 100 concurrent edits
    - GC reduces to: 12 KB (1.2x) after stability
    ```

### 9.3 Escrow and Reservations
* 9.3.1 Escrow Mathematics
  - Token allocation formulas
  - Refill strategies
  - Debt ceilings
  - Oversell risk calculation
* 9.3.2 Multi-Level Escrow
  - Global → Regional
  - Regional → Local
  - Dynamic rebalancing
  - Starvation detection
* 9.3.3 Reservation Systems
  - Time-bounded holds
  - Soft reservations
  - Reaper policies
  - User-visible states
  - Expiry handling

---

## Chapter 10: The Deterministic Revolution

### 10.1 Deterministic Execution
* 10.1.1 Calvin Architecture
  - Transaction pre-ordering
    - Global log defines execution order
    - Deterministic locking sequence
    - No deadlocks by design
  - Deterministic locking
    - Lock in sorted order by key
    - Two-phase locking with fixed order
  - Parallel execution
    - Independent transactions in parallel
    - Conflicting transactions serialized
  - Recovery simplicity
    - Replay log deterministically
    - No coordination needed
    - Identical state guaranteed

* 10.1.2 Floating-Point Determinism Gotchas
  - Architecture-specific behavior
    ```c
    // Same source code, different results
    float x = 0.1f;
    float y = 0.2f;
    float z = x + y;  // May differ on x86 vs ARM vs GPU

    // x86 with x87 FPU (80-bit intermediate):
    // z = 0.30000001192092896  (80-bit → 32-bit rounding)

    // ARM with VFP (32-bit throughout):
    // z = 0.30000000000000004

    // GPU (may use different rounding modes):
    // z = 0.29999998211860657
    ```

  - FMA (Fused Multiply-Add) differences
    ```c
    // Standard: (a * b) + c
    float result1 = a * b + c;  // Two rounding operations

    // FMA: single rounding
    float result2 = fma(a, b, c);  // One rounding operation

    // Example where they differ:
    a = 1.0e20, b = 1.0e-20, c = 1.0
    result1 = 1.0 + 0.0 = 1.0        (loses a*b precision)
    result2 = 1.0000000000000002     (keeps precision)

    // FMA availability:
    // - x86: Since Haswell (2013), requires -mfma flag
    // - ARM: Since ARMv8, default enabled
    // - Compiler may auto-generate FMA, breaking determinism
    ```

  - Compiler optimization issues
    ```c
    // Source code
    double compute() {
        double a = get_value();
        double b = a * 2.0;
        return b + 1.0;
    }

    // GCC -O3 may optimize to:
    return fma(a, 2.0, 1.0);  // Uses FMA if available

    // GCC -O2 generates:
    vmulsd %xmm0, %xmm1, %xmm0  // multiply
    vaddsd %xmm0, %xmm2, %xmm0  // add

    // Result: non-determinism across optimization levels
    ```

  - Solution: Strict FP control
    ```rust
    // Rust: explicit control
    #![feature(f128)]
    use std::num::FpCategory;

    fn deterministic_add(a: f64, b: f64) -> f64 {
        // Force no FMA
        #[cfg(target_feature = "fma")]
        compile_error!("FMA must be disabled");

        a + b  // Guaranteed two-stage rounding
    }

    // C: pragma control
    #pragma STDC FP_CONTRACT OFF  // Disable FMA contraction
    ```

  - Parallel reduction non-determinism
    ```python
    # Non-deterministic: sum order varies
    import numpy as np
    result = np.sum(array, axis=1)  # Uses SIMD, order varies

    # Why: (a + b) + c != a + (b + c) for floats
    # Example:
    a, b, c = 1e20, 1.0, -1e20
    (a + b) + c = 0.0
    a + (b + c) = 1.0

    # Deterministic solution:
    result = np.add.reduce(array, axis=1)  # Fixed left-to-right order
    ```

* 10.1.3 Hash Map Ordering Non-Determinism
  - Hash randomization for security
    ```rust
    // Rust HashMap uses SipHash with random seed
    use std::collections::HashMap;

    let mut map = HashMap::new();
    map.insert("key1", 1);
    map.insert("key2", 2);

    // Iteration order is non-deterministic across runs
    for (k, v) in &map {
        println!("{}: {}", k, v);  // Order varies!
    }

    // Fix: Use BTreeMap for deterministic order
    use std::collections::BTreeMap;
    let mut map = BTreeMap::new();  // Lexicographic order guaranteed
    ```

  - Java HashMap issues
    ```java
    // Java 7: iteration order depends on hash codes + capacity
    Map<String, Integer> map = new HashMap<>();
    map.put("a", 1);
    map.put("b", 2);
    map.keySet().forEach(System.out::println);  // Non-deterministic

    // Java 8+: more stable but still not guaranteed
    // Fix: Use LinkedHashMap (insertion order)
    Map<String, Integer> map = new LinkedHashMap<>();
    ```

* 10.1.4 Complete Determinism Checklist
  1. Time Sources
     - [ ] Replace System.currentTimeMillis() with logical clock
     - [ ] Use HLC (Hybrid Logical Clock) for ordering
     - [ ] No wall-clock dependencies in business logic
     - [ ] Example:
       ```java
       // Bad
       long now = System.currentTimeMillis();
       if (now > deadline) { ... }

       // Good
       HLC now = hlc.now();
       if (now.compareTo(deadline) > 0) { ... }
       ```

  2. Random Number Generation
     - [ ] Seed all RNGs explicitly with logged seed
     - [ ] Use deterministic PRNG (e.g., xorshift)
     - [ ] Log seed in transaction metadata
     - [ ] Example:
       ```rust
       use rand::{SeedableRng, rngs::StdRng};
       let seed: u64 = transaction.get_seed();
       let mut rng = StdRng::seed_from_u64(seed);
       let random_val = rng.gen_range(0..100);
       ```

  3. Iteration Order
     - [ ] Use ordered collections (BTreeMap, sorted vec)
     - [ ] Sort before iteration if order matters
     - [ ] No reliance on HashMap/HashSet iteration order
     - [ ] Example:
       ```rust
       // Bad
       for (key, value) in hashmap.iter() { ... }

       // Good
       let mut keys: Vec<_> = hashmap.keys().collect();
       keys.sort();
       for key in keys { ... }
       ```

  4. Floating-Point Operations
     - [ ] Disable FMA or use consistently across platforms
     - [ ] Set consistent rounding modes
     - [ ] Use fixed-point arithmetic for money
     - [ ] Document precision requirements
     - [ ] Flags: -ffp-contract=off (GCC), -fp-model=precise (MSVC)
     - [ ] Avoid parallel reductions unless order fixed

  5. Locale and Encoding
     - [ ] Pin locale to POSIX/C (no locale-dependent sorting)
     - [ ] Use UTF-8 exclusively
     - [ ] Explicit collation for string comparison
     - [ ] Example:
       ```rust
       // Bad: locale-dependent
       strings.sort();

       // Good: explicit collation
       strings.sort_by(|a, b| {
           a.bytes().cmp(b.bytes())  // Byte-wise comparison
       });
       ```

  6. Parallelism
     - [ ] No data races (use Arc/Mutex or message passing)
     - [ ] Deterministic thread scheduling (or avoid threads)
     - [ ] Fixed order for parallel results aggregation
     - [ ] Example:
       ```rust
       // Bad: race on counter
       let counter = Arc::new(Mutex::new(0));
       threads.par_iter().for_each(|_| {
           *counter.lock().unwrap() += 1;  // Non-deterministic order
       });

       // Good: map-reduce with sorted aggregation
       let results: Vec<_> = threads.par_iter()
           .map(|id| compute(id))
           .collect();
       results.sort_by_key(|r| r.id);
       let total = results.iter().map(|r| r.value).sum();
       ```

  7. External Input
     - [ ] Log all external inputs (API calls, user input)
     - [ ] Replay from log, not from live sources
     - [ ] Deterministic mocking in tests
     - [ ] Example transaction log:
       ```json
       {
         "tx_id": 12345,
         "inputs": {
           "user_request": {"action": "transfer", "amount": 100},
           "db_state": {"balance": 500},
           "random_seed": 0x123456,
           "timestamp": "HLC(physical=1000, logical=5)"
         }
       }
       ```

  8. System Calls
     - [ ] Intercept file I/O (log reads, mock in replay)
     - [ ] Deterministic network simulation
     - [ ] Virtual time for sleep/timeout
     - [ ] Example:
       ```rust
       trait FileSystem {
           fn read(&self, path: &str) -> Vec<u8>;
       }

       struct DeterministicFS {
           logged_reads: HashMap<String, Vec<u8>>,
       }
       ```

  9. Testing
     - [ ] Run test suite with deterministic mode
     - [ ] Verify replay produces identical state
     - [ ] Fuzz with recorded seeds
     - [ ] Example CI check:
       ```bash
       # Run test 100 times, should produce same output
       for i in {1..100}; do
         ./run_test --deterministic --seed=42 > output$i.txt
       done
       sort output*.txt | uniq | wc -l  # Should be 1
       ```

* 10.1.5 Production Systems
  - FaunaDB design
    - Calvin-style pre-ordering
    - Deterministic query execution
    - Temporal queries via log replay
  - FoundationDB approach
    - Simulation testing framework
    - Deterministic execution in tests
    - Buggify for fault injection
  - VoltDB architecture
    - Stored procedures in Java
    - Single-threaded execution per partition
    - Strict determinism enforcement
  - Performance analysis
    - Overhead: ~5-10% vs non-deterministic
    - Benefits: Easy replay, debugging, testing
    - Recovery: 10x faster (no coordination)

### 10.2 Simulation Testing
* 10.2.1 Simulation Framework
  - Time control
  - Network simulation
  - Disk fault injection
  - Schedule exploration
* 10.2.2 Bug Finding
  - Systematic testing
  - State space reduction
  - Invariant checking
  - Liveness validation
* 10.2.3 Production Integration
  - Shadow testing
  - Replay debugging
  - Continuous validation
  - Performance regression

### 10.3 Formal Methods
* 10.3.1 TLA+ in Practice
  - Protocol specification
  - Invariant definition
  - Model checking
  - Refinement mapping
* 10.3.2 Implementation Gap
  - Code generation
  - Runtime monitoring
  - Conformance testing
  - Proof preservation
* 10.3.3 Industry Adoption
  - Amazon's experience
  - Microsoft's P language
  - Cosmos DB verification
  - Lessons learned