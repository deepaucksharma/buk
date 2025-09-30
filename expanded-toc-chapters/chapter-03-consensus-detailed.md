# Chapter 3: Consensus - The Heart of Distributed Systems
## Exhaustive Detailed Table of Contents

### Chapter Blueprint
```
INVARIANT FOCUS
Primary: UNIQUENESS (at most one decision per instance)
Supporting: AGREEMENT (all correct nodes decide same), VALIDITY (decision was proposed)

UNCERTAINTY ADDRESSED
Cannot know: Who is leader, message delivery time, crash vs slow
Cost to know: Multiple round-trips, quorum coordination, leader election
Acceptable doubt: Temporary disagreement during reconfiguration

EVIDENCE GENERATED
Type(s): Quorum certificates, leader leases, commit proofs, view changes
Scope: Per-consensus instance   Lifetime: Until configuration change
Binding: Participant set   Transitivity: Non-transitive per instance
Revocation: View change, epoch increment

GUARANTEE VECTOR
Input G: ⟨Object, None, Fractured, EO, None, Unauth⟩
Output G: ⟨Global, Total, SI, Fresh(lease), Idem, Auth(cert)⟩
Upgrades: Quorum evidence → Total order
Downgrades: Partition → No progress (safety preserved)

MODE MATRIX
Floor: Never violate safety (no conflicting decisions)
Target: Consensus in 2 RTTs with stable leader
Degraded: Leader election, higher latency
Recovery: Establish new leader, replay uncommitted

DUALITIES
Safety/Liveness: Always choose safety
Local/Global: Local decisions require global coordination
Determinism/Adaptivity: Deterministic safety, adaptive performance

IRREDUCIBLE SENTENCE
"Consensus transforms distributed uncertainty into certified agreement through
quorum-based evidence that survives failures and preserves uniqueness."
```

---

## Part 3.1: Paxos - The Foundation (1998)

### 3.1.1 Basic Paxos Protocol
#### 3.1.1.1 The Two-Phase Structure
- **Phase 1: Prepare (Leader Election)**
  ```python
  class PaxosProposer:
      def prepare(self, proposal_number):
          """
          Phase 1a: Send prepare requests
          Establishes leadership for proposal number
          """
          self.n = proposal_number
          self.promises = []

          prepare_msg = {
              'type': 'PREPARE',
              'proposal_number': self.n,
              'proposer': self.node_id,
              'evidence': 'prepare_request'
          }

          # Send to majority quorum
          for acceptor in self.acceptors:
              response = acceptor.handle_prepare(prepare_msg)
              if response['promise']:
                  self.promises.append(response)

          # Check if we have quorum
          if len(self.promises) > len(self.acceptors) / 2:
              return self.phase1_success()
          else:
              return self.phase1_failure()

      def phase1_success(self):
          """Process promises, find highest accepted value"""
          highest_accepted = None
          for promise in self.promises:
              if promise.get('accepted_proposal'):
                  if not highest_accepted or \
                     promise['accepted_proposal']['n'] > highest_accepted['n']:
                      highest_accepted = promise['accepted_proposal']

          return {
              'status': 'success',
              'value': highest_accepted['value'] if highest_accepted else None,
              'evidence': 'quorum_promises',
              'guarantee': 'leadership_acquired'
          }
  ```
  - Evidence: Promise responses from majority
  - Invariant: UNIQUENESS via proposal numbers

#### 3.1.1.2 Phase 2: Accept (Value Agreement)
- **Phase 2a: Propose Value**
  ```python
  def accept(self, value):
      """
      Phase 2a: Send accept requests
      Attempts to get value accepted
      """
      if value is None:
          value = self.choose_value()  # Free to choose

      accept_msg = {
          'type': 'ACCEPT',
          'proposal_number': self.n,
          'value': value,
          'evidence': 'leader_certificate'
      }

      accepts = []
      for acceptor in self.acceptors:
          response = acceptor.handle_accept(accept_msg)
          if response['accepted']:
              accepts.append(response)

      # Check if value is chosen (majority accepted)
      if len(accepts) > len(self.acceptors) / 2:
          return {
              'status': 'chosen',
              'value': value,
              'evidence': 'quorum_accepts',
              'certificate': self.generate_commit_certificate(accepts)
          }
  ```
  - Evidence: Accept responses from majority
  - Guarantee: Value chosen immutably

#### 3.1.1.3 The Acceptor State Machine
- **Acceptor Persistent State**
  ```python
  class PaxosAcceptor:
      def __init__(self):
          # Persistent state (must survive crashes)
          self.promised_proposal = None  # Highest promised
          self.accepted_proposal = None  # Highest accepted

      def handle_prepare(self, msg):
          """Phase 1b: Promise or reject"""
          if self.promised_proposal and \
             msg['proposal_number'] <= self.promised_proposal:
              return {'promise': False, 'reason': 'old_proposal'}

          # Update promise
          self.promised_proposal = msg['proposal_number']

          return {
              'promise': True,
              'promised': self.promised_proposal,
              'accepted_proposal': self.accepted_proposal,
              'evidence': 'promise_certificate'
          }

      def handle_accept(self, msg):
          """Phase 2b: Accept or reject"""
          if self.promised_proposal and \
             msg['proposal_number'] < self.promised_proposal:
              return {'accepted': False, 'reason': 'promised_higher'}

          # Accept the value
          self.promised_proposal = msg['proposal_number']
          self.accepted_proposal = {
              'n': msg['proposal_number'],
              'value': msg['value']
          }

          return {
              'accepted': True,
              'proposal': self.accepted_proposal,
              'evidence': 'accept_certificate'
          }
  ```
  - Evidence: Persistent state across failures
  - Invariant: Never accept after promising higher

### 3.1.2 Multi-Paxos and Leadership
#### 3.1.2.1 The Leader Lease Optimization
- **Stable Leader for Multiple Instances**
  ```python
  class MultiPaxosLeader:
      def __init__(self):
          self.lease_expiry = 0
          self.instance_number = 0
          self.prepared_range = None

      def acquire_leadership(self, duration=5000):
          """
          Prepare for range of instances
          Amortizes Phase 1 cost
          """
          start_instance = self.instance_number
          end_instance = start_instance + 1000  # Prepare 1000 instances

          # Phase 1 for instance range
          prepare_msg = {
              'type': 'PREPARE_RANGE',
              'start': start_instance,
              'end': end_instance,
              'proposal_number': self.generate_proposal_number(),
              'lease_duration': duration
          }

          promises = self.collect_promises(prepare_msg)

          if self.has_quorum(promises):
              self.lease_expiry = time.time() + duration
              self.prepared_range = (start_instance, end_instance)
              return {
                  'status': 'leader',
                  'lease': duration,
                  'instances': self.prepared_range,
                  'evidence': 'leadership_lease'
              }
  ```
  - Evidence: Lease certificate with expiry
  - Optimization: Amortize Phase 1 overhead

#### 3.1.2.2 Log Replication via Paxos
- **Replicated State Machine**
  ```python
  class PaxosLog:
      def append(self, command):
          """Append command to replicated log"""
          if not self.am_leader():
              return self.forward_to_leader(command)

          # Assign log index
          index = self.next_index()

          # Run Paxos for this index
          if self.lease_valid():
              # Skip Phase 1 (already leader)
              result = self.phase2_only(index, command)
          else:
              # Full Paxos (need leadership)
              result = self.full_paxos(index, command)

          if result['status'] == 'chosen':
              self.commit_index = max(self.commit_index, index)
              return {
                  'index': index,
                  'status': 'committed',
                  'evidence': result['certificate']
              }
  ```
  - Evidence: Per-index consensus
  - Guarantee: Total order of commands

#### 3.1.2.3 Handling Leader Failures
- **Leader Change Protocol**
  - Detection: Heartbeat timeout
  - New leader: Highest proposal number
  - Recovery: Learn uncommitted values
  - Evidence: View change certificate
  - Mode: Degraded during election

### 3.1.3 Google's Paxos Implementation
#### 3.1.3.1 Chubby Lock Service
- **Paxos for Fault-Tolerant Locks**
  - 5-node Paxos groups
  - Master lease: 30 seconds
  - Session tokens for clients
  - Evidence: Lock ownership certificates
  - Production: Billions of ops/day

#### 3.1.3.2 Megastore's Paxos
- **Wide-Area Paxos**
  - Cross-datacenter replication
  - Witness replicas for quorum
  - Fast local reads
  - Evidence: Commit timestamps
  - Latency: 100-300ms cross-region

#### 3.1.3.3 Spanner's Paxos Groups
- **Paxos per Shard**
  - Millions of Paxos groups
  - Leader leases with TrueTime
  - Pipelined operations
  - Evidence: TrueTime-bounded leases
  - Scale: Planet-wide deployment

---

## Part 3.2: Raft - Understandable Consensus (2014)

### 3.2.1 Leader Election and Log Replication
#### 3.2.1.1 The Three States Model
- **Clear Role Separation**
  ```python
  class RaftNode:
      def __init__(self):
          self.state = 'FOLLOWER'
          self.current_term = 0
          self.voted_for = None
          self.log = []
          self.commit_index = 0

      def state_machine(self):
          """Raft state transitions"""
          while True:
              if self.state == 'FOLLOWER':
                  self.run_follower()
              elif self.state == 'CANDIDATE':
                  self.run_candidate()
              elif self.state == 'LEADER':
                  self.run_leader()

      def run_follower(self):
          """Follower: Respond to leader"""
          timeout = self.election_timeout()

          while time.time() < timeout:
              msg = self.receive_message(timeout)
              if msg and msg['term'] >= self.current_term:
                  self.reset_timeout()
                  self.handle_message(msg)

          # Timeout: Become candidate
          self.state = 'CANDIDATE'
  ```
  - Evidence: Term number monotonicity
  - Invariant: One leader per term

#### 3.2.1.2 Election Safety
- **Ensuring Single Leader**
  ```python
  def run_candidate(self):
      """Candidate: Try to become leader"""
      self.current_term += 1
      self.voted_for = self.node_id
      votes = 1  # Vote for self

      # Request votes
      request = {
          'type': 'REQUEST_VOTE',
          'term': self.current_term,
          'candidate': self.node_id,
          'last_log_index': len(self.log) - 1,
          'last_log_term': self.log[-1]['term'] if self.log else 0
      }

      for peer in self.peers:
          response = peer.request_vote(request)
          if response['vote_granted']:
              votes += 1

              if votes > len(self.peers) / 2:
                  self.state = 'LEADER'
                  self.send_heartbeats()
                  return {
                      'status': 'elected',
                      'term': self.current_term,
                      'evidence': 'majority_votes'
                  }

      # Split vote or lost: Back to follower
      self.state = 'FOLLOWER'
  ```
  - Evidence: Vote certificates
  - Guarantee: At most one leader per term

#### 3.2.1.3 Log Replication Protocol
- **Consistency via Leader Append**
  ```python
  def append_entries(self, entries):
      """Leader: Replicate log entries"""
      if self.state != 'LEADER':
          return {'error': 'not_leader'}

      # Append to own log
      for entry in entries:
          entry['term'] = self.current_term
          self.log.append(entry)

      # Replicate to followers
      for peer in self.peers:
          next_index = self.next_index[peer]

          request = {
              'type': 'APPEND_ENTRIES',
              'term': self.current_term,
              'leader': self.node_id,
              'prev_log_index': next_index - 1,
              'prev_log_term': self.log[next_index-1]['term'] if next_index > 0 else 0,
              'entries': self.log[next_index:],
              'commit_index': self.commit_index
          }

          response = peer.handle_append(request)

          if response['success']:
              self.match_index[peer] = len(self.log) - 1
              self.update_commit_index()
          else:
              # Decrement and retry
              self.next_index[peer] -= 1
  ```
  - Evidence: Log matching property
  - Invariant: Log consistency across replicas

### 3.2.2 Membership Changes
#### 3.2.2.1 Joint Consensus Approach
- **Two-Phase Configuration Change**
  ```python
  class RaftMembership:
      def change_configuration(self, new_config):
          """
          Safe configuration change via joint consensus
          C_old,new requires majorities from both
          """
          # Phase 1: Transition to joint config
          joint_config = {
              'type': 'CONFIG_JOINT',
              'old': self.current_config,
              'new': new_config,
              'timestamp': time.time()
          }

          # Replicate joint configuration
          self.append_entry(joint_config)

          # Wait for commitment with BOTH majorities
          def has_joint_majority(acks):
              old_majority = self.count_majority(acks, self.current_config)
              new_majority = self.count_majority(acks, new_config)
              return old_majority and new_majority

          if self.wait_for_commitment(has_joint_majority):
              # Phase 2: Transition to new config
              final_config = {
                  'type': 'CONFIG_NEW',
                  'members': new_config,
                  'timestamp': time.time()
              }

              self.append_entry(final_config)
              self.wait_for_commitment(lambda a: self.count_majority(a, new_config))

              return {
                  'status': 'reconfigured',
                  'config': new_config,
                  'evidence': 'joint_consensus'
              }
  ```
  - Evidence: Joint majority agreement
  - Guarantee: No two leaders in transition

#### 3.2.2.2 Single-Server Changes
- **Simplified for Common Case**
  - Add/remove one server at a time
  - No joint consensus needed
  - Majority shifts atomically
  - Evidence: Single configuration entry
  - Limitation: Can't change majority at once

#### 3.2.2.3 Learner and Witness Nodes
- **Non-Voting Participants**
  - Learners: Replicate without voting
  - Witnesses: Vote without storing log
  - Useful for geo-distribution
  - Evidence: Role certificates
  - Mode: Read scaling via learners

### 3.2.3 etcd and Consul Implementations
#### 3.2.3.1 etcd's Raft
- **Production-Hardened Implementation**
  ```go
  // etcd's optimizations
  type raftNode struct {
      // Pre-vote to reduce disruption
      preVote        bool

      // Pipeline for throughput
      maxInflight    int

      // Batching for efficiency
      maxBatchSize   int

      // Leader lease for read optimization
      leaseTimeout   time.Duration

      // Snapshot for log compaction
      snapshotIndex  uint64
  }
  ```
  - Evidence: Pre-vote prevents disruption
  - Production: Kubernetes control plane

#### 3.2.3.2 Consul's Enhanced Raft
- **HashiCorp's Extensions**
  - Autopilot: Automatic dead server cleanup
  - Network segments: WAN federation
  - Snapshot shipping: Fast catch-up
  - Evidence: Health certificates
  - Scale: Thousands of nodes

#### 3.2.3.3 Performance Optimizations
- **Making Raft Fast**
  - Batching: Amortize network cost
  - Pipelining: Multiple in-flight
  - Leader leases: Read without quorum
  - Evidence: Performance benchmarks
  - Throughput: 100K+ ops/sec

---

## Part 3.3: Modern Consensus Variants

### 3.3.1 EPaxos: Leaderless Consensus (2013)
#### 3.3.1.1 The Dependency Graph Approach
- **Commands Not Slots**
  ```python
  class EPaxosNode:
      def __init__(self):
          self.commands = {}  # cmd_id -> command
          self.dependencies = {}  # cmd_id -> set of dependencies

      def propose_command(self, cmd):
          """
          EPaxos: Establish dependencies then order
          """
          cmd_id = self.generate_id()

          # Phase 1: Pre-accept
          deps = self.compute_dependencies(cmd)

          pre_accept = {
              'type': 'PRE_ACCEPT',
              'cmd_id': cmd_id,
              'command': cmd,
              'deps': deps,
              'seq': self.next_seq()
          }

          responses = self.broadcast_pre_accept(pre_accept)

          # Fast path: If all agree on dependencies
          if self.all_agree_on_deps(responses):
              # Commit immediately (2 RTTs total)
              self.broadcast_commit(cmd_id, deps)
              return {
                  'status': 'committed_fast',
                  'latency': '1_rtt',
                  'evidence': 'unanimous_deps'
              }
          else:
              # Slow path: Run Paxos to agree on deps
              final_deps = self.paxos_accept(cmd_id, self.union_deps(responses))
              self.broadcast_commit(cmd_id, final_deps)
              return {
                  'status': 'committed_slow',
                  'latency': '2_rtt',
                  'evidence': 'paxos_deps'
              }
  ```
  - Evidence: Dependency certificates
  - Optimization: 1 RTT in common case

#### 3.3.1.2 Conflict Detection
- **Identifying Interfering Commands**
  ```python
  def compute_dependencies(self, cmd):
      """Find commands that conflict with cmd"""
      deps = set()

      for existing_id, existing_cmd in self.commands.items():
          if self.conflicts(cmd, existing_cmd):
              deps.add(existing_id)

      return deps

  def conflicts(self, cmd1, cmd2):
      """Check if commands conflict"""
      # Commands conflict if they:
      # 1. Access same key
      # 2. At least one writes
      keys1 = self.extract_keys(cmd1)
      keys2 = self.extract_keys(cmd2)

      if keys1.intersection(keys2):
          return cmd1['type'] == 'WRITE' or cmd2['type'] == 'WRITE'

      return False
  ```
  - Evidence: Conflict detection proofs
  - Guarantee: Serializability

#### 3.3.1.3 Execution and Recovery
- **Building Consistent Order**
  - Topological sort of dependency graph
  - Break cycles deterministically
  - Execute in derived order
  - Evidence: Execution certificates
  - Recovery: Rebuild graph from quorum

### 3.3.2 Flexible Paxos: Weakening Quorums (2016)
#### 3.3.2.1 The Quorum Intersection Theorem
- **Relaxing Majority Requirements**
  ```python
  class FlexiblePaxos:
      def __init__(self, n):
          self.n = n

      def valid_quorum_system(self, Q1, Q2):
          """
          Check if quorum system is valid
          Q1: Phase 1 quorums (leader election)
          Q2: Phase 2 quorums (replication)

          Requirement: Every Q1 intersects every Q2
          """
          for q1 in Q1:
              for q2 in Q2:
                  if not q1.intersection(q2):
                      return False
          return True

      def example_systems(self):
          """Valid quorum systems beyond simple majority"""
          # Simple majority
          majority = {
              'Q1': self.all_majorities(),
              'Q2': self.all_majorities()
          }

          # Fast reads: Small Q1, large Q2
          fast_read = {
              'Q1': self.all_sets_of_size(self.n),  # All nodes
              'Q2': self.all_sets_of_size(1)  # Any single node
          }

          # Grid quorum
          grid = {
              'Q1': self.all_rows(),  # Any row
              'Q2': self.all_columns()  # Any column
          }

          return [majority, fast_read, grid]
  ```
  - Evidence: Intersection proofs
  - Flexibility: Optimize for workload

#### 3.3.2.2 Practical Applications
- **Workload-Optimized Quorums**
  - Read-heavy: Large Q1, small Q2
  - Write-heavy: Small Q1, large Q2
  - Geo-distributed: Regional quorums
  - Evidence: Workload analysis
  - Trade-off: Availability vs latency

#### 3.3.2.3 FPaxos Implementation
- **Facebook's Usage**
  - Cross-region replication
  - Read quorum of 1 in region
  - Write quorum across regions
  - Evidence: Regional certificates
  - Performance: Sub-ms local reads

### 3.3.3 Per-Shard Consensus at Scale
#### 3.3.3.1 Micro-Sharding Architecture
- **Many Small Consensus Groups**
  ```python
  class ShardedConsensus:
      def __init__(self, num_shards=10000):
          self.shards = {}

          for shard_id in range(num_shards):
              self.shards[shard_id] = {
                  'consensus': RaftGroup(shard_id),
                  'key_range': self.compute_range(shard_id),
                  'replicas': self.assign_replicas(shard_id)
              }

      def route_request(self, key, operation):
          """Route to appropriate shard"""
          shard_id = self.hash_to_shard(key)
          shard = self.shards[shard_id]

          # Run consensus within shard
          result = shard['consensus'].propose(operation)

          return {
              'shard': shard_id,
              'result': result,
              'latency': result['latency'],
              'evidence': f'shard_{shard_id}_consensus'
          }
  ```
  - Evidence: Per-shard consensus proof
  - Scale: Millions of shards possible

#### 3.3.3.2 Cross-Shard Transactions
- **Coordinating Multiple Groups**
  - Two-phase commit across shards
  - Atomic commitment protocol
  - Deterministic locking order
  - Evidence: Cross-shard certificates
  - Challenge: Coordination overhead

#### 3.3.3.3 Performance Reality
- **Production Measurements**
  ```
  Single-shard operation:
  - P50: 1-2ms
  - P99: 5-10ms
  - Throughput: 10K ops/sec/shard

  Cross-shard transaction:
  - P50: 10-20ms
  - P99: 50-100ms
  - Throughput: 100 txn/sec
  ```
  - Evidence: Production metrics
  - **Correction**: Low single-digit milliseconds typical

---

## Part 3.4: Byzantine Fault Tolerance

### 3.4.1 Byzantine Generals Problem
#### 3.4.1.1 The Threat Model
- **Arbitrary Failures**
  ```python
  class ByzantineNode:
      """Node that can behave arbitrarily"""

      def malicious_behavior(self):
          """
          Byzantine nodes can:
          - Lie about their state
          - Send different messages to different nodes
          - Collude with other Byzantine nodes
          - Replay old messages
          - Stay silent selectively
          """
          behaviors = [
              self.send_conflicting_messages,
              self.replay_old_message,
              self.selective_silence,
              self.false_testimony,
              self.collusion_attack
          ]

          return random.choice(behaviors)
  ```
  - Evidence: Cryptographic signatures required
  - Assumption: At most f Byzantine among 3f+1

#### 3.4.1.2 The Impossibility Results
- **Lower Bounds**
  - Need 3f+1 nodes to tolerate f Byzantine
  - Need f+1 rounds in synchronous model
  - Impossible in asynchronous without randomization
  - Evidence: Mathematical proofs
  - **Correction**: O(n²) messages with signatures

#### 3.4.1.3 Authenticated vs Unauthenticated
- **Role of Digital Signatures**
  - Authenticated: Can detect lies
  - Unauthenticated: Cannot prove lying
  - Complexity reduction with signatures
  - Evidence: Signature chains
  - Trade-off: Crypto overhead vs messages

### 3.4.2 PBFT, Tendermint, HotStuff
#### 3.4.2.1 PBFT: Practical BFT (1999)
- **Three-Phase Protocol**
  ```python
  class PBFTNode:
      def process_request(self, request):
          """PBFT three-phase protocol"""

          # Phase 1: Pre-prepare (leader only)
          if self.is_leader():
              pre_prepare = {
                  'view': self.view,
                  'seq': self.next_seq(),
                  'digest': self.hash(request),
                  'signature': self.sign(...)
              }
              self.broadcast(pre_prepare)

          # Phase 2: Prepare (all nodes)
          if self.valid_pre_prepare(pre_prepare):
              prepare = {
                  'view': self.view,
                  'seq': pre_prepare['seq'],
                  'digest': pre_prepare['digest'],
                  'node': self.id,
                  'signature': self.sign(...)
              }
              self.broadcast(prepare)

          # Wait for 2f prepares
          if self.count_prepares() >= 2 * self.f:
              # Phase 3: Commit
              commit = {
                  'view': self.view,
                  'seq': pre_prepare['seq'],
                  'digest': pre_prepare['digest'],
                  'node': self.id,
                  'signature': self.sign(...)
              }
              self.broadcast(commit)

          # Wait for 2f+1 commits
          if self.count_commits() >= 2 * self.f + 1:
              self.execute(request)
              return {
                  'status': 'committed',
                  'evidence': 'commit_certificate',
                  'signatures': self.collect_signatures()
              }
  ```
  - Evidence: 2f+1 signatures per phase
  - Complexity: O(n²) messages

#### 3.4.2.2 Tendermint: Blockchain BFT
- **BFT for Cosmos**
  ```python
  class TendermintConsensus:
      def round(self, height, round_num):
          """
          Tendermint round structure
          """
          # Step 1: Propose
          if self.is_proposer(height, round_num):
              block = self.create_block()
              self.broadcast_proposal(block)

          # Step 2: Prevote
          if self.valid_proposal(block):
              self.broadcast_prevote(block.hash)
          else:
              self.broadcast_prevote(nil)

          # Step 3: Precommit
          if self.count_prevotes(block.hash) >= 2 * self.f + 1:
              self.locked_block = block
              self.broadcast_precommit(block.hash)

          # Step 4: Commit
          if self.count_precommits(block.hash) >= 2 * self.f + 1:
              self.commit_block(block)
              return {
                  'height': height,
                  'block': block,
                  'evidence': 'precommit_signatures'
              }

          # Timeout: Move to next round
          return self.round(height, round_num + 1)
  ```
  - Evidence: Prevote and precommit sets
  - Application: Blockchain consensus

#### 3.4.2.3 HotStuff: Linear BFT (2019)
- **Simplifying BFT**
  ```python
  class HotStuffNode:
      def process_phase(self, phase, proposal):
          """
          HotStuff: Linear message complexity
          All phases identical structure
          """
          # Vote on proposal
          vote = {
              'type': phase,  # PREPARE, PRECOMMIT, COMMIT
              'proposal': proposal,
              'signature': self.threshold_sign(proposal)
          }

          # Send to leader only (not broadcast)
          self.send_to_leader(vote)

          if self.is_leader():
              votes = self.collect_votes()

              if len(votes) >= 2 * self.f + 1:
                  # Combine into quorum certificate
                  qc = {
                      'phase': phase,
                      'proposal': proposal,
                      'signatures': self.threshold_combine(votes)
                  }

                  # Move to next phase
                  self.broadcast(qc)

                  if phase == 'COMMIT':
                      return {
                          'status': 'committed',
                          'evidence': qc,
                          'complexity': 'O(n)'  # Linear!
                      }
  ```
  - Evidence: Threshold signatures
  - Innovation: O(n) message complexity

### 3.4.3 Blockchain Consensus Mechanisms
#### 3.4.3.1 Proof of Work
- **Nakamoto Consensus**
  - Longest chain rule
  - Probabilistic finality
  - 51% attack threshold
  - Evidence: Proof of work
  - Energy cost: Immense

#### 3.4.3.2 Proof of Stake
- **Economic Security**
  - Stake-weighted voting
  - Slashing for misbehavior
  - Nothing-at-stake problem
  - Evidence: Stake bonds
  - Finality: Deterministic possible

#### 3.4.3.3 Hybrid Approaches
- **Combining Mechanisms**
  - PoW for randomness
  - BFT for finality
  - Checkpointing strategies
  - Evidence: Multiple types
  - Examples: Ethereum 2.0, Polkadot

---

## Part 3.5: Advanced Consensus Topics

### 3.5.1 Consensus with Weak Synchrony
#### 3.5.1.1 Eventually Synchronous Models
- **Between Async and Sync**
  - Unknown Global Stabilization Time
  - Bounded delay after GST
  - Safety always, liveness eventual
  - Evidence: Timeout certificates
  - Protocols: PBFT, HotStuff

#### 3.5.1.2 Partial Synchrony
- **Known Bounds, Unknown Validity**
  - Δ bound exists but unknown
  - Or bound known but holds eventually
  - Double timeout strategy
  - Evidence: Increasing timeouts
  - Guarantee: Eventually succeed

### 3.5.2 Fast Consensus Protocols
#### 3.5.2.1 Fast Paxos
- **Optimistic Fast Path**
  - 1.5 RTT in common case
  - Requires larger quorums
  - Collision recovery needed
  - Evidence: Fast quorum certificates
  - Trade-off: Speed vs quorum size

#### 3.5.2.2 Fast Byzantine Paxos
- **Byzantine Fast Path**
  - 2 RTT with Byzantine nodes
  - Requires 5f+1 nodes
  - Optimistic common case
  - Evidence: Larger certificate sets
  - Application: Low-latency BFT

### 3.5.3 Consensus for Machine Learning
#### 3.5.3.1 Parameter Server Consensus
- **Distributed Training**
  - Synchronous SGD needs agreement
  - Asynchronous has convergence issues
  - Bounded staleness compromise
  - Evidence: Gradient certificates
  - Scale: Thousands of workers

#### 3.5.3.2 Federated Learning Consensus
- **Privacy-Preserving ML**
  - Aggregate without seeing data
  - Byzantine-robust aggregation
  - Differential privacy integration
  - Evidence: Secure aggregation proofs
  - Challenge: Heterogeneous devices

---

## Part 3.6: Synthesis and Mental Models

### 3.6.1 The Three-Layer Model for Consensus
#### 3.6.1.1 Layer 1: Eternal Truths
- **What Cannot Be Changed**
  - FLP: No deterministic async consensus
  - Need majority intersection
  - f+1 rounds minimum
  - 3f+1 for Byzantine
  - Evidence has cost

#### 3.6.1.2 Layer 2: Design Patterns
- **How We Navigate**
  - Use leader for ordering
  - Majority quorums for agreement
  - Phases for safety
  - Timeouts for liveness
  - Signatures for Byzantine

#### 3.6.1.3 Layer 3: Implementations
- **What We Build**
  - Paxos/Raft for crash tolerance
  - PBFT/HotStuff for Byzantine
  - EPaxos for geo-distribution
  - Blockchain for open membership
  - Sharding for scale

### 3.6.2 Evidence Lifecycle in Consensus
#### 3.6.2.1 Generation
- **Creating Consensus Evidence**
  - Proposal certificates
  - Promise/vote responses
  - Quorum certificates
  - Commit proofs
  - Leader leases

#### 3.6.2.2 Validation
- **Checking Evidence**
  - Signature verification
  - Quorum counting
  - Term/view checking
  - Timeout validation
  - Certificate authentication

#### 3.6.2.3 Expiration
- **Evidence Lifetime**
  - Leader lease duration
  - View/term validity
  - Configuration epoch
  - Certificate timeout
  - Log truncation point

### 3.6.3 The Learning Spiral
#### 3.6.3.1 Pass 1: Intuition
- **Why Consensus Matters**
  - Need agreement despite failures
  - Distributed coordination required
  - State machine replication
  - Story: The first replicated database

#### 3.6.3.2 Pass 2: Understanding
- **The Complexity**
  - Multiple phases needed
  - Quorums must intersect
  - Leaders simplify but fail
  - Byzantine changes everything

#### 3.6.3.3 Pass 3: Mastery
- **Operating Consensus**
  - Choose right protocol
  - Tune for workload
  - Monitor health metrics
  - Debug with certificates

### 3.6.4 Consensus Guarantee Composition
#### 3.6.4.1 Typed Vectors for Consensus
- **Guarantee Components**
  ```
  G_consensus = ⟨Scope, Order, Visibility, Recency, Evidence_Type⟩

  Examples:
  - Paxos: ⟨Global, Total, SI, Fresh(lease), Quorum_Cert⟩
  - Raft: ⟨Global, Total, SI, Fresh(term), Majority_Vote⟩
  - PBFT: ⟨Global, Total, SI, Fresh(view), BFT_Cert⟩
  - EPaxos: ⟨Object, Partial, SI, Fresh(deps), Conflict_Cert⟩
  ```

#### 3.6.4.2 Mode Transitions
- **Consensus Modes**
  - Normal: Leader active, fast path
  - Election: Choosing new leader
  - Recovery: Rebuilding state
  - Reconfiguration: Membership change
  - Evidence drives transitions

---

## Exercises and Projects

### Conceptual Exercises
1. **Prove safety of Basic Paxos**
2. **Show why Byzantine needs 3f+1**
3. **Design quorum system for read-heavy workload**
4. **Analyze EPaxos dependency conflicts**

### Implementation Projects
1. **Build Raft from scratch**
   - Leader election
   - Log replication
   - Snapshot support
   - Membership changes

2. **Implement Multi-Paxos**
   - Basic Paxos first
   - Add leader lease
   - Log compaction
   - Performance optimization

3. **Create simple BFT**
   - Three-phase protocol
   - View changes
   - Signature verification
   - Byzantine testing

### Production Analysis
1. **Benchmark consensus protocols**
   - Latency vs throughput
   - Failure recovery time
   - Network partition behavior

2. **Analyze your system's consensus**
   - What protocol is used?
   - What are failure modes?
   - How does it scale?

---

## References and Further Reading

### Foundational Papers
- Lamport. "The Part-Time Parliament" (Paxos, 1998)
- Ongaro, Ousterhout. "In Search of an Understandable Consensus Algorithm" (Raft, 2014)
- Castro, Liskov. "Practical Byzantine Fault Tolerance" (1999)
- Moraru et al. "There Is More Consensus in Egalitarian Parliaments" (EPaxos, 2013)

### Modern Developments
- Yin et al. "HotStuff: BFT Consensus with Linearity and Responsiveness" (2019)
- Howard et al. "Flexible Paxos: Quorum Intersection Revisited" (2016)
- Nawab et al. "Dpaxos: Managing Data Closer to Users without Jeopardizing Correctness" (2018)

### Production Systems
- "The Chubby Lock Service for Loosely-Coupled Distributed Systems" (2006)
- "etcd: Distributed Reliable Key-value Store"
- "Consul by HashiCorp"
- "Amazon DynamoDB: A Scalable, Predictably Performant, and Fully Managed NoSQL Database Service"

### Books
- Lynch. "Distributed Algorithms"
- Cachin, Guerraoui, Rodrigues. "Introduction to Reliable and Secure Distributed Programming"
- Varela, Agha. "Programming Distributed Computing Systems"

---

## Chapter Summary

### The Irreducible Truth
**"Consensus transforms distributed uncertainty into certified agreement through quorum-based evidence that survives failures and preserves uniqueness—this is the fundamental mechanism that makes distributed systems possible."**

### Key Mental Models
1. **Quorums Create Truth**: Majority agreement becomes fact through intersection
2. **Phases Ensure Safety**: Multiple rounds prevent conflicting decisions
3. **Evidence Drives Progress**: Certificates, votes, and leases enable forward movement
4. **Leaders Optimize, Don't Require**: Leaderless possible but leader makes efficient
5. **Byzantine Changes Everything**: Signatures and larger quorums for arbitrary failures

### What's Next
Chapter 4 will explore replication—how we use consensus to maintain multiple copies of data, the different strategies for keeping replicas consistent, and the trade-offs between consistency, availability, and performance in replicated systems.