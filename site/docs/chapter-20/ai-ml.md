# AI/ML Integration: Learning Systems

## Machine Learning Meets Distributed Systems

AI/ML is transforming distributed systems from designed to learned. Our framework adapts: ML predictions become a new evidence type.

### Guarantee Vectors with ML

```python
# Classical system
G_classical = ⟨Global, SS, SER, Fresh(10ms), Idem, Auth(signature)⟩

# ML-augmented system
G_ml = ⟨Regional, Causal, RA, Fresh(predicted), Idem, Auth(model-attestation)⟩
#                                      ↑
#                           ML predicts freshness bound
```

**ML as evidence generator**:
- Predict failures before they occur
- Estimate query latency
- Forecast load patterns

### Predictive Failure Detection

```python
class MLFailurePredictor:
    def __init__(self):
        self.model = train_failure_model()

    def predict_failure(self, node):
        features = {
            'cpu_trend': node.cpu_history,
            'memory_pressure': node.memory_trend,
            'disk_errors': node.smart_stats,
            'network_latency': node.ping_times,
            'time_since_deploy': node.uptime
        }

        failure_prob = self.model.predict(features)

        if failure_prob > 0.7:  # 70% chance of failure
            return {
                'will_fail': True,
                'confidence': failure_prob,
                'estimated_time': 'within 1 hour',
                'action': 'preemptive_migration'
            }
```

**Evidence**: Statistical prediction (not deterministic)

**Mode transition**:
```
Normal → ML_Predicts_Failure → Proactive_Degraded → Recovery
```

### Learned Indexes (Kraska et al.)

Replace B-trees with neural networks:

```python
class LearnedIndex:
    """ML model predicts position of key"""

    def __init__(self, data):
        # Train model: key → position
        keys = [item.key for item in data]
        positions = range(len(data))

        self.model = train_regression(keys, positions)

    def lookup(self, key):
        # Model predicts position
        predicted_pos = int(self.model.predict([key])[0])

        # Search nearby (model isn't perfect)
        for offset in range(-10, 11):
            pos = predicted_pos + offset
            if 0 <= pos < len(self.data):
                if self.data[pos].key == key:
                    return self.data[pos].value

        return None  # Not found
```

**Benefits**:
- Faster than B-tree for some workloads (learned data distribution)
- Smaller memory footprint

**Trade-offs**:
- Requires retraining on data changes
- Worst-case still needs fallback (linear search)

### Neural Consensus: ML-Driven Paxos

**Idea**: Learn which nodes are slow/unreliable

```python
class NeuralPaxos:
    def __init__(self):
        self.model = train_node_reliability_model()

    def select_quorum(self, proposal):
        # Classical Paxos: any majority works
        # Neural Paxos: select fast, reliable nodes

        node_scores = {}
        for node in self.nodes:
            features = {
                'latency_p99': node.latency_history,
                'availability': node.uptime_ratio,
                'load': node.current_cpu
            }
            node_scores[node] = self.model.predict(features)

        # Select top N nodes (learned optimal quorum)
        quorum = sorted(node_scores, key=node_scores.get, reverse=True)[:majority]

        return quorum
```

**Result**: 2-3x faster consensus by avoiding slow nodes

### Resource Allocation with RL

**Kubernetes autoscaling with Reinforcement Learning**:

```python
class RLAutoscaler:
    """Learn optimal scaling policy"""

    def __init__(self):
        self.agent = PPO()  # Proximal Policy Optimization
        self.state_space = ['cpu', 'memory', 'latency', 'queue_depth']
        self.action_space = ['scale_up', 'scale_down', 'no_op']

    def decide_action(self, current_state):
        # Agent learned from experience
        action = self.agent.predict(current_state)

        if action == 'scale_up':
            self.add_pods(count=1)
        elif action == 'scale_down':
            self.remove_pods(count=1)

        # Observe reward (negative cost + negative latency)
        reward = -cost - latency_penalty
        self.agent.update(current_state, action, reward)
```

**Learned policy** beats hand-tuned thresholds

### Challenges: ML in Production

**1. Model staleness**:
```python
# Evidence lifecycle
Generated: Model trained on historical data
Validated: Tested on holdout set
Active: Making predictions
Expiring: Data distribution shifting
Expired: Model accuracy < threshold
Recovery: Retrain on new data
```

**2. Adversarial inputs**:
```python
# Attacker crafts input to fool model
adversarial_input = craft_to_fool_model(target_model)
prediction = model.predict(adversarial_input)
# Prediction is wrong but confident!
```

**3. Explainability**:
```python
# Why did model predict failure?
# Neural network: hard to explain
# Need: SHAP values, attention mechanisms
```

### Mode Matrix: ML-Augmented System

```
| Mode              | ML Status    | Evidence             | Operations       |
|-------------------|--------------|----------------------|------------------|
| Normal            | Accurate     | Predictions valid    | ML-guided        |
| Model_Degraded    | Inaccurate   | Predictions suspect  | Classical rules  |
| Model_Retraining  | Offline      | Historical data      | Manual overrides |
| Recovery          | Tested       | Validation metrics   | Gradual rollout  |
```

### Future: Distributed ML Training

**Federated Learning**: Train on distributed data without centralizing

```python
class FederatedLearning:
    def train_federated(self, clients):
        global_model = initialize_model()

        for round in range(100):
            # Each client trains locally
            client_models = []
            for client in clients:
                local_model = global_model.copy()
                local_model.train(client.local_data)  # Data never leaves client
                client_models.append(local_model.weights)

            # Aggregate models (weighted by data size)
            global_model.weights = average(client_models, weights=[c.data_size for c in clients])

        return global_model
```

**Privacy-preserving**: Data stays local (GDPR compliant)

Continue to [New Hardware →](hardware.md)