# Polyglot Persistence: The Right Tool for Each Job

## The End of One-Size-Fits-All

> "The era of the universal database is over. Modern applications speak many data languages."

For decades, enterprises ran on a single database. Oracle or DB2 stored everything: transactions, analytics, documents, queues, caches. This monolithic approach made sense when databases cost millions and required dedicated DBAs. But it forced square pegs into round holes—storing social graphs in relational tables, implementing queues with polling, caching in application memory.

The cloud changed everything. Suddenly, you could spin up a Redis cluster in minutes, deploy Elasticsearch with a click, or use DynamoDB without managing servers. **The cost of using the right tool plummeted**. Polyglot persistence was born.

## The Modern Data Architecture

### A Typical E-Commerce Stack

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │PostgreSQL│  │  Redis   │  │  Kafka   │  │  S3    │ │
│  │          │  │          │  │          │  │        │ │
│  │ Orders   │  │ Sessions │  │  Events  │  │ Images │ │
│  │ Inventory│  │  Cache   │  │  Logs    │  │ Videos │ │
│  │ Customers│  │  Cart    │  │Analytics │  │ PDFs   │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  Elastic │  │  Neo4j   │  │ InfluxDB │  │Redshift│ │
│  │  Search  │  │          │  │          │  │        │ │
│  │ Product  │  │  Social  │  │ Metrics  │  │Reports │ │
│  │  Search  │  │  Graph   │  │Monitoring│  │Analysis│ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
└─────────────────────────────────────────────────────────┘
```

Each system optimized for its workload:
- **PostgreSQL**: ACID transactions for orders
- **Redis**: Microsecond latency for sessions
- **Elasticsearch**: Full-text search for products
- **Kafka**: Event streaming for real-time updates
- **S3**: Infinite scale for objects
- **Neo4j**: Graph traversals for recommendations
- **InfluxDB**: Time-series for metrics
- **Redshift**: Analytics on historical data

## Choosing the Right System

### Decision Framework

```python
def choose_storage_system(requirements):
    """Evidence-based storage selection"""

    # Start with data model
    if requirements.data_model == 'key_value':
        if requirements.latency < 1_ms:
            return 'Redis/Memcached'
        elif requirements.durability == 'critical':
            return 'DynamoDB/FoundationDB'
        else:
            return 'RocksDB/LevelDB'

    elif requirements.data_model == 'document':
        if requirements.consistency == 'strong':
            return 'MongoDB (w=majority)'
        elif requirements.scale > petabyte:
            return 'Elasticsearch/Cassandra'
        else:
            return 'CouchDB/RethinkDB'

    elif requirements.data_model == 'relational':
        if requirements.global_scale:
            return 'Spanner/CockroachDB'
        elif requirements.analytics:
            return 'Snowflake/BigQuery'
        else:
            return 'PostgreSQL/MySQL'

    elif requirements.data_model == 'graph':
        if requirements.scale > billion_edges:
            return 'Dgraph/JanusGraph'
        else:
            return 'Neo4j/ArangoDB'

    elif requirements.data_model == 'time_series':
        if requirements.retention > years:
            return 'Cassandra/HBase'
        else:
            return 'InfluxDB/TimescaleDB'
```

### The CAP Compass

```
         Consistency
              △
             /│\
            / │ \
           /  │  \
          /   │   \
         /    │    \
    CP  ●─────┼─────● AP
       /      │      \
      /       │       \
     /        │        \
    ●─────────┴─────────●
 Partition          Availability
 Tolerance

CP Systems (Choose Consistency):
• Spanner, CockroachDB
• MongoDB (w=majority)
• etcd, Consul, ZooKeeper
• PostgreSQL (single node)

AP Systems (Choose Availability):
• Cassandra, DynamoDB
• CouchDB, Riak
• Redis (async replication)
• Elasticsearch

CA Systems (Single Node):
• PostgreSQL, MySQL
• SQLite
• Not truly distributed
```

## Pattern 1: Cache-Aside

### The Most Common Pattern

```python
class CacheAsidePattern:
    def __init__(self):
        self.cache = Redis()
        self.database = PostgreSQL()

    def read(self, key):
        # Check cache first
        value = self.cache.get(key)
        if value:
            return value  # Cache hit

        # Cache miss - read from database
        value = self.database.query(f"SELECT * FROM table WHERE id={key}")

        # Populate cache for next time
        self.cache.set(key, value, ttl=3600)

        return value

    def write(self, key, value):
        # Write to database
        self.database.execute(f"UPDATE table SET data={value} WHERE id={key}")

        # Invalidate cache
        self.cache.delete(key)
        # Or update cache (race condition risk)
        # self.cache.set(key, value, ttl=3600)
```

### Cache Stampede Problem

When cache expires, all requests hit database:

```python
class CacheStampedeProtection:
    def read_with_protection(self, key):
        value = self.cache.get(key)

        if not value:
            # Use distributed lock to prevent stampede
            lock_key = f"lock:{key}"
            if self.cache.set_nx(lock_key, "locked", ttl=10):
                try:
                    # We got the lock - refresh cache
                    value = self.database.query(key)
                    self.cache.set(key, value, ttl=3600)
                finally:
                    self.cache.delete(lock_key)
            else:
                # Someone else is refreshing - wait
                for _ in range(100):
                    time.sleep(0.01)
                    value = self.cache.get(key)
                    if value:
                        break

        return value
```

## Pattern 2: Event Sourcing

### Store Events, Not State

```python
class EventSourcingPattern:
    def __init__(self):
        self.event_store = Kafka()  # Immutable log
        self.snapshot_store = PostgreSQL()  # Current state
        self.cache = Redis()  # Read models

    def execute_command(self, command):
        # 1. Validate command
        if not self.validate(command):
            raise InvalidCommand()

        # 2. Generate events
        events = self.generate_events(command)

        # 3. Store events (source of truth)
        for event in events:
            self.event_store.append(event)

        # 4. Update read models (eventually)
        self.update_projections(events)

    def rebuild_state(self, entity_id):
        """Replay events to rebuild state"""
        events = self.event_store.read_all(entity_id)
        state = self.initial_state()

        for event in events:
            state = self.apply_event(state, event)

        return state
```

### Event Store Design

```sql
-- Events are immutable
CREATE TABLE events (
    event_id UUID PRIMARY KEY,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    event_data JSONB NOT NULL,
    event_time TIMESTAMP NOT NULL,
    event_version INT NOT NULL,
    -- Optimistic concurrency control
    UNIQUE(aggregate_id, event_version)
);

-- Never UPDATE or DELETE, only INSERT
```

## Pattern 3: CQRS (Command Query Responsibility Segregation)

### Different Models for Reading and Writing

```python
class CQRSPattern:
    def __init__(self):
        # Write side - normalized, consistent
        self.command_store = PostgreSQL()

        # Read side - denormalized, fast
        self.query_stores = {
            'search': Elasticsearch(),
            'analytics': ClickHouse(),
            'cache': Redis(),
            'graph': Neo4j()
        }

    def handle_command(self, command):
        # 1. Execute command on write model
        result = self.command_store.execute(command)

        # 2. Publish event
        event = self.create_event(command, result)
        self.publish_event(event)

        return result

    def handle_query(self, query):
        # Route to appropriate read model
        if query.type == 'search':
            return self.query_stores['search'].query(query)
        elif query.type == 'analytics':
            return self.query_stores['analytics'].query(query)
        else:
            return self.query_stores['cache'].get(query.key)

    def sync_read_models(self, event):
        """Update all read models (eventually consistent)"""
        for store in self.query_stores.values():
            store.apply_event(event)
```

## Pattern 4: Saga Pattern

### Distributed Transactions Without 2PC

```python
class SagaPattern:
    """Coordinate transactions across multiple databases"""

    def __init__(self):
        self.order_db = PostgreSQL()
        self.inventory_db = MongoDB()
        self.payment_db = DynamoDB()
        self.shipping_db = Cassandra()

    def process_order(self, order):
        saga_id = uuid.uuid4()
        compensations = []

        try:
            # Step 1: Reserve inventory
            reservation = self.inventory_db.reserve(
                order.items,
                saga_id
            )
            compensations.append(
                lambda: self.inventory_db.cancel_reservation(saga_id)
            )

            # Step 2: Process payment
            payment = self.payment_db.charge(
                order.payment,
                saga_id
            )
            compensations.append(
                lambda: self.payment_db.refund(saga_id)
            )

            # Step 3: Create shipment
            shipment = self.shipping_db.schedule(
                order.shipping,
                saga_id
            )
            compensations.append(
                lambda: self.shipping_db.cancel(saga_id)
            )

            # Step 4: Confirm order
            self.order_db.confirm(order.id, saga_id)

            return "SUCCESS"

        except Exception as e:
            # Compensate in reverse order
            for compensation in reversed(compensations):
                try:
                    compensation()
                except:
                    # Log compensation failure for manual intervention
                    self.log_compensation_failure(saga_id)

            raise SagaFailed(f"Order failed: {e}")
```

## Pattern 5: Lambda Architecture

### Batch + Stream Processing

```python
class LambdaArchitecture:
    def __init__(self):
        # Batch layer - complete, accurate
        self.hdfs = HDFS()  # Master dataset
        self.spark = Spark()  # Batch processing
        self.hive = Hive()  # Batch views

        # Speed layer - recent, approximate
        self.kafka = Kafka()  # Stream ingestion
        self.flink = Flink()  # Stream processing
        self.redis = Redis()  # Real-time views

        # Serving layer - unified queries
        self.query_engine = Presto()

    def ingest(self, data):
        # Write to both batch and stream
        self.hdfs.append(data)  # For completeness
        self.kafka.produce(data)  # For low latency

    def batch_process(self):
        """Run periodically (hourly/daily)"""
        # Process all historical data
        dataset = self.hdfs.read_all()
        results = self.spark.process(dataset)
        self.hive.write_views(results)

    def stream_process(self):
        """Run continuously"""
        stream = self.kafka.consume()
        for event in stream:
            result = self.flink.process(event)
            self.redis.update(result)

    def query(self, query):
        """Combine batch and real-time views"""
        batch_result = self.hive.query(query)
        stream_result = self.redis.query(query)
        return self.merge_results(batch_result, stream_result)
```

## Real-World Case Studies

### Netflix: Polyglot at Scale

```
Service          Storage           Why
-------          -------           ---
User Profiles    Cassandra        Global replication
Viewing History  Cassandra        Time-series, write-heavy
Recommendations  ElasticSearch    ML features, search
Video Metadata   DynamoDB         Low latency, global
Billing          MySQL            ACID transactions
Metrics          Atlas (TSDB)     Time-series monitoring
CDN Routing      EVCache (Redis)  Microsecond latency
```

### Uber: Evolution of Storage

**Phase 1: Monolithic PostgreSQL**
- Single database for everything
- Hit scaling limits at 100K trips/day

**Phase 2: Sharded PostgreSQL**
- Sharded by city
- Cross-city queries became impossible

**Phase 3: Polyglot Architecture**
```python
storage_choices = {
    'trips': 'Cassandra',  # Write-heavy, geo-distributed
    'users': 'MySQL',  # ACID for financial data
    'maps': 'Custom',  # Specialized graph storage
    'surge': 'Redis',  # Real-time pricing
    'analytics': 'Hive',  # Historical analysis
}
```

### Airbnb: Service-Storage Alignment

Each service owns its storage:

```yaml
services:
  - name: listing-service
    storage:
      primary: MySQL
      cache: Redis
      search: Elasticsearch

  - name: booking-service
    storage:
      primary: MySQL (sharded)
      events: Kafka

  - name: messaging-service
    storage:
      primary: HBase
      cache: Memcached

  - name: payment-service
    storage:
      primary: MySQL
      audit: S3
```

## Migration Strategies

### Gradual Migration

```python
class DualWritesMigration:
    """Migrate from old_db to new_db safely"""

    def __init__(self):
        self.old_db = MySQL()
        self.new_db = DynamoDB()
        self.migration_state = 'dual_writes'

    def write(self, key, value):
        if self.migration_state in ['dual_writes', 'new_primary']:
            self.new_db.write(key, value)

        if self.migration_state in ['dual_writes', 'old_primary']:
            self.old_db.write(key, value)

    def read(self, key):
        if self.migration_state == 'old_primary':
            return self.old_db.read(key)
        elif self.migration_state == 'new_primary':
            return self.new_db.read(key)
        else:  # dual_writes
            # Compare for consistency
            old_value = self.old_db.read(key)
            new_value = self.new_db.read(key)
            if old_value != new_value:
                self.log_inconsistency(key, old_value, new_value)
            return old_value  # Still trust old
```

### Strangler Fig Pattern

```python
class StranglerFigMigration:
    """Gradually replace old system"""

    def __init__(self):
        self.legacy_system = LegacyMonolith()
        self.new_services = {}
        self.router = Router()

    def migrate_feature(self, feature_name):
        # 1. Build new service
        new_service = self.build_service(feature_name)
        self.new_services[feature_name] = new_service

        # 2. Route percentage of traffic
        self.router.add_rule(
            feature=feature_name,
            route_to_new=0.01  # Start with 1%
        )

        # 3. Gradually increase traffic
        for percentage in [0.05, 0.10, 0.25, 0.50, 1.00]:
            self.router.update_rule(
                feature=feature_name,
                route_to_new=percentage
            )
            self.monitor_and_rollback_if_needed()
            time.sleep(hours=24)

        # 4. Decommission old code
        self.legacy_system.remove_feature(feature_name)
```

## Anti-Patterns to Avoid

### 1. Distributed Joins

```python
# DON'T: Join across databases
users = mysql.query("SELECT * FROM users")
for user in users:
    orders = dynamodb.query(user_id=user.id)  # N+1 problem!

# DO: Denormalize or use CQRS
user_orders = elasticsearch.query(user_id=user.id)  # Pre-joined
```

### 2. Synchronous Chains

```python
# DON'T: Synchronous calls across stores
def get_user_profile(user_id):
    user = postgresql.get(user_id)
    preferences = redis.get(user_id)
    history = cassandra.get(user_id)
    recommendations = neo4j.get(user_id)
    return merge(user, preferences, history, recommendations)
    # If any fails, all fail!

# DO: Async with fallbacks
async def get_user_profile(user_id):
    tasks = [
        postgresql.get_async(user_id),
        redis.get_async(user_id, default={}),
        cassandra.get_async(user_id, default=[]),
        neo4j.get_async(user_id, default=[])
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return merge_with_fallbacks(results)
```

### 3. Inconsistent Event Ordering

```python
# DON'T: Multiple event streams
kafka.send(user_event)
rabbitmq.send(user_event)
sqs.send(user_event)
# Order not guaranteed across systems!

# DO: Single source of truth
kafka.send(user_event)
# Other systems consume from Kafka
```

## Summary: Embracing Complexity

Polyglot persistence isn't free. It brings:
- **Operational complexity**: Multiple systems to manage
- **Consistency challenges**: No global transactions
- **Learning curve**: Teams must know multiple technologies
- **Integration work**: Glue code between systems

But it enables:
- **Optimal performance**: Right tool for each workload
- **Independent scaling**: Scale only what needs scaling
- **Team autonomy**: Services choose their storage
- **Cost optimization**: Use expensive features only where needed

### The Evidence Framework for Polyglot Systems

Each storage system maintains its own evidence:
- **PostgreSQL**: WAL, MVCC versions, locks
- **Redis**: Replication offsets, TTLs
- **Cassandra**: Vector clocks, tombstones
- **Elasticsearch**: Segment files, transaction logs
- **Kafka**: Offsets, ISR lists

The application layer becomes the **evidence coordinator**, ensuring business invariants hold across system boundaries.

### Key Principles

1. **Service boundaries = storage boundaries**
2. **Async by default, sync when required**
3. **Embrace eventual consistency between systems**
4. **Design for partial failure**
5. **Monitor boundaries more than systems**

The future isn't one perfect database—it's many specialized databases, coordinated by applications that understand their trade-offs.

---

**Mental Model**: Polyglot persistence systems maintain local invariants within each storage system while coordinating global invariants at the application layer through asynchronous evidence propagation (events, sagas, CDC).

Continue to [Production Lessons →](production-lessons.md)