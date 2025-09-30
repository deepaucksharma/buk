# Consensus in Production

## Real-World Consensus Deployments

> "In production, consensus isn't about the algorithm—it's about operations, monitoring, and handling the 3am failures."

This section examines how consensus protocols perform in production environments, the challenges operators face, and the lessons learned from running consensus at scale.

## etcd: Kubernetes' Foundation

### Architecture Overview
etcd is the distributed key-value store that powers Kubernetes:

```yaml
# Typical etcd cluster configuration
cluster:
  name: prod-cluster
  members:
    - name: etcd-1
      peer-urls: https://10.0.1.10:2380
      client-urls: https://10.0.1.10:2379
    - name: etcd-2
      peer-urls: https://10.0.1.11:2380
      client-urls: https://10.0.1.11:2379
    - name: etcd-3
      peer-urls: https://10.0.1.12:2380
      client-urls: https://10.0.1.12:2379
    - name: etcd-4
      peer-urls: https://10.0.1.13:2380
      client-urls: https://10.0.1.13:2379
    - name: etcd-5
      peer-urls: https://10.0.1.14:2380
      client-urls: https://10.0.1.14:2379
```

### Production Challenges

#### Challenge 1: Leader Election Storms
**Problem**: Frequent leader changes during high load

```python
class EtcdMonitoring:
    def detect_election_storm(self):
        """Detect excessive leader elections"""
        elections_per_minute = self.count_elections(minutes=1)

        if elections_per_minute > 1:
            alert = Alert(
                severity='critical',
                message=f'Election storm: {elections_per_minute} elections/min',
                runbook='https://wiki/etcd-election-storm'
            )
            self.send_alert(alert)

    def diagnose_election_cause(self):
        """Find why elections are happening"""
        causes = []

        # Check disk latency
        if self.disk_latency_ms > 10:
            causes.append(f"Slow disk: {self.disk_latency_ms}ms")

        # Check network
        if self.packet_loss_rate > 0.01:
            causes.append(f"Packet loss: {self.packet_loss_rate*100}%")

        # Check CPU
        if self.cpu_usage > 0.8:
            causes.append(f"High CPU: {self.cpu_usage*100}%")

        return causes
```

**Solution**: Tune election timeout based on infrastructure
```bash
# For cloud environments with variable latency
etcd --election-timeout=5000 \
     --heartbeat-interval=500

# For bare metal with predictable latency
etcd --election-timeout=1000 \
     --heartbeat-interval=100
```

#### Challenge 2: Large Key Updates
**Problem**: Kubernetes ConfigMaps/Secrets causing timeout

```python
def handle_large_values():
    """Best practices for large values"""
    # DON'T: Store large values directly
    # This blocks consensus
    bad_practice = {
        'key': '/config/large',
        'value': '10MB of data'  # Blocks cluster!
    }

    # DO: Use chunking
    def chunk_value(key, large_value, chunk_size=1024*1024):  # 1MB chunks
        chunks = []
        for i in range(0, len(large_value), chunk_size):
            chunk_key = f"{key}/chunk_{i//chunk_size}"
            chunk = large_value[i:i+chunk_size]
            chunks.append((chunk_key, chunk))

        # Store metadata
        metadata = {
            'chunks': len(chunks),
            'size': len(large_value),
            'hash': hashlib.sha256(large_value).hexdigest()
        }
        chunks.append((f"{key}/meta", json.dumps(metadata)))

        return chunks
```

#### Challenge 3: Compaction and Defragmentation
**Problem**: etcd database growth affecting performance

```bash
#!/bin/bash
# Automated maintenance script

# Auto compaction
etcdctl compact $(etcdctl endpoint status --write-out="json" | jq -r '.header.revision')

# Defragmentation (do one member at a time)
for member in $(etcdctl member list --write-out=json | jq -r '.members[].name'); do
    echo "Defragmenting $member"
    etcdctl --endpoints=$member defrag
    sleep 10  # Let cluster recover
done

# Check database size
etcdctl endpoint status --write-out=table
```

### Monitoring Dashboard
```python
class EtcdDashboard:
    """Key metrics for etcd monitoring"""

    def get_golden_signals(self):
        return {
            'latency': {
                'commit_latency_p50': self.histogram_quantile(0.5, 'etcd_disk_wal_fsync_duration_seconds'),
                'commit_latency_p99': self.histogram_quantile(0.99, 'etcd_disk_wal_fsync_duration_seconds'),
                'apply_latency_p99': self.histogram_quantile(0.99, 'etcd_server_apply_duration_seconds')
            },
            'traffic': {
                'reads_per_sec': self.rate('etcd_mvcc_range_total'),
                'writes_per_sec': self.rate('etcd_mvcc_put_total'),
                'watches_active': self.gauge('etcd_mvcc_watcher_total')
            },
            'errors': {
                'failed_proposals': self.rate('etcd_server_proposals_failed_total'),
                'slow_applies': self.rate('etcd_server_slow_apply_total'),
                'leader_changes': self.rate('etcd_server_leader_changes_seen_total')
            },
            'saturation': {
                'db_size_bytes': self.gauge('etcd_mvcc_db_total_size_in_bytes'),
                'memory_usage': self.gauge('process_resident_memory_bytes'),
                'open_fds': self.gauge('process_open_fds')
            }
        }
```

## Apache ZooKeeper: The Veteran

### Production Architecture
```java
// ZooKeeper ensemble configuration
public class ZooKeeperConfig {
    // Odd number for clear majority
    private static final int ENSEMBLE_SIZE = 5;

    // Distributed across failure domains
    private static final String[] SERVERS = {
        "zk1.dc1.example.com:2888:3888",  // DC1, Rack A
        "zk2.dc1.example.com:2888:3888",  // DC1, Rack B
        "zk3.dc2.example.com:2888:3888",  // DC2, Rack A
        "zk4.dc2.example.com:2888:3888",  // DC2, Rack B
        "zk5.dc3.example.com:2888:3888"   // DC3, Rack A
    };

    // Hierarchical quorums for WAN deployment
    private static final String HIERARCHICAL_QUORUM =
        "group.1=1:2:3\n" +
        "group.2=4:5\n" +
        "weight.1=1\n" +
        "weight.2=1\n" +
        "weight.3=1\n" +
        "weight.4=1\n" +
        "weight.5=1";
}
```

### Common Production Issues

#### Issue 1: Connection Storms
```python
class ZooKeeperConnectionManager:
    """Handle connection storms after recovery"""

    def __init__(self):
        self.backoff = ExponentialBackoff(
            initial=0.1,
            maximum=30.0,
            multiplier=2.0
        )

    def connect_with_jitter(self, servers):
        """Add jitter to prevent thundering herd"""
        # Add random jitter
        jitter = random.uniform(0, 5.0)
        time.sleep(jitter)

        attempt = 0
        while True:
            try:
                return self.connect(servers)
            except ConnectionFailed:
                delay = self.backoff.next_delay(attempt)
                time.sleep(delay)
                attempt += 1
```

#### Issue 2: Snapshot Overhead
```bash
# ZooKeeper snapshot configuration
# Balance between recovery time and performance impact

# Snapshot every 100,000 transactions
snapCount=100000

# Retain 3 snapshots
autopurge.snapRetainCount=3

# Purge old snapshots every hour
autopurge.purgeInterval=1
```

## CockroachDB: Distributed SQL

### Multi-Raft Architecture
CockroachDB uses one Raft group per range (64MB of data):

```python
class CockroachRange:
    """Each range is a separate Raft group"""

    def __init__(self, range_id, start_key, end_key):
        self.range_id = range_id
        self.start_key = start_key
        self.end_key = end_key
        self.raft_group = RaftGroup(
            group_id=f"range_{range_id}",
            members=self.select_replicas()
        )

    def select_replicas(self):
        """Intelligent replica placement"""
        constraints = [
            'different_racks',
            'different_zones',
            'minimize_latency',
            'balance_load'
        ]
        return self.allocator.place_replicas(
            num_replicas=3,
            constraints=constraints
        )
```

### Production Optimizations

#### Optimization 1: Follower Reads
```sql
-- Read from followers for better load distribution
SET CLUSTER SETTING kv.follower_read.target_multiple = 3;

-- Allow stale reads for performance
BEGIN AS OF SYSTEM TIME '-10s';
SELECT * FROM large_table;
COMMIT;
```

#### Optimization 2: Range Splits
```python
def auto_split_ranges(self):
    """Split ranges that grow too large"""
    for range in self.ranges:
        if range.size_bytes > 512 * 1024 * 1024:  # 512MB
            # Find split point
            split_key = range.find_median_key()

            # Create new Raft groups
            left_range = Range(
                start=range.start_key,
                end=split_key
            )
            right_range = Range(
                start=split_key,
                end=range.end_key
            )

            # Atomic split
            self.execute_split(range, left_range, right_range)
```

## Kafka: Event Streaming

### KRaft: Kafka Without ZooKeeper
Kafka's new consensus layer:

```python
class KRaftController:
    """Kafka's internal consensus implementation"""

    def __init__(self):
        self.metadata_log = RaftLog()
        self.controller_quorum = [
            'controller-1:9093',
            'controller-2:9093',
            'controller-3:9093'
        ]

    def handle_metadata_change(self, change):
        """All metadata changes go through Raft"""
        # Propose change to Raft
        entry = MetadataLogEntry(
            type=change.type,
            payload=change.serialize()
        )

        # Wait for consensus
        if self.raft.propose(entry):
            # Apply to local state
            self.apply_metadata_change(change)

            # Notify brokers
            self.broadcast_metadata_update(change)
```

### Production Challenges

#### Challenge: Coordinating ISR Updates
```python
class ISRManager:
    """In-Sync Replica management"""

    def update_isr(self, partition, new_isr):
        """Coordinate ISR updates through consensus"""
        # Must go through controller
        update = ISRUpdate(
            topic=partition.topic,
            partition=partition.id,
            new_isr=new_isr,
            leader_epoch=partition.leader_epoch
        )

        # Use consensus to ensure consistency
        return self.controller.propose_isr_update(update)

    def shrink_isr_on_failure(self, partition, failed_replica):
        """Remove failed replica from ISR"""
        current_isr = partition.isr
        new_isr = [r for r in current_isr if r != failed_replica]

        # Must maintain min.insync.replicas
        if len(new_isr) < self.min_insync_replicas:
            # Partition goes offline
            partition.go_offline()
            raise InsufficientReplicasException()

        return self.update_isr(partition, new_isr)
```

## Consul: Service Mesh

### Consensus for Service Discovery
```python
class ConsulCatalog:
    """Service catalog backed by Raft"""

    def register_service(self, service):
        """Register service through consensus"""
        registration = ServiceRegistration(
            id=service.id,
            name=service.name,
            address=service.address,
            port=service.port,
            health_checks=service.health_checks,
            metadata=service.metadata
        )

        # Write to Raft log
        if self.raft.propose(registration):
            # Update local catalog
            self.catalog[service.id] = service

            # Trigger health checks
            self.health_checker.start_checking(service)

    def handle_node_failure(self, node_id):
        """Clean up services when node fails"""
        # Find all services on failed node
        affected_services = [
            s for s in self.catalog.values()
            if s.node_id == node_id
        ]

        # Deregister through consensus
        for service in affected_services:
            deregistration = ServiceDeregistration(
                id=service.id,
                reason='node_failure'
            )
            self.raft.propose(deregistration)
```

## Production Best Practices

### 1. Deployment Topology
```python
def plan_consensus_deployment(num_nodes):
    """Best practices for deployment"""
    if num_nodes < 3:
        raise ValueError("Need at least 3 nodes for fault tolerance")

    if num_nodes % 2 == 0:
        print(f"Warning: Even number ({num_nodes}) provides no benefit over {num_nodes-1}")

    if num_nodes > 7:
        print(f"Warning: {num_nodes} nodes will have high latency")

    # Optimal configurations
    configs = {
        3: "Tolerates 1 failure - good for dev/test",
        5: "Tolerates 2 failures - recommended for production",
        7: "Tolerates 3 failures - for critical systems"
    }

    return configs.get(num_nodes, "Non-standard configuration")
```

### 2. Monitoring and Alerting
```yaml
# Prometheus rules for consensus monitoring
groups:
  - name: consensus_alerts
    rules:
      - alert: HighLeaderElectionRate
        expr: rate(leader_elections_total[5m]) > 0.1
        annotations:
          summary: "Excessive leader elections"
          runbook: "Check network latency and disk I/O"

      - alert: ConsensusLagHigh
        expr: consensus_commit_lag_seconds > 1
        annotations:
          summary: "Consensus commits are slow"
          runbook: "Check follower health and network"

      - alert: QuorumAtRisk
        expr: consensus_healthy_members <= (consensus_total_members / 2)
        annotations:
          summary: "Close to losing quorum"
          runbook: "Restore failed members immediately"
```

### 3. Backup and Recovery
```bash
#!/bin/bash
# Consensus backup strategy

backup_consensus_data() {
    local node=$1
    local backup_dir="/backups/consensus/$(date +%Y%m%d_%H%M%S)"

    # Stop node to get consistent snapshot
    systemctl stop consensus-node

    # Backup data directory
    cp -r /var/lib/consensus "$backup_dir/"

    # Backup configuration
    cp /etc/consensus/config.yaml "$backup_dir/"

    # Capture current term/index for recovery
    echo "term: $(get_current_term)" > "$backup_dir/metadata"
    echo "index: $(get_last_index)" >> "$backup_dir/metadata"

    # Restart node
    systemctl start consensus-node

    # Verify node rejoined
    wait_for_healthy_state
}
```

### 4. Chaos Testing
```python
class ConsensusChaosTesting:
    """Test consensus under failure conditions"""

    def test_partition_tolerance(self):
        """Test behavior during network partition"""
        # Create partition
        self.network.partition(['node1', 'node2'], ['node3', 'node4', 'node5'])

        # Verify minority cannot make progress
        with pytest.raises(NoQuorumException):
            self.cluster['node1'].propose('value')

        # Verify majority continues
        result = self.cluster['node3'].propose('value')
        assert result.success

        # Heal partition
        self.network.heal()

        # Verify convergence
        self.wait_for_convergence()

    def test_leader_crash(self):
        """Test leader failure handling"""
        leader = self.cluster.get_leader()

        # Crash leader
        leader.crash()

        # Measure election time
        start = time.time()
        new_leader = self.wait_for_new_leader()
        election_time = time.time() - start

        assert election_time < 5.0  # Should elect within 5 seconds
```

## Lessons Learned

### Lesson 1: Network Matters More Than CPU
Most consensus failures come from network issues, not CPU limitations.

### Lesson 2: Disk Latency Is Critical
Slow disks (especially WAL writes) cause leader elections.

### Lesson 3: Monitor Everything
You can't debug what you can't see. Comprehensive monitoring is essential.

### Lesson 4: Test Failures Continuously
Regular chaos testing finds problems before they hit production.

### Lesson 5: Understand Your Guarantees
Know exactly what your consensus system promises—and what it doesn't.

## Summary

Production consensus requires:

1. **Careful deployment planning** - Odd numbers, geographic distribution
2. **Comprehensive monitoring** - Latency, elections, quorum health
3. **Operational procedures** - Backup, recovery, maintenance
4. **Continuous testing** - Chaos engineering, failure injection
5. **Deep understanding** - Know the algorithm and implementation

The difference between theory and production is operations.

---

> "In production, consensus is 20% algorithm and 80% operations."

Continue to [Evidence & Quorums →](evidence-quorums.md)