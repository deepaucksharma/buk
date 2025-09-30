# Evidence Calculus for Impossibility Results

## Introduction: Converting Impossibility into Evidence

Every distributed system is a machine for preserving invariants across space and time by converting uncertainty into evidence. But what happens when impossibility results—FLP, CAP, consensus lower bounds—tell us that certain guarantees are fundamentally unachievable? The answer lies in a rigorous **evidence calculus**: a formal framework for understanding what we can know, what we cannot know, and how to operate soundly within those boundaries.

This chapter develops the complete evidence calculus for impossibility results. We define:

1. **Evidence taxonomy** for detecting and reasoning about impossibility conditions
2. **Typed guarantee vectors** that degrade predictably when impossibilities manifest
3. **Context capsules** that carry impossibility constraints across system boundaries
4. **Mode matrices** that define safe operation under impossibility
5. **Evidence lifecycles** from generation through expiration
6. **Calculus principles** for composition, weakening, and circumvention

The central insight: **impossibility results don't prohibit building systems—they define the evidence requirements for safe operation**. FLP doesn't say "consensus is impossible"; it says "consensus requires detecting failures, and failure detection requires assumptions we must make explicit." CAP doesn't say "pick two"; it says "availability and consistency require different evidence, which cannot coexist during partitions."

## I. Evidence Taxonomy for Impossibility Conditions

Impossibility results manifest through observable phenomena. Our taxonomy classifies the evidence we can gather about system behavior and the conclusions we can safely draw.

### 1.1 Failure Detector Evidence

Failure detectors are the primary mechanism for circumventing FLP. Each class provides different evidence with different guarantees.

#### Perfect Failure Detector (P)

**Evidence Type**: Definitive failure notification
**Properties**:
- **Strong Completeness**: Eventually every crashed process is permanently suspected by every correct process
- **Strong Accuracy**: No process is suspected before it crashes

**Scope**: Process-level
**Lifetime**: Permanent once generated (monotonic)
**Binding**: Bound to process identity and configuration epoch
**Transitivity**: Transitive—if A knows P crashed and tells B with proof, B can rely on it
**Revocation**: None (crashes are permanent in this model)

**Implementation Requirements**:
- Synchronous system assumption (known bounds on message delay and processing)
- Reliable detection mechanism (e.g., hardware watchdog, STONITH)
- No false positives tolerated

**Evidence Structure**:
```
PerfectFailureEvidence {
  failed_process: ProcessID,
  detection_time: PhysicalTimestamp,
  detector: ProcessID,
  epoch: ConfigurationEpoch,
  mechanism: DetectionMechanism,  // hardware, timeout with proven bounds
  attestation: Signature           // cryptographic binding
}
```

**Usage**: Enables consensus with termination guarantees in synchronous systems. Presence of this evidence allows algorithms to make progress by excluding failed processes from quorums.

**Absence Semantics**: Without perfect detection, must fall back to weaker detectors or probabilistic termination.

#### Eventually Perfect Failure Detector (◊P)

**Evidence Type**: Eventually reliable suspicion
**Properties**:
- **Strong Completeness**: Same as P
- **Eventual Strong Accuracy**: After some unknown time T, no correct process is suspected

**Scope**: Process-level
**Lifetime**: Evidence may be retracted; only eventual stability guaranteed
**Binding**: Bound to process and time interval
**Transitivity**: Non-transitive during unstable period
**Revocation**: Suspicions can be withdrawn; requires versioning

**Implementation Requirements**:
- Eventually synchronous system (partial synchrony)
- Adaptive timeout mechanisms
- Heartbeat protocols with increasing timeouts

**Evidence Structure**:
```
EventuallyPerfectEvidence {
  suspected_process: ProcessID,
  suspicion_time: LogicalTimestamp,
  suspicion_version: VersionNumber,    // allows retraction
  detector: ProcessID,
  confidence: ConfidenceLevel,         // increases over time
  stability_flag: Boolean,              // true after GST
  epoch: ConfigurationEpoch
}
```

**Usage**: Enables consensus in partially synchronous systems (Raft, Multi-Paxos, PBFT). Must handle suspicion churn before stabilization.

**Absence Semantics**: Cannot guarantee termination; may livelock if suspicions never stabilize.

**Composition Rule**: When composing with mechanisms requiring P, must either:
1. Wait for stability_flag = true (blocks progress)
2. Use probabilistic evidence and accept non-zero livelock probability
3. Introduce external synchronization (watchdog, lease service)

#### Strong Failure Detector (S)

**Evidence Type**: Complete suspicion with eventual accuracy
**Properties**:
- **Strong Completeness**: Eventually every crashed process is permanently suspected
- **Weak Accuracy**: Some correct process is never suspected

**Scope**: System-level (at least one correct process)
**Lifetime**: Permanent for crashed; may be incorrect for some correct processes
**Binding**: Weaker binding—some correct processes may be falsely accused
**Transitivity**: Non-transitive—others may have different suspicion sets
**Revocation**: No retraction for crashed; false suspicions may persist

**Implementation Requirements**:
- Asymmetric network assumptions (some paths more reliable)
- Hierarchical detection (some processes privileged)
- Stable core subset

**Evidence Structure**:
```
StrongFailureEvidence {
  suspected_process: ProcessID,
  detector: ProcessID,
  is_definitive: Boolean,            // true only for crashed
  protected_set: Set<ProcessID>,      // never suspected
  epoch: ConfigurationEpoch
}
```

**Usage**: Sufficient for consensus but allows some correct processes to be permanently excluded. Used in Byzantine settings where some correct processes may be isolated.

**Absence Semantics**: Falls back to weak detector; fewer processes can coordinate.

#### Weak Failure Detector (W)

**Evidence Type**: Incomplete suspicion
**Properties**:
- **Weak Completeness**: Eventually every crashed process is permanently suspected by some correct process
- **Weak Accuracy**: Some correct process is never suspected

**Scope**: Partial—only some correct processes have evidence
**Lifetime**: Permanent for crashed; varies by detector
**Binding**: Detector-specific; non-uniform
**Transitivity**: Non-transitive—evidence must be shared explicitly
**Revocation**: Detector-dependent

**Implementation Requirements**:
- Minimal synchrony assumptions
- Gossip-based dissemination
- Quorum-based aggregation

**Evidence Structure**:
```
WeakFailureEvidence {
  suspected_process: ProcessID,
  detector: ProcessID,
  witness_set: Set<ProcessID>,        // who else suspects
  quorum_size: Integer,                // needed for confidence
  epoch: ConfigurationEpoch
}
```

**Usage**: Enables consensus but requires evidence aggregation. Individual suspicions insufficient; must collect quorum of suspicions.

**Absence Semantics**: No consensus possible; reduced to termination detection or completely asynchronous protocols (which cannot guarantee progress).

### 1.2 Timeout Evidence and Its Limitations

Timeouts are the most common "evidence" in practice, but they are fundamentally ambiguous.

#### Timeout Evidence Properties

**Evidence Type**: Response deadline violation
**Scope**: Request-response pair
**Lifetime**: Instantaneous—only valid at timeout moment
**Binding**: Bound to specific request and timeout value
**Transitivity**: Non-transitive—timeout for A→B says nothing about B→C
**Revocation**: Response arrival revokes timeout retroactively (but decision may already be made)

**Structure**:
```
TimeoutEvidence {
  request_id: RequestID,
  sender: ProcessID,
  receiver: ProcessID,
  timeout_value: Duration,
  timeout_time: Timestamp,
  context: {
    expected_bound: Duration,      // what we assumed
    previous_latencies: [Duration], // historical data
    network_conditions: Conditions  // known issues
  }
}
```

**Limitations**:

1. **Cannot Distinguish Failure Types**:
   - Slow response vs crashed process
   - Network partition vs process overload
   - Message loss vs message delay

2. **No Accuracy Guarantee**:
   - False positives in asynchronous systems
   - Correct processes appear failed under load
   - Cannot prove crash vs slowness

3. **Coordination Required**:
   - Different processes may have different timeout evidence
   - Clock skew affects timeout interpretation
   - Must aggregate to get confidence

**Evidence Calculus for Timeouts**:

```
TimeoutConfidence = f(
  timeout_value / expected_latency,     // how much margin
  consistency_across_detectors,         // agreement
  historical_stability,                 // track record
  alternative_evidence                  // corroborating signals
)
```

**Composition with Failure Detectors**:
- Raw timeout → W (weak completeness at best)
- Timeout + quorum agreement → S (if some correct never timeout)
- Timeout + bounded network → ◊P (eventual accuracy)
- Timeout + synchronous system → P (strong accuracy)

**Upgrade Path**: Timeout evidence can be upgraded to failure detector evidence by:
1. Adding synchrony assumptions (bounds)
2. Collecting quorum of consistent timeouts
3. Combining with other evidence (health checks, monitoring)
4. Waiting for stability period (eventual synchrony)

### 1.3 Message Omission Evidence

Networks can lose messages. What can we prove about omissions?

#### Omission Evidence Types

**Fair-Loss Link Evidence**:
- **Property**: If sender sends infinitely often, receiver receives infinitely often
- **Evidence**: Cannot prove single message lost, only patterns over time
- **Scope**: Link between two processes
- **Lifetime**: Statistical (requires multiple sends)
- **Binding**: Sender-receiver pair
- **Transitivity**: Non-transitive

```
FairLossEvidence {
  link: (ProcessID, ProcessID),
  sends_observed: Integer,
  receives_observed: Integer,
  omission_rate: Probability,
  time_window: Duration,
  confidence_interval: (Float, Float)
}
```

**Stubborn Link Evidence**:
- **Property**: Every message is retransmitted infinitely often; eventually delivered
- **Evidence**: Proves eventual delivery, not timely delivery
- **Scope**: Link with retry mechanism
- **Lifetime**: Proof requires observing delivery or bounded omissions
- **Binding**: Message ID and link

```
StubbornLinkEvidence {
  message_id: MessageID,
  link: (ProcessID, ProcessID),
  retransmission_count: Integer,
  max_omissions_observed: Integer,
  delivery_confirmed: Boolean,
  timestamp_first_send: Timestamp,
  timestamp_delivery: Option<Timestamp>
}
```

**Perfect Link Evidence**:
- **Property**: If sender sends once, receiver receives exactly once
- **Evidence**: Requires no duplicates, no omissions, no fabrication
- **Scope**: Link with reliable protocol
- **Lifetime**: Per-message proof (ACK)
- **Binding**: Message ID, sender, receiver
- **Transitivity**: Can be chained if each hop proves perfect delivery

```
PerfectLinkEvidence {
  message_id: MessageID,
  sender: ProcessID,
  receiver: ProcessID,
  send_timestamp: Timestamp,
  receive_timestamp: Timestamp,
  ack_signature: Signature,        // cryptographic receipt
  deduplication_token: Token,      // proves exactly-once
  epoch: ConfigurationEpoch
}
```

**Evidence Lifecycle**:
1. **Generation**: Sender records send; receiver records receive
2. **Validation**: ACK verified; deduplication checked
3. **Active**: Evidence valid within epoch
4. **Expiring**: Epoch change or timeout approaching
5. **Expired**: New transmission required

**Absence Semantics**:
- No perfect link evidence → assume fair-loss
- No fair-loss evidence → assume arbitrary omissions (adversarial)
- Must design protocols that tolerate missing evidence

### 1.4 Partition Detection Evidence

Network partitions are the crux of CAP. What can we detect?

#### Partition Evidence Properties

**Evidence Type**: Connectivity loss
**Scope**: Set of processes that cannot communicate
**Lifetime**: Duration of partition (hard to determine precisely)
**Binding**: Network topology and process set
**Transitivity**: Partial—A cannot reach B and B cannot reach C doesn't mean A cannot reach C
**Revocation**: Connectivity restoration revokes partition evidence

**Structure**:
```
PartitionEvidence {
  partition_id: PartitionID,
  detected_by: ProcessID,
  detection_time: Timestamp,
  unreachable_processes: Set<ProcessID>,
  reachable_processes: Set<ProcessID>,
  evidence_sources: [ConnectivityProbe],
  confidence: ConfidenceLevel,
  epoch: ConfigurationEpoch
}

ConnectivityProbe {
  source: ProcessID,
  destination: ProcessID,
  probe_time: Timestamp,
  result: ProbeResult,  // Success, Timeout, Refused, NetworkError
  latency: Option<Duration>
}
```

**Detection Mechanisms**:

1. **Direct Evidence**: Process A cannot reach B
   - Timeout on direct messages
   - TCP connection failures
   - Ping/health check failures

2. **Transitive Evidence**: A can reach C, C cannot reach B → A and B partitioned
   - Requires gossip or coordinator
   - Evidence aggregation needed
   - May have false positives (asymmetric partition)

3. **Quorum Evidence**: Majority of processes agree on partition
   - Stronger than individual detection
   - Enables safe decision-making
   - Requires pre-partition majority

**Limitations**:

1. **Cannot Prove Partition Start**:
   - Slowness vs partition ambiguous
   - Gradual degradation hard to detect
   - No single definitive moment

2. **Cannot Prove Partition End**:
   - One message through doesn't mean partition healed
   - May be transient connectivity
   - Requires sustained evidence

3. **Asymmetric Partitions**:
   - A can reach B, B cannot reach A
   - Evidence conflicts across processes
   - Requires careful quorum rules

**Composition with CAP**:

```
CAPDecision {
  mode: ConsistencyPreference | AvailabilityPreference,

  consistency_mode: {
    requires: QuorumPartitionEvidence,
    action: BlockMinorityPartition,
    guarantees: ⟨Global, Lx, Serializable, Fresh(φ), Idem(K), Auth(π)⟩
  },

  availability_mode: {
    requires: LocalPartitionEvidence,
    action: AllowLocalWrites,
    guarantees: ⟨Local, Causal, ReadAtomic, Eventual, Idem(K), Auth(π)⟩
  },

  partition_evidence: PartitionEvidence,
  decision_time: Timestamp,
  epoch: ConfigurationEpoch
}
```

**Evidence-Based CAP Strategy**:

| Evidence State | CP System Behavior | AP System Behavior |
|---------------|-------------------|-------------------|
| No partition evidence | Strong consistency available | Strong consistency preferred |
| Weak partition evidence (timeouts) | Cautious—may reject writes | Continue with conflict detection |
| Strong partition evidence (quorum) | Minority blocks, majority proceeds | All partitions accept writes |
| Partition healing evidence | Wait for stability, then merge | Begin conflict resolution |
| Post-healing | Resume normal operation | Convergence protocol active |

### 1.5 Synchrony Bound Violations

Partial synchrony assumes eventual bounds. Detecting violations is evidence we're outside assumptions.

#### Synchrony Violation Evidence

**Evidence Type**: Bound exceeded
**Scope**: Message delay or clock drift observation
**Lifetime**: Per-observation; pattern over time
**Binding**: Specific bound and measurement
**Transitivity**: Non-transitive
**Revocation**: Bound restoration revokes violation

**Structure**:
```
SynchronyViolationEvidence {
  violation_type: MessageDelay | ClockDrift | ProcessingTime,

  message_delay_violation: {
    expected_bound: Duration,
    observed_delay: Duration,
    message_id: MessageID,
    path: (ProcessID, ProcessID),
    timestamp_send: Timestamp,
    timestamp_receive: Timestamp
  },

  clock_drift_violation: {
    expected_drift_bound: Duration,
    observed_drift: Duration,
    processes: (ProcessID, ProcessID),
    measurement_method: ExternalSync | QuorumComparison,
    timestamp: Timestamp
  },

  processing_time_violation: {
    expected_processing_bound: Duration,
    observed_processing_time: Duration,
    operation: OperationType,
    process: ProcessID,
    timestamp: Timestamp
  },

  context: {
    is_transient: Boolean,
    recurrence_count: Integer,
    first_observed: Timestamp,
    last_observed: Timestamp,
    system_load_during_violation: LoadMetrics
  }
}
```

**Detection Mechanisms**:

1. **Statistical Monitoring**: Track latency distributions, detect outliers
2. **Explicit Bounds**: Configure timeouts, measure violations
3. **Clock Comparison**: Use GPS/NTP to detect drift beyond bounds
4. **Workload Characterization**: Measure processing times, detect anomalies

**Implications for Guarantees**:

| Violation Type | Affected Guarantee | Degradation Strategy |
|---------------|-------------------|---------------------|
| Message delay exceeds bound | Termination guarantee | Extend timeout, risk livelock |
| Clock drift exceeds bound | Timestamp ordering | Fall back to causal order |
| Processing time exceeds bound | Linearizability | Downgrade to sequential consistency |
| Repeated violations | Partial synchrony assumption | Treat as asynchronous |

**Evidence Calculus**:

```
SystemSynchronyConfidence = f(
  fraction_violations / total_observations,
  max_violation_magnitude / expected_bound,
  recency_of_violations,
  correlation_across_measurements
)

if SystemSynchronyConfidence < threshold:
  degrade_guarantees(AsynchronousAssumptions)
```

**Lifecycle Integration**:

1. **Generation**: Instrumentation detects bound violation
2. **Validation**: Confirm violation not measurement error
3. **Active**: System operates with weakened assumptions
4. **Expiring**: Observe bound compliance resuming
5. **Expired**: Confidence restored, resume strong guarantees
6. **Renewal**: Continuous monitoring for new violations

## II. Typed Guarantee Vectors for Impossibility Results

Impossibility results constrain which guarantee vectors are achievable. We define vectors for systems respecting FLP, CAP, and PACELC, showing how guarantees degrade at boundaries.

### 2.1 Guarantee Vector Definition (Review)

```
G = ⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩

Scope ∈ {Object, Range, Transaction, Global}
Order ∈ {None, Causal, Lx (linearizable per-object), SS (strict serializable)}
Visibility ∈ {Fractured, RA (read-atomic), SI (snapshot isolation), SER (serializable)}
Recency ∈ {EO (eventual only), BS(δ) (bounded staleness), Fresh(φ) (verifiable proof)}
Idempotence ∈ {None, Idem(K) (keying discipline)}
Auth ∈ {Unauth, Auth(π) (identity/attestation)}
```

### 2.2 FLP-Respecting Systems

**Impossibility Statement**: In an asynchronous system with even one crash failure, no deterministic consensus protocol can guarantee termination.

**Implication for Guarantees**: Cannot achieve both:
- **Safety** (agreement, validity, integrity)
- **Liveness** (termination)

in fully asynchronous systems without additional assumptions.

#### FLP Floor Vector (No Synchrony Assumptions)

```
G_FLP_Floor = ⟨
  Scope: Global,
  Order: Causal,
  Visibility: RA,
  Recency: EO,
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Global scope**: All processes eventually learn decision
- **Causal order**: Respects causality but no linearization
- **Read-atomic visibility**: Consistent reads within a process
- **Eventual recency**: No time bound on propagation
- **Idempotence required**: Cannot rely on exactly-once delivery
- **Authentication present**: Can verify message source

**Termination Guarantee**: **None**—may run forever

**Evidence Requirements**: None (operates without failure detection)

**Use Cases**: CRDTs, eventual consistency systems, gossip protocols

#### FLP Target Vector (With ◊P Failure Detector)

```
G_FLP_Target = ⟨
  Scope: Global,
  Order: Lx,
  Visibility: SER,
  Recency: Fresh(φ),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Linearizable order**: Total order on operations
- **Serializable visibility**: Consistent snapshots
- **Fresh recency**: Provable freshness (leader lease)
- **Termination Guarantee**: **Eventual** (after GST, with ◊P)

**Evidence Requirements**:
- **◊P failure detector** evidence (heartbeats, timeouts)
- **Leader lease** φ with epoch E
- **Quorum certificates** for commits

**Upgrade Path from Floor**:
```
G_FLP_Floor
  + EventuallyPerfectEvidence
  + LeaderLeaseEvidence
  → G_FLP_Target
```

**Degradation Triggers**:
- Loss of ◊P evidence → fall back to Floor
- Lease expiration → block until renewal
- Quorum loss → cannot commit

#### FLP Probabilistic Vector (Randomization)

```
G_FLP_Probabilistic = ⟨
  Scope: Global,
  Order: Lx (with probability 1),
  Visibility: SER (with probability 1),
  Recency: Fresh(φ) (with probability 1),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Probabilistic termination**: Terminates with probability 1
- **No synchrony required**: Works in fully asynchronous system
- **Randomization evidence**: Common coin, leader election lottery

**Evidence Requirements**:
- **Random oracle** or **verifiable random function** (VRF)
- **Cryptographic commitments** to prevent bias
- **Proof of randomness** φ_rand

**Composition Rule**:
```
G_FLP_Floor
  + RandomnessEvidence(φ_rand)
  → G_FLP_Probabilistic
```

**Termination Bound**: Expected number of rounds finite, but no worst-case bound

### 2.3 CAP-Consistent Systems (CP)

**Impossibility Statement**: During a network partition, cannot provide both:
- **Consistency** (all nodes see same data)
- **Availability** (all requests receive responses)

**CP Choice**: Prioritize consistency; sacrifice availability during partitions.

#### CAP-CP Target Vector (No Partition)

```
G_CAP_CP_Target = ⟨
  Scope: Global,
  Order: SS,
  Visibility: SER,
  Recency: Fresh(φ),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Strict serializable**: Global total order with real-time constraints
- **Serializable visibility**: Linearizable reads and writes
- **Fresh recency**: Always return latest committed value

**Evidence Requirements**:
- **No partition evidence**: QuorumConnectivity
- **Majority quorum** reachable
- **Leader lease** valid
- **Commit certificates** from quorum

**Availability Guarantee**: **Yes** (when no partition)

#### CAP-CP Degraded Vector (During Partition, Majority Side)

```
G_CAP_CP_Degraded_Majority = ⟨
  Scope: Global,
  Order: SS,
  Visibility: SER,
  Recency: Fresh(φ),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Same strong guarantees** maintained
- **Availability**: Yes (majority can proceed)
- **Evidence**: PartitionEvidence + MajorityQuorumEvidence

**Minority Side Behavior**:
```
G_CAP_CP_Degraded_Minority = ⟨
  Scope: Local,
  Order: None,
  Visibility: Fractured,
  Recency: EO,
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Blocked writes**: Cannot commit
- **Stale reads**: May serve stale data (bounded by last known commit)
- **Availability Guarantee**: **None** (fail closed)

**Evidence Requirements**:
- **Partition evidence** (strong)
- **Minority quorum evidence** (insufficient for commits)

#### CAP-CP Recovery Vector (Partition Healing)

```
G_CAP_CP_Recovery = ⟨
  Scope: Global,
  Order: SS,
  Visibility: SER,
  Recency: BS(δ_heal),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Bounded staleness during catchup**: Minority must sync
- **Availability**: Partial (majority continues; minority catches up)

**Evidence Requirements**:
- **Partition healing evidence** (sustained connectivity)
- **Sync completion evidence** (minority caught up)
- **Lease renewal evidence** (new epoch)

**Upgrade Path**:
```
G_CAP_CP_Degraded_Minority
  + PartitionHealingEvidence
  + SyncCompletionEvidence
  → G_CAP_CP_Recovery
  → G_CAP_CP_Target
```

### 2.4 CAP-Available Systems (AP)

**AP Choice**: Prioritize availability; accept temporary inconsistency during partitions.

#### CAP-AP Target Vector (No Partition)

```
G_CAP_AP_Target = ⟨
  Scope: Global,
  Order: Causal,
  Visibility: RA,
  Recency: Fresh(φ) or BS(δ_small),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Causal consistency**: Respects causality but allows concurrent divergence
- **Read-atomic**: Consistent prefix reads
- **Fresh or bounded staleness**: Tunable based on replication lag

**Evidence Requirements**:
- **Vector clocks** or **version vectors** for causal order
- **Replication lag measurements** for BS(δ)
- **Optional quorum reads** for Fresh(φ)

**Availability Guarantee**: **Yes** (all nodes can serve)

#### CAP-AP Degraded Vector (During Partition)

```
G_CAP_AP_Degraded = ⟨
  Scope: Local,
  Order: Causal (per-partition),
  Visibility: Fractured,
  Recency: EO (diverging),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Local scope**: Each partition operates independently
- **Fractured visibility**: Different partitions see different states
- **Eventual recency**: Unbounded divergence during partition
- **Availability Guarantee**: **Yes** (all partitions accept writes)

**Evidence Requirements**:
- **Partition evidence** (any level)
- **Local commit evidence** (per-partition)
- **Conflict tracking evidence** (version vectors, last-write-wins timestamps)

**Conflict Semantics**:
- **Detect**: Version vectors reveal concurrent updates
- **Resolve**: LWW, CRDTs, application-level resolution
- **Evidence of resolution**: Merge commits with proof of resolution strategy

#### CAP-AP Recovery Vector (Partition Healing)

```
G_CAP_AP_Recovery = ⟨
  Scope: Global,
  Order: Causal,
  Visibility: RA (converging),
  Recency: BS(δ_converge),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Convergence in progress**: Replicas exchanging updates
- **Bounded staleness decreasing**: δ_converge → 0
- **Conflict resolution active**: Merges happening

**Evidence Requirements**:
- **Partition healing evidence**
- **Anti-entropy progress evidence** (replicas synchronizing)
- **Conflict resolution evidence** (for divergent branches)
- **Convergence evidence** (all replicas reached same state)

**Upgrade Path**:
```
G_CAP_AP_Degraded
  + PartitionHealingEvidence
  + AntiEntropyEvidence
  → G_CAP_AP_Recovery
  → G_CAP_AP_Target
```

### 2.5 PACELC Systems (Context-Dependent)

**Impossibility Extension**: Even without partitions, must trade latency vs consistency.

**PACELC**:
- **If Partition**: Choose Availability or Consistency (like CAP)
- **Else** (no partition): Choose Latency or Consistency

#### PACELC-PC/EL Vector (Consistency-Preferred, Latency-Preferred)

**Mode**: PC (partition → consistency), EL (else → latency)

**Target Vector (No Partition)**:
```
G_PACELC_PC_EL_Target = ⟨
  Scope: Range,
  Order: Causal,
  Visibility: RA,
  Recency: BS(δ_tolerable),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Accept staleness for latency**: Serve from local replicas
- **Bounded staleness**: δ_tolerable configured
- **Fast reads**: No quorum required

**Evidence Requirements**:
- **Replication lag evidence**: δ_current ≤ δ_tolerable
- **No partition evidence**: Connectivity confirmed
- **Causal tracking**: Vector clocks or hybrid logical clocks

**During Partition**:
```
G_PACELC_PC_EL_Partition = ⟨
  Scope: Global (majority only),
  Order: Lx,
  Visibility: SER,
  Recency: Fresh(φ),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Sacrifice availability for consistency**: Minority blocked
- **Strong guarantees maintained**: Linearizability
- **Evidence**: PartitionEvidence + MajorityQuorumEvidence

#### PACELC-PA/EC Vector (Availability-Preferred, Consistency-Preferred)

**Mode**: PA (partition → availability), EC (else → consistency)

**Target Vector (No Partition)**:
```
G_PACELC_PA_EC_Target = ⟨
  Scope: Global,
  Order: SS,
  Visibility: SER,
  Recency: Fresh(φ),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Strong consistency when possible**: Linearizable
- **Pay latency cost**: Quorum reads/writes
- **Evidence**: QuorumCertificates + LeaseEvidence

**During Partition**:
```
G_PACELC_PA_EC_Partition = ⟨
  Scope: Local,
  Order: Causal,
  Visibility: Fractured,
  Recency: EO,
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Sacrifice consistency for availability**: Allow divergence
- **All partitions serve**: Full availability
- **Evidence**: PartitionEvidence + ConflictTrackingEvidence

#### PACELC-PA/EL Vector (Both Relaxed)

**Target Vector**:
```
G_PACELC_PA_EL_Target = ⟨
  Scope: Global,
  Order: Causal,
  Visibility: RA,
  Recency: EO,
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

**Characteristics**:
- **Maximum availability and performance**
- **Weakest consistency**: Eventual
- **Use case**: Caches, read-heavy workloads, CRDT-based systems

### 2.6 Guarantee Composition Under Impossibility

**Composition Operator**: meet(G1, G2) = weakest component-wise

**Rule 1: Partition Boundaries Force Downgrade**

```
G_CP_Strong ⊗[Partition] G_CP_Strong
  → G_CP_Minority (blocked) || G_CP_Majority (proceeding)

meet(G_CP_Minority, G_CP_Majority) = G_CP_Minority
```

**Rule 2: Cross-Partition Composition Requires Conflict Resolution**

```
G_AP_PartitionA ⊗[Healing] G_AP_PartitionB
  + ConflictResolutionEvidence
  → G_AP_Target
```

**Rule 3: FLP + CAP Composition**

```
G_FLP_Target (with ◊P) ⊗[Partition] G_FLP_Target
  → loses ◊P in minority
  → G_FLP_Floor (no termination guarantee)
```

**Rule 4: Evidence Loss Triggers Downgrade**

```
G_Strong - Evidence(φ) → G_Weak

// Example:
G_CAP_CP_Target - LeaderLeaseEvidence
  → G_CAP_CP_Degraded_Minority (blocked)
```

**Rule 5: Evidence Addition Enables Upgrade**

```
G_Weak + Evidence(φ) → G_Strong

// Example:
G_FLP_Floor + EventuallyPerfectEvidence
  → G_FLP_Target (termination guaranteed)
```

**Rule 6: Mode Transitivity**

```
if A.mode = Degraded then:
  (A ▷ B).mode = Degraded regardless of B.mode
```

**Rule 7: Impossibility Composition**

```
FLP_constraint ∧ CAP_constraint =
  (no_termination_without_FD) ∧ (no_CA_during_partition)

→ During partition:
  - CP: Minority has no termination (FLP) + no availability (CAP)
  - AP: All have termination (writes local) but no consistency (CAP)
```

## III. Context Capsules for Impossibility Results

Context capsules carry guarantees and the evidence that justifies them across boundaries. For impossibility results, capsules must carry:
- Which impossibility applies
- Current assumptions (synchrony, failures)
- Evidence of assumption violations
- Fallback behavior

### 3.1 Base Impossibility Capsule Structure

```
ImpossibilityCapsule {
  // Core capsule fields
  invariant: InvariantType,
  evidence: [EvidenceToken],
  boundary: BoundaryScope,
  mode: SystemMode,
  fallback: FallbackPolicy,

  // Impossibility-specific fields
  impossibility_context: {
    applicable_results: [ImpossibilityResult],
    current_assumptions: AssumptionSet,
    violation_evidence: [ViolationEvidence],
    circumvention_strategy: CircumventionStrategy,
    guarantee_vector: GuaranteeVector
  },

  // Lifecycle
  epoch: Epoch,
  valid_until: Timestamp,
  renewal_policy: RenewalPolicy
}
```

### 3.2 FLP Consensus Capsule

```
FLP_ConsensusCapsule {
  invariant: "Agreement on single value",

  evidence: [
    FailureDetectorEvidence(type: ◊P, confidence: 0.95),
    QuorumCertificate(term: 5, value: "commit", signatures: [s1, s2, s3]),
    LeaderLease(leader: p1, epoch: 5, expires_at: t + 10s)
  ],

  boundary: "Replica group R1",
  mode: "Target",

  fallback: {
    on_evidence_loss: {
      action: "Downgrade to Floor",
      behavior: "Accept proposals but do not guarantee termination",
      guarantee_vector: G_FLP_Floor
    },
    on_quorum_loss: {
      action: "Block writes",
      behavior: "Cannot make progress without majority",
      guarantee_vector: ⟨Global, None, Fractured, EO, Idem(K), Auth(π)⟩
    }
  },

  impossibility_context: {
    applicable_results: ["FLP85"],

    current_assumptions: {
      system_model: "Partially Synchronous",
      failure_model: "Crash failures, up to f = 1 of n = 3",
      synchrony_bound: "GST exists but unknown",
      failure_detector: "◊P (eventually perfect)"
    },

    violation_evidence: [
      // Currently empty—operating within assumptions
    ],

    circumvention_strategy: {
      mechanism: "Leader-based consensus with ◊P",
      termination_condition: "Stable leader after GST",
      liveness_guarantee: "Eventual (dependent on ◊P stability)",
      safety_guarantee: "Always (agreement, validity, integrity)"
    },

    guarantee_vector: G_FLP_Target
  },

  epoch: 5,
  valid_until: "t + 10s (lease expiration)",
  renewal_policy: "Leader extends lease before expiration"
}
```

**Capsule Operations**:

**restrict()**: Narrow to specific value decided
```
restrict(FLP_ConsensusCapsule, value: "commit") → {
  boundary: "Value 'commit' agreed",
  guarantee_vector: G_FLP_Target,  // unchanged
  evidence: [QuorumCertificate(value: "commit")]  // proof of decision
}
```

**degrade()**: Loss of failure detector evidence
```
degrade(FLP_ConsensusCapsule, lost_evidence: FailureDetectorEvidence) → {
  mode: "Floor",
  guarantee_vector: G_FLP_Floor,
  violation_evidence: [
    AsynchronyViolation(detection: "◊P timeout pattern unstable")
  ],
  fallback: "No termination guarantee; wait for evidence renewal"
}
```

**renew()**: Extend lease before expiration
```
renew(FLP_ConsensusCapsule) → {
  evidence: [
    FailureDetectorEvidence(type: ◊P, confidence: 0.97),  // refreshed
    LeaderLease(leader: p1, epoch: 5, expires_at: t + 20s)  // extended
  ],
  valid_until: "t + 20s"
}
```

### 3.3 CAP-Aware Capsule

```
CAP_Capsule {
  invariant: "Linearizability across replicas",

  evidence: [
    NoPartitionEvidence(quorum_reachable: true, confidence: 0.99),
    QuorumConnectivity(majority: [r1, r2, r3], minority: [r4, r5]),
    CommitCertificate(term: 8, index: 1523, signatures: [s1, s2, s3])
  ],

  boundary: "Replica set RS1, geographic distribution: [us-east, us-west, eu-west]",
  mode: "Target",

  fallback: {
    on_partition_detection: {
      majority_side: {
        action: "Continue with CP guarantees",
        guarantee_vector: G_CAP_CP_Degraded_Majority
      },
      minority_side: {
        action: "Block writes, serve stale reads with staleness labels",
        guarantee_vector: G_CAP_CP_Degraded_Minority
      }
    }
  },

  impossibility_context: {
    applicable_results: ["CAP"],

    current_assumptions: {
      system_model: "Distributed replicas across WAN",
      failure_model: "Network partitions possible, no Byzantine faults",
      partition_detection: "Quorum-based, timeout-driven",
      consistency_choice: "CP (consistency prioritized)"
    },

    violation_evidence: [
      // Currently none—no partition detected
    ],

    circumvention_strategy: {
      mechanism: "Majority quorum for consistency",
      partition_behavior: "Minority blocks to preserve consistency",
      availability_guarantee: "Majority partition only",
      consistency_guarantee: "Always linearizable in majority"
    },

    guarantee_vector: G_CAP_CP_Target
  },

  epoch: 8,
  valid_until: "Until partition detected or epoch change",
  renewal_policy: "Continuous connectivity monitoring"
}
```

**Capsule Operations**:

**degrade() on partition**:
```
// Minority side
degrade(CAP_Capsule, partition_evidence: PartitionEvidence(minority: [r4, r5])) → {
  mode: "Degraded_Minority",
  guarantee_vector: G_CAP_CP_Degraded_Minority,
  violation_evidence: [
    PartitionEvidence(
      unreachable: [r1, r2, r3],
      detected_at: t1,
      confidence: 0.95
    )
  ],
  fallback: "Block all writes; serve reads with staleness warning"
}

// Majority side
degrade(CAP_Capsule, partition_evidence: PartitionEvidence(majority: [r1, r2, r3])) → {
  mode: "Degraded_Majority",
  guarantee_vector: G_CAP_CP_Degraded_Majority,  // same strong guarantees
  violation_evidence: [
    PartitionEvidence(
      unreachable: [r4, r5],
      detected_at: t1,
      confidence: 0.95
    )
  ],
  fallback: "Continue normal operation with reduced replica set"
}
```

**extend() on healing**:
```
extend(CAP_Capsule_Minority, healing_evidence: PartitionHealingEvidence) → {
  mode: "Recovery",
  guarantee_vector: G_CAP_CP_Recovery,
  evidence: [
    PartitionHealingEvidence(
      reachable: [r1, r2, r3],
      sustained_connectivity: "5 minutes",
      confidence: 0.98
    ),
    SyncInProgressEvidence(
      missing_commits: [1524..1750],
      sync_rate: "1000 commits/sec",
      estimated_completion: "t + 30s"
    )
  ],
  fallback: "Continue recovery; resume Target mode after sync complete"
}
```

### 3.4 Lower Bound Capsule (Communication Complexity)

Some impossibility results concern communication complexity, not just feasibility.

```
LowerBound_Capsule {
  invariant: "Byzantine agreement with f faults",

  evidence: [
    RoundCertificate(round: 3, phase: "Commit", signatures: [s1..s7]),
    MessageComplexityProof(messages_sent: 42, expected_minimum: 28)
  ],

  boundary: "Byzantine consensus group, n=10, f=3",
  mode: "Target",

  fallback: {
    on_round_timeout: {
      action: "Retry round with view change",
      guarantee_vector: "Same (safety always, liveness eventual)"
    }
  },

  impossibility_context: {
    applicable_results: [
      "Dolev-Strong lower bound: Ω(f+1) rounds",
      "Byzantine broadcast lower bound: Ω(n²) messages"
    ],

    current_assumptions: {
      system_model: "Synchronous or partially synchronous",
      failure_model: "Byzantine failures, f < n/3",
      adversary: "Computationally bounded, cannot forge signatures",
      communication: "Authenticated point-to-point channels"
    },

    violation_evidence: [
      // None—complexity bounds are mathematical, not violated in practice
    ],

    circumvention_strategy: {
      mechanism: "PBFT-style consensus with prepared/commit phases",
      round_complexity: "f+1 rounds (matches lower bound)",
      message_complexity: "O(n²) (matches lower bound for all-to-all)",
      optimizations: [
        "Threshold signatures reduce to O(n) messages",
        "View change adds complexity but preserves safety"
      ]
    },

    guarantee_vector: ⟨
      Scope: Global,
      Order: SS,
      Visibility: SER,
      Recency: Fresh(φ),
      Idempotence: Idem(K),
      Auth: Auth(π)
    ⟩
  },

  epoch: 3,
  valid_until: "Until epoch change or view change",
  renewal_policy: "Leader rotates on timeout"
}
```

### 3.5 Capsule Composition Example

**Scenario**: Client request crosses FLP-respecting consensus layer, then CAP-aware replication layer.

```
Client_Request {
  operation: "Write(key: user:42, value: {name: 'Alice', balance: 1000})"
}

// Step 1: Enter consensus layer
Capsule_1_Consensus = FLP_ConsensusCapsule {
  invariant: "Agreement on operation order",
  guarantee_vector: G_FLP_Target,
  evidence: [◊P_Evidence, LeaderLease, QuorumCert]
}

// Step 2: Consensus decides → produces commit certificate
Capsule_2_Commit = restrict(Capsule_1_Consensus, decision: "Commit at index 1234") {
  invariant: "Operation ordered at index 1234",
  guarantee_vector: G_FLP_Target,  // still strong
  evidence: [CommitCertificate(index: 1234, value: Write(...), signatures: [...])]
}

// Step 3: Cross boundary to replication layer
Capsule_3_Replication = rebind(Capsule_2_Commit, new_boundary: "Replication to regions") {
  invariant: "Replicate committed operation",
  guarantee_vector: meet(G_FLP_Target, G_CAP_CP_Target) = G_CAP_CP_Target,
  evidence: [
    CommitCertificate(index: 1234, ...),
    NoPartitionEvidence(all_regions_reachable)
  ]
}

// Step 4: Partition detected during replication
Capsule_4_Degraded = degrade(Capsule_3_Replication, PartitionEvidence) {
  invariant: "Replicate committed operation (best effort)",
  guarantee_vector: G_CAP_CP_Degraded_Majority,  // minority blocked
  evidence: [
    CommitCertificate(index: 1234, ...),
    PartitionEvidence(minority: [region:eu-west])
  ],
  fallback: "Majority regions (us-east, us-west) replicate; eu-west will sync on healing"
}

// Step 5: Return to client
Client_Response {
  status: "Committed",
  guarantee: "Linearizable write committed to majority; eu-west region currently unreachable and will sync asynchronously",
  capsule: Capsule_4_Degraded  // client can inspect degradation
}
```

**Composition Guarantee**:
```
Final_Guarantee = meet(
  G_FLP_Target,         // consensus
  G_CAP_CP_Target,      // replication (normal)
  G_CAP_CP_Degraded_Majority  // partition handling
) = G_CAP_CP_Degraded_Majority

= ⟨
  Scope: Global (majority only),
  Order: SS,
  Visibility: SER,
  Recency: Fresh(φ),
  Idempotence: Idem(K),
  Auth: Auth(π)
⟩
```

## IV. Mode Matrix Under Impossibility Results

Modes define system behavior under different conditions. Impossibility results manifest as mode transitions.

### 4.1 Mode Definitions (Review)

- **FLOOR**: Minimum viable correctness (never lie; may be partial)
- **TARGET**: Normal operation (primary guarantees)
- **DEGRADED**: Reduced guarantees, labeled and principled
- **RECOVERY**: Restricted actions until proofs re-established

### 4.2 FLP-Respecting System Modes

#### FLOOR Mode: Asynchronous Safety-Only

**Preserved Invariants**:
- Agreement: If two processes decide, they decide the same value
- Validity: If all propose the same value, that value is decided
- Integrity: Each process decides at most once

**Allowed Operations**:
- Propose value
- Receive proposals from others
- Execute consensus rounds
- **Cannot guarantee**: Termination

**Evidence Requirements**: None (operates without failure detection)

**Guarantee Vector**: G_FLP_Floor

**Entry Trigger**:
- Loss of failure detector evidence (◊P unstable)
- Synchrony violations exceed threshold
- Explicit fallback to asynchronous model

**Exit Trigger**:
- Failure detector evidence stabilizes
- Synchrony bounds observable for sufficient duration

**User-Visible Contract**:
- "Writes may never complete if failures occur"
- "Reads reflect only committed values (may be empty)"
- "No time bound on any operation"

#### TARGET Mode: Consensus with ◊P

**Preserved Invariants**:
- All FLOOR invariants (agreement, validity, integrity)
- **Plus**: Termination (eventual, after GST)

**Allowed Operations**:
- All FLOOR operations
- **Plus**: Guaranteed decision after GST

**Evidence Requirements**:
- ◊P failure detector evidence (stable heartbeats)
- Leader lease (for leader-based protocols)
- Quorum certificates (for commit proofs)

**Guarantee Vector**: G_FLP_Target

**Entry Trigger**:
- ◊P evidence stable for threshold duration
- Leader elected and lease obtained
- Quorum reachable

**Exit Trigger**:
- Loss of ◊P stability
- Leader lease expiration without renewal
- Quorum loss

**User-Visible Contract**:
- "Writes will eventually complete (no time bound, but eventual)"
- "Reads reflect latest committed value"
- "System guarantees progress after stabilization period"

#### DEGRADED Mode: Split Brain Risk

**Preserved Invariants**:
- Integrity (still at most one decision per process)
- **Weakened**: Agreement (may have multiple tentative values)

**Allowed Operations**:
- Local proposals (not globally committed)
- Speculative execution
- Conflict tracking

**Evidence Requirements**:
- Partition evidence or ◊P instability
- Conflict detection mechanism active

**Guarantee Vector**: G_FLP_Floor but with fractured visibility

**Entry Trigger**:
- Partition detected and no clear majority
- Prolonged ◊P instability (livelock detected)

**Exit Trigger**:
- Partition heals
- Clear majority emerges

**User-Visible Contract**:
- "Writes are speculative and may be rolled back"
- "Reads may reflect non-committed values (labeled as tentative)"
- "Conflicts will be resolved on recovery"

#### RECOVERY Mode: Reconciliation

**Preserved Invariants**:
- Agreement (reconciling to single truth)
- Integrity (no duplicate decisions)

**Allowed Operations**:
- Conflict resolution
- State synchronization
- Checkpoint verification

**Evidence Requirements**:
- Partition healing evidence
- Quorum reachability evidence
- Sync completion evidence

**Guarantee Vector**: G_FLP_Target (being restored)

**Entry Trigger**:
- DEGRADED mode + partition healing evidence

**Exit Trigger**:
- All replicas synchronized
- No conflicting tentative values remain
- Leader election complete

**User-Visible Contract**:
- "System is reconciling after partition"
- "New writes blocked until recovery complete"
- "Reads reflect pre-partition committed state"

### 4.3 CAP-CP System Modes

#### FLOOR Mode: Read-Only

**Preserved Invariants**:
- Consistency: All reads return last known committed value
- Integrity: No writes accepted (cannot ensure consistency)

**Allowed Operations**:
- Read last committed state
- Serve bounded-stale data with explicit staleness labels

**Evidence Requirements**:
- Last known commit certificate
- Staleness bound evidence (time since last commit)

**Guarantee Vector**:
```
⟨Global (stale), SS (for committed), SER, BS(δ_unbounded), Idem(K), Auth(π)⟩
```

**Entry Trigger**:
- Cannot reach majority quorum
- Partition detected and in minority side

**Exit Trigger**:
- Quorum restored
- Partition healed

**User-Visible Contract**:
- "Read-only mode: Writes rejected"
- "Reads may be stale (staleness: up to partition duration)"
- "Data consistent but not fresh"

#### TARGET Mode: Linearizable Read-Write

**Preserved Invariants**:
- Linearizability (global total order)
- Consistency (all nodes agree)
- Freshness (reads return latest committed)

**Allowed Operations**:
- Linearizable reads and writes
- Quorum-based commits

**Evidence Requirements**:
- No partition evidence
- Majority quorum reachable
- Leader lease valid
- Commit certificates

**Guarantee Vector**: G_CAP_CP_Target

**Entry Trigger**:
- System initialized or recovered
- No partition evidence
- Quorum available

**Exit Trigger**:
- Partition detected
- Quorum lost

**User-Visible Contract**:
- "Full read-write access"
- "All operations linearizable"
- "Reads always fresh"

#### DEGRADED Mode (Majority): Continued Operation

**Preserved Invariants**:
- All TARGET invariants (linearizability, consistency, freshness)

**Allowed Operations**:
- All TARGET operations

**Evidence Requirements**:
- Partition evidence (minority unreachable)
- Majority quorum evidence
- Continued leader lease

**Guarantee Vector**: G_CAP_CP_Degraded_Majority (same as TARGET)

**Entry Trigger**:
- Partition detected and in majority side

**Exit Trigger**:
- Partition healed

**User-Visible Contract**:
- "Operating with reduced replica count"
- "All guarantees maintained"
- "Minority replicas will sync on reconnection"

#### DEGRADED Mode (Minority): Blocked

**Preserved Invariants**:
- Integrity (no inconsistent writes)

**Allowed Operations**:
- Stale reads with staleness labels
- **No writes**

**Evidence Requirements**:
- Partition evidence (majority unreachable)
- Last known commit certificate

**Guarantee Vector**: G_CAP_CP_Degraded_Minority (blocked)

**Entry Trigger**:
- Partition detected and in minority side

**Exit Trigger**:
- Partition healed

**User-Visible Contract**:
- "Minority partition: Write operations unavailable"
- "Reads serve last known consistent state (stale)"
- "Waiting for partition to heal"

#### RECOVERY Mode: Synchronization

**Preserved Invariants**:
- Consistency (being restored)
- Integrity (no duplicate commits)

**Allowed Operations**:
- State transfer from majority
- Checkpoint validation
- Replay missing commits

**Evidence Requirements**:
- Partition healing evidence
- Sync in progress evidence
- Commit sequence from majority

**Guarantee Vector**: G_CAP_CP_Recovery

**Entry Trigger**:
- DEGRADED (minority) + partition healing evidence

**Exit Trigger**:
- Sync complete
- All missing commits applied
- Checkpoint verified

**User-Visible Contract**:
- "Rejoining cluster after partition"
- "Writes continue to majority; minority catching up"
- "Will resume full participation after sync complete"

### 4.4 CAP-AP System Modes

#### FLOOR Mode: Local-Only

**Preserved Invariants**:
- Causal consistency (local)
- Integrity (local commits valid)

**Allowed Operations**:
- Local reads and writes
- Causal ordering maintained locally

**Evidence Requirements**:
- Local commit log
- Vector clock or causal timestamp

**Guarantee Vector**:
```
⟨Local, Causal, RA, EO (local only), Idem(K), Auth(π)⟩
```

**Entry Trigger**:
- All remote replicas unreachable

**Exit Trigger**:
- Any remote replica reachable

**User-Visible Contract**:
- "Operating in isolation"
- "Writes committed locally only"
- "Conflicts likely on reconnection"

#### TARGET Mode: Eventually Consistent

**Preserved Invariants**:
- Causal consistency (global)
- Eventual convergence

**Allowed Operations**:
- Reads and writes on any replica
- Anti-entropy (background sync)

**Evidence Requirements**:
- Replication lag evidence (bounded)
- Vector clock comparisons
- No partition evidence

**Guarantee Vector**: G_CAP_AP_Target

**Entry Trigger**:
- System initialized
- No partitions
- Replication lag within bounds

**Exit Trigger**:
- Partition detected

**User-Visible Contract**:
- "Full availability"
- "Reads may be slightly stale (bounded)"
- "Writes always accepted"

#### DEGRADED Mode: Partitioned

**Preserved Invariants**:
- Local causal consistency (per partition)
- Integrity (local)

**Allowed Operations**:
- All operations (reads and writes)
- Conflict tracking active

**Evidence Requirements**:
- Partition evidence
- Local commit evidence
- Version vector for conflict detection

**Guarantee Vector**: G_CAP_AP_Degraded

**Entry Trigger**:
- Partition detected

**Exit Trigger**:
- Partition healed

**User-Visible Contract**:
- "Partitioned: All replicas accept writes"
- "Conflicts possible and will be resolved on reconnection"
- "Reads reflect local state only"

#### RECOVERY Mode: Convergence

**Preserved Invariants**:
- Eventual consistency (being restored)
- Conflict resolution (in progress)

**Allowed Operations**:
- Anti-entropy exchanges
- Conflict resolution
- Reads and writes continue

**Evidence Requirements**:
- Partition healing evidence
- Anti-entropy progress evidence
- Conflict resolution evidence

**Guarantee Vector**: G_CAP_AP_Recovery

**Entry Trigger**:
- DEGRADED mode + partition healing evidence

**Exit Trigger**:
- All replicas converged
- No outstanding conflicts

**User-Visible Contract**:
- "Reconnected: Synchronizing state"
- "Conflicts being resolved (may see resolution artifacts)"
- "Full consistency being restored"

### 4.5 Mode Transition Matrix

```
         │ FLOOR │ TARGET │ DEGRADED │ RECOVERY │
─────────┼───────┼────────┼──────────┼──────────┤
FLP-     │       │        │          │          │
Aware    │ Start │ ◊P     │ ◊P Lost  │ ◊P       │
         │       │ Stable │ Partition│ Restored │
─────────┼───────┼────────┼──────────┼──────────┤
CAP-CP   │ Init  │ Quorum │ Partition│ Healing  │
(Maj)    │       │ Avail  │ (Maj)    │ Complete │
─────────┼───────┼────────┼──────────┼──────────┤
CAP-CP   │ Quorum│ N/A    │ Partition│ Healing  │
(Min)    │ Lost  │        │ (Min)    │ Sync Done│
─────────┼───────┼────────┼──────────┼──────────┤
CAP-AP   │ Full  │ No     │ Partition│ Healing  │
         │ Isol. │ Part.  │ Detected │ Converged│
─────────┴───────┴────────┴──────────┴──────────┘

Transitions triggered by evidence changes.
```

## V. Evidence Lifecycle

Every piece of evidence follows a lifecycle. Impossibility results affect how evidence is generated, validated, and renewed.

### 5.1 Lifecycle State Machine

```
┌─────────────┐
│  Generated  │ ← Evidence produced by mechanism
└──────┬──────┘
       │
       ↓ Verification
┌─────────────┐
│  Validated  │ ← Evidence checked for correctness
└──────┬──────┘
       │
       ↓ Propagation
┌─────────────┐
│   Active    │ ← Evidence in use for decisions
└──────┬──────┘
       │
       ↓ Time / Epoch / Condition
┌─────────────┐
│  Expiring   │ ← Evidence approaching end of validity
└──────┬──────┘
       │
       ↓ Renewal attempt
       ├──→ Renewed → back to Validated
       │
       ↓ Expiration
┌─────────────┐
│   Expired   │ ← Evidence no longer valid
└──────┬──────┘
       │
       ↓ Optional
┌─────────────┐
│   Revoked   │ ← Evidence explicitly invalidated
└─────────────┘
```

### 5.2 Failure Detector Evidence Lifecycle

#### Generation: Detecting Failures

**Perfect Detector (P)**:
```
generate_P_Evidence(process: ProcessID) → PerfectFailureEvidence {
  // Requires: Synchronous system, known timeout bound Δ
  wait(Δ)  // bounded delay
  if no_message_from(process) within Δ:
    evidence = PerfectFailureEvidence {
      failed_process: process,
      detection_time: now(),
      detector: self,
      mechanism: "Timeout with proven bound Δ",
      epoch: current_epoch()
    }
    return evidence
  else:
    return None  // process alive
}
```

**Eventually Perfect Detector (◊P)**:
```
generate_◊P_Evidence(process: ProcessID) → EventuallyPerfectEvidence {
  // Requires: Partial synchrony, adaptive timeout
  timeout = initial_timeout
  suspicion_count = 0

  loop:
    wait(timeout)
    if no_message_from(process):
      suspicion_count++
      timeout *= backoff_factor  // adaptive increase

      evidence = EventuallyPerfectEvidence {
        suspected_process: process,
        suspicion_version: suspicion_count,
        confidence: confidence(suspicion_count, timeout),
        stability_flag: (timeout > stability_threshold),
        detector: self,
        epoch: current_epoch()
      }

      publish(evidence)
    else:
      suspicion_count = max(0, suspicion_count - recovery_rate)
      timeout = max(min_timeout, timeout / recovery_factor)

  // Eventually after GST, suspicions stabilize
}
```

#### Validation: Checking Evidence

```
validate_failure_evidence(evidence: FailureEvidence) → Boolean {
  // Check epoch
  if evidence.epoch != current_epoch():
    return False  // stale evidence

  // Check signature / authentication
  if not verify_signature(evidence.attestation, evidence.detector):
    return False  // forged evidence

  // Check detector authority
  if not is_authorized_detector(evidence.detector):
    return False  // unauthorized detector

  // For ◊P, check confidence threshold
  if evidence.type == "◊P":
    if evidence.confidence < min_confidence_threshold:
      return False  // insufficient confidence

  // Check against own observations
  if independently_observed(evidence.failed_process):
    evidence.confidence += corroboration_boost

  return True
}
```

#### Active: Using Evidence for Decisions

```
decide_with_evidence(evidence: FailureEvidence) → Decision {
  if not validate_failure_evidence(evidence):
    return Decision.Abort

  // Remove failed process from quorum
  active_quorum = original_quorum - {evidence.failed_process}

  // Recalculate majority
  if size(active_quorum) < majority_threshold:
    return Decision.EnterFloorMode  // cannot make progress

  // Proceed with reduced quorum
  if evidence.type == "P":
    // Perfect detection → can definitely exclude
    exclude_permanently(evidence.failed_process)
  else if evidence.type == "◊P":
    // Eventually perfect → exclude but prepare for retraction
    exclude_tentatively(evidence.failed_process, evidence.suspicion_version)

  return Decision.Proceed(active_quorum)
}
```

#### Expiring: Evidence Approaching End of Life

```
check_expiring(evidence: FailureEvidence) → ExpirationState {
  // Epoch-based expiration
  if evidence.epoch < current_epoch() - epoch_tolerance:
    return ExpirationState.Expired

  // For ◊P, check if suspicion retracted
  if evidence.type == "◊P":
    if received_message_from(evidence.suspected_process):
      return ExpirationState.Retracted

  // For P, permanent unless epoch changes
  if evidence.type == "P":
    return ExpirationState.Permanent

  // Warning state: approaching expiration
  if evidence.epoch < current_epoch():
    return ExpirationState.Expiring

  return ExpirationState.Active
}
```

#### Renewal: Refreshing Evidence

```
renew_failure_evidence(old_evidence: FailureEvidence) → Option<FailureEvidence> {
  // For ◊P, re-detect
  if old_evidence.type == "◊P":
    if still_no_messages_from(old_evidence.suspected_process):
      new_evidence = generate_◊P_Evidence(old_evidence.suspected_process)
      new_evidence.suspicion_version = old_evidence.suspicion_version + 1
      return Some(new_evidence)
    else:
      // Suspicion retracted
      return None

  // For P, check if still crashed
  if old_evidence.type == "P":
    if still_crashed(old_evidence.failed_process):
      // Refresh with new epoch
      new_evidence = old_evidence
      new_evidence.epoch = current_epoch()
      return Some(new_evidence)
    else:
      // Process recovered (unusual in crash-stop model)
      return None

  return None
}
```

### 5.3 Partition Evidence Lifecycle

#### Generation: Detecting Partitions

```
generate_partition_evidence() → PartitionEvidence {
  // Probe all known processes
  connectivity_probes = []

  for peer in all_peers:
    probe_result = probe_connectivity(peer)
    connectivity_probes.append(probe_result)

  // Identify unreachable set
  unreachable = [p for p in all_peers if probe_result(p).failed]
  reachable = [p for p in all_peers if not probe_result(p).failed]

  // Determine confidence
  if size(unreachable) == 0:
    return None  // no partition

  // Aggregate evidence from reachable peers
  peer_evidence = gather_evidence_from(reachable)

  // Calculate confidence based on agreement
  agreement_ratio = count_agreeing_peers(peer_evidence, unreachable) / size(reachable)

  evidence = PartitionEvidence {
    partition_id: generate_partition_id(unreachable),
    detected_by: self,
    detection_time: now(),
    unreachable_processes: unreachable,
    reachable_processes: reachable,
    evidence_sources: connectivity_probes,
    confidence: confidence_from_agreement(agreement_ratio),
    epoch: current_epoch()
  }

  return evidence
}
```

#### Validation: Confirming Partition

```
validate_partition_evidence(evidence: PartitionEvidence) → Boolean {
  // Check epoch
  if evidence.epoch != current_epoch():
    return False

  // Check that detector is reachable
  if evidence.detected_by not in evidence.reachable_processes:
    return False  // inconsistent evidence

  // Check partition consistency
  if intersection(evidence.reachable_processes, evidence.unreachable_processes):
    return False  // overlapping sets

  // Verify with own probes
  own_probes = [probe_connectivity(p) for p in evidence.unreachable_processes]
  own_unreachable = [p for p in evidence.unreachable_processes if own_probes[p].failed]

  overlap_ratio = size(intersection(own_unreachable, evidence.unreachable_processes)) / size(evidence.unreachable_processes)

  if overlap_ratio < min_overlap_threshold:
    return False  // insufficient corroboration

  return True
}
```

#### Active: Operating Under Partition

```
operate_under_partition(evidence: PartitionEvidence) → OperationMode {
  // Determine which side of partition
  if self in evidence.reachable_processes:
    my_partition = evidence.reachable_processes
    other_partition = evidence.unreachable_processes
  else:
    // Shouldn't happen, but handle gracefully
    my_partition = [self]
    other_partition = all_peers - [self]

  // Calculate quorum implications
  if size(my_partition) >= majority_threshold:
    // Majority partition
    mode = OperationMode.CAP_CP_Majority
    action = "Continue with CP guarantees"
  else:
    // Minority partition
    mode = OperationMode.CAP_CP_Minority
    action = "Block writes, serve stale reads"

  // Update guarantee vector
  update_guarantee_vector_for_mode(mode)

  // Set expiration: re-check partition status frequently
  schedule_partition_recheck(interval: partition_recheck_interval)

  return mode
}
```

#### Expiring: Partition Healing Detected

```
detect_partition_healing(evidence: PartitionEvidence) → Option<PartitionHealingEvidence> {
  // Probe previously unreachable processes
  healing_probes = [probe_connectivity(p) for p in evidence.unreachable_processes]

  newly_reachable = [p for p in evidence.unreachable_processes if healing_probes[p].success]

  if size(newly_reachable) == 0:
    return None  // partition still active

  // Check sustained connectivity
  if not sustained_connectivity(newly_reachable, duration: healing_confirmation_duration):
    return None  // transient connectivity, not healed

  // Generate healing evidence
  healing_evidence = PartitionHealingEvidence {
    healed_partition_id: evidence.partition_id,
    newly_reachable: newly_reachable,
    detection_time: now(),
    sustained_connectivity_duration: healing_confirmation_duration,
    confidence: high,
    epoch: current_epoch()
  }

  return Some(healing_evidence)
}
```

#### Renewal: Post-Healing Convergence

```
enter_recovery_mode(partition_evidence: PartitionEvidence, healing_evidence: PartitionHealingEvidence) → RecoveryProcess {
  // Determine what needs to sync
  if was_majority_partition():
    // Other side needs to catch up
    missing_commits = identify_missing_commits(healing_evidence.newly_reachable)
    sync_direction = "Push to minority"
  else:
    // We need to catch up
    missing_commits = identify_missing_commits_from_majority()
    sync_direction = "Pull from majority"

  // Initiate sync
  recovery = RecoveryProcess {
    mode: RecoveryMode.Synchronization,
    sync_direction: sync_direction,
    missing_commits: missing_commits,
    target_nodes: healing_evidence.newly_reachable,
    start_time: now(),
    estimated_completion: estimate_sync_time(missing_commits)
  }

  // Track sync progress
  monitor_sync_progress(recovery)

  // Upon completion, transition to Target mode
  on_sync_complete(recovery):
    transition_to_target_mode()
    invalidate(partition_evidence)
    invalidate(healing_evidence)

  return recovery
}
```

### 5.4 Synchrony Bound Evidence Lifecycle

#### Generation: Measuring Bounds

```
generate_synchrony_evidence() → SynchronyEvidence {
  // Measure message delays
  delay_samples = []
  for i in 1..sample_size:
    sent_time = now()
    send_message(probe: "latency_check", to: random_peer())
    received_time = wait_for_response()
    delay = received_time - sent_time
    delay_samples.append(delay)

  // Statistical analysis
  mean_delay = mean(delay_samples)
  max_delay = max(delay_samples)
  p99_delay = percentile(delay_samples, 99)

  // Check against assumed bounds
  violations = [d for d in delay_samples if d > assumed_bound]
  violation_rate = len(violations) / len(delay_samples)

  evidence = SynchronyEvidence {
    measurement_window: (start_time, end_time),
    sample_size: len(delay_samples),
    mean_delay: mean_delay,
    max_delay: max_delay,
    p99_delay: p99_delay,
    assumed_bound: assumed_bound,
    violations: violations,
    violation_rate: violation_rate,
    confidence: confidence_from_samples(sample_size),
    epoch: current_epoch()
  }

  return evidence
}
```

#### Validation: Assessing Synchrony Assumptions

```
validate_synchrony(evidence: SynchronyEvidence) → SynchronyAssessment {
  if evidence.violation_rate == 0:
    return SynchronyAssessment {
      status: "Synchronous",
      recommendation: "Can use P (perfect failure detector)",
      guarantee_upgrade: G_FLP_Target
    }

  if evidence.violation_rate < eventual_threshold:
    return SynchronyAssessment {
      status: "Eventually Synchronous",
      recommendation: "Use ◊P (eventually perfect failure detector)",
      guarantee_upgrade: G_FLP_Target (eventual)
    }

  if evidence.violation_rate < partial_threshold:
    return SynchronyAssessment {
      status: "Partially Synchronous",
      recommendation: "Use adaptive timeouts, expect delays",
      guarantee_upgrade: G_FLP_Floor with probabilistic termination
    }

  return SynchronyAssessment {
    status: "Asynchronous",
    recommendation: "Cannot rely on timeouts; use randomization or weaker model",
    guarantee_upgrade: None (remain in G_FLP_Floor)
  }
}
```

#### Active: Adapting to Synchrony

```
adapt_to_synchrony(evidence: SynchronyEvidence) → AdaptationStrategy {
  // Adjust timeouts based on observed delays
  new_timeout = evidence.p99_delay * safety_margin

  // If timeouts increasing, reduce load
  if new_timeout > current_timeout * threshold:
    strategy = AdaptationStrategy {
      action: "Reduce load",
      new_timeout: new_timeout,
      backpressure: enabled,
      guarantee_vector: G_FLP_Floor  // degrade to safety-only
    }

  // If stable, increase confidence in termination
  if evidence.violation_rate == 0 for duration > stability_duration:
    strategy = AdaptationStrategy {
      action: "Increase confidence",
      new_timeout: new_timeout,
      guarantee_vector: G_FLP_Target,  // upgrade to eventual termination
      failure_detector: "◊P (stable)"
    }

  return strategy
}
```

#### Expiring: Synchrony Degradation

```
detect_synchrony_degradation(evidence_history: [SynchronyEvidence]) -> Option<DegradationEvidence> {
  // Compare recent to historical
  recent_violations = mean([e.violation_rate for e in evidence_history[-10:]])
  historical_violations = mean([e.violation_rate for e in evidence_history[:-10]])

  if recent_violations > historical_violations * degradation_threshold:
    degradation = DegradationEvidence {
      detected_at: now(),
      recent_violation_rate: recent_violations,
      historical_violation_rate: historical_violations,
      severity: calculate_severity(recent_violations),
      recommendation: "Degrade guarantees to Floor mode"
    }
    return Some(degradation)

  return None
}
```

#### Renewal: Restoring Synchrony Confidence

```
restore_synchrony_confidence(degradation: DegradationEvidence) -> Option<RestorationEvidence> {
  // Monitor for improvement
  while true:
    current_evidence = generate_synchrony_evidence()

    if current_evidence.violation_rate < restoration_threshold:
      sustained_count++
    else:
      sustained_count = 0

    if sustained_count >= required_sustained_periods:
      restoration = RestorationEvidence {
        restored_at: now(),
        final_violation_rate: current_evidence.violation_rate,
        sustained_periods: sustained_count,
        recommendation: "Restore Target mode guarantees"
      }
      return Some(restoration)

    wait(monitoring_interval)
}
```

## VI. Calculus Principles

The evidence calculus governs how evidence composes, weakens, and enables circumvention of impossibility results.

### 6.1 Composition of Impossibilities

**Principle**: When multiple impossibility results apply, evidence requirements are the **union** of individual requirements.

#### FLP + CAP Composition

```
FLP_Evidence_Requirements = {◊P or P or Randomness}
CAP_Evidence_Requirements = {PartitionEvidence → (MajorityQuorum or ConflictResolution)}

Combined_Requirements = {
  (◊P or P or Randomness) AND
  (if PartitionEvidence then (MajorityQuorum or ConflictResolution))
}
```

**Scenarios**:

**Scenario 1: No Partition, Partial Synchrony**
```
Evidence Available:
  - ◊P (eventually perfect failure detector)
  - No partition evidence
  - Majority quorum reachable

Guarantees Achievable:
  - FLP: Eventual termination (via ◊P)
  - CAP: Strong consistency (no partition, majority available)

Result: G_FLP_Target ∩ G_CAP_CP_Target = G_CAP_CP_Target (strongest)
```

**Scenario 2: Partition, Majority Side, Partial Synchrony**
```
Evidence Available:
  - ◊P (within majority partition)
  - Partition evidence (minority unreachable)
  - Majority quorum reachable

Guarantees Achievable:
  - FLP: Eventual termination (via ◊P in majority)
  - CAP: Strong consistency (majority can proceed)

Result: G_FLP_Target ∩ G_CAP_CP_Degraded_Majority = G_CAP_CP_Degraded_Majority
```

**Scenario 3: Partition, Minority Side, Partial Synchrony**
```
Evidence Available:
  - ◊P (but minority, insufficient)
  - Partition evidence (majority unreachable)
  - Minority quorum (insufficient)

Guarantees Achievable:
  - FLP: No termination (no majority for quorum)
  - CAP: No consistency or availability (minority blocked)

Result: G_FLP_Floor ∩ G_CAP_CP_Degraded_Minority = Blocked (safety only, no progress)
```

**Scenario 4: Partition, AP System, Asynchronous**
```
Evidence Available:
  - No failure detector (asynchronous)
  - Partition evidence
  - Local commits only

Guarantees Achievable:
  - FLP: No termination guarantee
  - CAP: Availability (all partitions accept writes), no consistency

Result: G_FLP_Floor ∩ G_CAP_AP_Degraded = Local causal consistency, eventual convergence
```

#### FLP + Byzantine Fault Tolerance (BFT)

```
FLP_Requirements = {◊P or P or Randomness}
BFT_Requirements = {n ≥ 3f+1, QuorumCertificates with 2f+1 signatures}

Combined_Requirements = {
  (◊P or P or Randomness) AND
  (n ≥ 3f+1) AND
  (QuorumCertificates with 2f+1 signatures)
}
```

**Implications**:
- Need **both** eventual synchrony (for termination) **and** large quorum (for Byzantine resilience)
- Partition to minority < 2f+1 → cannot proceed (safety preserved)
- Partition to majority ≥ 2f+1 → can proceed if ◊P within majority

### 6.2 Weakening Strategies and Their Evidence

**Principle**: Relaxing impossibility constraints requires explicit evidence that justifies the relaxation.

#### Weakening FLP: From Termination to Probabilistic Termination

**Original Constraint**: Termination impossible in asynchronous systems with crashes
**Weakening**: Accept probabilistic termination (probability 1, but unbounded expected time)

**Evidence Required**:
- **Randomness Evidence**: VRF, common coin, cryptographic beacon
- **Cryptographic Commitments**: Prevent bias or manipulation
- **Fairness Proof**: Show all processes have equal chance

**Guarantee Transformation**:
```
G_FLP_Floor (no termination)
  + RandomnessEvidence
  → G_FLP_Probabilistic (terminates with probability 1)
```

**Use Cases**: HoneyBadgerBFT, probabilistic consensus algorithms

#### Weakening CAP: From Linearizability to Bounded Staleness

**Original Constraint**: Cannot have both consistency and availability during partition
**Weakening**: Accept bounded staleness instead of linearizability

**Evidence Required**:
- **Staleness Bound Evidence**: δ_max measured and enforced
- **Clock Synchronization Evidence**: Bounded clock drift
- **Replication Lag Evidence**: Actual staleness ≤ δ_max

**Guarantee Transformation**:
```
G_CAP_CP_Target (linearizable)
  - PartitionEvidence
  + BoundedStalenessEvidence(δ)
  → G_CAP_CP_Target (bounded stale, but available)
```

**Use Cases**: CRAQ with δ-bounded staleness, timeline consistency

#### Weakening Consensus: From SS to SI

**Original Constraint**: Strict serializability requires global total order
**Weakening**: Accept snapshot isolation (concurrent transactions may not conflict)

**Evidence Required**:
- **Snapshot Evidence**: Consistent read timestamp
- **Write-Write Conflict Detection**: Track concurrent writes to same keys
- **Commit Timestamp Evidence**: Assign non-overlapping commit timestamps

**Guarantee Transformation**:
```
G_CAP_CP_Target (SS: strict serializable)
  - GlobalOrderEvidence
  + SnapshotTimestampEvidence
  → G_Relaxed (SI: snapshot isolation)

Visibility: SER → SI
Order: SS → Lx (per-object)
```

**Use Cases**: Spanner read-only transactions, PostgreSQL SI

### 6.3 Probabilistic Evidence vs Deterministic

**Deterministic Evidence**: Provides certainty (within a model)
- Perfect failure detector P: **Certain** that process crashed
- Quorum certificate: **Certain** that majority agreed
- Leader lease: **Certain** that leader is unique (within epoch)

**Probabilistic Evidence**: Provides high confidence, not certainty
- Eventually perfect detector ◊P: **Eventual** certainty (after GST)
- Timeout: **Likely** indicates failure (but could be slow)
- Statistical synchrony bounds: **Probable** that delays are bounded

#### Calculus for Probabilistic Evidence

**Confidence Accumulation**:
```
Confidence(E1 AND E2) = min(Confidence(E1), Confidence(E2))  // weakest link
Confidence(E1 OR E2) = max(Confidence(E1), Confidence(E2))   // best evidence

Confidence(E over time) = f(observations, consistency, recency)
```

**Example: Building ◊P from Timeouts**:
```
Single_Timeout_Confidence = 0.6  // ambiguous
Quorum_Timeout_Confidence (3 of 5 agree) = 0.85  // stronger
Sustained_Timeout_Confidence (10 consecutive) = 0.95  // eventual accuracy

◊P_Confidence = combine(
  Quorum_Timeout_Confidence,
  Sustained_Timeout_Confidence,
  Historical_Accuracy
) → approaches 1.0 after GST
```

**Using Probabilistic Evidence**:
- **Accept**: If confidence above threshold, proceed
- **Reject**: If confidence below threshold, use weaker model
- **Hedge**: Use probabilistic guarantees (expected-case, not worst-case)

**Composition Rule**:
```
Deterministic_Evidence ⊗ Probabilistic_Evidence → Probabilistic_Result

// Example:
QuorumCertificate (deterministic) ⊗ ◊P (probabilistic)
  → Eventual_Termination (probabilistic liveness, deterministic safety)
```

### 6.4 Evidence-Based Circumvention of Impossibility

**Principle**: Impossibility results define what **cannot** be achieved **without assumptions**. Evidence embodies assumptions, enabling circumvention.

#### Circumventing FLP

**Impossibility**: Consensus impossible in asynchronous systems with crashes
**Circumvention Strategy**: Introduce synchrony or randomness assumptions

**Strategy 1: Partial Synchrony + ◊P**
```
Assumption: GST (Global Stabilization Time) exists
Evidence: ◊P (eventually perfect failure detector)

Mechanism:
  - Use ◊P to exclude crashed processes
  - After GST, ◊P stabilizes → progress guaranteed
  - Before GST, safety maintained (no incorrect decisions)

Guarantee: Eventual termination (probabilistic before GST, certain after)
```

**Strategy 2: Randomization**
```
Assumption: Common coin / random oracle available
Evidence: Verifiable Random Function (VRF) outputs

Mechanism:
  - Use randomness to break symmetry in leader election
  - Expected number of rounds finite
  - No dependence on synchrony

Guarantee: Termination with probability 1 (expected finite time)
```

**Strategy 3: Synchronous Model**
```
Assumption: Known message delay bound Δ
Evidence: P (perfect failure detector based on timeout Δ)

Mechanism:
  - Use P to deterministically detect crashes
  - Progress guaranteed in finite rounds (f+1 rounds)

Guarantee: Deterministic termination
```

#### Circumventing CAP

**Impossibility**: Cannot have consistency and availability during partition
**Circumvention Strategy**: Detect partition, choose one side, or weaken consistency

**Strategy 1: CP (Consistency-Preferring)**
```
Assumption: Partition detection possible
Evidence: PartitionEvidence + MajorityQuorumEvidence

Mechanism:
  - Detect partition
  - Majority side proceeds with strong consistency
  - Minority side blocks (sacrifices availability)

Guarantee: Linearizability maintained in majority, no availability in minority
```

**Strategy 2: AP (Availability-Preferring)**
```
Assumption: Conflict resolution mechanism exists
Evidence: VersionVectorEvidence + ConflictResolutionEvidence

Mechanism:
  - All partitions accept writes (availability)
  - Track conflicts with version vectors
  - Resolve conflicts on healing (e.g., LWW, CRDTs)

Guarantee: Availability always, eventual consistency after healing
```

**Strategy 3: Hybrid (PACELC)**
```
Assumption: Context-dependent choice
Evidence: PartitionEvidence + WorkloadEvidence

Mechanism:
  - If partition: choose CP or AP based on workload
  - If no partition: choose latency vs consistency based on SLA

Guarantee: Tunable per-operation or per-workload
```

#### Circumventing Communication Lower Bounds

**Impossibility**: Byzantine consensus requires Ω(n²) messages (worst case)
**Circumvention Strategy**: Use cryptographic techniques to reduce message complexity

**Strategy 1: Threshold Signatures**
```
Assumption: Threshold cryptography available
Evidence: ThresholdSignatureEvidence

Mechanism:
  - Each process signs individually
  - Aggregate into single threshold signature (O(1) size)
  - Broadcast aggregate instead of individual signatures
  - Message complexity: O(n) instead of O(n²)

Guarantee: Same security, lower communication (average case)
```

**Strategy 2: Trusted Hardware (TEE)**
```
Assumption: Trusted Execution Environment (TEE) available
Evidence: AttestationEvidence from TEE

Mechanism:
  - TEE acts as trusted component (reduces f)
  - Can reduce from n ≥ 3f+1 to n ≥ 2f+1
  - Lower message complexity

Guarantee: Security dependent on TEE trust assumptions
```

### 6.5 Evidence Algebra

**Definition**: Operations on evidence tokens that preserve or weaken guarantees.

#### Evidence Operations

**Conjunction (AND)**: Both pieces of evidence required
```
E1 ∧ E2 = Evidence requiring both E1 and E2

Guarantee(E1 ∧ E2) = min(Guarantee(E1), Guarantee(E2))  // weakest
Confidence(E1 ∧ E2) = min(Confidence(E1), Confidence(E2))
```

**Disjunction (OR)**: Either piece of evidence sufficient
```
E1 ∨ E2 = Evidence from either E1 or E2

Guarantee(E1 ∨ E2) = max(Guarantee(E1), Guarantee(E2))  // strongest available
Confidence(E1 ∨ E2) = max(Confidence(E1), Confidence(E2))
```

**Implication (→)**: E1 produces E2
```
E1 → E2 = If E1 present, then E2 derivable

Example: QuorumCertificate → CommitDecision
```

**Negation (¬)**: Absence of evidence
```
¬E = Evidence that E is absent

Example: ¬PartitionEvidence = NoPartitionEvidence
Note: Absence of evidence is not evidence of absence (in general)
       But can be evidence of absence if expected to be present
```

**Temporal (⋄, □)**: Eventually or always
```
⋄E = Eventually E will be present (liveness)
□E = E always present (safety)

Example: ◊P provides ⋄(Stability) → ⋄(Termination)
```

#### Derivation Rules

**Rule 1: Evidence Strengthening**
```
Weak_Evidence + Additional_Corroboration → Strong_Evidence

Example:
  Timeout (weak) + Quorum_Agreement → ◊P (stronger)
  ◊P (eventual) + Stability_Duration → P (strongest)
```

**Rule 2: Evidence Weakening**
```
Strong_Evidence - Corroboration → Weak_Evidence

Example:
  P (perfect) - Synchrony_Assumption → ◊P (eventual)
  ◊P (eventual) - Quorum → Timeout (ambiguous)
```

**Rule 3: Evidence Transitivity**
```
If E1 → E2 and E2 → E3, then E1 → E3

Example:
  QuorumCertificate → CommitDecision → Durability
  Therefore: QuorumCertificate → Durability
```

**Rule 4: Evidence Expiration**
```
Evidence(t) + Time(Δ) → Evidence(t+Δ) only if renewable

Example:
  LeaderLease(t, duration: 10s) at t=0
    → valid until t=10s
    → must renew before expiration to maintain validity
```

#### Example: FLP Circumvention Algebra

```
// Goal: Achieve consensus (Agreement ∧ Validity ∧ Integrity ∧ Termination)

// Safety properties (always achievable in FLP)
Safety = Agreement ∧ Validity ∧ Integrity
Safety_Evidence = Protocol_Correctness_Proof  // mathematical

// Liveness property (termination) requires additional evidence
Liveness = Termination
Liveness_Evidence = ◊P ∨ Randomness ∨ P

// Full consensus
Consensus = Safety ∧ Liveness
Consensus_Evidence = Safety_Evidence ∧ Liveness_Evidence
                   = Protocol_Correctness_Proof ∧ (◊P ∨ Randomness ∨ P)

// Without Liveness_Evidence
Consensus_Evidence - Liveness_Evidence = Safety_Evidence (FLP Floor)

// With ◊P
Consensus_Evidence + ◊P_Evidence
  = Safety_Evidence ∧ ◊P_Evidence
  → Eventual_Termination (FLP Target)
```

#### Example: CAP Circumvention Algebra

```
// Goal: Consistency ∧ Availability (during partition)

// CAP states this is impossible
Consistency ∧ Availability | Partition = ⊥ (impossible)

// Strategy: Choose one or weaken
CP_Choice = Consistency ∧ ¬Availability | Partition
  Evidence = PartitionEvidence ∧ MajorityQuorumEvidence
  Result = Linearizability (majority), Blocked (minority)

AP_Choice = ¬Consistency ∧ Availability | Partition
  Evidence = PartitionEvidence ∧ ConflictTrackingEvidence
  Result = Eventual_Consistency, Full_Availability

// Weakening: Bounded staleness instead of linearizability
Weakened_Choice = Bounded_Consistency ∧ Availability | Partition
  Evidence = PartitionEvidence ∧ StalenessEvidenc(δ)
  Result = Bounded_Staleness(δ), Full_Availability
```

## VII. Practical Implications and Operator Mental Model

### 7.1 Evidence-Driven Operations

**Principle**: Operators should think in terms of evidence, not just symptoms.

**Traditional Debugging**:
- "Writes are slow" → increase timeout
- "Reads are stale" → add more replicas
- "Consensus stuck" → restart processes

**Evidence-Driven Debugging**:
- "Writes are slow" → Check: Do we have fresh leader lease evidence? Quorum reachable? Synchrony violations?
- "Reads are stale" → Check: Replication lag evidence? Partition evidence? Staleness bounds?
- "Consensus stuck" → Check: Failure detector evidence? Quorum evidence? Liveness evidence?

### 7.2 Diagnostic Questions

**For FLP-Related Issues**:
- Q: "Is consensus making progress?"
  - Check: ◊P evidence present? Confidence level? Stability flag?
  - Check: Quorum reachable? Leader lease valid?
  - Action: If ◊P unstable, increase timeouts; if quorum lost, restore connectivity

**For CAP-Related Issues**:
- Q: "Why are writes blocked?"
  - Check: Partition evidence? Minority side?
  - Action: If minority, wait for healing or promote to majority (dangerous!)
  - Check: Are we in CP mode? Should we switch to AP for availability?

**For Synchrony Issues**:
- Q: "Why are operations timing out?"
  - Check: Synchrony violation evidence? Frequency?
  - Action: If frequent violations, degrade to Floor mode; if rare, increase margin
  - Check: Load issues? Network issues? Clock drift?

### 7.3 Evidence Dashboards

**Recommended Metrics**:

```
FLP Evidence Panel:
  - Failure Detector Type: {None, W, S, ◊P, P}
  - Confidence: 0.0 to 1.0
  - Stability Flag: {Unstable, Stabilizing, Stable}
  - Current Mode: {Floor, Target, Degraded, Recovery}
  - Suspicion Churn Rate: suspicions/minute
  - Guarantee Vector: Display current G

CAP Evidence Panel:
  - Partition Evidence: {None, Weak, Strong}
  - Partition Topology: Visual of reachable/unreachable
  - Quorum Status: {Minority, Majority, Full}
  - Current Mode: {Target, Degraded_Majority, Degraded_Minority, Recovery}
  - Healing Progress: If in recovery, % complete
  - Guarantee Vector: Display current G

Synchrony Evidence Panel:
  - Message Delay: Mean, P50, P99, Max
  - Synchrony Bound: Configured vs Observed
  - Violation Rate: % of messages exceeding bound
  - Synchrony Assessment: {Synchronous, Eventually, Partially, Asynchronous}
  - Recommended Action: Text guidance

Evidence Lifecycle Panel:
  - Evidence Types: List of active evidence tokens
  - Expiring Soon: Evidence approaching expiration
  - Recently Expired: Evidence that expired (last hour)
  - Renewal Status: Evidence renewal success/failure rate
```

### 7.4 Runbook Patterns

**Pattern 1: Evidence Loss → Degrade**
```
Trigger: LeaderLease expired without renewal
Evidence: LeaseExpirationEvidence

Actions:
  1. Check: Is leader still reachable? (Probe leader)
  2. If unreachable:
     - Transition to Floor mode (safety-only)
     - Initiate leader election
     - Block new writes
  3. If reachable but lease not renewed:
     - Check clock skew
     - Check network latency
     - Extend lease if possible
  4. Communicate degradation to clients (downgrade guarantee vector)
```

**Pattern 2: Partition Detected → CP Decision**
```
Trigger: PartitionEvidence with confidence > 0.9

Actions:
  1. Determine partition side: Majority or Minority?
  2. If Majority:
     - Continue normal operation (Target mode)
     - Log minority replicas as unreachable
     - Prepare for eventual healing (track missing commits)
  3. If Minority:
     - Transition to Degraded_Minority mode
     - Block writes immediately
     - Serve reads with staleness warnings
     - Wait for partition healing evidence
  4. Monitor partition status continuously
```

**Pattern 3: Partition Healing → Recovery**
```
Trigger: PartitionHealingEvidence sustained for 5 minutes

Actions:
  1. Confirm healing: Probe all previously unreachable replicas
  2. Identify divergence:
     - Compare commit logs
     - Identify conflicting writes (shouldn't exist in CP, but check)
  3. Initiate sync:
     - Push missing commits to minority replicas
     - Verify checksums and integrity
  4. Monitor sync progress:
     - Track bytes transferred, commits applied
  5. Upon completion:
     - Verify all replicas converged
     - Transition minority replicas to Target mode
     - Resume normal operation
```

**Pattern 4: Synchrony Degradation → Adaptive Timeout**
```
Trigger: SynchronyViolationEvidence rate > 5%

Actions:
  1. Measure current latency distribution (P99, Max)
  2. Calculate new timeout: P99 * safety_margin (e.g., 2x)
  3. Update timeout configuration dynamically
  4. Assess impact:
     - If violations decrease, maintain new timeout
     - If violations persist, consider degrading to Floor mode
  5. Investigate root cause:
     - Network congestion? Load spike? Failing hardware?
     - Address underlying issue if possible
  6. Monitor for improvement:
     - When violation rate < 1% sustained, gradually reduce timeout
```

## VIII. Conclusion: Impossibility as Evidence Requirements

Impossibility results are not barriers—they are **specifications for evidence requirements**. Each impossibility defines:

1. **What cannot be achieved** without assumptions
2. **What evidence embodies** those assumptions
3. **How to detect** when assumptions are violated
4. **How to degrade** guarantees when evidence is lost
5. **How to recover** when evidence is restored

### The Evidence-Centric Worldview

```
Traditional View:
  "We can't have consensus in async systems." (Blocked)

Evidence View:
  "Consensus requires failure detection evidence.
   In async systems, no deterministic failure detection exists.
   Therefore: provide ◊P evidence (partial synchrony) or randomness evidence.
   With evidence: consensus achievable with eventual termination.
   Without evidence: safety maintained, liveness not guaranteed."
```

### Design Implications

**1. Make Evidence Explicit**:
- APIs should expose guarantee vectors and evidence
- Systems should track evidence lifecycle
- Operators should monitor evidence health

**2. Design for Evidence Loss**:
- Every strong guarantee should have a degradation path
- Evidence expiration should trigger explicit mode transitions
- Never silently weaken guarantees

**3. Compose with Evidence**:
- Context capsules carry evidence across boundaries
- Composition is a meet of guarantees (weakest wins)
- Upgrades require evidence; downgrades are explicit

**4. Operate on Evidence**:
- Dashboards show evidence, not just metrics
- Runbooks trigger on evidence changes, not just symptoms
- Debugging traces evidence flow

### The Impossibility Landscape

```
             ┌──────────────┐
             │ Synchronous  │
             │  (Known Δ)   │  ← P (perfect FD)
             │              │  ← Deterministic termination (f+1 rounds)
             └──────┬───────┘
                    │
                    ↓ Weaken synchrony
             ┌──────────────┐
             │   Partial    │
             │  Synchrony   │  ← ◊P (eventual FD)
             │ (Unknown GST)│  ← Eventual termination
             └──────┬───────┘
                    │
                    ↓ Further weaken
             ┌──────────────┐
             │ Asynchronous │
             │  (No bounds) │  ← No deterministic FD
             │              │  ← Randomization for termination
             └──────────────┘

         Consistency ←→ Availability (CAP)
             ↑              ↑
             │              │
    Partition Evidence ────┘
         │
         ├─ Majority → CP (strong consistency)
         └─ Minority → Blocked or AP (eventual consistency)

    Communication Complexity
         │
         ├─ Byzantine (f faults) → Ω(n²) messages, Ω(f+1) rounds
         ├─ Threshold Crypto → O(n) messages (average case)
         └─ TEE → Reduce n requirement
```

### Final Principle

**Every impossibility result is an evidence specification**:
- FLP → "Termination requires failure detection evidence"
- CAP → "Consistency + Availability requires partition absence evidence"
- Lower bounds → "Fast consensus requires either fewer faults or cryptographic evidence"

**Design insight**: Build systems that:
1. Generate the required evidence
2. Validate evidence continuously
3. Degrade gracefully when evidence is lost
4. Recover systematically when evidence is restored

This is the essence of the evidence calculus: **treating impossibility not as a wall, but as a contract we must satisfy with explicit, verifiable, lifecycle-managed evidence**.

---

**Word Count**: ~12,500 words

**Cross-References**:
- See Chapter 2 (State) for evidence in replication protocols
- See Chapter 3 (Time) for timestamp evidence and causality
- See Chapter 4 (Agreement) for consensus evidence in depth
- See Chapter 10 (Failures) for failure detector implementations
- See Chapter 11 (Composition) for capsule composition in practice
