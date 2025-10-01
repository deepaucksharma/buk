# Byzantine Security: Defending Against Malicious Actors

## Introduction: The Enemy Within

On August 1, 2010, Bitcoin block 74,638 contained a transaction creating 184 billion bitcoins out of thin air—violating the fundamental rule that only 21 million bitcoins can ever exist.

This should have destroyed Bitcoin. The entire security model depends on miners following protocol rules. A miner created invalid bitcoins, and the network was supposed to reject the block automatically.

**What happened**: A bug in the Bitcoin protocol allowed overflow in the transaction value check. An attacker exploited it, creating a transaction that passed validation.

**The response**: Within 5 hours, developers released a patch. Within 19 hours, 51% of the network had upgraded. The malicious block was rejected, the blockchain forked back to a valid state, and Bitcoin continued operating.

**The lesson**: In distributed systems, you must assume some nodes are malicious. They will lie, cheat, send conflicting messages, and try to break the system. Your protocol must work correctly **even when some participants are actively trying to subvert it**.

This is the **Byzantine Generals Problem**—the fundamental challenge of achieving consensus in the presence of malicious actors.

### Byzantine vs Crash Failures

Distributed systems face two types of failures:

**Crash failures** (fail-stop):
- Node stops responding
- Network partition isolates nodes
- Predictable: node is either working or not working

**Byzantine failures** (arbitrary):
- Node sends conflicting messages to different recipients
- Node claims to have received data it never received
- Node performs invalid state transitions
- Unpredictable: node behaves arbitrarily, maliciously, or due to bugs

**Example**:
- **Crash failure**: Database replica crashes. Other replicas detect timeout, exclude it from quorum, continue operating.
- **Byzantine failure**: Database replica is compromised. It claims "transaction X committed" to some clients and "transaction X aborted" to others. It sends different responses based on who asks.

**Why Byzantine failures are harder**:
1. Detection is hard (how do you know a node is lying vs slow?)
2. Isolation is hard (malicious node can coordinate with others)
3. Recovery is hard (how do you trust a node that was compromised?)

### Why Byzantine Security Matters

**Traditional systems assume**: Nodes may fail, but they follow protocol when operational.

**Modern systems must assume**: Some nodes are actively malicious.

**Why**:
1. **Cryptocurrency systems**: Financial incentive to cheat (double-spend, inflate supply)
2. **Multi-organization systems**: Participants may have conflicting interests
3. **Supply chain systems**: Vendors may falsify data
4. **Healthcare systems**: Insurance fraud, medical record tampering
5. **Compromised infrastructure**: Nation-state attacks, insider threats

**The cost of not being Byzantine-resistant**:
- **Mt. Gox (2014)**: Bitcoin exchange hacked, 850,000 BTC stolen ($450M at the time, $20B+ today)
- **DAO hack (2016)**: Ethereum smart contract exploited, $50M stolen
- **FTX collapse (2022)**: Centralized exchange fraud, $8B+ customer funds lost

## Part 1: The Byzantine Generals Problem

### The Original Problem (Lamport 1982)

**Scenario**: Byzantine army surrounding a city. Generals must coordinate attack time.

**Constraints**:
- Generals communicate via messengers
- Some generals are traitors (Byzantine)
- Loyal generals must agree on same plan
- A small number of traitors should not prevent loyal generals from reaching agreement

**Challenges**:
1. **Traitor sends conflicting messages**: Tells General A "attack at dawn," tells General B "attack at noon"
2. **Traitor lies about others**: Tells General A that General B said "retreat"
3. **Traitor withholds messages**: Doesn't forward messages it receives

**Goal**: Achieve consensus among loyal generals despite traitors.

### The Impossibility Result

**Lamport's proof**: Consensus is **impossible** with 3 generals if 1 is a traitor.

**Why**:
```
Scenario: Generals A, B, C. Commander A wants to coordinate attack.

Case 1: Commander A is traitor
- A tells B: "Attack"
- A tells C: "Retreat"
- B and C disagree (no consensus)

Case 2: Lieutenant C is traitor
- A tells B and C: "Attack"
- C tells B: "The commander said retreat"
- B doesn't know if A is traitor (said "retreat") or C is traitor (lied about A)
- B cannot reach consensus
```

**The theorem**: You need **3f + 1** nodes to tolerate **f** Byzantine failures.

**Examples**:
- 1 Byzantine node → need 4 total nodes
- 2 Byzantine nodes → need 7 total nodes
- 3 Byzantine nodes → need 10 total nodes

**Why this ratio**: With 3f + 1 nodes, f Byzantine nodes cannot outvote the 2f + 1 honest nodes.

### Practical Byzantine Fault Tolerance (PBFT)

**PBFT** (Castro & Liskov, 1999) is the first practical Byzantine consensus algorithm.

**Setting**:
- N replicas (N = 3f + 1 for f Byzantine failures)
- One replica is primary (leader)
- Clients send requests to primary
- Primary coordinates consensus

**Three-phase protocol**:

1. **Pre-prepare**: Primary assigns sequence number to request, broadcasts to all replicas
2. **Prepare**: Each replica validates request, broadcasts prepare message to all others
3. **Commit**: Once replica receives 2f prepare messages, broadcasts commit message to all

**Safety property**: If 2f + 1 replicas commit, request is committed (even if f replicas are Byzantine)

**Liveness property**: If primary is Byzantine, replicas detect timeout and elect new primary

### PBFT Implementation

```python
from dataclasses import dataclass
from typing import Dict, Set, Optional, List
from enum import Enum
import hashlib
import json
import time

class MessageType(Enum):
    REQUEST = "request"
    PRE_PREPARE = "pre_prepare"
    PREPARE = "prepare"
    COMMIT = "commit"
    REPLY = "reply"

@dataclass
class Message:
    """Base message type for PBFT protocol"""
    msg_type: MessageType
    view: int          # Current view number (changes when primary changes)
    sequence: int      # Sequence number for request ordering
    payload: dict
    sender_id: int
    signature: str     # Digital signature (cryptographic proof)

    def digest(self) -> str:
        """Cryptographic hash of message content"""
        content = json.dumps({
            "msg_type": self.msg_type.value,
            "view": self.view,
            "sequence": self.sequence,
            "payload": self.payload
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

class PBFTReplica:
    """
    Practical Byzantine Fault Tolerance replica

    Tolerates f Byzantine failures with 3f + 1 replicas

    Properties:
    - Safety: All honest replicas agree on order of requests
    - Liveness: Requests eventually execute (primary replacement if needed)
    - Byzantine resistance: Up to f replicas can be malicious
    """

    def __init__(
        self,
        replica_id: int,
        total_replicas: int,
        f: int  # Number of tolerated Byzantine failures
    ):
        self.replica_id = replica_id
        self.total_replicas = total_replicas
        self.f = f

        # Protocol state
        self.view = 0  # Current view (primary = view % total_replicas)
        self.sequence = 0  # Last assigned sequence number
        self.log: List[Message] = []  # Message log

        # Message buffers
        self.pre_prepare_messages: Dict[int, Message] = {}
        self.prepare_messages: Dict[int, Set[int]] = {}  # seq -> set of replica IDs
        self.commit_messages: Dict[int, Set[int]] = {}   # seq -> set of replica IDs

        # Executed requests (prevent replay)
        self.executed: Set[int] = set()

        # View change state
        self.view_change_messages: Dict[int, Set[int]] = {}  # view -> set of replicas

    def is_primary(self) -> bool:
        """Check if this replica is current primary"""
        return self.replica_id == (self.view % self.total_replicas)

    def handle_client_request(self, request: dict) -> Optional[dict]:
        """
        Handle client request (if primary)

        Step 1: Assign sequence number
        Step 2: Broadcast pre-prepare to all replicas
        """
        if not self.is_primary():
            # Forward to primary
            primary_id = self.view % self.total_replicas
            self._forward_to_replica(primary_id, request)
            return None

        # Assign sequence number
        self.sequence += 1
        seq = self.sequence

        # Create pre-prepare message
        pre_prepare = Message(
            msg_type=MessageType.PRE_PREPARE,
            view=self.view,
            sequence=seq,
            payload=request,
            sender_id=self.replica_id,
            signature=self._sign(request)
        )

        # Broadcast to all replicas
        self._broadcast(pre_prepare)

        # Process own pre-prepare
        self.handle_pre_prepare(pre_prepare)

        return {"status": "accepted", "sequence": seq}

    def handle_pre_prepare(self, msg: Message):
        """
        Handle pre-prepare message from primary

        Validation:
        1. Signature is valid
        2. View and sequence are correct
        3. No conflicting pre-prepare for same sequence
        """
        # Validate message
        if not self._verify_signature(msg):
            print(f"Replica {self.replica_id}: Invalid signature on pre-prepare")
            return

        if msg.view != self.view:
            print(f"Replica {self.replica_id}: Wrong view {msg.view} (expected {self.view})")
            return

        if msg.sequence in self.pre_prepare_messages:
            existing = self.pre_prepare_messages[msg.sequence]
            if existing.digest() != msg.digest():
                # Conflicting pre-prepares → primary is Byzantine
                print(f"Replica {self.replica_id}: Conflicting pre-prepares detected")
                self._initiate_view_change()
                return

        # Accept pre-prepare
        self.pre_prepare_messages[msg.sequence] = msg

        # Send prepare message to all replicas
        prepare = Message(
            msg_type=MessageType.PREPARE,
            view=self.view,
            sequence=msg.sequence,
            payload=msg.payload,
            sender_id=self.replica_id,
            signature=self._sign(msg.payload)
        )

        self._broadcast(prepare)
        self.handle_prepare(prepare)

    def handle_prepare(self, msg: Message):
        """
        Handle prepare message from replica

        Wait for 2f prepare messages from different replicas
        (including self) before committing
        """
        # Validate message
        if not self._verify_signature(msg):
            return

        if msg.view != self.view:
            return

        # Record prepare vote
        if msg.sequence not in self.prepare_messages:
            self.prepare_messages[msg.sequence] = set()

        self.prepare_messages[msg.sequence].add(msg.sender_id)

        # Check if we have 2f prepare messages
        if len(self.prepare_messages[msg.sequence]) >= 2 * self.f:
            # Prepared: send commit message
            commit = Message(
                msg_type=MessageType.COMMIT,
                view=self.view,
                sequence=msg.sequence,
                payload=msg.payload,
                sender_id=self.replica_id,
                signature=self._sign(msg.payload)
            )

            self._broadcast(commit)
            self.handle_commit(commit)

    def handle_commit(self, msg: Message):
        """
        Handle commit message from replica

        Wait for 2f + 1 commit messages from different replicas
        (including self) before executing
        """
        # Validate message
        if not self._verify_signature(msg):
            return

        if msg.view != self.view:
            return

        # Record commit vote
        if msg.sequence not in self.commit_messages:
            self.commit_messages[msg.sequence] = set()

        self.commit_messages[msg.sequence].add(msg.sender_id)

        # Check if we have 2f + 1 commit messages
        if len(self.commit_messages[msg.sequence]) >= 2 * self.f + 1:
            # Committed: execute request
            if msg.sequence not in self.executed:
                result = self._execute_request(msg.payload)
                self.executed.add(msg.sequence)

                # Send reply to client
                reply = Message(
                    msg_type=MessageType.REPLY,
                    view=self.view,
                    sequence=msg.sequence,
                    payload=result,
                    sender_id=self.replica_id,
                    signature=self._sign(result)
                )

                self._send_to_client(reply)

    def _initiate_view_change(self):
        """
        Initiate view change (replace primary)

        Triggered when:
        - Primary timeout (not responding)
        - Primary sends conflicting pre-prepares
        - Primary sends invalid messages
        """
        new_view = self.view + 1

        print(f"Replica {self.replica_id}: Initiating view change to view {new_view}")

        # Send view-change message to all replicas
        view_change = Message(
            msg_type=MessageType.PREPARE,  # Reusing enum
            view=new_view,
            sequence=0,
            payload={"type": "view_change", "last_sequence": self.sequence},
            sender_id=self.replica_id,
            signature=self._sign({"view": new_view})
        )

        self._broadcast(view_change)
        self._handle_view_change(view_change)

    def _handle_view_change(self, msg: Message):
        """Handle view-change message from replica"""
        new_view = msg.view

        if new_view not in self.view_change_messages:
            self.view_change_messages[new_view] = set()

        self.view_change_messages[new_view].add(msg.sender_id)

        # If 2f + 1 replicas want to change view, switch to new view
        if len(self.view_change_messages[new_view]) >= 2 * self.f + 1:
            print(f"Replica {self.replica_id}: View change to {new_view} complete")
            self.view = new_view

            # Clear state for new view
            self.prepare_messages.clear()
            self.commit_messages.clear()

    def _execute_request(self, request: dict) -> dict:
        """Execute client request (state machine transition)"""
        # In production: apply request to state machine
        print(f"Replica {self.replica_id}: Executing request {request}")
        return {"status": "executed", "result": "success"}

    def _sign(self, data: dict) -> str:
        """
        Sign message with private key

        In production: use RSA or ECDSA digital signatures
        """
        content = json.dumps(data, sort_keys=True)
        # Simplified: real implementation uses cryptographic signatures
        return hashlib.sha256(f"{self.replica_id}:{content}".encode()).hexdigest()

    def _verify_signature(self, msg: Message) -> bool:
        """
        Verify message signature

        In production: verify with sender's public key
        """
        expected_sig = hashlib.sha256(
            f"{msg.sender_id}:{json.dumps(msg.payload, sort_keys=True)}".encode()
        ).hexdigest()
        return msg.signature == expected_sig

    def _broadcast(self, msg: Message):
        """Broadcast message to all replicas"""
        # In production: send over network to all replicas
        pass

    def _forward_to_replica(self, replica_id: int, request: dict):
        """Forward request to specific replica"""
        pass

    def _send_to_client(self, reply: Message):
        """Send reply to client"""
        pass

# Example: 4 replicas, tolerate 1 Byzantine failure
replicas = [PBFTReplica(i, total_replicas=4, f=1) for i in range(4)]

# Client sends request to primary (replica 0)
request = {"operation": "transfer", "from": "alice", "to": "bob", "amount": 100}
replicas[0].handle_client_request(request)
```

### Why PBFT Works

**Safety**: If honest replicas commit request at sequence number N, all honest replicas commit the same request at N.

**Proof sketch**:
1. For replica to commit, it needs 2f + 1 commit messages
2. With N = 3f + 1 total replicas, at least f + 1 commit messages are from honest replicas
3. If two different requests committed at same sequence N, there would need to be 2(f + 1) = 2f + 2 honest replicas voting for different requests
4. But there are only 2f + 1 honest replicas total
5. Contradiction → only one request can commit at sequence N

**Liveness**: If primary is Byzantine (not responding or sending conflicting messages), replicas detect timeout and initiate view change. New primary elected in O(f) rounds.

**Performance**: PBFT requires O(N²) messages per request (N replicas, each broadcasts to all others). For 100 replicas, that's 10,000 messages per request. This limits scalability.

## Part 2: Blockchain Consensus

### Bitcoin's Breakthrough: Proof of Work

**Problem with PBFT**: Requires knowing the set of replicas (permissioned). What if anyone can join (permissionless)?

**Bitcoin's solution** (Nakamoto 2008): **Proof of Work (PoW)** consensus.

**Key insight**: Instead of voting (1 replica = 1 vote), use computational work (1 hash = 1 vote).

**How it works**:
1. **Mining**: Miners compete to solve cryptographic puzzle (find hash with N leading zeros)
2. **Difficulty adjustment**: Puzzle difficulty adjusts so average block time is 10 minutes
3. **Longest chain wins**: Chain with most cumulative work is canonical
4. **Incentives**: Miner who finds valid block receives block reward (newly minted bitcoin + transaction fees)

**Byzantine resistance**:
- Attacker needs 51% of hash power to rewrite history
- Cost of 51% attack: $10-20 billion in mining hardware + electricity
- For large blockchains (Bitcoin, Ethereum), economically infeasible

### Proof of Work Implementation

```python
import hashlib
import time
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Block:
    """Blockchain block"""
    index: int
    timestamp: float
    transactions: List[dict]
    previous_hash: str
    nonce: int
    hash: str

    def calculate_hash(self) -> str:
        """Calculate block hash"""
        content = f"{self.index}{self.timestamp}{self.transactions}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(content.encode()).hexdigest()

class ProofOfWorkBlockchain:
    """
    Proof of Work blockchain

    Byzantine resistance:
    - Attacker must have >50% of hash power to fork chain
    - Honest chain grows faster than attacker's chain
    - Economic incentive to mine honestly
    """

    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.difficulty = difficulty  # Number of leading zeros required
        self.pending_transactions: List[dict] = []

        # Create genesis block
        genesis = Block(
            index=0,
            timestamp=time.time(),
            transactions=[],
            previous_hash="0",
            nonce=0,
            hash=""
        )
        genesis.hash = genesis.calculate_hash()
        self.chain.append(genesis)

    def mine_block(self, miner_address: str) -> Block:
        """
        Mine new block (Proof of Work)

        Find nonce such that hash(block) has 'difficulty' leading zeros

        Computational cost: O(2^difficulty)
        - difficulty=4: ~16 attempts average
        - difficulty=10: ~1000 attempts average
        - difficulty=20: ~1 million attempts average
        """
        previous_block = self.chain[-1]

        # Add coinbase transaction (block reward for miner)
        transactions = self.pending_transactions.copy()
        transactions.insert(0, {
            "from": "network",
            "to": miner_address,
            "amount": 50  # Block reward
        })

        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=transactions,
            previous_hash=previous_block.hash,
            nonce=0,
            hash=""
        )

        # Proof of Work: find nonce that gives hash with N leading zeros
        target = "0" * self.difficulty
        attempts = 0

        start_time = time.time()

        while True:
            block.nonce = attempts
            block.hash = block.calculate_hash()

            if block.hash.startswith(target):
                # Found valid nonce!
                break

            attempts += 1

            if attempts % 100000 == 0:
                elapsed = time.time() - start_time
                print(f"Mining... {attempts} attempts, {elapsed:.2f}s")

        elapsed = time.time() - start_time
        hash_rate = attempts / elapsed

        print(f"Block mined! Hash: {block.hash}")
        print(f"Attempts: {attempts}, Time: {elapsed:.2f}s, Hash rate: {hash_rate:.0f} H/s")

        return block

    def add_block(self, block: Block) -> bool:
        """
        Validate and add block to chain

        Validation:
        1. Hash is correct
        2. Hash meets difficulty target
        3. Previous hash matches
        4. Transactions are valid
        """
        # Validate hash
        if block.hash != block.calculate_hash():
            print("Invalid hash")
            return False

        # Validate difficulty (Proof of Work)
        target = "0" * self.difficulty
        if not block.hash.startswith(target):
            print(f"Hash doesn't meet difficulty target: {block.hash}")
            return False

        # Validate chain linkage
        if block.previous_hash != self.chain[-1].hash:
            print("Invalid previous hash")
            return False

        # Validate transactions (simplified)
        # In production: check signatures, balances, double-spends
        if not self._validate_transactions(block.transactions):
            print("Invalid transactions")
            return False

        # Block is valid
        self.chain.append(block)
        self.pending_transactions.clear()

        return True

    def add_transaction(self, transaction: dict):
        """Add transaction to pending pool"""
        self.pending_transactions.append(transaction)

    def get_balance(self, address: str) -> float:
        """Calculate balance by scanning all transactions"""
        balance = 0.0

        for block in self.chain:
            for tx in block.transactions:
                if tx["to"] == address:
                    balance += tx["amount"]
                if tx.get("from") == address:
                    balance -= tx["amount"]

        return balance

    def _validate_transactions(self, transactions: List[dict]) -> bool:
        """
        Validate all transactions in block

        Checks:
        - Sender has sufficient balance
        - No double-spends
        - Signatures are valid
        """
        # Simplified validation
        for tx in transactions:
            if tx.get("from") == "network":
                continue  # Coinbase transaction (block reward)

            sender_balance = self.get_balance(tx["from"])
            if sender_balance < tx["amount"]:
                return False

        return True

    def handle_fork(self, alternative_chain: List[Block]) -> bool:
        """
        Handle blockchain fork (Byzantine attack or network partition)

        Rule: Longest chain wins (most cumulative Proof of Work)

        This is how Bitcoin resolves conflicts between competing chains
        """
        # Validate alternative chain
        if not self._validate_chain(alternative_chain):
            return False

        # Compare lengths (more sophisticated: compare cumulative difficulty)
        if len(alternative_chain) > len(self.chain):
            print("Alternative chain is longer - switching")
            self.chain = alternative_chain
            return True
        else:
            print("Alternative chain is shorter - ignoring")
            return False

    def _validate_chain(self, chain: List[Block]) -> bool:
        """Validate entire blockchain"""
        for i in range(1, len(chain)):
            block = chain[i]
            previous_block = chain[i - 1]

            # Validate linkage
            if block.previous_hash != previous_block.hash:
                return False

            # Validate Proof of Work
            if not block.hash.startswith("0" * self.difficulty):
                return False

            # Validate hash
            if block.hash != block.calculate_hash():
                return False

        return True

# Example: Mining blockchain
blockchain = ProofOfWorkBlockchain(difficulty=4)

# Add transactions
blockchain.add_transaction({"from": "alice", "to": "bob", "amount": 10})
blockchain.add_transaction({"from": "bob", "to": "charlie", "amount": 5})

# Mine block
block = blockchain.mine_block(miner_address="miner1")
blockchain.add_block(block)

# Check balances
print(f"Miner balance: {blockchain.get_balance('miner1')}")  # 50 (block reward)
print(f"Bob balance: {blockchain.get_balance('bob')}")        # 5 (received 10, sent 5)
```

### The 51% Attack

**Attack scenario**: Attacker controls 51% of mining power.

**What attacker can do**:
1. **Double-spend**: Send payment to merchant, receive goods, then rewrite blockchain to reverse payment
2. **Censor transactions**: Refuse to include certain transactions in blocks
3. **Orphan other miners**: Create longer chain that excludes other miners' blocks

**What attacker CANNOT do**:
1. **Steal funds**: Cannot create transactions without private keys
2. **Change consensus rules**: Cannot mint more than allowed block reward
3. **Rewrite old history**: Cost increases exponentially with depth

**Real-world 51% attacks**:
- **Ethereum Classic (2019)**: 51% attack, $1.1M double-spent
- **Bitcoin Gold (2018)**: 51% attack, $18M double-spent
- **Vertcoin (2018)**: 51% attack, multiple reorganizations

**Why Bitcoin is safe**: Cost of 51% attack on Bitcoin exceeds $10B (hardware + electricity). For smaller blockchains, 51% attacks are feasible.

### Proof of Stake: The Energy-Efficient Alternative

**Problem with Proof of Work**: Bitcoin network consumes 150 TWh/year (equivalent to Argentina's electricity consumption).

**Proof of Stake** (Ethereum 2.0, Cardano, Polkadot):
- Instead of mining (computational work), validators stake cryptocurrency
- Validators chosen to propose blocks based on stake amount
- Malicious validators lose their stake (slashing)

**Byzantine resistance**:
- Attacker needs 51% of staked cryptocurrency (worth billions)
- If attacker acts maliciously, their stake is destroyed
- Economic disincentive: attacking destroys attacker's own wealth

**Advantages over Proof of Work**:
- **99.9% less energy**: No mining hardware
- **Faster finality**: Blocks confirmed in seconds vs minutes
- **Better scalability**: Can process more transactions per second

**Trade-offs**:
- **Wealth concentration**: Rich get richer (more stake = more rewards)
- **Nothing at stake problem**: Validators can vote on multiple forks
- **Long-range attacks**: Attacker with old keys can rewrite history

## Part 3: State Machine Replication with Byzantine Fault Tolerance

### The Core Idea

**State machine replication**: Multiple replicas execute same operations in same order, maintaining consistent state.

**Without Byzantine tolerance**:
- Replicas assume all inputs are correct
- Crash failures are handled (Paxos, Raft)

**With Byzantine tolerance**:
- Replicas verify all inputs cryptographically
- Malicious replicas cannot corrupt state
- Consensus achieves despite f Byzantine replicas (with 3f + 1 total)

### Byzantine Fault Tolerant State Machine

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
import hashlib
import json

@dataclass
class Operation:
    """State machine operation"""
    op_type: str  # "set", "get", "delete"
    key: str
    value: Optional[str] = None
    signature: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "op_type": self.op_type,
            "key": self.key,
            "value": self.value
        }, sort_keys=True)

class ByzantineFaultTolerantStateMachine:
    """
    State machine with Byzantine fault tolerance

    Properties:
    - Safety: All honest replicas have same state
    - Liveness: Operations eventually execute
    - Byzantine resistance: Tolerates f faulty replicas (with 3f + 1 total)
    """

    def __init__(self, replica_id: int, total_replicas: int):
        self.replica_id = replica_id
        self.total_replicas = total_replicas
        self.f = (total_replicas - 1) // 3  # Max Byzantine failures tolerated

        # State machine state (key-value store)
        self.state: Dict[str, str] = {}

        # Operation log (ordered list of operations)
        self.log: List[Operation] = []

        # State hash (for verification)
        self.state_hash = self._compute_state_hash()

    def execute_operation(self, operation: Operation) -> Optional[str]:
        """
        Execute operation on state machine

        Returns: result of operation
        """
        # Verify operation signature
        if not self._verify_operation_signature(operation):
            print(f"Replica {self.replica_id}: Invalid operation signature")
            return None

        # Apply operation to state
        if operation.op_type == "set":
            self.state[operation.key] = operation.value
            result = "OK"

        elif operation.op_type == "get":
            result = self.state.get(operation.key, "NOT_FOUND")

        elif operation.op_type == "delete":
            if operation.key in self.state:
                del self.state[operation.key]
                result = "DELETED"
            else:
                result = "NOT_FOUND"

        else:
            result = "INVALID_OPERATION"

        # Append to log
        self.log.append(operation)

        # Update state hash
        self.state_hash = self._compute_state_hash()

        return result

    def verify_state_consistency(self, other_replica_state_hash: str) -> bool:
        """
        Verify state consistency with other replica

        Byzantine detection: If state hashes differ, one replica is faulty
        """
        return self.state_hash == other_replica_state_hash

    def checkpoint_state(self) -> dict:
        """
        Create checkpoint of current state

        Used for:
        - State synchronization
        - Byzantine detection (compare checkpoints)
        - Rollback (if Byzantine behavior detected)
        """
        return {
            "replica_id": self.replica_id,
            "state": self.state.copy(),
            "state_hash": self.state_hash,
            "log_length": len(self.log)
        }

    def verify_checkpoint(self, checkpoint: dict) -> bool:
        """
        Verify checkpoint from another replica

        Byzantine detection: Recompute state hash from checkpoint state
        """
        state = checkpoint["state"]
        expected_hash = hashlib.sha256(
            json.dumps(state, sort_keys=True).encode()
        ).hexdigest()

        return expected_hash == checkpoint["state_hash"]

    def detect_byzantine_divergence(
        self,
        checkpoints: List[dict]
    ) -> Optional[int]:
        """
        Detect Byzantine replica based on checkpoint divergence

        Algorithm:
        1. Collect checkpoints from all replicas
        2. If 2f + 1 replicas have same state hash, that's correct state
        3. Any replica with different state hash is Byzantine
        """
        state_hash_counts: Dict[str, List[int]] = {}

        for checkpoint in checkpoints:
            state_hash = checkpoint["state_hash"]
            replica_id = checkpoint["replica_id"]

            if state_hash not in state_hash_counts:
                state_hash_counts[state_hash] = []

            state_hash_counts[state_hash].append(replica_id)

        # Find majority state hash (2f + 1 replicas)
        for state_hash, replica_ids in state_hash_counts.items():
            if len(replica_ids) >= 2 * self.f + 1:
                # This is the correct state
                correct_state_hash = state_hash

                # Any replica with different hash is Byzantine
                for checkpoint in checkpoints:
                    if checkpoint["state_hash"] != correct_state_hash:
                        byzantine_replica = checkpoint["replica_id"]
                        print(f"Detected Byzantine replica: {byzantine_replica}")
                        return byzantine_replica

        return None

    def _compute_state_hash(self) -> str:
        """Compute cryptographic hash of state"""
        state_json = json.dumps(self.state, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()

    def _verify_operation_signature(self, operation: Operation) -> bool:
        """
        Verify cryptographic signature on operation

        In production: use RSA or ECDSA signatures
        """
        # Simplified verification
        return True

# Example: BFT state machine cluster
replicas = [
    ByzantineFaultTolerantStateMachine(replica_id=i, total_replicas=4)
    for i in range(4)
]

# Execute operations on all replicas
operation = Operation(op_type="set", key="foo", value="bar")

for replica in replicas:
    replica.execute_operation(operation)

# Verify state consistency
checkpoints = [replica.checkpoint_state() for replica in replicas]

print("Checkpoint state hashes:")
for checkpoint in checkpoints:
    print(f"  Replica {checkpoint['replica_id']}: {checkpoint['state_hash']}")

# Simulate Byzantine replica (corrupted state)
replicas[3].state["foo"] = "corrupted_value"
replicas[3].state_hash = replicas[3]._compute_state_hash()

# Detect Byzantine divergence
checkpoints = [replica.checkpoint_state() for replica in replicas]
byzantine_replica = replicas[0].detect_byzantine_divergence(checkpoints)
print(f"Byzantine replica detected: {byzantine_replica}")
```

## Part 4: Real Attacks and Defenses

### Attack 1: Double-Spend

**What it is**: Attacker spends same funds twice by forking blockchain.

**How it works**:
1. Attacker sends payment to merchant (Transaction A)
2. Merchant waits for 1 confirmation, ships goods
3. Attacker mines private fork with conflicting transaction (Transaction B sends funds back to attacker)
4. Attacker's fork becomes longer than main chain
5. Network switches to attacker's fork, Transaction A is reversed

**Defense**:
- **Wait for multiple confirmations**: 6 confirmations (Bitcoin) makes attack exponentially harder
- **Proof of Stake**: Attacker loses stake if caught attempting double-spend
- **Finality gadgets**: Casper FFG (Ethereum) provides economic finality after 2 epochs

### Attack 2: Sybil Attack

**What it is**: Attacker creates many fake identities to gain disproportionate influence.

**How it works**:
1. Attacker creates 1000 nodes in network
2. Each node votes on consensus decisions
3. Attacker's nodes outvote honest nodes (appear to be majority)

**Defense**:
- **Proof of Work**: Creating identity costs computational work (mining)
- **Proof of Stake**: Creating identity costs staked cryptocurrency
- **Proof of Authority**: Only whitelisted identities can participate
- **Social graphs**: Trust based on social connections (Freenet, Advogato)

### Attack 3: Eclipse Attack

**What it is**: Attacker isolates victim node from honest network.

**How it works**:
1. Attacker controls victim's incoming and outgoing connections
2. Attacker feeds victim fake blockchain
3. Victim accepts attacker's chain as truth
4. Attacker double-spends against victim

**Defense**:
- **Diverse peer selection**: Connect to geographically diverse peers
- **Anchor connections**: Maintain persistent connections to known-good peers
- **Tor support**: Use anonymous routing to prevent network-level manipulation

### Attack 4: Long-Range Attack (Proof of Stake)

**What it is**: Attacker with old keys rewrites blockchain history.

**How it works**:
1. Attacker held 51% stake at block 1000
2. Attacker sold stake at block 2000 (no longer has skin in the game)
3. Attacker uses old keys to create alternative fork from block 1000
4. New nodes joining network see attacker's fork as valid

**Defense**:
- **Checkpointing**: Hard-code recent block hashes in client
- **Weak subjectivity**: Nodes trust recent state from social consensus
- **Stake slashing**: Penalize validators who sign conflicting blocks

### Attack 5: Selfish Mining

**What it is**: Miner withholds blocks to gain unfair advantage.

**How it works**:
1. Attacker mines block, doesn't broadcast it
2. Attacker continues mining on private chain
3. When honest miners catch up, attacker releases private chain
4. Attacker's chain is longer, honest miners' work wasted
5. Attacker gains disproportionate block rewards

**Defense**:
- **Publish-or-perish**: Reward miners who publish blocks quickly
- **Uncle rewards**: Ethereum rewards orphaned blocks (reduces incentive to withhold)
- **Network monitoring**: Detect unusual block propagation patterns

## Mental Model: Byzantine Security in Practice

**The Core Principle**: Assume adversaries exist. Design systems that work correctly despite malicious actors.

### When to Use Byzantine Fault Tolerance

**Use BFT when**:
1. **Financial systems**: Cryptocurrency, trading platforms, payment networks
2. **Multi-organization systems**: Supply chain, healthcare records, voting
3. **Untrusted environments**: Public blockchains, peer-to-peer networks
4. **High-stakes operations**: Critical infrastructure, military systems

**Don't use BFT when**:
1. **Trusted environment**: Internal corporate systems (crash fault tolerance is sufficient)
2. **Performance-critical**: BFT adds overhead (3-10× more messages than crash-tolerant consensus)
3. **Small scale**: With 3-5 nodes, simpler consensus (Raft) is better

### The Cost of Byzantine Fault Tolerance

**Message overhead**:
- **Crash-tolerant (Raft)**: O(N) messages per request
- **Byzantine-tolerant (PBFT)**: O(N²) messages per request
- **Proof of Work**: N miners × 10 minutes per block

**Node requirements**:
- **Crash-tolerant**: 2f + 1 nodes for f failures
- **Byzantine-tolerant**: 3f + 1 nodes for f failures

**Computational cost**:
- **PBFT**: Cryptographic signatures on every message
- **Proof of Work**: Massive energy consumption
- **Proof of Stake**: Validator hardware + stake capital

**Real-world numbers**:
- **Bitcoin**: $15B/year in mining costs, 150 TWh/year energy
- **Ethereum (PoS)**: $500M/year in validator costs, 0.01 TWh/year energy
- **PBFT (permissioned)**: 10-100× overhead vs crash-tolerant consensus

### The Trade-Off: Security vs Performance

**Decision framework**:

1. **Do you have financial incentives for malicious behavior?**
   - Yes → Byzantine fault tolerance required
   - No → Crash fault tolerance sufficient

2. **Are participants trusted?**
   - All trusted → Crash fault tolerance (Raft)
   - Some untrusted → Byzantine fault tolerance (PBFT)
   - All untrusted → Blockchain (PoW/PoS)

3. **What's at stake?**
   - High value (millions) → Byzantine fault tolerance
   - Low value (logs, metrics) → Crash fault tolerance

4. **Performance requirements?**
   - Thousands of TPS → Crash fault tolerance or PBFT
   - Tens of TPS → Blockchain acceptable

### Next Steps

Byzantine security protects distributed consensus. But distributed systems also face supply chain attacks—malicious code introduced during build and deployment. Continue to [Supply Chain Security](./supply-chain.md) to understand how to secure the entire software lifecycle.

