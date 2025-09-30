# Raft: Understandable Consensus

## Consensus for Humans

> "Raft is what you get when you design a consensus protocol for understandability first, performance second."

Raft, introduced by Diego Ongaro and John Ousterhout in 2014, revolutionized consensus by prioritizing human understanding. Where Paxos feels like solving a puzzle, Raft feels like following a recipe.

## The Design Philosophy

### Understandability as a Primary Goal
Raft's authors made radical decisions:
- **Decomposition**: Separate concerns completely
- **State space reduction**: Minimize possible states
- **Coherency**: Information flows in one direction
- **Intuitive**: Match human intuition about leadership

### The Three Sub-Problems
Raft decomposes consensus into three independent problems:
1. **Leader election**: Choose one leader
2. **Log replication**: Leader replicates log
3. **Safety**: Ensure consistency across failures

This separation makes each piece independently understandable.

## Core Concepts

### Terms: Logical Time
```python
class Term:
    """Terms act as logical clocks in Raft"""
    def __init__(self, number=0):
        self.number = number

    def increment(self):
        self.number += 1
        return self.number

    def __gt__(self, other):
        return self.number > other.number

    def __eq__(self, other):
        return self.number == other.number
```

Terms divide time into epochs:
- Each term has at most one leader
- Terms increase monotonically
- Servers always use latest term they've seen

### Server States
```python
class ServerState(Enum):
    FOLLOWER = "follower"      # Normal state
    CANDIDATE = "candidate"     # Trying to become leader
    LEADER = "leader"          # Coordinating replication
```

The state transitions are simple:
```
Follower → (timeout) → Candidate → (win election) → Leader
   ↑                        ↓              ↓
   ←←←←← (higher term) ←←←←←←←←← (higher term)
```

### The Log
```python
class LogEntry:
    def __init__(self, term, index, command):
        self.term = term        # Term when entry was created
        self.index = index      # Position in log
        self.command = command  # State machine command

class RaftLog:
    def __init__(self):
        self.entries = []
        self.commit_index = 0  # Highest committed entry
        self.last_applied = 0  # Highest applied to state machine

    def append(self, entry):
        self.entries.append(entry)

    def get_last_log_index(self):
        return len(self.entries)

    def get_last_log_term(self):
        if self.entries:
            return self.entries[-1].term
        return 0
```

## Leader Election

### The Algorithm
```python
class RaftNode:
    def __init__(self, id, peers):
        self.id = id
        self.peers = peers
        self.state = ServerState.FOLLOWER
        self.current_term = Term(0)
        self.voted_for = None
        self.election_timeout = self.random_timeout()

    def random_timeout(self):
        """Random timeout prevents split votes"""
        return random.uniform(150, 300)  # milliseconds

    def become_candidate(self):
        """Start election when timeout expires"""
        self.state = ServerState.CANDIDATE
        self.current_term.increment()
        self.voted_for = self.id
        self.reset_election_timeout()

        # Vote for self
        votes = 1

        # Request votes from others
        for peer in self.peers:
            vote = self.request_vote(peer)
            if vote.granted:
                votes += 1

            if votes > len(self.peers) / 2:
                self.become_leader()
                return

        # Didn't win, return to follower
        self.become_follower()
```

### RequestVote RPC
```python
def request_vote(self, peer):
    """Request vote from peer"""
    request = RequestVoteRequest(
        term=self.current_term,
        candidate_id=self.id,
        last_log_index=self.log.get_last_log_index(),
        last_log_term=self.log.get_last_log_term()
    )
    return peer.handle_request_vote(request)

def handle_request_vote(self, request):
    """Decide whether to grant vote"""
    # Update term if necessary
    if request.term > self.current_term:
        self.current_term = request.term
        self.become_follower()
        self.voted_for = None

    # Grant vote if:
    # 1. Haven't voted or voted for same candidate
    # 2. Candidate's log is at least as up-to-date
    if request.term < self.current_term:
        return RequestVoteResponse(
            term=self.current_term,
            vote_granted=False
        )

    if (self.voted_for is None or self.voted_for == request.candidate_id):
        if self.is_log_up_to_date(request.last_log_index, request.last_log_term):
            self.voted_for = request.candidate_id
            self.reset_election_timeout()
            return RequestVoteResponse(
                term=self.current_term,
                vote_granted=True
            )

    return RequestVoteResponse(
        term=self.current_term,
        vote_granted=False
    )
```

### Election Safety
The **Election Restriction** ensures safety:
- Voters only vote for candidates with logs at least as up-to-date
- "Up-to-date" = higher term, or same term but longer log
- This guarantees the leader has all committed entries

## Log Replication

### AppendEntries RPC
The leader sends AppendEntries to replicate log entries:

```python
def append_entries(self, follower):
    """Leader replicates entries to follower"""
    # Find next entry to send
    next_index = self.next_index[follower.id]
    prev_index = next_index - 1
    prev_term = self.log.get_term_at(prev_index) if prev_index > 0 else 0

    # Send entries starting from next_index
    entries = self.log.get_entries_from(next_index)

    request = AppendEntriesRequest(
        term=self.current_term,
        leader_id=self.id,
        prev_log_index=prev_index,
        prev_log_term=prev_term,
        entries=entries,
        leader_commit=self.commit_index
    )

    response = follower.handle_append_entries(request)

    if response.success:
        # Update follower's match index
        self.match_index[follower.id] = prev_index + len(entries)
        self.next_index[follower.id] = self.match_index[follower.id] + 1
        self.update_commit_index()
    else:
        # Log inconsistency, backup
        self.next_index[follower.id] = max(1, self.next_index[follower.id] - 1)
```

### Handling AppendEntries
```python
def handle_append_entries(self, request):
    """Follower handles replication"""
    # Check term
    if request.term < self.current_term:
        return AppendEntriesResponse(
            term=self.current_term,
            success=False
        )

    # Recognize leader
    if request.term >= self.current_term:
        self.current_term = request.term
        self.become_follower()
        self.reset_election_timeout()

    # Check log consistency
    if request.prev_log_index > 0:
        if len(self.log.entries) < request.prev_log_index:
            # Don't have prev entry
            return AppendEntriesResponse(
                term=self.current_term,
                success=False
            )

        if self.log.get_term_at(request.prev_log_index) != request.prev_log_term:
            # Prev entry doesn't match
            # Delete conflicting entries and all that follow
            self.log.truncate(request.prev_log_index)
            return AppendEntriesResponse(
                term=self.current_term,
                success=False
            )

    # Append new entries
    self.log.append_entries(request.entries)

    # Update commit index
    if request.leader_commit > self.commit_index:
        self.commit_index = min(
            request.leader_commit,
            self.log.get_last_log_index()
        )

    return AppendEntriesResponse(
        term=self.current_term,
        success=True
    )
```

### Commitment
The leader commits an entry when it's replicated on a majority:

```python
def update_commit_index(self):
    """Leader updates commit index"""
    # Find highest index replicated on majority
    for n in range(self.commit_index + 1, self.log.get_last_log_index() + 1):
        if self.log.get_term_at(n) == self.current_term:
            replicas = 1  # Leader has it
            for follower_id in self.match_index:
                if self.match_index[follower_id] >= n:
                    replicas += 1

            if replicas > len(self.peers) / 2:
                self.commit_index = n
```

## Safety Properties

### The Log Matching Property
If two logs contain an entry with the same index and term:
- They are identical in all entries up through that index
- The logs are identical in all preceding entries

This is maintained by:
- AppendEntries consistency check
- Followers deleting conflicting entries

### Leader Completeness
If an entry is committed in a given term, it will be present in the logs of all future leaders.

This is ensured by:
- Election restriction (candidates need up-to-date logs)
- Commitment rules (only commit from current term)

### State Machine Safety
If a server has applied a log entry at a given index to its state machine, no other server will ever apply a different log entry for the same index.

## Cluster Membership Changes

### The Problem
Changing membership (adding/removing servers) is tricky:
- Can't atomically update all servers
- During transition, could elect two leaders

### Joint Consensus Solution
Raft uses a two-phase approach:
1. Transition to joint configuration (C_old,new)
2. Transition to new configuration (C_new)

```python
class MembershipChange:
    def change_membership(self, new_members):
        """Two-phase membership change"""
        # Phase 1: Joint consensus
        joint_config = self.current_config.union(new_members)
        self.log.append(ConfigEntry(joint_config, joint=True))

        # Wait for commitment
        self.wait_for_commit()

        # Phase 2: New configuration
        self.log.append(ConfigEntry(new_members, joint=False))

        # Wait for commitment
        self.wait_for_commit()

        # Old servers can shut down
        if self.id not in new_members:
            self.shutdown()
```

## Optimizations

### Pre-Vote
Prevent disruption from isolated nodes:
```python
def pre_vote(self):
    """Check if election would succeed before incrementing term"""
    votes = 0
    for peer in self.peers:
        if peer.would_vote_for(self):
            votes += 1

    if votes > len(self.peers) / 2:
        # Would win, proceed with real election
        self.become_candidate()
```

### Leader Leases
Reduce read latency with time-based leases:
```python
class LeaderLease:
    def __init__(self, duration=150):  # ms
        self.duration = duration
        self.expiry = None

    def renew(self):
        """Renew lease after successful heartbeat"""
        self.expiry = time.time() + self.duration

    def is_valid(self):
        return time.time() < self.expiry if self.expiry else False

    def read_locally(self):
        """Safe to read without consensus if lease valid"""
        if self.is_valid():
            return self.state_machine.read()
        else:
            # Must use consensus
            return self.read_through_consensus()
```

### Batching and Pipelining
```python
def replicate_batch(self):
    """Batch multiple commands for efficiency"""
    batch = []
    deadline = time.time() + 0.01  # 10ms batching window

    while time.time() < deadline and len(batch) < 100:
        if cmd := self.command_queue.get_nowait():
            batch.append(cmd)

    if batch:
        entry = LogEntry(
            term=self.current_term,
            index=self.log.get_next_index(),
            commands=batch
        )
        self.log.append(entry)
        self.replicate_to_followers()
```

## Production Considerations

### Deployment Patterns
```yaml
# Typical 5-node deployment
nodes:
  - node1: {region: us-west, zone: a}
  - node2: {region: us-west, zone: b}
  - node3: {region: us-east, zone: a}
  - node4: {region: us-east, zone: b}
  - node5: {region: us-central, zone: a}

# Ensures:
# - Survives 2 node failures
# - Survives 1 region failure
# - Good geographic distribution
```

### Monitoring Metrics
```python
class RaftMetrics:
    def __init__(self):
        self.election_count = 0
        self.election_timeout_count = 0
        self.commit_latency_ms = []
        self.replication_lag = {}
        self.log_size = 0
        self.snapshot_count = 0

    def record_election(self, duration_ms):
        self.election_count += 1
        prometheus.histogram('raft_election_duration_ms', duration_ms)

    def record_commit(self, latency_ms):
        self.commit_latency_ms.append(latency_ms)
        prometheus.histogram('raft_commit_latency_ms', latency_ms)
```

### Common Issues and Solutions

#### Issue 1: Frequent Elections
**Symptoms**: Leader changes every few seconds
**Causes**: Network issues, overloaded leader
**Solutions**:
- Increase election timeout
- Add jitter to timeout
- Implement pre-vote

#### Issue 2: Slow Commits
**Symptoms**: High latency for writes
**Causes**: Slow followers, network latency
**Solutions**:
- Use leader leases for reads
- Batch commands
- Pipeline replication

#### Issue 3: Log Growth
**Symptoms**: Unbounded memory/disk usage
**Solutions**:
```python
def snapshot(self):
    """Create snapshot and truncate log"""
    if self.log.size() > self.snapshot_threshold:
        snapshot = Snapshot(
            last_included_index=self.commit_index,
            last_included_term=self.log.get_term_at(self.commit_index),
            state=self.state_machine.serialize()
        )
        self.save_snapshot(snapshot)
        self.log.truncate_before(self.commit_index)
```

## Raft vs Paxos

### Similarities
Both protocols:
- Solve consensus
- Use majority quorums
- Have leader-based optimizations
- Are proven safe

### Key Differences

| Aspect | Raft | Paxos |
|--------|------|-------|
| Design Goal | Understandability | Minimality |
| Decomposition | 3 sub-problems | Single protocol |
| Leader | Always has leader | Leader optional |
| Log Entries | Committed in order | Can have gaps |
| Membership | Joint consensus | No standard approach |
| Learning Curve | Hours | Days/Weeks |

## Implementation Tips

### 1. Start Simple
```python
# Begin with leader election only
def minimal_raft():
    node = RaftNode()
    node.implement_elections()
    node.test_elections()
    # Then add log replication
    # Then add snapshots
    # Then add membership changes
```

### 2. Test Thoroughly
```python
def test_safety():
    """Test with systematic failure injection"""
    cluster = RaftCluster(nodes=5)

    # Inject various failures
    scenarios = [
        NetworkPartition(nodes=[0,1], duration=1000),
        NodeCrash(node=2, at_time=500),
        PacketLoss(rate=0.1),
        PacketDelay(mean=50, stddev=20)
    ]

    for scenario in scenarios:
        cluster.reset()
        scenario.apply(cluster)
        cluster.run_workload()
        assert cluster.check_safety_properties()
```

### 3. Debug with Visualization
```python
def visualize_cluster_state(cluster):
    """Generate visual representation of Raft state"""
    for node in cluster.nodes:
        print(f"Node {node.id}: {node.state} Term={node.current_term}")
        print(f"  Log: {node.log.summary()}")
        print(f"  Commit: {node.commit_index}")
        if node.state == ServerState.LEADER:
            print(f"  NextIndex: {node.next_index}")
            print(f"  MatchIndex: {node.match_index}")
```

## Summary

Raft achieves its goal of understandable consensus through:

1. **Clean separation**: Three independent sub-problems
2. **Reduced states**: Fewer possible configurations
3. **Strong leader**: Simplifies reasoning
4. **Intuitive design**: Matches human thinking

The result is a protocol that's both:
- **Provably correct**: Same safety as Paxos
- **Practically usable**: Implemented in hours, not weeks

Raft has become the default choice for new systems requiring consensus, from etcd to CockroachDB to Consul.

---

> "In Raft, the leader does all the thinking so followers don't have to."

Continue to [Byzantine Consensus →](byzantine.md)