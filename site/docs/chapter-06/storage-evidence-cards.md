# Chapter 6: Storage System Evidence Cards
## From ACID to BASE to NewSQL: Evidence-Based Durability

---

## Introduction: Storage as Evidence Persistence

Storage systems are fundamentally **evidence persistence engines**. Every write generates evidence of durability, every read consumes evidence of existence, and every transaction creates evidence of consistency. This chapter catalogs the evidence types across the storage evolution.

---

## Part 1: ACID Storage Evidence

### Evidence Card: Two-Phase Commit (2PC) Certificate
```yaml
EVIDENCE CARD: Two-Phase Commit Certificate
═══════════════════════════════════════════════════════════
TYPE: Order/Commit
PROTOCOL: 2PC (ACID Transactions)

PROPERTIES:
- Scope: Transaction (all participants)
- Lifetime: Until transaction completes or aborts
- Binding: Transaction ID + Participants
- Transitivity: No (each participant votes independently)
- Revocation: Coordinator timeout or explicit abort
- Cost: O(2n) messages (prepare + commit), 2 RTT latency

LIFECYCLE:
Generated → Coordinator initiates with unique TxID
Validated → All participants vote "yes" (prepared)
Active → Coordinator decides "commit"
Expiring → Timeout approaching
Expired → Abort if any "no" vote or timeout

ENABLES:
- Atomic commitment across partitions
- Serializable isolation
- Distributed consistency

FAILURE MODES:
- Coordinator crash: Participants blocked
- Participant crash: Transaction must abort
- Network partition: May block indefinitely

CODE EXAMPLE:
class TwoPhaseCommit:
    def prepare_phase(self):
        prepare_cert = {
            'tx_id': uuid4(),
            'participants': ['DB1', 'DB2', 'DB3'],
            'votes': {},
            'timeout': time() + 30
        }
        for p in participants:
            vote = p.prepare(tx_id)
            prepare_cert['votes'][p] = vote

        if all(v == 'YES' for v in votes.values()):
            return self.commit_phase(prepare_cert)
        else:
            return self.abort_phase(prepare_cert)
```

### Evidence Card: Write-Ahead Log (WAL) Entry
```yaml
EVIDENCE CARD: Write-Ahead Log Entry
═══════════════════════════════════════════════════════════
TYPE: Durability/Order
PROTOCOL: ACID (Write-Ahead Logging)

PROPERTIES:
- Scope: Transaction operations
- Lifetime: Until checkpoint + archive period
- Binding: LSN (Log Sequence Number)
- Transitivity: Yes (recovery applies in order)
- Revocation: After checkpoint confirms durability
- Cost: Sequential write (fast), storage space

LIFECYCLE:
Generated → Before data page modification
Validated → Fsync to stable storage
Active → Enables transaction commit
Expiring → After checkpoint
Expired → Can be archived/deleted

ENABLES:
- Crash recovery
- Point-in-time recovery
- Replication via log shipping

FAILURE MODES:
- Log corruption: Database cannot start
- Log full: Writes blocked
- Missing segments: Recovery impossible

CODE EXAMPLE:
class WALEntry:
    def __init__(self, lsn, tx_id, operation):
        self.evidence = {
            'lsn': lsn,  # Monotonically increasing
            'tx_id': tx_id,
            'timestamp': time(),
            'operation': operation,
            'checksum': crc32(operation)
        }

    def persist(self):
        # Must fsync before acknowledging write
        self.file.write(serialize(self.evidence))
        self.file.flush()
        os.fsync(self.file.fileno())  # Durability evidence
```

### Evidence Card: MVCC Version Timestamp
```yaml
EVIDENCE CARD: MVCC Version Timestamp
═══════════════════════════════════════════════════════════
TYPE: Order/Visibility
PROTOCOL: Multi-Version Concurrency Control

PROPERTIES:
- Scope: Row version
- Lifetime: Until garbage collection
- Binding: Transaction timestamp
- Transitivity: No (each transaction decides visibility)
- Revocation: When no transaction needs version
- Cost: Extra storage per version

LIFECYCLE:
Generated → Transaction creates new version
Validated → Timestamp assigned at commit
Active → Version visible to appropriate transactions
Expiring → No active transaction needs it
Expired → Garbage collected

ENABLES:
- Snapshot isolation
- Read without locks
- Time-travel queries

FAILURE MODES:
- Version chain too long: Read performance degrades
- GC too aggressive: Needed version deleted
- GC too conservative: Storage bloat

CODE EXAMPLE:
class MVCCVersion:
    def __init__(self, row_id, tx_timestamp, data):
        self.evidence = {
            'row_id': row_id,
            'created_by_tx': tx_timestamp,
            'deleted_by_tx': None,  # Set when deleted
            'data': data,
            'next_version': None  # Version chain
        }

    def is_visible_to(self, reader_tx):
        return (self.created_by_tx <= reader_tx.snapshot_time and
                (self.deleted_by_tx is None or
                 self.deleted_by_tx > reader_tx.snapshot_time))
```

---

## Part 2: BASE Storage Evidence

### Evidence Card: Vector Clock
```yaml
EVIDENCE CARD: Vector Clock
═══════════════════════════════════════════════════════════
TYPE: Causality/Order
PROTOCOL: Dynamo-style Eventually Consistent Storage

PROPERTIES:
- Scope: Object/Key
- Lifetime: Indefinite (carried with object)
- Binding: Object version
- Transitivity: Yes (causality is transitive)
- Revocation: Never (immutable history)
- Cost: O(N) space per object (N = nodes)

LIFECYCLE:
Generated → On write, increment local component
Validated → On read, check for conflicts
Active → Determines causal order
Expiring → Never
Expired → Never (unless explicitly pruned)

ENABLES:
- Conflict detection
- Causal ordering
- Sibling detection

FAILURE MODES:
- Vector clock pruning: Lose conflict detection
- Clock drift: Incorrect causality
- Too many actors: Vector size explosion

CODE EXAMPLE:
class VectorClock:
    def __init__(self, node_id):
        self.clock = {}
        self.node_id = node_id

    def increment(self):
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1
        return self.clock.copy()

    def compare(self, other):
        # Returns: BEFORE, AFTER, CONCURRENT
        if all(self.clock.get(k, 0) <= other.clock.get(k, 0)
               for k in set(self.clock) | set(other.clock)):
            return 'BEFORE'
        elif all(self.clock.get(k, 0) >= other.clock.get(k, 0)
                 for k in set(self.clock) | set(other.clock)):
            return 'AFTER'
        else:
            return 'CONCURRENT'  # Conflict!
```

### Evidence Card: Hinted Handoff Token
```yaml
EVIDENCE CARD: Hinted Handoff Token
═══════════════════════════════════════════════════════════
TYPE: Durability/Availability
PROTOCOL: Dynamo/Cassandra

PROPERTIES:
- Scope: Write operation
- Lifetime: Until successful delivery
- Binding: Target node + hint holder
- Transitivity: No (specific to node pair)
- Revocation: After successful replay
- Cost: Extra storage, background bandwidth

LIFECYCLE:
Generated → Target node unavailable during write
Validated → Stored with hint metadata
Active → Enables write availability
Expiring → Periodic retry attempts
Expired → Delivered or TTL exceeded

ENABLES:
- Write availability during failures
- Eventual consistency
- Self-healing

FAILURE MODES:
- Hint overflow: Lost writes
- TTL expiry: Permanent inconsistency
- Hint node failure: Lost hints

CODE EXAMPLE:
class HintedHandoff:
    def __init__(self, target_node, key, value, timestamp):
        self.evidence = {
            'hint_id': uuid4(),
            'target_node': target_node,
            'key': key,
            'value': value,
            'timestamp': timestamp,
            'attempts': 0,
            'max_attempts': 10,
            'ttl': timestamp + 3600  # 1 hour
        }

    def should_retry(self):
        return (time() < self.ttl and
                self.attempts < self.max_attempts)

    def deliver(self):
        if self.target_node.write(self.key, self.value):
            self.mark_delivered()
            return True
        self.attempts += 1
        return False
```

### Evidence Card: Read Repair Certificate
```yaml
EVIDENCE CARD: Read Repair Certificate
═══════════════════════════════════════════════════════════
TYPE: Convergence
PROTOCOL: Eventually Consistent Storage

PROPERTIES:
- Scope: Single key
- Lifetime: Until next write
- Binding: Read coordinator
- Transitivity: No
- Revocation: Next write supersedes
- Cost: Extra read latency, write amplification

LIFECYCLE:
Generated → Inconsistency detected during read
Validated → Latest version determined
Active → Repair writes sent to stale replicas
Expiring → On successful repair
Expired → When all replicas consistent

ENABLES:
- Eventual consistency
- Self-healing reads
- Anti-entropy

FAILURE MODES:
- Repair storm: Too many repairs
- Incorrect resolution: Wrong version chosen
- Failed repair: Inconsistency persists

CODE EXAMPLE:
class ReadRepair:
    def execute_read(self, key, quorum_size):
        responses = self.read_from_replicas(key, quorum_size)

        if not self.all_versions_match(responses):
            repair_cert = {
                'key': key,
                'versions': responses,
                'winning_version': self.resolve_conflicts(responses),
                'stale_replicas': self.find_stale_replicas(responses),
                'timestamp': time()
            }

            # Repair in background
            for replica in repair_cert['stale_replicas']:
                replica.write(key, repair_cert['winning_version'])

            return repair_cert['winning_version'], repair_cert
```

---

## Part 3: NewSQL Evidence

### Evidence Card: Hybrid Logical Clock (HLC) Timestamp
```yaml
EVIDENCE CARD: Hybrid Logical Clock Timestamp
═══════════════════════════════════════════════════════════
TYPE: Order/Recency
PROTOCOL: Spanner/CockroachDB

PROPERTIES:
- Scope: Global
- Lifetime: Indefinite
- Binding: Transaction commit
- Transitivity: Yes (total order)
- Revocation: Never
- Cost: Clock sync overhead

LIFECYCLE:
Generated → At transaction commit
Validated → Checked against uncertainty window
Active → Orders all operations
Expiring → Never
Expired → Never

ENABLES:
- External consistency
- Global ordering
- Bounded staleness reads

FAILURE MODES:
- Clock skew: Uncertainty window grows
- Restart: Must wait for uncertainty
- NTP failure: System must pause

CODE EXAMPLE:
class HLCTimestamp:
    def __init__(self):
        self.physical = time()
        self.logical = 0
        self.max_offset = 500  # ms

    def generate_timestamp(self, received_ts=None):
        now = time()

        if received_ts:
            # Ensure happens-after relationship
            self.physical = max(now, received_ts.physical)
            if self.physical == received_ts.physical:
                self.logical = received_ts.logical + 1
            else:
                self.logical = 0
        else:
            self.physical = now
            self.logical = 0

        return HLCEvidence(self.physical, self.logical)
```

### Evidence Card: Paxos Commit Certificate
```yaml
EVIDENCE CARD: Paxos Commit Certificate (Spanner)
═══════════════════════════════════════════════════════════
TYPE: Commit/Agreement
PROTOCOL: Spanner/TrueTime

PROPERTIES:
- Scope: Transaction across shards
- Lifetime: Permanent
- Binding: Transaction ID + Timestamp
- Transitivity: Yes
- Revocation: Never
- Cost: Cross-region RTT

LIFECYCLE:
Generated → 2PC over Paxos groups
Validated → Majority in each group
Active → Transaction visible
Expiring → Never
Expired → Never

ENABLES:
- Globally consistent transactions
- Strict serializability
- External consistency

FAILURE MODES:
- Coordinator failure: Transaction stuck
- Paxos group unavailable: Cannot commit
- Time uncertainty: Must wait

CODE EXAMPLE:
class SpannerCommit:
    def commit_transaction(self, tx):
        # Phase 1: Prepare at all participants
        prepare_ts = TrueTime.now()

        prepare_certs = []
        for shard in tx.participants:
            cert = shard.paxos_prepare(tx.id, prepare_ts)
            prepare_certs.append(cert)

        if all(cert.success for cert in prepare_certs):
            # Phase 2: Commit with final timestamp
            commit_ts = max(prepare_ts, TrueTime.now())

            # Wait out uncertainty
            TrueTime.wait_until(commit_ts)

            commit_cert = {
                'tx_id': tx.id,
                'commit_ts': commit_ts,
                'participants': prepare_certs,
                'evidence_type': 'PAXOS_COMMIT'
            }

            for shard in tx.participants:
                shard.paxos_commit(commit_cert)

            return commit_cert
```

### Evidence Card: Range Lease
```yaml
EVIDENCE CARD: Range Lease (CockroachDB)
═══════════════════════════════════════════════════════════
TYPE: Authority/Recency
PROTOCOL: CockroachDB

PROPERTIES:
- Scope: Key range
- Lifetime: Lease interval (9 seconds)
- Binding: Leaseholder node
- Transitivity: No
- Revocation: Expiry or transfer
- Cost: Raft consensus for transfer

LIFECYCLE:
Generated → Raft consensus on leaseholder
Validated → Majority confirms
Active → Leaseholder serves reads/writes
Expiring → Before lease expiry
Expired → Must renew or transfer

ENABLES:
- Consistent reads without consensus
- Local reads from leaseholder
- Write linearizability

FAILURE MODES:
- Lease expiry: Unavailability window
- Split brain: Prevented by Raft
- Clock skew: Lease overlap danger

CODE EXAMPLE:
class RangeLease:
    def __init__(self, range_id, node_id):
        self.evidence = {
            'range_id': range_id,
            'leaseholder': node_id,
            'epoch': self.raft_term,
            'start_ts': HLC.now(),
            'expiry_ts': HLC.now() + timedelta(seconds=9),
            'sequence': 0  # Increments on transfer
        }

    def can_serve_read(self, read_ts):
        return (self.is_leaseholder() and
                read_ts < self.expiry_ts and
                self.raft_leader_confirmed())
```

---

## Part 4: LSM Tree Evidence

### Evidence Card: SSTable Bloom Filter
```yaml
EVIDENCE CARD: SSTable Bloom Filter
═══════════════════════════════════════════════════════════
TYPE: Inclusion (Probabilistic)
PROTOCOL: LSM Trees (RocksDB/LevelDB)

PROPERTIES:
- Scope: SSTable file
- Lifetime: Until compaction
- Binding: SSTable file
- Transitivity: No
- Revocation: On file deletion
- Cost: Memory per SSTable

LIFECYCLE:
Generated → During SSTable creation
Validated → Probability calculation
Active → Negative lookups skip file
Expiring → During compaction
Expired → When SSTable deleted

ENABLES:
- Skip unnecessary disk reads
- Reduce read amplification
- Fast negative lookups

FAILURE MODES:
- False positive: Unnecessary read
- Corrupted filter: All reads go to disk
- Memory pressure: Filters evicted

CODE EXAMPLE:
class BloomFilter:
    def __init__(self, expected_items, fp_rate=0.01):
        self.size = self.optimal_size(expected_items, fp_rate)
        self.bits = bitarray(self.size)
        self.k = self.optimal_hash_functions(expected_items, self.size)

    def add(self, key):
        for i in range(self.k):
            idx = hash(key, i) % self.size
            self.bits[idx] = 1

    def possibly_contains(self, key):
        # False positive possible, false negative impossible
        return all(self.bits[hash(key, i) % self.size]
                  for i in range(self.k))
```

### Evidence Card: Compaction Certificate
```yaml
EVIDENCE CARD: LSM Compaction Certificate
═══════════════════════════════════════════════════════════
TYPE: Convergence/GC
PROTOCOL: LSM Tree Compaction

PROPERTIES:
- Scope: Level in LSM tree
- Lifetime: Until next compaction
- Binding: Set of SSTables
- Transitivity: No
- Revocation: Never
- Cost: CPU + I/O for merge

LIFECYCLE:
Generated → Compaction triggered
Validated → Merge sort completed
Active → New SSTable active
Expiring → Old SSTables marked
Expired → Old SSTables deleted

ENABLES:
- Space reclamation
- Read performance
- Tombstone cleanup

FAILURE MODES:
- Compaction lag: Write stalls
- Too aggressive: Write amplification
- Failed compaction: Space exhaustion

CODE EXAMPLE:
class CompactionEvidence:
    def __init__(self, level, input_files, output_file):
        self.cert = {
            'compaction_id': uuid4(),
            'level': level,
            'input_files': input_files,
            'output_file': output_file,
            'start_time': time(),
            'stats': {
                'bytes_read': 0,
                'bytes_written': 0,
                'keys_merged': 0,
                'tombstones_dropped': 0
            }
        }

    def execute(self):
        merger = MergeIterator(self.input_files)
        writer = SSTableWriter(self.output_file)

        for key, value in merger:
            if not self.is_tombstone_expired(key, value):
                writer.write(key, value)
                self.stats['keys_merged'] += 1

        writer.finish()
        self.mark_success()
        self.schedule_deletion(self.input_files)
```

---

## Part 5: B-Tree Evidence

### Evidence Card: Page Split Certificate
```yaml
EVIDENCE CARD: B-Tree Page Split
═══════════════════════════════════════════════════════════
TYPE: Structure/Rebalancing
PROTOCOL: B-Tree/B+Tree

PROPERTIES:
- Scope: Parent + Children pages
- Lifetime: Permanent
- Binding: Page IDs
- Transitivity: No
- Revocation: Never
- Cost: Multiple page writes

LIFECYCLE:
Generated → Page becomes full
Validated → Median key chosen
Active → Split completed
Expiring → Never
Expired → Never

ENABLES:
- Balanced tree structure
- Logarithmic operations
- Concurrent access (with latches)

FAILURE MODES:
- Crash during split: Inconsistent tree
- Parent full: Recursive splits
- Concurrent splits: Latch conflicts

CODE EXAMPLE:
class BTreeSplit:
    def split_page(self, full_page):
        split_evidence = {
            'original_page': full_page.id,
            'median_key': full_page.find_median(),
            'left_page': self.allocate_page(),
            'right_page': self.allocate_page(),
            'parent_update': None
        }

        # Distribute keys
        left_keys = [k for k in full_page.keys if k < median]
        right_keys = [k for k in full_page.keys if k >= median]

        # Update parent (may trigger recursive split)
        parent = full_page.parent
        if parent.is_full():
            self.split_page(parent)  # Recursive

        parent.add_separator(median_key, left_page, right_page)
        split_evidence['parent_update'] = parent.id

        return split_evidence
```

---

## Evidence Composition in Storage Systems

### Transaction Composition
```python
def distributed_transaction_evidence():
    """Shows how evidence composes in a distributed transaction"""

    # Start transaction
    tx_begin = {
        'tx_id': uuid4(),
        'start_ts': HLC.now(),
        'isolation': 'SERIALIZABLE'
    }

    # Accumulate evidence during execution
    evidence_chain = []

    # Read evidence
    read_evidence = {
        'type': 'MVCC_READ',
        'timestamp': tx_begin['start_ts'],
        'versions_checked': [...],
        'snapshot_consistent': True
    }
    evidence_chain.append(read_evidence)

    # Lock evidence
    lock_evidence = {
        'type': '2PL_LOCK',
        'resources': ['row_1', 'row_2'],
        'mode': 'EXCLUSIVE',
        'timeout': tx_begin['start_ts'] + 30
    }
    evidence_chain.append(lock_evidence)

    # Write evidence
    wal_evidence = {
        'type': 'WAL_ENTRY',
        'lsn': get_next_lsn(),
        'operations': [...],
        'synced': True
    }
    evidence_chain.append(wal_evidence)

    # Commit evidence
    commit_evidence = {
        'type': '2PC_COMMIT',
        'tx_id': tx_begin['tx_id'],
        'commit_ts': HLC.now(),
        'participants': ['shard_1', 'shard_2'],
        'votes': ['COMMIT', 'COMMIT'],
        'evidence_chain': evidence_chain
    }

    return commit_evidence
```

### Storage Mode Matrix

| Mode | Invariants | Evidence Required | Operations |
|------|------------|-------------------|------------|
| **Target** | ACID guarantees | WAL synced, Locks held, 2PC prepared | All |
| **Degraded** | Durability only | WAL synced, No isolation | Writes only |
| **Floor** | Read-only | Checkpoints valid | Reads from snapshot |
| **Recovery** | Consistency | Logs available, Replay in progress | None |

---

## Key Insights: Storage Evolution as Evidence Evolution

1. **ACID → BASE → NewSQL** = **Strong evidence → Weak evidence → Smart evidence**
   - ACID: Expensive, guaranteed evidence (2PC, locks)
   - BASE: Cheap, eventual evidence (vector clocks, hints)
   - NewSQL: Efficient, sufficient evidence (HLC, Paxos)

2. **Evidence determines guarantees**
   - No evidence = No guarantees
   - Weak evidence = Weak guarantees
   - Strong evidence = Strong guarantees
   - Smart evidence = Adaptive guarantees

3. **Storage engines are evidence factories**
   - LSM: Creates evidence through compaction
   - B-Tree: Creates evidence through splits
   - MVCC: Creates evidence through versions

4. **Durability is evidence persistence**
   - WAL = Evidence of operations
   - Checkpoints = Evidence of state
   - Replication = Evidence redundancy

5. **Performance vs Evidence trade-off**
   - More evidence = Slower writes, stronger guarantees
   - Less evidence = Faster writes, weaker guarantees
   - Smart evidence = Fast enough, strong enough

---

## Transfer Tests

### Near Transfer: In-Memory Database
How does Redis provide durability evidence?
- AOF (Append-Only File) = WAL evidence
- RDB snapshots = Checkpoint evidence
- Replication = Evidence distribution

### Medium Transfer: Blockchain Storage
How does blockchain create evidence?
- Blocks = Batch commit evidence
- Merkle trees = Inclusion evidence
- Proof-of-Work = Ordering evidence

### Far Transfer: Git Version Control
How does Git manage evidence?
- Commits = Transaction evidence
- SHA hashes = Integrity evidence
- Branches = Isolation evidence

---

This framework makes storage system trade-offs explicit through their evidence generation and consumption patterns.