# Chapter 3: Consensus - The Heart of Distributed Systems

## Introduction: The Problem of Agreement

Three replicas of a database. A client wants to write "X=5". All three replicas must agree that X=5. Simple, right?

Not quite.

What if one replica crashes before receiving the write? What if the network partitions and the replicas can't communicate? What if two clients simultaneously try to write different values (X=5 and X=7)? What if messages arrive out of order? What if a replica is malicious and lies about its state?

**Consensus is the problem of getting distributed nodes to agree on a single value despite failures, delays, and uncertainty.**

It sounds simple. It is provably impossible in the general case (FLP, Chapter 1). Yet every distributed system that provides strong guarantees relies on consensus: databases need to agree on commit order, leader election needs to agree on who leads, configuration management needs to agree on current config, blockchain needs to agree on transaction history.

This chapter explores how distributed systems achieve consensus anyway—by adding assumptions, generating evidence through voting, and operating in explicit modes that degrade predictably when assumptions fail.

### Why Consensus Matters

Without consensus, distributed systems fall apart:

**Database without consensus**:
- Write goes to 3 replicas
- Replica 1 commits, Replica 2 fails, Replica 3 commits
- Later, Replica 2 recovers—does it have the write or not?
- Different replicas have different states (split-brain)
- Data loss, corruption, inconsistency

**Leader election without consensus**:
- Two nodes both think they're leader (both have expired lease from old leader)
- Both accept writes to the same key
- Conflicting writes, data corruption
- Split-brain scenario

**Configuration management without consensus**:
- Cluster needs to change config (add node, remove node)
- Some nodes see new config, some see old config
- Cluster is partitioned into incompatible groups
- Cannot make progress

**The pattern**: Without consensus, you get **divergence**—different nodes making independent, incompatible decisions.

### The Central Challenge

Consensus must satisfy three properties:

1. **Agreement**: All correct processes decide the same value
2. **Validity**: The decided value was proposed by some process
3. **Termination**: All correct processes eventually decide

Seems reasonable. But FLP (Chapter 1) proves: in an asynchronous system with even one crash failure, no deterministic protocol can guarantee all three simultaneously.

**The tension**: We need consensus, but it's impossible in the general case. The solution: add assumptions.

Every practical consensus protocol makes trade-offs:
- **Paxos/Raft**: Assume partial synchrony (bounded delays after unknown GST)
- **Byzantine consensus**: Tolerate malicious failures but need 3F+1 nodes for F failures
- **Deterministic protocols**: Give up termination guarantee (may never decide)
- **Randomized protocols**: Give up determinism (probabilistic termination)

### Real-World Consequences

**MongoDB primary election stall (2019)**:
- Network congestion caused heartbeat delays > timeout threshold
- Leader thought followers crashed, stepped down
- Followers thought leader crashed, started election
- Election took 47 seconds (protocol churn, split votes)
- During those 47 seconds: no writes accepted, 100% write unavailability
- Cost: $2.3M in lost transactions for one customer
- **This is FLP in production**: Cannot guarantee bounded-time consensus without synchrony assumptions

**etcd split-brain (2015)**:
- Network partition split 5-node cluster: 2 nodes | 3 nodes
- Partition lasted 90 seconds
- Both sides ran leader election
- Minority (2 nodes) couldn't elect leader (no quorum)
- Majority (3 nodes) elected new leader, continued serving
- Partition healed, minority rejoined, discovered conflicting state
- **Evidence-based view**: Majority had quorum evidence (3/5 votes), minority didn't. Safety preserved.

**ZooKeeper cascade failure (2014, Yahoo)**:
- One ZooKeeper node became slow (GC pauses, disk contention)
- Other nodes marked it as failed (timeout-based failure detection)
- Remaining nodes elected new leader
- Slow node recovered, thought it was still leader (stale lease)
- **Fencing prevented split-brain**: Epoch numbers ensured old leader's writes rejected
- But recovery took 40 minutes (all dependent services waiting on ZooKeeper)

### What This Chapter Covers

**Part 1: Intuition (First Pass)**
- The Parliament Problem (Lamport's motivation for Paxos)
- Why agreement is hard (no global view, partial failures)
- Real-world consensus use cases

**Part 2: Understanding (Second Pass)**
- **Paxos**: The foundational protocol (two-phase, quorum-based)
- **Raft**: Understandable consensus (leader election, log replication, safety)
- **Byzantine consensus**: PBFT, HotStuff (tolerating malicious failures)
- **Advanced topics**: Flexible Paxos, EPaxos, Consensus-as-a-Service

**Part 3: Mastery (Third Pass)**
- **Evidence framework**: Consensus as evidence generation (quorum certificates)
- **Invariant preservation**: UNIQUENESS (only one decision), AGREEMENT (all decide same)
- **Mode matrix**: Target (healthy), Degraded (some failures), Floor (safety-only), Recovery
- **Production patterns**: Monitoring, tuning, failure handling, case studies

### The Evidence-Based View

Reframe consensus through evidence:

**Consensus is the process of converting uncertain proposals into certain decisions by collecting sufficient evidence (votes) from a quorum of nodes.**

- **Proposal**: Uncertain claim ("I think X=5")
- **Votes**: Evidence from individual nodes ("I accept X=5")
- **Quorum**: Sufficient evidence to prove claim (majority votes)
- **Decision**: Certain fact ("X=5 is chosen, proven by quorum certificate")

**Evidence lifecycle**:
```
Generate (propose value) →
Collect (gather votes) →
Validate (check quorum) →
Active (decision made) →
Expire (epoch/term change) →
Renew (new consensus round)
```

**Evidence types in consensus**:
- **Promise certificates** (Paxos Phase 1): Proof that acceptors won't accept lower-numbered proposals
- **Accept certificates** (Paxos Phase 2): Proof that quorum accepted a value
- **Commit certificates**: Proof that value is chosen (learners notified)
- **Vote certificates** (Raft): Proof that candidate received quorum votes for leadership
- **Term numbers** (Raft): Epoch evidence preventing stale leaders
- **Signed certificates** (Byzantine): Cryptographic proof of vote authenticity

### The Conservation Principle

Throughout this chapter, observe **conservation of certainty**: You cannot create consensus from nothing—you need enough votes (evidence) from enough nodes (quorum) to prove the claim.

**Quorum intersection is the key**: Any two quorums must overlap, ensuring no two conflicting decisions can both have quorum certificates.

- Classic quorum: Majority (F+1 out of 2F+1 nodes)
- Byzantine quorum: 2F+1 out of 3F+1 nodes
- Flexible quorum: Phase 1 quorum Q₁ + Phase 2 quorum Q₂ such that Q₁ + Q₂ > N

**When evidence is insufficient** (no quorum), systems must:
- Refuse to decide (CP choice, maintain consistency)
- Or make local decision (AP choice, risk inconsistency)

The choice must be **explicit, principled, and safe**.

### Chapter Structure

We'll explore consensus in three passes:

**First pass (Intuition)**: Experience the problem through stories
- Distributed systems as parliaments making decisions
- The birthday reservation problem
- Real-world split-brain scenarios

**Second pass (Understanding)**: Build mental models of solutions
- Paxos (prepare, accept, learn phases)
- Raft (leader election, log replication, safety)
- Byzantine consensus (PBFT, HotStuff, modern protocols)

**Third pass (Mastery)**: Compose and operate consensus systems
- Evidence-based consensus framework
- Guarantee vectors for consensus operations
- Mode matrix for failure handling
- Production case studies (etcd, ZooKeeper, CockroachDB, Kafka)

Let's begin with the Parliament Problem—Lamport's story that gave birth to Paxos.

---

## Part 1: INTUITION (First Pass) — The Felt Need

### The Parliament Problem

In ancient Greece, the Paxon parliament must pass laws. The parliament has many legislators who communicate via messengers. But:

- **Legislators come and go**: Some are away, some are asleep, some are distracted
- **Messengers are unreliable**: Messages can be lost, delayed, or delivered out of order
- **No global coordination**: No single legislator knows the state of all others

Yet the parliament must agree on laws. How?

**Naive approach: Single legislator**
- One legislator proposes a law
- All others must accept it
- **Problem**: If that legislator is unavailable, parliament is stuck (single point of failure)

**Naive approach: Majority vote**
- Legislator proposes law, broadcasts to all
- Each legislator votes yes or no
- Majority wins
- **Problem**: What if messages are delayed? What if two legislators simultaneously propose different laws? What if some legislators never respond?

**The key insight**: A law is passed when a majority of legislators have agreed, and this fact can be proven (via quorum of votes). Even if some legislators are unavailable, the majority's decision stands.

**Paxos is the protocol that implements this**:
1. Legislator proposes a law with a proposal number (to order proposals)
2. Gathers promises from majority ("I won't accept lower-numbered proposals")
3. Proposes the law to majority ("Accept law L with number N")
4. If majority accepts, law is passed (decision is certain)

**Evidence view**:
- **Promise**: Evidence that acceptor won't undermine this proposal
- **Accept vote**: Evidence of individual agreement
- **Quorum of accepts**: Sufficient evidence to prove law passed
- **Even if some legislators are unavailable later**, the law stands (quorum certificate is permanent proof)

### Why Agreement Is Hard: The Birthday Reservation Problem

Alice wants to organize a surprise birthday party. She needs to book:
- A restaurant (availability uncertain)
- A cake shop (availability uncertain)
- Entertainment (availability uncertain)

She needs **all three** or the party fails. Each vendor is independent (distributed). How does she ensure atomic agreement?

**Scenario 1: Sequential booking (no coordination)**
1. Alice books restaurant (commits)
2. Alice tries to book cake shop (unavailable)
3. Party fails, but Alice already committed to restaurant
4. **Problem**: Non-atomic decision, wasted resources

**Scenario 2: Two-phase booking (coordinator)**
1. Alice asks all vendors: "Can you be available on Oct 1?" (prepare phase)
2. Restaurant: Yes (tentative hold)
3. Cake shop: Yes (tentative hold)
4. Entertainment: No (unavailable)
5. Alice tells restaurant and cake shop: "Cancel" (abort)
6. **Result**: No commitment until all agreed (atomicity)

**This is two-phase commit (2PC)**—a consensus protocol for atomic transactions.

**But what if the coordinator (Alice) crashes after vendors respond but before she sends commit/abort?**
- Vendors are stuck holding reservations
- Cannot proceed without Alice's decision
- **Blocking protocol**: If coordinator crashes, system hangs

**Paxos/Raft solve this**: Even if the coordinator (proposer/leader) crashes, another can take over and either complete or abort the decision. **Non-blocking consensus.**

### Real-World Split-Brain Scenarios

**The danger of no consensus**: Split-brain—multiple nodes making independent, conflicting decisions.

#### Scenario 1: Database Split-Brain

**Setup**: 3-node MySQL cluster with replication, no consensus protocol.

**Failure**: Network partition splits cluster: Node 1 | Nodes 2,3

**Without consensus**:
- Node 1 thinks it's still master (old config), accepts writes
- Nodes 2,3 think Node 1 is dead, elect Node 2 as new master, accept writes
- Both "masters" accept writes to the same keys
- **Conflicting writes**, data corruption

**With consensus (Raft)**:
- Partition detected
- Node 1 (minority) cannot get quorum, refuses writes (CP choice)
- Nodes 2,3 (majority) elect new leader, continue serving (have quorum)
- **Safety preserved**: Only one leader at a time (UNIQUENESS invariant)

**Evidence view**:
- Node 1 lacks quorum evidence (only 1/3 votes)
- Nodes 2,3 have quorum evidence (2/3 votes)
- Quorum intersection ensures conflicting decisions impossible

#### Scenario 2: Distributed Lock Split-Brain

**Setup**: Distributed lock service (like Chubby, etcd) with 3 nodes.

**Failure**: Client A holds lock, then network partition.

**Without fencing**:
- Client A holds lock (from Nodes 1,2)
- Partition splits: Node 1 | Nodes 2,3
- Client A thinks it holds lock (can't reach Node 2, but already had lock)
- Nodes 2,3 think lock expired (can't reach Client A), grant lock to Client B
- **Two clients hold the same lock** (UNIQUENESS violated)

**With fencing (epoch numbers)**:
- Lock includes epoch number (incremented on each grant)
- Client A has lock with epoch 5
- Partition heals, Nodes 2,3 increment epoch to 6, grant lock to Client B with epoch 6
- Client A tries to write with epoch 5 (stale)
- Storage rejects write (epoch 5 < current epoch 6)
- **Fencing prevents split-brain**: Epoch evidence ensures only latest lock holder succeeds

**Evidence view**:
- **Lease** is evidence of lock ownership, with scope (lock ID) and lifetime (expiration time)
- **Epoch/term** is evidence of which lease is current
- Stale evidence (old epoch) is rejected, even if lease hasn't expired

#### Scenario 3: Configuration Change Split-Brain

**Setup**: Raft cluster with 3 nodes: A, B, C. Want to add node D.

**Failure**: Configuration change without joint consensus.

**Naive approach**:
- Leader broadcasts new config: {A, B, C, D}
- Some nodes (A, B) apply it immediately
- Some nodes (C) haven't received it yet
- **Two configurations active simultaneously**:
  - Old: {A, B, C} (majority: 2/3)
  - New: {A, B, C, D} (majority: 3/4)
- **Conflicting majorities**:
  - Nodes A, B can form quorum in new config (2/4 = not majority)
  - Nodes C, D can form quorum in old config (C is 1/3, D not in config = invalid)
  - Wait, let me recalculate:
  - Old config {A,B,C}: Majority = 2/3
  - New config {A,B,C,D}: Majority = 3/4
  - **The problem**: A,B can form majority in old config (2/3). B,C,D could form majority in new config (3/4). These don't overlap on all members—A could be elected leader in old config, D in new config.

**Raft's solution: Joint consensus**:
- Phase 1: Commit **joint config** {A,B,C} + {A,B,C,D} (requires majority in both old and new)
  - Must get 2/3 votes from {A,B,C} AND 3/4 votes from {A,B,C,D}
  - This ensures no conflicting leaders can be elected
- Phase 2: Once joint config committed, commit **new config** {A,B,C,D} alone
- **Guaranteed safety**: At all times, only one configuration can form a quorum

**Evidence view**:
- **Configuration** is evidence of cluster membership
- **Joint config** ensures overlap between old and new quorums
- **Epoch** ensures old configs can't override new ones

### The Essence of the Problem

Consensus is hard because:

1. **No global view**: Each node has only local information (own state, received messages)
2. **Partial failures**: Some nodes crash, some are slow, some are partitioned (cannot distinguish)
3. **Asynchrony**: Messages can be arbitrarily delayed (cannot wait forever)
4. **Concurrency**: Multiple nodes may propose simultaneously (need coordination)
5. **Byzantine failures** (optional): Some nodes may be malicious (lie, equivocate)

**The solution pattern**: Use **quorums** (majority voting) to create **overlapping evidence** that makes conflicting decisions impossible.

**Two-phase structure**:
- **Phase 1 (Prepare/Promise)**: Gather evidence that it's safe to propose (no conflicting proposals in progress)
- **Phase 2 (Accept/Commit)**: Gather evidence that value is chosen (quorum accepts)

**Evidence accumulation**: Start uncertain → gather votes → reach quorum → become certain.

---

## Part 2: UNDERSTANDING (Second Pass) — Building Mental Models

### The Consensus Problem: Formal Definition

Before diving into protocols, let's formalize what we're trying to achieve.

**System model**:
- **N processes** (nodes), each with unique ID
- **F failures tolerated** (crash failures: processes stop sending/receiving messages)
- **Quorum size**: Majority = F+1 out of N=2F+1 nodes
- **Communication**: Asynchronous message-passing (messages can be lost, delayed, reordered)

**Consensus properties** (must all be satisfied):

1. **Agreement**: All correct processes decide the same value
   - Formally: If process P decides v and process Q decides w, then v = w

2. **Validity**: If a value v is decided, then v was proposed by some process
   - Formally: No process decides a value that was never proposed (prevents trivial solutions)

3. **Termination**: All correct processes eventually decide some value
   - Formally: Every correct process eventually reaches a decision state
   - **This is the liveness property** (may be violated in practice during failures)

**Impossibility context** (from Chapter 1):
- FLP proves: Cannot achieve all three properties deterministically in asynchronous systems with even one crash
- **Resolution**: Practical protocols assume **partial synchrony** (bounded delays after GST) or use **failure detectors** (with eventual accuracy)

**Additional desirable properties**:

4. **Integrity**: Each process decides at most once
   - Once decided, decision doesn't change

5. **Uniform Agreement**: If any process (correct or faulty) decides v, then all correct processes decide v
   - Prevents faulty process from deciding differently before crashing

### Paxos: The Foundational Protocol

Paxos is the foundational consensus protocol, invented by Leslie Lamport in 1989 (published 1998, explained clearly in 2001). It's notoriously difficult to understand, but the core idea is elegant.

#### The Roles

Paxos has three roles (a node can play multiple roles):

1. **Proposers**: Propose values to be chosen
2. **Acceptors**: Vote on proposals (form quorum for decisions)
3. **Learners**: Learn the chosen value (not involved in decision)

**Typical configuration**:
- All nodes are acceptors (voting members)
- One node is the active proposer (leader)
- All nodes are learners (need to know the result)

#### The Protocol Phases

Paxos proceeds in two phases:

**Phase 1: Prepare/Promise (Proposer seeks permission to propose)**

1. **Proposer** selects a unique proposal number `n` (higher than any number it's used before)
   - Proposal numbers are globally unique and totally ordered (e.g., `(counter, node_id)` tuple)

2. **Proposer** sends `Prepare(n)` to all acceptors
   - "I want to propose with number n. Do you accept?"

3. **Acceptor** receives `Prepare(n)`:
   - If n > highest proposal number seen so far:
     - **Promise** to not accept any proposal < n
     - **Respond** with `Promise(n, v_a, n_a)` where:
       - `v_a` = value of highest-numbered proposal accepted so far (if any)
       - `n_a` = number of highest-numbered proposal accepted so far (if any)
   - If n ≤ highest proposal number seen:
     - **Ignore** or send `Nack` (old proposal)

**Phase 2: Accept/Learn (Proposer asks for votes on a value)**

4. **Proposer** receives promises from a quorum (majority) of acceptors:
   - If any promise included a previously accepted value `v_a`:
     - **Choose** the value `v_a` with the highest `n_a` (continue the highest-numbered previous proposal)
   - Else:
     - **Choose** its own proposed value `v`
   - Send `Accept(n, v)` to all acceptors

5. **Acceptor** receives `Accept(n, v)`:
   - If n ≥ highest proposal number promised:
     - **Accept** the proposal
     - Send `Accepted(n, v)` to proposer and learners
   - Else:
     - **Reject** (promised a higher number)

6. **Learner** receives `Accepted(n, v)` from a quorum of acceptors:
   - **Learn** that value `v` is chosen
   - Decision is final

#### Paxos Invariants: Why It Works

Paxos preserves the **AGREEMENT** invariant through careful design:

**Invariant P1**: An acceptor must accept the first proposal it receives.
- Ensures progress (proposals aren't arbitrarily rejected)

**Invariant P2**: If a proposal with value `v` is chosen, then every higher-numbered proposal has value `v`.
- This is the core safety property (prevents conflicting decisions)

**P2 is achieved through refinement**:

**P2a**: If a proposal with value `v` is chosen, then every higher-numbered proposal *accepted* by any acceptor has value `v`.

**P2b**: If a proposal with value `v` is chosen, then every higher-numbered proposal *issued* by any proposer has value `v`.

**P2c**: For any `n` and `v`, if a proposal `(n, v)` is issued, then:
- There exists a quorum Q such that:
  - Either: No acceptor in Q has accepted any proposal < n
  - Or: `v` is the value of the highest-numbered proposal < n accepted by some acceptor in Q

**Why P2c ensures P2b**:
- When proposer prepares with number `n`, it gets promises from quorum Q
- If any acceptor in Q accepted a proposal < n, proposer must use the value of the highest-numbered one
- By quorum intersection, any quorum that chose a value < n overlaps with Q
- Therefore, proposer will learn about any previously chosen value and continue it

**Evidence view**:
- **Promise certificate**: Quorum of promises is evidence that no conflicting proposal < n can be chosen
- **Accept certificate**: Quorum of accepts is evidence that value v is chosen
- **Quorum intersection**: Any two quorums overlap, so conflicting certificates cannot coexist

#### Multi-Paxos: Optimizing for Log Replication

Basic Paxos runs consensus on a single value. But distributed systems need to agree on a **sequence** of values (log entries). Running separate Paxos instances for each entry is inefficient.

**Multi-Paxos optimization**:

1. **Elect a stable leader**: Run Paxos once to agree on a leader for an epoch
2. **Leader skip Phase 1**: Leader can skip Phase 1 (prepare) for subsequent proposals (already has implicit promises)
3. **Leader propose directly**: Leader sends `Accept` messages directly (Phase 2)
4. **Log replication**: Each log entry is a separate Paxos instance, but leader optimizes to 1-round trip

**Leader lease**:
- Leader holds lease for a period (e.g., 10 seconds)
- Lease is evidence of leadership with limited lifetime
- Followers promise not to accept proposals from other leaders during lease
- If leader crashes, lease expires, new leader elected

**Evidence in Multi-Paxos**:
- **Leader lease**: Evidence of exclusive proposal rights (scope: epoch, lifetime: lease duration)
- **Log entry commit**: Evidence that value at index i is chosen (quorum of accepts)
- **Epoch number**: Evidence of leader generation (prevents stale leaders)

**State machine replication**:
- Apply log entries in order to deterministic state machine
- All replicas see same inputs in same order → same output state
- Consensus on log order = consistency of state

#### Paxos in Practice: Challenges

Despite theoretical elegance, Paxos has practical challenges:

1. **Hard to understand**: The protocol's correctness is subtle (Phase 1 vs Phase 2, why proposer must choose highest accepted value)
2. **Hard to implement correctly**: Many edge cases (concurrent proposers, message loss, acceptor recovery)
3. **Leader election not specified**: Paxos assumes a proposer somehow becomes active (but doesn't specify how)
4. **Log management not specified**: Snapshotting, log compaction, garbage collection are implementation details
5. **Configuration changes not specified**: How to add/remove nodes safely

**This motivated Raft**: a consensus protocol explicitly designed for understandability.

### Raft: Consensus for the Real World

Raft was designed in 2013 by Diego Ongaro and John Ousterhout with one goal: **be easier to understand and implement than Paxos**.

**Design principles**:
1. **Decomposition**: Separate leader election, log replication, and safety
2. **Reduced state space**: Fewer states and transitions than Paxos
3. **Strong leader**: Log entries only flow from leader to followers (simpler than Paxos where any node can propose)

#### Raft Overview

**Key concepts**:
- **Term**: Logical time period with at most one leader (like Paxos epoch)
- **Leader**: Elected by majority vote, handles all client requests, replicates log
- **Follower**: Passive, accepts log entries from leader, votes in elections
- **Candidate**: Follower seeking to become leader (transient state)

**Protocol structure**:
1. **Leader Election**: Elect a single leader for a term
2. **Log Replication**: Leader replicates log entries to followers
3. **Safety**: Ensure chosen log entries are never lost

#### Raft: Leader Election

**Normal operation**: One leader, all others followers.

**Followers expect periodic heartbeats from leader** (e.g., every 50ms):
- If heartbeat received: Reset election timeout (leader is alive)
- If election timeout expires (e.g., 150-300ms): Become candidate, start election

**Election process**:

1. **Follower timeout**: Election timeout expires, follower becomes candidate
   - Increment term: `current_term = current_term + 1`
   - Vote for self
   - Send `RequestVote(term, candidateId, lastLogIndex, lastLogTerm)` to all nodes

2. **Follower receives `RequestVote`**:
   - If `term < current_term`: Reject (stale candidate)
   - If already voted in this term: Reject (one vote per term)
   - If candidate's log is at least as up-to-date as receiver's log:
     - **Grant vote**
     - Reset election timeout (gave vote, don't start own election)
   - Else: Reject (candidate's log is stale)

3. **Candidate collects votes**:
   - If receive votes from majority: **Become leader**
     - Send heartbeats to all (establish leadership)
   - If receive `AppendEntries` from another leader with `term ≥ current_term`: **Step down to follower**
   - If election timeout expires (no majority): **Start new election** (increment term, try again)

**Log up-to-date comparison**: Candidate's log is at least as up-to-date if:
- Last entry's term is higher, OR
- Last entry's term is same and log is at least as long

**Why this matters**: Ensures new leader has all committed entries (Leader Completeness property).

**Preventing split votes**:
- **Randomized election timeouts**: Each follower picks random timeout in [150ms, 300ms]
- Usually one follower times out first, wins election before others start
- If split vote (no majority), random timeouts prevent simultaneous retry

**Evidence in leader election**:
- **Vote**: Evidence of support for candidate (scope: term, lifetime: until next term)
- **Vote certificate**: Majority of votes is evidence of leadership (quorum certificate)
- **Term number**: Evidence of election generation (prevents stale leaders)

#### Raft: Log Replication

Once elected, leader handles all client requests by appending entries to its log and replicating to followers.

**Log structure**:
- Each entry contains:
  - **Term**: When entry was created
  - **Index**: Position in log
  - **Command**: State machine command (e.g., "set X=5")

**Replication process**:

1. **Client sends command** to leader

2. **Leader appends entry** to local log (not yet committed)

3. **Leader sends `AppendEntries(term, leaderId, prevLogIndex, prevLogTerm, entries[], leaderCommit)`** to all followers
   - `prevLogIndex`: Index of log entry immediately preceding new ones
   - `prevLogTerm`: Term of prevLogIndex entry
   - `entries[]`: New log entries to replicate
   - `leaderCommit`: Leader's commit index (highest index known to be committed)

4. **Follower receives `AppendEntries`**:
   - If `term < current_term`: Reject (stale leader)
   - If log doesn't contain entry at `prevLogIndex` with `prevLogTerm`:
     - **Reject** (log inconsistency, need to back up)
   - Else:
     - **Append entries** (may overwrite uncommitted conflicting entries)
     - **Update commit index**: `commitIndex = min(leaderCommit, index of last new entry)`
     - **Reply success**

5. **Leader receives success** from majority:
   - **Mark entry as committed**: `commitIndex = index`
   - **Apply to state machine**
   - **Return result to client**
   - Followers apply committed entries to their state machines

**Log consistency check**: The `(prevLogIndex, prevLogTerm)` ensures followers apply entries in order. If check fails:
- Leader decrements `nextIndex` for that follower (back up one entry)
- Retry `AppendEntries` with earlier prevLogIndex
- Repeat until logs match, then catch up follower

**Commitment rule**: Entry is committed when:
- It is stored on a majority of servers, AND
- At least one entry from leader's current term is committed

(Second condition prevents committing entries from past terms prematurely)

**Evidence in log replication**:
- **AppendEntries RPC**: Evidence of leader's proposed log state
- **Success response**: Evidence that follower has entry (individual vote)
- **Commit certificate**: Majority of successes is evidence that entry is chosen (quorum certificate)
- **commitIndex**: Evidence of how much of the log is durable

#### Raft: Safety Properties

Raft ensures the following safety properties:

1. **Election Safety**: At most one leader per term
   - Ensured by: Each node votes for at most one candidate per term

2. **Leader Append-Only**: Leader never overwrites or deletes entries in its log
   - Ensured by: Leader only appends, never modifies existing entries

3. **Log Matching**: If two logs contain an entry with the same index and term, then all preceding entries are identical
   - Ensured by: AppendEntries consistency check (prevLogIndex, prevLogTerm)

4. **Leader Completeness**: If an entry is committed in a term, it will be present in the logs of leaders of all higher terms
   - Ensured by: Election restriction (candidate must have all committed entries to win)

5. **State Machine Safety**: If a server has applied a log entry at a given index, no other server will apply a different entry at that index
   - Ensured by: Log Matching + Leader Completeness

**Why State Machine Safety matters**: This is the ultimate goal—all replicas apply the same commands in the same order, producing identical state.

**Evidence view**:
- Safety properties are invariants preserved by Raft's rules
- Each property is protected by evidence requirements:
  - Election Safety: Vote certificates ensure uniqueness (quorum intersection)
  - Leader Completeness: Vote granted only if candidate's log is up-to-date (evidence of having committed entries)
  - State Machine Safety: Commit certificate ensures entry chosen, log matching ensures order

#### Raft: Log Compaction (Snapshotting)

Logs grow unbounded. Eventually must discard old entries.

**Snapshotting**:
- Periodically, each server creates snapshot of current state
- Snapshot includes:
  - Last included index (last entry in snapshot)
  - Last included term
  - State machine state
- Discard log entries ≤ last included index

**Installing snapshots**:
- If follower is far behind, leader sends entire snapshot via `InstallSnapshot` RPC
- Follower replaces its state with snapshot, discards old log

**Evidence lifecycle**:
- Log entries are evidence with limited lifetime (until snapshot)
- After snapshot, snapshot itself becomes evidence of state at that point
- Old log evidence is revoked (discarded)

#### Raft: Configuration Changes (Joint Consensus)

How to add or remove nodes without split-brain?

**Unsafe approach**: Switch directly from old config to new config
- Some nodes apply new config immediately, some still on old
- Two majorities can form (in old and new configs) that don't overlap
- **Split-brain risk**

**Raft's safe approach: Joint consensus**:

1. **Leader receives request** to change config from `C_old` to `C_new`

2. **Leader commits `C_old,new` (joint configuration)**:
   - Requires majority in *both* `C_old` and `C_new`
   - While in `C_old,new`, all decisions (elections, commits) require double quorum
   - This prevents split-brain (cannot form quorum in only old or only new)

3. **Once `C_old,new` committed, leader commits `C_new` alone**:
   - Now requires majority only in `C_new`
   - Old nodes not in `C_new` can shut down

**Guarantee**: At no point can both old-only and new-only quorums make decisions.

**Evidence view**:
- **Configuration** is evidence of cluster membership
- **Joint config** ensures all quorums overlap during transition
- **Term numbers** ensure old configs cannot override new ones

### Byzantine Consensus: Tolerating Malicious Failures

So far, we've assumed **crash failures** (nodes stop, don't lie). What if nodes are **Byzantine** (malicious, send conflicting messages, lie about state)?

**Byzantine failure model**:
- Faulty nodes can:
  - Send arbitrary messages
  - Equivocate (send conflicting messages to different nodes)
  - Collude with other faulty nodes
  - Pretend to crash or recover arbitrarily

**Impossibility**: Cannot tolerate F Byzantine failures with ≤ 3F nodes.
- Need at least **3F + 1 nodes** to tolerate F Byzantine failures
- Byzantine quorum: 2F + 1 (majority of non-faulty + faulty nodes)

**Why 3F+1?**:
- In worst case, F nodes are faulty
- Need 2F+1 responses to ensure F+1 are from correct nodes (majority of correct)
- If you have only 3F nodes, 2F responses might include all F faulty + F correct (no majority of correct)

#### PBFT: Practical Byzantine Fault Tolerance

PBFT (1999, Castro & Liskov) was the first practical Byzantine consensus protocol.

**Three-phase protocol**:

1. **Pre-Prepare**: Leader (primary) assigns sequence number to request, broadcasts `<PRE-PREPARE, v, n, m>` to all replicas
   - `v` = view number (like term)
   - `n` = sequence number
   - `m` = message (request)

2. **Prepare**: Replicas verify pre-prepare, then broadcast `<PREPARE, v, n, d, i>` to all replicas
   - `d` = digest of message (hash)
   - `i` = replica ID
   - **Prepared certificate**: Replica collects 2F+1 matching `PREPARE` messages (including own)
   - This proves: 2F+1 replicas agree on sequence number for this request

3. **Commit**: Once prepared, replica broadcasts `<COMMIT, v, n, d, i>` to all replicas
   - **Committed certificate**: Replica collects 2F+1 matching `COMMIT` messages
   - This proves: At least F+1 correct replicas are prepared (by quorum intersection)
   - **Execute** request, reply to client

**Why three phases?**:
- **Pre-Prepare**: Leader proposes order
- **Prepare**: Replicas agree on order within view (prevents conflicting orders from faulty primary)
- **Commit**: Replicas ensure agreement across views (even if view change occurs, committed value survives)

**View change**: If primary is faulty or slow:
- Replicas timeout, broadcast `<VIEW-CHANGE, v+1, ...>` to new primary
- New primary collects 2F+1 view-change messages (quorum)
- New primary sends `<NEW-VIEW, v+1, ...>` with proof
- Replicas verify and adopt new view

**Authentication**: All messages signed (public-key cryptography)
- Prevents forgery, ensures non-repudiation
- Faulty nodes cannot forge correct nodes' signatures

**Evidence in PBFT**:
- **Prepared certificate**: 2F+1 signed PREPARE messages (proof of order agreement within view)
- **Committed certificate**: 2F+1 signed COMMIT messages (proof of cross-view agreement)
- **View-change certificate**: 2F+1 signed VIEW-CHANGE messages (proof of need for new primary)

#### Modern Byzantine Consensus: HotStuff

PBFT has **O(n²) message complexity** (all-to-all communication). Recent protocols improve this.

**HotStuff (2019, VMware Research)**:
- **Linear message complexity**: O(n) messages per consensus (leader broadcasts, replicas respond to leader)
- **Pipelined**: Multiple instances in flight (higher throughput)
- **Responsive**: Commit latency depends on actual network delay, not worst-case timeout

**Three-phase protocol** (like PBFT, but streamlined):
1. **Prepare**: Leader proposes, collects 2F+1 votes
2. **Pre-commit**: Leader creates QC (quorum certificate), broadcasts, collects 2F+1 votes
3. **Commit**: Leader creates pre-commit QC, broadcasts, collects 2F+1 votes
4. **Decide**: Leader creates commit QC, broadcasts, all decide

**Threshold signatures**: Instead of collecting 2F+1 individual signatures, use threshold signature scheme:
- Replicas send signature shares
- Leader combines F+1 shares into single aggregate signature
- Reduces communication and verification overhead

**Responsiveness**: Uses pacemaker for leader rotation, but committed values survive leader changes with low latency.

**Use cases**:
- **Blockchains**: DiemBFT (Libra/Diem), Ethereum 2.0 (Casper)
- **Permissioned systems**: Hyperledger, Quorum

**Evidence in HotStuff**:
- **Quorum Certificate (QC)**: Aggregate signature of 2F+1 votes (compact evidence)
- **Chained QCs**: Each phase includes QC from previous phase (chain of evidence)
- **View number**: Evidence of leader rotation (prevents stale leaders)

### Advanced Consensus Topics

#### Flexible Paxos: Relaxing Quorum Requirements

Classic Paxos requires **majority quorum in both phases**. Flexible Paxos (2016, Howard & Heidi) relaxes this.

**Key insight**: Only need quorum intersection, not necessarily majority in each phase.

**Flexible quorum condition**:
- Phase 1 quorum: Q₁
- Phase 2 quorum: Q₂
- **Requirement**: Q₁ + Q₂ > N (quorums must overlap)

**Example**: N=5 nodes
- Classic Paxos: Q₁=3, Q₂=3 (both majority)
- Flexible: Q₁=2, Q₂=4 (still overlap: 2+4=6 > 5)

**Benefits**:
- Can make Phase 1 (prepare) cheaper (smaller quorum) at cost of more expensive Phase 2 (accept)
- Or vice versa: cheaper Phase 2 (fast path for common case), expensive Phase 1 (rare leader change)

**Use case**: Read-heavy workloads
- Make reads (Phase 2 in Paxos for read quorum) cheap: Q₂=2
- Make writes expensive: Q₁=4
- Reads are faster, writes slower (acceptable if reads dominate)

**Evidence view**:
- Flexible quorums still ensure quorum intersection (no conflicting evidence)
- But can optimize evidence collection costs based on workload

#### EPaxos: Leaderless Consensus

Classic Paxos/Raft use a leader (single proposer at a time). EPaxos (Egalitarian Paxos, 2013) is leaderless—any node can propose.

**Key idea**: Order **commutative operations** concurrently, only serialize conflicting operations.

**Protocol**:
1. Any replica proposes a command
2. Collect dependencies: Which concurrent commands conflict?
3. Fast path: If no conflicts, commit in one round (no leader needed)
4. Slow path: If conflicts detected, run full Paxos to determine order

**Advantages**:
- **No leader bottleneck**: All replicas can propose simultaneously (higher throughput)
- **Low latency**: Single round-trip for non-conflicting operations
- **Load balancing**: Replicas geographically distributed, clients send to nearest replica

**Disadvantages**:
- **Complexity**: Dependency tracking is intricate
- **Garbage collection**: Must track and merge dependency graphs
- **Applicability**: Only works for commutative/compatible operations (doesn't apply to all workloads)

**Evidence view**:
- **Dependency graph**: Evidence of causal/conflict relationships between commands
- **Fast quorum**: Quorum agreement on dependencies allows single-round commit
- **Slow path**: Fall back to full Paxos if dependency agreement fails

#### Consensus-as-a-Service

In practice, implementing consensus correctly is hard. Many systems use dedicated consensus services.

**etcd** (Raft-based):
- Distributed key-value store
- Used by Kubernetes for cluster coordination
- Provides: Linearizable reads/writes, leases, watches
- **Typical deployment**: 3-5 nodes, <10ms commit latency (local network)

**Apache ZooKeeper** (ZAB protocol, Paxos variant):
- Coordination service (configuration, synchronization, naming)
- Used by Hadoop, Kafka, HBase
- Provides: Sequential consistency, watches, ephemeral nodes
- **Typical deployment**: 3-5 nodes, <15ms commit latency

**Consul** (Raft-based):
- Service discovery and configuration
- Provides: Multi-datacenter support, health checks, KV store

**When to use consensus-as-a-service**:
- Need coordination primitives (locks, leader election, config management)
- Don't want to implement consensus yourself (complexity)
- Acceptable to depend on external service (operational overhead, single point of failure)

**Trade-offs**:
- **Pro**: Proven implementation, operational tools, community support
- **Con**: Network hop (added latency), separate system to operate, potential bottleneck

---

## Part 3: MASTERY (Third Pass) — Evidence, Invariants, and Operations

### Evidence-Based Consensus

Let's formalize consensus through the evidence lens.

**Consensus is evidence generation**: Converting uncertain proposals into certain decisions by collecting sufficient votes (evidence) from a quorum.

#### Evidence Types in Consensus

**1. Promise Evidence (Paxos Phase 1)**:
- **Type**: Promise not to accept lower-numbered proposals
- **Scope**: Proposal number n, acceptor ID
- **Lifetime**: Until acceptor sees higher proposal number
- **Binding**: Acceptor that issued promise
- **Transitivity**: Non-transitive (promise is local to acceptor)
- **Quorum requirement**: Majority of acceptors

**Promise certificate** (quorum of promises):
- Evidence that proposer can safely propose with number n
- Guarantees: No conflicting proposal < n can be chosen (quorum intersection)

**2. Accept Evidence (Paxos Phase 2, Raft AppendEntries)**:
- **Type**: Acceptance of value v with proposal number n
- **Scope**: Proposal number n, value v, acceptor ID
- **Lifetime**: Permanent (accepted value cannot be unaccepted)
- **Binding**: Acceptor that accepted
- **Transitivity**: Non-transitive (each acceptor's acceptance is independent)
- **Quorum requirement**: Majority of acceptors

**Accept certificate** (quorum of accepts):
- Evidence that value v is chosen
- Guarantees: Value v is the decided value, immutable

**3. Vote Evidence (Raft RequestVote)**:
- **Type**: Vote for candidate in term
- **Scope**: Term number, candidate ID
- **Lifetime**: Until end of term
- **Binding**: Voter that issued vote
- **Transitivity**: Non-transitive
- **Quorum requirement**: Majority of voters

**Vote certificate** (quorum of votes):
- Evidence that candidate is leader for this term
- Guarantees: Only one leader per term (quorum intersection)

**4. Commit Evidence (Raft leaderCommit)**:
- **Type**: Proof that entry at index i is committed
- **Scope**: Log index i, term
- **Lifetime**: Permanent (committed entries never lost)
- **Binding**: Leader that committed
- **Transitivity**: Transitive (followers trust leader's commit index)
- **Quorum requirement**: Majority of followers acknowledged

**Commit certificate**:
- Evidence that log entry is durable and will be applied to state machine
- Guarantees: Entry will appear in all future leaders' logs (Leader Completeness)

**5. Byzantine Evidence (PBFT certificates)**:
- **Prepared certificate**: 2F+1 signed PREPARE messages
- **Committed certificate**: 2F+1 signed COMMIT messages
- **Scope**: View number, sequence number, message digest
- **Lifetime**: Permanent (certificate proves historical agreement)
- **Binding**: Replicas that signed (authenticated by signatures)
- **Transitivity**: Transitive (anyone can verify signatures)

#### Evidence Lifecycle in Consensus

**1. Generation** (Propose phase):
- **Paxos**: Proposer generates proposal with number n
- **Raft**: Leader generates log entry with term and index
- **Byzantine**: Primary generates pre-prepare with view and sequence

**2. Collection** (Voting phase):
- **Paxos Phase 1**: Collect promises from quorum
- **Paxos Phase 2**: Collect accepts from quorum
- **Raft Election**: Collect votes from quorum
- **Raft Replication**: Collect AppendEntries successes from quorum
- **Byzantine**: Collect signed messages from 2F+1 replicas

**3. Validation** (Quorum check):
- **Count votes**: Do we have quorum (majority or 2F+1)?
- **Check authenticity**: Are signatures valid (Byzantine)?
- **Check freshness**: Are votes for current term/view?

**4. Active** (Decision made):
- **Paxos**: Value is chosen (learned by learners)
- **Raft**: Entry is committed (applied to state machine)
- **Byzantine**: Request is executed (reply sent to client)

**5. Expiring** (Term/view change):
- **Paxos**: New proposal number used, old promises expired
- **Raft**: New term started, old votes expired
- **Byzantine**: View change, old view's certificates expired

**6. Expired/Revoked**:
- **Paxos**: Acceptor promises higher number, old promise revoked
- **Raft**: New leader elected, old leader's authority revoked
- **Byzantine**: View change complete, old primary's authority revoked

**7. Renewal** (New round):
- **Paxos**: New proposer starts with higher proposal number
- **Raft**: New election for new term
- **Byzantine**: New primary elected in new view

### Invariant Framework for Consensus

Consensus protocols preserve specific invariants. Let's catalog them.

#### Primary Invariant: UNIQUENESS

**Statement**: At most one value can be chosen for a given decision instance.

**Formally**:
- For consensus instance I, if value v₁ is chosen and value v₂ is chosen, then v₁ = v₂
- Or equivalently: There exists at most one chosen value per instance

**Why it matters**:
- Prevents split decisions (conflicting values)
- Ensures all nodes agree on the same value (AGREEMENT property follows)

**Threat model**:
- **Concurrent proposers**: Two proposers simultaneously propose different values
- **Network partition**: Different quorums form in different partitions, potentially choosing different values
- **Byzantine nodes**: Malicious nodes vote for conflicting values

**Protection mechanisms**:
- **Quorum intersection**: Any two quorums overlap, ensuring conflicting decisions cannot both have quorum certificates
- **Proposal numbering**: Higher-numbered proposals override lower-numbered (total order)
- **Byzantine quorums**: 2F+1 quorum ensures at least F+1 correct nodes in common (majority of correct)

**Evidence needed**: Quorum certificate (majority accepts or 2F+1 in Byzantine)

**Degradation**: If quorum unavailable, refuse to decide (maintain safety, sacrifice liveness)

#### Supporting Invariant: AGREEMENT

**Statement**: All correct processes decide the same value.

**Formally**: If process P decides v and process Q decides w, then v = w

**Relationship to UNIQUENESS**: AGREEMENT follows from UNIQUENESS (if only one value chosen, all must decide that one)

**Protection**: Same as UNIQUENESS (quorum intersection)

#### Supporting Invariant: VALIDITY

**Statement**: The decided value was proposed by some process (not manufactured).

**Why it matters**: Prevents trivial solutions (e.g., always decide 0)

**Protection**: Proposer chooses value from proposals, never invents arbitrary value

#### Supporting Invariant: MONOTONICITY (Log order)

**Statement**: Once a log entry is committed, all subsequent log states include that entry.

**Formally**: If entry E at index i is committed in log L, then all future log states L' include E at index i

**Threat model**:
- **Leader crash**: New leader might not have committed entries
- **Log divergence**: Followers might have conflicting uncommitted entries

**Protection (Raft)**:
- **Leader election restriction**: Candidate must have all committed entries to win election
- **AppendEntries consistency check**: Followers reject entries that don't match previous entry

**Evidence needed**: Commit certificate (quorum acknowledged)

**Degradation**: If majority unavailable, cannot commit new entries (but old commits are safe)

#### Composite Invariant: LEADER UNIQUENESS (Raft/Multi-Paxos)

**Statement**: At most one leader per term/epoch.

**Why it matters**: Multiple leaders can propose conflicting log entries, violating consensus

**Protection**:
- **One vote per term**: Each node votes for at most one candidate per term
- **Quorum of votes**: Leader must have majority votes (quorums overlap)
- **Term numbers**: Higher term overrides lower (fencing)

**Evidence needed**: Vote certificate (majority votes)

**Degradation**: If partition prevents quorum, no leader elected (unavailable but safe)

#### Composite Invariant: LEADER COMPLETENESS (Raft)

**Statement**: If an entry is committed in term T, it appears in the log of every leader of term > T.

**Why it matters**: Ensures committed entries are never lost across leader changes

**Protection**:
- **Election restriction**: Candidate's log must be at least as up-to-date as voter's log
- **Log comparison**: Compare last entry's term and log length

**Evidence needed**: Vote granted only if candidate's log is up-to-date

**Degradation**: N/A (this is a safety invariant, never relaxed)

### Guarantee Vectors for Consensus Operations

Let's type consensus operations using guarantee vectors.

**Reminder**: Guarantee vector `G = ⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩`

#### Raft Write (Committed entry)

**Input**: Client request (command)

**Output**: Committed log entry

**Guarantee vector**: `⟨Global, SS, SER, Fresh(φ), Idem(K), Auth⟩`

- **Scope**: Global (all replicas see same log order)
- **Order**: SS (strict serializable—real-time order via term numbers)
- **Visibility**: SER (serializable—all reads see committed writes)
- **Recency**: Fresh(φ) (evidence: commit certificate)
- **Idempotence**: Idem(K) (client assigns unique request ID)
- **Auth**: Auth(π) (leader verifies client identity)

**Evidence flow**:
1. Client sends command to leader (authenticated)
2. Leader appends to log (proposal)
3. Leader sends AppendEntries to followers (collect votes)
4. Followers respond (evidence generation)
5. Leader receives quorum (commit certificate)
6. Leader updates commitIndex, applies to state machine (decision)
7. Leader responds to client (proof of commit)

#### Raft Follower Read (Stale read)

**Input**: Client read request

**Output**: Value from follower's state machine

**Guarantee vector**: `⟨Range, SS, SI, BS(δ), Idem, Auth⟩`

- **Scope**: Range (follower's view of log)
- **Order**: SS (log order is strict serializable)
- **Visibility**: SI (snapshot isolation—read sees consistent snapshot)
- **Recency**: BS(δ) (bounded staleness—follower may lag leader by replication delay δ)
- **Idempotence**: Idem (reads are idempotent)
- **Auth**: Auth(π) (follower verifies client identity)

**Evidence**: Follower's commitIndex (proof of how much log is applied)

**Staleness bound**: δ = time since last heartbeat (typically 50-200ms)

**Downgrade from leader read**: Fresh(φ) → BS(δ) (trade freshness for lower latency)

#### Paxos Single-Value Consensus

**Input**: Proposed value v

**Output**: Chosen value (may be v or another value)

**Guarantee vector**: `⟨Object, SS, SER, Fresh(φ), Idem(K), Auth⟩`

- **Scope**: Object (single consensus instance)
- **Order**: SS (proposal numbers totally ordered)
- **Visibility**: SER (all learners see same chosen value)
- **Recency**: Fresh(φ) (accept quorum certificate proves value chosen now)
- **Idempotence**: Idem(K) (proposal numbers ensure uniqueness)
- **Auth**: Auth(π) (acceptors verify proposer)

**Evidence flow**:
1. Proposer sends Prepare(n) (seek permission)
2. Acceptors respond with Promise (vote to support)
3. Proposer collects quorum (promise certificate)
4. Proposer sends Accept(n, v) (ask for decision)
5. Acceptors respond with Accepted(n, v) (vote for value)
6. Learners receive quorum Accepted messages (accept certificate = proof of decision)

#### Byzantine Consensus (PBFT)

**Input**: Client request m

**Output**: Executed request, reply

**Guarantee vector**: `⟨Global, SS, SER, Fresh(φ), Idem, Signed⟩`

- **Scope**: Global (all replicas execute in same order)
- **Order**: SS (sequence numbers totally ordered)
- **Visibility**: SER (all replicas see same execution order)
- **Recency**: Fresh(φ) (committed certificate proves current agreement)
- **Idempotence**: Idem (client assigns unique request ID)
- **Auth**: Signed (all messages signed, cryptographic proof)

**Evidence flow**:
1. Client sends signed request to primary
2. Primary assigns sequence number, sends PRE-PREPARE (proposal)
3. Replicas send PREPARE (vote on order)
4. Replicas collect 2F+1 PREPARE (prepared certificate)
5. Replicas send COMMIT (vote on execution)
6. Replicas collect 2F+1 COMMIT (committed certificate = proof of agreement)
7. Replicas execute, send signed reply to client
8. Client waits for F+1 matching replies (proof of correct execution)

**Stronger evidence**: Signatures provide non-repudiation (can prove to third party)

### Mode Matrix for Consensus Systems

Consensus systems operate in different modes depending on failures and evidence availability.

#### Target Mode (Healthy operation)

**State**:
- Stable leader elected
- Quorum of followers available
- Network delays within expected bounds (partial synchrony holds)

**Invariants preserved**:
- **UNIQUENESS**: Only one value chosen per instance
- **AGREEMENT**: All correct nodes decide same value
- **LEADER UNIQUENESS**: Only one leader per term
- **MONOTONICITY**: Committed entries never lost

**Evidence available**:
- **Leader lease**: Valid (hasn't expired)
- **Quorum reachable**: Leader can reach majority of followers
- **Heartbeats current**: Followers receiving heartbeats within timeout
- **Commit certificates**: Fresh (entries committed within expected latency)

**Allowed operations**:
- **Writes**: Client writes accepted by leader, replicated to followers, committed (quorum)
- **Linearizable reads**: Leader serves reads (has fresh commit state)
- **Follower reads**: Followers serve bounded-stale reads (with explicit staleness bound)

**Guarantee vector** (write): `⟨Global, SS, SER, Fresh(φ), Idem, Auth⟩`

**Performance**:
- **Commit latency**: 1-2 RTT (leader to followers and back)
- **Throughput**: High (leader not overloaded)

**Entry condition**:
- Leader elected successfully
- Quorum of followers responsive
- Network stable

**Exit condition** (to Degraded):
- Leader cannot reach quorum (network partition, node failures)
- Heartbeat timeouts (followers suspect leader failure)

#### Degraded Mode (Partial failures)

**State**:
- Leader available but some followers unreachable, OR
- Leader suspected failed (timeouts), election in progress, OR
- Quorum borderline (exactly F+1 nodes available, no margin for error)

**Invariants preserved**:
- **UNIQUENESS**: Still only one value chosen (safety paramount)
- **AGREEMENT**: Committed values agreed upon (though new commits may fail)

**Invariants relaxed**:
- **TERMINATION**: May not make progress on new proposals (liveness affected)
- **LEADER UNIQUENESS**: During election, temporarily no leader (unavailable)

**Evidence available**:
- **Commit certificates**: For old entries (already committed)
- **Quorum uncertain**: May or may not have quorum (if exactly F+1 nodes reachable)

**Allowed operations**:
- **Writes**: May fail (leader cannot reach quorum) OR accepted but slow (marginal quorum)
- **Reads**: Serve stale data (followers may lag) OR redirect to leader (if leader still reachable)
- **Elections**: In progress (if leader suspected failed)

**Guarantee vector** (read): `⟨Range, SS, SI, BS(δ), Idem, Auth⟩`

**Degradation strategy**:
- **Leader**: Continue attempting to replicate, increase timeouts (adaptive backoff)
- **Followers**: If heartbeats missing, start election (after timeout)
- **Clients**: Retry writes (idempotent), accept stale reads (with staleness bound)

**Entry condition** (from Target):
- Some followers unreachable (but quorum still available)
- Intermittent network issues (delays approaching timeout threshold)
- Node failures (F-1 or F nodes failed, barely maintaining quorum)

**Exit condition**:
- **To Target**: All followers reachable again, leader stable
- **To Floor**: Quorum lost (majority of nodes unreachable)

#### Floor Mode (Safety-only, no liveness)

**State**:
- No quorum available (majority of nodes unreachable), OR
- Leader election failing repeatedly (split votes), OR
- Network partition with minority partition

**Invariants preserved**:
- **UNIQUENESS**: Still only one value chosen (never violate safety)
- **AGREEMENT**: Committed values remain agreed upon

**Invariants abandoned**:
- **TERMINATION**: Cannot make progress (liveness lost)

**Evidence available**:
- **Old commit certificates**: For previously committed entries (historical evidence)
- **No fresh evidence**: Cannot generate new commit certificates (no quorum)

**Allowed operations**:
- **Writes**: Rejected (cannot commit without quorum)
- **Reads**:
  - **Option 1**: Serve stale reads (with explicit staleness warning)
  - **Option 2**: Reject reads (fail closed, prevent serving arbitrarily stale data)
- **Elections**: Attempted but failing (no quorum to elect leader)

**Guarantee vector** (if serving reads): `⟨Range, —, RA, EO, Idem, Auth⟩`

- No ordering guarantee (can't commit new entries to establish order)
- Read-atomic (can read local state)
- Eventual consistency (will converge once partition heals)

**Floor mode strategy**:
- **CP choice**: Reject writes and reads (maintain consistency, sacrifice availability)
- **AP choice**: Serve stale reads (maintain availability, sacrifice consistency—explicitly labeled)

**Entry condition** (from Degraded):
- Quorum lost (majority unreachable)
- Election timeouts repeatedly (cannot elect leader)

**Exit condition** (to Recovery):
- Network partition heals
- Failed nodes recover
- Quorum becomes available again

#### Recovery Mode (Rejoining/healing)

**State**:
- Network partition healed
- Failed nodes recovering
- New leader elected, but some nodes need to catch up

**Goal**: Restore consistency and return to Target mode.

**Actions**:
- **Leader election**: Complete election, establish new leader with term/epoch number
- **Log repair**: Leader identifies followers with stale logs
- **Log replication**: Leader sends missing entries (or snapshot if too far behind)
- **Catch-up**: Followers apply missing entries, update state machine
- **Validation**: Ensure all nodes have consistent view of committed log

**Evidence needed**:
- **Vote certificate**: New leader elected (quorum of votes)
- **Commit certificates**: For all entries being caught up
- **Epoch number**: New term/view established (fences old leaders)

**Allowed operations** (during recovery):
- **Writes**: Leader accepts new writes (commits once catch-up complete)
- **Reads**:
  - **Leader**: Can serve reads (has up-to-date state)
  - **Followers**: Serve stale reads until caught up, then fresh reads

**Guarantee vector** (write, once stable): `⟨Global, SS, SER, Fresh(φ), Idem, Auth⟩`

**Recovery patterns**:

1. **Log catch-up** (Raft):
   - Leader sends AppendEntries with missing entries
   - Follower applies incrementally
   - Once caught up, follower returns to Target mode

2. **Snapshot transfer** (Raft):
   - If follower too far behind (leader already compacted log)
   - Leader sends InstallSnapshot RPC with full snapshot
   - Follower replaces state with snapshot, discards old log

3. **Reconciliation** (eventual consistency):
   - If AP choice was made (served stale reads/writes during partition)
   - After partition heals, reconcile conflicting values (last-write-wins, CRDTs, manual intervention)

**Exit condition** (to Target):
- All nodes caught up
- Stable leader
- Quorum healthy

**Fallback** (to Degraded/Floor):
- Recovery fails (another partition, more failures)
- Cannot establish quorum

### Production Patterns for Consensus

#### Monitoring Consensus Health

**Key metrics**:

| Metric | Target | Degraded | Floor |
|--------|--------|----------|-------|
| Leader stable | Yes (term > 10 sec) | Elections frequent (<10 sec) | No leader |
| Quorum available | 100% | Borderline (F+1) | Lost (<F+1) |
| Commit latency P50 | <10ms | 10-100ms | N/A (no commits) |
| Commit latency P99 | <50ms | >100ms | N/A |
| Replication lag P50 | <5ms | 5-50ms | N/A |
| Replication lag P99 | <20ms | >50ms | N/A |
| Election frequency | <1/hour | >1/hour | Continuous |
| Heartbeat success rate | >99% | 90-99% | <90% |

**Dashboard example (etcd, Raft-based)**:

```
Cluster Health: Target ✓
  Leader: node-1 (term 47, stable for 3h 24m)
  Followers: node-2 (lag: 3ms), node-3 (lag: 5ms)
  Quorum: 3/3 nodes reachable ✓

Performance:
  Commit latency P50: 4ms ✓
  Commit latency P99: 12ms ✓
  Throughput: 5000 commits/sec

Recent events:
  [12h ago] Term 46 → 47: Leader re-election (node-1 timeout)
  [3h ago] node-3 rejoined (was unreachable 2min)
```

**Alerts**:

- **Warning**: `commit_latency_p99 > 50ms` (degrading performance)
- **Warning**: `replication_lag_p99 > 50ms` (followers falling behind)
- **Critical**: `quorum_lost` (cannot commit new entries)
- **Critical**: `election_duration > 10 sec` (liveness affected)
- **Critical**: `term_frequency > 10 per hour` (unstable cluster)

**Evidence-based alerts**:

- "Commit evidence generation slow (P99 > 50ms)" → Investigate leader load, network
- "Quorum evidence unavailable (lost majority)" → Enter Floor mode, alert on-call
- "Leader lease evidence expired (no heartbeats)" → Election triggered, expect brief unavailability

#### Tuning Consensus Parameters

**Raft tuning knobs**:

1. **Election timeout**: Time follower waits before starting election (default: 150-300ms)
   - **Too low**: Frequent elections (false timeouts due to transient delays)
   - **Too high**: Slow leader failure detection (extended unavailability)
   - **Guideline**: 10× expected network RTT (if RTT=5ms, use 50ms timeout)

2. **Heartbeat interval**: How often leader sends heartbeats (default: 50ms)
   - **Too low**: High network overhead
   - **Too high**: Slower failure detection
   - **Guideline**: Election timeout / 10 (if election timeout 200ms, heartbeat every 20ms)

3. **Max entries per AppendEntries**: Batch size for log replication (default: 64-256)
   - **Too low**: High RPC overhead (many small batches)
   - **Too high**: High latency (large batches take longer to serialize/deserialize)
   - **Guideline**: Optimize for your workload (large writes: smaller batches; many small writes: larger batches)

4. **Snapshot threshold**: How often to snapshot (default: every 10,000 entries)
   - **Too low**: High snapshot overhead (disk I/O)
   - **Too high**: Slow recovery (long log replay)
   - **Guideline**: Balance recovery time vs snapshot cost (if log replay takes 1min for 10k entries, snapshot every 10k)

**Paxos tuning knobs**:

1. **Proposal number increment**: How much to increment proposal number on retry
   - Larger increment: Less likely to collide with other proposers
   - Smaller increment: Tighter proposal numbering
   - **Guideline**: Increment by number of proposers × safety margin

2. **Leader lease duration**: How long leader can propose without Phase 1 (default: 10 sec)
   - **Too short**: Frequent Phase 1 (higher latency)
   - **Too long**: Slow leader failure detection
   - **Guideline**: 10× election timeout equivalent

3. **Acceptor timeout**: (if used) How long acceptor waits for Phase 2 after Phase 1
   - **Too short**: Proposals abandoned prematurely
   - **Too long**: Slow garbage collection of abandoned proposals

**Byzantine consensus tuning**:

1. **View change timeout**: When to suspect Byzantine primary and change view
   - **Too short**: Frequent view changes (liveness suffers)
   - **Too long**: Tolerating slow/faulty primary for long time
   - **Guideline**: 10× expected commit latency

2. **Batch size**: How many requests to batch per consensus instance
   - Higher batch: Better throughput, higher latency
   - Lower batch: Lower latency, lower throughput

3. **Authentication method**: Signatures vs MACs
   - **Signatures**: Stronger (non-repudiation), slower
   - **MACs**: Faster, weaker (no non-repudiation)
   - **Threshold signatures**: Best of both (aggregate fast, verify fast)

#### Common Problems and Solutions

**Problem 1: Frequent leader elections (term churn)**

**Symptoms**:
- Term number increasing rapidly (>10 per hour)
- Write unavailability during elections
- High commit latency P99

**Causes**:
- Network instability (packet loss, delays)
- Leader overload (CPU, disk I/O, network bandwidth)
- GC pauses (leader appears crashed during long GC)
- Incorrect timeouts (too aggressive)

**Diagnosis**:
- Check heartbeat success rate (should be >99%)
- Check leader CPU/disk/network metrics
- Check GC pause duration (if using Java/Go, check GC logs)
- Compare election timeout with actual network RTT

**Solutions**:
- **Increase election timeout** (if transient delays cause false timeouts)
- **Add capacity to leader** (more CPU, faster disk, higher network bandwidth)
- **Tune GC** (shorter GC pauses, e.g., Java G1GC, Go GOGC)
- **Improve network** (reduce latency, packet loss)
- **Pre-vote optimization** (Raft extension): Candidate checks if it can win election before actually starting one (prevents disruptive elections)

**Problem 2: Slow commits (high commit latency)**

**Symptoms**:
- Commit latency P50/P99 higher than expected
- Throughput lower than expected
- Followers lagging behind leader

**Causes**:
- Slow follower(s) (disk I/O, CPU, network)
- Large batch sizes (serialization overhead)
- Network latency between leader and followers
- Disk fsync latency (commit wait for durable storage)

**Diagnosis**:
- Check per-follower replication lag (identify slow followers)
- Check disk latency (fsync time)
- Check network RTT between leader and followers
- Profile leader CPU usage (is serialization/deserialization bottleneck?)

**Solutions**:
- **Replace slow followers** (upgrade hardware, switch to SSD)
- **Adjust batch sizes** (reduce if latency problem, increase if throughput problem)
- **Async fsync** (if acceptable to lose recent writes on crash—not recommended for critical data)
- **Read-only replicas** (learners, not voters): Don't wait for them to acknowledge
- **Flexible Paxos** (if using Paxos): Reduce Phase 2 quorum size (accept higher Phase 1 cost)

**Problem 3: Split-brain (safety violation)**

**Symptoms**:
- Two nodes both think they're leader
- Conflicting writes accepted
- Data corruption, inconsistency

**Causes**:
- **Fencing failure**: Epoch/term numbers not checked
- **Quorum misconfiguration**: Incorrect quorum size (e.g., 2/4 nodes instead of 3/4)
- **Bug in consensus implementation**: Logic error in leader election or commit protocol

**Diagnosis**:
- Check logs for overlapping leader terms (two leaders with same term)
- Check commit logs for conflicting entries at same index
- Verify quorum configuration (should be majority)

**Prevention**:
- **Fencing tokens**: Always check epoch/term before accepting writes
- **Correct quorum sizes**: Majority (F+1 out of 2F+1) or Byzantine (2F+1 out of 3F+1)
- **Formal verification**: Use TLA+ or similar to verify consensus protocol
- **Jepsen testing**: Test under network partitions, clock skew, node crashes

**Recovery**:
- **If caught early**: Shut down one leader (higher term wins), reconcile logs
- **If data corrupted**: Restore from backup, replay logs, manual reconciliation

**Problem 4: Log divergence (follower logs conflict with leader)**

**Symptoms**:
- Follower logs have entries that differ from leader at same index
- AppendEntries consistency check failing
- Follower cannot catch up

**Causes**:
- **Leader crash before committing**: Uncommitted entries on old leader may differ from new leader
- **Network partition**: Minority leader accepted uncommitted entries, majority elected different leader
- **Bug**: Implementation error in log replication logic

**Diagnosis**:
- Compare logs: Check entries at same index on leader and follower
- Check term numbers: Follower may have entries from old terms that were never committed

**Solution (Raft)**:
- **Leader backs up**: Decrease `nextIndex` for follower, find point where logs match (same term at same index)
- **Overwrite conflicting entries**: Follower deletes conflicting entries, accepts leader's entries
- **Catch up**: Once logs match, follower accepts new entries normally

**This is safe because**: Conflicting entries were never committed (no quorum). Raft's election restriction ensures new leader has all committed entries.

### Case Studies: Consensus in Production

#### Case Study 1: etcd in Kubernetes

**System**: etcd is a distributed key-value store using Raft, serving as Kubernetes' backing store for cluster state.

**Deployment**:
- Typically 3 or 5 nodes (tolerate 1 or 2 failures)
- Deployed in same datacenter (low latency)
- Hardware: SSD (fast fsync), multi-core CPU, 10Gbps network

**Use cases**:
- **Configuration storage**: Kubernetes objects (Pods, Services, ConfigMaps)
- **Coordination**: Leader election for controllers
- **Watches**: Notify clients of changes (event-driven architecture)

**Consensus guarantee vector**: `⟨Global, SS, SER, Fresh(φ), Idem, Auth⟩`

**Production lessons**:

1. **Disk latency dominates**:
   - Commit latency = disk fsync latency (typically 1-10ms on SSD)
   - HDDs are too slow (50-200ms fsync) → use SSDs
   - Network latency is secondary (1-2ms RTT within datacenter)

2. **Write amplification**:
   - Every Kubernetes API write → etcd write
   - Large clusters (1000s of nodes) generate high write load
   - **Solution**: Batch updates, rate limiting, caching

3. **Snapshot management**:
   - Kubernetes generates millions of log entries
   - Must snapshot frequently (default: every 10,000 entries)
   - **Tuning**: More frequent snapshots (shorter recovery) vs disk I/O cost

4. **Watch scalability**:
   - etcd supports watches (long-lived connections for change notifications)
   - Kubernetes controllers watch thousands of objects
   - **Challenge**: Broadcasting changes to all watchers (CPU, network)
   - **Solution**: Efficient indexing, incremental updates

5. **Failure modes**:
   - **Disk full**: Node cannot write log, becomes unavailable → monitor disk usage
   - **Slow disk**: fsync >50ms → commit latency spikes → increase timeout
   - **Network partition**: Minority partition unavailable (CP choice, expected)

**Incident example (2019)**:
- etcd cluster under heavy write load (1000s of writes/sec)
- Disk IOPS exhausted (saturated disk queue)
- Commit latency spiked to 500ms (usually <10ms)
- Election timeouts triggered (followers suspected leader crashed)
- Frequent elections (term churn)
- **Resolution**: Added disk capacity (faster SSD), reduced write rate (batching, caching)

**Evidence view**:
- **Commit certificates**: Quorum of AppendEntries successes (proof of durable log entry)
- **Watch notifications**: Evidence of state change (derived from commit certificates)
- **Lease evidence**: Controllers use etcd leases for leader election (evidence with TTL)

#### Case Study 2: Apache ZooKeeper and the ZAB Protocol

**System**: ZooKeeper is a coordination service using ZAB (ZooKeeper Atomic Broadcast), a Paxos variant.

**Deployment**:
- Typically 3, 5, or 7 nodes (tolerate 1, 2, or 3 failures)
- Used by Hadoop, Kafka, HBase, Solr for coordination
- **Ensemble**: ZooKeeper cluster, quorum-based

**Use cases**:
- **Configuration management**: Distributed config, centralized
- **Naming service**: Service discovery
- **Synchronization**: Distributed locks, barriers
- **Leader election**: For distributed applications

**Consensus guarantee vector**: `⟨Global, Sequential, RA, BS(δ), Idem, Auth⟩`

Note: ZooKeeper provides **sequential consistency** (not linearizable):
- All clients see updates in the same order
- But reads may return stale data (don't require quorum)

**ZAB protocol phases**:

1. **Leader election**: Elect leader using voting (Paxos-like)
2. **Discovery**: New leader synchronizes with followers (finds highest zxid, commits pending proposals)
3. **Broadcast**: Leader broadcasts proposals, waits for quorum acknowledgment

**ZooKeeper's unique properties**:

- **Ephemeral nodes**: Nodes that disappear when client disconnects (used for leader election, presence detection)
- **Watches**: One-time triggers when data changes (event-driven)
- **zxid (ZooKeeper transaction ID)**: 64-bit (epoch + counter), totally ordered (Lamport clock)

**Production lessons**:

1. **Sequential consistency trade-off**:
   - Reads don't require quorum (low latency, high throughput)
   - But reads may be stale (bounded by replication lag)
   - **Use case fit**: Configuration reads (staleness acceptable), writes rare (coordination events)

2. **Session management**:
   - Clients have sessions with timeout (heartbeats)
   - If session expires, ephemeral nodes deleted (evidence of liveness lost)
   - **Challenge**: Network glitches cause false session expiry → leader election churn
   - **Solution**: Increase session timeout (at cost of slower failure detection)

3. **Garbage collection pauses**:
   - ZooKeeper written in Java (GC pauses affect heartbeats)
   - Long GC pause (>500ms) → leader suspected failed → election
   - **Solution**: Tune GC (G1GC, short pause times), increase timeouts

4. **Cascading failures**:
   - Many systems depend on ZooKeeper (Kafka, HBase, etc.)
   - If ZooKeeper unavailable, all dependent systems affected
   - **Single point of failure** (despite being distributed)
   - **Mitigation**: Redundant ZooKeeper ensembles, fallback mechanisms

**Incident example (2014, Yahoo)**:
- ZooKeeper ensemble under heavy load (large Yahoo deployment)
- One node experienced slow disk (HDD, not SSD)
- Slow node became leader (election is random)
- Leader couldn't keep up with writes (disk bottleneck)
- Followers marked leader as failed (timeout)
- New election, different node became leader
- **But**: Old leader didn't realize it was deposed (network glitch)
- **Split-brain risk**: Fencing via zxid prevented actual split-brain (old leader's proposals rejected)
- **Resolution**: 40 minutes of partial unavailability, manual intervention to stabilize

**Evidence view**:
- **zxid**: Evidence of proposal order (epoch + counter, like HLC)
- **Quorum acks**: Evidence of committed proposal (2F+1 servers acknowledged)
- **Session**: Evidence of client liveness (heartbeat-based)
- **Ephemeral node**: Evidence of client presence (lifecycle tied to session)

#### Case Study 3: CockroachDB Multi-Raft Architecture

**System**: CockroachDB is a distributed SQL database using Raft for replication, with a twist—**Multi-Raft** (many Raft groups, one per range).

**Architecture**:
- Data partitioned into **ranges** (~64MB each)
- Each range is a Raft group (leader + followers)
- Thousands of Raft groups per cluster (scaling consensus)
- HLC timestamps for causality (from Chapter 2)

**Consensus guarantee vector** (per range): `⟨Range, Lx, SI, Fresh(φ), Idem, Auth⟩`

- **Scope**: Range (not global—each range has independent consensus)
- **Order**: Lx (linearizable per range)
- **Visibility**: SI (snapshot isolation across ranges)
- **Recency**: Fresh(φ) (commit certificate per range write)

**Multi-Raft benefits**:

1. **Scalability**: Consensus load distributed across many groups (not single leader bottleneck)
2. **Fault isolation**: Range failure doesn't affect other ranges
3. **Load balancing**: Ranges can have different leaders (distribute load)

**Challenges**:

1. **Distributed transactions across ranges**:
   - Transaction touches multiple ranges (each with own Raft group)
   - Need distributed commit protocol (2PC) across Raft groups
   - **Solution**: Transaction coordinator uses Raft for commit decision

2. **Range splits/merges**:
   - As data grows, ranges split (one Raft group becomes two)
   - As data shrinks, ranges merge (two groups become one)
   - Must safely reconfigure Raft groups (joint consensus)

3. **Leader placement**:
   - Want leaders near clients (low latency)
   - But also need load balancing
   - **Solution**: Leaseholder (leader for reads) vs Raft leader (leader for consensus)

**Production lessons**:

1. **Lease optimization**:
   - **Raft leader**: Handles consensus (log replication)
   - **Leaseholder**: Handles reads (may be different node from Raft leader)
   - Leaseholder can serve reads without consensus (using closed timestamps from Chapter 2)
   - **Trade-off**: Faster reads (no consensus) vs weaker guarantees (bounded staleness)

2. **Joint consensus for range splits**:
   - When splitting range [A, B) into [A, M) and [M, B):
   - Use joint consensus: Old members + new members must both approve
   - Ensures safety during split
   - Once split committed, new ranges operate independently

3. **Follower reads**:
   - Followers serve reads using closed timestamps (from Chapter 2)
   - Staleness bound: ~200ms (closed timestamp interval)
   - **Benefit**: Read load distributed (not just leader)
   - **Trade-off**: Bounded staleness (not linearizable)

**Guarantee vector downgrade** (follower read):
`⟨Range, Lx, SI, Fresh(φ), Idem, Auth⟩` → `⟨Range, Lx, SI, BS(200ms), Idem, Auth⟩`

**Evidence view**:
- **Per-range commit certificates**: Each Raft group generates independent evidence
- **HLC timestamps**: Causal evidence across ranges (from Chapter 2)
- **Closed timestamps**: Evidence of replication progress (enables follower reads)
- **Transaction record**: Evidence of distributed transaction commit (stored in Raft log)

#### Case Study 4: Kafka's Evolution from ZooKeeper to KRaft

**System**: Apache Kafka is a distributed streaming platform, originally relying on ZooKeeper for metadata management. In 2020, Kafka introduced **KRaft** (Kafka Raft) to remove ZooKeeper dependency.

**Before KRaft (with ZooKeeper)**:
- ZooKeeper stores metadata (topic configs, partition assignments, controller leadership)
- Kafka controller (elected via ZooKeeper) manages cluster metadata
- **Problem**: ZooKeeper is external dependency (operational overhead, scaling limits)

**After KRaft (Kafka's own Raft)**:
- Kafka brokers run Raft consensus internally for metadata
- **Controller quorum**: 3-5 brokers run Raft (metadata controllers)
- Metadata stored in Kafka's own log (self-hosting)

**Benefits of KRaft**:

1. **Simpler operations**: One system to operate (not Kafka + ZooKeeper)
2. **Better scalability**: Kafka can scale to millions of partitions (ZooKeeper limited scalability)
3. **Faster metadata updates**: Raft log replication faster than ZooKeeper watches
4. **Cleaner architecture**: Metadata and data in same system

**Consensus guarantee vector** (metadata): `⟨Global, SS, SER, Fresh(φ), Idem, Auth⟩`

**Production lessons (from KRaft migration)**:

1. **Metadata as log**:
   - Metadata changes (create topic, reassign partition) are log entries
   - Controllers replicate log using Raft
   - Brokers consume metadata log (learn cluster state)
   - **Benefit**: Metadata replication = log replication (unified approach)

2. **Controller quorum**:
   - 3 or 5 brokers designated as controllers (run Raft)
   - Other brokers are observers (consume metadata log, don't vote)
   - **Benefit**: Quorum overhead isolated to few nodes (not all brokers)

3. **Migration complexity**:
   - Migrating from ZooKeeper to KRaft required dual-mode support
   - Kafka had to support both ZooKeeper and KRaft during transition
   - **Lesson**: Consensus protocol changes are hard (can't just switch overnight)

4. **Testing consensus changes**:
   - Extensive testing with Jepsen (partition tolerance, crash failures)
   - Formal verification (TLA+ model of KRaft protocol)
   - Gradual rollout (opt-in for early adopters)

**Evidence view**:
- **Metadata log**: Evidence of cluster configuration (topic assignments, broker membership)
- **Commit certificates**: Quorum of controllers acknowledged metadata change
- **Epoch numbers**: Evidence of controller leadership (fencing old controllers)
- **Metadata cache**: Brokers' local view of metadata (derived from log, with bounded staleness)

---

## Synthesis: The Nature of Agreement

### Mental Models for Consensus

**1. Consensus as Voting**

The most intuitive model: Consensus is a democratic vote.

- **Proposals are candidates**: Different nodes propose different values (like candidates in election)
- **Acceptors/Voters**: Nodes cast votes for proposals
- **Majority determines winner**: Proposal with quorum of votes is chosen
- **Tie-breaking**: Proposal numbers ensure total order (higher number wins)

**Use this model for**: Explaining consensus to non-experts, reasoning about quorum requirements.

**2. Consensus as Evidence Generation**

The evidence-based model (this book's approach):

- **Proposals are uncertain claims**: "I believe X=5"
- **Votes are evidence**: Each vote is a piece of evidence supporting the claim
- **Quorum is sufficient proof**: Majority of votes proves the claim
- **Decision is proven fact**: "X=5 is chosen, proven by quorum certificate"

**Use this model for**: Designing systems, debugging failures, reasoning about safety.

**3. Consensus as State Machine Replication**

The operational model:

- **Goal**: All replicas have identical state machines
- **Method**: Agree on sequence of inputs (log entries)
- **Result**: Deterministic state machines produce same outputs
- **Consensus**: Ensure all replicas see same input sequence

**Use this model for**: Implementing databases, understanding log replication.

**4. Consensus as Barrier Synchronization**

The synchronization model:

- **Problem**: Distributed processes must coordinate action
- **Solution**: Use consensus to agree on when/what to do
- **Barrier**: No process proceeds until quorum agrees
- **Release**: Once quorum agrees, all proceed

**Use this model for**: Distributed algorithms, coordination primitives.

### Design Principles

**1. Separate safety from liveness**

Safety (never violate invariants) and liveness (eventually make progress) are distinct concerns.

- **Safety**: Never choose two different values (AGREEMENT, UNIQUENESS)
- **Liveness**: Eventually choose some value (TERMINATION)
- **Trade-off**: In practice, sacrifice liveness (become unavailable) to preserve safety (remain consistent)

**Guideline**: Always preserve safety. Liveness is optional (can be sacrificed during failures).

**2. Make evidence explicit**

Don't rely on implicit assumptions—make evidence (votes, certificates) explicit and verifiable.

- **Quorum certificates**: Explicit proof of agreement (majority accepts)
- **Epoch/term numbers**: Explicit evidence of leadership generation (fencing)
- **Commit index**: Explicit evidence of how much log is durable

**Guideline**: Every decision must be backed by verifiable evidence (quorum certificate).

**3. Preserve invariants at all costs**

Identify core invariants (UNIQUENESS, AGREEMENT) and never violate them, even during failures.

- **Quorum requirement**: Cannot decide without quorum (preserve UNIQUENESS)
- **Fencing**: Cannot accept stale proposals (preserve LEADER UNIQUENESS)
- **Log matching**: Cannot apply conflicting entries (preserve STATE MACHINE SAFETY)

**Guideline**: If invariant cannot be preserved, enter degraded/floor mode (refuse to decide).

**4. Optimize the common case**

Design for normal operation (Target mode), not just failures.

- **Multi-Paxos**: Skip Phase 1 when leader is stable (1 RTT instead of 2)
- **Raft**: Strong leader (simpler protocol for common case)
- **Batching**: Amortize consensus cost over multiple requests

**Guideline**: Make happy path fast, tolerate occasional slow path (leader election, recovery).

**5. Plan for failures**

Failures are not rare—they're the norm in large-scale systems.

- **Timeouts**: Detect failures (but tune carefully to avoid false positives)
- **Retries**: Clients retry (but use idempotency to avoid duplicate execution)
- **Elections**: Automatically elect new leader (but use randomization to avoid split votes)
- **Fencing**: Prevent stale leaders (use epoch/term numbers)

**Guideline**: Test under failures (network partitions, node crashes, slow nodes).

### Operational Wisdom

**Monitor everything**:
- Leader stability (term numbers, election frequency)
- Quorum availability (how many nodes reachable)
- Commit latency (P50, P99, P999)
- Replication lag (how far behind followers are)
- Evidence health (lease expiry, certificate freshness)

**Tune carefully**:
- Timeouts (balance false positives vs failure detection speed)
- Batch sizes (balance latency vs throughput)
- Snapshot frequency (balance recovery time vs I/O cost)
- Start conservative (longer timeouts), tune based on metrics

**Test fault scenarios**:
- Network partitions (split cluster, observe CP/AP behavior)
- Node crashes (kill leader, verify new leader elected)
- Slow nodes (inject latency, verify cluster adapts)
- Clock skew (if using physical time, verify fencing works)
- Use Jepsen, chaos engineering tools

**Understand failure modes**:
- No quorum → unavailable (expected in minority partition)
- Slow leader → high latency (replace leader or add capacity)
- Split votes → transient unavailability (elections retry, randomization helps)
- Disk full → node failure (monitor disk usage)

**Have recovery procedures**:
- Lost quorum → investigate network, restart nodes, restore from backup if needed
- Log divergence → leader backs up follower, overwrites conflicting entries
- Split-brain (if happens, despite fencing) → manual reconciliation, restore from backup

---

## Exercises

### Conceptual Exercises

1. **Prove Paxos Safety**
   - Show that if value `v` is chosen (quorum of acceptors accepted), then no conflicting value `w ≠ v` can be chosen.
   - Use quorum intersection property: Any two quorums overlap.

2. **Explain why 2F+1 nodes are needed to tolerate F crash failures**
   - Show that with 2F nodes, you cannot distinguish between F crashed and F alive (ambiguous quorum).
   - Show that with 2F+1 nodes, majority (F+1) ensures at least one correct node in any quorum.

3. **Explain why 3F+1 nodes are needed to tolerate F Byzantine failures**
   - Show that with 3F nodes, F Byzantine nodes + F correct nodes could vote, giving no majority of correct nodes.
   - Show that with 3F+1 nodes, 2F+1 quorum ensures at least F+1 correct nodes (majority of correct).

4. **Design consensus for specific use case: Distributed queue**
   - Multiple workers dequeue tasks from shared queue
   - Ensure each task dequeued exactly once (no duplicates)
   - Use consensus to assign tasks to workers (leader assigns, log replicates assignments)
   - Handle worker failures (task reassignment)

5. **Analyze Byzantine fault scenario: Equivocation attack**
   - Byzantine node sends different messages to different replicas
   - Example: Tells replica A "vote for value X", tells replica B "vote for value Y"
   - Show how PBFT prevents this (all messages signed, replicas compare signed messages, detect equivocation)

### Implementation Projects

1. **Implement basic Paxos**
   - Roles: Proposer, Acceptor, Learner
   - Phase 1: Prepare, Promise
   - Phase 2: Accept, Learn
   - Handle concurrent proposers (higher proposal number wins)
   - Test: Simulate 3 acceptors, 2 proposers, verify agreement

2. **Build Raft with leader election**
   - Implement term numbers, election timeouts, RequestVote RPC
   - Randomized timeouts (prevent split votes)
   - Test: Kill leader, verify new leader elected within 2× election timeout

3. **Add log replication to Raft**
   - Implement AppendEntries RPC, log consistency check
   - Commit rule (majority replication + current term entry)
   - Test: Replicate log entries, verify all followers converge

4. **Implement view change in PBFT**
   - Detect primary failure (timeout)
   - Collect VIEW-CHANGE messages (2F+1 quorum)
   - New primary sends NEW-VIEW with proof
   - Test: Kill primary, verify view change completes, new primary takes over

5. **Build consensus testing framework**
   - Simulate network (send, delay, drop messages)
   - Inject failures (crash nodes, partition network)
   - Check invariants (agreement, validity, integrity)
   - Visualize execution (message traces, state transitions)

### Production Analysis

1. **Analyze etcd metrics from your Kubernetes cluster**
   - Collect metrics: commit latency, election frequency, disk fsync time
   - Identify bottlenecks (disk I/O, network, CPU)
   - Tune parameters (snapshot frequency, heartbeat interval)

2. **Debug split-brain scenario in test environment**
   - Set up 3-node Raft cluster
   - Partition network (1 node | 2 nodes)
   - Observe: Majority (2 nodes) continues, minority (1 node) unavailable
   - Verify: No conflicting decisions (safety preserved)

3. **Tune consensus parameters for workload**
   - Measure baseline: commit latency, throughput
   - Adjust election timeout (test different values: 100ms, 200ms, 500ms)
   - Adjust batch size (test: 1, 10, 100 entries per AppendEntries)
   - Find optimal parameters for your workload (latency vs throughput trade-off)

4. **Design monitoring dashboard for consensus health**
   - Metrics: leader stability, quorum status, commit latency (P50, P99), replication lag
   - Alerts: quorum lost, high commit latency, frequent elections
   - Visualization: timeseries graphs, current cluster state, recent events

5. **Create chaos tests for consensus system**
   - Test scenarios:
     - Kill leader (verify new leader elected)
     - Partition network (verify minority unavailable, majority continues)
     - Slow node (inject 500ms delay, verify cluster adapts)
     - Disk full (fill disk, verify node becomes unavailable)
   - Use tools: Jepsen, Chaos Mesh, Toxiproxy

---

## Key Takeaways

### Core Insights

1. **Consensus is about converting uncertainty into certainty through evidence**
   - Proposals are uncertain claims
   - Votes are evidence
   - Quorum certificates are proof of agreement

2. **Quorum intersection is the fundamental safety mechanism**
   - Any two quorums must overlap
   - Ensures conflicting decisions cannot both have quorum certificates
   - Majority (F+1 out of 2F+1) for crash failures
   - 2F+1 out of 3F+1 for Byzantine failures

3. **Two-phase structure is common across protocols**
   - Phase 1: Seek permission (gather evidence it's safe to propose)
   - Phase 2: Propose value (gather evidence of agreement)
   - Optimization: Skip Phase 1 when leader is stable (Multi-Paxos, Raft)

4. **Safety and liveness are separate concerns**
   - Safety: Never violate invariants (AGREEMENT, UNIQUENESS)
   - Liveness: Eventually make progress (TERMINATION)
   - Trade-off: Sacrifice liveness (unavailable) to preserve safety (consistent)

5. **Leader-based vs leaderless trade-offs**
   - **Leader-based (Raft, Multi-Paxos)**: Simpler protocol, single bottleneck, efficient for many operations
   - **Leaderless (EPaxos)**: No bottleneck, more complex, good for commutative operations
   - Most systems use leader-based (simplicity wins)

6. **Byzantine consensus is expensive**
   - Requires 3F+1 nodes (vs 2F+1 for crash failures)
   - Three phases (vs two for crash consensus)
   - Cryptographic signatures (computational overhead)
   - Use only when necessary (untrusted participants, e.g., blockchain)

7. **Production requires careful tuning and monitoring**
   - Timeouts: Balance false positives vs failure detection speed
   - Batch sizes: Balance latency vs throughput
   - Hardware: Fast disks (SSD), low-latency network
   - Monitoring: Leader stability, commit latency, replication lag, quorum status

### The Evidence-Based View

**Consensus as evidence lifecycle**:

```
Proposal (uncertain claim)
  ↓
Voting (evidence generation)
  ↓
Quorum check (validation)
  ↓
Decision (certain fact, backed by certificate)
  ↓
Execution (apply to state machine)
  ↓
Expiry (term/view change)
  ↓
Renewal (new round)
```

**Evidence types**:
- **Promise certificates**: Permission to propose
- **Accept certificates**: Agreement on value
- **Vote certificates**: Leadership
- **Commit certificates**: Durability
- **Term/epoch numbers**: Fencing (prevents stale leaders)

**Evidence properties** (from lifecycle framework):
- **Scope**: What it applies to (proposal, term, log entry)
- **Lifetime**: How long valid (until term change, permanent for commits)
- **Binding**: Who generated it (acceptor, voter, replica)
- **Transitivity**: Can it be forwarded? (certificates are transitive)

### Practical Guidelines

**When to use consensus**:
- Need strong consistency (linearizability, serializability)
- Coordination primitives (locks, leader election, barriers)
- State machine replication (databases, message queues)
- Configuration management (cluster membership, service discovery)

**When NOT to use consensus**:
- High-throughput, low-latency workloads (consensus adds 1-2 RTT)
- Acceptable to have eventual consistency (use CRDTs, anti-entropy)
- Single-datacenter with trusted network (can use simpler replication)

**Deployment best practices**:
- Use dedicated consensus service (etcd, ZooKeeper, Consul) for coordination
- Embed consensus (Raft, Multi-Paxos) for state machine replication in databases
- Deploy odd number of nodes (3, 5, 7) to avoid ties
- Deploy across failure domains (racks, zones) for fault tolerance
- Use fast disks (SSD) for log storage (fsync latency dominates commit latency)
- Monitor continuously (leader stability, commit latency, quorum status)

---

## Further Reading

### Foundational Papers

**Paxos**:
- Lamport, Leslie. "The Part-Time Parliament" (TOCS 1998) — Original Paxos paper (in story form)
- Lamport, Leslie. "Paxos Made Simple" (ACM SIGACT News 2001) — Clearer explanation
- van Renesse, Robbert and Altinbuken, Deniz. "Paxos Made Moderately Complex" (ACM Computing Surveys 2015) — Detailed algorithm and implementation guide

**Raft**:
- Ongaro, Diego and Ousterhout, John. "In Search of an Understandable Consensus Algorithm (Extended Version)" (USENIX ATC 2014) — The Raft paper
- raft.github.io — Interactive visualization, implementations in many languages

**Byzantine Consensus**:
- Castro, Miguel and Liskov, Barbara. "Practical Byzantine Fault Tolerance" (OSDI 1999) — PBFT protocol
- Yin, Maofan et al. "HotStuff: BFT Consensus with Linearity and Responsiveness" (PODC 2019) — Modern Byzantine consensus
- Buchman, Ethan. "Tendermint: Byzantine Fault Tolerance in the Age of Blockchains" (2016) — BFT for blockchains

**Advanced Topics**:
- Howard, Heidi and Mortier, Richard. "Paxos vs Raft: Have we reached consensus on distributed consensus?" (PaPoC 2020) — Comparison of protocols
- Moraru, Iulian et al. "There Is More Consensus in Egalitarian Parliaments" (SOSP 2013) — EPaxos (leaderless consensus)
- Howard, Heidi et al. "Flexible Paxos: Quorum Intersection Revisited" (2016) — Flexible quorum requirements

### Production Systems and Case Studies

**etcd**:
- etcd documentation: etcd.io — Raft-based distributed key-value store
- "etcd Raft Library Design" (CoreOS blog) — Implementation details

**ZooKeeper**:
- Hunt, Patrick et al. "ZooKeeper: Wait-free coordination for Internet-scale systems" (USENIX ATC 2010) — ZooKeeper design
- ZooKeeper documentation — zookeeper.apache.org

**CockroachDB**:
- "Consensus in CockroachDB" (Cockroach Labs blog) — Multi-Raft architecture
- "Living Without Atomic Clocks" (Cockroach Labs blog) — HLC for causality

**Kafka KRaft**:
- "KIP-500: Replace ZooKeeper with a Self-Managed Metadata Quorum" — Kafka's move to internal Raft

**Spanner**:
- Corbett, James et al. "Spanner: Google's Globally-Distributed Database" (OSDI 2012) — TrueTime and consensus

### Incident Reports and Postmortems

- "etcd Split Brain" (2015) — Network partition, quorum behavior
- "MongoDB Primary Election Stall" (2019) — Election taking 47 seconds
- "ZooKeeper Cascading Failure at Yahoo" (2014) — Slow node becoming leader

### Testing and Verification

**Testing**:
- Kingsbury, Kyle (Aphyr). "Jepsen: On the Perils of Network Partitions" (2013+) — Testing consensus under failures (jepsen.io)
- "Call Me Maybe: etcd and Consul" — Jepsen tests for popular consensus systems

**Formal Verification**:
- Newcombe, Chris et al. "How Amazon Web Services Uses Formal Methods" (CACM 2015) — TLA+ for verifying distributed systems
- Raft TLA+ specification — github.com/ongardie/raft.tla

### Books

- van Steen, Maarten and Tanenbaum, Andrew. "Distributed Systems" (3rd ed, 2017) — Chapter 8: Distributed Transactions (consensus)
- Cachin, Christian et al. "Introduction to Reliable and Secure Distributed Programming" (2011) — Formal treatment of consensus
- Kleppmann, Martin. "Designing Data-Intensive Applications" (2017) — Chapter 9: Consistency and Consensus
- Wattenhofer, Roger. "Distributed Ledger Technology: The Science of the Blockchain" (2020) — Byzantine consensus, blockchain

### Talks and Tutorials

- Ongaro, Diego. "Consensus: Bridging Theory and Practice" (PhD thesis, 2014) — Comprehensive Raft discussion
- Howard, Heidi. "Distributed Consensus: Making Impossible Possible" (Strange Loop 2019) — Accessible overview
- Kleppmann, Martin. "Please Stop Calling Databases CP or AP" (2015 blog post) — CAP and consensus nuances

---

## Cross-Chapter Connections

### From Chapter 1 (Impossibility Results)

- **FLP impossibility** says deterministic consensus is impossible in asynchronous systems → Paxos/Raft circumvent by assuming partial synchrony
- **Lower bounds** (f+1 rounds, O(n) messages) are realized in Paxos (2 phases), Raft (1 phase after leader election)
- **CAP theorem** forces CP or AP choice → Consensus protocols choose CP (unavailable during partition, but consistent)

### From Chapter 2 (Time, Order, Causality)

- **Term/epoch numbers** are logical clocks (Lamport clocks) that order proposals and fence stale leaders
- **Commit timestamps** (Raft log entries, Paxos proposals) use logical or hybrid time
- **Leader leases** have expiration times, requiring time synchronization (or conservative timeouts)

### To Chapter 4 (Replication)

- **Consensus enables state machine replication**: Agree on log order → replicas converge to same state
- **Replication strategies** use consensus for consistency (synchronous replication = consensus on commit)
- **Quorum-based replication** (like Dynamo) is related but weaker than consensus (eventual consistency, not linearizability)

### To Chapter 5 (Transactions)

- **Distributed transactions** need consensus for atomic commit (two-phase commit coordinator uses consensus to decide commit/abort)
- **MVCC timestamps** use consensus for globally ordered timestamps (Spanner uses Paxos + TrueTime)
- **Serializability** requires consensus on transaction order

### To Chapter 6 (Storage)

- **Write-ahead log (WAL)** is replicated using consensus (Raft log = WAL)
- **Log compaction** (snapshotting) uses consensus to agree on snapshot points
- **Durable commits** require fsync (consensus commit latency = disk fsync time)

### To Chapter 7 (Cloud-Native)

- **Service discovery** uses consensus (etcd, Consul for service registry)
- **Leader election for microservices** uses consensus primitives
- **Configuration management** (Kubernetes API server backed by etcd) uses consensus

### To Chapter 8 (Failure Handling)

- **Consensus failure modes** (no quorum, frequent elections) are instances of general failure patterns
- **Mode matrix** (Target, Degraded, Floor, Recovery) applies to consensus systems
- **Evidence-based failure detection** (heartbeats, votes, quorum checks) is used throughout consensus protocols

---

## Chapter Summary

### The Irreducible Truth

**"Consensus is the process of converting uncertain proposals into certain decisions by collecting sufficient evidence—votes from a quorum—such that conflicting decisions are impossible due to quorum intersection. It is the foundation of coordination in distributed systems, enabling agreement despite failures."**

### The Evidence-Based Mental Model

Every consensus protocol is an evidence-generating machine:

**Proposal** (uncertain claim)
  ↓ **Phase 1** (gather evidence it's safe)
**Promise quorum** (permission certificate)
  ↓ **Phase 2** (gather evidence of agreement)
**Accept quorum** (decision certificate)
  ↓ **Learning**
**Decided value** (certain fact)

**Guarantee vectors for consensus**:

| Operation | Guarantee Vector |
|-----------|------------------|
| Raft write (committed) | `⟨Global, SS, SER, Fresh(φ), Idem, Auth⟩` |
| Raft follower read | `⟨Range, SS, SI, BS(δ), Idem, Auth⟩` |
| Paxos single-value | `⟨Object, SS, SER, Fresh(φ), Idem, Auth⟩` |
| Byzantine (PBFT) | `⟨Global, SS, SER, Fresh(φ), Idem, Signed⟩` |

### What's Next

We've established how to achieve agreement through consensus. But consensus is expensive—it requires multiple round-trips, quorum communication, and durable storage. Not every operation needs consensus.

Chapter 4 explores **Replication**—how to maintain multiple copies of data for fault tolerance and performance, using a spectrum of consistency models from strong (consensus-based) to weak (eventual consistency). We'll see when consensus is necessary (strong consistency) and when weaker models suffice (high availability, low latency).

Consensus provides the foundation. Replication builds practical systems on top.

---

**Context Capsule for Next Chapter**:
```
{
  invariant: CONSISTENCY (replica agreement),
  evidence: Quorum certificates (consensus) or anti-entropy (eventual),
  boundary: Chapter transition (from agreement to replication),
  mode: Target,
  fallback: Use consensus when strong consistency needed,
  trace: {
    chapter: 3,
    concepts: [
      quorum intersection,
      evidence generation,
      leader-based replication,
      term numbers for fencing,
      two-phase structure
    ]
  }
}
```
