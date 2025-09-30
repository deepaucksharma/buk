# Chapter 6: The Storage Revolution
## Exhaustive Detailed Table of Contents

### Chapter Blueprint
```
INVARIANT FOCUS
Primary: DURABILITY (data survives failures and time)
Supporting: CONSISTENCY (reads see expected state), PERFORMANCE (meet latency/throughput needs)

UNCERTAINTY ADDRESSED
Cannot know: Future access patterns, hardware failures, optimal data model
Cost to know: Schema migration overhead, consistency coordination, index maintenance
Acceptable doubt: Eventually consistent reads, probabilistic structures, approximate aggregates

EVIDENCE GENERATED
Type(s): Write-ahead logs, commit records, index entries, compaction logs
Scope: Row to table to database   Lifetime: Until compaction/garbage collection
Binding: Transaction boundaries   Transitivity: Depends on isolation level
Revocation: Rollback, compensating transactions

GUARANTEE VECTOR
Input G: ⟨Row, None, Uncommitted, Cache, None, None⟩
Output G: ⟨Database, Serial, Committed, Durable, Exactly-once, Authorized⟩
Upgrades: Add 2PC for distributed transactions
Downgrades: Relax to eventual consistency

MODE MATRIX
Floor: Durability preserved (never lose committed data)
Target: ACID transactions with target latency
Degraded: Read-only mode, eventual consistency
Recovery: Replay from WAL, rebuild indexes

DUALITIES
Structure/Flexibility: Schema vs schemaless
Consistency/Performance: ACID vs BASE
Memory/Disk: Speed vs durability

IRREDUCIBLE SENTENCE
"The storage revolution represents the journey from one-size-fits-all relational
databases to polyglot persistence, where each data model serves its optimal use case."
```

---

## Part 6.1: ACID to BASE Journey

### 6.1.1 ACID Properties Deep Dive
#### 6.1.1.1 Atomicity Implementation
- **All or Nothing Semantics**
  ```python
  class AtomicityImplementation:
      def __init__(self):
          self.undo_log = []
          self.redo_log = []
          self.shadow_pages = {}

      def write_ahead_logging(self):
          """
          WAL implementation for atomicity
          """
          class WAL:
              def __init__(self):
                  self.log_buffer = []
                  self.log_file = open('wal.log', 'ab')
                  self.lsn = 0  # Log Sequence Number

              def begin_transaction(self, tx_id):
                  """Log transaction start"""
                  log_record = {
                      'lsn': self.next_lsn(),
                      'type': 'BEGIN',
                      'tx_id': tx_id,
                      'timestamp': time.time()
                  }
                  self.append_log(log_record)
                  return log_record['lsn']

              def log_update(self, tx_id, page_id, offset, old_val, new_val):
                  """Log before image for undo"""
                  log_record = {
                      'lsn': self.next_lsn(),
                      'type': 'UPDATE',
                      'tx_id': tx_id,
                      'page_id': page_id,
                      'offset': offset,
                      'before': old_val,
                      'after': new_val
                  }
                  self.append_log(log_record)
                  return log_record['lsn']

              def commit(self, tx_id):
                  """Log commit - point of durability"""
                  log_record = {
                      'lsn': self.next_lsn(),
                      'type': 'COMMIT',
                      'tx_id': tx_id
                  }
                  self.append_log(log_record)
                  self.force_log()  # Ensure durability
                  return {'status': 'committed', 'lsn': log_record['lsn']}

              def rollback(self, tx_id):
                  """Undo all changes of transaction"""
                  # Scan log backwards
                  for record in reversed(self.get_tx_records(tx_id)):
                      if record['type'] == 'UPDATE':
                          # Restore before image
                          self.restore_page(record['page_id'],
                                          record['offset'],
                                          record['before'])

                  # Log rollback completion
                  self.append_log({
                      'lsn': self.next_lsn(),
                      'type': 'ROLLBACK',
                      'tx_id': tx_id
                  })

          return WAL()

      def shadow_paging(self):
          """
          Shadow paging for atomicity
          """
          return {
              'concept': 'Keep two page tables',
              'current': 'Active page table',
              'shadow': 'Committed state',
              'commit': 'Atomic pointer swap',
              'rollback': 'Discard current',
              'advantage': 'No undo needed',
              'disadvantage': 'Fragmentation',
              'evidence': 'Page table pointers'
          }
  ```
  - Evidence: WAL records, commit logs
  - Guarantee: All or nothing

#### 6.1.1.2 Consistency Rules and Constraints
- **Maintaining Invariants**
  ```python
  class ConsistencyEnforcement:
      def constraint_types(self):
          """
          Database constraint types
          """
          return {
              'entity_integrity': {
                  'primary_key': 'Unique, not null',
                  'implementation': 'Unique index',
                  'check': 'On insert/update'
              },
              'referential_integrity': {
                  'foreign_key': 'References exist',
                  'cascade_options': ['RESTRICT', 'CASCADE', 'SET NULL'],
                  'check': 'On delete/update parent'
              },
              'domain_integrity': {
                  'check_constraints': 'Value validation',
                  'data_types': 'Type safety',
                  'not_null': 'Presence required'
              },
              'user_defined': {
                  'triggers': 'Custom logic',
                  'stored_procedures': 'Complex rules',
                  'application_rules': 'Business logic'
              }
          }

      def trigger_implementation(self):
          """
          Trigger-based consistency
          """
          class TriggerEngine:
              def __init__(self):
                  self.triggers = defaultdict(list)

              def create_trigger(self, definition):
                  """
                  Register consistency trigger
                  """
                  trigger = {
                      'name': definition['name'],
                      'table': definition['table'],
                      'timing': definition['timing'],  # BEFORE/AFTER
                      'event': definition['event'],    # INSERT/UPDATE/DELETE
                      'condition': definition.get('when'),
                      'action': definition['action']
                  }

                  key = (trigger['table'], trigger['timing'], trigger['event'])
                  self.triggers[key].append(trigger)

              def fire_triggers(self, table, timing, event, old_row, new_row):
                  """
                  Execute relevant triggers
                  """
                  key = (table, timing, event)
                  results = []

                  for trigger in self.triggers.get(key, []):
                      if self.evaluate_condition(trigger['condition'], old_row, new_row):
                          result = self.execute_action(trigger['action'], old_row, new_row)
                          results.append(result)

                          # BEFORE triggers can modify new_row
                          if timing == 'BEFORE' and result.get('new_row'):
                              new_row = result['new_row']

                  return {
                      'fired': len(results),
                      'new_row': new_row,
                      'evidence': 'trigger_log'
                  }

          return TriggerEngine()
  ```
  - Evidence: Constraint violation logs
  - Enforcement: Immediate or deferred

#### 6.1.1.3 Isolation Levels
- **Concurrent Transaction Control**
  ```python
  class IsolationLevels:
      def isolation_phenomena(self):
          """
          Phenomena prevented by isolation levels
          """
          return {
              'dirty_read': {
                  'description': 'Read uncommitted data',
                  'prevented_by': ['READ_COMMITTED', 'REPEATABLE_READ', 'SERIALIZABLE']
              },
              'non_repeatable_read': {
                  'description': 'Different reads in same transaction',
                  'prevented_by': ['REPEATABLE_READ', 'SERIALIZABLE']
              },
              'phantom_read': {
                  'description': 'New rows appear in range',
                  'prevented_by': ['SERIALIZABLE']
              },
              'lost_update': {
                  'description': 'Concurrent updates overwrite',
                  'prevented_by': ['REPEATABLE_READ', 'SERIALIZABLE']
              },
              'write_skew': {
                  'description': 'Constraint violation from concurrent writes',
                  'prevented_by': ['SERIALIZABLE']
              }
          }

      def mvcc_implementation(self):
          """
          Multi-Version Concurrency Control
          """
          class MVCC:
              def __init__(self):
                  self.versions = defaultdict(list)
                  self.active_transactions = {}
                  self.next_tx_id = 1

              def begin_transaction(self, isolation_level):
                  """Start transaction with snapshot"""
                  tx_id = self.next_tx_id
                  self.next_tx_id += 1

                  snapshot = {
                      'tx_id': tx_id,
                      'start_time': time.time(),
                      'isolation': isolation_level,
                      'snapshot': self.get_snapshot(isolation_level),
                      'read_set': set(),
                      'write_set': set()
                  }

                  self.active_transactions[tx_id] = snapshot
                  return tx_id

              def read(self, tx_id, key):
                  """Read visible version"""
                  tx = self.active_transactions[tx_id]

                  # Find visible version
                  for version in reversed(self.versions[key]):
                      if self.is_visible(version, tx):
                          tx['read_set'].add((key, version['version_id']))
                          return version['value']

                  return None  # No visible version

              def write(self, tx_id, key, value):
                  """Create new version"""
                  tx = self.active_transactions[tx_id]

                  new_version = {
                      'tx_id': tx_id,
                      'version_id': self.next_version_id(),
                      'value': value,
                      'created': time.time(),
                      'committed': False
                  }

                  tx['write_set'].add((key, new_version['version_id']))
                  self.versions[key].append(new_version)

                  return new_version['version_id']

              def is_visible(self, version, tx):
                  """Check if version visible to transaction"""
                  if tx['isolation'] == 'READ_UNCOMMITTED':
                      return True

                  if tx['isolation'] == 'READ_COMMITTED':
                      return version['committed']

                  if tx['isolation'] == 'REPEATABLE_READ':
                      return version['committed'] and \
                             version['tx_id'] in tx['snapshot']

                  if tx['isolation'] == 'SERIALIZABLE':
                      # Additional checks for serializability
                      return self.check_serializable(version, tx)

          return MVCC()
  ```
  - Evidence: Version chains, snapshot timestamps
  - Trade-off: Isolation vs performance

#### 6.1.1.4 Durability Mechanisms
- **Ensuring Persistence**
  ```python
  class DurabilityMechanisms:
      def storage_hierarchy(self):
          """
          Data durability levels
          """
          return {
              'cpu_cache': {
                  'durability': 'None',
                  'latency': '1-10 ns',
                  'volatile': True
              },
              'ram': {
                  'durability': 'None',
                  'latency': '100 ns',
                  'volatile': True
              },
              'ssd_cache': {
                  'durability': 'Power-fail protection',
                  'latency': '10-100 μs',
                  'volatile': 'Partially'
              },
              'ssd': {
                  'durability': 'Persistent',
                  'latency': '100-500 μs',
                  'wear': 'Limited writes'
              },
              'hdd': {
                  'durability': 'Persistent',
                  'latency': '5-10 ms',
                  'mechanical': True
              },
              'tape': {
                  'durability': '30+ years',
                  'latency': 'Minutes',
                  'archival': True
              }
          }

      def fsync_guarantees(self):
          """
          File system sync guarantees
          """
          return {
              'write()': 'Buffer cache only',
              'fsync()': 'Force to disk',
              'fdatasync()': 'Data only, not metadata',
              'O_DIRECT': 'Bypass buffer cache',
              'O_SYNC': 'Synchronous writes',
              'evidence': 'iostat metrics'
          }
  ```
  - Evidence: fsync confirmations, disk flush
  - Cost: Latency for durability

### 6.1.2 BASE Properties
#### 6.1.2.1 Basically Available
- **System Remains Operational**
  ```python
  class BasicallyAvailable:
      def availability_strategies(self):
          """
          Strategies for basic availability
          """
          return {
              'partial_failure': {
                  'strategy': 'Degrade gracefully',
                  'example': 'Read-only mode during maintenance',
                  'evidence': 'Health check responses'
              },
              'best_effort': {
                  'strategy': 'Return what you can',
                  'example': 'Stale data better than no data',
                  'evidence': 'Staleness markers'
              },
              'timeout_handling': {
                  'strategy': 'Fail fast with fallback',
                  'example': 'Return cached or default',
                  'evidence': 'Timeout counters'
              },
              'circuit_breaking': {
                  'strategy': 'Prevent cascade failures',
                  'example': 'Stop calling failing service',
                  'evidence': 'Circuit state changes'
              }
          }

      def degraded_operations(self):
          """
          Operating in degraded mode
          """
          class DegradedMode:
              def __init__(self):
                  self.mode = 'normal'
                  self.degradations = []

              def enter_degraded_mode(self, reason):
                  """Switch to degraded operations"""
                  self.mode = 'degraded'
                  self.degradations.append(reason)

                  # Adjust system behavior
                  adjustments = {
                      'disable_writes': reason in ['replication_lag', 'split_brain'],
                      'serve_stale': reason in ['cache_miss', 'timeout'],
                      'reduce_consistency': reason in ['high_load', 'partition'],
                      'limit_features': reason in ['resource_exhaustion']
                  }

                  return {
                      'mode': 'degraded',
                      'adjustments': adjustments,
                      'evidence': 'mode_change_log'
                  }

          return DegradedMode()
  ```
  - Evidence: Availability metrics
  - Goal: Stay operational

#### 6.1.2.2 Soft State
- **State May Change Without Input**
  ```python
  class SoftState:
      def ttl_mechanisms(self):
          """
          Time-to-live implementations
          """
          class TTLManager:
              def __init__(self):
                  self.items = {}
                  self.expiry_index = defaultdict(set)

              def set_with_ttl(self, key, value, ttl_seconds):
                  """Set value with expiration"""
                  expiry_time = time.time() + ttl_seconds

                  self.items[key] = {
                      'value': value,
                      'expires': expiry_time
                  }

                  # Index by expiry time for efficient cleanup
                  self.expiry_index[int(expiry_time)].add(key)

                  return {
                      'key': key,
                      'ttl': ttl_seconds,
                      'expires_at': expiry_time,
                      'evidence': 'ttl_set'
                  }

              def get(self, key):
                  """Get value if not expired"""
                  if key not in self.items:
                      return None

                  item = self.items[key]
                  if time.time() > item['expires']:
                      # Lazy deletion
                      del self.items[key]
                      return None

                  return item['value']

              def cleanup_expired(self):
                  """Background expiration"""
                  current_time = int(time.time())

                  for timestamp in list(self.expiry_index.keys()):
                      if timestamp <= current_time:
                          for key in self.expiry_index[timestamp]:
                              if key in self.items:
                                  del self.items[key]
                          del self.expiry_index[timestamp]

          return TTLManager()

      def cache_invalidation(self):
          """
          Cache coherence strategies
          """
          return {
              'ttl': 'Time-based expiration',
              'lru': 'Least recently used eviction',
              'write_through': 'Update cache and store',
              'write_behind': 'Update cache, async store',
              'refresh_ahead': 'Proactive refresh',
              'evidence': 'Cache hit/miss ratios'
          }
  ```
  - Evidence: Expiration logs
  - Nature: Ephemeral state

#### 6.1.2.3 Eventual Consistency
- **Convergence Over Time**
  ```python
  class EventualConsistency:
      def convergence_mechanisms(self):
          """
          How systems achieve eventual consistency
          """
          return {
              'anti_entropy': {
                  'method': 'Periodic reconciliation',
                  'example': 'Merkle tree exchange',
                  'frequency': 'Minutes to hours',
                  'evidence': 'Sync completion logs'
              },
              'read_repair': {
                  'method': 'Fix on read',
                  'example': 'Cassandra read path',
                  'latency': 'Added to read',
                  'evidence': 'Repair counters'
              },
              'gossip': {
                  'method': 'Epidemic propagation',
                  'example': 'Membership updates',
                  'convergence': 'O(log N) rounds',
                  'evidence': 'Gossip round metrics'
              },
              'vector_clocks': {
                  'method': 'Causal ordering',
                  'example': 'Dynamo replication',
                  'overhead': 'O(N) metadata',
                  'evidence': 'Vector clock sizes'
              }
          }

      def consistency_metrics(self):
          """
          Measuring eventual consistency
          """
          class ConsistencyMonitor:
              def __init__(self):
                  self.write_times = {}
                  self.read_times = defaultdict(list)

              def measure_consistency_window(self):
                  """
                  Time until all replicas consistent
                  """
                  windows = []

                  for key, write_time in self.write_times.items():
                      read_times = self.read_times[key]

                      # Find when all replicas saw write
                      if read_times:
                          consistency_time = max(read_times) - write_time
                          windows.append(consistency_time)

                  return {
                      'p50': percentile(windows, 50),
                      'p99': percentile(windows, 99),
                      'p999': percentile(windows, 99.9),
                      'unit': 'milliseconds',
                      'evidence': 'consistency_measurements'
                  }

              def measure_staleness(self):
                  """
                  How stale can reads be?
                  """
                  staleness_values = []

                  for replica in self.replicas:
                      lag = self.master_timestamp - replica.timestamp
                      staleness_values.append(lag)

                  return {
                      'max_staleness': max(staleness_values),
                      'avg_staleness': mean(staleness_values),
                      'evidence': 'replication_lag_metrics'
                  }

          return ConsistencyMonitor()
  ```
  - Evidence: Convergence time measurements
  - Guarantee: Eventually consistent

---

## Part 6.2: NoSQL Movement (2009)

### 6.2.1 Document Stores
#### 6.2.1.1 MongoDB Architecture
- **Document-Oriented Database**
  ```python
  class MongoDBArchitecture:
      def document_model(self):
          """
          BSON document structure
          """
          document_example = {
              '_id': ObjectId('507f1f77bcf86cd799439011'),
              'username': 'johndoe',
              'email': 'john@example.com',
              'profile': {
                  'age': 30,
                  'interests': ['coding', 'reading'],
                  'address': {
                      'street': '123 Main St',
                      'city': 'Boston',
                      'state': 'MA'
                  }
              },
              'posts': [
                  {'title': 'First Post', 'date': ISODate('2024-01-01')},
                  {'title': 'Second Post', 'date': ISODate('2024-01-02')}
              ]
          }

          return {
              'format': 'BSON (Binary JSON)',
              'schema': 'Flexible/Dynamic',
              'nesting': 'Embedded documents',
              'arrays': 'Native support',
              'size_limit': '16MB per document',
              'evidence': 'Collection statistics'
          }

      def replica_set_architecture(self):
          """
          MongoDB replica sets
          """
          class ReplicaSet:
              def __init__(self, name, members):
                  self.name = name
                  self.members = members
                  self.primary = None
                  self.secondaries = []
                  self.arbiters = []

              def election_protocol(self):
                  """
                  Primary election via Raft
                  """
                  # Raft-based election since 3.2
                  election = {
                      'protocol': 'Raft consensus',
                      'majority': len(self.members) // 2 + 1,
                      'priority': 'Configurable per member',
                      'timeout': '10 seconds default',
                      'evidence': 'rs.status() output'
                  }

                  # Elect highest priority member
                  candidates = [m for m in self.members if m.state == 'SECONDARY']
                  candidates.sort(key=lambda x: x.priority, reverse=True)

                  if candidates:
                      new_primary = candidates[0]
                      new_primary.state = 'PRIMARY'
                      self.primary = new_primary

                  return election

              def read_concern_levels(self):
                  """
                  Read consistency options
                  """
                  return {
                      'local': 'Read from primary (default)',
                      'available': 'Read from any',
                      'majority': 'Read majority-committed',
                      'linearizable': 'Linearizable reads',
                      'snapshot': 'Read from snapshot'
                  }

          return ReplicaSet('rs0', ['mongo1', 'mongo2', 'mongo3'])

      def sharding_architecture(self):
          """
          MongoDB sharding
          """
          return {
              'components': {
                  'mongos': 'Query router',
                  'config_servers': 'Metadata storage (3 or 5)',
                  'shards': 'Data storage (replica sets)'
              },
              'shard_key': {
                  'types': ['hashed', 'ranged'],
                  'choice': 'Critical for performance',
                  'immutable': 'Cannot change after sharding'
              },
              'balancer': {
                  'automatic': True,
                  'chunk_size': '64MB default',
                  'migration': 'Background process'
              },
              'evidence': 'sh.status() output'
          }
  ```
  - Evidence: oplog entries, shard statistics
  - Model: Flexible schema

#### 6.2.1.2 CouchDB and Multi-Master
- **Distributed Document Database**
  ```python
  class CouchDBArchitecture:
      def mvcc_and_revisions(self):
          """
          CouchDB revision tree
          """
          class RevisionTree:
              def __init__(self):
                  self.revisions = {}

              def update_document(self, doc_id, current_rev, new_data):
                  """
                  Create new revision
                  """
                  # Parse revision: N-hash
                  rev_num = int(current_rev.split('-')[0])
                  new_rev_num = rev_num + 1

                  # Generate new revision
                  new_rev_hash = self.hash(current_rev + str(new_data))
                  new_rev = f"{new_rev_num}-{new_rev_hash}"

                  # Store revision
                  self.revisions[doc_id] = {
                      '_id': doc_id,
                      '_rev': new_rev,
                      'data': new_data,
                      'prev_rev': current_rev
                  }

                  return {
                      'ok': True,
                      'id': doc_id,
                      'rev': new_rev,
                      'evidence': 'revision_tree'
                  }

              def handle_conflict(self, doc_id, revisions):
                  """
                  Deterministic conflict resolution
                  """
                  # CouchDB picks winner deterministically
                  winner = max(revisions, key=lambda r: (r.split('-')[0], r))

                  return {
                      'winner': winner,
                      'conflicts': [r for r in revisions if r != winner],
                      'resolution': 'deterministic',
                      'evidence': 'conflict_log'
                  }

          return RevisionTree()

      def replication_protocol(self):
          """
          CouchDB replication
          """
          class CouchReplication:
              def replicate(self, source, target):
                  """
                  CouchDB replication protocol
                  """
                  # 1. Get source changes
                  changes = source.get_changes_since(target.last_seq)

                  # 2. Get missing revisions
                  missing = target.get_missing_revisions(changes)

                  # 3. Transfer documents
                  for doc_id in missing:
                      doc = source.get_document(doc_id)
                      target.put_document(doc)

                  # 4. Update checkpoint
                  target.update_checkpoint(source.current_seq)

                  return {
                      'docs_transferred': len(missing),
                      'protocol': 'CouchDB Replication Protocol',
                      'bidirectional': True,
                      'continuous': 'Optional',
                      'evidence': '_replicator database'
                  }

          return CouchReplication()
  ```
  - Evidence: Revision trees, replication logs
  - Feature: Multi-master replication

### 6.2.2 Key-Value Stores
#### 6.2.2.1 Redis Data Structures
- **In-Memory Data Structure Store**
  ```python
  class RedisDataStructures:
      def core_data_types(self):
          """
          Redis data type implementations
          """
          return {
              'string': {
                  'operations': ['GET', 'SET', 'INCR', 'APPEND'],
                  'use_cases': ['Caching', 'Counters', 'Sessions'],
                  'max_size': '512MB'
              },
              'list': {
                  'implementation': 'Linked list or ziplist',
                  'operations': ['LPUSH', 'RPOP', 'LRANGE', 'BLPOP'],
                  'use_cases': ['Queues', 'Timeline', 'Logs']
              },
              'set': {
                  'implementation': 'Hash table or intset',
                  'operations': ['SADD', 'SINTER', 'SUNION', 'SISMEMBER'],
                  'use_cases': ['Tags', 'Unique items', 'Relations']
              },
              'sorted_set': {
                  'implementation': 'Skip list + hash table',
                  'operations': ['ZADD', 'ZRANGE', 'ZRANK'],
                  'use_cases': ['Leaderboards', 'Priority queues']
              },
              'hash': {
                  'implementation': 'Hash table or ziplist',
                  'operations': ['HSET', 'HGET', 'HINCRBY'],
                  'use_cases': ['Objects', 'User profiles']
              },
              'stream': {
                  'implementation': 'Radix tree',
                  'operations': ['XADD', 'XREAD', 'XGROUP'],
                  'use_cases': ['Event sourcing', 'Message queue']
              }
          }

      def persistence_mechanisms(self):
          """
          Redis persistence options
          """
          class RedisPersistence:
              def rdb_snapshots(self):
                  """
                  RDB (Redis Database) snapshots
                  """
                  return {
                      'mechanism': 'Point-in-time snapshots',
                      'trigger': 'SAVE, BGSAVE, or automatic',
                      'format': 'Compressed binary',
                      'config': 'save 900 1, save 300 10, save 60 10000',
                      'pros': 'Compact, fast restore',
                      'cons': 'Data loss window',
                      'evidence': 'dump.rdb file'
                  }

              def aof_logging(self):
                  """
                  AOF (Append Only File) logging
                  """
                  return {
                      'mechanism': 'Write operation log',
                      'fsync_policies': {
                          'always': 'Every write (slow, safe)',
                          'everysec': 'Every second (balanced)',
                          'no': 'OS decides (fast, risky)'
                      },
                      'rewrite': 'Background compaction',
                      'format': 'Redis protocol text',
                      'pros': 'Minimal data loss',
                      'cons': 'Larger files, slower',
                      'evidence': 'appendonly.aof file'
                  }

              def hybrid_approach(self):
                  """
                  RDB + AOF hybrid
                  """
                  return {
                      'strategy': 'Use both RDB and AOF',
                      'rdb': 'Fast recovery baseline',
                      'aof': 'Complete recovery',
                      'redis_4_0': 'AOF rewrite with RDB preamble',
                      'evidence': 'Both files present'
                  }

          return RedisPersistence()

      def redis_cluster(self):
          """
          Redis Cluster architecture
          """
          return {
              'sharding': {
                  'slots': 16384,
                  'hash_slot': 'CRC16(key) % 16384',
                  'hash_tags': '{user:1000}:* same slot'
              },
              'topology': {
                  'minimum': '3 masters',
                  'recommended': '6 nodes (3 master, 3 replica)',
                  'max_nodes': 1000
              },
              'consistency': {
                  'model': 'Eventual consistency',
                  'replication': 'Asynchronous by default',
                  'writes': 'To master only'
              },
              'failover': {
                  'detection': 'Gossip protocol',
                  'election': 'Raft-like consensus',
                  'time': '~ 1-2 seconds'
              },
              'evidence': 'CLUSTER INFO output'
          }
  ```
  - Evidence: RDB/AOF files, cluster state
  - Performance: Sub-millisecond latency

#### 6.2.2.2 DynamoDB Design
- **Managed Key-Value Store**
  ```python
  class DynamoDBDesign:
      def partition_key_design(self):
          """
          DynamoDB partition key patterns
          """
          return {
              'single_partition_key': {
                  'example': 'user_id',
                  'distribution': 'Must be uniform',
                  'hot_partition': 'Performance bottleneck'
              },
              'composite_key': {
                  'partition_key': 'user_id',
                  'sort_key': 'timestamp',
                  'queries': 'Range queries on sort key',
                  'example': 'User activity timeline'
              },
              'synthetic_keys': {
                  'pattern': 'Combine attributes',
                  'example': 'tenant#user#date',
                  'benefit': 'Better distribution'
              },
              'write_sharding': {
                  'pattern': 'Add random suffix',
                  'example': 'date + random(0-9)',
                  'benefit': 'Avoid hot partitions',
                  'tradeoff': 'Scatter-gather reads'
              }
          }

      def consistency_models(self):
          """
          DynamoDB consistency options
          """
          return {
              'eventually_consistent': {
                  'cost': '0.5 RCU per 4KB',
                  'staleness': 'Usually < 1 second',
                  'use_case': 'Read-heavy, tolerates stale'
              },
              'strongly_consistent': {
                  'cost': '1 RCU per 4KB',
                  'guarantee': 'Read after write',
                  'use_case': 'Requires latest data'
              },
              'global_tables': {
                  'consistency': 'Eventually consistent',
                  'conflict': 'Last writer wins',
                  'replication': '< 1 second typically'
              },
              'transactions': {
                  'guarantee': 'ACID across items',
                  'cost': '2x regular operations',
                  'limit': '25 items per transaction'
              }
          }

      def capacity_modes(self):
          """
          DynamoDB capacity planning
          """
          return {
              'provisioned': {
                  'model': 'Pre-allocated RCU/WCU',
                  'scaling': 'Auto-scaling available',
                  'cost': 'Pay for provisioned',
                  'burst': 'Burst capacity available'
              },
              'on_demand': {
                  'model': 'Pay per request',
                  'scaling': 'Automatic',
                  'cost': 'Pay for actual use',
                  'limit': '40K RCU/WCU per table'
              },
              'reserved': {
                  'commitment': '1 or 3 years',
                  'discount': 'Up to 77%',
                  'use_case': 'Predictable workloads'
              },
              'evidence': 'CloudWatch metrics'
          }
  ```
  - Evidence: ConsumedCapacity metrics
  - Scale: Automatic partitioning

### 6.2.3 Column-Family Stores
#### 6.2.3.1 Cassandra Architecture
- **Wide-Column Store**
  ```python
  class CassandraArchitecture:
      def data_model(self):
          """
          Cassandra data model
          """
          return {
              'keyspace': {
                  'definition': 'Database equivalent',
                  'replication': 'Per-keyspace strategy',
                  'example': "CREATE KEYSPACE app WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3}"
              },
              'table': {
                  'partition_key': 'Data distribution',
                  'clustering_key': 'Sorting within partition',
                  'columns': 'Static or dynamic',
                  'example': """
                      CREATE TABLE users (
                          user_id UUID,
                          timestamp TIMESTAMP,
                          action TEXT,
                          PRIMARY KEY (user_id, timestamp)
                      ) WITH CLUSTERING ORDER BY (timestamp DESC)
                  """
              },
              'partition': {
                  'size': 'Keep < 100MB',
                  'rows': 'Keep < 100K rows',
                  'wide_rows': 'Millions of columns possible'
              }
          }

      def consistency_levels(self):
          """
          Tunable consistency in Cassandra
          """
          consistency_levels = {
              'ANY': 'Write to any node (including hinted)',
              'ONE': 'One replica responds',
              'TWO': 'Two replicas respond',
              'THREE': 'Three replicas respond',
              'QUORUM': '(RF/2) + 1 replicas',
              'LOCAL_QUORUM': 'Quorum in local DC',
              'EACH_QUORUM': 'Quorum in each DC',
              'ALL': 'All replicas respond',
              'LOCAL_ONE': 'One replica in local DC',
              'LOCAL_SERIAL': 'Lightweight transactions local',
              'SERIAL': 'Lightweight transactions global'
          }

          return {
              'levels': consistency_levels,
              'formula': 'R + W > RF for strong consistency',
              'tradeoff': 'Consistency vs Availability vs Latency',
              'evidence': 'Driver metrics'
          }

      def storage_engine(self):
          """
          LSM-tree based storage
          """
          class LSMTree:
              def __init__(self):
                  self.memtable = {}
                  self.sstables = []
                  self.commit_log = []

              def write_path(self, key, value):
                  """
                  Cassandra write path
                  """
                  # 1. Write to commit log (durability)
                  self.commit_log.append({
                      'key': key,
                      'value': value,
                      'timestamp': time.time()
                  })

                  # 2. Write to memtable (memory)
                  self.memtable[key] = value

                  # 3. Flush memtable to SSTable when full
                  if len(self.memtable) > 100000:  # Example threshold
                      self.flush_memtable()

                  return {
                      'status': 'written',
                      'latency': 'sub-millisecond',
                      'evidence': 'commit_log'
                  }

              def flush_memtable(self):
                  """
                  Flush memtable to SSTable
                  """
                  sstable = {
                      'id': len(self.sstables),
                      'data': dict(self.memtable),
                      'bloom_filter': self.build_bloom_filter(self.memtable.keys()),
                      'index': self.build_index(self.memtable),
                      'timestamp': time.time()
                  }

                  self.sstables.append(sstable)
                  self.memtable.clear()

                  return {'sstable_id': sstable['id']}

              def compaction(self):
                  """
                  Merge and compact SSTables
                  """
                  strategies = {
                      'STCS': 'Size-Tiered Compaction',
                      'LCS': 'Leveled Compaction',
                      'TWCS': 'Time-Window Compaction'
                  }

                  # Merge overlapping SSTables
                  # Remove deleted data (tombstones)
                  # Create new consolidated SSTable

                  return {
                      'strategies': strategies,
                      'benefit': 'Improved read performance',
                      'cost': 'CPU and I/O',
                      'evidence': 'Compaction stats'
                  }

          return LSMTree()
  ```
  - Evidence: SSTable files, compaction logs
  - Scale: Linear scalability

### 6.2.4 Graph Databases
#### 6.2.4.1 Neo4j and Property Graphs
- **Native Graph Storage**
  ```python
  class Neo4jArchitecture:
      def property_graph_model(self):
          """
          Property graph data model
          """
          return {
              'nodes': {
                  'definition': 'Entities',
                  'properties': 'Key-value pairs',
                  'labels': 'Type categorization',
                  'example': '(:Person {name: "Alice", age: 30})'
              },
              'relationships': {
                  'definition': 'Connections between nodes',
                  'direction': 'Always directed',
                  'type': 'Named relationship',
                  'properties': 'Can have properties',
                  'example': '-[:KNOWS {since: 2020}]->'
              },
              'paths': {
                  'definition': 'Series of nodes and relationships',
                  'traversal': 'Index-free adjacency',
                  'performance': 'O(1) per hop'
              }
          }

      def cypher_query_language(self):
          """
          Cypher query examples
          """
          queries = {
              'create': """
                  CREATE (alice:Person {name: 'Alice'})
                  CREATE (bob:Person {name: 'Bob'})
                  CREATE (alice)-[:KNOWS]->(bob)
              """,
              'match': """
                  MATCH (p:Person)-[:KNOWS]->(friend)
                  WHERE p.name = 'Alice'
                  RETURN friend.name
              """,
              'shortest_path': """
                  MATCH path = shortestPath(
                      (start:Person {name: 'Alice'})-[*]-(end:Person {name: 'Charlie'})
                  )
                  RETURN path
              """,
              'pattern_matching': """
                  MATCH (a:Person)-[:KNOWS]->(b:Person)-[:KNOWS]->(c:Person)
                  WHERE NOT (a)-[:KNOWS]->(c)
                  RETURN a, b, c
                  LIMIT 10
              """
          }

          return {
              'queries': queries,
              'optimization': 'Query planner',
              'indexes': 'On node properties',
              'evidence': 'Query execution plan'
          }

      def storage_architecture(self):
          """
          Native graph storage
          """
          return {
              'node_store': {
                  'format': 'Fixed-size records',
                  'size': '15 bytes per node',
                  'direct_access': 'O(1) by ID'
              },
              'relationship_store': {
                  'format': 'Doubly-linked lists',
                  'size': '34 bytes per relationship',
                  'traversal': 'Pointer-based'
              },
              'property_store': {
                  'format': 'Linked property chains',
                  'types': 'Dynamic for strings/arrays'
              },
              'advantages': {
                  'traversal': 'No index lookups',
                  'performance': 'Constant time',
                  'locality': 'Related data nearby'
              },
              'evidence': 'Store file sizes'
          }
  ```
  - Evidence: Graph traversal metrics
  - Use case: Connected data

---

## Part 6.3: NewSQL Renaissance (2012)

### 6.3.1 Distributed SQL Systems
#### 6.3.1.1 Spanner's Architecture
- **Globally Distributed SQL**
  ```python
  class SpannerArchitecture:
      def true_time_transactions(self):
          """
          Spanner's transaction model
          """
          return {
              'read_write': {
                  'protocol': '2PL + 2PC',
                  'timestamp': 'TrueTime commit wait',
                  'isolation': 'External consistency',
                  'latency': '10-100ms typical'
              },
              'read_only': {
                  'protocol': 'Snapshot reads',
                  'timestamp': 'Any past timestamp',
                  'consistency': 'Global snapshot',
                  'latency': '5-10ms typical'
              },
              'bounded_staleness': {
                  'guarantee': 'Read within bound',
                  'benefit': 'No coordination',
                  'use_case': 'Analytics queries'
              }
          }

      def data_distribution(self):
          """
          Spanner's data model
          """
          return {
              'hierarchy': [
                  'Universe (deployment)',
                  'Zone (datacenter)',
                  'Zone master',
                  'Spanserver (100-1000)',
                  'Tablet (100-600MB)'
              ],
              'splits': {
                  'automatic': 'Based on size/load',
                  'key_range': 'Lexicographic order',
                  'movement': 'Automated rebalancing'
              },
              'directories': {
                  'unit': 'Movement and placement',
                  'size': 'Set of contiguous keys',
                  'placement': 'Geographic controls'
              },
              'evidence': 'Spanner metrics'
          }
  ```
  - Evidence: TrueTime bounds, commit timestamps
  - Scale: Global distribution

#### 6.3.1.2 CockroachDB Implementation
- **Open-Source Distributed SQL**
  ```python
  class CockroachDBImplementation:
      def range_based_sharding(self):
          """
          CockroachDB's range architecture
          """
          class Range:
              def __init__(self, start_key, end_key):
                  self.start_key = start_key
                  self.end_key = end_key
                  self.replicas = []
                  self.lease_holder = None
                  self.size = 0

              def split(self):
                  """
                  Split range when too large
                  """
                  if self.size > 64 * 1024 * 1024:  # 64MB default
                      split_key = self.find_split_key()

                      new_range = Range(split_key, self.end_key)
                      self.end_key = split_key

                      return {
                          'original': self,
                          'new': new_range,
                          'split_key': split_key,
                          'evidence': 'Range split log'
                      }

              def merge(self, other):
                  """
                  Merge adjacent small ranges
                  """
                  if self.size + other.size < 32 * 1024 * 1024:  # 32MB
                      self.end_key = other.end_key
                      self.size += other.size

                      return {
                          'merged': True,
                          'new_size': self.size,
                          'evidence': 'Range merge log'
                      }

          return Range('/Table/1', '/Table/2')

      def mvcc_timestamps(self):
          """
          MVCC implementation
          """
          return {
              'hlc': 'Hybrid Logical Clocks',
              'uncertainty': 'Max clock offset window',
              'gc': {
                  'ttl': '25 hours default',
                  'versions': 'Keep multiple versions',
                  'tombstones': 'Cleaned after TTL'
              },
              'read_timestamp': {
                  'follower_reads': 'As of system time',
                  'bounded_staleness': 'Within bound',
                  'strong_consistency': 'Latest'
              },
              'evidence': 'MVCC statistics'
          }
  ```
  - Evidence: Range descriptors, lease transfers
  - Compatibility: PostgreSQL wire protocol

### 6.3.2 HTAP Systems
#### 6.3.2.1 Hybrid Workloads
- **OLTP + OLAP Together**
  ```python
  class HTAPSystems:
      def architecture_patterns(self):
          """
          HTAP architecture patterns
          """
          return {
              'single_engine': {
                  'example': 'MemSQL/SingleStore',
                  'approach': 'Row + column in same engine',
                  'benefit': 'Real-time analytics',
                  'challenge': 'Resource contention'
              },
              'dual_engine': {
                  'example': 'TiDB (TiKV + TiFlash)',
                  'approach': 'Separate OLTP/OLAP engines',
                  'sync': 'Raft replication',
                  'benefit': 'Isolation',
                  'challenge': 'Consistency lag'
              },
              'lambda_architecture': {
                  'batch': 'Hadoop/Spark',
                  'speed': 'Storm/Flink',
                  'serving': 'Merged view',
                  'challenge': 'Complexity'
              }
          }

      def tidb_architecture(self):
          """
          TiDB HTAP implementation
          """
          return {
              'components': {
                  'tidb_server': 'SQL layer (stateless)',
                  'tikv': 'Row store (Raft-based)',
                  'tiflash': 'Column store (learner)',
                  'pd': 'Placement driver (metadata)'
              },
              'data_flow': {
                  'write': 'TiDB -> TiKV (row)',
                  'replicate': 'TiKV -> TiFlash (async)',
                  'oltp_read': 'TiDB -> TiKV',
                  'olap_read': 'TiDB -> TiFlash'
              },
              'consistency': {
                  'tikv': 'Strong consistency',
                  'tiflash': 'Eventually consistent',
                  'learner': 'Non-voting replica'
              },
              'evidence': 'TiDB dashboard metrics'
          }
  ```
  - Evidence: Query routing decisions
  - Benefit: Real-time analytics

---

## Part 6.4: Multi-Model Databases

### 6.4.1 Unified Data Platforms
#### 6.4.1.1 Multi-Model Benefits
- **One System, Multiple Models**
  ```python
  class MultiModelDatabases:
      def model_combinations(self):
          """
          Common multi-model combinations
          """
          return {
              'document_graph': {
                  'example': 'ArangoDB, Azure Cosmos DB',
                  'benefit': 'Connected documents',
                  'query': 'Traverse and filter'
              },
              'key_value_document': {
                  'example': 'Couchbase, Amazon DocumentDB',
                  'benefit': 'Cache + persistence',
                  'query': 'Get and query'
              },
              'relational_document': {
                  'example': 'PostgreSQL + JSONB',
                  'benefit': 'Structure + flexibility',
                  'query': 'SQL + JSON operators'
              },
              'graph_relational': {
                  'example': 'AgensGraph',
                  'benefit': 'Tables + relationships',
                  'query': 'SQL + Cypher'
              }
          }

      def cosmos_db_apis(self):
          """
          Azure Cosmos DB multi-model
          """
          return {
              'sql_api': {
                  'model': 'Document',
                  'query': 'SQL-like',
                  'consistency': 'Five levels'
              },
              'mongodb_api': {
                  'model': 'Document',
                  'compatibility': 'MongoDB drivers',
                  'limitation': 'Subset of features'
              },
              'cassandra_api': {
                  'model': 'Column-family',
                  'protocol': 'CQL',
                  'use_case': 'Wide-column'
              },
              'gremlin_api': {
                  'model': 'Graph',
                  'query': 'Gremlin traversal',
                  'use_case': 'Connected data'
              },
              'table_api': {
                  'model': 'Key-value',
                  'protocol': 'Azure Table Storage',
                  'use_case': 'Simple lookups'
              },
              'evidence': 'API usage metrics'
          }
  ```
  - Evidence: API call distribution
  - Trade-off: Flexibility vs optimization

### 6.4.2 Storage Engine Unification
#### 6.4.2.1 Adaptive Storage Engines
- **Workload-Aware Storage**
  ```python
  class AdaptiveStorage:
      def peloton_architecture(self):
          """
          Self-driving database concepts
          """
          return {
              'tile_based_storage': {
                  'concept': 'Hybrid row/column',
                  'adaptation': 'Based on access patterns',
                  'granularity': 'Tile level'
              },
              'brain_components': {
                  'workload_forecasting': 'Predict future queries',
                  'action_planning': 'Index/partition decisions',
                  'cost_models': 'Estimate operation costs'
              },
              'ml_models': {
                  'query_prediction': 'LSTM/Transformer',
                  'index_recommendation': 'Reinforcement learning',
                  'knob_tuning': 'Gaussian process'
              },
              'evidence': 'Adaptation decisions'
          }

      def data_format_optimization(self):
          """
          Adaptive data formats
          """
          class AdaptiveFormat:
              def __init__(self):
                  self.access_history = defaultdict(int)
                  self.format = 'row'  # Start with row format

              def record_access(self, query_type, columns):
                  """Track access patterns"""
                  if query_type == 'scan' and len(columns) < 3:
                      self.access_history['columnar'] += 1
                  elif query_type == 'point':
                      self.access_history['row'] += 1

                  # Adapt format if needed
                  if self.should_adapt():
                      self.adapt_format()

              def adapt_format(self):
                  """Change storage format based on workload"""
                  if self.access_history['columnar'] > self.access_history['row'] * 2:
                      self.convert_to_columnar()
                  elif self.access_history['row'] > self.access_history['columnar'] * 2:
                      self.convert_to_row()

                  return {
                      'new_format': self.format,
                      'reason': self.access_history,
                      'evidence': 'Format conversion log'
                  }

          return AdaptiveFormat()
  ```
  - Evidence: Format adaptation logs
  - Future: Self-tuning databases

---

## Part 6.5: Synthesis and Mental Models

### 6.5.1 The Storage Evolution Pattern
#### 6.5.1.1 Specialization Cycle
- **From General to Specific to General**
  ```python
  def storage_evolution():
      """
      Evolution of storage systems
      """
      return {
          'phase1_general': {
              'era': '1970s-1990s',
              'system': 'RDBMS',
              'motto': 'One size fits all',
              'strength': 'ACID, SQL',
              'weakness': 'Scale, flexibility'
          },
          'phase2_specialized': {
              'era': '2000s-2010s',
              'systems': ['KV', 'Document', 'Graph', 'Column'],
              'motto': 'Right tool for job',
              'strength': 'Optimized for use case',
              'weakness': 'Operational complexity'
          },
          'phase3_convergence': {
              'era': '2010s-present',
              'systems': ['NewSQL', 'Multi-model', 'HTAP'],
              'motto': 'Best of both worlds',
              'strength': 'Flexibility + performance',
              'weakness': 'Complexity'
          },
          'pattern': 'Pendulum swings with learning'
      }
  ```

#### 6.5.1.2 CAP Trade-offs in Practice
- **How Systems Choose**
  ```python
  def cap_choices():
      """
      CAP theorem in real systems
      """
      return {
          'cp_systems': {
              'examples': ['HBase', 'MongoDB', 'Redis'],
              'choice': 'Consistency over availability',
              'partition': 'Reject writes',
              'use_case': 'Financial data'
          },
          'ap_systems': {
              'examples': ['Cassandra', 'DynamoDB', 'Riak'],
              'choice': 'Availability over consistency',
              'partition': 'Accept writes, diverge',
              'use_case': 'Shopping carts'
          },
          'tunable': {
              'examples': ['Cassandra', 'Cosmos DB'],
              'choice': 'Per-operation decision',
              'mechanism': 'Consistency levels',
              'use_case': 'Mixed workloads'
          }
      }
  ```

### 6.5.2 The Learning Spiral
#### 6.5.2.1 Pass 1: Intuition
- **Why Storage Evolves**
  - Scale breaks assumptions
  - Use cases diversify
  - Hardware changes economics
  - Story: Google's Bigtable genesis

#### 6.5.2.2 Pass 2: Understanding
- **Forces Shaping Storage**
  - Data model fit
  - Consistency requirements
  - Performance needs
  - Operational complexity

#### 6.5.2.3 Pass 3: Mastery
- **Choosing Storage Systems**
  - Analyze access patterns
  - Define consistency needs
  - Consider operational cost
  - Plan for evolution

---

## References and Further Reading

### Foundational Papers
- Gray et al. "The Transaction Concept" (1981)
- Stonebraker et al. "The End of an Architectural Era" (2007)
- Brewer. "CAP Twelve Years Later" (2012)
- Pavlo, Aslett. "What's Really New with NewSQL?" (2016)

### System Papers
- Chang et al. "Bigtable: A Distributed Storage System" (2006)
- DeCandia et al. "Dynamo: Amazon's Highly Available Key-value Store" (2007)
- Lakshman, Malik. "Cassandra - A Decentralized Structured Storage System" (2010)
- Corbett et al. "Spanner: Google's Globally-Distributed Database" (2012)

### Books
- Kleppmann. "Designing Data-Intensive Applications" (2017)
- Petrov. "Database Internals" (2019)
- Winand. "SQL Performance Explained" (2012)

---

## Chapter Summary

### The Irreducible Truth
**"The storage revolution transformed databases from monolithic ACID systems to a diverse ecosystem of specialized engines, each optimizing different trade-offs in the fundamental tension between consistency, availability, and performance."**

### Key Mental Models
1. **No Perfect Database**: Every system makes trade-offs
2. **Data Model Matters**: Structure determines access patterns
3. **Consistency Has Cost**: Stronger guarantees mean higher latency
4. **Workload Drives Design**: OLTP vs OLAP vs HTAP
5. **Evolution Continues**: Storage systems keep adapting

### What's Next
Chapter 7 will explore the cloud native transformation, showing how containerization, orchestration, and serverless computing have fundamentally changed how we build, deploy, and operate distributed systems.