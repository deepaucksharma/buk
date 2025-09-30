# Byzantine Consensus

## When Nodes Lie

> "Byzantine consensus is what you need when you can't trust your own servers—when failures aren't just crashes but active malice."

Byzantine consensus handles the hardest failure model: nodes that can lie, cheat, and actively try to break the system. Named after the Byzantine Generals Problem, these protocols ensure agreement even when some participants are malicious.

## The Byzantine Generals Problem

### The Original Formulation
Imagine Byzantine generals surrounding a city:
- Must coordinate attack or retreat
- Communicate via messengers
- Some generals are traitors
- Traitors can send different messages to different generals

**The Challenge**: Loyal generals must agree on a plan despite traitors.

### The Fundamental Result
**Theorem**: Byzantine consensus requires:
- **N ≥ 3F + 1** nodes to tolerate F Byzantine failures
- **Synchronous networks** for deterministic solutions
- **Cryptography** for efficient solutions

This is much more expensive than crash failures (which need only 2F + 1).

## Why Byzantine Fault Tolerance Matters

### Real-World Byzantine Failures
Byzantine failures aren't just theoretical:

1. **Hardware Corruption**: Bit flips, memory corruption
2. **Software Bugs**: Heisenbugs that manifest randomly
3. **Malicious Insiders**: Compromised nodes
4. **Network Attacks**: Message tampering
5. **Configuration Errors**: Inconsistent deployments

### Applications Requiring BFT
- **Blockchains**: Cryptocurrency networks
- **Critical Infrastructure**: Power grids, air traffic control
- **Military Systems**: Command and control
- **Financial Systems**: Trading platforms
- **Space Systems**: Satellite constellations

## PBFT: Practical Byzantine Fault Tolerance

### The Breakthrough
Miguel Castro and Barbara Liskov's PBFT (1999) made BFT practical:
- Works in asynchronous networks
- O(n²) message complexity
- Performs well in practice

### The Three-Phase Protocol

```python
class PBFTNode:
    def __init__(self, node_id, f):
        self.node_id = node_id
        self.f = f  # Number of failures to tolerate
        self.n = 3 * f + 1  # Total nodes
        self.view = 0  # Current view number
        self.is_primary = (self.view % self.n == self.node_id)
```

#### Phase 1: Pre-Prepare
Primary assigns sequence number and broadcasts:

```python
def pre_prepare(self, client_request):
    """Primary assigns sequence number"""
    if not self.is_primary:
        return

    sequence_num = self.get_next_sequence_number()
    digest = self.hash(client_request)

    message = PrePrepareMessage(
        view=self.view,
        sequence_num=sequence_num,
        digest=digest,
        request=client_request,
        signature=self.sign(digest)
    )

    # Log the pre-prepare
    self.log[sequence_num] = {
        'phase': 'pre-prepared',
        'message': message
    }

    # Broadcast to backups
    self.broadcast(message)
```

#### Phase 2: Prepare
Backups validate and broadcast prepare:

```python
def handle_pre_prepare(self, message):
    """Backup validates pre-prepare"""
    # Verify signature
    if not self.verify_signature(message):
        return

    # Check view and sequence number
    if message.view != self.view:
        return

    if self.already_accepted_different(message.sequence_num, message.digest):
        # Byzantine primary!
        self.trigger_view_change()
        return

    # Accept the pre-prepare
    self.log[message.sequence_num] = {
        'phase': 'pre-prepared',
        'message': message
    }

    # Broadcast prepare
    prepare_msg = PrepareMessage(
        view=self.view,
        sequence_num=message.sequence_num,
        digest=message.digest,
        node_id=self.node_id,
        signature=self.sign(message.digest)
    )

    self.broadcast(prepare_msg)
    self.prepare_votes[message.sequence_num] = [self.node_id]
```

#### Phase 3: Commit
After 2F prepare messages, broadcast commit:

```python
def handle_prepare(self, message):
    """Collect prepares and move to commit"""
    if not self.verify_signature(message):
        return

    # Add to prepare votes
    self.prepare_votes[message.sequence_num].append(message.node_id)

    # Check if we have 2F + 1 prepares (including our own)
    if len(self.prepare_votes[message.sequence_num]) >= 2 * self.f + 1:
        if self.log[message.sequence_num]['phase'] == 'pre-prepared':
            # Move to prepared state
            self.log[message.sequence_num]['phase'] = 'prepared'

            # Broadcast commit
            commit_msg = CommitMessage(
                view=self.view,
                sequence_num=message.sequence_num,
                digest=message.digest,
                node_id=self.node_id,
                signature=self.sign(message.digest)
            )

            self.broadcast(commit_msg)
            self.commit_votes[message.sequence_num] = [self.node_id]
```

#### Execution
After 2F + 1 commits, execute:

```python
def handle_commit(self, message):
    """Collect commits and execute"""
    if not self.verify_signature(message):
        return

    self.commit_votes[message.sequence_num].append(message.node_id)

    if len(self.commit_votes[message.sequence_num]) >= 2 * self.f + 1:
        if self.log[message.sequence_num]['phase'] == 'prepared':
            # Committed!
            self.log[message.sequence_num]['phase'] = 'committed'

            # Execute in sequence order
            self.execute_committed_requests()
```

### View Changes
When primary is faulty, initiate view change:

```python
def trigger_view_change(self):
    """Start view change when primary is faulty"""
    self.view += 1
    new_primary = self.view % self.n

    view_change_msg = ViewChangeMessage(
        new_view=self.view,
        last_stable_checkpoint=self.last_checkpoint,
        prepared_messages=self.get_prepared_messages(),
        node_id=self.node_id,
        signature=self.sign(...)
    )

    self.send_to(new_primary, view_change_msg)
```

## Modern Byzantine Consensus

### HotStuff: Linear Complexity
HotStuff (2019) achieves O(n) complexity:

```python
class HotStuffNode:
    def __init__(self):
        self.threshold_signatures = ThresholdSignatureScheme()

    def collect_votes(self, messages):
        """Aggregate signatures for O(n) complexity"""
        # Instead of storing n signatures
        signatures = [msg.signature for msg in messages]

        # Create one threshold signature
        combined = self.threshold_signatures.combine(signatures)

        # Now only need to send one signature
        return combined
```

Key innovations:
- **Threshold signatures**: Combine multiple signatures into one
- **Linear view change**: O(n) instead of O(n²)
- **Pipelined phases**: Overlap phases for throughput

### Tendermint: Blockchain Consensus
Used by Cosmos blockchain:

```python
class TendermintNode:
    def consensus_round(self, height, round):
        """Tendermint consensus for block height"""
        # Propose
        if self.is_proposer(height, round):
            block = self.create_block()
            self.broadcast_proposal(block)

        # Prevote
        if self.valid_proposal(block):
            self.broadcast_prevote(block.hash)
        else:
            self.broadcast_prevote(nil)

        # Wait for 2/3+ prevotes
        if self.has_supermajority_prevotes(block.hash):
            self.broadcast_precommit(block.hash)
        else:
            self.broadcast_precommit(nil)

        # Wait for 2/3+ precommits
        if self.has_supermajority_precommits(block.hash):
            self.commit_block(block)
            return block

        # Otherwise, move to next round
        return self.consensus_round(height, round + 1)
```

### LibraBFT/DiemBFT: Optimized HotStuff
Facebook's (now Diem) improvements:

```python
class DiemBFT:
    def __init__(self):
        self.reputation_system = ReputationSystem()
        self.leader_rotation = PacemakerProtocol()

    def select_leader(self):
        """Reputation-based leader selection"""
        # Leaders chosen based on past performance
        scores = self.reputation_system.get_scores()
        return self.weighted_selection(scores)

    def vote(self, proposal):
        """Vote with commit rule"""
        # 3-chain commit rule
        if self.is_third_in_chain(proposal):
            # Can commit the first in chain
            self.commit(self.get_first_in_chain(proposal))

        return self.sign_vote(proposal)
```

## Byzantine Failure Detection

### The Challenge
Cannot definitively detect Byzantine nodes, but can detect Byzantine behavior:

```python
class ByzantineDetector:
    def __init__(self):
        self.equivocation_evidence = {}
        self.invalid_message_evidence = {}
        self.timeout_evidence = {}

    def check_equivocation(self, msg1, msg2):
        """Detect node sending conflicting messages"""
        if (msg1.sender == msg2.sender and
            msg1.sequence == msg2.sequence and
            msg1.content != msg2.content):

            # Byzantine behavior detected!
            self.equivocation_evidence[msg1.sender] = (msg1, msg2)
            return True
        return False

    def verify_message(self, message):
        """Check message validity"""
        checks = [
            self.verify_signature(message),
            self.verify_format(message),
            self.verify_semantics(message),
            self.verify_freshness(message)
        ]
        return all(checks)
```

### Evidence of Byzantine Behavior

```python
class ByzantineEvidence:
    def __init__(self):
        self.types = {
            'equivocation': [],      # Conflicting messages
            'invalid_signature': [],  # Forged signatures
            'protocol_violation': [], # Wrong message order
            'censorship': [],        # Withholding messages
            'flooding': []           # DoS attempts
        }

    def create_proof(self, byzantine_node):
        """Create cryptographic proof of Byzantine behavior"""
        proof = {
            'node': byzantine_node,
            'evidence': self.types,
            'timestamp': time.time(),
            'witnesses': self.get_witnesses()
        }
        return self.sign(proof)
```

## Performance Characteristics

### Message Complexity

| Protocol | Normal Case | View Change | Cryptography |
|----------|------------|-------------|--------------|
| PBFT | O(n²) | O(n²) | RSA signatures |
| HotStuff | O(n) | O(n) | Threshold sigs |
| Tendermint | O(n²) | O(n²) | Ed25519 |
| DiemBFT | O(n) | O(n) | BLS signatures |

### Latency Comparison

```python
def benchmark_byzantine_protocols():
    """Compare different BFT protocols"""
    results = {
        'PBFT': {
            'latency_ms': 100,
            'throughput_tps': 10000,
            'nodes': 4
        },
        'HotStuff': {
            'latency_ms': 200,
            'throughput_tps': 50000,
            'nodes': 100
        },
        'Tendermint': {
            'latency_ms': 1000,
            'throughput_tps': 1000,
            'nodes': 100
        }
    }
    return results
```

## Optimizations

### Speculation
Execute optimistically before full agreement:

```python
def speculative_execution(self, request):
    """Execute speculatively, roll back if needed"""
    # Execute immediately
    checkpoint = self.state_machine.checkpoint()
    result = self.state_machine.execute(request)

    # Send result to client optimistically
    self.send_to_client(result, speculative=True)

    # Wait for consensus
    if self.wait_for_consensus(request):
        # Confirmed, make permanent
        self.state_machine.commit()
        self.send_to_client(result, speculative=False)
    else:
        # Rollback
        self.state_machine.restore(checkpoint)
        self.send_to_client(error="Speculation failed")
```

### Batching
Amortize consensus cost:

```python
def batch_consensus(self):
    """Batch multiple requests"""
    batch = []
    deadline = time.time() + 0.01  # 10ms

    while time.time() < deadline and len(batch) < 1000:
        if request := self.request_queue.get_nowait():
            batch.append(request)

    if batch:
        # Single consensus for entire batch
        self.run_consensus(batch)
```

### Separating Agreement from Execution
```python
class SeparatedBFT:
    def __init__(self):
        self.agreement_nodes = []  # Only do consensus
        self.execution_nodes = []  # Only execute

    def process_request(self, request):
        # Agreement cluster orders request
        order = self.agreement_nodes.agree_on_order(request)

        # Execution nodes process in agreed order
        result = self.execution_nodes.execute_at(order, request)

        return result
```

## Byzantine Consensus in Blockchains

### Proof of Work vs BFT
```python
class ConsensusComparison:
    def compare(self):
        pow = {
            'finality': 'probabilistic',
            'latency': 'minutes',
            'throughput': '7 tps',
            'energy': 'very high',
            'network': 'open'
        }

        bft = {
            'finality': 'immediate',
            'latency': 'seconds',
            'throughput': '1000+ tps',
            'energy': 'low',
            'network': 'permissioned'
        }
        return pow, bft
```

### Hybrid Approaches
Combining PoW/PoS with BFT:

```python
class HybridConsensus:
    def __init__(self):
        self.pow_chain = ProofOfWorkChain()
        self.bft_finality = BFTFinalityGadget()

    def finalize_blocks(self):
        """Use BFT to finalize PoW blocks"""
        # PoW produces blocks
        blocks = self.pow_chain.get_recent_blocks()

        # BFT finalizes them
        for block in blocks:
            if self.bft_finality.vote(block):
                block.finalized = True
```

## Common Pitfalls

### Pitfall 1: Underestimating Message Complexity
**Problem**: O(n²) becomes prohibitive at scale
**Solution**: Use threshold signatures, aggregate messages

### Pitfall 2: Assuming Synchrony
**Problem**: Network delays break safety
**Solution**: Design for asynchrony, use timeouts carefully

### Pitfall 3: Weak Cryptography
**Problem**: Broken signatures compromise everything
**Solution**: Use proven libraries, rotate keys

### Pitfall 4: Missing Equivocation Detection
**Problem**: Byzantine nodes send conflicting messages
**Solution**: Detect and punish equivocation

## Testing Byzantine Systems

```python
class ByzantineTest:
    def test_byzantine_agreement(self):
        """Test with Byzantine nodes"""
        cluster = BFTCluster(n=7)  # 3f+1 with f=2

        # Make some nodes Byzantine
        cluster.make_byzantine([2, 4], behavior='equivocate')

        # Run consensus
        results = cluster.run_consensus("value")

        # Check agreement despite Byzantine nodes
        honest_results = [r for i, r in enumerate(results)
                         if i not in [2, 4]]

        assert all(r == honest_results[0] for r in honest_results)
```

## Summary

Byzantine consensus solves the hardest problem in distributed systems:

**The Challenge**: Agreement despite malicious participants
**The Cost**: 3F+1 nodes, O(n²) messages, cryptography
**The Reward**: Tolerance of arbitrary failures

Key insights:
1. **Byzantine failures are real** - bugs and attacks happen
2. **Cost is high** - 3x nodes, quadratic messages
3. **Optimizations help** - threshold signatures, speculation
4. **Blockchains need BFT** - fundamental requirement
5. **Testing is critical** - Byzantine behaviors are subtle

Byzantine consensus shows that even with malicious actors, agreement is possible—at a price.

---

> "Byzantine consensus is like democracy—expensive, slow, but resistant to tyranny."

Continue to [Modern Variants →](modern-variants.md)