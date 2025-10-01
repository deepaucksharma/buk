# Chapter Crafting Implementation Templates
## A Comprehensive Toolkit for Applying the Unified Mental Model Authoring Framework 3.0

This document provides reusable, fill-in-the-blank templates, schemas, and tools that authors can use to transform chapters according to the ChapterCraftingGuide.md framework. Each template includes field descriptions, examples, validation rules, and best practices.

---

## Table of Contents

1. [Guarantee Vector Template](#1-guarantee-vector-template)
2. [Mode Matrix Generator](#2-mode-matrix-generator)
3. [Evidence Card Template](#3-evidence-card-template)
4. [Context Capsule Schema](#4-context-capsule-schema)
5. [Sacred Diagram ASCII Templates](#5-sacred-diagram-ascii-templates)
6. [Chapter Development Canvas](#6-chapter-development-canvas)
7. [Supporting Tools](#7-supporting-tools)

---

## 1. Guarantee Vector Template

### 1.1 YAML Format Specification

```yaml
# Guarantee Vector Specification
# G = ⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩

system_name: "FollowerReads"
description: "Reading from replicas with freshness guarantees"

# Initial Guarantee Vector
initial_vector:
  scope: "Range"              # {Object, Range, Transaction, Global}
  order: "Lx"                 # {None, Causal, Lx, SS}
  visibility: "SI"            # {Fractured, RA, SI, SER}
  recency: "Fresh(φ)"         # {EO, BS(δ), Fresh(φ)}
  idempotence: "Idem(K)"      # {None, Idem(K)}
  auth: "Auth(π)"             # {Unauth, Auth(π)}

# Evidence Requirements for Each Component
evidence_requirements:
  scope:
    type: "Range identifier"
    scope: "Per range/shard"
    lifetime: "Epoch duration"
    binding: "Range ID + epoch"

  order:
    type: "Read-index receipt"
    scope: "Per replica"
    lifetime: "Until next leadership change"
    binding: "Leader epoch + position"

  visibility:
    type: "Snapshot isolation token"
    scope: "Transaction or read timestamp"
    lifetime: "Transaction duration"
    binding: "Timestamp + range"

  recency:
    type: "Closed timestamp φ or lease epoch E"
    scope: "Range-level"
    lifetime: "Heartbeat interval (e.g., 9s)"
    binding: "Range + epoch + timestamp"
    revocation: "Leadership change or lease expiry"

  idempotence:
    type: "Request deduplication key K"
    scope: "Per operation"
    lifetime: "Deduplication window"
    binding: "Client ID + sequence number"

  auth:
    type: "Authenticated identity π"
    scope: "Per request"
    lifetime: "Session or token lifetime"
    binding: "Tenant + principal + nonce"

# Composition Examples

compositions:
  # Sequential composition: A ▷ B
  sequential:
    operation: "Read ▷ Process ▷ Write"
    input_A:
      scope: "Range"
      order: "Lx"
      visibility: "SI"
      recency: "Fresh(φ)"
      idempotence: "Idem(K)"
      auth: "Auth(π)"
    operation_B:
      requires_order: "SS"
      requires_recency: "Fresh(φ')"
    result:
      # Meet operation: weakest component wins
      scope: "Range"
      order: "Lx"          # Cannot upgrade without new evidence
      visibility: "SI"
      recency: "BS(δ)"     # Degraded if φ expired
      idempotence: "Idem(K)"
      auth: "Auth(π)"
    notes: "Order cannot be upgraded from Lx to SS without serialization point"

  # Parallel composition: A || B → Merge
  parallel:
    operation: "ParallelReads → Merge"
    input_A:
      scope: "Object"
      order: "Causal"
      recency: "BS(δ₁)"
    input_B:
      scope: "Object"
      order: "Lx"
      recency: "BS(δ₂)"
    merge_result:
      scope: "Object"       # meet(Object, Object) = Object
      order: "Causal"       # meet(Causal, Lx) = Causal (weaker)
      recency: "BS(max(δ₁, δ₂))"  # worst-case bound
      merge_semantics: "Last-write-wins or CRDT join"
    notes: "Parallel reads bound by weakest guarantee"

  # Upgrade example: EO ↑ Lx
  upgrade:
    operation: "Eventual → Linearizable via fence"
    input:
      scope: "Object"
      order: "None"
      visibility: "Fractured"
      recency: "EO"
      idempotence: "None"
      auth: "Unauth"
    upgrade_evidence:
      - type: "Lease acquisition"
        effect: "order: None → Lx"
      - type: "Read-index proof"
        effect: "recency: EO → Fresh(φ)"
      - type: "Snapshot token"
        effect: "visibility: Fractured → SI"
    output:
      scope: "Object"
      order: "Lx"
      visibility: "SI"
      recency: "Fresh(φ)"
      idempotence: "None"
      auth: "Unauth"
    cost: "Synchronization with leader; lease acquisition latency"

  # Downgrade example: Fresh(φ) ⤓ BS(δ)
  downgrade:
    operation: "Fresh → Bounded-stale when lease expires"
    input:
      scope: "Range"
      order: "Lx"
      visibility: "SI"
      recency: "Fresh(φ)"
      idempotence: "Idem(K)"
      auth: "Auth(π)"
    trigger: "Lease expiry or evidence validation failure"
    fallback_policy: "Degrade to bounded staleness with explicit label"
    output:
      scope: "Range"
      order: "Lx"
      visibility: "SI"
      recency: "BS(δ)"     # δ = max observed lag
      idempotence: "Idem(K)"
      auth: "Auth(π)"
    user_visible: "Response includes staleness bound header: X-Staleness: 5s"

# Validation Rules
validation:
  rules:
    - "Weakest component governs end-to-end promise"
    - "Strong → weak = weak unless upgrade evidence is provided"
    - "Weak → strong requires new evidence or serialization"
    - "Absence of context capsule implies downgrade"
    - "Every downgrade must be explicit and labeled"

  checklist:
    - "All six components specified?"
    - "Evidence requirements documented for each component?"
    - "Composition operations show meet semantics?"
    - "Upgrades justify new evidence acquisition?"
    - "Downgrades specify trigger and fallback?"
```

### 1.2 Field Descriptions

| Component | Valid Values | Meaning | Evidence Needed |
|-----------|-------------|---------|-----------------|
| **Scope** | Object, Range, Transaction, Global | The domain over which guarantees apply | Range ID, transaction token, global epoch |
| **Order** | None, Causal, Lx (linearizable), SS (strict serializable) | Ordering guarantees across operations | Commit certificates, read-index, serialization points |
| **Visibility** | Fractured, RA (read-atomic), SI (snapshot isolation), SER (serializable) | What subset of state is atomically visible | Snapshot tokens, transaction IDs, isolation proofs |
| **Recency** | EO (eventual only), BS(δ) (bounded staleness), Fresh(φ) (provably fresh) | How recent the observed state is | Closed timestamps, leases, freshness proofs |
| **Idempotence** | None, Idem(K) (with deduplication key) | Whether retries are safe | Request ID, sequence number, dedup window |
| **Auth** | Unauth, Auth(π) (authenticated) | Whether identity is verified | Signatures, tokens, attestations |

### 1.3 Composition Operators

- **meet(A, B)**: Component-wise minimum (weakest wins)
  - `meet(Lx, Causal) = Causal`
  - `meet(Fresh(φ), BS(δ)) = BS(δ)`
  - `meet(Range, Object) = Object`

- **A ▷ B (Sequential)**: `result = meet(A, B)` unless upgrade evidence inserted

- **A || B → Merge (Parallel)**: `result = meet(A, B)` plus merge semantics

- **↑ Upgrade**: Introduce new evidence to strengthen component(s)
  - Must document evidence type, cost, and scope

- **⤓ Downgrade**: Explicit weakening with labeled fallback
  - Must document trigger condition and user visibility

### 1.4 Best Practices

1. **Always specify all six components** - Even if "None" or "Unauth"
2. **Document evidence lifecycle** - Scope, lifetime, binding, revocation
3. **Make downgrades explicit** - Never silently accept weaker guarantees
4. **Show upgrade costs** - Synchronization, latency, coordination budget
5. **Validate composition paths** - Trace end-to-end using meet semantics

---

## 2. Mode Matrix Generator

### 2.1 YAML Input Format

```yaml
# Mode Matrix for a System Component
# Defines contracts under different operational conditions

service_name: "DistributedKV"
component: "ReplicaReadPath"

modes:
  floor:
    description: "Minimum viable correctness - never lie, may be partial"
    preserved_invariants:
      - "Monotonicity: never serve older committed data as newer"
      - "Authenticity: only serve data from authorized writers"
    evidence_requirements:
      - type: "Commit certificate"
        must_verify: true
        on_failure: "reject read"
      - type: "Range ownership proof"
        must_verify: true
        on_failure: "proxy to leaseholder"
    allowed_operations:
      - operation: "Read"
        guarantee_vector:
          scope: "Object"
          order: "Causal"
          visibility: "Fractured"
          recency: "EO"
          idempotence: "None"
          auth: "Auth(π)"
        restrictions: "May return stale; may return unavailable"
    user_visible_contract: "Reads may be stale or unavailable, but never incorrect"
    entry_trigger: "Any evidence validation failure"
    exit_trigger: "Evidence re-established and verified"

  target:
    description: "Normal operation with primary guarantees"
    preserved_invariants:
      - "Monotonicity"
      - "Authenticity"
      - "Freshness: serve data within staleness bound δ"
      - "Read-atomic visibility"
    evidence_requirements:
      - type: "Closed timestamp φ"
        lifetime: "9s heartbeat interval"
        must_verify: true
        on_failure: "degrade to floor"
      - type: "Lease epoch E"
        lifetime: "Until lease expiry"
        must_verify: true
        on_failure: "degrade to degraded mode"
    allowed_operations:
      - operation: "Read"
        guarantee_vector:
          scope: "Range"
          order: "Lx"
          visibility: "SI"
          recency: "Fresh(φ)"
          idempotence: "Idem(K)"
          auth: "Auth(π)"
        restrictions: "None"
    user_visible_contract: "Reads are provably fresh within 9s bound"
    entry_trigger: "Evidence channel healthy; φ and E validated"
    exit_trigger: "Evidence expiry or validation failure"

  degraded:
    description: "Reduced guarantees with explicit labels"
    preserved_invariants:
      - "Monotonicity"
      - "Authenticity"
      - "Bounded staleness: δ = 30s"
    evidence_requirements:
      - type: "Last known φ timestamp"
        must_verify: false
        use_as: "staleness bound calculation"
      - type: "Commit certificate"
        must_verify: true
        on_failure: "degrade to floor"
    allowed_operations:
      - operation: "Read"
        guarantee_vector:
          scope: "Range"
          order: "Lx"
          visibility: "SI"
          recency: "BS(30s)"
          idempotence: "Idem(K)"
          auth: "Auth(π)"
        restrictions: "Response includes staleness label"
    user_visible_contract: "Reads may be stale up to 30s; staleness disclosed in header"
    response_modifications:
      headers:
        - "X-Staleness-Bound: 30s"
        - "X-Mode: degraded"
    entry_trigger: "Evidence φ expired but within configured grace period"
    exit_trigger: "Evidence renewed or grace period exceeded"

  recovery:
    description: "Restricted actions until proofs re-established"
    preserved_invariants:
      - "Monotonicity"
      - "Authenticity"
    evidence_requirements:
      - type: "Recovery checkpoint"
        must_verify: true
        on_failure: "remain in recovery"
    allowed_operations:
      - operation: "Read"
        guarantee_vector:
          scope: "Object"
          order: "Causal"
          visibility: "Fractured"
          recency: "EO"
          idempotence: "None"
          auth: "Auth(π)"
        restrictions: "Read-only; no writes; proxy to leader for strong reads"
    disallowed_operations:
      - "Write"
      - "Strong consistency read"
    user_visible_contract: "Read-only mode; rebuilding evidence; ETA provided"
    entry_trigger: "Evidence completely lost (e.g., after network partition heal)"
    exit_trigger: "Evidence re-proven via leader sync and checkpoint validation"
    recovery_steps:
      - "Sync with current leader"
      - "Validate applied index matches leader"
      - "Re-acquire closed timestamp stream"
      - "Verify lease epoch"
      - "Transition to degraded or target based on evidence health"

# Cross-service compatibility
compatibility:
  rules:
    - "Upstream Target cannot override downstream Degraded"
    - "Final promise = meet(upstream_mode, downstream_mode)"
    - "Missing capsule fields trigger downgrade"
  examples:
    - scenario: "Upstream in Target, downstream in Degraded"
      result: "End-to-end promise uses Degraded guarantees"
      reason: "Downstream mode governs final contract"
```

### 2.2 Python Generator Script

```python
#!/usr/bin/env python3
"""
Mode Matrix Generator
Converts YAML mode specifications to formatted Markdown tables
"""

import yaml
import sys
from typing import Dict, Any, List

def format_vector(vec: Dict[str, str]) -> str:
    """Format a guarantee vector for display"""
    return f"⟨{vec['scope']}, {vec['order']}, {vec['visibility']}, {vec['recency']}, {vec['idempotence']}, {vec['auth']}⟩"

def generate_mode_table(data: Dict[str, Any]) -> str:
    """Generate a comprehensive mode matrix table"""

    service = data['service_name']
    component = data['component']
    modes = data['modes']

    md = f"# Mode Matrix: {service} - {component}\n\n"

    # Summary table
    md += "## Mode Summary\n\n"
    md += "| Mode | Preserved Invariants | Primary Evidence | User Contract |\n"
    md += "|------|---------------------|------------------|---------------|\n"

    for mode_name, mode in modes.items():
        invariants = ", ".join(inv.split(":")[0] for inv in mode['preserved_invariants'])
        evidence = mode['evidence_requirements'][0]['type'] if mode['evidence_requirements'] else "None"
        contract = mode['user_visible_contract']
        md += f"| **{mode_name.title()}** | {invariants} | {evidence} | {contract} |\n"

    md += "\n"

    # Detailed mode specifications
    for mode_name, mode in modes.items():
        md += f"## {mode_name.title()} Mode\n\n"
        md += f"**Description:** {mode['description']}\n\n"

        # Preserved invariants
        md += "### Preserved Invariants\n\n"
        for inv in mode['preserved_invariants']:
            md += f"- {inv}\n"
        md += "\n"

        # Evidence requirements
        md += "### Evidence Requirements\n\n"
        md += "| Type | Must Verify | On Failure | Lifetime |\n"
        md += "|------|-------------|------------|----------|\n"
        for ev in mode['evidence_requirements']:
            lifetime = ev.get('lifetime', 'N/A')
            md += f"| {ev['type']} | {ev['must_verify']} | {ev.get('on_failure', 'N/A')} | {lifetime} |\n"
        md += "\n"

        # Allowed operations
        md += "### Allowed Operations\n\n"
        for op in mode['allowed_operations']:
            md += f"**{op['operation']}**\n\n"
            md += f"- Guarantee Vector: {format_vector(op['guarantee_vector'])}\n"
            if 'restrictions' in op:
                md += f"- Restrictions: {op['restrictions']}\n"
        md += "\n"

        # Disallowed operations (if present)
        if 'disallowed_operations' in mode:
            md += "### Disallowed Operations\n\n"
            for op in mode['disallowed_operations']:
                md += f"- {op}\n"
            md += "\n"

        # Mode transitions
        md += "### Mode Transitions\n\n"
        md += f"**Entry Trigger:** {mode['entry_trigger']}\n\n"
        md += f"**Exit Trigger:** {mode['exit_trigger']}\n\n"

        # Response modifications (if present)
        if 'response_modifications' in mode:
            md += "### Response Modifications\n\n"
            if 'headers' in mode['response_modifications']:
                md += "**Additional Headers:**\n\n"
                for header in mode['response_modifications']['headers']:
                    md += f"- `{header}`\n"
                md += "\n"

        # Recovery steps (if present)
        if 'recovery_steps' in mode:
            md += "### Recovery Steps\n\n"
            for i, step in enumerate(mode['recovery_steps'], 1):
                md += f"{i}. {step}\n"
            md += "\n"

        md += "---\n\n"

    # Compatibility rules
    if 'compatibility' in data:
        md += "## Cross-Service Compatibility\n\n"
        md += "### Rules\n\n"
        for rule in data['compatibility']['rules']:
            md += f"- {rule}\n"
        md += "\n"

        if 'examples' in data['compatibility']:
            md += "### Examples\n\n"
            for ex in data['compatibility']['examples']:
                md += f"**Scenario:** {ex['scenario']}\n\n"
                md += f"- **Result:** {ex['result']}\n"
                md += f"- **Reason:** {ex['reason']}\n\n"

    return md

def main():
    if len(sys.argv) != 2:
        print("Usage: python mode_matrix_generator.py <input.yaml>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        data = yaml.safe_load(f)

    markdown = generate_mode_table(data)
    print(markdown)

if __name__ == '__main__':
    main()
```

### 2.3 Example Usage

```bash
# Create a mode specification YAML file
cat > replica_modes.yaml << EOF
service_name: "DistributedKV"
component: "ReplicaReadPath"
modes:
  # ... (paste YAML from 2.1)
EOF

# Generate markdown table
python mode_matrix_generator.py replica_modes.yaml > replica_modes.md
```

### 2.4 Validation Checklist

- [ ] All four modes defined (Floor, Target, Degraded, Recovery)?
- [ ] Each mode specifies preserved invariants from catalog?
- [ ] Evidence requirements include type, verification rules, and failure handling?
- [ ] Guarantee vectors specified for all allowed operations?
- [ ] Entry and exit triggers are evidence-based (not just time-based)?
- [ ] User-visible contract clearly stated for each mode?
- [ ] Cross-service compatibility rules documented?

---

## 3. Evidence Card Template

### 3.1 Template Structure

```yaml
# Evidence Card Template
# Documents a specific evidence type with full lifecycle

evidence_id: "closed_timestamp_phi"
evidence_name: "Closed Timestamp (φ)"
category: "Recency"          # {Order, Recency, Inclusion, Identity}

# Core Definition
definition:
  what: "A timestamp φ that certifies all transactions with commit timestamp ≤ φ have been applied to this replica"
  why: "Allows followers to serve fresh reads without coordinating with the leader"
  invariant_protected: "Freshness - never represent data as fresher than it is"

# Lifecycle States
lifecycle:
  states:
    generated:
      actor: "Leaseholder"
      trigger: "Periodic heartbeat (every 3s)"
      process: "Determine minimum in-flight transaction timestamp; broadcast φ = min(in_flight) - ε"
      cost: "O(1) computation + broadcast to all replicas"

    validated:
      actor: "Follower replica"
      trigger: "Receipt of φ message"
      process: "Verify φ message signature; check φ > last_φ (monotonicity); check sender has valid lease"
      cost: "Signature verification + monotonicity check"
      failure_mode: "Reject φ; use last valid φ or degrade"

    active:
      actor: "Follower replica"
      trigger: "Validation successful"
      process: "Mark φ as active; use for read queries with timestamp ≤ φ"
      constraints: "Must have φ ≤ current_time and φ > last_applied"

    expiring:
      actor: "Follower replica"
      trigger: "φ age > threshold (e.g., 9s) but < grace period (e.g., 30s)"
      process: "Continue serving with staleness label; attempt to obtain fresh φ"
      user_impact: "Responses include X-Staleness header"

    expired:
      actor: "Follower replica"
      trigger: "φ age > grace period (30s) or lease epoch changed"
      process: "Cannot use φ for Fresh(φ) guarantees; degrade to floor or recovery"
      user_impact: "Reads fail or downgrade to eventual consistency"

    renewed:
      actor: "Leaseholder → Follower"
      trigger: "New φ message received and validated"
      process: "Replace old φ with new φ; transition from expiring → active"

    revoked:
      actor: "System (implicit)"
      trigger: "Leadership change; lease expiry; split-brain detection"
      process: "Immediately invalidate all φ from old epoch"
      safety: "Must not serve reads with φ from revoked epoch"

# Evidence Properties
properties:
  scope:
    type: "Range"
    granularity: "Per-range, per-epoch"
    boundaries: "Does not cross range boundaries or lease epochs"

  lifetime:
    generation_interval: "3s"
    typical_validity: "3-9s (until next heartbeat batch)"
    max_staleness_bound: "30s (grace period)"
    expiry_rule: "Age-based + epoch-based"

  binding:
    bound_to:
      - "Range ID"
      - "Lease epoch E"
      - "Timestamp φ value"
    verification: "Signed by leaseholder; signature includes range + epoch"

  transitivity:
    is_transitive: false
    reason: "φ is specific to one replica's applied state; cannot be forwarded to other ranges"
    cross_boundary: "Must re-prove freshness at range boundaries"

  revocation:
    explicit: false
    implicit_triggers:
      - "Lease epoch change"
      - "Range split/merge"
      - "Leaseholder failure"
    detection: "Follower detects via lease epoch mismatch or heartbeat timeout"
    response: "Immediate transition to expired state; degrade guarantees"

# Cost Analysis
cost:
  generation:
    computation: "O(1) - track minimum in-flight timestamp"
    communication: "Broadcast to N replicas every 3s"
    coordination: "None - unilateral decision by leaseholder"

  verification:
    computation: "O(1) - signature check + monotonicity check"
    communication: "None - passive receipt"
    coordination: "None"

  storage:
    per_replica: "One φ value + signature (~64 bytes)"
    retention: "Only most recent φ"

  amortization:
    strategy: "Single φ broadcast serves unlimited reads for 3-9s window"
    efficiency: "High - O(1) generation cost amortized over O(N) reads"

# Usage Examples
usage:
  follower_reads:
    scenario: "Client requests read from follower with freshness guarantee"
    precondition: "Follower has active φ; read timestamp ≤ φ"
    process: |
      1. Receive read request with desired timestamp ts
      2. Check: ts ≤ φ_active
      3. If yes: serve read with Fresh(φ) guarantee
      4. If no: wait for φ ≥ ts, proxy to leader, or return error
    guarantee_vector: "⟨Range, Lx, SI, Fresh(φ), Idem(K), Auth(π)⟩"

  cross_range_read:
    scenario: "Transaction reads from multiple ranges"
    precondition: "Each range must have φ_i ≥ transaction timestamp"
    process: |
      1. Determine transaction timestamp ts
      2. For each range i: obtain φ_i ≥ ts
      3. If all φ_i available: serve read with Fresh(φ)
      4. If any φ_i unavailable: coordinate with leaders or degrade
    guarantee_vector: "⟨Transaction, SS, SER, Fresh(φ), Idem(K), Auth(π)⟩"
    composition: "meet(φ_1, φ_2, ..., φ_n) = all must be valid"

# Failure Modes and Degradation
failures:
  stale_phi:
    symptom: "φ older than staleness bound δ"
    detection: "current_time - φ_timestamp > δ"
    response: "Transition to expiring or expired; degrade to BS(δ) or EO"
    user_impact: "Explicit staleness label or reduced availability"

  missing_phi:
    symptom: "No φ received for extended period"
    detection: "Heartbeat timeout"
    response: "Transition to expired; degrade to floor or recovery mode"
    user_impact: "Reads unavailable or eventual consistency only"

  wrong_epoch:
    symptom: "φ signed with old lease epoch"
    detection: "Epoch mismatch in signature verification"
    response: "Reject φ; treat as missing; await φ from new leaseholder"
    user_impact: "Temporary unavailability during leadership transition"

  byzantine_phi:
    symptom: "φ violates monotonicity or consistency"
    detection: "φ_new < φ_old or φ > current_time + clock_skew_bound"
    response: "Reject φ; alert; potentially blacklist sender"
    user_impact: "Maintain safety; degrade availability"

# Integration Points
integration:
  required_mechanisms:
    - "Lease protocol (provides epoch E)"
    - "Raft log application (determines applied state)"
    - "Heartbeat subsystem (carries φ messages)"

  provides_to:
    - "Read path (enables follower reads)"
    - "Transaction coordinator (enables non-blocking reads)"
    - "Staleness monitoring (observability)"

  context_capsule_fields:
    invariant: "Freshness"
    evidence: "φ value + signature"
    boundary: "range_id + epoch_E"
    mode: "Target | Degraded | Expired"
    fallback: "BS(δ) or proxy to leader"

# Validation Checklist
validation:
  - "φ generation is monotonic?"
  - "φ ≤ current_time (respecting clock skew)?"
  - "φ signature valid for current epoch?"
  - "φ received within heartbeat timeout?"
  - "Follower applied index supports reads at φ?"
  - "Downgrade path defined for expiry?"
  - "Revocation on epoch change enforced?"

# Related Evidence Types
related:
  complements:
    - evidence: "Lease epoch E"
      relationship: "φ is only valid within lease epoch E"
    - evidence: "Read-index receipt"
      relationship: "Alternative freshness proof via leader coordination"

  alternatives:
    - evidence: "Synchronous read from leader"
      tradeoff: "Lower latency (φ) vs stronger guarantee (leader read)"
    - evidence: "Bounded staleness bound δ"
      tradeoff: "Provable freshness (φ) vs best-effort bound (δ)"

# Human Mental Model
human:
  see:
    - "Closed timestamp age metric"
    - "Follower read success rate"
    - "Staleness label frequency"
  think:
    - "Is φ channel healthy?"
    - "Are followers receiving timely φ updates?"
    - "What is acceptable staleness bound for this workload?"
  do:
    - "Monitor φ age across replicas"
    - "Alert if φ age exceeds threshold"
    - "Adjust staleness policy based on SLO"
    - "Investigate if φ propagation fails"
```

### 3.2 Blank Template (Fill-in)

```yaml
evidence_id: "__________"
evidence_name: "__________"
category: "__________"    # {Order, Recency, Inclusion, Identity}

definition:
  what: "__________"
  why: "__________"
  invariant_protected: "__________"

lifecycle:
  states:
    generated:
      actor: "__________"
      trigger: "__________"
      process: "__________"
      cost: "__________"
    validated:
      actor: "__________"
      trigger: "__________"
      process: "__________"
      cost: "__________"
      failure_mode: "__________"
    active:
      actor: "__________"
      trigger: "__________"
      process: "__________"
      constraints: "__________"
    expiring:
      actor: "__________"
      trigger: "__________"
      process: "__________"
      user_impact: "__________"
    expired:
      actor: "__________"
      trigger: "__________"
      process: "__________"
      user_impact: "__________"
    renewed:
      actor: "__________"
      trigger: "__________"
      process: "__________"
    revoked:
      actor: "__________"
      trigger: "__________"
      process: "__________"
      safety: "__________"

properties:
  scope:
    type: "__________"
    granularity: "__________"
    boundaries: "__________"
  lifetime:
    generation_interval: "__________"
    typical_validity: "__________"
    max_staleness_bound: "__________"
    expiry_rule: "__________"
  binding:
    bound_to: []
    verification: "__________"
  transitivity:
    is_transitive: false
    reason: "__________"
    cross_boundary: "__________"
  revocation:
    explicit: false
    implicit_triggers: []
    detection: "__________"
    response: "__________"

cost:
  generation:
    computation: "__________"
    communication: "__________"
    coordination: "__________"
  verification:
    computation: "__________"
    communication: "__________"
    coordination: "__________"
  storage:
    per_replica: "__________"
    retention: "__________"
  amortization:
    strategy: "__________"
    efficiency: "__________"

usage:
  primary_scenario:
    scenario: "__________"
    precondition: "__________"
    process: "__________"
    guarantee_vector: "__________"

failures:
  primary_failure:
    symptom: "__________"
    detection: "__________"
    response: "__________"
    user_impact: "__________"

integration:
  required_mechanisms: []
  provides_to: []
  context_capsule_fields:
    invariant: "__________"
    evidence: "__________"
    boundary: "__________"
    mode: "__________"
    fallback: "__________"

validation: []

related:
  complements: []
  alternatives: []
```

### 3.3 Validation Checklist

- [ ] All lifecycle states documented (Generated → Validated → Active → Expiring → Expired → Renewed/Revoked)?
- [ ] Properties include scope, lifetime, binding, transitivity, and revocation?
- [ ] Cost analysis covers generation, verification, storage, and amortization?
- [ ] At least one usage example with guarantee vector?
- [ ] Failure modes specify symptom, detection, response, and user impact?
- [ ] Integration points identify required mechanisms and context capsule fields?
- [ ] Related evidence types documented (complements and alternatives)?

---

## 4. Context Capsule Schema

### 4.1 JSON Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://distributedbook.org/schemas/context-capsule.json",
  "title": "Context Capsule",
  "description": "A vehicle carrying guarantees and evidence across system boundaries",
  "type": "object",

  "required": ["invariant", "evidence", "boundary", "mode", "fallback"],

  "properties": {
    "invariant": {
      "description": "Which property is being preserved (from invariant catalog)",
      "type": "string",
      "enum": [
        "Conservation",
        "Uniqueness",
        "Authenticity",
        "Integrity",
        "Order",
        "Exclusivity",
        "Monotonicity",
        "Freshness",
        "Visibility",
        "Convergence",
        "Idempotence",
        "BoundedStaleness",
        "Availability"
      ]
    },

    "evidence": {
      "description": "Proof(s) validating the invariant (typed, scoped)",
      "type": "object",
      "required": ["type", "value", "scope", "lifetime"],
      "properties": {
        "type": {
          "type": "string",
          "enum": [
            "CommitCertificate",
            "LeasEpoch",
            "ClosedTimestamp",
            "ReadIndex",
            "MerkleProof",
            "VerkleProof",
            "Signature",
            "TEEAttestation",
            "ConsistencyProof"
          ]
        },
        "value": {
          "description": "The actual proof data (hex, base64, or structured)",
          "oneOf": [
            {"type": "string"},
            {"type": "object"}
          ]
        },
        "scope": {
          "description": "What domain this evidence covers",
          "type": "object",
          "required": ["type"],
          "properties": {
            "type": {
              "type": "string",
              "enum": ["Object", "Range", "Transaction", "Global"]
            },
            "identifier": {
              "type": "string",
              "description": "Specific scope ID (range ID, txn ID, etc.)"
            }
          }
        },
        "lifetime": {
          "description": "When this evidence expires or must be renewed",
          "type": "object",
          "required": ["expiry_type"],
          "properties": {
            "expiry_type": {
              "type": "string",
              "enum": ["age_based", "epoch_based", "event_based", "permanent"]
            },
            "expiry_value": {
              "description": "Timestamp, epoch number, or event condition",
              "oneOf": [
                {"type": "string", "format": "date-time"},
                {"type": "integer"},
                {"type": "string"}
              ]
            },
            "renewable": {
              "type": "boolean",
              "description": "Can this evidence be renewed?"
            }
          }
        },
        "binding": {
          "description": "Who/what this evidence is valid for",
          "type": "object",
          "properties": {
            "principal": {
              "type": "string",
              "description": "User, service, or tenant ID"
            },
            "session": {
              "type": "string",
              "description": "Session or request ID"
            },
            "nonce": {
              "type": "string",
              "description": "Single-use token to prevent replay"
            }
          }
        },
        "transitive": {
          "type": "boolean",
          "description": "Can downstream services rely on this evidence?"
        }
      }
    },

    "boundary": {
      "description": "Valid scope/domain and epoch",
      "type": "object",
      "required": ["type", "identifier"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["Service", "Shard", "Range", "Region", "Organization"]
        },
        "identifier": {
          "type": "string",
          "description": "Specific boundary identifier"
        },
        "epoch": {
          "type": "integer",
          "description": "Current epoch number for this boundary"
        }
      }
    },

    "mode": {
      "description": "Current operational mode",
      "type": "string",
      "enum": ["Floor", "Target", "Degraded", "Recovery"]
    },

    "fallback": {
      "description": "Authorized downgrade if verification fails",
      "type": "object",
      "required": ["degraded_mode", "degraded_guarantee"],
      "properties": {
        "degraded_mode": {
          "type": "string",
          "enum": ["Floor", "Degraded", "Recovery", "Reject"]
        },
        "degraded_guarantee": {
          "description": "The weaker guarantee vector to use",
          "type": "object",
          "properties": {
            "scope": {"type": "string"},
            "order": {"type": "string"},
            "visibility": {"type": "string"},
            "recency": {"type": "string"},
            "idempotence": {"type": "string"},
            "auth": {"type": "string"}
          }
        },
        "user_notification": {
          "type": "string",
          "description": "How to inform the user (header, status code, etc.)"
        }
      }
    },

    "scope": {
      "description": "Optional: Explicit guarantee scope",
      "type": "string",
      "enum": ["Object", "Range", "Transaction", "Global"]
    },

    "order": {
      "description": "Optional: Desired order class",
      "type": "string",
      "enum": ["None", "Causal", "Lx", "SS"]
    },

    "recency": {
      "description": "Optional: Desired recency contract",
      "type": "string",
      "pattern": "^(EO|BS\\([0-9]+[smh]\\)|Fresh\\([^)]+\\))$"
    },

    "identity": {
      "description": "Optional: Caller/tenant binding and nonce",
      "type": "object",
      "properties": {
        "caller": {"type": "string"},
        "tenant": {"type": "string"},
        "nonce": {"type": "string"}
      }
    },

    "trace": {
      "description": "Optional: Causality token/session context",
      "type": "object",
      "properties": {
        "trace_id": {"type": "string"},
        "span_id": {"type": "string"},
        "causality_token": {"type": "string"}
      }
    },

    "obligations": {
      "description": "Optional: What the receiver must check/return",
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "action"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["VerifyEvidence", "RenewEvidence", "PropagateEvidence", "RecordMetric"]
          },
          "action": {
            "type": "string",
            "description": "Specific action required"
          },
          "on_failure": {
            "type": "string",
            "description": "What to do if obligation cannot be met"
          }
        }
      }
    }
  }
}
```

### 4.2 Example Capsules

#### Example 1: Follower Read with Fresh Guarantee

```json
{
  "invariant": "Freshness",
  "evidence": {
    "type": "ClosedTimestamp",
    "value": "2025-10-01T12:34:56.789Z",
    "scope": {
      "type": "Range",
      "identifier": "range_123"
    },
    "lifetime": {
      "expiry_type": "age_based",
      "expiry_value": "2025-10-01T12:35:05.789Z",
      "renewable": true
    },
    "binding": {
      "principal": "tenant_A",
      "session": "sess_xyz"
    },
    "transitive": false
  },
  "boundary": {
    "type": "Range",
    "identifier": "range_123",
    "epoch": 42
  },
  "mode": "Target",
  "fallback": {
    "degraded_mode": "Degraded",
    "degraded_guarantee": {
      "scope": "Range",
      "order": "Lx",
      "visibility": "SI",
      "recency": "BS(30s)",
      "idempotence": "Idem(K)",
      "auth": "Auth(π)"
    },
    "user_notification": "X-Staleness-Bound: 30s"
  },
  "scope": "Range",
  "order": "Lx",
  "recency": "Fresh(φ)",
  "identity": {
    "caller": "service_B",
    "tenant": "tenant_A",
    "nonce": "nonce_12345"
  },
  "trace": {
    "trace_id": "trace_abc",
    "span_id": "span_def"
  },
  "obligations": [
    {
      "type": "VerifyEvidence",
      "action": "Check closed timestamp signature and monotonicity",
      "on_failure": "Degrade to fallback guarantee"
    }
  ]
}
```

#### Example 2: Cross-Range Transaction

```json
{
  "invariant": "Visibility",
  "evidence": {
    "type": "CommitCertificate",
    "value": {
      "transaction_id": "txn_789",
      "commit_timestamp": "2025-10-01T12:35:00.000Z",
      "participants": ["range_123", "range_456"],
      "quorum_signatures": ["sig1", "sig2", "sig3"]
    },
    "scope": {
      "type": "Transaction",
      "identifier": "txn_789"
    },
    "lifetime": {
      "expiry_type": "permanent",
      "renewable": false
    },
    "transitive": true
  },
  "boundary": {
    "type": "Service",
    "identifier": "distributed_kv",
    "epoch": 100
  },
  "mode": "Target",
  "fallback": {
    "degraded_mode": "Reject",
    "degraded_guarantee": null,
    "user_notification": "Transaction cannot proceed without commit evidence"
  },
  "scope": "Transaction",
  "order": "SS",
  "recency": "Fresh(φ)",
  "visibility": "SER"
}
```

#### Example 3: Degraded Mode Capsule

```json
{
  "invariant": "BoundedStaleness",
  "evidence": {
    "type": "ClosedTimestamp",
    "value": "2025-10-01T12:34:30.000Z",
    "scope": {
      "type": "Range",
      "identifier": "range_123"
    },
    "lifetime": {
      "expiry_type": "age_based",
      "expiry_value": "2025-10-01T12:34:39.000Z",
      "renewable": false
    },
    "transitive": false
  },
  "boundary": {
    "type": "Range",
    "identifier": "range_123",
    "epoch": 42
  },
  "mode": "Degraded",
  "fallback": {
    "degraded_mode": "Floor",
    "degraded_guarantee": {
      "scope": "Object",
      "order": "Causal",
      "visibility": "Fractured",
      "recency": "EO",
      "idempotence": "None",
      "auth": "Auth(π)"
    },
    "user_notification": "X-Mode: floor; eventual consistency only"
  },
  "scope": "Range",
  "order": "Lx",
  "recency": "BS(30s)"
}
```

### 4.3 Capsule Operations

#### restrict() - Narrow scope at boundary

```python
def restrict(capsule, new_scope):
    """
    Narrow the capsule scope to maintain safety at a boundary.
    Can only restrict to equal or narrower scope.
    """
    scope_hierarchy = ["Object", "Range", "Transaction", "Global"]
    current_idx = scope_hierarchy.index(capsule["scope"])
    new_idx = scope_hierarchy.index(new_scope)

    if new_idx > current_idx:
        raise ValueError("Cannot restrict to broader scope without upgrade")

    restricted = capsule.copy()
    restricted["scope"] = new_scope
    restricted["boundary"]["identifier"] = f"{new_scope}_specific_id"

    # Re-verify evidence is still valid for narrower scope
    if not verify_evidence(restricted):
        restricted["mode"] = restricted["fallback"]["degraded_mode"]

    return restricted
```

#### extend() - Widen scope after upgrade

```python
def extend(capsule, new_scope, upgrade_evidence):
    """
    Widen capsule scope only after acquiring upgrade evidence.
    """
    scope_hierarchy = ["Object", "Range", "Transaction", "Global"]
    current_idx = scope_hierarchy.index(capsule["scope"])
    new_idx = scope_hierarchy.index(new_scope)

    if new_idx <= current_idx:
        raise ValueError("Use restrict() to narrow scope")

    # Verify upgrade evidence is sufficient
    if not verify_upgrade_evidence(upgrade_evidence, new_scope):
        raise ValueError("Insufficient evidence for scope extension")

    extended = capsule.copy()
    extended["scope"] = new_scope
    extended["evidence"] = upgrade_evidence
    extended["boundary"]["identifier"] = f"{new_scope}_id"

    return extended
```

#### rebind() - Bind to new identity/epoch/domain

```python
def rebind(capsule, new_identity, new_epoch):
    """
    Re-bind capsule to a new identity/epoch/domain.
    Must re-verify evidence for new binding.
    """
    rebound = capsule.copy()
    rebound["identity"] = new_identity
    rebound["boundary"]["epoch"] = new_epoch
    rebound["evidence"]["binding"] = {
        "principal": new_identity["caller"],
        "session": new_identity.get("session"),
        "nonce": generate_nonce()
    }

    # Re-verify evidence under new binding
    if not verify_evidence(rebound):
        rebound["mode"] = rebound["fallback"]["degraded_mode"]

    return rebound
```

#### renew() - Refresh expiring evidence

```python
def renew(capsule, new_evidence):
    """
    Refresh expiring evidence to maintain current mode.
    """
    if capsule["evidence"]["lifetime"]["renewable"] == False:
        raise ValueError("Evidence is not renewable")

    renewed = capsule.copy()
    renewed["evidence"] = new_evidence

    # Verify new evidence is compatible
    if new_evidence["type"] != capsule["evidence"]["type"]:
        raise ValueError("Cannot renew with different evidence type")

    if verify_evidence(renewed):
        renewed["mode"] = "Target"  # Restore to target if successful

    return renewed
```

#### degrade() - Apply fallback policy

```python
def degrade(capsule, reason):
    """
    Explicitly degrade capsule with labeled fallback policy.
    """
    degraded = capsule.copy()
    degraded["mode"] = degraded["fallback"]["degraded_mode"]

    if degraded["fallback"]["degraded_guarantee"]:
        for key, value in degraded["fallback"]["degraded_guarantee"].items():
            degraded[key] = value

    # Add user-visible notification
    degraded["degradation_reason"] = reason
    degraded["degradation_timestamp"] = datetime.utcnow().isoformat()

    # Record obligation to notify user
    if "obligations" not in degraded:
        degraded["obligations"] = []
    degraded["obligations"].append({
        "type": "RecordMetric",
        "action": f"Increment degradation counter: {reason}",
        "on_failure": "Log error"
    })

    return degraded
```

### 4.4 Composition Rules

1. **Sequential composition (A ▷ B)**
   - `capsule_B.evidence` must include or supersede `capsule_A.evidence`
   - If not, insert upgrade step or downgrade `capsule_B`
   - Result: `meet(capsule_A, capsule_B)`

2. **Parallel composition (A || B → Merge)**
   - Merge capsules: `capsule_merge.evidence = combine(A.evidence, B.evidence)`
   - Guarantees: component-wise meet
   - Mode: `meet(A.mode, B.mode)` (degraded if either is degraded)

3. **Boundary crossing**
   - Receiver must verify all evidence fields
   - On verification failure: apply `fallback` policy
   - Non-transitive evidence must be replaced or re-verified

### 4.5 Validation Checklist

- [ ] All five required fields present (invariant, evidence, boundary, mode, fallback)?
- [ ] Evidence includes type, value, scope, lifetime?
- [ ] Boundary specifies type, identifier, and epoch?
- [ ] Fallback policy defines degraded mode and guarantee?
- [ ] Optional fields used appropriately for composition?
- [ ] Obligations specify verification requirements?
- [ ] Evidence binding matches identity fields?
- [ ] Transitivity correctly marked for cross-boundary usage?

---

## 5. Sacred Diagram ASCII Templates

### 5.1 The Five Canonical Diagrams

#### Diagram 1: The Invariant Guardian

**Purpose:** Show how mechanisms protect invariants from threats by generating evidence.

**Template:**

```
┌─────────────────────────────────────────────────────────┐
│           THE INVARIANT GUARDIAN PATTERN                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│    [THREAT] ⚡                                           │
│       │                                                  │
│       │ attempts to violate                             │
│       ↓                                                  │
│   ╔═══════════════╗                                     │
│   ║  INVARIANT    ║  ← protected by                     │
│   ║  {name}       ║                                     │
│   ╚═══════════════╝                                     │
│       ↑       ↑                                          │
│       │       │                                          │
│       │       └─────── [MECHANISM] 🛡️                   │
│       │                    │                             │
│       │                    │ generates                   │
│       │                    ↓                             │
│       └────────────── 📜 [EVIDENCE]                     │
│                            │                             │
│                            │ scope: {scope}              │
│                            │ lifetime: {lifetime}        │
│                            └ binding: {binding}          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Example (Filled):**

```
┌─────────────────────────────────────────────────────────┐
│           THE INVARIANT GUARDIAN PATTERN                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│    [Split Brain] ⚡                                      │
│       │                                                  │
│       │ attempts to violate                             │
│       ↓                                                  │
│   ╔═══════════════╗                                     │
│   ║  INVARIANT    ║  ← protected by                     │
│   ║  Uniqueness   ║                                     │
│   ╚═══════════════╝                                     │
│       ↑       ↑                                          │
│       │       │                                          │
│       │       └─────── [Lease Protocol] 🛡️              │
│       │                    │                             │
│       │                    │ generates                   │
│       │                    ↓                             │
│       └────────────── 📜 [Lease Epoch E]                │
│                            │                             │
│                            │ scope: Range                │
│                            │ lifetime: 9s                │
│                            └ binding: LeaderID+Epoch     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Symbology:**
- ⚡ = Threat (red in color diagrams)
- ╔═══╗ = Invariant (blue, hexagonal conceptually)
- 🛡️ = Mechanism (green, circular conceptually)
- 📜 = Evidence (green, rectangular conceptually)

---

#### Diagram 2: The Evidence Flow

**Purpose:** Show the lifecycle of evidence from generation through expiry.

**Template:**

```
┌────────────────────────────────────────────────────────────────┐
│                  THE EVIDENCE LIFECYCLE                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐             │
│  │ Generate │  →   │ Propagate│  →   │  Verify  │             │
│  │   ($)    │      │    →     │      │    ✓     │             │
│  └──────────┘      └──────────┘      └──────────┘             │
│       ↓                                    ↓                    │
│  [Actor: {who}]                       [Actor: {who}]           │
│  Cost: {cost}                         Cost: {cost}             │
│                                            ↓                    │
│                                       ┌──────────┐             │
│                                       │   Use    │             │
│                                       │    !     │             │
│                                       └──────────┘             │
│                                            ↓                    │
│                                       [Enables: {action}]      │
│                                            ↓                    │
│                                       ┌──────────┐             │
│                                       │  Expire  │             │
│                                       │    ⏰    │             │
│                                       └──────────┘             │
│                                            ↓                    │
│                                       [Trigger: {condition}]   │
│                                            ↓                    │
│                        ┌───────────────────┴──────────────┐    │
│                        ↓                                   ↓    │
│                   ┌─────────┐                        ┌────────┐│
│                   │  Renew  │                        │ Revoke ││
│                   │    ♻    │                        │   ✗    ││
│                   └─────────┘                        └────────┘│
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Example (Filled):**

```
┌────────────────────────────────────────────────────────────────┐
│            CLOSED TIMESTAMP EVIDENCE LIFECYCLE                 │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐             │
│  │ Generate │  →   │ Propagate│  →   │  Verify  │             │
│  │   ($)    │      │    →     │      │    ✓     │             │
│  └──────────┘      └──────────┘      └──────────┘             │
│       ↓                                    ↓                    │
│  [Actor: Leaseholder]                 [Actor: Follower]        │
│  Cost: O(1) + broadcast               Cost: Sig verification   │
│                                            ↓                    │
│                                       ┌──────────┐             │
│                                       │   Use    │             │
│                                       │    !     │             │
│                                       └──────────┘             │
│                                            ↓                    │
│                                       [Enables: Fresh reads]   │
│                                            ↓                    │
│                                       ┌──────────┐             │
│                                       │  Expire  │             │
│                                       │    ⏰    │             │
│                                       └──────────┘             │
│                                            ↓                    │
│                                       [Trigger: Age > 9s]      │
│                                            ↓                    │
│                        ┌───────────────────┴──────────────┐    │
│                        ↓                                   ↓    │
│                   ┌─────────┐                        ┌────────┐│
│                   │  Renew  │                        │ Revoke ││
│                   │  (New φ)│                        │ (Epoch ││
│                   │    ♻    │                        │ change)││
│                   └─────────┘                        │   ✗    ││
│                                                      └────────┘│
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Symbology:**
- ($) = Generation cost
- → = Data/evidence flow (solid line)
- ✓ = Verification point
- ! = Active use
- ⏰ = Time-based event
- ♻ = Renewal
- ✗ = Revocation

---

#### Diagram 3: The Composition Ladder

**Purpose:** Visualize guarantee strength and composition using meet semantics.

**Template:**

```
┌────────────────────────────────────────────────────────────┐
│                THE COMPOSITION LADDER                      │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Strong                                                     │
│  ═══════  {System A}                                        │
│     │     G_A = ⟨{scope}, {order}, {visibility},           │
│     │            {recency}, {idem}, {auth}⟩                 │
│     │                                                        │
│     │ ┌─ upgrade via {evidence} ──┐                        │
│     ↓ │                            │                        │
│  ═══════  {Boundary}               │                        │
│     │     Capsule: {present/absent}│                        │
│     │                               │                        │
│     │ meet(G_A, G_B)                │                        │
│     ↓                               ↓                        │
│  ═══════  {System B}          ═══════  {Upgraded System}   │
│     │     G_B = ⟨{weaker}⟩          Strong (if evidence)    │
│     │                                                        │
│     │ ⤓ explicit downgrade                                  │
│     ↓   (missing evidence)                                  │
│  ═══⊗═══  {Degraded}                                        │
│     │     G_degraded = ⟨{degraded}⟩                         │
│     │     Label: {user_visible}                             │
│     ↓                                                        │
│  ═══════  Weak/Floor                                        │
│           G_floor = ⟨{minimal}⟩                             │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

**Example (Filled):**

```
┌────────────────────────────────────────────────────────────┐
│         FOLLOWER READ COMPOSITION LADDER                   │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Strong                                                     │
│  ═══════  Leader Read                                       │
│     │     G = ⟨Range, SS, SER, Fresh(φ), Idem(K), Auth(π)⟩ │
│     │                                                        │
│     │                                                        │
│     ↓                                                        │
│  ═══════  Boundary: Range → Follower                       │
│     │     Capsule: {φ, E} present                           │
│     │                                                        │
│     │ meet(G_leader, G_follower)                            │
│     ↓                                                        │
│  ═══════  Follower Read (with φ)                           │
│     │     G = ⟨Range, Lx, SI, Fresh(φ), Idem(K), Auth(π)⟩  │
│     │         ^                ^                            │
│     │         |                |                            │
│     │       weaker          fresh via φ                     │
│     │                                                        │
│     │ ⤓ explicit downgrade                                  │
│     ↓   (φ expired)                                         │
│  ═══⊗═══  Follower Read (degraded)                         │
│     │     G = ⟨Range, Lx, SI, BS(30s), Idem(K), Auth(π)⟩   │
│     │     Label: X-Staleness-Bound: 30s                     │
│     ↓                                                        │
│  ═══════  Floor (eventual only)                            │
│           G = ⟨Object, Causal, Fractured, EO, None, Auth⟩  │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

**Symbology:**
- ═══════ = Guarantee strength (thick = strong, thin = weak)
- ⊗ = Explicit downgrade point
- ⤓ = Degradation arrow
- meet(A, B) = Component-wise minimum

---

#### Diagram 4: The Mode Compass

**Purpose:** Show mode transitions and their triggers.

**Template:**

```
┌────────────────────────────────────────────────────┐
│                 THE MODE COMPASS                   │
├────────────────────────────────────────────────────┤
│                                                     │
│                    ╔═══════════╗                   │
│                    ║  Target   ║                   │
│                    ║  {desc}   ║                   │
│                    ╚═══════════╝                   │
│                         ↑                           │
│                         │                           │
│           {enter} ──────┤                           │
│                         │                           │
│     ┌───────────────────┼───────────────────┐      │
│     │                   │                   │      │
│     ↓                   ↓                   ↓      │
│ ╔═══════════╗                         ╔═══════════╗│
│ ║ Recovery  ║  ←─── {trigger} ────→  ║ Degraded  ║│
│ ║  {desc}   ║                         ║  {desc}   ║│
│ ╚═══════════╝                         ╚═══════════╝│
│     │                                       │       │
│     │                                       │       │
│     │          ╔═══════════╗                │       │
│     └────────→ ║   Floor   ║ ←──────────────┘       │
│                ║  {desc}   ║                        │
│                ╚═══════════╝                        │
│                                                     │
│  Legend:                                            │
│  ────→  Transition triggered by {evidence}         │
│  {enter} Entry condition                            │
│  {desc}  Preserved invariants                       │
│                                                     │
└────────────────────────────────────────────────────┘
```

**Example (Filled):**

```
┌────────────────────────────────────────────────────┐
│          REPLICA READ PATH MODE COMPASS            │
├────────────────────────────────────────────────────┤
│                                                     │
│                    ╔═══════════╗                   │
│                    ║  Target   ║                   │
│                    ║ Fresh(φ)  ║                   │
│                    ╚═══════════╝                   │
│                         ↑                           │
│                         │                           │
│        φ renewed ───────┤                           │
│                         │                           │
│     ┌───────────────────┼───────────────────┐      │
│     │                   │                   │      │
│     ↓                   ↓                   ↓      │
│ ╔═══════════╗                         ╔═══════════╗│
│ ║ Recovery  ║  ←─ φ age > 30s ────→  ║ Degraded  ║│
│ ║ Rebuild   ║                         ║  BS(30s)  ║│
│ ║ evidence  ║                         ║ + label   ║│
│ ╚═══════════╝                         ╚═══════════╝│
│     │                                       │       │
│     │ φ lost                    φ age > 9s  │       │
│     │                                       │       │
│     │          ╔═══════════╗                │       │
│     └────────→ ║   Floor   ║ ←──────────────┘       │
│  evidence      ║    EO     ║  all evidence          │
│  validation    ║ Monotonic ║  validation            │
│  failed        ╚═══════════╝  failed                │
│                                                     │
│  Preserved invariants:                              │
│  • Floor: Monotonicity, Authenticity                │
│  • Target: + Freshness(φ), Visibility(SI)           │
│  • Degraded: + BoundedStaleness(30s)                │
│  • Recovery: Rebuilding all evidence                │
│                                                     │
└────────────────────────────────────────────────────┘
```

**Symbology:**
- ╔═══╗ = Mode state (hexagonal)
- ────→ = Transition (evidence-triggered)
- ↑↓ = Promotion/demotion

---

#### Diagram 5: Knowledge vs Data Flow

**Purpose:** Distinguish data plane from evidence/control plane.

**Template:**

```
┌────────────────────────────────────────────────────────────┐
│           KNOWLEDGE vs DATA FLOW SEPARATION                │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Client                Service A              Service B    │
│    │                      │                      │         │
│    │ ──── Request ──────→ │                      │         │
│    │      (Data)          │                      │         │
│    │                      │                      │         │
│    │                      ├─ Boundary Check ─┐   │         │
│    │                      │  Verify Capsule  │   │         │
│    │                      │  {invariant}     │   │         │
│    │                      │  {evidence}      │   │         │
│    │                      └──────────────────┘   │         │
│    │                      │                      │         │
│    │                      │ ──── Forward ──────→ │         │
│    │                      │      (Data +         │         │
│    │                      │       Capsule)       │         │
│    │                      │                      │         │
│    │                      │                      ├─ Verify │
│    │                      │                      │  Evidence│
│    │                      │                      │    ✓    │
│    │                      │                      │         │
│    │                      │ ←─── Response ────── │         │
│    │                      │      (Data +         │         │
│    │                      │       Evidence)      │         │
│    │                      │                      │         │
│    │ ←─── Response ────── │                      │         │
│    │      (Data +         │                      │         │
│    │       Guarantee)     │                      │         │
│    │                      │                      │         │
│                                                             │
│  ━━━━━━━━━  Data Plane (high volume)                       │
│  ─ ─ ─ ─   Evidence Plane (checks at boundaries)           │
│  ┌──────┐  Verification Point                              │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

**Example (Filled):**

```
┌────────────────────────────────────────────────────────────┐
│         FOLLOWER READ: DATA + EVIDENCE PLANES              │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Client              Follower              Leaseholder     │
│    │                    │                      │           │
│    │ ──── Read(k) ────→ │                      │           │
│    │      (Data)        │                      │           │
│    │                    │                      │           │
│    │                    ├─ Boundary Check ─┐   │           │
│    │                    │  Have φ for ts?  │   │           │
│    │                    │  φ age < 9s?     │   │           │
│    │                    │  Epoch valid?    │   │           │
│    │                    └──────────────────┘   │           │
│    │                    │                      │           │
│    │                    │  Evidence valid: ✓   │           │
│    │                    │  Serve local read    │           │
│    │                    │                      │           │
│    │ ←─── v, φ ──────── │                      │           │
│    │      (Data +       │                      │           │
│    │       Fresh proof) │                      │           │
│    │                    │                      │           │
│    │                    │                      │           │
│    │ ─ ─ Evidence ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│           │
│    │     Heartbeat      │  ←── φ heartbeat ─── │           │
│    │     (Background)   │      every 3s        │           │
│    │                    │                      │           │
│                                                             │
│  ━━━━━━━━━  Data Plane (read request/response)             │
│  ─ ─ ─ ─   Evidence Plane (φ propagation in background)    │
│  ┌──────┐  Verification Point (check φ validity)           │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

**Symbology:**
- ━━━━ = Data plane (solid line, high volume)
- ─ ─ ─ = Evidence/control plane (dashed, lower volume)
- ┌──┐ = Verification/decision point
- ✓ = Evidence validated

---

### 5.2 Consistent Visual Grammar

#### Colors (for rendered diagrams)
- **Blue**: Invariants (what must be preserved)
- **Green**: Evidence and mechanisms (what protects)
- **Red**: Threats and failures (what violates)
- **Yellow**: Boundaries (where verification happens)
- **Gray**: Normal data flow

#### Shapes
- **Hexagons** (╔═══╗): Invariants and modes
- **Rectangles** (┌───┐): Evidence, processes, systems
- **Circles** (conceptually 🛡️): Mechanisms
- **Double lines** (═══): Strong guarantees
- **Single lines** (───): Weak guarantees

#### Lines
- **Solid** (───): Data flow, strong relationships
- **Dashed** (─ ─): Evidence flow, background processes
- **Wavy** (~~~): Degradation, failure paths
- **Thick** (═══): Strong guarantees
- **Thin** (───): Weak guarantees

#### Symbols
- ⚡ Threat
- 🛡️ Mechanism/Protection
- 📜 Evidence
- ✓ Verification
- ✗ Rejection/Revocation
- ⏰ Time-based event
- ♻ Renewal
- ⊗ Degradation point
- ($) Cost
- ! Active use

### 5.3 Template Usage Guidelines

1. **Choose the right diagram:**
   - Invariant Guardian: Introducing a new protection mechanism
   - Evidence Flow: Explaining evidence lifecycle
   - Composition Ladder: Showing guarantee composition
   - Mode Compass: Describing operational modes
   - Knowledge vs Data: Separating evidence from data plane

2. **Fill in placeholders:**
   - Replace `{name}`, `{desc}`, `{evidence}` with specifics
   - Keep text concise (3-5 words per label)
   - Maintain visual balance

3. **Maintain consistency:**
   - Use same symbols across all diagrams in a chapter
   - Keep colors/shapes aligned with grammar
   - Reference earlier diagrams when patterns recur

4. **Validate clarity:**
   - Can a reader understand the flow in 30 seconds?
   - Are decision points clearly marked?
   - Is the "so what" evident?

---

## 6. Chapter Development Canvas

### 6.1 Full Canvas Template

```markdown
# CHAPTER DEVELOPMENT CANVAS
## Chapter: {Chapter Number and Title}

---

### 1. INVARIANT FOCUS

**Primary Invariant:**
- Name: __________
- From catalog: [ ] Fundamental  [ ] Derived  [ ] Composite
- Definition: __________

**Supporting Invariants:**
1. __________ (reinforces primary via __________)
2. __________ (enables composition with __________)

**Threat Model:**
- Primary threat: __________
- Attack vector: __________
- Consequence if violated: __________

---

### 2. UNCERTAINTY ADDRESSED

**What Cannot Be Known:**
- __________
- Reason: {physics/distribution/asynchrony}

**Cost to Know:**
- Mechanism: __________
- Latency cost: __________
- Coordination cost: __________
- Tradeoff: __________

**Acceptable Doubt:**
- What we can tolerate: __________
- Bounded by: __________
- Degradation semantics: __________

---

### 3. EVIDENCE GENERATED (Calculus)

**Primary Evidence Type(s):**
1. Type: __________
   - Category: [ ] Order  [ ] Recency  [ ] Inclusion  [ ] Identity
   - What it certifies: __________

**Evidence Properties:**

| Property | Value |
|----------|-------|
| **Scope** | {Object/Range/Transaction/Global} |
| **Lifetime** | {duration or epoch} |
| **Binding** | {who/what it's valid for} |
| **Transitivity** | [ ] Transitive  [ ] Non-transitive |
| **Revocation** | {how and when} |

**Cost Analysis:**
- Generation: __________
- Verification: __________
- Amortization strategy: __________

---

### 4. GUARANTEE VECTOR (Path Typing)

**Input G:**
```
⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩
⟨_____, _____, __________, _______, ___________, ____⟩
```

**Output G:**
```
⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩
⟨_____, _____, __________, _______, ___________, ____⟩
```

**Composition Operations:**

| Operation | Evidence Required | Result |
|-----------|------------------|--------|
| **Upgrade (↑)** | __________ | __________ |
| **Downgrade (⤓)** | __________ | __________ |
| **Sequential (▷)** | __________ | meet(A, B) |
| **Parallel (\|\|)** | __________ | meet(A, B) + merge |

**Weakest Component:**
- Component: __________
- Governs end-to-end: __________

---

### 5. CONTEXT CAPSULE

```json
{
  "invariant": "__________",
  "evidence": {
    "type": "__________",
    "scope": {"type": "________", "identifier": "______"},
    "lifetime": {"expiry_type": "________", "expiry_value": "______"}
  },
  "boundary": {
    "type": "__________",
    "identifier": "__________",
    "epoch": __
  },
  "mode": "__________",
  "fallback": {
    "degraded_mode": "__________",
    "degraded_guarantee": "⟨_____, _____, _____, _____, _____, _____⟩",
    "user_notification": "__________"
  }
}
```

**Capsule Operations Used:**
- [ ] restrict()  - Why: __________
- [ ] extend()    - Why: __________
- [ ] rebind()    - Why: __________
- [ ] renew()     - Why: __________
- [ ] degrade()   - Why: __________

---

### 6. MODE MATRIX SNAPSHOT

| Mode | Preserved Invariants | Evidence Required | Operations Allowed | Entry/Exit Trigger |
|------|---------------------|-------------------|-------------------|-------------------|
| **Floor** | __________ | __________ | __________ | __________ |
| **Target** | __________ | __________ | __________ | __________ |
| **Degraded** | __________ | __________ | __________ | __________ |
| **Recovery** | __________ | __________ | __________ | __________ |

**Cross-Service Compatibility:**
- Upstream mode: __________
- Downstream mode: __________
- Final promise: meet(upstream, downstream) = __________

---

### 7. DUALITY CHOICES

For each duality, mark your stance and justify:

**Safety ↔ Liveness**
```
Safety ←─────[  X  ]─────→ Liveness
```
- Stance: __________
- Justification: __________
- Evidence that enables this: __________

**Freshness ↔ Availability**
```
Freshness ←─────[  X  ]─────→ Availability
```
- Stance: __________
- Justification: __________
- Mode dependence: __________

**Coordination ↔ Confluence**
```
Coordination ←─────[  X  ]─────→ Confluence
```
- Stance: __________
- What we avoid: __________
- How: __________

**Determinism ↔ Adaptivity**
```
Determinism ←─────[  X  ]─────→ Adaptivity
```
- Stance: __________
- Tradeoff: __________

---

### 8. HUMAN MODEL (Operator Mental Framework)

**See:**
- Observable 1: __________
- Observable 2: __________
- Key metric: __________

**Think:**
- Question 1: __________
- Question 2: __________
- Decision point: __________

**Do:**
- Safe action 1: __________
- Safe action 2: __________
- Dangerous action to avoid: __________

**Incident Narrative:**
- Symptom: __________
- Root cause (invariant violated): __________
- Evidence missing/expired: __________
- Recovery action: __________

---

### 9. LEARNING SPIRAL

**Pass 1: Intuition (Felt Need)**
- Failure story: __________
- Invariant at risk: __________
- Simple fix (and why it's incomplete): __________

**Pass 2: Understanding (Limits)**
- Why simple fails at scale: __________
- Evidence-based solution: __________
- Trade-offs made explicit: __________

**Pass 3: Mastery (Composition)**
- How it composes with: __________
- Mode matrix under stress: __________
- Operator mental model: __________

---

### 10. TRANSFER TESTS

**Near Transfer:**
- Same pattern, nearby domain: __________
- Example: __________
- Invariant/evidence reused: __________

**Medium Transfer:**
- Related problem: __________
- Example: __________
- Mental model applied: __________

**Far Transfer:**
- Novel domain: __________
- Example: __________
- Abstraction level: __________

---

### 11. CROSS-CHAPTER THREADS

**Reinforces (from prior chapters):**
1. Concept: __________ (Chapter __)
   - How: __________
2. Concept: __________ (Chapter __)
   - How: __________

**Sets Up (for future chapters):**
1. Concept: __________ (Chapter __)
   - Teaser: __________

**Resonance Plan:**
- [ ] Recency proofs
- [ ] Causality vs real time
- [ ] Coordination budget
- [ ] Determinism and replay
- [ ] Degraded semantics
- [ ] Composition via capsules
- [ ] Governance invariants

---

### 12. SACRED DIAGRAMS

**Diagrams to Include:**
- [ ] Invariant Guardian (for __________)
- [ ] Evidence Flow (lifecycle of __________)
- [ ] Composition Ladder (showing __________)
- [ ] Mode Compass (modes for __________)
- [ ] Knowledge vs Data (separation in __________)

**Custom Diagram:**
- Purpose: __________
- Symbology used: __________

---

### 13. IRREDUCIBLE SENTENCE

**In essence:**
```
"__________________________________________________________
 __________________________________________________________"
```

(1-2 sentences that capture the core insight, the "why it must be so")

---

### 14. COGNITIVE LOAD CHECK

**New Ideas Introduced (max 3):**
1. Invariant: __________
2. Evidence type: __________
3. Composition pattern: __________

**Ideas Reinforced (prior concepts):**
1. __________
2. __________

---

### 15. VALIDATION CHECKLIST

- [ ] Maps to exactly one primary invariant from catalog?
- [ ] Uses evidence types with scope, lifetime, binding, revocation?
- [ ] Path typed with G vectors; meet/upgrade/downgrade explicit?
- [ ] Capsule has all five core fields (plus optional as needed)?
- [ ] Mode matrix shows all four modes and triggers?
- [ ] Dualities stated with justified stance?
- [ ] Spiral narrative present (intuition → understanding → mastery)?
- [ ] Contains three transfer tests (near, medium, far)?
- [ ] Reinforces two prior concepts and sets up one future concept?
- [ ] Ends with an irreducible sentence?
- [ ] Diagrams use consistent symbology from framework?
- [ ] Human mental model (See/Think/Do) included?
- [ ] No hidden downgrades (all explicit and labeled)?
- [ ] No evidence-free claims?

---

### 16. ANTI-PATTERNS TO AVOID

Mark any that might appear and plan reframes:

- [ ] WRONG: "System X achieves Y performance."
  - RIGHT: "System X protects __ by generating __ evidence."

- [ ] WRONG: "Use technique Z for speed."
  - RIGHT: "Technique Z avoids coordination by ensuring __ via __."

- [ ] WRONG: "The leader knows the truth."
  - RIGHT: "The leader's __ evidence authorizes action; others verify or degrade."

- [ ] WRONG: "Eventually consistent = faster."
  - RIGHT: "We trade __ evidence for weaker __ guarantee and lower latency."

---

### 17. NOTES AND OPEN QUESTIONS

**Questions to resolve:**
1. __________
2. __________

**Dependencies:**
- Needs input from: __________
- Blocks: __________

**Research needed:**
- __________

---
```

### 6.2 Example Filled Canvas (Follower Reads)

```markdown
# CHAPTER DEVELOPMENT CANVAS
## Chapter: 8 - Follower Reads with Freshness Guarantees

---

### 1. INVARIANT FOCUS

**Primary Invariant:**
- Name: Freshness
- From catalog: [X] Fundamental  [ ] Derived  [X] Composite
- Definition: Never represent data as fresher than it actually is; provide verifiable recency bound

**Supporting Invariants:**
1. Monotonicity (ensures time does not go backward in reads)
2. Visibility/Snapshot Isolation (ensures atomic view of state at φ)

**Threat Model:**
- Primary threat: Stale reads presented as fresh
- Attack vector: Replica lag, leadership staleness, clock skew
- Consequence if violated: Causal anomalies, user confusion, correctness violations

---

### 2. UNCERTAINTY ADDRESSED

**What Cannot Be Known:**
- Exact replica lag without coordination
- Reason: Asynchrony - no global "now"; network delays variable

**Cost to Know:**
- Mechanism: Synchronous read from leader
- Latency cost: +2-5ms network RTT
- Coordination cost: Leader becomes bottleneck
- Tradeoff: Freshness guarantee vs read scaling

**Acceptable Doubt:**
- What we can tolerate: Bounded staleness (e.g., 9s)- Bounded by: Closed timestamp φ propagation interval
- Degradation semantics: Fall back to BS(30s) or EO if φ unavailable

---

### 3. EVIDENCE GENERATED (Calculus)

**Primary Evidence Type(s):**
1. Type: Closed Timestamp (φ)
   - Category: [X] Order  [X] Recency  [ ] Inclusion  [ ] Identity
   - What it certifies: All transactions with commit_ts ≤ φ have been applied

**Evidence Properties:**

| Property | Value |
|----------|-------|
| **Scope** | Range (per-range, per-epoch) |
| **Lifetime** | 9s (3s generation + 6s grace period) |
| **Binding** | Range ID + Lease Epoch + φ timestamp |
| **Transitivity** | [X] Transitive  [ ] Non-transitive |
| **Revocation** | Lease epoch change or heartbeat timeout |

**Cost Analysis:**
- Generation: O(1) computation + broadcast to N replicas every 3s
- Verification: O(1) signature check + monotonicity check
- Amortization strategy: Single φ broadcast serves unlimited reads for 3-9s window

---

### 4. GUARANTEE VECTOR (Path Typing)

**Input G (Leader Read):**
```
⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩
⟨Range, SS,    SER,        Fresh(φ), Idem(K),     Auth(π)⟩
```

**Output G (Follower Read with φ):**
```
⟨Scope, Order, Visibility, Recency,   Idempotence, Auth⟩
⟨Range, Lx,    SI,         Fresh(φ),  Idem(K),     Auth(π)⟩
```

**Composition Operations:**

| Operation | Evidence Required | Result |
|-----------|------------------|--------|
| **Upgrade (↑)** | None - φ already present | Maintain Fresh(φ) |
| **Downgrade (⤓)** | φ expired | BS(30s) with label |
| **Sequential (▷)** | φ valid for all ranges | meet(A, B) |
| **Parallel (\|\|)** | Each range has φ_i | meet(φ_1, φ_2, ..., φ_n) |

**Weakest Component:**
- Component: Order (Lx vs SS)
- Governs end-to-end: Follower reads are linearizable per-object, not globally serializable

---

### 5. CONTEXT CAPSULE

```json
{
  "invariant": "Freshness",
  "evidence": {
    "type": "ClosedTimestamp",
    "scope": {"type": "Range", "identifier": "range_123"},
    "lifetime": {"expiry_type": "age_based", "expiry_value": "2025-10-01T12:35:05.789Z"}
  },
  "boundary": {
    "type": "Range",
    "identifier": "range_123",
    "epoch": 42
  },
  "mode": "Target",
  "fallback": {
    "degraded_mode": "Degraded",
    "degraded_guarantee": "⟨Range, Lx, SI, BS(30s), Idem(K), Auth(π)⟩",
    "user_notification": "X-Staleness-Bound: 30s"
  }
}
```

**Capsule Operations Used:**
- [X] restrict()  - Why: N/A (single range)
- [ ] extend()    - Why: N/A
- [ ] rebind()    - Why: N/A (same epoch)
- [X] renew()     - Why: φ refreshed every 3s
- [X] degrade()   - Why: φ expired after 9s

---

### 6. MODE MATRIX SNAPSHOT

| Mode | Preserved Invariants | Evidence Required | Operations Allowed | Entry/Exit Trigger |
|------|---------------------|-------------------|-------------------|-------------------|
| **Floor** | Monotonicity, Authenticity | Commit cert | Read (EO) | Evidence validation failed |
| **Target** | + Freshness(φ), Visibility(SI) | φ (age < 9s) | Read (Fresh) | φ active and valid |
| **Degraded** | + BoundedStaleness(30s) | Last known φ | Read (BS) + label | φ age > 9s, < 30s |
| **Recovery** | Monotonicity only | None | Proxy to leader | φ age > 30s or epoch changed |

**Cross-Service Compatibility:**
- Upstream mode: Target (Leader write path)
- Downstream mode: Target (Follower read path with φ)
- Final promise: meet(Target_write, Target_read) = ⟨Range, Lx, SI, Fresh(φ), Idem(K), Auth(π)⟩

---

### 7. DUALITY CHOICES

**Freshness ↔ Availability**
```
Freshness ←─────[    X    ]─────→ Availability
```
- Stance: Balanced - Fresh when φ available, degrade predictably when not
- Justification: φ mechanism allows high availability (read from any follower) while maintaining freshness
- Mode dependence: Target = Fresh, Degraded = BS, Recovery = Proxy

**Safety ↔ Liveness**
```
Safety ←─────[   X     ]─────→ Liveness
```
- Stance: Safety-first - Never serve stale as fresh
- Justification: Monotonicity enforced even in floor mode
- Evidence that enables this: Commit certificates always verified

---

### 8. HUMAN MODEL (Operator Mental Framework)

**See:**
- Observable 1: Closed timestamp age metric (per range)
- Observable 2: Follower read success rate vs degraded read rate
- Key metric: Percentage of reads served with Fresh(φ) vs BS(δ)

**Think:**
- Question 1: Is φ propagation healthy across all ranges?
- Question 2: What is acceptable staleness bound for this workload?
- Decision point: Should I increase φ propagation frequency or relax staleness bound?

**Do:**
- Safe action 1: Monitor φ age; alert if > 9s threshold
- Safe action 2: Adjust staleness policy based on SLO
- Dangerous action to avoid: Disable φ verification to "improve performance"

**Incident Narrative:**
- Symptom: 50% of follower reads returning X-Staleness-Bound: 30s header
- Root cause (invariant violated): φ propagation failed due to network partition
- Evidence missing/expired: φ heartbeats not reaching followers for 20s
- Recovery action: Re-establish network connectivity; followers transition from Degraded → Target as φ renewed

---

### 9. LEARNING SPIRAL

**Pass 1: Intuition (Felt Need)**
- Failure story: Leader becomes read bottleneck; need to scale reads
- Invariant at risk: Freshness (if we read from stale replicas)
- Simple fix (and why it's incomplete): "Read from any replica" - but how do we know it's fresh?

**Pass 2: Understanding (Limits)**
- Why simple fails at scale: Replica lag is variable; can't trust local clocks
- Evidence-based solution: Closed timestamp φ provides verifiable recency bound
- Trade-offs made explicit: 3-9s staleness bound vs unlimited read scaling

**Pass 3: Mastery (Composition)**
- How it composes with: Multi-range transactions (need φ for each range)
- Mode matrix under stress: Graceful degradation from Fresh → BS → EO
- Operator mental model: See φ age, think about freshness/availability tradeoff, adjust policy

---

### 10. TRANSFER TESTS

**Near Transfer:**
- Same pattern, nearby domain: Reading from cache with TTL
- Example: HTTP cache with Cache-Control: max-age header
- Invariant/evidence reused: Freshness via time-bound evidence

**Medium Transfer:**
- Related problem: Distributed snapshot reads across multiple databases
- Example: Coordinating read timestamp across shards
- Mental model applied: Each shard provides φ_i; transaction succeeds if all φ_i ≥ read_ts

**Far Transfer:**
- Novel domain: Academic paper citations and freshness
- Example: Citing a paper with "as of date X"
- Abstraction level: φ as a freshness certificate; citation date as evidence lifetime

---

### 11. CROSS-CHAPTER THREADS

**Reinforces (from prior chapters):**
1. Concept: Leases (Chapter 5)
   - How: φ is only valid within lease epoch E
2. Concept: Evidence lifecycle (Chapter 3)
   - How: φ follows Generate → Validate → Active → Expire → Renew

**Sets Up (for future chapters):**
1. Concept: Distributed transactions (Chapter 10)
   - Teaser: How do we coordinate φ across multiple ranges for serializable transactions?

**Resonance Plan:**
- [X] Recency proofs (φ as primary example)
- [X] Causality vs real time (φ is not wall-clock time)
- [X] Coordination budget (avoid coordinating on every read)
- [X] Degraded semantics (predictable fallback to BS)
- [X] Composition via capsules (φ travels with read request)
- [ ] Governance invariants

---

### 12. SACRED DIAGRAMS

**Diagrams to Include:**
- [X] Invariant Guardian (for Freshness protected by closed timestamp)
- [X] Evidence Flow (lifecycle of φ from generation to expiry)
- [X] Composition Ladder (showing Fresh → BS → EO degradation)
- [X] Mode Compass (modes for follower read path)
- [X] Knowledge vs Data (separation of φ heartbeat from read path)

**Custom Diagram:**
- Purpose: Show φ propagation timeline
- Symbology used: Timeline with φ generation points, heartbeat intervals, expiry markers

---

### 13. IRREDUCIBLE SENTENCE

**In essence:**
```
"Follower reads scale by amortizing a single freshness proof (φ) across unlimited reads,
 trading precise real-time freshness for a verifiable staleness bound enforced by evidence expiry."
```

---

### 14. COGNITIVE LOAD CHECK

**New Ideas Introduced (max 3):**
1. Invariant: Freshness (bounded staleness with verifiable proof)
2. Evidence type: Closed timestamp (φ)
3. Composition pattern: Evidence amortization (one φ → many reads)

**Ideas Reinforced (prior concepts):**
1. Leases (φ bound to lease epoch)
2. Mode matrix (graceful degradation)

---

### 15. VALIDATION CHECKLIST

- [X] Maps to exactly one primary invariant from catalog? (Freshness)
- [X] Uses evidence types with scope, lifetime, binding, revocation? (φ)
- [X] Path typed with G vectors; meet/upgrade/downgrade explicit? (Yes)
- [X] Capsule has all five core fields (plus optional as needed)? (Yes)
- [X] Mode matrix shows all four modes and triggers? (Yes)
- [X] Dualities stated with justified stance? (Freshness/Availability, Safety/Liveness)
- [X] Spiral narrative present (intuition → understanding → mastery)? (Yes)
- [X] Contains three transfer tests (near, medium, far)? (Yes)
- [X] Reinforces two prior concepts and sets up one future concept? (Yes)
- [X] Ends with an irreducible sentence? (Yes)
- [X] Diagrams use consistent symbology from framework? (Yes)
- [X] Human mental model (See/Think/Do) included? (Yes)
- [X] No hidden downgrades (all explicit and labeled)? (Yes)
- [X] No evidence-free claims? (Yes)

---
```

---

## 7. Supporting Tools

### 7.1 Mental Linter (Quick Validation Script)

```python
#!/usr/bin/env python3
"""
Mental Linter for Chapter Drafts
Checks for presence of framework elements
"""

import re
import sys

class ChapterLinter:
    def __init__(self, content):
        self.content = content
        self.errors = []
        self.warnings = []

    def check_invariant_naming(self):
        """Check if invariants are named from the catalog"""
        catalog = [
            "Conservation", "Uniqueness", "Authenticity", "Integrity",
            "Order", "Exclusivity", "Monotonicity", "Freshness",
            "Visibility", "Convergence", "Idempotence", "BoundedStaleness",
            "Availability"
        ]

        found_invariants = re.findall(r'\b(invariant[s]?)\s*:\s*(\w+)', self.content, re.IGNORECASE)

        if not found_invariants:
            self.errors.append("No explicitly named invariant found")
        else:
            for _, inv in found_invariants:
                if inv not in catalog:
                    self.warnings.append(f"Invariant '{inv}' not in standard catalog")

    def check_evidence_properties(self):
        """Check if evidence has required properties"""
        required = ["scope", "lifetime", "binding"]

        for prop in required:
            if not re.search(rf'\b{prop}\b', self.content, re.IGNORECASE):
                self.errors.append(f"Evidence property '{prop}' not documented")

    def check_guarantee_vector(self):
        """Check if G vectors are present"""
        g_vector_pattern = r'⟨[^⟩]+⟩'

        if not re.search(g_vector_pattern, self.content):
            self.errors.append("No guarantee vector (G = ⟨...⟩) found")

    def check_context_capsule(self):
        """Check if context capsules have required fields"""
        required_fields = ["invariant", "evidence", "boundary", "mode", "fallback"]

        capsule_count = 0
        for field in required_fields:
            if re.search(rf'["\']?{field}["\']?\s*:', self.content):
                capsule_count += 1

        if capsule_count < len(required_fields):
            missing = len(required_fields) - capsule_count
            self.warnings.append(f"Context capsule may be missing {missing} required fields")

    def check_mode_matrix(self):
        """Check if all four modes are mentioned"""
        modes = ["Floor", "Target", "Degraded", "Recovery"]

        found_modes = []
        for mode in modes:
            if re.search(rf'\b{mode}\b', self.content, re.IGNORECASE):
                found_modes.append(mode)

        if len(found_modes) < 4:
            missing = set(modes) - set(found_modes)
            self.warnings.append(f"Mode matrix incomplete. Missing: {', '.join(missing)}")

    def check_explicit_downgrades(self):
        """Check for downgrade labeling"""
        downgrade_indicators = [r'⤓', r'downgrade', r'degrade', r'fallback']

        has_downgrade = any(re.search(indicator, self.content, re.IGNORECASE)
                           for indicator in downgrade_indicators)

        if not has_downgrade and re.search(r'\bweak\b|\bstale\b|\beventual\b', self.content, re.IGNORECASE):
            self.warnings.append("Possible implicit downgrade - should be explicit and labeled")

    def check_learning_spiral(self):
        """Check for three-pass learning structure"""
        passes = ["intuition", "understanding", "mastery"]

        found_passes = []
        for p in passes:
            if re.search(rf'\b{p}\b', self.content, re.IGNORECASE):
                found_passes.append(p)

        if len(found_passes) < 3:
            self.warnings.append("Learning spiral may be incomplete (should have: intuition, understanding, mastery)")

    def check_transfer_tests(self):
        """Check for transfer test examples"""
        test_types = ["near", "medium", "far"]

        found_tests = []
        for t in test_types:
            if re.search(rf'\b{t}\b.*transfer', self.content, re.IGNORECASE):
                found_tests.append(t)

        if len(found_tests) < 3:
            missing = set(test_types) - set(found_tests)
            self.warnings.append(f"Transfer tests incomplete. Missing: {', '.join(missing)}")

    def check_anti_patterns(self):
        """Check for common anti-patterns"""
        anti_patterns = [
            (r'\bachieves\s+\d+.*performance\b', "Performance claim without evidence mechanism"),
            (r'\bfaster\b(?!.*because|.*via|.*by)', "Speed claim without justification"),
            (r'\bleader knows\b(?!.*evidence)', "Leader authority without evidence framing"),
        ]

        for pattern, message in anti_patterns:
            if re.search(pattern, self.content, re.IGNORECASE):
                self.warnings.append(f"Possible anti-pattern: {message}")

    def lint(self):
        """Run all checks"""
        self.check_invariant_naming()
        self.check_evidence_properties()
        self.check_guarantee_vector()
        self.check_context_capsule()
        self.check_mode_matrix()
        self.check_explicit_downgrades()
        self.check_learning_spiral()
        self.check_transfer_tests()
        self.check_anti_patterns()

        return self.errors, self.warnings

def main():
    if len(sys.argv) != 2:
        print("Usage: python mental_linter.py <chapter_file.md>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        content = f.read()

    linter = ChapterLinter(content)
    errors, warnings = linter.lint()

    print(f"=== Mental Linter Results for {sys.argv[1]} ===\n")

    if errors:
        print("ERRORS (must fix):")
        for err in errors:
            print(f"  ✗ {err}")
        print()

    if warnings:
        print("WARNINGS (should review):")
        for warn in warnings:
            print(f"  ⚠ {warn}")
        print()

    if not errors and not warnings:
        print("✓ All checks passed!")

    sys.exit(len(errors))

if __name__ == '__main__':
    main()
```

### 7.2 Guarantee Vector Validator (Python)

```python
#!/usr/bin/env python3
"""
Guarantee Vector Validator
Validates composition operations follow meet semantics
"""

class GuaranteeVector:
    SCOPE_HIERARCHY = ["Object", "Range", "Transaction", "Global"]
    ORDER_HIERARCHY = ["None", "Causal", "Lx", "SS"]
    VISIBILITY_HIERARCHY = ["Fractured", "RA", "SI", "SER"]
    RECENCY_HIERARCHY = ["EO", "BS", "Fresh"]

    def __init__(self, scope, order, visibility, recency, idempotence, auth):
        self.scope = scope
        self.order = order
        self.visibility = visibility
        self.recency = recency
        self.idempotence = idempotence
        self.auth = auth

    @staticmethod
    def _meet_component(a, b, hierarchy):
        """Return weaker (earlier in hierarchy) component"""
        idx_a = hierarchy.index(a) if a in hierarchy else -1
        idx_b = hierarchy.index(b) if b in hierarchy else -1

        if idx_a == -1 or idx_b == -1:
            raise ValueError(f"Invalid values: {a}, {b}")

        return hierarchy[min(idx_a, idx_b)]

    def meet(self, other):
        """Compute meet (weakest) of two guarantee vectors"""
        return GuaranteeVector(
            scope=self._meet_component(self.scope, other.scope, self.SCOPE_HIERARCHY),
            order=self._meet_component(self.order, other.order, self.ORDER_HIERARCHY),
            visibility=self._meet_component(self.visibility, other.visibility, self.VISIBILITY_HIERARCHY),
            recency=self._meet_recency(self.recency, other.recency),
            idempotence=self._meet_simple(self.idempotence, other.idempotence),
            auth=self._meet_simple(self.auth, other.auth)
        )

    def _meet_recency(self, a, b):
        """Meet for recency (special handling for BS values)"""
        # Simplified: EO < BS < Fresh
        if "EO" in [a, b]:
            return "EO"
        if "BS" in a and "BS" in b:
            # Extract numeric bounds if present
            return "BS"  # In practice, take max bound
        if "Fresh" in [a, b] and "BS" in [a, b]:
            return "BS"
        return "Fresh"

    def _meet_simple(self, a, b):
        """Simple meet: None < Something"""
        if a == "None" or b == "None":
            return "None"
        if a.startswith("Unauth") or b.startswith("Unauth"):
            return "Unauth"
        return a  # Assume compatible

    def __str__(self):
        return f"⟨{self.scope}, {self.order}, {self.visibility}, {self.recency}, {self.idempotence}, {self.auth}⟩"

# Example usage
if __name__ == "__main__":
    leader_read = GuaranteeVector("Range", "SS", "SER", "Fresh", "Idem(K)", "Auth(π)")
    follower_read = GuaranteeVector("Range", "Lx", "SI", "Fresh", "Idem(K)", "Auth(π)")

    composed = leader_read.meet(follower_read)

    print(f"Leader:    {leader_read}")
    print(f"Follower:  {follower_read}")
    print(f"Composed:  {composed}")
    print(f"\nWeakest component: Order (Lx < SS)")
```

### 7.3 Capsule Operation Examples (Pseudocode)

See section 4.3 for full Python implementations of:
- `restrict()` - Narrow scope at boundary
- `extend()` - Widen scope after upgrade
- `rebind()` - Bind to new identity/epoch/domain
- `renew()` - Refresh expiring evidence
- `degrade()` - Apply fallback policy

---

## 8. Best Practices and Usage Guidelines

### 8.1 Getting Started

1. **Begin with the Chapter Canvas**
   - Fill out sections 1-3 (Invariant, Uncertainty, Evidence) first
   - This forces clarity about what you're protecting and how

2. **Type the guarantee path**
   - Map out input/output G vectors
   - Identify all composition points and boundaries

3. **Define modes early**
   - What happens when evidence expires?
   - What's the minimum viable correctness (floor)?

4. **Choose 1-2 diagrams**
   - Not all five are needed in every chapter
   - Pick the ones that clarify the core insight

### 8.2 Common Workflows

**For a new mechanism (e.g., "Two-Phase Commit"):**
1. Fill out Guarantee Vector YAML (what guarantees change?)
2. Create Evidence Card (what proof is generated?)
3. Fill out Mode Matrix (what happens under stress?)
4. Draw Invariant Guardian diagram
5. Fill out Chapter Canvas
6. Run Mental Linter

**For composition across services:**
1. Define capsule for each boundary crossing
2. Type each segment with G vectors
3. Identify meet points (where guarantees weaken)
4. Draw Composition Ladder
5. Validate with Capsule Operations pseudocode

**For failure mode analysis:**
1. Create Mode Matrix YAML for each component
2. Map evidence expiry → mode transitions
3. Draw Mode Compass
4. Fill out Human Model (See/Think/Do)

### 8.3 Validation Workflow

Before submitting a chapter:
1. Fill out complete Chapter Canvas
2. Check all 15 validation checklist items
3. Run Mental Linter on draft
4. Validate G vector composition with validator script
5. Review all diagrams for consistent symbology
6. Confirm irreducible sentence captures core insight

### 8.4 Tips for Consistency

- **Reuse terminology**: Always use catalog invariant names
- **Reference prior chapters**: "As we saw with leases in Chapter 5..."
- **Label downgrades**: Never silently accept weaker guarantees
- **Show evidence costs**: Generation vs verification vs amortization
- **Think in layers**: Physics (constraints) → Strategies (patterns) → Tactics (implementations)

---

## 9. Quick Reference

### Invariant Catalog (Brief)

| Category | Invariants |
|----------|------------|
| **Fundamental** | Conservation, Uniqueness, Authenticity, Integrity |
| **Derived** | Order, Exclusivity, Monotonicity |
| **Composite** | Freshness, Visibility, Convergence, Idempotence, Bounded Staleness, Availability |

### Evidence Types (Brief)

| Type | What it proves | Typical lifetime |
|------|---------------|------------------|
| **Commit Certificate** | Operation is durable | Permanent |
| **Lease Epoch** | Exclusive authority | Seconds to minutes |
| **Closed Timestamp** | Recency bound | Seconds |
| **Merkle/Verkle Proof** | Inclusion in set | Permanent |
| **Signature** | Authenticity/authorization | Variable |

### Guarantee Vector Components

| Component | Values (weak → strong) |
|-----------|----------------------|
| **Scope** | Object → Range → Transaction → Global |
| **Order** | None → Causal → Lx → SS |
| **Visibility** | Fractured → RA → SI → SER |
| **Recency** | EO → BS(δ) → Fresh(φ) |
| **Idempotence** | None → Idem(K) |
| **Auth** | Unauth → Auth(π) |

### Mode Transitions (Typical)

```
Target ←→ Degraded ←→ Recovery
   ↓          ↓           ↓
          Floor
```

- **Target**: Normal operation, all evidence present
- **Degraded**: Reduced guarantees, explicit labels
- **Recovery**: Rebuilding evidence, restricted operations
- **Floor**: Minimum viable correctness, never lie

---

## 10. Conclusion

These templates provide a comprehensive toolkit for authoring chapters that adhere to the Unified Mental Model Authoring Framework 3.0. By using:

- **Guarantee Vectors** to type paths and composition
- **Evidence Cards** to document proof lifecycles
- **Mode Matrices** to plan degradation
- **Context Capsules** to carry guarantees across boundaries
- **Sacred Diagrams** to visualize patterns consistently
- **Chapter Canvases** to ensure completeness

...authors can create chapters that reinforce a coherent mental model, teach transferable understanding, and maintain consistency across the entire book.

**Key Principles:**
1. Invariants first - everything protects something
2. Evidence explicit - scope, lifetime, binding, revocation
3. Composition typed - G vectors and meet semantics
4. Modes principled - floor, target, degraded, recovery
5. Downgrades labeled - never silently accept weaker guarantees

**Success Metrics:**
- Reader can name invariants being protected
- Reader can identify evidence and its lifecycle
- Reader can trace guarantee composition
- Reader can predict degradation modes
- Reader can apply patterns to new domains

---

**Document Version:** 1.0
**Last Updated:** 2025-10-01
**Maintained By:** Book Authors
**Reference:** ChapterCraftingGuide.md
