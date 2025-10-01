# Chapter 10: The State of State

## Managing State in Distributed Systems

> "State is the source of all complexity in distributed systems—it's what makes them distributed rather than merely parallel."

State management is the fundamental challenge in distributed systems. Every other problem—consensus, replication, consistency—exists because we need to manage state across multiple nodes. This chapter explores how modern systems handle state at scale.

## Introduction: The State Paradox

Consider this paradox: we build distributed systems to be stateless for scalability, then spend enormous effort managing the state we claimed not to have. The truth is, state never disappears—it just moves. Understanding where it moves and how to manage it there is the key to building successful distributed systems.

### The State Diaspora

State has migrated over the decades:
- **1980s**: State in the database
- **1990s**: State in the application server session
- **2000s**: State in distributed caches
- **2010s**: State in event logs
- **2020s**: State everywhere (edge, streams, meshes)

Each migration solved previous problems while creating new ones. Today's systems must handle state at every layer, from edge functions to global databases.

## Part 1: INTUITION (First Pass)

### The Shopping Cart Journey

Let's follow a shopping cart through a modern e-commerce system to understand state challenges:

**9:00 AM - Desktop Browser**
Sarah adds a book to her cart. The state could be:
- In a browser cookie (client-side)
- In server session (memory)
- In Redis cache (distributed)
- In database (persistent)
- In event stream (log)

**12:30 PM - Mobile App**
Sarah opens the app at lunch. The cart should be there. This requires:
- State synchronization across devices
- Consistent view despite different apps
- Handling concurrent modifications

**3:00 PM - Network Partition**
The data center experiences a split. Sarah's cart exists in two versions:
- Version A: Book + headphones (added on mobile)
- Version B: Book + coffee mug (added on desktop)

**6:00 PM - Checkout**
Sarah completes purchase. The system must:
- Merge cart versions (conflict resolution)
- Ensure exactly-once payment (idempotency)
- Update inventory (distributed transaction)
- Send confirmation (state machine)

This simple journey touches every state management challenge we'll explore.

### The Bank Account Problem

Consider two ATM withdrawals happening simultaneously:

```
Account balance: $1000

ATM 1 (New York)          ATM 2 (Los Angeles)
Check balance: $1000       Check balance: $1000
Withdraw $800              Withdraw $500
Update balance: $200       Update balance: $500
```

Without proper state management, the bank loses $300. This is why banks spend millions on state consistency.

### The Social Media Timeline

When you post on social media:
1. Your post is written to multiple replicas
2. It's added to your timeline (your state)
3. It's pushed to followers' timelines (their state)
4. It's indexed for search (search state)
5. It's cached at edge locations (edge state)
6. Likes/comments create new state

A single action creates state in dozens of systems. How do we keep it all consistent?

## Part 2: UNDERSTANDING (Second Pass)

### Stateless vs Stateful Services

#### The Stateless Illusion

```python
class StatelessService:
    """Appears stateless but state is everywhere"""

    def process_request(self, request):
        # State in database
        user = self.database.get_user(request.user_id)

        # State in cache
        preferences = self.cache.get(f"prefs:{user.id}")

        # State in external service
        recommendations = self.ml_service.get_recommendations(user)

        # State in message queue
        self.queue.publish(UserActivityEvent(user.id, request))

        # State in metrics
        self.metrics.increment("requests", tags={"user": user.id})

        # "Stateless" processing
        result = self.business_logic(user, preferences, recommendations)

        return result
```

The service has no local state, but it touches state everywhere. "Stateless" really means "state is someone else's problem."

#### Embracing Stateful Services

```python
class StatefulService:
    """Explicitly manages local state"""

    def __init__(self):
        self.local_state = {}  # In-memory state
        self.wal = WriteAheadLog()  # Durability
        self.replicas = []  # Replication

    def process_request(self, request):
        # Check local state first
        if request.key in self.local_state:
            return self.local_state[request.key]

        # State is local and fast
        result = self.compute(request)

        # Persist and replicate
        self.wal.append(WriteEntry(request.key, result))
        self.replicate_to_followers(request.key, result)

        self.local_state[request.key] = result
        return result
```

Benefits of stateful services:
- **Lower latency**: No network calls for state
- **Better locality**: Related state stays together
- **Simplified architecture**: Fewer moving parts
- **Cost efficiency**: Less network traffic

Challenges:
- **Deployment complexity**: State migration during updates
- **Failure handling**: State recovery after crashes
- **Scaling**: Resharding state
- **Debugging**: State adds complexity

### State Machine Replication

#### The Deterministic State Machine

```python
class DeterministicStateMachine:
    """Same inputs always produce same outputs"""

    def __init__(self):
        self.state = InitialState()
        self.log = []

    def apply_command(self, command):
        """Deterministically apply command"""
        # No randomness
        # No timestamps
        # No external calls
        # Pure function of state and command

        old_state = self.state.copy()

        if command.type == "increment":
            self.state.counter += command.value
        elif command.type == "multiply":
            self.state.counter *= command.value

        # Log for replication
        self.log.append(LogEntry(
            index=len(self.log),
            command=command,
            old_state=old_state,
            new_state=self.state.copy()
        ))

        return self.state
```

#### Replication Protocol

```python
class ReplicatedStateMachine:
    """Replicate state machine across nodes"""

    def __init__(self):
        self.state_machine = DeterministicStateMachine()
        self.consensus = RaftConsensus()

    def execute_command(self, command):
        """Execute via consensus"""
        # Achieve consensus on order
        index = self.consensus.append(command)

        # Wait for commit
        self.consensus.wait_for_commit(index)

        # Apply to state machine
        result = self.state_machine.apply_command(command)

        # All replicas will apply in same order
        # Determinism ensures same state
        return result
```

### Distributed Transactions in 2025

#### The 2PC Protocol (Still Relevant)

```python
class TwoPhaseCommit:
    """Classic 2PC for distributed transactions"""

    def execute_transaction(self, operations):
        transaction_id = generate_txn_id()
        participants = self.identify_participants(operations)

        # Phase 1: Prepare
        prepare_results = []
        for participant in participants:
            result = participant.prepare(transaction_id, operations)
            prepare_results.append(result)

            if result.status != "PREPARED":
                # Someone can't commit, abort all
                self.abort_all(participants, transaction_id)
                return TransactionAborted()

        # Phase 2: Commit
        for participant in participants:
            participant.commit(transaction_id)

        return TransactionCommitted()

    def abort_all(self, participants, transaction_id):
        """Abort on all participants"""
        for participant in participants:
            try:
                participant.abort(transaction_id)
            except Exception as e:
                # Log for manual cleanup
                self.log_abort_failure(participant, transaction_id, e)
```

#### Modern Distributed Transactions

**Spanner-Style Transactions**
```python
class SpannerTransaction:
    """TrueTime-based transactions"""

    def execute(self, operations):
        # Get global timestamp
        timestamp = TrueTime.now()

        # Read at timestamp
        reads = self.perform_reads(operations, timestamp)

        # Compute writes
        writes = self.compute_writes(reads, operations)

        # Two-phase commit with timestamp
        commit_timestamp = TrueTime.now()

        # Wait out uncertainty
        TrueTime.wait_until_after(commit_timestamp)

        # Now safe to commit
        self.commit_writes(writes, commit_timestamp)
```

**Calvin-Style Deterministic Transactions**
```python
class CalvinTransaction:
    """Deterministic transaction execution"""

    def execute(self, transaction):
        # Pre-determine order
        sequence_number = self.sequencer.get_next_sequence()

        # Broadcast to all replicas
        self.broadcast_transaction(sequence_number, transaction)

        # Everyone executes in same order
        # Determinism ensures same result
        self.execute_deterministic(sequence_number, transaction)
```

### Saga Patterns

#### Choreographed Sagas

```python
class ChoreographedSaga:
    """Each service knows what to do next"""

    def start_order_saga(self, order):
        # First service starts the saga
        self.inventory_service.reserve_items(
            order_id=order.id,
            items=order.items,
            on_success=lambda: self.payment_service.charge_customer(
                order_id=order.id,
                amount=order.total,
                on_success=lambda: self.shipping_service.schedule_delivery(
                    order_id=order.id,
                    address=order.address,
                    on_success=lambda: self.notification_service.send_confirmation(order.id),
                    on_failure=lambda: self.compensate_from_shipping(order.id)
                ),
                on_failure=lambda: self.compensate_from_payment(order.id)
            ),
            on_failure=lambda: self.compensate_from_inventory(order.id)
        )
```

#### Orchestrated Sagas

```python
class OrchestratedSaga:
    """Central orchestrator manages the saga"""

    def __init__(self):
        self.saga_log = SagaLog()  # Persistent saga state

    def execute_order_saga(self, order):
        saga_id = self.start_saga(order)

        try:
            # Step 1: Reserve inventory
            self.saga_log.record(saga_id, "RESERVE_INVENTORY", "STARTED")
            inventory_result = self.inventory_service.reserve(order.items)
            self.saga_log.record(saga_id, "RESERVE_INVENTORY", "COMPLETED", inventory_result)

            # Step 2: Process payment
            self.saga_log.record(saga_id, "PROCESS_PAYMENT", "STARTED")
            payment_result = self.payment_service.charge(order.total)
            self.saga_log.record(saga_id, "PROCESS_PAYMENT", "COMPLETED", payment_result)

            # Step 3: Schedule shipping
            self.saga_log.record(saga_id, "SCHEDULE_SHIPPING", "STARTED")
            shipping_result = self.shipping_service.schedule(order)
            self.saga_log.record(saga_id, "SCHEDULE_SHIPPING", "COMPLETED", shipping_result)

            # Success!
            self.saga_log.record(saga_id, "SAGA", "COMPLETED")

        except Exception as e:
            # Compensate in reverse order
            self.compensate_saga(saga_id)
            raise SagaFailed(saga_id, e)

    def compensate_saga(self, saga_id):
        """Run compensating transactions"""
        completed_steps = self.saga_log.get_completed_steps(saga_id)

        for step in reversed(completed_steps):
            if step.name == "SCHEDULE_SHIPPING":
                self.shipping_service.cancel(step.result)
            elif step.name == "PROCESS_PAYMENT":
                self.payment_service.refund(step.result)
            elif step.name == "RESERVE_INVENTORY":
                self.inventory_service.release(step.result)
```

### Session State Management

#### Client-Side Sessions

```python
class ClientSideSession:
    """State stored in client (cookie/localStorage)"""

    def create_session(self, user_data):
        # Encrypt and sign
        session_data = {
            "user_id": user_data.id,
            "permissions": user_data.permissions,
            "expires": time.time() + 3600
        }

        encrypted = self.encrypt(json.dumps(session_data))
        signature = self.sign(encrypted)

        return {
            "token": base64.encode(encrypted),
            "signature": signature
        }

    def validate_session(self, token, signature):
        # Verify signature
        if not self.verify_signature(token, signature):
            raise InvalidSession("Signature mismatch")

        # Decrypt and parse
        decrypted = self.decrypt(base64.decode(token))
        session_data = json.loads(decrypted)

        # Check expiration
        if session_data["expires"] < time.time():
            raise SessionExpired()

        return session_data
```

#### Server-Side Sessions

```python
class ServerSideSession:
    """State stored in server (Redis/database)"""

    def __init__(self):
        self.session_store = Redis()

    def create_session(self, user_data):
        session_id = generate_secure_id()

        session_data = {
            "user_id": user_data.id,
            "permissions": user_data.permissions,
            "created": time.time(),
            "last_accessed": time.time()
        }

        # Store in Redis with TTL
        self.session_store.setex(
            key=f"session:{session_id}",
            value=json.dumps(session_data),
            ttl=3600
        )

        return session_id

    def get_session(self, session_id):
        data = self.session_store.get(f"session:{session_id}")
        if not data:
            raise SessionNotFound()

        # Update last accessed
        session_data = json.loads(data)
        session_data["last_accessed"] = time.time()

        # Extend TTL on access
        self.session_store.setex(
            key=f"session:{session_id}",
            value=json.dumps(session_data),
            ttl=3600
        )

        return session_data
```

## Part 3: MASTERY (Third Pass)

### Evidence-Based State Management

#### State as Evidence

Every piece of state is evidence of something:

```python
class StateEvidence:
    """State carries evidence of its validity"""

    def __init__(self):
        self.evidence_types = {
            'existence': 'The state exists',
            'ownership': 'Who owns this state',
            'freshness': 'How recent is this state',
            'consistency': 'How consistent with other state',
            'durability': 'How permanent is this state'
        }

    def create_state_with_evidence(self, key, value):
        return StateWithEvidence(
            key=key,
            value=value,
            evidence={
                'existence_proof': self.generate_merkle_proof(key, value),
                'ownership_proof': self.sign_ownership(key),
                'freshness_proof': self.get_timestamp_proof(),
                'consistency_proof': self.get_vector_clock(),
                'durability_proof': self.get_replication_confirmation()
            }
        )
```

#### Evidence Lifecycle for State

```python
class StateLifecycle:
    """State evidence through its lifecycle"""

    def __init__(self):
        self.states = {
            'CREATED': 'State just created, evidence being generated',
            'VALIDATED': 'Evidence validated, state accepted',
            'ACTIVE': 'State in use, evidence fresh',
            'STALE': 'Evidence aging, refresh needed',
            'EXPIRED': 'Evidence expired, state questionable',
            'ARCHIVED': 'State archived with historical evidence'
        }

    def transition(self, state, event):
        if state == 'CREATED' and event == 'evidence_complete':
            return 'VALIDATED'
        elif state == 'VALIDATED' and event == 'first_use':
            return 'ACTIVE'
        elif state == 'ACTIVE' and event == 'ttl_approaching':
            return 'STALE'
        elif state == 'STALE' and event == 'refreshed':
            return 'ACTIVE'
        elif state == 'STALE' and event == 'ttl_exceeded':
            return 'EXPIRED'
        elif state == 'EXPIRED' and event == 'archived':
            return 'ARCHIVED'
```

### Invariant Framework for State

#### Primary Invariant: STATE COHERENCE

State must remain coherent across all views:

```python
class StateCoherence:
    """Ensure state coherence across system"""

    def check_coherence(self, state_views):
        """All views must be explainably related"""

        # Collect all state versions
        versions = []
        for view in state_views:
            versions.append({
                'node': view.node_id,
                'version': view.version,
                'vector_clock': view.vector_clock,
                'timestamp': view.timestamp
            })

        # Check if versions are causally related
        if self.are_concurrent(versions):
            # Concurrent updates - need resolution
            return self.resolve_concurrent_states(versions)
        elif self.has_causality_violation(versions):
            # Causality broken - critical error
            raise CausalityViolation(versions)
        else:
            # Versions form a valid history
            return self.get_latest_version(versions)
```

#### Supporting Invariants

**ISOLATION**: State changes don't interfere
```python
def ensure_isolation(self, transaction):
    # Snapshot isolation
    snapshot = self.get_snapshot(transaction.start_time)
    transaction.execute_on_snapshot(snapshot)

    # Check for write conflicts
    if self.has_write_conflicts(transaction, snapshot):
        raise IsolationViolation()
```

**DURABILITY**: State survives failures
```python
def ensure_durability(self, state_change):
    # Write to WAL
    self.wal.append(state_change)

    # Replicate to quorum
    confirmations = self.replicate_to_quorum(state_change)

    if confirmations < self.quorum_size:
        raise DurabilityNotGuaranteed()
```

**CONSISTENCY**: State respects constraints
```python
def ensure_consistency(self, new_state):
    # Check invariants
    for invariant in self.invariants:
        if not invariant.holds(new_state):
            raise ConsistencyViolation(invariant)

    # Check foreign key constraints
    for reference in new_state.get_references():
        if not self.exists(reference):
            raise ReferentialIntegrityViolation(reference)
```

### Mode Matrix for State Systems

#### Target Mode (Optimal State)
```python
target_mode = {
    'consistency': 'strong',
    'availability': 'high',
    'partition_tolerance': 'handled',
    'latency': '<10ms',
    'durability': '11-nines',
    'operations': ['read', 'write', 'transaction', 'query']
}
```

#### Degraded Mode (Partial Failures)
```python
degraded_mode = {
    'consistency': 'bounded_staleness',
    'availability': 'reduced',
    'partition_tolerance': 'active_partition',
    'latency': '<100ms',
    'durability': '5-nines',
    'operations': ['read', 'write']  # No transactions
}
```

#### Floor Mode (Survival)
```python
floor_mode = {
    'consistency': 'eventual',
    'availability': 'read_only',
    'partition_tolerance': 'isolated',
    'latency': 'best_effort',
    'durability': 'at_risk',
    'operations': ['read']  # Read-only
}
```

#### Recovery Mode (Healing)
```python
recovery_mode = {
    'consistency': 'converging',
    'availability': 'increasing',
    'partition_tolerance': 'healing',
    'latency': 'variable',
    'durability': 'rebuilding',
    'operations': ['read', 'reconcile']
}
```

### Production Patterns

#### State Migration

```python
class StateMigration:
    """Migrate state without downtime"""

    def live_migration(self, source, target):
        # Phase 1: Dual writes
        self.enable_dual_writes(source, target)

        # Phase 2: Bulk copy
        checkpoint = self.copy_existing_state(source, target)

        # Phase 3: Catch up
        self.replay_changes_since(checkpoint, source, target)

        # Phase 4: Verification
        if not self.verify_consistency(source, target):
            raise MigrationInconsistency()

        # Phase 5: Cutover
        self.switch_reads_to_target(target)
        self.disable_writes_to_source(source)

        # Phase 6: Cleanup
        self.decommission_source(source)
```

#### State Sharding

```python
class StateSharding:
    """Shard state for scalability"""

    def __init__(self):
        self.shard_map = ConsistentHashRing()

    def get_shard(self, key):
        """Determine which shard owns this key"""
        return self.shard_map.get_node(key)

    def resharding(self, new_shard_count):
        """Split or merge shards"""
        old_map = self.shard_map
        new_map = ConsistentHashRing(new_shard_count)

        # Identify key movements
        movements = []
        for key in self.all_keys():
            old_shard = old_map.get_node(key)
            new_shard = new_map.get_node(key)

            if old_shard != new_shard:
                movements.append((key, old_shard, new_shard))

        # Execute migrations
        for key, source, target in movements:
            self.migrate_key(key, source, target)

        # Atomic cutover
        self.shard_map = new_map
```

### Case Studies

#### Redis Cluster: Sharded State

```python
class RedisClusterExample:
    """How Redis handles distributed state"""

    def __init__(self):
        self.slots = 16384  # Hash slots
        self.nodes = []  # Cluster nodes

    def key_to_slot(self, key):
        """Map key to hash slot"""
        return crc16(key) % self.slots

    def execute_command(self, command, key):
        slot = self.key_to_slot(key)
        node = self.get_node_for_slot(slot)

        try:
            return node.execute(command, key)
        except MOVED as e:
            # Slot moved to different node
            new_node = self.cluster.get_node(e.node_id)
            self.update_slot_map(slot, new_node)
            return new_node.execute(command, key)
        except ASK as e:
            # Slot being migrated
            temp_node = self.cluster.get_node(e.node_id)
            return temp_node.execute(command, key, asking=True)
```

#### DynamoDB: Managed State

```python
class DynamoDBExample:
    """AWS's approach to distributed state"""

    def __init__(self):
        self.consistent_hashing = ConsistentHashRing()
        self.replication_factor = 3

    def put_item(self, table, key, item):
        # Find coordinator node
        coordinator = self.consistent_hashing.get_node(key)

        # Get preference list (N nodes)
        preference_list = self.consistent_hashing.get_preference_list(
            key,
            self.replication_factor
        )

        # Write to W nodes
        write_confirmations = coordinator.write_to_nodes(
            preference_list,
            item,
            w=2  # W value
        )

        if write_confirmations >= 2:
            return Success()
        else:
            return InsufficientWrites()
```

#### CockroachDB: Distributed SQL

```python
class CockroachDBExample:
    """Distributed SQL with serializable isolation"""

    def execute_transaction(self, txn):
        # Start distributed transaction
        txn_id = self.begin_transaction()

        # Track read and write timestamps
        read_timestamp = HLC.now()
        write_timestamp = None

        # Execute operations
        for operation in txn.operations:
            if operation.is_read():
                self.track_read(txn_id, operation.key, read_timestamp)
            else:
                write_timestamp = HLC.now()
                self.track_write(txn_id, operation.key, write_timestamp)

        # Check for conflicts
        if self.has_serialization_conflict(txn_id):
            self.abort_transaction(txn_id)
            raise SerializationFailure()

        # Commit via Raft
        self.commit_via_consensus(txn_id, write_timestamp)
```

## Synthesis: State Management Principles

### The Fundamental Trade-offs

1. **Consistency vs Availability**: You can't have both during partition
2. **Latency vs Durability**: Faster responses mean less durability
3. **Simplicity vs Scalability**: Simple solutions don't scale
4. **Cost vs Reliability**: More replicas cost more
5. **Flexibility vs Performance**: Generic solutions are slower

### Design Principles

1. **Make state explicit**: Don't hide state, embrace it
2. **Design for failure**: State will be inconsistent, plan for it
3. **Use appropriate consistency**: Not everything needs strong consistency
4. **Batch when possible**: Amortize coordination costs
5. **Cache aggressively**: But know invalidation is hard
6. **Monitor state health**: You can't manage what you don't measure
7. **Test state corruption**: It will happen in production

### Choosing State Management Approaches

```python
def choose_state_approach(requirements):
    if requirements.needs_transactions and requirements.needs_sql:
        return "Distributed SQL (CockroachDB, Spanner)"

    elif requirements.needs_transactions and not requirements.needs_sql:
        return "Transactional KV (FoundationDB, etcd)"

    elif requirements.needs_high_availability and requirements.can_handle_eventual:
        return "Dynamo-style (DynamoDB, Cassandra)"

    elif requirements.needs_caching and requirements.can_lose_data:
        return "In-memory (Redis, Memcached)"

    elif requirements.needs_streaming and requirements.can_replay:
        return "Event log (Kafka, Pulsar)"

    else:
        return "Combination of above"
```

## Exercises

### Conceptual Exercises
1. Design a distributed counter that never loses increments
2. Prove that exactly-once delivery requires state
3. Design a session store for 1 billion users
4. Analyze the state requirements of a ride-sharing app
5. Design state management for a global game

### Implementation Projects
1. Build a replicated state machine
2. Implement 2PC coordinator
3. Create a saga orchestrator
4. Build a distributed cache
5. Implement vector clock conflict resolution

### Production Analysis
1. Measure state distribution in your system
2. Calculate state growth rate
3. Analyze state access patterns
4. Find state consistency violations
5. Profile state migration impact

## Key Takeaways

- **State is everywhere**: Even "stateless" systems have state
- **State is evidence**: Every piece of state proves something
- **Consistency is expensive**: Choose the right level
- **Failures are certain**: Design for split-brain
- **Monitoring is critical**: State health determines system health
- **Testing is essential**: State bugs are the worst bugs
- **Simplicity wins**: Complex state management fails

## Further Reading

- "Designing Data-Intensive Applications" - Martin Kleppmann
- "Database Internals" - Alex Petrov
- "Streaming Systems" - Reuven Lax et al.
- Papers: Calvin, Spanner, FaunaDB, Amazon Aurora
- Blogs: High Scalability, Uber Engineering, Netflix Tech Blog

## Chapter Summary

State is the fundamental challenge in distributed systems. We've explored:

- The difference between stateless and stateful services
- State machine replication for consistency
- Modern distributed transactions
- Saga patterns for long-running operations
- Session state strategies
- Evidence-based state management
- Production patterns for state at scale

The key insight: **State is not a problem to eliminate but a resource to manage**. By treating state as evidence with explicit lifecycle, guarantees, and degradation modes, we can build systems that handle state reliably at scale.

Remember:
- Every system has state somewhere
- State coherence is the primary invariant
- Evidence tracks state validity
- Modes define degradation behavior
- Production requires careful state management

Next, we'll explore how the giants—Google, Amazon, Meta—build planet-scale systems that manage exabytes of state across millions of machines.

---

> "The state of state is that state is everywhere, and pretending otherwise is the source of most distributed systems failures."

Continue to [Chapter 11: Systems That Never Sleep →](../chapter-11/index.md)