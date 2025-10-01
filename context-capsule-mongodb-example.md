# Context Capsule Example: MongoDB Primary Election Stall

## The Scenario

In 2019, network flakiness caused MongoDB leader election to take 47 seconds (should be <10s). During that time, no writes were accepted. Cost: **$2.3M in lost transactions** for one customer.

This document shows how **Context Capsules** would make this degradation explicit, trackable, and actionable.

---

## 1. Capsule During Normal Operation (Target Mode)

### Write Request to Primary

When the MongoDB cluster operates normally with a stable primary, write requests carry this capsule:

```json
{
  "invariant": "SingleWriter",
  "evidence": {
    "type": "PrimaryLease",
    "holder": "mongo-replica-1",
    "epoch": 42,
    "issued_at": "2019-05-15T14:23:11.000Z",
    "expires_at": "2019-05-15T14:23:21.000Z",
    "quorum_cert": {
      "term": 42,
      "voters": ["mongo-replica-1", "mongo-replica-2", "mongo-replica-3"],
      "signatures": ["sig1...", "sig2...", "sig3..."]
    }
  },
  "boundary": {
    "scope": "cluster:production-mongo-main",
    "region": "us-east-1",
    "epoch": 42
  },
  "mode": "Target",
  "fallback": {
    "on_expired_lease": "Degraded:ReadOnly",
    "on_lost_quorum": "Recovery:RefuseWrites"
  },

  "order": "Linearizable",
  "recency": "Fresh(QuorumWrite)",
  "identity": {
    "service": "payment-service",
    "tenant": "customer-12345",
    "request_id": "req-abc-123",
    "nonce": "0x4f3a..."
  },
  "trace": {
    "causality_token": "payment-txn-789",
    "session_id": "sess-xyz-456",
    "parent_span": "span-checkout-001"
  },
  "obligations": {
    "receiver_must_check": [
      "lease.expires_at > now()",
      "epoch == current_epoch",
      "quorum_cert.term == epoch"
    ],
    "receiver_must_return": [
      "write_concern_acknowledged",
      "majority_committed_lsn"
    ]
  }
}
```

### What Each Field Means

**invariant**: `SingleWriter`
- Only one node can accept writes at a time
- Prevents split-brain scenarios
- Foundation of linearizability

**evidence**: `PrimaryLease`
- **Type**: Lease-based primary authority
- **Holder**: Which replica holds the lease
- **Epoch**: Monotonic term number (Raft/Paxos term)
- **Lifetime**: 10-second lease (renewable)
- **Quorum Certificate**: Proof that majority agreed this node is primary in term 42

**boundary**:
- **Scope**: Which cluster this applies to
- **Region**: Physical location constraint
- **Epoch**: Changes on every election, invalidates old evidence

**mode**: `Target`
- Full guarantees in effect
- Linearizable writes accepted
- Primary is stable and healthy

**fallback**:
- **on_expired_lease**: Drop to read-only mode if lease cannot be renewed
- **on_lost_quorum**: Enter recovery, refuse all writes until new primary elected

**Optional Fields**:
- **order**: `Linearizable` - strongest ordering guarantee
- **recency**: `Fresh(QuorumWrite)` - write visible after quorum ack
- **identity**: Request tracking for auditing
- **trace**: Distributed tracing context
- **obligations**: Contract enforcement - receiver MUST verify lease freshness

---

## 2. Capsule During Election Stall (Degraded Mode)

### T+0s: Network Flakiness Begins

The primary node (mongo-replica-1) starts experiencing network packet loss. It cannot renew its lease because it cannot reach a quorum of replicas.

### T+10s: Lease Expires

At T+10s, the primary's lease expires. The capsule **automatically degrades**:

```json
{
  "invariant": "SafetyFirst",
  "evidence": {
    "type": "ExpiredLease",
    "former_holder": "mongo-replica-1",
    "epoch": 42,
    "expired_at": "2019-05-15T14:23:21.000Z",
    "expiry_detected_at": "2019-05-15T14:23:21.003Z",
    "reason": "QuorumUnreachable",
    "last_successful_heartbeat": {
      "timestamp": "2019-05-15T14:23:18.500Z",
      "replicas": ["mongo-replica-1", "mongo-replica-2"]
    }
  },
  "boundary": {
    "scope": "cluster:production-mongo-main",
    "region": "us-east-1",
    "epoch": 42,
    "degraded_since": "2019-05-15T14:23:21.003Z"
  },
  "mode": "Degraded:NoWrites",
  "fallback": {
    "current_policy": "RefuseWrites",
    "on_election_success": "Recovery:ValidationRequired",
    "on_election_timeout": "Degraded:AlertOperators"
  },

  "order": "Undefined",
  "recency": "BoundedStaleness(10s)",
  "identity": {
    "service": "payment-service",
    "tenant": "customer-12345",
    "request_id": "req-abc-124",
    "nonce": "0x5a2b..."
  },
  "trace": {
    "causality_token": "payment-txn-790",
    "session_id": "sess-xyz-456",
    "parent_span": "span-checkout-002",
    "degradation_event": "evt-lease-expired-001"
  },
  "obligations": {
    "receiver_must_check": [
      "mode == Degraded",
      "no writes accepted"
    ],
    "receiver_must_return": [
      "error: NotWritableReplica",
      "reason: LeaseExpired",
      "estimated_recovery_time: Unknown",
      "current_epoch: 42",
      "election_in_progress: true"
    ]
  }
}
```

### What Changed

**invariant**: `SingleWriter` → `SafetyFirst`
- Cannot guarantee single writer
- Can guarantee no conflicting writes (refuse all writes)
- Safety preserved at cost of availability

**evidence**: `PrimaryLease` → `ExpiredLease`
- **Type**: Evidence of absence (lease expired)
- **Reason**: Cannot reach quorum for renewal
- **Last heartbeat**: Only 2/3 replicas reachable
- **Forensics**: Timestamp trail for debugging

**mode**: `Target` → `Degraded:NoWrites`
- Explicit degradation label
- Write operations rejected
- Read operations may continue (with staleness warning)

**order**: `Linearizable` → `Undefined`
- Cannot provide ordering guarantees without primary
- Downstream services must handle this explicitly

**recency**: `Fresh(QuorumWrite)` → `BoundedStaleness(10s)`
- Reads may be up to 10s stale (lease expiry window)
- Maximum staleness bounded by lease duration

**obligations**:
- Receiver MUST reject writes
- MUST return structured error with:
  - Current mode (Degraded)
  - Reason for rejection (LeaseExpired)
  - Election status (in progress)
  - No false promises about recovery time

---

## 3. Capsule During Recovery (After Election Completes)

### T+47s: New Primary Elected

After 47 seconds, mongo-replica-2 wins the election and becomes primary in epoch 43.

### Initial Recovery Capsule

```json
{
  "invariant": "SingleWriter",
  "evidence": {
    "type": "PrimaryLease",
    "holder": "mongo-replica-2",
    "epoch": 43,
    "issued_at": "2019-05-15T14:24:08.000Z",
    "expires_at": "2019-05-15T14:24:18.000Z",
    "quorum_cert": {
      "term": 43,
      "voters": ["mongo-replica-2", "mongo-replica-3", "mongo-replica-4"],
      "signatures": ["sig4...", "sig5...", "sig6..."]
    },
    "election_metadata": {
      "previous_epoch": 42,
      "election_duration_ms": 47000,
      "election_reason": "LeaseExpiry",
      "votes_received": 3,
      "quorum_size": 3
    }
  },
  "boundary": {
    "scope": "cluster:production-mongo-main",
    "region": "us-east-1",
    "epoch": 43,
    "recovered_at": "2019-05-15T14:24:08.000Z",
    "outage_duration_ms": 47000
  },
  "mode": "Recovery:CatchupInProgress",
  "fallback": {
    "on_expired_lease": "Degraded:ReadOnly",
    "on_lost_quorum": "Recovery:RefuseWrites"
  },

  "order": "Linearizable",
  "recency": "BoundedStaleness(5s)",
  "identity": {
    "service": "payment-service",
    "tenant": "customer-12345",
    "request_id": "req-abc-125",
    "nonce": "0x6b3c..."
  },
  "trace": {
    "causality_token": "payment-txn-791",
    "session_id": "sess-xyz-456",
    "parent_span": "span-checkout-003",
    "recovery_event": "evt-election-complete-001"
  },
  "obligations": {
    "receiver_must_check": [
      "lease.expires_at > now()",
      "epoch > previous_epoch",
      "quorum_cert.term == epoch"
    ],
    "receiver_must_return": [
      "write_accepted: true",
      "mode: Recovery",
      "latency_warning: Elevated",
      "majority_committed_lsn"
    ],
    "receiver_should_warn": [
      "System recently recovered from 47s outage",
      "Writes accepted but latency may be elevated",
      "Replica catchup in progress"
    ]
  }
}
```

### What Changed

**mode**: `Degraded:NoWrites` → `Recovery:CatchupInProgress`
- Writes now accepted (primary elected)
- But system is still recovering
- Replicas catching up on missed writes

**evidence**: Includes election metadata
- **election_duration_ms**: 47000ms (explains the outage)
- **previous_epoch**: 42 (continuity check)
- **votes_received**: Proof of quorum agreement

**recency**: Still degraded to `BoundedStaleness(5s)`
- Replicas catching up
- Read-your-writes may be delayed
- Staleness bounds tighter than during outage but looser than normal

**obligations**: Includes warnings
- Clients informed system is in recovery
- Latency may be elevated
- Transparency about recent outage

### T+2min: Full Recovery

After replicas catch up, system returns to Target mode with full guarantees.

---

## 4. Timeline: Capsule Evolution During Incident

```
T-10s ════════════════════════════════════════════════════════════
      MODE: Target
      WRITES: Accepted (10ms p99 latency)
      CAPSULE: { invariant: SingleWriter, evidence: PrimaryLease, mode: Target }

T+0s  Network flakiness begins
      ↓ Primary (mongo-replica-1) loses connectivity to replicas

T+5s  ════════════════════════════════════════════════════════════
      MODE: Target (lease still valid)
      WRITES: Accepted (increasing latency, 50ms p99)
      CAPSULE: { invariant: SingleWriter, evidence: PrimaryLease, mode: Target }
      WARNING: Lease renewal attempts failing

T+10s LEASE EXPIRES ⚠️
      ════════════════════════════════════════════════════════════
      MODE: Degraded:NoWrites
      WRITES: REFUSED ❌
      CAPSULE: { invariant: SafetyFirst, evidence: ExpiredLease, mode: Degraded:NoWrites }
      REASON: QuorumUnreachable

      CAPSULE CHANGES:
      ✓ invariant: SingleWriter → SafetyFirst
      ✓ evidence.type: PrimaryLease → ExpiredLease
      ✓ mode: Target → Degraded:NoWrites
      ✓ order: Linearizable → Undefined
      ✓ recency: Fresh(QuorumWrite) → BoundedStaleness(10s)

T+10s to T+47s: ELECTION IN PROGRESS
      ════════════════════════════════════════════════════════════
      37 seconds of write unavailability

      Transaction attempts: ~15,000
      Transactions refused: ~15,000
      Revenue impact: $2.3M

      Capsule returned to clients:
      {
        mode: "Degraded:NoWrites",
        error: "NotWritableReplica",
        reason: "LeaseExpired",
        election_in_progress: true,
        estimated_recovery: "Unknown"
      }

T+47s NEW PRIMARY ELECTED ✓
      ════════════════════════════════════════════════════════════
      MODE: Recovery:CatchupInProgress
      WRITES: Accepted (degraded latency, 200ms p99)
      CAPSULE: { invariant: SingleWriter, evidence: PrimaryLease, mode: Recovery, epoch: 43 }

      CAPSULE CHANGES:
      ✓ invariant: SafetyFirst → SingleWriter
      ✓ evidence.type: ExpiredLease → PrimaryLease
      ✓ evidence.epoch: 42 → 43
      ✓ mode: Degraded:NoWrites → Recovery:CatchupInProgress
      ✓ order: Undefined → Linearizable
      ✓ recency: BoundedStaleness(10s) → BoundedStaleness(5s)

T+2min Full replica catchup complete
      ════════════════════════════════════════════════════════════
      MODE: Target
      WRITES: Accepted (10ms p99 latency)
      CAPSULE: { invariant: SingleWriter, evidence: PrimaryLease, mode: Target, recency: Fresh }

      CAPSULE CHANGES:
      ✓ mode: Recovery:CatchupInProgress → Target
      ✓ recency: BoundedStaleness(5s) → Fresh(QuorumWrite)
      ✓ obligations: Removed recovery warnings
```

---

## 5. How Capsules Flow Across Boundaries

### Service A (Payment Service) → MongoDB

**Request**: Process payment of $150

```json
{
  "operation": "write",
  "collection": "payments",
  "document": { "amount": 150, "customer": "12345" },
  "capsule": {
    "invariant": "SingleWriter",
    "required_guarantees": {
      "order": "Linearizable",
      "recency": "Fresh(QuorumWrite)",
      "durability": "Majority"
    },
    "acceptable_modes": ["Target"],
    "reject_if": ["Degraded", "Recovery"],
    "identity": {
      "service": "payment-service",
      "request_id": "req-payment-001"
    }
  }
}
```

**MongoDB Response During Target Mode**:

```json
{
  "status": "success",
  "write_acknowledged": true,
  "capsule": {
    "invariant": "SingleWriter",
    "evidence": { "type": "PrimaryLease", "epoch": 42, "expires_at": "..." },
    "mode": "Target",
    "order": "Linearizable",
    "recency": "Fresh(QuorumWrite)",
    "obligations_met": ["write_concern_acknowledged", "majority_committed"]
  }
}
```

**MongoDB Response During Degraded Mode**:

```json
{
  "status": "error",
  "error_code": "NotWritableReplica",
  "capsule": {
    "invariant": "SafetyFirst",
    "evidence": { "type": "ExpiredLease", "expired_at": "..." },
    "mode": "Degraded:NoWrites",
    "reason": "LeaseExpired",
    "election_in_progress": true,
    "order": "Undefined",
    "recency": "BoundedStaleness(10s)",
    "obligations_met": ["safety_preserved", "no_conflicting_writes"]
  }
}
```

### Payment Service → Customer

**Without Capsule Awareness** (Bad):

```
Error 500: Internal Server Error
(Customer sees generic error, no context)
```

**With Capsule Awareness** (Good):

```json
{
  "status": "unavailable",
  "error": "ServiceDegraded",
  "message": "Payment processing temporarily unavailable",
  "details": {
    "reason": "Database leader election in progress",
    "mode": "Degraded:NoWrites",
    "estimated_recovery": "Unknown",
    "retry_after_seconds": 30,
    "alternative_actions": [
      "Try again in 30 seconds",
      "Use alternative payment method",
      "Contact support if urgent"
    ]
  },
  "capsule": {
    "invariant": "Transparency",
    "mode": "Degraded:Informational",
    "evidence": {
      "type": "DownstreamDegraded",
      "service": "mongodb",
      "propagated_from": "payment-database"
    }
  }
}
```

---

## 6. Capsule Validation Code

### MongoDB Primary: Lease Validation

```python
class PrimaryNode:
    def __init__(self):
        self.current_lease = None
        self.epoch = 0

    def handle_write_request(self, request):
        """Validate capsule before accepting write."""

        # Check if we have valid primary lease
        capsule = self.get_current_capsule()

        # Validate lease freshness
        validation = self.validate_capsule(capsule)

        if not validation.valid:
            # Return degraded capsule
            return {
                "status": "error",
                "error_code": "NotWritableReplica",
                "capsule": self.create_degraded_capsule(validation.reason)
            }

        # Process write with target mode capsule
        result = self.execute_write(request)
        result["capsule"] = capsule
        return result

    def validate_capsule(self, capsule):
        """Enforce capsule obligations."""

        # OBLIGATION 1: lease.expires_at > now()
        if capsule.evidence.expires_at <= time.now():
            return ValidationResult(
                valid=False,
                reason="LeaseExpired",
                required_mode="Degraded:NoWrites"
            )

        # OBLIGATION 2: epoch == current_epoch
        if capsule.boundary.epoch != self.epoch:
            return ValidationResult(
                valid=False,
                reason="EpochMismatch",
                required_mode="Recovery:StaleEpoch"
            )

        # OBLIGATION 3: quorum_cert.term == epoch
        if capsule.evidence.quorum_cert.term != self.epoch:
            return ValidationResult(
                valid=False,
                reason="QuorumCertificateInvalid",
                required_mode="Recovery:InvalidEvidence"
            )

        # All obligations met
        return ValidationResult(valid=True)

    def get_current_capsule(self):
        """Generate capsule based on current state."""

        if self.has_valid_lease():
            return self.create_target_capsule()
        else:
            return self.create_degraded_capsule("LeaseExpired")

    def create_target_capsule(self):
        """Target mode: full guarantees."""
        return {
            "invariant": "SingleWriter",
            "evidence": {
                "type": "PrimaryLease",
                "holder": self.node_id,
                "epoch": self.epoch,
                "issued_at": self.current_lease.issued_at,
                "expires_at": self.current_lease.expires_at,
                "quorum_cert": self.current_lease.quorum_cert
            },
            "boundary": {
                "scope": self.cluster_id,
                "region": self.region,
                "epoch": self.epoch
            },
            "mode": "Target",
            "fallback": {
                "on_expired_lease": "Degraded:ReadOnly",
                "on_lost_quorum": "Recovery:RefuseWrites"
            },
            "order": "Linearizable",
            "recency": "Fresh(QuorumWrite)"
        }

    def create_degraded_capsule(self, reason):
        """Degraded mode: safety preserved, availability reduced."""
        return {
            "invariant": "SafetyFirst",
            "evidence": {
                "type": "ExpiredLease",
                "former_holder": self.node_id,
                "epoch": self.epoch,
                "expired_at": self.current_lease.expires_at if self.current_lease else None,
                "expiry_detected_at": time.now(),
                "reason": reason
            },
            "boundary": {
                "scope": self.cluster_id,
                "region": self.region,
                "epoch": self.epoch,
                "degraded_since": time.now()
            },
            "mode": "Degraded:NoWrites",
            "fallback": {
                "current_policy": "RefuseWrites",
                "on_election_success": "Recovery:ValidationRequired"
            },
            "order": "Undefined",
            "recency": "BoundedStaleness(10s)"
        }

    def has_valid_lease(self):
        """Check if current lease is still valid."""
        if not self.current_lease:
            return False

        return (
            self.current_lease.expires_at > time.now() and
            self.can_reach_quorum()
        )

    def can_reach_quorum(self):
        """Check if we can reach majority of replicas."""
        reachable = self.count_reachable_replicas()
        quorum_size = (len(self.replicas) // 2) + 1
        return reachable >= quorum_size
```

### Payment Service: Capsule-Aware Client

```python
class PaymentService:
    def __init__(self, mongo_client):
        self.mongo = mongo_client

    def process_payment(self, payment_data):
        """Process payment with capsule awareness."""

        # Create request with required guarantees
        request = {
            "operation": "write",
            "collection": "payments",
            "document": payment_data,
            "capsule": {
                "invariant": "SingleWriter",
                "required_guarantees": {
                    "order": "Linearizable",
                    "recency": "Fresh(QuorumWrite)",
                    "durability": "Majority"
                },
                "acceptable_modes": ["Target"],
                "reject_if": ["Degraded", "Recovery"]
            }
        }

        try:
            response = self.mongo.write(request)

            # Check response capsule
            if not self.validate_response_capsule(response.capsule, request.capsule):
                return self.handle_degraded_response(response)

            # Success with target guarantees
            return {
                "status": "success",
                "transaction_id": response.id,
                "guarantees_met": response.capsule
            }

        except MongoException as e:
            return self.handle_mongo_error(e)

    def validate_response_capsule(self, response_capsule, request_capsule):
        """Validate that response meets requested guarantees."""

        # Check mode
        if response_capsule.mode not in request_capsule.acceptable_modes:
            logger.warning(
                f"Mode mismatch: got {response_capsule.mode}, "
                f"acceptable: {request_capsule.acceptable_modes}"
            )
            return False

        # Check order guarantee
        if response_capsule.order != request_capsule.required_guarantees.order:
            logger.warning(
                f"Order downgrade: requested {request_capsule.required_guarantees.order}, "
                f"got {response_capsule.order}"
            )
            return False

        # Check recency guarantee
        if not self.recency_sufficient(
            response_capsule.recency,
            request_capsule.required_guarantees.recency
        ):
            logger.warning(
                f"Recency downgrade: requested {request_capsule.required_guarantees.recency}, "
                f"got {response_capsule.recency}"
            )
            return False

        return True

    def handle_degraded_response(self, response):
        """Handle degraded mode gracefully."""

        capsule = response.capsule

        # Log degradation for observability
        logger.error(
            f"Database in degraded mode",
            extra={
                "mode": capsule.mode,
                "reason": capsule.evidence.get("reason"),
                "epoch": capsule.boundary.epoch,
                "degraded_since": capsule.boundary.get("degraded_since")
            }
        )

        # Emit metric
        metrics.increment(
            "database.degraded_requests",
            tags={
                "mode": capsule.mode,
                "reason": capsule.evidence.get("reason")
            }
        )

        # Return structured error to caller
        return {
            "status": "unavailable",
            "error": "ServiceDegraded",
            "details": {
                "service": "payment-database",
                "mode": capsule.mode,
                "reason": capsule.evidence.get("reason"),
                "retry_after": 30
            },
            "capsule": {
                "invariant": "Transparency",
                "mode": "Degraded:Informational",
                "evidence": {
                    "type": "DownstreamDegraded",
                    "service": "mongodb",
                    "propagated_from": capsule
                }
            }
        }
```

---

## 7. How Operators Use Capsule Information

### Real-Time Monitoring Dashboard

```
┌─────────────────────────────────────────────────────────┐
│ MongoDB Cluster: production-mongo-main                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ CURRENT MODE: Degraded:NoWrites                    ⚠️  │
│ EPOCH: 42                                               │
│ DEGRADED SINCE: 2019-05-15T14:23:21.003Z (37s ago)     │
│                                                         │
│ REASON: LeaseExpired                                    │
│ EVIDENCE: QuorumUnreachable                             │
│                                                         │
│ ELECTION STATUS: In Progress                            │
│ CANDIDATES: mongo-replica-2, mongo-replica-3            │
│ VOTES RECEIVED: 2/3 (need 3)                            │
│                                                         │
│ IMPACT:                                                 │
│ - Write Requests Refused: 15,247                        │
│ - Estimated Revenue Loss: $2,301,450                    │
│ - Affected Services: payment-service, order-service     │
│                                                         │
│ CAPSULE DETAILS:                                        │
│ {                                                       │
│   "invariant": "SafetyFirst",                          │
│   "evidence": {                                         │
│     "type": "ExpiredLease",                            │
│     "reason": "QuorumUnreachable",                     │
│     "last_successful_heartbeat": "14:23:18.500Z"       │
│   },                                                    │
│   "mode": "Degraded:NoWrites"                          │
│ }                                                       │
│                                                         │
│ OPERATOR ACTIONS:                                       │
│ [Check Network] [Force Election] [View Logs]           │
└─────────────────────────────────────────────────────────┘
```

### Alert Triggered

```
CRITICAL: MongoDB Cluster Degraded

Cluster: production-mongo-main
Mode: Degraded:NoWrites
Duration: 37 seconds
Impact: $2.3M in lost transactions

CAPSULE EVIDENCE:
- Invariant: SafetyFirst
- Evidence Type: ExpiredLease
- Reason: QuorumUnreachable
- Epoch: 42
- Last Heartbeat: 14:23:18.500Z (2/3 replicas)

ELECTION STATUS:
- In Progress: Yes
- Candidates: mongo-replica-2, mongo-replica-3
- Votes: 2/3 (waiting for quorum)

RECOMMENDED ACTIONS:
1. Check network connectivity between replicas
2. Verify firewall rules (port 27017)
3. Review packet loss metrics
4. Consider manual intervention if election exceeds 60s

AFFECTED SERVICES:
- payment-service: 8,432 requests refused
- order-service: 6,815 requests refused

RUNBOOK: https://wiki.company.com/mongodb-degraded-mode
```

### Post-Incident Analysis

```python
# Query capsule history
capsule_history = get_capsule_timeline(
    cluster="production-mongo-main",
    start="2019-05-15T14:23:00Z",
    end="2019-05-15T14:26:00Z"
)

# Analyze mode transitions
for event in capsule_history:
    print(f"{event.timestamp}: {event.mode}")
    print(f"  Evidence: {event.evidence.type}")
    print(f"  Reason: {event.evidence.get('reason')}")
    print(f"  Epoch: {event.boundary.epoch}")
    print()

# Output:
# 2019-05-15T14:23:11.000Z: Target
#   Evidence: PrimaryLease
#   Reason: None
#   Epoch: 42
#
# 2019-05-15T14:23:21.003Z: Degraded:NoWrites
#   Evidence: ExpiredLease
#   Reason: QuorumUnreachable
#   Epoch: 42
#
# 2019-05-15T14:24:08.000Z: Recovery:CatchupInProgress
#   Evidence: PrimaryLease
#   Reason: ElectionComplete
#   Epoch: 43
#
# 2019-05-15T14:26:15.000Z: Target
#   Evidence: PrimaryLease
#   Reason: ReplicaCatchupComplete
#   Epoch: 43

# Calculate impact
degraded_duration = calculate_duration(
    start_mode="Degraded:NoWrites",
    end_mode="Recovery:CatchupInProgress"
)
print(f"Degraded duration: {degraded_duration}s")  # 47s

refused_requests = count_refused_requests(
    during=degraded_duration
)
print(f"Refused requests: {refused_requests}")  # 15,247

revenue_loss = calculate_revenue_loss(
    refused_requests=refused_requests,
    avg_transaction_value=150
)
print(f"Revenue loss: ${revenue_loss:,.2f}")  # $2,287,050

# Root cause
root_cause = analyze_evidence_trail(
    capsule_history,
    focus="evidence.reason"
)
print(f"Root cause: {root_cause}")
# "QuorumUnreachable due to network packet loss (12% loss rate) on mongo-replica-1"
```

---

## 8. Connection to $2.3M Loss

### Without Capsules (What Actually Happened)

**Operator Perspective**:
```
15:23:21 - ERROR: Write failed (NotWritableReplica)
15:23:22 - ERROR: Write failed (NotWritableReplica)
15:23:23 - ERROR: Write failed (NotWritableReplica)
...
(15,000 error messages)
...

WHY? Unknown
WHEN DID IT START? Unknown
WHAT MODE ARE WE IN? Unknown
WHEN WILL IT RECOVER? Unknown
HOW MANY TRANSACTIONS LOST? Unknown
IS THIS A SPLIT-BRAIN? Unknown
```

**Customer Perspective**:
```
Error 500: Internal Server Error
(No context, no transparency, customer abandons purchase)
```

**Business Impact**:
- 47 seconds of complete write unavailability
- ~15,000 payment transactions refused
- Customers see generic errors
- No transparency about recovery
- **Result**: $2.3M in lost revenue

### With Capsules (What Could Have Happened)

**Operator Perspective**:
```
15:23:21 - MODE CHANGE: Target → Degraded:NoWrites
           REASON: LeaseExpired (QuorumUnreachable)
           EVIDENCE: Last heartbeat 2/3 replicas at 15:23:18.500Z
           IMPACT: Writes refused, reads allowed (10s staleness)
           ELECTION: In progress

Dashboard shows:
- Clear mode: Degraded:NoWrites
- Clear reason: LeaseExpired
- Clear evidence: Cannot reach quorum
- Clear impact: $X/second in lost transactions
- Clear status: Election in progress (2/3 votes)

OPERATOR ACTION:
- Checks network dashboard
- Sees 12% packet loss on mongo-replica-1
- Fixes network issue
- Election completes in 47s
```

**Customer Perspective**:
```json
{
  "status": "unavailable",
  "message": "Payment processing temporarily unavailable due to database maintenance",
  "retry_after": 30,
  "alternatives": [
    "Try again in 30 seconds",
    "Use alternative payment method"
  ]
}
```

**Business Impact**:
- 47 seconds of write unavailability (same)
- ~15,000 transactions delayed (not lost)
- Customers see informative errors
- Clear retry guidance
- Some transactions succeed on retry
- **Result**: Reduced loss, better customer experience

---

## 9. Key Insights

### 1. Degradation is Explicit

**Without Capsules**:
- System silently degrades
- Errors are opaque ("NotWritableReplica")
- No machine-readable context

**With Capsules**:
- Mode change is explicit (Target → Degraded:NoWrites)
- Evidence explains why (LeaseExpired due to QuorumUnreachable)
- Structured information enables automation

### 2. Guarantees are Verifiable

**Without Capsules**:
- Clients trust server implicitly
- No proof of linearizability
- No way to detect violations

**With Capsules**:
- Evidence field carries proof (quorum certificate)
- Obligations enforce verification
- Violations are detectable

### 3. Composition is Safe

**Without Capsules**:
- Degradation hides in error codes
- Downstream services can't react appropriately
- Guarantees silently weaken

**With Capsules**:
- Degradation propagates explicitly
- Downstream services see mode changes
- Weakest guarantee governs end-to-end

### 4. Observability is Built-In

**Without Capsules**:
- Need separate monitoring infrastructure
- Correlation is manual
- Root cause unclear

**With Capsules**:
- Capsule history IS the timeline
- Evidence trail shows root cause
- Impact calculable from mode changes

### 5. FLP Impossibility Made Explicit

The MongoDB election stall is **FLP impossibility in production**:

- Cannot guarantee bounded-time consensus in asynchronous systems
- Network flakiness = asynchrony
- 47-second election = unbounded time

**Capsules make this explicit**:
```json
{
  "mode": "Degraded:NoWrites",
  "evidence": {
    "type": "ExpiredLease",
    "reason": "QuorumUnreachable"
  },
  "invariant": "SafetyFirst"
}
```

Translation: "We cannot prove we're the primary (FLP), so we refuse writes (safety)."

---

## 10. Summary

### The MongoDB Election Stall in Capsule Terms

1. **Target Mode**: Primary holds lease, writes accepted with linearizability
2. **Lease Expiry**: Evidence expires, cannot renew (quorum unreachable)
3. **Degraded Mode**: No primary, all writes refused (safety preserved)
4. **Election**: FLP impossibility manifests (47s unbounded time)
5. **Recovery Mode**: New primary elected, writes resume (elevated latency)
6. **Target Mode**: Replicas caught up, full guarantees restored

### What Capsules Provide

- **Explicit modes**: Target, Degraded, Recovery
- **Verifiable evidence**: Leases, quorum certificates, timestamps
- **Clear boundaries**: Scope, epoch, valid domains
- **Principled fallbacks**: Degrade to safety, not failure
- **Composable guarantees**: Propagate mode changes across services
- **Built-in observability**: Evidence trail for debugging

### The Cost of Not Having Capsules

- $2.3M in lost transactions
- Opaque errors to customers
- Difficult root cause analysis
- No structured recovery process
- Silent degradation
- Impossible to reason about guarantees

### The Value of Having Capsules

- Explicit degradation tracking
- Transparent communication to customers
- Clear evidence for operators
- Principled recovery process
- Verifiable guarantees
- FLP impossibility made concrete and actionable
