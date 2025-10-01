# GitHub's 24-Hour Outage: When Guarantees Collapse

## The Incident: October 21, 2018, 22:52 UTC

> "We lost the ability to serve consistent data. Our guarantee vector collapsed from global serializability to regional eventual consistency. Recovery took 24 hours because we had no framework for reasoning about degraded modes."

At 22:52 UTC on October 21, 2018, a network partition split GitHub's infrastructure between US-East and US-West. For 43 seconds, the network connectivity between coasts was severed. What followed was a 24-hour outage that revealed fundamental gaps in how we reason about distributed systems under stress.

This chapter analyzes the incident through the **guarantee vector framework**—showing how GitHub's guarantees collapsed, why recovery was so difficult, and what a principled approach to degradation could have prevented.

### Timeline with Guarantee Vectors

```
22:52:00 UTC - Network partition begins
  G = ⟨Global, SS, SER, Fresh(lease), Idem(uuid), Auth(oauth)⟩
       ↓
22:52:05 UTC - Orchestrator detects partition
  G_east = ⟨Regional, SS, SER, Fresh(lease), Idem(uuid), Auth(cache)⟩
  G_west = ⟨Regional, SS, SER, Fresh(lease), Idem(uuid), Auth(cache)⟩
       ↓
22:52:15 UTC - Orchestrator promotes West to primary (SPLIT BRAIN!)
  G_east = ⟨Regional, SS, SER, BS(30s), Idem(uuid), Auth(cache)⟩  [writes accepted]
  G_west = ⟨Regional, SS, SER, BS(30s), Idem(uuid), Auth(cache)⟩  [writes accepted]
       ↓
22:52:43 UTC - Partition heals
  meet(G_east, G_west) = ⟨Object, None, Fractured, EO, None, Unauth⟩
  [GUARANTEE COLLAPSE - data diverged]
       ↓
23:02:00 UTC - Engineers detect data inconsistency
  G = ⟨Regional, Causal, Fractured, EO, None, Auth(manual)⟩  [degraded mode]
       ↓
23:30:00 UTC - Enter read-only mode (Floor)
  G = ⟨Global, Causal, RA, EO, Idem(best-effort), Auth(manual)⟩
       ↓
Oct 22, 16:24 UTC - Recovery begins (Manual reconciliation)
  G = ⟨Global, Causal, SI, BS(∞), Idem(uuid), Auth(manual)⟩
       ↓
Oct 23, 06:00 UTC - Normal service restored
  G = ⟨Global, SS, SER, Fresh(lease), Idem(uuid), Auth(oauth)⟩
```

**The core failure**: GitHub's systems had no principled way to compose degraded guarantee vectors across services.

## Part I: The Three-Layer Analysis

### Layer 1: Physics (The Eternal Truths)

**Truth 1: Information diverges without coordination**

During the 43-second partition, two invariants were simultaneously active:
- East Coast: "I am the primary MySQL"
- West Coast: "I am the primary MySQL"

```
Physics says: CAP theorem forbids global consistency during partition

GitHub's choice during partition:
  - Availability ✓ (both regions accepted writes)
  - Consistency ✗ (data diverged)

Result: 0.0003% of metadata diverged (millions of rows)
```

**Truth 2: Evidence expires without communication**

MySQL replication evidence:

```python
class BinlogEvidence:
    """Evidence that a transaction replicated"""

    # Normal operation
    evidence = {
        'type': 'binlog_position',
        'position': '1000',
        'acknowledged_by': ['replica1', 'replica2', 'replica3'],
        'timestamp': 1540162320,
        'expires_at': 1540162350  # 30s TTL
    }

    # During partition
    evidence = {
        'type': 'binlog_position',
        'position': '1050',
        'acknowledged_by': [],  # NO ACKS!
        'timestamp': 1540162330,
        'expires_at': 1540162360,
        'status': 'EXPIRED'  # Evidence lost
    }
```

**Truth 3: Agreement requires communication**

The Orchestrator (GitHub's MySQL failover tool) runs leader election:

```
Normal: Raft consensus across 5 nodes
  - 3 in East, 2 in West
  - Quorum = 3

During partition:
  - East has 3 nodes → Can elect leader ✓
  - West has 2 nodes → Cannot elect leader ✗

But: Orchestrator had a bug!
  - West claimed leadership with minority
  - Result: SPLIT BRAIN
```

### Layer 2: Patterns (Design Strategies)

**Pattern 1: Primary key generation requires consensus**

MySQL AUTO_INCREMENT is a **distributed counter**:

```python
class MySQLAutoIncrement:
    """Invariant: Globally unique primary keys"""

    def next_id(self):
        # Conservation invariant
        # Threat: Concurrent increment on split brains

        # Evidence required: Exclusive lock
        with self.lock:  # What if lock is regional?
            self.counter += 1
            return self.counter
```

During split brain:
```
East generates: 1001, 1002, 1003, 1004, 1005
West generates: 1001, 1002, 1003, 1004, 1005

Collision! Conservation violated!
```

**Pattern 2: Degradation requires explicit policy**

GitHub had no mode matrix. The failure mode was:

```python
# What GitHub had (implicit)
if partition_detected:
    # Hope it goes away?
    # Keep accepting writes?
    # Reject writes?
    # UNDEFINED BEHAVIOR
    panic()

# What GitHub needed (explicit)
def enter_degraded_mode(partition_evidence):
    mode_matrix = {
        'invariant': 'primary_key_uniqueness',
        'preserved': ['reads', 'health_checks'],
        'suspended': ['writes'],
        'evidence': 'EXPIRED',
        'operations': {
            'write': 'REJECT',
            'read': 'ALLOW (stale)',
            'health': 'ALLOW'
        },
        'g_vector': '⟨Regional, Causal, RA, EO, Idem(best), Auth(cache)⟩'
    }
    return mode_matrix
```

**Pattern 3: Recovery requires authoritative choice**

Both regions had diverged data. Recovery pattern:

```python
def recover_from_split_brain(east_state, west_state):
    # Cannot merge - data conflicted
    # Cannot discard - both had legitimate writes
    # Must choose authoritative source

    # GitHub's choice: East was authoritative
    # Reason: More transactions (heuristic)

    authoritative = east_state
    discarded = west_state

    # Replay discarded transactions IF POSSIBLE
    # Many couldn't be replayed (PK conflicts)

    return (authoritative, lost_transactions)
```

### Layer 3: Implementation (The Tactics)

**MySQL AUTO_INCREMENT Exhaustion**

```sql
CREATE TABLE repositories (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255),
  owner_id BIGINT
);

-- Normal operation:
-- East primary: id = 1000
-- West replica: waits for replication

-- During partition:
-- East primary: id = 1001, 1002, 1003...
-- West promoted: id = 1001, 1002, 1003...

-- Collision detection:
SELECT id, COUNT(*)
FROM repositories
GROUP BY id
HAVING COUNT(*) > 1;

-- Result: 1,000+ collisions
```

**Orchestrator Split Brain**

```go
// Orchestrator bug (simplified)
func (o *Orchestrator) electLeader(nodes []Node) Node {
    votes := 0
    for _, node := range nodes {
        if node.isReachable() {
            votes++
        }
    }

    // BUG: Should be votes > len(nodes)/2
    // Actual: votes >= len(nodes)/2

    if votes >= len(nodes)/2 {  // Off-by-one!
        return nodes[0]  // Promote to primary
    }

    return nil
}

// During partition:
// West has 2 nodes, total=5
// 2 >= 5/2 = 2 >= 2 → TRUE (should be FALSE)
```

## Part II: Guarantee Vector Algebra

### Normal Operation Composition

GitHub's architecture:

```
[Client] → [HAProxy] → [App Server] → [MySQL] → [Redis] → [Elasticsearch]
```

Each service has a guarantee vector. End-to-end guarantee is the **meet** (weakest):

```python
G_haproxy = ⟨Global, SS, SER, Fresh(lease), Idem(conn_id), Auth(tls)⟩
G_app     = ⟨Global, SS, SER, Fresh(lease), Idem(uuid), Auth(session)⟩
G_mysql   = ⟨Global, SS, SER, Fresh(lease), Idem(tx_id), Auth(user)⟩
G_redis   = ⟨Global, Causal, RA, BS(1s), Idem(key), Auth(token)⟩
G_elastic = ⟨Global, None, Fractured, BS(10s), None, Auth(token)⟩

# Sequential composition
G_end_to_end = meet(G_haproxy, G_app, G_mysql, G_redis, G_elastic)
             = ⟨Global, None, Fractured, BS(10s), None, Auth(token)⟩
```

**Key insight**: Redis and Elasticsearch already weakened guarantees! GitHub's "strong consistency" was an illusion.

### Partition-Time Degradation

```python
# East region during partition
G_east_mysql = ⟨Regional, SS, SER, BS(30s), Idem(uuid), Auth(cache)⟩
G_east_redis = ⟨Regional, Causal, RA, BS(30s), Idem(key), Auth(cache)⟩

# West region during partition
G_west_mysql = ⟨Regional, SS, SER, BS(30s), Idem(uuid), Auth(cache)⟩
G_west_redis = ⟨Regional, Causal, RA, BS(30s), Idem(key), Auth(cache)⟩

# Parallel composition attempt (merge after partition)
G_merged = meet(G_east_mysql, G_west_mysql)
         = ⟨Object, None, Fractured, EO, None, Unauth⟩
```

**The collapse**: From global serializability to object-level eventual consistency.

### Upgrade Requirements

To restore guarantees after partition:

```python
# Current state
G_current = ⟨Object, None, Fractured, EO, None, Unauth⟩

# Target state
G_target = ⟨Global, SS, SER, Fresh(lease), Idem(uuid), Auth(oauth)⟩

# Upgrade path requires NEW EVIDENCE
upgrade_evidence = [
    'reconcile_diverged_data',  # Object → Global scope
    'establish_total_order',     # None → SS order
    'verify_transactions',       # Fractured → SER visibility
    'restart_replication',       # EO → Fresh recency
    'rebuild_indices',           # None → Idem idempotence
    'refresh_auth_tokens'        # Unauth → Auth
]

# Cannot upgrade without evidence!
# GitHub took 24 hours to generate this evidence
```

### Composition Operators

**Sequential (▷)**:

```python
# MySQL ▷ Redis
G_mysql = ⟨Global, SS, SER, Fresh(lease), Idem(uuid), Auth(user)⟩
G_redis = ⟨Global, Causal, RA, BS(1s), Idem(key), Auth(token)⟩

# Result: meet(G_mysql, G_redis)
G_composed = ⟨Global, Causal, RA, BS(1s), Idem(key), Auth(token)⟩
#            └─────────────────┬───────────────────┘
#                      Redis weakens MySQL's guarantees
```

**Parallel (||)**:

```python
# East || West during partition
G_result = meet(G_east, G_west)
#        = weakest of each component
```

**Downgrade (⤓)**:

```python
# Explicit degradation with labeling
G_normal = ⟨Global, SS, SER, Fresh(lease), Idem(uuid), Auth(oauth)⟩
         ⤓ [partition detected]
G_degraded = ⟨Regional, Causal, RA, BS(30s), Idem(uuid), Auth(cache)⟩
#             └─labeled as DEGRADED in logs/metrics
```

**Upgrade (↑)**:

```python
# Requires new evidence
G_degraded = ⟨Regional, Causal, RA, BS(30s), Idem(uuid), Auth(cache)⟩
          ↑ [evidence: data_reconciled + replication_verified]
G_normal = ⟨Global, SS, SER, Fresh(lease), Idem(uuid), Auth(oauth)⟩
```

## Part III: Context Capsules

### Capsule at MySQL Primary Boundary

**Normal operation**:

```python
mysql_primary_capsule = {
    'invariant': 'primary_key_uniqueness',
    'evidence': {
        'type': 'auto_increment_lock',
        'holder': 'mysql-east-primary',
        'epoch': 1540162320,
        'expires_at': 1540162350,
        'proof': 'binlog_position=1000 + acks=[r1,r2,r3]'
    },
    'boundary': 'mysql_primary@us-east',
    'scope': 'Global',
    'mode': 'target',
    'g_vector': '⟨Global, SS, SER, Fresh(lease), Idem(tx), Auth(user)⟩',
    'operations': {
        'read': 'ALLOW',
        'write': 'ALLOW',
        'admin': 'ALLOW'
    },
    'fallback': 'degrade_to_read_only_on_evidence_loss'
}
```

**During partition** (East):

```python
mysql_east_capsule = {
    'invariant': 'primary_key_uniqueness',
    'evidence': {
        'type': 'auto_increment_lock',
        'holder': 'mysql-east-primary',
        'epoch': 1540162330,
        'expires_at': 1540162360,
        'proof': 'binlog_position=1050 + acks=[]',  # NO ACKS!
        'status': 'EXPIRING'
    },
    'boundary': 'mysql_primary@us-east',
    'scope': 'Regional',  # Narrowed!
    'mode': 'degraded',
    'g_vector': '⟨Regional, SS, SER, BS(30s), Idem(tx), Auth(cache)⟩',
    'operations': {
        'read': 'ALLOW (local)',
        'write': 'ALLOW (risky!)',  # SHOULD BE REJECTED
        'admin': 'REQUIRE_MANUAL'
    },
    'fallback': 'SHOULD_ACTIVATE'  # But didn't!
}
```

**During partition** (West - SPLIT BRAIN):

```python
mysql_west_capsule = {
    'invariant': 'primary_key_uniqueness',
    'evidence': {
        'type': 'auto_increment_lock',
        'holder': 'mysql-west-primary',  # Illegitimate!
        'epoch': 1540162335,
        'expires_at': 1540162365,
        'proof': 'orchestrator_promotion + minority_vote',  # INVALID
        'status': 'INVALID'
    },
    'boundary': 'mysql_primary@us-west',
    'scope': 'Regional',
    'mode': 'INVALID',  # System didn't know this!
    'g_vector': '⟨Regional, SS, SER, BS(30s), Idem(tx), Auth(cache)⟩',
    'operations': {
        'read': 'ALLOW',
        'write': 'ALLOW',  # VIOLATES GLOBAL INVARIANT
        'admin': 'ALLOW'
    },
    'fallback': 'NOT_DEFINED'  # Root cause!
}
```

### Capsule Operations

**restrict()** - Narrow scope during partition:

```python
def restrict_capsule(capsule, new_scope):
    """Maintain safety at boundary"""
    return {
        **capsule,
        'scope': new_scope,  # Global → Regional
        'g_vector': downgrade_vector(capsule['g_vector'], new_scope),
        'mode': 'degraded',
        'evidence': mark_as_restricted(capsule['evidence'])
    }
```

**degrade()** - Apply fallback policy:

```python
def degrade_capsule(capsule, reason):
    """Explicit degradation with labeling"""
    return {
        **capsule,
        'mode': 'floor',
        'g_vector': apply_fallback_vector(capsule),
        'operations': {
            'read': 'ALLOW (stale)',
            'write': 'REJECT',
            'admin': 'REQUIRE_MANUAL'
        },
        'degradation_reason': reason,
        'degraded_at': time.now(),
        'evidence': mark_as_expired(capsule['evidence'])
    }
```

**renew()** - Refresh expiring evidence:

```python
def renew_evidence(capsule):
    """Attempt to refresh evidence"""
    new_evidence = attempt_replication_ack(capsule)

    if new_evidence:
        return {
            **capsule,
            'evidence': new_evidence,
            'mode': 'target'
        }
    else:
        # Evidence cannot be renewed
        return degrade_capsule(capsule, 'evidence_renewal_failed')
```

## Part IV: Five Sacred Diagrams

### Diagram 1: Invariant Lattice

```
                    Conservation
                   (Nothing created/destroyed)
                          |
                          |
                    Uniqueness
                (At most one primary)
                    /         \
                   /           \
          PK_Unique          Monotonicity
         (No collisions)    (Counters increase)
                \              /
                 \            /
                  \          /
                   Freshness
              (Replicas sync < 1s)
                      |
                      |
                 Visibility
           (Transactions serializable)


During GitHub outage:

✓ Conservation: Maintained (no data destroyed)
✗ Uniqueness: VIOLATED (two primaries)
✗ PK_Unique: VIOLATED (collisions occurred)
✓ Monotonicity: Maintained per-region
✗ Freshness: VIOLATED (no sync for 43s)
✗ Visibility: VIOLATED (diverged views)
```

### Diagram 2: Evidence Flow

```
                  NORMAL OPERATION

[Primary MySQL]                          [Replica MySQL]
      |                                        |
      | writes: id=1001                       |
      | generates: binlog_pos=1001            |
      |                                        |
      +-------------binlog stream------------>+
      |                                        |
      |                                        | validates: checksum OK
      |                                        | writes: id=1001
      |                                        |
      +<-----------acknowledgment--------------+
      |                                        |
   evidence:                              evidence:
   - binlog_pos=1001                      - binlog_pos=1001
   - ack_received=TRUE                    - sync=TRUE
   - expires_at=t+30s                     - lag=0.1s


                  DURING PARTITION

[Primary MySQL East]    ╳╳╳PARTITION╳╳╳    [Replica MySQL West]
      |                                           |
      | writes: id=1001                          |
      | generates: binlog_pos=1001               |
      |                                           |
      +-------------binlog stream----╳╳╳         |
      |                                           |
      | NO ACKNOWLEDGMENT!                        | NO DATA RECEIVED
      |                                           |
   evidence:                                   evidence:
   - binlog_pos=1001                           - binlog_pos=1000 (stale)
   - ack_received=FALSE                        - sync=FALSE
   - expires_at=t+30s                          - lag=UNKNOWN
   - status=EXPIRING                           - status=DISCONNECTED
      |                                           |
      v                                           v
   SHOULD DEGRADE                            SHOULD STAY READ-ONLY
   (but didn't!)                             (but got promoted!)


              AFTER PARTITION (SPLIT BRAIN)

[Primary MySQL East]                      [Primary MySQL West]
      |                                           |
      | writes: id=1001, 1002, 1003              | writes: id=1001, 1002, 1003
      | binlog_pos=1003                          | binlog_pos=1003
      |                                           |
   evidence:                                   evidence:
   - REGIONAL only                             - REGIONAL only
   - NO GLOBAL COORDINATION                    - NO GLOBAL COORDINATION
      |                                           |
      |        PARTITION HEALS                    |
      |              ↓                            |
      +-------------CONFLICT!---------------------+
                     |
                     v
              DATA DIVERGED
         (1000+ primary key collisions)
```

### Diagram 3: Mode Transitions

```
┌─────────────────────────────────────────────────────────────┐
│                        TARGET MODE                           │
│  Invariants: PK unique, Order, Freshness                    │
│  Evidence: binlog acks, replication < 1s                    │
│  G-vector: ⟨Global, SS, SER, Fresh(lease), Idem, Auth⟩      │
│  Operations: ALL writes and reads                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [evidence expiring: replication_lag > 1s]
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                      DEGRADED MODE                           │
│  Invariants: PK unique (paused), Read consistency           │
│  Evidence: stale replicas, no recent acks                   │
│  G-vector: ⟨Regional, Causal, RA, BS(30s), Idem, Auth⟩      │
│  Operations: Reads (stale), writes SHOULD BE rejected       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [evidence expired: replication_lag > 30s]
                       │ [evidence conflict: binlog diverged]
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                        FLOOR MODE                            │
│  Invariants: Availability only                              │
│  Evidence: None                                              │
│  G-vector: ⟨Object, None, Fractured, EO, None, Unauth⟩      │
│  Operations: Health checks, no writes, stale reads          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [operator intervention]
                       │ [choose authoritative source]
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                      RECOVERY MODE                           │
│  Invariants: Manual reconciliation                          │
│  Evidence: Human verification, controlled replay            │
│  G-vector: ⟨Global, Causal, SI, BS(∞), Idem, Auth(manual)⟩  │
│  Operations: Controlled writes, reconciliation              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [evidence restored: replication verified]
                       │ [verification passed: no more conflicts]
                       ↓
                   (back to TARGET)


GitHub's actual path:

22:52:00 - TARGET
22:52:05 - DEGRADED (should have gone here)
22:52:15 - FLOOR (should have gone here immediately)
23:02:00 - RECOVERY (10 minutes too late)
Oct 23  - TARGET (24 hours of recovery)
```

### Diagram 4: Guarantee Degradation

```
Components:  Scope      Order    Visibility  Recency      Idem      Auth
            ━━━━━━    ━━━━━━━   ━━━━━━━━━  ━━━━━━━━    ━━━━━━    ━━━━━━

Normal:     Global ─┐   SS ─┐     SER ─┐    Fresh ─┐   uuid ─┐   oauth ─┐
            22:52   │   22:52│    22:52│    22:52  │   22:52│   22:52  │
                    │        │         │           │        │          │
Partition:  Global  │   SS   │     SER │    Fresh  │   uuid │   cache  │
   +5s:     22:57   │   22:57│    22:57│    22:57  │   22:57│   22:57  │
                    ↓        │         │           ↓        │          ↓
Split       Region  │   SS   │     SER │    BS(30s)│   uuid │   cache
Brain:      al─┐    │        │         │           │        │
   +15s     22:│    │        │         │           │        │
            57  │   │        │         │           │        │
                ↓   ↓        ↓         ↓           │        │
Merge       Object  None  Fractured   EO          │        │
   +43s:                                           │        │
            23:00   23:00   23:00     23:00       │        │
                                                   ↓        ↓
Floor:      Object  None  Fractured   EO         None    Unauth
            23:30   23:30   23:30     23:30      23:30   23:30

                    ↑ UPGRADE REQUIRES NEW EVIDENCE ↑

Recovery:   Global  Causal   SI      BS(∞)       uuid    manual
            Oct22   Oct22   Oct22    Oct22       Oct22   Oct22
            16:24   16:24   16:24    16:24       16:24   16:24
                    ↓        ↓         ↓           ↓        ↓
Target:     Global   SS      SER     Fresh       uuid    oauth
            Oct23   Oct23   Oct23    Oct23       Oct23   Oct23
            06:00   06:00   06:00    06:00       06:00   06:00
```

### Diagram 5: Context Propagation Failure

```
              CLIENT REQUEST
                    ↓
            [API Gateway]
            Context Capsule:
            {invariant: "auth",
             evidence: "jwt_token",
             g_vector: ⟨G,SS,SER,Fresh,Idem,Auth⟩}
                    ↓
            [Application Server]
            Capsule forwarded ✓
                    ↓
            [MySQL Primary East]     [MySQL Primary West]
            Capsule forwarded ✓      Capsule forwarded ✓
                    ↓                        ↓
            During partition:

            EAST CAPSULE               WEST CAPSULE
            {invariant: "PK",          {invariant: "PK",
             evidence: "binlog_1001",   evidence: "binlog_1001",
             scope: "Regional",         scope: "Regional",
             mode: "degraded"}          mode: "INVALID"}
                    ↓                        ↓
                    ╳╳╳╳ PARTITION ╳╳╳╳
                    ↓                        ↓
            NO CAPSULE EXCHANGE!
            (Context propagation FAILED)
                    ↓                        ↓
            Writes id=1001-1050      Writes id=1001-1045
                    ↓                        ↓
                    ↓   PARTITION HEALS     ↓
                    └─────────┬──────────────┘
                              ↓
                    CAPSULES INCOMPATIBLE!
                    meet(East, West) = ⟨Object, None...⟩
                              ↓
                        DATA DIVERGED

Root cause: No cross-region capsule propagation mechanism
```

## Part V: Mode Matrix

```
┌────────┬──────────────────┬───────────────────┬─────────────────────┬──────────────────┬─────────────────────────┐
│ Mode   │ Invariants       │ Evidence          │ G-vector            │ Operations       │ Entry/Exit Triggers      │
│        │ Preserved        │ Required          │                     │ Allowed          │                         │
├────────┼──────────────────┼───────────────────┼─────────────────────┼──────────────────┼─────────────────────────┤
│ Target │ • PK uniqueness  │ • AI lock held    │ ⟨Global,            │ • All writes     │ Entry: evidence_restored│
│        │ • Order (SS)     │ • Binlog acks<1s  │  SS,                │ • All reads      │ Exit: evidence_expiring │
│        │ • Freshness <1s  │ • Replica lag<1s  │  SER,               │ • Admin ops      │   OR partition_detected │
│        │ • Auth valid     │ • OAuth tokens    │  Fresh(lease),      │                  │                         │
│        │                  │                   │  Idem(uuid),        │                  │                         │
│        │                  │                   │  Auth(oauth)⟩       │                  │                         │
├────────┼──────────────────┼───────────────────┼─────────────────────┼──────────────────┼─────────────────────────┤
│Degraded│ • Read           │ • Stale replica   │ ⟨Regional,          │ • Reads (stale)  │ Entry: evidence_expiring│
│        │   consistency    │   lag 1-30s       │  Causal,            │ • Writes (SHOULD │ Exit: evidence_expired  │
│        │ • Auth (cached)  │ • Cached tokens   │  RA,                │   BE rejected!)  │   OR evidence_restored  │
│        │                  │ • Partial acks    │  BS(30s),           │ • Health checks  │                         │
│        │                  │                   │  Idem(uuid),        │                  │                         │
│        │                  │                   │  Auth(cache)⟩       │                  │                         │
├────────┼──────────────────┼───────────────────┼─────────────────────┼──────────────────┼─────────────────────────┤
│ Floor  │ • Availability   │ • None            │ ⟨Object,            │ • Health checks  │ Entry: evidence_expired │
│        │   only           │                   │  None,              │ • Stale reads    │   OR conflict_detected  │
│        │                  │                   │  Fractured,         │ • NO writes      │ Exit: operator_         │
│        │                  │                   │  EO,                │                  │   intervention          │
│        │                  │                   │  None,              │                  │                         │
│        │                  │                   │  Unauth⟩            │                  │                         │
├────────┼──────────────────┼───────────────────┼─────────────────────┼──────────────────┼─────────────────────────┤
│Recovery│ • Manual         │ • Human           │ ⟨Global,            │ • Controlled     │ Entry: operator_choice  │
│        │   reconciliation │   verification    │  Causal,            │   writes         │ Exit: verification_     │
│        │ • Conflict       │ • Replay logs     │  SI,                │ • Reconciliation │   passed AND            │
│        │   resolution     │ • Checksums       │  BS(∞),             │ • Gradual resume │   replication_verified  │
│        │                  │                   │  Idem(uuid),        │                  │                         │
│        │                  │                   │  Auth(manual)⟩      │                  │                         │
└────────┴──────────────────┴───────────────────┴─────────────────────┴──────────────────┴─────────────────────────┘
```

### What GitHub Actually Did vs. What Mode Matrix Prescribes

```python
# What happened (implicit, ad-hoc)
22:52:05 - Detected partition → Continued accepting writes (WRONG)
22:52:15 - Orchestrator promoted West → Split brain (CATASTROPHIC)
22:52:43 - Partition healed → Data diverged (INEVITABLE)
23:02:00 - Detected inconsistency → Panic (TOO LATE)
23:30:00 - Entered read-only → Floor mode (17 minutes late)

# What Mode Matrix prescribes (explicit, principled)
22:52:05 - evidence_expiring detected
        → Transition Target → Degraded
        → Reject writes, allow stale reads
        → Label degradation in logs/metrics

22:52:15 - evidence_expired detected (no acks for 10s)
        → Transition Degraded → Floor
        → Reject ALL writes
        → Health checks only
        → Alert on-call

22:52:43 - Partition heals, check for conflicts
        → IF conflicts: Stay in Floor
        → Page senior engineers
        → Begin Recovery mode

23:00:00 - operator_intervention (choose East as authoritative)
        → Transition Floor → Recovery
        → Manual reconciliation begins
        → Controlled write resumption

Oct 23  - verification_passed + replication_verified
        → Transition Recovery → Target
        → Full service restored
```

## Part VI: Evidence Lifecycle Analysis

### MySQL Binlog Position Evidence

**Phase 1: Generated**

```python
class BinlogEvidence:
    def generate(self, transaction):
        """Primary generates evidence when committing"""
        return {
            'type': 'binlog_position',
            'position': self.current_position,
            'transaction_id': transaction.id,
            'timestamp': time.now(),
            'checksum': sha256(transaction.data),
            'scope': 'transaction',
            'lifetime': 30,  # seconds
            'binding': f"mysql-primary@{self.region}",
            'cost_generation': 'cheap (local increment)',
            'cost_verification': 'network RTT + checksum'
        }
```

**Phase 2: Validated**

```python
class ReplicaValidation:
    def validate(self, evidence):
        """Replica validates when receiving"""
        # 1. Checksum matches?
        if not verify_checksum(evidence):
            return ValidationResult.CORRUPT

        # 2. Position sequential?
        if evidence.position != self.last_position + 1:
            return ValidationResult.GAP

        # 3. Within validity window?
        if time.now() > evidence.timestamp + evidence.lifetime:
            return ValidationResult.EXPIRED

        return ValidationResult.VALID
```

**Phase 3: Active**

```python
class ActiveEvidence:
    """Evidence is fresh and usable"""

    def is_active(self, evidence):
        return (
            self.received_ack_from_majority() and
            self.replication_lag < 1.0 and
            time.now() < evidence.expires_at
        )

    # During this phase:
    # - Primary can commit new transactions
    # - G-vector maintains Fresh(lease)
    # - Mode = Target
```

**Phase 4: Expiring**

```python
class ExpiringEvidence:
    """Evidence aging, grace period"""

    def is_expiring(self, evidence):
        return (
            self.replication_lag >= 1.0 and
            self.replication_lag < 30.0 and
            not self.received_recent_ack()
        )

    # During this phase:
    # - Should enter Degraded mode
    # - G-vector downgrades: Fresh → BS(30s)
    # - Writes should be rate-limited or rejected
    # - Alert: "Evidence expiring, prepare to degrade"
```

**Phase 5: Expired**

```python
class ExpiredEvidence:
    """Evidence invalid, cannot be used"""

    def is_expired(self, evidence):
        return (
            self.replication_lag >= 30.0 or
            time.now() > evidence.expires_at or
            self.partition_detected
        )

    # During this phase:
    # - MUST enter Floor mode
    # - G-vector collapses: Fresh → EO
    # - Reject ALL writes
    # - Serve stale reads only
    # - Alert: "Evidence expired, Floor mode active"
```

**Phase 6: Recovery**

```python
class RecoveryEvidence:
    """Generating new evidence after outage"""

    def recover(self):
        # Cannot simply resume - must verify consistency

        # 1. Check for conflicts
        conflicts = self.detect_binlog_conflicts()
        if conflicts:
            # Human intervention required
            return RecoveryStrategy.MANUAL_RECONCILIATION

        # 2. Choose authoritative source
        authoritative = operator.choose_primary()

        # 3. Replay or discard diverged transactions
        for txn in self.diverged_transactions:
            if can_replay_safely(txn):
                replay(txn)
            else:
                log_discarded_transaction(txn)

        # 4. Restart replication
        self.reset_replicas(authoritative)

        # 5. Wait for evidence to become Active again
        wait_for_replication_catchup()

        # 6. Verify: Run consistency checks
        if self.verify_consistency():
            return RecoveryStrategy.RESTORE_TARGET_MODE
        else:
            return RecoveryStrategy.STAY_IN_RECOVERY
```

### Evidence Properties

**Scope**: Per-transaction (binlog position is per-transaction sequential)

**Lifetime**: 30 seconds without acknowledgment

**Binding**: Bound to specific MySQL primary in specific region

**Transitivity**: **NOT transitive** - replicas cannot delegate evidence to other replicas. Only primary can generate authoritative evidence.

**Revocation**:
- Explicit: Primary detects partition → revokes own evidence
- Implicit: Timeout after 30s

**Cost**:
- Generation: Cheap (local counter increment)
- Verification: Network RTT + checksum computation
- Amortization: Can batch multiple transactions in single binlog entry

### Evidence During GitHub Outage

```
Timeline:

22:52:00 - Evidence Active
  position=1000, acks=[r1,r2,r3], lag=0.2s

22:52:05 - Evidence Expiring (partition detected)
  position=1005, acks=[r1], lag=5s
  WARNING: Should degrade to BS(30s)

22:52:15 - Evidence Expired (West promoted)
  East: position=1010, acks=[], lag=∞
  West: position=1003, acks=[], lag=∞
  CRITICAL: Should enter Floor mode

22:52:43 - Evidence Conflicted (partition heals)
  East: position=1050
  West: position=1045
  CONFLICT: Diverged binlogs

23:02:00 - Evidence Invalid (detected by monitoring)
  Cannot merge, cannot trust either source
  Need new evidence type: Human verification

Oct 22 16:24 - Recovery begins
  Generating new evidence: Manual reconciliation

Oct 23 06:00 - Evidence Active again
  position=1050 (East chosen), replicas synchronized
```

## Part VII: Dualities - The Tensions That Defined the Outage

### Duality 1: Safety ↔ Liveness

**Invariant at stake**: Primary key uniqueness

**The tension**:
- Safety: Never generate duplicate primary keys (requires coordination)
- Liveness: Always accept new repository creates (requires availability)

**GitHub's choice during partition**:
```python
# Chose LIVENESS over SAFETY
liveness_priority = True  # Continue accepting writes
safety_priority = False   # Allowed PK collisions

# Result: 1000+ duplicate primary keys
```

**What evidence allows movement along spectrum?**
- Strong evidence (majority quorum) → Can have both safety AND liveness
- Weak evidence (minority) → Must choose
- GitHub had NO evidence but chose liveness anyway

**Which mode?**
- Should have been: Floor mode (prioritize safety, reject writes)
- Actually was: Degraded mode with writes (prioritized liveness, broke safety)

### Duality 2: Local ↔ Global

**Invariant at stake**: Global serializability

**The tension**:
- Local: Each region can operate independently (available)
- Global: All regions agree on order (consistent)

**GitHub's partition**:
```python
# Split into two local regions
east_local = True  # Operating independently
west_local = True  # Operating independently
global_consistency = False  # No agreement

# Each region had LOCAL serializability
# But GLOBAL serializability was lost
```

**Evidence movement**:
- Global consensus evidence (Raft quorum) → Global consistency
- Local evidence only (regional locks) → Local consistency
- During partition: Downgraded from Global to Local

**G-vector impact**:
```
Normal:     ⟨Global, SS, ...⟩
Partition:  ⟨Regional, SS, ...⟩  # Scope narrowed
Merge:      ⟨Object, None, ...⟩  # Collapsed entirely
```

### Duality 3: Evidence ↔ Trust

**Invariant at stake**: Replication correctness

**The tension**:
- Evidence: Verify every replication (expensive, correct)
- Trust: Assume replication works (cheap, risky)

**GitHub's mistake**:
```python
# Normal operation: Trust-based
if replication_enabled:
    assume_replicas_will_sync()  # Trust
    # No evidence verification!

# During partition: Trust failed
partition_occurs()
# Still trusting replication would work
# But replicas couldn't reach primary
# No evidence to prove data replicated

# Result: Split brain because trust was misplaced
```

**What evidence was needed?**
- Binlog acknowledgments (evidence of replication)
- Quorum certificates (evidence of agreement)
- Heartbeats (evidence of liveness)

**Mode impact**:
```
Target:     Evidence ≥ 3 replicas acked
Degraded:   Evidence ≥ 1 replica acked (trusting others will sync)
Floor:      Evidence = 0 replicas (zero trust, no writes)
```

### Duality 4: Freshness ↔ Availability

**Invariant at stake**: Bounded staleness

**The tension**:
- Freshness: Reads reflect recent writes (requires waiting)
- Availability: Reads always succeed (serve stale data)

**GitHub's degradation**:
```python
# Normal: Fresh(lease) - reads within 1s of writes
g_vector_normal = '⟨..., Fresh(lease), ...⟩'

# Partition: Chose availability over freshness
g_vector_partition = '⟨..., BS(30s), ...⟩'
# Served stale reads up to 30s old

# After split brain: Unbounded staleness
g_vector_split = '⟨..., EO, ...⟩'
# Eventual consistency only (no bound!)
```

**Evidence trade-off**:
- Fresh requires: Recent replication evidence (< 1s lag)
- Available requires: Any data, regardless of age
- During partition: No recent evidence → Must choose

### Duality 5: Coordination ↔ Confluence

**Invariant at stake**: Conflict-free merge

**The tension**:
- Coordination: Synchronize before diverging (prevents conflicts)
- Confluence: Allow independent operation (enables conflicts)

**GitHub's failure**:
```python
# Normal: Coordination via replication
primary.coordinate_with_replicas()
# Prevents divergence

# Partition: Lost coordination
east.operate_independently()
west.operate_independently()
# Divergence occurred

# After partition: No confluence mechanism
merge_conflict = cannot_merge(east_state, west_state)
# Coordination was required but unavailable
# Confluence was impossible (not CRDT-based)
# Result: Data loss
```

**What was needed?**
```python
# Option 1: Maintain coordination (CP system)
if no_quorum:
    reject_writes()  # Sacrifice availability

# Option 2: Design for confluence (AP system)
use_crdts_for_merging()  # Sacrifice strong consistency

# GitHub had neither!
# Not designed for confluence
# Didn't maintain coordination
```

### Duality 6: Determinism ↔ Adaptivity

**Invariant at stake**: Predictable behavior

**The tension**:
- Determinism: Always do the same thing (predictable, inflexible)
- Adaptivity: Respond to conditions (flexible, unpredictable)

**GitHub's system**:
```python
# Orchestrator was deterministic
def failover_logic():
    if primary_unreachable:
        promote_replica()  # Always promote
    # No adaptation to partition vs crash
    # No consideration of majority

# Should have been adaptive
def adaptive_failover():
    if primary_unreachable:
        if have_quorum():
            promote_replica()  # Safe
        else:
            enter_read_only()  # Adaptive
            wait_for_operator()
```

**Mode matrix provides adaptivity**:
- Deterministic rule: "If evidence expires, enter Floor mode"
- Adaptive behavior: Different modes for different evidence states

### Duality 7: Strong-Here ↔ Weak-Everywhere

**Invariant at stake**: Consistency model

**The tension**:
- Strong-here: Strong consistency in one region (partition sensitive)
- Weak-everywhere: Weak consistency globally (partition tolerant)

**GitHub's unintended downgrade**:
```python
# Goal: Strong-everywhere
g_vector_goal = '⟨Global, SS, SER, Fresh, ...⟩'

# Partition result: Weak-everywhere
g_vector_actual = '⟨Object, None, Fractured, EO, ...⟩'
# Lost both strong consistency AND global scope

# Better choice: Strong-here during partition
g_vector_adaptive = '⟨Regional, SS, SER, BS(30s), ...⟩'
# Maintain strong consistency in reachable region
# Clearly label as regional scope
```

## Part VIII: Transfer Tests

### Near Transfer: Apply to MongoDB Auto-Increment

**Scenario**: Your MongoDB has replica set split brain. Primary in US-East generates `_id` using counter. Secondary in US-West is promoted during partition.

**Test 1**: Map the G-vector degradation
```python
# Answer:
normal = '⟨Global, Causal, SI, Fresh(OpTime), Idem(idempotent), Auth(x509)⟩'

# During partition
degraded = '⟨Regional, Causal, RA, BS(secondary_lag), Idem, Auth⟩'

# After split brain (if writes accepted on both)
collapsed = '⟨Object, None, Fractured, EO, None, Auth⟩'
```

**Test 2**: Which invariants break first?
```python
# Answer:
# 1. Uniqueness (both generate same _id)
# 2. Order (transactions from both appear to be concurrent)
# 3. Freshness (secondaries lag indefinitely)
```

**Test 3**: What context capsule would prevent data loss?
```python
# Answer:
mongodb_capsule = {
    'invariant': '_id_uniqueness',
    'evidence': 'replica_set_oplog_ack + majority_commit',
    'boundary': 'primary@region',
    'mode': 'target',
    'fallback': 'reject_writes_if_no_majority',
    'operations': {
        'write': 'ALLOW only if majority_ack',
        'read': 'ALLOW from primary or secondary with readConcern'
    }
}

# Key: MongoDB's writeConcern majority prevents split brain
# GitHub MySQL lacked equivalent mechanism
```

### Medium Transfer: Apply to Cassandra Counter Columns

**Scenario**: Cassandra cluster partitions. Counter columns diverge.

**Test 1**: What's different from GitHub's MySQL case?
```python
# Answer:
# Cassandra uses CRDTs for counters (confluence!)
# Divergence is expected and mergeable

# G-vector during partition:
g_cassandra = '⟨Regional, Causal, RA, EO, Idem(commutative), Auth⟩'

# After partition heals:
g_merged = '⟨Global, Causal, EO, EO, Idem(commutative), Auth⟩'
# Can merge without conflicts!
```

**Test 2**: Why doesn't Cassandra have GitHub's problem?
```python
# Answer:
# 1. Designed for AP (not CP like MySQL)
# 2. Counters are convergent (CRDT)
# 3. No global uniqueness invariant
# 4. Tunable consistency (can choose strong reads)

# Trade-off:
# - GitHub: Strong consistency normally, catastrophic during partition
# - Cassandra: Weak consistency always, graceful during partition
```

**Test 3**: What's the evidence difference?
```python
# MySQL (GitHub):
evidence = 'binlog_position + majority_ack'
# Non-transitive, expires, requires quorum

# Cassandra:
evidence = 'vector_clock + hinted_handoff'
# Transitive, mergeable, no quorum required

# Mode matrix:
# MySQL: Target → Floor (huge gap)
# Cassandra: Target → Degraded (smaller gap)
```

### Far Transfer: Distributed Payment System

**Scenario**: Your payment system has accounts in multiple regions. Network partition occurs during Black Friday. Design the degradation strategy using GitHub's evidence lifecycle.

**Test 1**: Define the G-vector for payment system
```python
# Answer:
g_payment_target = '⟨Global, SS, SER, Fresh(lease), Idem(txn_id), Auth(2FA)⟩'

# Why each component:
# - Global: Can't have regional money supplies
# - SS: Transactions must be strictly ordered
# - SER: Must prevent double-spend
# - Fresh: Can't charge old payment methods
# - Idem: Retries must not double-charge
# - Auth: Must verify user identity
```

**Test 2**: Design mode matrix for partition
```python
# Answer:
payment_modes = {
    'Target': {
        'invariants': ['balance_non_negative', 'double_spend_prevented'],
        'evidence': ['majority_quorum', 'txn_locks', 'recent_balance'],
        'g_vector': '⟨Global, SS, SER, Fresh(lease), Idem, Auth(2FA)⟩',
        'operations': {'charge': 'ALLOW', 'refund': 'ALLOW', 'balance': 'FRESH'}
    },

    'Degraded': {
        'invariants': ['balance_cached', 'double_spend_best_effort'],
        'evidence': ['regional_quorum', 'cached_balance'],
        'g_vector': '⟨Regional, SS, SI, BS(5min), Idem, Auth(2FA)⟩',
        'operations': {
            'charge': 'ALLOW if balance_cached > amount',
            'refund': 'QUEUE for later',
            'balance': 'STALE (warn user)'
        }
    },

    'Floor': {
        'invariants': ['availability_only'],
        'evidence': ['none'],
        'g_vector': '⟨Regional, None, Fractured, EO, None, Auth(session)⟩',
        'operations': {
            'charge': 'REJECT (show error)',
            'refund': 'REJECT (show error)',
            'balance': 'CACHED (clearly labeled)'
        }
    },

    'Recovery': {
        'invariants': ['reconciliation', 'fraud_detection'],
        'evidence': ['human_review', 'fraud_analysis'],
        'g_vector': '⟨Global, Causal, SI, BS(∞), Idem, Auth(admin)⟩',
        'operations': {
            'charge': 'MANUAL_APPROVAL_ONLY',
            'refund': 'PROCESS_QUEUED',
            'balance': 'RECOMPUTE'
        }
    }
}
```

**Test 3**: What evidence lifecycle applies?
```python
# Answer:
class PaymentEvidence:
    """Evidence for payment transaction"""

    # Generated: When charge initiated
    def generate(self, charge):
        return {
            'txn_id': uuid.uuid4(),
            'balance_before': account.balance,
            'amount': charge.amount,
            'timestamp': time.now(),
            'quorum_needed': 3,
            'expires_in': 30  # seconds
        }

    # Validated: When replicas confirm balance check
    def validate(self, evidence):
        confirmations = 0
        for replica in replicas:
            if replica.confirm_balance(evidence):
                confirmations += 1
        return confirmations >= evidence.quorum_needed

    # Active: When transaction commits with quorum
    def is_active(self, evidence):
        return (
            self.has_quorum(evidence) and
            time.now() < evidence.expires_in
        )

    # Expiring: When approaching timeout
    def is_expiring(self, evidence):
        time_left = evidence.expires_in - time.now()
        return 0 < time_left < 5  # Less than 5s left

    # Expired: When timeout or partition
    def is_expired(self, evidence):
        return (
            time.now() >= evidence.expires_in or
            not self.has_quorum(evidence)
        )

    # Recovery: When partition heals
    def recover(self):
        # Check for duplicate charges
        duplicates = find_duplicate_txn_ids()

        # Check for negative balances
        negative = find_negative_balances()

        # Reconcile with fraud detection
        for txn in duplicates + negative:
            if is_fraudulent(txn):
                reverse_transaction(txn)
            else:
                confirm_transaction(txn)
```

**Test 4**: Compare to GitHub outage
```python
# Similarities:
# - Both need global consistency
# - Both suffer from partition
# - Both require evidence-based degradation
# - Both need human intervention for recovery

# Differences:
# - Payments have stricter invariants (money conservation)
# - Payments can't "discard" diverged data (refund instead)
# - Payments need fraud detection during recovery
# - Payments have regulatory requirements (audit logs)

# Key lesson from GitHub:
# "Have a mode matrix BEFORE the outage, not during"
```

## Part IX: Canonical Lenses (STA + DCEH)

### STA Triad

**State**: What diverged and how

```python
# State divergence during outage
state_analysis = {
    # MySQL data diverged
    'repositories': {
        'east_only': 5,  # Created only on East
        'west_only': 3,  # Created only on West
        'conflicts': 1000,  # Same ID, different data
    },

    # Redis cache diverged
    'cache': {
        'east_entries': 1_000_000,
        'west_entries': 998_000,
        'divergence': 2000
    },

    # Elasticsearch index diverged
    'search_index': {
        'east_docs': 50_000_000,
        'west_docs': 49_998_500,
        'resync_required': True
    },

    # How to reconcile:
    'reconciliation_strategy': {
        'mysql': 'Choose East as authoritative',
        'redis': 'Invalidate all, rebuild',
        'elasticsearch': 'Reindex from MySQL'
    }
}
```

**Time**: How clocks and causality broke

```python
# Time analysis during outage
time_analysis = {
    # Clock skew
    'ntp_skew': {
        'east': '+0.5s',
        'west': '-0.3s',
        'max_skew': '0.8s'
    },

    # Causality lost
    'happens_before': {
        'east_txn_1001': '22:52:10.123',
        'west_txn_1001': '22:52:10.456',
        # Same ID, but which happened first?
        'causality': 'UNKNOWN'
    },

    # Ordering ambiguous
    'transaction_order': {
        'east_view': '[1001_east, 1002_east, 1003_east]',
        'west_view': '[1001_west, 1002_west, 1003_west]',
        'global_order': 'UNDEFINED - cannot merge'
    },

    # Recovery used wall-clock time (risky!)
    'recovery_heuristic': {
        'method': 'Choose earlier wall-clock timestamp',
        'risk': 'Clock skew could choose wrong transaction'
    }
}
```

**Agreement**: How consensus failed

```python
# Agreement analysis during outage
agreement_analysis = {
    # Raft consensus in Orchestrator
    'raft': {
        'quorum_needed': 3,
        'east_votes': 3,  # Quorum achieved
        'west_votes': 2,  # Quorum NOT achieved
        'bug': 'West claimed leadership with 2 votes',
        'root_cause': 'Off-by-one error in quorum check'
    },

    # MySQL replication
    'replication': {
        'normal_acks': 3,
        'partition_acks': 0,
        'should_have': 'Rejected writes',
        'actually_did': 'Accepted writes'
    },

    # What agreement was needed:
    'required_agreement': {
        'primary_election': 'Raft quorum (3/5)',
        'transaction_commit': 'Replication quorum (2/3)',
        'partition_healing': 'Manual agreement (operator choice)'
    }
}
```

### DCEH Planes

**Data Plane**: High-volume writes and reads

```python
# Data plane during outage
data_plane = {
    # Write path
    'writes': {
        'normal_rate': '10,000 writes/sec',
        'partition_rate_east': '6,000 writes/sec',
        'partition_rate_west': '4,000 writes/sec',
        'total': '10,000 writes/sec',  # Same total!
        'problem': 'Both regions accepting writes',
        'result': 'Diverged by 43 seconds × 10K writes/sec = 430K diverged writes'
    },

    # Read path
    'reads': {
        'normal_rate': '100,000 reads/sec',
        'partition_rate': '100,000 reads/sec',  # Reads continued
        'served_by': 'Local replicas',
        'consistency': 'Eventually consistent (broken)',
        'users_impacted': 'Saw stale data for 24 hours'
    },

    # What should have happened:
    'should_have_been': {
        'writes': 'Rejected on BOTH regions (no quorum)',
        'reads': 'Served with STALE warning',
        'user_experience': 'Degraded but CORRECT'
    }
}
```

**Control Plane**: Orchestration decisions

```python
# Control plane during outage
control_plane = {
    # Orchestrator decisions
    'orchestrator': {
        '22:52:05': 'Detected partition',
        '22:52:10': 'Initiated failover (East)',
        '22:52:15': 'Initiated failover (West)',  # MISTAKE
        'bug_location': 'quorum_check() function',
        'fix_applied': 'Changed >= to >'
    },

    # Human operators
    'humans': {
        '23:02:00': 'First alert received',
        '23:15:00': 'Severity understood',
        '23:30:00': 'Entered read-only mode',
        '00:00:00': 'All hands on deck',
        'Oct 22 16:24': 'Recovery plan approved',
        'Oct 23 06:00': 'Service restored'
    },

    # What control plane needed:
    'required_controls': {
        'detect': 'Partition detection (had this)',
        'decide': 'Mode matrix decision (lacked this)',
        'act': 'Automatic degradation (lacked this)',
        'verify': 'Evidence verification (lacked this)',
        'recover': 'Reconciliation protocol (lacked this)'
    }
}
```

**Evidence Plane**: The artifacts that should have triggered degradation

```python
# Evidence plane during outage
evidence_plane = {
    # Evidence that WAS available
    'available_evidence': {
        'heartbeat_loss': 'Detected at 22:52:05',
        'replication_lag': 'Climbing rapidly',
        'binlog_acks': 'Zero from West',
        'orchestrator_votes': 'Split 3-2'
    },

    # Evidence that SHOULD HAVE triggered action
    'trigger_points': {
        '22:52:05': {
            'evidence': 'heartbeat_loss',
            'should_trigger': 'Enter Degraded mode',
            'actually_did': 'Nothing'
        },
        '22:52:15': {
            'evidence': 'binlog_acks = 0 for 10s',
            'should_trigger': 'Enter Floor mode',
            'actually_did': 'Promoted West (catastrophic)'
        }
    },

    # Evidence-based mode transitions (what was needed)
    'mode_triggers': {
        'Target → Degraded': 'replication_lag > 1s',
        'Degraded → Floor': 'replication_lag > 30s OR partition_detected',
        'Floor → Recovery': 'operator_intervention + conflict_resolution_plan',
        'Recovery → Target': 'consistency_verified + replication_verified'
    },

    # Evidence gaps
    'missing_evidence': {
        'global_clock': 'No TrueTime equivalent',
        'quorum_certificate': 'No formal proof of primary',
        'reconciliation_proof': 'No automatic merge protocol'
    }
}
```

**Human Plane**: Operator mental models and actions

```python
# Human plane during outage
human_plane = {
    # Operator mental model
    'assumptions': {
        'network_reliable': False,  # Assumed true, was false
        'orchestrator_correct': False,  # Assumed true, was false
        'mysql_safe': False,  # Assumed failover was safe
        'recovery_fast': False  # Thought it would be quick
    },

    # Information available to operators
    'observability': {
        'could_see': [
            'Replication lag metrics',
            'Orchestrator logs',
            'MySQL slow query log',
            'Application error rate'
        ],
        'could_not_see': [
            'G-vector degradation',
            'Evidence expiration',
            'Mode transitions',
            'Context capsule failures'
        ]
    },

    # Actions operators could take
    'available_actions': {
        'safe': [
            'Enter read-only mode',
            'Stop Orchestrator',
            'Alert senior engineers'
        ],
        'risky': [
            'Choose authoritative primary',
            'Discard diverged data'
        ],
        'impossible': [
            'Automatically merge conflicted data',
            'Time-travel to prevent split brain'
        ]
    },

    # What operators needed
    'required_tools': {
        'mode_dashboard': 'Show current mode and G-vector',
        'evidence_viewer': 'Show evidence state and expiration',
        'degradation_controls': 'Explicit mode transition buttons',
        'runbook': 'Step-by-step recovery procedure',
        'simulation': 'Practice partition recovery'
    },

    # Lessons for human-in-the-loop
    'lessons': {
        'design_for_operators': 'Make current mode OBVIOUS',
        'principle_over_procedure': 'Teach G-vectors, not just steps',
        'practice_chaos': 'Regular partition drills',
        'automate_degradation': 'Don't rely on human reaction time'
    }
}
```

## Part X: Lessons Through the Framework Lens

### Lesson 1: Implicit Guarantees Fail Silently

**What GitHub thought they had**:
```python
g_assumed = '⟨Global, SS, SER, Fresh, Idem, Auth⟩'
```

**What they actually had**:
```python
g_actual = '⟨Global, SS, SER, Fresh, Idem, Auth⟩'  # Normal
g_partition = '⟨Regional, ???, ???, ???, ???, ???⟩'  # Undefined!
```

**Framework insight**: Without explicit G-vectors at every boundary, you don't know what guarantees you have during failure.

### Lesson 2: Degradation Requires Advance Planning

**GitHub's approach**: Ad-hoc decisions during incident

**Framework approach**: Mode matrix defined beforehand
```
Every service should have:
- Target mode (normal operation)
- Degraded modes (predictable failures)
- Floor mode (minimum viable)
- Recovery mode (path back to target)
- Evidence-based transition triggers
```

### Lesson 3: Evidence Expiration Must Trigger Action

**GitHub's failure**: Evidence expired but writes continued

**Framework principle**: Expired evidence FORCES downgrade
```python
if evidence.is_expired():
    transition_to_floor_mode()  # Automatic, no debate
```

### Lesson 4: Composition Requires Explicit Contracts

**GitHub's architecture**: Services composed without guarantee contracts

**Framework approach**: Context capsules at every boundary
```python
service_a.response_capsule = {
    'g_vector': '⟨Regional, Causal, RA, BS(30s), Idem, Auth⟩',
    'mode': 'degraded',
    'evidence': 'EXPIRED'
}

service_b.check_capsule(service_a.response_capsule)
# If incompatible, reject or downgrade further
```

### Lesson 5: Recovery Is an Evidence Generation Process

**GitHub's mistake**: Thought recovery was "flip switch to primary"

**Framework insight**: Recovery = generating new evidence
- Choose authoritative source (manual evidence)
- Verify consistency (checksum evidence)
- Replay transactions (causality evidence)
- Restart replication (quorum evidence)
- Verify no conflicts (reconciliation evidence)

Each step generates evidence needed to upgrade G-vector back to target.

## Mental Model Summary

**GitHub's outage through the framework**:

1. **G-vectors collapsed** from `⟨Global, SS, SER, Fresh, Idem, Auth⟩` to `⟨Object, None, Fractured, EO, None, Unauth⟩` because:
   - Network partition eliminated global scope
   - Split brain eliminated ordering
   - Diverged data eliminated serializability
   - Lost replication eliminated freshness

2. **Context capsules failed** to propagate across partition, leading to:
   - East believing it was authoritative
   - West believing it was authoritative
   - No mechanism to detect incompatibility

3. **Evidence expired** but didn't trigger mode transitions:
   - Binlog acknowledgments stopped
   - Should have entered Floor mode
   - Instead continued accepting writes

4. **Mode matrix was absent**:
   - No predefined degradation strategy
   - Ad-hoc decisions during incident
   - 24-hour recovery instead of minutes

5. **Dualities resolved incorrectly**:
   - Chose Liveness over Safety (broke PK uniqueness)
   - Chose Local over Global (broke ordering)
   - Chose Trust over Evidence (caused split brain)

**The revolutionary insight**: If GitHub had defined G-vectors, context capsules, and mode matrices beforehand, the outage would have been:
- Automatically degraded to Floor mode (reject writes)
- Duration: 43 seconds (partition length) instead of 24 hours
- Impact: Read-only mode instead of data loss
- Recovery: Automatic when partition healed

This is the power of the framework: turning catastrophic failures into predictable degradations.

---

**Context capsule for next case study**:
```
{
  invariant: "Configuration_Consistency",
  evidence: "S3_outage_teaches_blast_radius",
  boundary: "service_dependencies",
  mode: "analyzing_cascade_failures",
  g_vector: "⟨Global, Causal, RA, BS(examples), Idem, Auth(research)⟩"
}
```

Continue to [AWS S3 Outage →](aws-s3.md)