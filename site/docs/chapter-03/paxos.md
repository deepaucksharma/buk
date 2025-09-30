# Paxos Deep Dive

## The Protocol That Started It All

> "Paxos is the foundation of distributed consensus—every other protocol is either Paxos in disguise or explicitly not Paxos."

Paxos, introduced by Leslie Lamport in 1989 (and published in 1998), remains the gold standard for consensus protocols. Despite its reputation for complexity, Paxos is elegantly simple once you understand its core insight: **consensus is about preventing conflicting decisions through careful promise management**.

## The Core Insight

### The Problem Paxos Solves
Multiple proposers trying to get a value chosen, with:
- Asynchronous network (no timing assumptions)
- Crash failures (nodes can fail and recover)
- No Byzantine behavior (no lying)
- Must ensure only one value is chosen

### The Brilliant Solution
Two-phase protocol with promises:
1. **Phase 1**: Establish the right to propose
2. **Phase 2**: Actually propose a value

The key: **Higher-numbered proposals must discover and preserve any value that might have been chosen in lower-numbered proposals**.

## The Basic Paxos Protocol

### Roles
- **Proposers**: Propose values
- **Acceptors**: Vote on proposals
- **Learners**: Learn the chosen value

### Phase 1: Prepare

#### Proposer Side
```python
class Proposer:
    def prepare(self):
        # Choose unique proposal number
        self.proposal_num = self.get_next_proposal_number()

        # Send to majority of acceptors
        prepare_msg = Prepare(self.proposal_num)
        self.send_to_acceptors(prepare_msg)

        # Wait for promises
        promises = self.collect_promises()

        if len(promises) > self.num_acceptors / 2:
            # Got majority, proceed to Phase 2
            return self.analyze_promises(promises)
        else:
            # Failed, try again with higher number
            return self.retry()
```

#### Acceptor Side
```python
class Acceptor:
    def on_prepare(self, prepare_msg):
        if prepare_msg.proposal_num > self.promised_num:
            # Promise not to accept lower proposals
            self.promised_num = prepare_msg.proposal_num

            # Report previously accepted value if any
            promise = Promise(
                proposal_num=prepare_msg.proposal_num,
                accepted_num=self.accepted_num,
                accepted_val=self.accepted_val
            )
            return promise
        else:
            # Reject - already promised higher
            return Reject(self.promised_num)
```

### Phase 2: Accept

#### Proposer Side
```python
def accept_phase(self, promises):
    # Choose value to propose
    if any(p.accepted_val for p in promises):
        # Must use previously accepted value with highest proposal
        value = max(promises, key=lambda p: p.accepted_num).accepted_val
    else:
        # Free to choose own value
        value = self.client_value

    # Send accept request
    accept_msg = Accept(self.proposal_num, value)
    self.send_to_acceptors(accept_msg)

    # Wait for accepts
    accepts = self.collect_accepts()

    if len(accepts) > self.num_acceptors / 2:
        # Value is chosen!
        return Chosen(value)
    else:
        # Failed, retry
        return self.retry()
```

#### Acceptor Side
```python
def on_accept(self, accept_msg):
    if accept_msg.proposal_num >= self.promised_num:
        # Accept the proposal
        self.promised_num = accept_msg.proposal_num
        self.accepted_num = accept_msg.proposal_num
        self.accepted_val = accept_msg.value

        return Accepted(accept_msg.proposal_num, accept_msg.value)
    else:
        # Reject - promised not to accept
        return Reject(self.promised_num)
```

## The Paxos Invariants

### P1: An acceptor accepts the first proposal it receives
Simple starting point.

### P2: If a proposal with value v is chosen, then every higher-numbered proposal that is chosen has value v
This is the key safety property.

### P2a: If a proposal with value v is chosen, then every higher-numbered proposal accepted by any acceptor has value v
Stronger, implies P2.

### P2b: If a proposal with value v is chosen, then every higher-numbered proposal issued by any proposer has value v
Even stronger, implies P2a.

### P2c: For any v and n, if a proposal with value v and number n is issued, then there is a set S consisting of a majority of acceptors such that either:
1. No acceptor in S has accepted any proposal numbered less than n, or
2. v is the value of the highest-numbered proposal among all proposals numbered less than n accepted by acceptors in S

This is what the prepare phase ensures!

## Multi-Paxos: The Practical Version

Basic Paxos chooses a single value. Multi-Paxos extends this to choose a sequence of values (a log).

### The Optimization
1. **Elect a stable leader** using Phase 1
2. **Skip Phase 1** for subsequent values
3. **Only run Phase 2** until leader fails

### Leader Election
```python
class MultiPaxosLeader:
    def become_leader(self):
        # Run Phase 1 for all future instances
        self.proposal_num = self.get_next_proposal_number()

        # Prepare for infinite range
        prepare_msg = Prepare(
            proposal_num=self.proposal_num,
            instance_range=(self.next_instance, ∞)
        )

        promises = self.send_prepare_and_collect()

        if self.got_majority(promises):
            self.is_leader = True
            self.process_promises(promises)
            # Can now run Phase 2 only
```

### Log Replication
```python
def replicate_command(self, command):
    if not self.is_leader:
        return self.forward_to_leader(command)

    # Assign next log position
    instance = self.next_instance
    self.next_instance += 1

    # Skip Phase 1, go directly to Phase 2
    accept_msg = Accept(
        proposal_num=self.proposal_num,
        instance=instance,
        value=command
    )

    accepts = self.send_accept_and_collect(accept_msg)

    if self.got_majority(accepts):
        self.commit(instance, command)
        return Success()
    else:
        # Lost leadership
        self.is_leader = False
        return self.retry_as_follower()
```

## Paxos in Production

### Google's Usage
Google uses Paxos extensively:
- **Chubby**: Lock service using Multi-Paxos
- **Megastore**: Paxos for wide-area replication
- **Spanner**: Paxos for replication groups

### Implementation Challenges

#### Challenge 1: Dueling Proposers
**Problem**: Two proposers keep interfering
```
Proposer1: Prepare(1) → Success → Accept(1,A) → Fail
Proposer2: Prepare(2) → Success → Accept(2,B) → Fail
Proposer1: Prepare(3) → Success → Accept(3,A) → Fail
...
```

**Solution**: Exponential backoff
```python
def retry_with_backoff(self):
    delay = min(
        self.base_delay * (2 ** self.retry_count),
        self.max_delay
    )
    time.sleep(delay + random.uniform(0, delay/2))
    self.retry_count += 1
```

#### Challenge 2: Acceptor State Persistence
**Problem**: Acceptor must remember promises across crashes

**Solution**: Write-ahead logging
```python
def on_prepare(self, msg):
    # Persist state before responding
    self.wal.write({
        'type': 'promise',
        'promised_num': msg.proposal_num,
        'timestamp': time.time()
    })
    self.wal.flush()

    # Now safe to promise
    self.promised_num = msg.proposal_num
    return Promise(...)
```

#### Challenge 3: Learning the Decision
**Problem**: How do learners find out a value was chosen?

**Solution 1**: Acceptors notify all learners
```python
def on_accept(self, msg):
    if self.should_accept(msg):
        # ... accept logic ...

        # Notify learners
        for learner in self.learners:
            learner.notify(Accepted(msg.instance, msg.value))
```

**Solution 2**: Distinguished learner
- Acceptors notify one learner
- That learner notifies others
- Reduces messages from O(n²) to O(n)

## Paxos Variants

### Fast Paxos
Skip Phase 1 in common case:
- Proposer sends value directly to acceptors
- Acceptors accept if no conflict
- Fall back to classic Paxos on collision

### Byzantine Paxos
Handle Byzantine failures:
- Need 3f+1 acceptors (not 2f+1)
- Use cryptographic signatures
- Verify all messages

### Cheap Paxos
Reduce number of acceptors:
- f+1 main acceptors
- f auxiliary acceptors
- Auxiliaries activate only during failures

### Generalized Paxos
Allow non-interfering concurrent operations:
- Commands that commute can be reordered
- Reduces conflicts and improves throughput

## Evidence Model for Paxos

### Evidence Types

#### Promise Certificate
```python
class PromiseCertificate:
    def __init__(self, proposal_num, promises):
        self.proposal_num = proposal_num
        self.promises = promises  # From majority
        self.timestamp = time.time()

    def is_valid(self):
        return (
            len(self.promises) > self.total_acceptors / 2 and
            all(p.proposal_num == self.proposal_num for p in self.promises)
        )

    def get_constrained_value(self):
        """Returns value we must propose, if any"""
        accepted = [p for p in self.promises if p.accepted_val]
        if accepted:
            return max(accepted, key=lambda p: p.accepted_num).accepted_val
        return None
```

#### Accept Certificate
```python
class AcceptCertificate:
    def __init__(self, proposal_num, value, accepts):
        self.proposal_num = proposal_num
        self.value = value
        self.accepts = accepts  # From majority

    def is_chosen(self):
        return len(self.accepts) > self.total_acceptors / 2
```

### Evidence Lifecycle
1. **Generate**: Proposer creates proposal number
2. **Collect**: Gather promises/accepts
3. **Validate**: Check for majority
4. **Use**: Proceed to next phase or declare chosen
5. **Expire**: Higher proposals override
6. **Archive**: Keep for debugging/audit

## Common Misconceptions

### Misconception 1: "Paxos is too complex for production"
**Reality**: Paxos is running in production at massive scale (Google, Microsoft, Amazon)

### Misconception 2: "Paxos requires synchronized clocks"
**Reality**: Paxos works in asynchronous networks, no clock sync needed

### Misconception 3: "Paxos is slow"
**Reality**: Multi-Paxos leader can commit in one round-trip

### Misconception 4: "Raft is simpler than Paxos"
**Reality**: Raft is a specific way of implementing Multi-Paxos with particular choices

## Implementing Paxos: Practical Tips

### 1. Start with Basic Paxos
- Implement single-value consensus first
- Test thoroughly with failure injection
- Verify safety properties hold

### 2. Add Multi-Paxos Carefully
- Leader election is critical
- Handle leader changes gracefully
- Implement catch-up for slow replicas

### 3. Optimize for Common Case
- Stable leader → Phase 2 only
- Batch multiple commands
- Pipeline for throughput

### 4. Test Extensively
```python
def test_paxos_safety():
    """No two different values chosen"""
    cluster = PaxosCluster(num_acceptors=5)

    # Concurrent proposers
    results = []
    threads = [
        Thread(target=lambda: results.append(
            cluster.propose(f"value_{i}")
        )) for i in range(10)
    ]

    # Run with random delays and failures
    with chaos_injection(cluster):
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # Check safety
    chosen = [r for r in results if r.is_chosen()]
    assert all(v.value == chosen[0].value for v in chosen)
```

## Performance Characteristics

### Latency
- **Best case** (stable leader): 1 RTT
- **Leader election**: 2 RTTs
- **Conflict resolution**: 2+ RTTs

### Throughput
- **Batching**: Amortize consensus cost
- **Pipelining**: Multiple in-flight proposals
- **Typical**: 10K-100K ops/sec per group

### Scalability
- **Acceptors**: Usually 3, 5, or 7
- **Proposers**: Any number (but coordination needed)
- **Learners**: Can scale independently

## Summary

Paxos is the foundational consensus protocol because:

1. **Provably safe**: Mathematical proof of correctness
2. **Optimal**: Cannot do better in async network
3. **Practical**: Powers production systems
4. **Flexible**: Many variants for different needs

The key insight—using promises to prevent conflicting decisions—appears in every consensus protocol since. Understanding Paxos deeply means understanding the fundamental nature of distributed agreement.

---

> "Paxos is either impossibly complex or impossibly simple, depending on whether you're trying to understand the implementation or the core idea."

Continue to [Raft →](raft.md)