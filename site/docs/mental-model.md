# The Unified Mental Model

## Distributed Systems as Evidence Machines

> "Every distributed system is a machine for preserving invariants across space and time by converting uncertainty into evidence."

This single principle underlies every concept in this book. Understanding it transforms how you think about distributed systems—from mysterious black boxes to predictable evidence-processing machines.

## The Core Principle

### What Are Invariants?

Invariants are properties that must remain true for a system to be correct:
- **Conservation**: Nothing created or destroyed except through authorized flows
- **Uniqueness**: At most one leader, one owner, one decision
- **Order**: Events maintain their causal relationships
- **Authenticity**: Only authorized changes from verified sources

### What Is Uncertainty?

Uncertainty is what we don't know and can't control:
- **Network delays**: Messages take unknown time
- **Failures**: Nodes crash without warning
- **Asynchrony**: No global clock exists
- **Partitions**: Network splits isolate components
- **Byzantine behavior**: Malicious or buggy nodes lie

### What Is Evidence?

Evidence is proof that allows us to act safely despite uncertainty:
- **Quorum certificates**: Proof of majority agreement
- **Leases**: Time-bounded exclusive access
- **Timestamps**: Ordering relationships
- **Signatures**: Authentication and integrity
- **Heartbeats**: Liveness detection

## The Three-Layer Mental Model

Every distributed systems concept exists at one of three layers:

### Layer 1: Eternal Truths (Physics)
What cannot be changed—the laws of physics and mathematics:
- Information travels at finite speed
- No universal "now" exists across space
- Failures are indistinguishable from delays
- Agreement requires communication
- Entropy increases without energy

### Layer 2: Design Patterns (Strategies)
How we navigate physical reality:
- Generate evidence through protocols
- Protect invariants with mechanisms
- Avoid coordination where possible
- Degrade predictably under stress
- Compose systems with explicit contracts

### Layer 3: Implementation Choices (Tactics)
The specific technologies we build:
- Paxos, Raft, EPaxos (consensus protocols)
- B-trees, LSM trees (storage structures)
- TCP, QUIC (network protocols)
- Docker, Kubernetes (orchestration)
- Spanner, DynamoDB (databases)

## The Evidence Lifecycle

All evidence follows a predictable lifecycle:

```
Generated → Validated → Active → Expiring → Expired → Renewed/Revoked
```

### Generation
Evidence is created through:
- **Consensus rounds**: Collecting votes
- **Clock synchronization**: Bounding time uncertainty
- **Cryptographic proofs**: Signing data
- **Failure detection**: Timeout expiration

### Validation
Evidence is verified by checking:
- **Scope**: What it covers
- **Lifetime**: When it expires
- **Binding**: Who it applies to
- **Authority**: Who created it

### Use
Evidence enables safe actions:
- **Writes**: With lease evidence
- **Reads**: With freshness evidence
- **Decisions**: With quorum evidence
- **Trust**: With signature evidence

### Expiration
Evidence becomes invalid through:
- **Timeout**: Predetermined expiration
- **Revocation**: Explicit invalidation
- **Epoch change**: System reconfiguration
- **Violation**: Assumption failure

## The Guarantee Vector

Every operation provides guarantees expressed as a vector:

```
G = ⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩
```

- **Scope**: Object, Range, Transaction, or Global
- **Order**: None, Causal, Linearizable, or Serializable
- **Visibility**: Fractured, Atomic, Snapshot, or Serializable
  - Note: "Fractured" is a custom term (not ANSI SQL standard) describing visibility incoherence during network partitions
- **Recency**: Eventual, Bounded, or Fresh
- **Idempotence**: None or Keyed
- **Auth**: Unauthenticated or Authenticated

### Composition Rules

When systems compose, guarantees follow the "weakest link" principle:
- Strong → Weak = Weak (unless evidence upgrades it)
- Weak → Strong requires new evidence
- Parallel composition takes the minimum
- Sequential composition may degrade

## The Mode Matrix

Systems operate in different modes based on available evidence:

### Target Mode
Normal operation with full evidence:
- All invariants protected
- Strong guarantees provided
- Optimal performance

### Degraded Mode
Partial evidence available:
- Core invariants protected
- Weaker guarantees
- Reduced functionality

### Floor Mode
Minimum viable operation:
- Safety invariants only
- Basic guarantees
- Survival focus

### Recovery Mode
Rebuilding evidence:
- Limited operations
- Evidence regeneration
- Gradual restoration

## Context Capsules

Evidence travels in context capsules at system boundaries:

```
{
  invariant: "What we're protecting",
  evidence: "Proof we have",
  boundary: "Valid scope",
  mode: "Current operating mode",
  fallback: "What to do if invalid"
}
```

## Applying the Mental Model

### For Design
1. **Identify invariants** that must be preserved
2. **Recognize uncertainties** in the environment
3. **Determine evidence** needed to protect invariants
4. **Design mechanisms** to generate evidence
5. **Plan degradation** when evidence is unavailable

### For Implementation
1. **Choose protocols** that generate required evidence
2. **Implement validation** at every boundary
3. **Handle expiration** explicitly
4. **Provide fallbacks** for evidence loss
5. **Monitor evidence** health continuously

### For Operations
1. **Track evidence** age and validity
2. **Detect degradation** through evidence loss
3. **Respond to modes** appropriately
4. **Restore evidence** systematically
5. **Learn from incidents** about evidence gaps

## Common Patterns

### Evidence-Free Zones
Places where we operate without evidence (dangerous):
- After timeout before confirmation
- During network partition
- Between lease expiration and renewal

### Evidence Chains
How evidence propagates through systems:
- Leader generates → Followers validate
- Primary writes → Backups acknowledge
- Coordinator decides → Participants execute

### Evidence Boundaries
Where evidence must be checked:
- Service boundaries
- Network boundaries
- Trust boundaries
- Failure domains

## The Power of This Model

This mental model gives you:

### Predictive Power
- Anticipate failure modes
- Predict degradation patterns
- Identify evidence gaps
- Plan recovery strategies

### Diagnostic Power
- Trace evidence flow
- Find invalidation points
- Identify missing evidence
- Locate trust violations

### Design Power
- Choose appropriate evidence
- Place generation points
- Plan validation boundaries
- Design degradation modes

## Examples Throughout the Book

Every chapter reinforces this model:

- **Chapter 1**: Impossibility results show where evidence cannot exist
- **Chapter 2**: Time systems generate ordering evidence
- **Chapter 3**: Consensus protocols manufacture agreement evidence
- **Chapter 4**: Replication maintains durability evidence
- **Chapter 5-7**: Evolution of evidence generation mechanisms
- **Chapter 8-10**: Modern evidence patterns
- **Chapter 11-13**: Evidence at planet scale
- **Chapter 14-16**: Practical evidence management
- **Chapter 17-19**: Advanced evidence structures
- **Chapter 20-21**: Future of evidence systems

## Your Journey

As you read this book, constantly ask:
1. What invariant is at risk?
2. What uncertainty threatens it?
3. What evidence protects it?
4. How is evidence generated?
5. When does evidence expire?
6. What happens without evidence?

These questions will become second nature, transforming you from someone who operates distributed systems to someone who truly understands them.

## Summary

The unified mental model is simple but powerful:
- **Invariants** must be preserved
- **Uncertainty** threatens invariants
- **Evidence** protects against uncertainty
- **Mechanisms** generate evidence
- **Boundaries** validate evidence
- **Modes** handle evidence loss

Master this model, and you master distributed systems.

---

> "Once you see distributed systems as evidence machines, you can never unsee it. Every protocol, every mechanism, every failure—they all become evidence transformations."

Continue to [Chapter 1: The Impossibility Results That Define Our Field](chapter-01/index.md) →