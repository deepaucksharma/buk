# Chapter 4: Replication Guarantee Vectors
## How State Divergence Becomes Evidence-Based Convergence

---

## Introduction: Replication Through the G-Vector Lens

Replication is fundamentally about **managing state divergence** while providing useful guarantees. Every replication strategy makes different trade-offs, which we can now express precisely using guarantee vectors:

```
G = ⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩
```

This chapter shows how different replication strategies provide different evidence and thus different guarantees.

---

## 1. Primary-Backup Replication

### System Model
- One primary accepts writes
- Backups replicate from primary
- Reads can be served from primary or backups

### Guarantee Vector Analysis

#### Primary Writes
```python
G_primary = ⟨Global, Lx, SI, Fresh(lease), Idem(txn), Auth(cert)⟩
```
- **Scope**: Global (primary is single source of truth)
- **Order**: Linearizable (primary serializes all writes)
- **Visibility**: Snapshot Isolation (consistent snapshots)
- **Recency**: Fresh with lease evidence
- **Idempotence**: Transaction IDs ensure exactly-once
- **Auth**: Primary certificate proves authority

**Evidence Generated:**
```yaml
PrimaryLease:
  type: Recency
  scope: Cluster
  lifetime: 10 seconds
  binding: Primary node ID
  transitivity: No (backups cannot inherit)
  revocation: Lease timeout or explicit release
  cost: O(n) heartbeats/second
```

#### Backup Reads (Follower Reads)
```python
G_backup = ⟨Range, Causal, RA, BS(lag), Idem(txn), Auth(cert)⟩
```
- **Scope**: Range (subset of data on this backup)
- **Order**: Causal (preserves primary's order)
- **Visibility**: Read Atomic (may not see all writes)
- **Recency**: Bounded Staleness (replication lag)
- **Idempotence**: Inherited from primary
- **Auth**: Certificate chains to primary

**Evidence for Freshness:**
```yaml
ReplicationOffset:
  type: Order/Recency
  scope: This backup
  lifetime: Until next sync
  binding: Backup instance
  value: "Primary@LSN:4567, Backup@LSN:4565, Lag:2"

ClosedTimestamp:
  type: Recency
  scope: Range of keys
  lifetime: Until advanced
  binding: Timestamp T
  guarantee: "All writes ≤ T are visible"
```

### Composition: Client → Primary → Backup → Client

```python
def follower_read_composition():
    # Client request
    G_request = ⟨-, -, -, Fresh(required), -, -⟩

    # Primary state
    G_primary = ⟨Global, Lx, SI, Fresh(lease), Idem, Auth⟩

    # Replication to backup (asynchronous)
    G_replication = ⟨Range, Causal, RA, BS(2s), Idem, Auth⟩

    # Backup serves read
    G_backup = meet(G_primary, G_replication)
    # Result: ⟨Range, Causal, RA, BS(2s), Idem, Auth⟩

    # Client receives
    if G_backup.recency < G_request.recency:
        return "REJECT: Cannot guarantee freshness"
    else:
        return G_backup, "May be up to 2s stale"
```

### Mode Matrix for Primary-Backup

| Mode | Invariants | Evidence | Operations | G-Vector |
|------|------------|----------|------------|----------|
| **Target** | Consistency, Durability | Primary lease valid, Lag < 1s | All reads/writes | ⟨Global, Lx, SI, Fresh, Idem, Auth⟩ |
| **Degraded** | Durability | Primary lease valid, Lag > 1s | Writes to primary, No backup reads | ⟨Global, Lx, SI, BS(lag), Idem, Auth⟩ |
| **Floor** | Durability only | No primary lease | Read-only from backups | ⟨Range, Causal, RA, EO, Idem, Auth⟩ |
| **Recovery** | Durability | New primary election | Limited writes | ⟨Range, None, Fractured, None, None, Auth⟩ |

---

## 2. Chain Replication

### System Model
- Writes go to head, propagate down chain
- Reads from tail (always consistent)
- Strong consistency with good throughput

### Guarantee Vector Analysis

#### Write Path (Head → ... → Tail)
```python
G_write = ⟨Global, SS, SER, Fresh(ack), Idem(seq), Auth(chain)⟩
```
- **Order**: Strict Serializable (total order via head)
- **Visibility**: Serializable (tail sees all committed)
- **Recency**: Fresh when tail acknowledges

**Evidence Chain:**
```yaml
ChainPosition:
  type: Order
  value: "Head → Node2 → Node3 → Tail"

WriteToken:
  sequence: 12345
  propagation: [
    {node: Head, time: T0},
    {node: Node2, time: T0+10ms},
    {node: Node3, time: T0+20ms},
    {node: Tail, time: T0+30ms}
  ]
  commitment: "Tail ACK at T0+30ms"
```

#### Read Path (From Tail)
```python
G_read = ⟨Global, SS, SER, Fresh(tail), Idem(seq), Auth(chain)⟩
```
All reads see the same guarantees because tail has all committed writes.

### Chain Reconfiguration

When a node fails, the chain must reconfigure:

```python
def chain_reconfiguration(failed_node):
    if failed_node == "Head":
        # Promote second node
        G_during = ⟨Range, None, Fractured, None, None, Auth⟩
        # After promotion
        G_after = ⟨Global, SS, SER, Fresh, Idem, Auth⟩

    elif failed_node == "Middle":
        # Link around failed node
        G_during = ⟨Global, SS, SER, BS(timeout), Idem, Auth⟩
        # After bypass
        G_after = ⟨Global, SS, SER, Fresh, Idem, Auth⟩

    elif failed_node == "Tail":
        # Promote second-to-last
        G_during = ⟨Global, SS, SER, BS(catchup), Idem, Auth⟩
        # After promotion
        G_after = ⟨Global, SS, SER, Fresh, Idem, Auth⟩
```

---

## 3. Quorum-Based Replication

### System Model
- Writes require W nodes, reads require R nodes
- W + R > N ensures overlap
- Tunable consistency

### Guarantee Vector Analysis

#### Strict Quorum (W + R > N)
```python
G_strict = ⟨Global, Causal, RA, BS(clock_skew), Idem(K), Auth(quorum)⟩
```

**Evidence:**
```yaml
QuorumCertificate:
  write_quorum: 3/5 nodes
  read_quorum: 3/5 nodes
  overlap_guarantee: "At least 1 node has latest"
  version_vector: {A:5, B:5, C:4, D:3, E:5}
```

#### Eventual Consistency (W = 1, R = 1)
```python
G_eventual = ⟨Range, None, Fractured, EO, Idem(K), Auth(any)⟩
```

#### Tunable Configurations

```python
def quorum_guarantees(N, W, R):
    if W + R > N:
        # Strict quorum - overlap guaranteed
        return ⟨Global, Causal, RA, BS(δ), Idem, Auth⟩
    elif W > N/2:
        # Write quorum - no write conflicts
        return ⟨Global, Causal, Fractured, EO, Idem, Auth⟩
    elif R > N/2:
        # Read quorum - consistent reads
        return ⟨Global, None, RA, BS(δ), Idem, Auth⟩
    else:
        # No quorum - eventual only
        return ⟨Range, None, Fractured, EO, Idem, Auth⟩
```

### Read Repair Evidence

```yaml
ReadRepair:
  detected: "Version divergence on read"
  nodes: {A: v5, B: v3, C: v5}
  resolution: "Latest version v5 written back to B"
  evidence: {
    type: "Convergence",
    scope: "Key K",
    lifetime: "Until next write"
  }
```

---

## 4. State Machine Replication (Raft/Paxos)

### System Model
- Replicated log of commands
- Consensus on each entry
- Applied to identical state machines

### Guarantee Vector Analysis

```python
G_consensus = ⟨Global, Lx, SI, Fresh(lease), Idem(log), Auth(cert)⟩
```

**Complete Evidence Chain:**

```yaml
ConsensusEvidence:
  - LogEntry:
      index: 100
      term: 7
      command: "SET x=1"
      evidence: QuorumCertificate

  - CommitProof:
      type: Order/Commit
      committed_index: 100
      evidence: "Majority replicated"

  - LeaderLease:
      type: Recency
      leader: Node-1
      term: 7
      expires: T+10s

  - AppliedIndex:
      type: Order
      value: 99
      pending: [100]
```

### Composition Through State Machine

```python
def state_machine_composition():
    # Command arrives
    G_command = ⟨-, -, -, Fresh(required), -, -⟩

    # Consensus on log entry
    G_consensus = ⟨Global, Lx, SI, Fresh(lease), Idem(idx), Auth(cert)⟩

    # Application to state machine
    G_apply = ⟨Global, Lx, SI, Fresh(immediate), Idem(idx), Auth⟩

    # Client read
    if read_index ≤ applied_index:
        return G_apply  # Linearizable read
    else:
        return "NOT_YET_APPLIED"
```

---

## 5. Geo-Replication

### System Model
- Multiple regions
- Each region has local replicas
- Cross-region replication (asynchronous)

### Guarantee Vector by Scope

#### Local Region (Synchronous)
```python
G_local = ⟨Regional, SS, SER, Fresh(local), Idem, Auth(region)⟩
```

#### Remote Region (Asynchronous)
```python
G_remote = ⟨Regional, Causal, RA, BS(100ms), Idem, Auth(region)⟩
```

#### Global (After Convergence)
```python
G_global = ⟨Global, Causal, RA, EO, Idem, Auth(global)⟩
```

### Evidence for Geo-Replication

```yaml
RegionalCommit:
  region: US-East
  timestamp: T1
  durability: "3/3 replicas in region"

CrossRegionReplication:
  source: US-East
  destination: EU-West
  lag: 120ms
  applied_timestamp: T1 + 120ms

GlobalConvergence:
  regions: [US-East, US-West, EU-West, AP-Southeast]
  convergence_time: "~500ms"
  conflict_resolution: "Last-Write-Wins via HLC"
```

### Composition Across Regions

```python
def cross_region_write():
    # Write in US-East
    G_us = ⟨Regional, SS, SER, Fresh, Idem, Auth(US)⟩

    # Replicate to EU-West (async)
    G_replication = ⟨-, Causal, -, BS(120ms), -, -⟩

    # EU-West state
    G_eu = meet(G_us, G_replication)
    # Result: ⟨Regional, Causal, RA, BS(120ms), Idem, Auth(EU)⟩

    # Client in EU reads
    return G_eu, "May be 120ms behind US-East"
```

---

## 6. CRDT Replication (Convergent Replicated Data Types)

### System Model
- Conflict-free replicated data types
- Merge function guarantees convergence
- No coordination required

### Guarantee Vector Analysis

```python
G_crdt = ⟨Global, None, RA, EO, Idem(op), Auth(node)⟩
```
- **Order**: None (concurrent operations commute)
- **Visibility**: Read Atomic (see full state merges)
- **Recency**: Eventual (no bounds)
- **Idempotence**: Operation-based CRDTs are idempotent

### Evidence of Convergence

```yaml
CRDTMerge:
  type: "G-Counter"
  node_states: {
    A: {A:5, B:3, C:2},
    B: {A:4, B:4, C:2},
    C: {A:5, B:4, C:3}
  }
  merged_state: {A:5, B:4, C:3}  # Element-wise max
  convergence_proof: "Merge is commutative, associative, idempotent"
```

### CRDT Composition

```python
def crdt_composition():
    # Node A state
    G_A = ⟨Range, None, RA, EO, Idem, Auth(A)⟩

    # Node B state (concurrent)
    G_B = ⟨Range, None, RA, EO, Idem, Auth(B)⟩

    # Merge (no coordination!)
    G_merged = merge(G_A, G_B)  # NOT meet - merge!
    # Result: ⟨Global, None, RA, EO, Idem, Auth(AB)⟩

    # Key insight: Merge ≠ Meet
    # Merge combines states
    # Meet takes weakest guarantee
```

---

## 7. Master-Master Replication

### System Model
- Multiple masters accept writes
- Conflict resolution required
- Often uses vector clocks or MVCC

### Guarantee Vector Analysis

```python
G_master_master = ⟨Regional, None, Fractured, EO, Idem(vc), Auth(any)⟩
```

### Conflict Resolution Evidence

```yaml
ConflictDetection:
  type: "Vector Clock Comparison"
  object: Key_X
  versions: [
    {master: A, vclock: {A:5, B:2}, value: "v1"},
    {master: B, vclock: {A:3, B:4}, value: "v2"}
  ]
  relationship: "Concurrent (A:5,B:2) || (A:3,B:4)"

ConflictResolution:
  strategy: "Last-Write-Wins"
  winner: {master: A, timestamp: T2}
  evidence: "HLC timestamp comparison"
  client_visible: "Sibling versions available on request"
```

---

## Mode Transitions in Replication

### Unified Mode Matrix for All Replication Types

```python
class ReplicationModes:
    def __init__(self, replication_type):
        self.type = replication_type
        self.modes = {
            'floor': {
                'invariants': ['DURABILITY'],
                'evidence': ['Local persistence only'],
                'operations': ['Read local state'],
                'guarantee': ⟨Range, None, Fractured, None, None, Unauth⟩
            },
            'degraded': {
                'invariants': ['DURABILITY', 'CAUSALITY'],
                'evidence': ['Partial replication', 'Some nodes unreachable'],
                'operations': ['Restricted writes', 'Stale reads'],
                'guarantee': ⟨Range, Causal, RA, BS(unknown), Idem, Auth⟩
            },
            'target': {
                'invariants': ['ALL'],
                'evidence': self.get_target_evidence(),
                'operations': ['All'],
                'guarantee': self.get_target_guarantee()
            },
            'recovery': {
                'invariants': ['DURABILITY', 'MONOTONICITY'],
                'evidence': ['Catchup in progress', 'Reconciliation active'],
                'operations': ['Limited writes', 'Reads with warnings'],
                'guarantee': ⟨Range, None, Fractured, EO, None, Auth⟩
            }
        }

    def get_target_evidence(self):
        if self.type == "primary_backup":
            return ['Primary lease', 'Replication lag < 1s']
        elif self.type == "chain":
            return ['Chain intact', 'Tail responsive']
        elif self.type == "quorum":
            return ['W + R > N satisfied', 'Quorum reachable']
        elif self.type == "consensus":
            return ['Leader elected', 'Majority available']
        elif self.type == "crdt":
            return ['Merge function defined', 'Network connected']
```

---

## Transfer Tests

### Near Transfer: Replicated Cache
**Question**: How do guarantee vectors apply to a distributed cache with replication?

**Answer**:
```python
G_cache = ⟨Regional, None, RA, BS(TTL), Idem(key), Unauth⟩
```
- No ordering (cache updates are last-write-wins)
- Bounded staleness = TTL
- Evidence: TTL timestamps, invalidation messages

### Medium Transfer: Database Read Replicas
**Question**: How do cloud database read replicas compose with primary?

**Answer**:
Primary: `⟨Global, SS, SER, Fresh, Idem, Auth⟩`
Replica: `⟨Regional, Causal, RA, BS(lag), Idem, Auth⟩`
Composition: Application must handle staleness or pay latency cost for primary reads.

### Far Transfer: Document Collaboration
**Question**: How does Google Docs handle concurrent edits?

**Answer**:
Operational Transformation (OT) is essentially CRDT-like:
`G_docs = ⟨Global, None, RA, EO, Idem(op), Auth(user)⟩`
Evidence: Operation sequence numbers, transformation functions
Convergence: All users eventually see same document

---

## Key Insights

1. **Replication weakens guarantees**: Every replication hop potentially degrades the G-vector
2. **Evidence enables stronger guarantees**: Closed timestamps, quorum certificates, vector clocks
3. **Mode transitions are universal**: All replication systems have Floor/Degraded/Target/Recovery
4. **Composition requires explicit choice**: Accept degradation or pay for stronger evidence
5. **CRDTs avoid coordination**: By accepting `Order=None`, gain `Availability=Always`

---

## Summary: The Replication Spectrum

```
Strong Consistency          Weak Consistency
(Expensive, Coordinated) ←→ (Cheap, Uncoordinated)

Chain Replication          Primary-Backup         Quorum           CRDT
G=⟨Global,SS,SER,         G=⟨Global,Lx,SI,      G=⟨Global,       G=⟨Global,
   Fresh,Idem,Auth⟩          Fresh/BS,Idem,Auth⟩   Causal,RA,       None,RA,EO,
                                                    BS,Idem,Auth⟩    Idem,Auth⟩

Evidence Required:         Evidence Required:     Evidence:        Evidence:
- Chain integrity         - Primary lease        - Quorum cert    - Merge function
- Tail acknowledgment     - Replication offset   - Version vector - State vectors
- Total ordering          - Closed timestamp     - Read repair    - Convergence proof

Choose based on:
- Consistency requirements
- Latency tolerance
- Availability needs
- Operational complexity
```

This framework makes replication trade-offs explicit and evidence-based.