# Production Lessons: What We Learned the Hard Way

## The MongoDB Ransomware Incident (2017)

> "We lost 40% of our user data. The backups were corrupted. The replicas had the same corruption. This is our post-mortem."

In 2017, a SaaS company suffered a catastrophic data loss incident costing millions in customer value. The root cause? They ran MongoDB with default settings: **no authentication, no replication, listening on public IP**. Hackers deleted their data and left a ransom note. But this wasn't really about security—it was about not understanding the storage system they chose.

**Note**: This incident represents a well-documented pattern from 2017 when thousands of MongoDB instances were compromised in similar ransomware attacks, resulting from using default configurations in production.

## Lesson 1: Defaults Are Rarely Production-Ready

### The MongoDB Wake-Up Call

```yaml
# Default MongoDB config (DON'T USE IN PRODUCTION!)
systemLog:
  destination: file
  path: /var/log/mongodb/mongod.log
storage:
  dbPath: /var/lib/mongo
net:
  port: 27017
  bindIp: 0.0.0.0  # DANGER: Listens on all interfaces!
security:
  authorization: disabled  # DANGER: No authentication!
```

Production-ready configuration:
```yaml
# Production MongoDB config
systemLog:
  destination: file
  path: /var/log/mongodb/mongod.log
  logAppend: true
  logRotate: reopen

storage:
  dbPath: /var/lib/mongo
  journal:
    enabled: true
  engine: wiredTiger
  wiredTiger:
    engineConfig:
      cacheSizeGB: 4

net:
  port: 27017
  bindIp: 127.0.0.1,10.0.0.5  # Only specific interfaces
  ssl:
    mode: requireSSL
    PEMKeyFile: /etc/ssl/mongodb.pem

security:
  authorization: enabled
  javascriptEnabled: false

replication:
  replSetName: prod-replica-set

sharding:
  clusterRole: shardsvr
```

### The Elasticsearch Apocalypse

```python
# How companies accidentally expose data
class ElasticsearchMisconfiguration:
    """Real incidents from production"""

    def common_mistakes(self):
        mistakes = [
            "No authentication (pre-6.8 default)",
            "Listening on 0.0.0.0 instead of localhost",
            "No TLS encryption",
            "Scripting enabled without sandboxing",
            "Dynamic mapping creating field explosion",
            "No backup strategy"
        ]

        # Result: 36,000 exposed databases (2019 scan)
        # Containing: medical records, financial data, PII
```

## Lesson 2: Replication Doesn't Mean Backup

### The GitLab Database Incident (2017)

GitLab.com deleted 300GB of production data. Here's how:

```bash
# What happened (simplified)
# 1. Engineer intended to remove secondary database
$ sudo rm -rf /var/opt/gitlab/postgresql/data

# 2. But was on PRIMARY server (wrong terminal)
# 3. Replication faithfully replicated the deletion
# 4. Backups hadn't run for weeks
# 5. Recovery took 18 hours
```

### Proper Backup Strategy

```python
class BackupStrategy:
    """Defense in depth"""

    def __init__(self):
        self.layers = {
            'continuous': 'WAL archiving / binlog',
            'snapshots': 'Hourly filesystem snapshots',
            'daily': 'Full backup to different region',
            'weekly': 'Full backup to different cloud',
            'monthly': 'Full backup to cold storage',
            'yearly': 'Immutable archive'
        }

    def backup_checklist(self):
        return [
            "✓ Automated backups running?",
            "✓ Backups in different region?",
            "✓ Backups tested by restoration?",
            "✓ Point-in-time recovery tested?",
            "✓ Backup monitoring and alerting?",
            "✓ Encryption at rest and in transit?",
            "✓ Access controls on backups?",
            "✓ Compliance with retention policy?"
        ]

    def test_restoration(self):
        """Actually restore, don't assume"""
        # Weekly restoration drill
        backup = self.get_latest_backup()
        test_env = self.spin_up_test_environment()

        try:
            test_env.restore(backup)
            test_env.verify_data_integrity()
            test_env.run_smoke_tests()
        except RestorationFailed as e:
            self.page_oncall(severity='critical')
```

## Lesson 3: Eventual Consistency Is Harder Than You Think

### The Double-Charge Bug

```python
class EventualConsistencyBug:
    """Real production bug that cost $50K"""

    def problematic_code(self):
        # User clicks "Pay" twice quickly
        # Request 1 and Request 2 run in parallel

        # Request 1: Check balance
        balance = dynamodb.get_item(
            Key={'user_id': user_id},
            ConsistentRead=False  # Default: eventual consistency
        )
        # Sees balance = $1000

        # Request 2: Check balance (100ms later)
        balance = dynamodb.get_item(
            Key={'user_id': user_id},
            ConsistentRead=False
        )
        # ALSO sees balance = $1000 (stale read!)

        # Both approve $600 charge
        # User gets charged twice!

    def fixed_code(self):
        # Solution 1: Strong consistency
        balance = dynamodb.get_item(
            Key={'user_id': user_id},
            ConsistentRead=True  # Forces strong read
        )

        # Solution 2: Idempotency key
        charge_id = f"{user_id}:{invoice_id}:{timestamp}"
        dynamodb.put_item(
            Item={'charge_id': charge_id, 'amount': amount},
            ConditionExpression='attribute_not_exists(charge_id)'
        )
```

## Lesson 4: Scaling Reads != Scaling Writes

### The Redis Meltdown

```python
class RedisScalingFail:
    """Black Friday 2019 incident"""

    def what_happened(self):
        timeline = [
            "10:00 - Black Friday sale starts",
            "10:01 - Traffic spike 10x normal",
            "10:02 - Redis CPU at 100%",
            "10:03 - Added read replicas",
            "10:05 - Reads scaled, but writes bottlenecked",
            "10:06 - Session writes failing",
            "10:07 - Users can't add to cart",
            "10:15 - Lost $2M in sales"
        ]

    def root_cause(self):
        # Redis is single-threaded
        # Master handles ALL writes
        # Read replicas don't help with writes
        # Session writes were the bottleneck

    def solution(self):
        # Shard writes across multiple masters
        def get_redis_shard(session_id):
            shard_id = hash(session_id) % num_shards
            return redis_shards[shard_id]

        # Or use Redis Cluster
        redis_cluster = RedisCluster(
            startup_nodes=[
                {"host": "127.0.0.1", "port": "7000"},
                {"host": "127.0.0.1", "port": "7001"},
                {"host": "127.0.0.1", "port": "7002"}
            ]
        )
```

## Lesson 5: Network Partitions Really Happen

### The AWS us-east-1 Outage

```python
class NetworkPartitionReality:
    """Real outages that happened"""

    def famous_partitions(self):
        return [
            {
                'date': '2011-04-21',
                'service': 'AWS us-east-1',
                'duration': '4 days',
                'cause': 'Network configuration error',
                'impact': 'Netflix, Reddit, Foursquare down'
            },
            {
                'date': '2017-02-28',
                'service': 'AWS S3',
                'duration': '4 hours',
                'cause': 'Typo in debugging tool',
                'impact': 'Half the internet broken'
            },
            {
                'date': '2021-12-07',
                'service': 'AWS us-east-1',
                'duration': '7 hours',
                'cause': 'Network device failure',
                'impact': 'Disney+, Netflix, Ring down'
            }
        ]

    def partition_survival_strategies(self):
        strategies = {
            'detect': 'Heartbeats, gossip protocols',
            'decide': 'Sacrifice consistency OR availability',
            'degrade': 'Graceful degradation',
            'repair': 'Automatic reconciliation'
        }

        # Example: Multi-region active-active
        def handle_region_partition(self):
            if self.detect_partition():
                if self.is_minority_partition():
                    # Stop writes, serve stale reads
                    self.enter_read_only_mode()
                else:
                    # Continue, track divergence
                    self.enable_conflict_tracking()

            # After partition heals
            self.reconcile_conflicts()
```

## Lesson 6: Monitoring Production Storage

### What to Monitor

```python
class StorageMonitoring:
    """Metrics that matter in production"""

    def golden_signals(self):
        return {
            'latency': {
                'read_p50': 'ms',
                'read_p99': 'ms',
                'write_p50': 'ms',
                'write_p99': 'ms'
            },
            'traffic': {
                'reads_per_sec': 'ops',
                'writes_per_sec': 'ops',
                'bytes_in': 'MB/s',
                'bytes_out': 'MB/s'
            },
            'errors': {
                'connection_errors': 'count',
                'timeout_errors': 'count',
                'consistency_violations': 'count'
            },
            'saturation': {
                'disk_usage': '%',
                'memory_usage': '%',
                'connection_pool': '%',
                'replication_lag': 'seconds'
            }
        }

    def alerting_rules(self):
        return """
        - alert: HighReplicationLag
          expr: mysql_slave_lag_seconds > 10
          for: 5m
          annotations:
            summary: "Replication lag is {{ $value }} seconds"

        - alert: DiskSpaceLow
          expr: disk_usage_percent > 85
          for: 10m
          annotations:
            summary: "Disk usage at {{ $value }}%"

        - alert: ConnectionPoolExhausted
          expr: connection_pool_usage > 0.9
          for: 1m
          annotations:
            summary: "Connection pool at {{ $value }}% capacity"
        """
```

### Debugging Production Issues

```python
class ProductionDebugging:
    """How to diagnose storage problems"""

    def slow_queries(self):
        # PostgreSQL
        sql = """
        SELECT query, calls, mean_time, max_time
        FROM pg_stat_statements
        ORDER BY mean_time DESC
        LIMIT 10;
        """

        # MongoDB
        mongo_cmd = """
        db.currentOp({
            "secs_running": { "$gte": 3 }
        })
        """

        # Redis
        redis_cmd = "SLOWLOG GET 10"

    def lock_contention(self):
        # MySQL
        sql = """
        SELECT * FROM information_schema.innodb_lock_waits;
        """

        # PostgreSQL
        sql = """
        SELECT blocked_locks.pid AS blocked_pid,
               blocking_locks.pid AS blocking_pid,
               blocked_activity.query AS blocked_query,
               blocking_activity.query AS blocking_query
        FROM pg_catalog.pg_locks blocked_locks
        JOIN pg_catalog.pg_locks blocking_locks
            ON blocking_locks.locktype = blocked_locks.locktype
        WHERE NOT blocked_locks.granted;
        """
```

## Lesson 7: Capacity Planning

### The Thanksgiving Surprise

```python
class CapacityPlanningFail:
    """True story from major retailer"""

    def what_happened(self):
        # Wednesday before Thanksgiving
        disk_usage = 0.75  # 75% full
        growth_rate = 0.01  # 1% per day normally

        # Thursday (Thanksgiving)
        disk_usage = 0.76  # Expected

        # Friday (Black Friday)
        disk_usage = 0.95  # Explosion of analytics!

        # Saturday
        disk_usage = 1.00  # Database down
        # Emergency cloud migration at 3am

    def proper_capacity_planning(self):
        def predict_usage(current, days_ahead):
            # Account for seasonality
            seasonal_multiplier = self.get_seasonal_factor(days_ahead)

            # Account for growth
            growth_factor = (1 + daily_growth_rate) ** days_ahead

            # Add safety margin
            safety_margin = 1.5

            predicted = current * growth_factor * seasonal_multiplier * safety_margin

            if predicted > 0.7:  # 70% threshold
                self.order_more_capacity()
```

## Lesson 8: The Human Factor

### The 3am Disaster

```python
class HumanFactors:
    """Most outages are human error"""

    def common_mistakes(self):
        return [
            "Running commands on wrong server",
            "Forgetting WHERE clause in UPDATE",
            "Dropping production instead of staging",
            "Applying wrong migration",
            "Misconfiguring replication",
            "Ignoring backup failures"
        ]

    def safeguards(self):
        return {
            'colored_prompts': 'Red for production, green for staging',
            'confirmation': 'Type environment name to confirm',
            'readonly_users': 'Default to read-only access',
            'audit_logging': 'Log all admin actions',
            'peer_review': 'Two-person rule for critical ops',
            'automation': 'Reduce human interaction',
            'runbooks': 'Step-by-step procedures',
            'chaos_engineering': 'Practice failures'
        }
```

## War Stories from the Trenches

### Story 1: The Cascade Failure

```
Company: Social Media Startup
Database: Cassandra
What happened:
1. One node ran out of disk space
2. Operator increased replication factor to "fix" it
3. This INCREASED disk usage on all nodes
4. Cascade of nodes running out of space
5. Entire cluster down

Lesson: Understand the system before "fixing"
```

### Story 2: The Phantom Writes

```
Company: Financial Services
Database: MongoDB
What happened:
1. Network partition split cluster
2. Both sides elected primary (split brain)
3. Both accepted writes
4. Partition healed
5. Half the transactions lost

Lesson: Configure proper quorum (majority)
```

### Story 3: The Time Bomb

```
Company: E-commerce Platform
Database: MySQL
What happened:
1. AUTO_INCREMENT reached max INT (2,147,483,647)
2. Next insert failed
3. All orders stopped processing
4. Took 6 hours to ALTER TABLE to BIGINT

Lesson: Monitor approaching limits
```

## The Checklist

### Production Readiness Checklist

```markdown
## Before Going to Production

### Configuration
- [ ] Authentication enabled and tested
- [ ] Encryption in transit (TLS/SSL)
- [ ] Encryption at rest configured
- [ ] Network ACLs restrict access
- [ ] Resource limits configured

### High Availability
- [ ] Replication configured (min 3 nodes)
- [ ] Automatic failover tested
- [ ] Split-brain prevention configured
- [ ] Read replicas for scaling
- [ ] Multi-region deployment (if needed)

### Backup & Recovery
- [ ] Automated backups scheduled
- [ ] Backups stored in different region
- [ ] Point-in-time recovery tested
- [ ] Restoration procedure documented
- [ ] Recovery time objective (RTO) met

### Monitoring
- [ ] Metrics collection configured
- [ ] Alerting rules defined
- [ ] Dashboard created
- [ ] Log aggregation setup
- [ ] Distributed tracing enabled

### Operations
- [ ] Runbooks written
- [ ] On-call rotation defined
- [ ] Escalation path documented
- [ ] Chaos engineering tests run
- [ ] Load testing completed

### Security
- [ ] Security scan completed
- [ ] Penetration testing done
- [ ] Access controls reviewed
- [ ] Audit logging enabled
- [ ] Compliance requirements met
```

## Summary: Hard-Won Wisdom

After thousands of production incidents, patterns emerge:

### Universal Truths

1. **Everything fails** - Design for failure
2. **Defaults are dangerous** - Configure explicitly
3. **Backup != Replication** - They solve different problems
4. **Monitoring is not optional** - You can't fix what you can't see
5. **Testing prevents most outages** - Chaos engineering works
6. **Humans make mistakes** - Build safeguards
7. **Capacity runs out** - Plan ahead
8. **Networks partition** - CAP theorem is real

### The Learning Organization

```python
class LearningFromFailure:
    """Turn incidents into improvements"""

    def post_mortem_process(self):
        return {
            'immediate': 'Fix the problem',
            'document': 'Write blameless post-mortem',
            'analyze': 'Find root causes (5 whys)',
            'prevent': 'Add safeguards',
            'share': 'Teach others',
            'test': 'Chaos engineering',
            'improve': 'Update runbooks'
        }

    def culture_of_learning(self):
        principles = [
            "Blameless post-mortems",
            "Share failures openly",
            "Reward finding problems",
            "Practice incident response",
            "Learn from others' failures",
            "Question assumptions",
            "Verify everything"
        ]
```

The path to production wisdom is paved with outages. Each incident teaches something new. The key is to learn not just from your own failures, but from the entire community's collective experience.

Remember: **In production, the question isn't if you'll have a storage incident, it's when. The difference between disaster and minor inconvenience is preparation.**

---

**Mental Model**: Production storage systems accumulate evidence of problems (metrics, logs, errors) that must be actively monitored and interpreted to maintain invariants (availability, durability, consistency) across different operational modes (normal, degraded, emergency).

End of Chapter 6: The Storage Revolution