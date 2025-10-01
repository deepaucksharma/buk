# Blockchain Evolution: Beyond Bitcoin

## From Proof-of-Work to Composable Consensus

Blockchain has evolved from Bitcoin's energy-intensive PoW to sophisticated consensus mechanisms. The framework lens reveals blockchain as an extreme application of our principles.

### Guarantee Vector: Blockchain

```python
# Bitcoin (PoW)
G_bitcoin = ⟨Global, Total-Order, Linearizable, Fresh(10min), Idem(tx-hash), Auth(signature)⟩

# Ethereum 2.0 (PoS)
G_eth2 = ⟨Global, Total-Order, Linearizable, Fresh(12sec), Idem(tx-hash), Auth(BLS-sig)⟩

# Solana (PoH + PoS)
G_solana = ⟨Global, Total-Order, Linearizable, Fresh(400ms), Idem(tx-hash), Auth(ed25519)⟩
```

### Evolution: Proof of Stake

**Why PoS wins**:
- Energy efficient (99.95% reduction)
- Faster finality (Ethereum: 10min → 12sec)
- Economic security (cryptoeconomics)

```python
class ProofOfStake:
    def select_validator(self, epoch):
        # Weighted random selection by stake
        validators = self.get_validators()
        weights = [v.stake for v in validators]
        return random.choices(validators, weights=weights)[0]

    def slash_for_misbehavior(self, validator, evidence):
        # Slashing: lose stake for bad behavior
        if self.verify_double_sign(evidence):
            self.burn(validator.stake * 0.5)  # 50% slash
        elif self.verify_invalid_block(evidence):
            self.burn(validator.stake * 0.01)  # 1% slash
```

**Evidence**: Economic stake at risk

### Zero-Knowledge Proofs: Privacy + Verification

**ZK-SNARK**: Prove statement without revealing witness

```python
def zk_proof_example():
    # Prover wants to prove: "I know x such that hash(x) = y"
    # Without revealing x

    # Setup (trusted setup required for SNARKs)
    proving_key, verification_key = trusted_setup()

    # Prover generates proof
    secret_x = "my_secret"
    public_y = hash(secret_x)
    proof = generate_proof(proving_key, secret_x, public_y)

    # Verifier checks proof
    is_valid = verify_proof(verification_key, proof, public_y)
    # Returns True, but never learns secret_x
```

**Applications**:
- **ZK-Rollups**: Ethereum scaling (Polygon, zkSync)
- **Private transactions**: Zcash, Monero
- **Compliance**: Prove eligibility without revealing identity

### Cross-Chain Bridges: Composing Blockchains

```python
class CrossChainBridge:
    """Connect Ethereum and Polygon"""

    def deposit(self, eth_amount, user):
        # Lock on Ethereum
        eth_contract.lock(user, eth_amount)

        # Generate merkle proof of lock
        proof = eth_chain.generate_merkle_proof(lock_tx)

        # Mint on Polygon (after verification)
        polygon_contract.mint(user, eth_amount, proof)

    def withdraw(self, polygon_amount, user):
        # Burn on Polygon
        polygon_contract.burn(user, polygon_amount)

        # Wait for checkpoint (security)
        checkpoint = wait_for_polygon_checkpoint()

        # Unlock on Ethereum
        eth_contract.unlock(user, polygon_amount, checkpoint)
```

**Challenge**: Bridge security (hacks: Ronin $624M, Poly Network $611M)

### DAG-Based Consensus: Beyond Linear Chains

**Hashgraph, IOTA, Nano**: Directed Acyclic Graph instead of chain

```
Linear Chain (Bitcoin):     DAG (Hashgraph):
Block1 → Block2 → Block3    Tx1 → Tx4 → Tx7
                             ↓  ↘    ↗   ↓
                            Tx2 → Tx5 → Tx8
                             ↓      ↘   ↓
                            Tx3 → Tx6 → Tx9
```

**Benefits**:
- Higher throughput (parallel transactions)
- Lower latency (no block interval)

**Trade-offs**:
- More complex consensus
- Not all DAGs reach same total order

### Mode Matrix: Blockchain Modes

```
| Mode       | Invariants          | Evidence           | Finality  |
|------------|---------------------|--------------------|-----------|
| Normal     | Total order         | PoW/PoS consensus  | 6-12 conf |
| Forked     | Multiple chains     | Competing chains   | None      |
| Reorging   | Reorganizing        | Longer chain found | Reverted  |
| Finalized  | Irreversible        | Economic finality  | Certain   |
```

### Production Landscape (2024)

**Layer 1s**:
- Ethereum: PoS, 12sec blocks, $200B+ TVL
- Solana: PoH+PoS, 400ms blocks, validator hardware
- Avalanche: Subnet model, <1sec finality

**Layer 2s**:
- Arbitrum/Optimism: Optimistic rollups
- zkSync/Polygon: ZK-rollups
- Lightning: Bitcoin payment channels

Continue to [AI/ML Integration →](ai-ml.md)