# Uber: From Monolith to Microservices

## Introduction: The Architecture That Couldn't Scale

In 2014, Uber was growing at an unprecedented rate. The company was doubling in size every six months. Cities were being launched weekly. The product was evolving from "just rides" to "rides + pool + eats + freight." And the system was buckling under the load.

The architecture was a monolith: **one Python application, one PostgreSQL database, one datacenter**. Every feature shared the same codebase. Every request touched the same database. Every deployment meant downtime. Every outage affected every city.

**The breaking point**: In September 2014, during high demand, the database became so overloaded that queries took minutes instead of milliseconds. Drivers couldn't see new ride requests. Riders couldn't book trips. The entire system ground to a halt. Uber was losing tens of thousands of dollars per minute.

This wasn't a one-time incident—it was the third major outage that month. The team realized: **The architecture that got us to 100 cities won't get us to 1,000 cities. We need to rebuild, while the plane is flying, without crashing.**

### The Migration Journey

**2014**: Monolith with PostgreSQL
**2015**: Microservices with Schemaless (custom datastore)
**2016**: Service mesh with Ringpop (gossip-based coordination)
**2017**: Geospatial at scale with H3 (hexagonal grid)
**2018**: 1000+ microservices, global real-time platform

**The numbers**:
- **Rides**: From 1 million/month (2014) → 15 million/day (2018)
- **Services**: From 1 monolith → 2,200+ microservices
- **Datacenters**: From 1 → 8+ regions globally
- **Latency**: Trip dispatch from 2000ms → 200ms
- **Availability**: From 99.9% → 99.99%

### The Core Challenges

1. **Real-time dispatching**: Match riders to drivers in <1 second, globally
2. **Geospatial queries**: "Find all drivers within 1 mile" across millions of drivers
3. **High write throughput**: 10,000+ trips started per second at peak
4. **Fault tolerance**: Any single service failure can't halt dispatching
5. **Schema evolution**: Multiple teams shipping features daily, can't coordinate schema changes

**The innovations**:

1. **Schemaless**: Append-only, sharded datastore that scales writes infinitely
2. **Ringpop**: Consistent hash ring for service coordination without Zookeeper
3. **H3**: Hexagonal hierarchical geospatial index for efficient proximity queries
4. **DISCO (service discovery)**: DNS-based service mesh for inter-service communication
5. **Cadence**: Distributed workflow orchestration for multi-step business logic

**The evidence lens**: Uber built systems that generate **operational evidence** (dispatch confirmations, location updates), **consistency evidence** (exactly-once trip charging), and **availability evidence** (redundant dispatching across regions), enabling real-time global ride-hailing.

Let's explore how they did it.

---

## Part 1: INTUITION (First Pass)—The PostgreSQL Wall

### The Monolith Architecture (2012-2014)

**The setup**:

```
                      [Load Balancer]
                            |
           [Python Monolith] × 10 instances
                            |
                    [PostgreSQL]
                      (Master + 3 replicas)

Tables:
  - users
  - drivers
  - trips
  - locations (driver positions updated every 4 seconds)
```

**What worked well initially**:
- Simple to develop: All code in one repository
- Easy to deploy: One application, one database
- ACID transactions: PostgreSQL ensures consistency
- Powerful queries: JOIN across users, drivers, trips

**What broke at scale**:

**Problem 1: Write bottleneck**

Every trip creates/updates multiple rows:
```sql
BEGIN;
INSERT INTO trips (rider_id, status) VALUES (123, 'requesting');
UPDATE drivers SET status = 'assigned' WHERE driver_id = 456;
INSERT INTO trip_locations (trip_id, lat, lon) VALUES (...);
COMMIT;
```

At 1,000 trips/sec = 5,000+ writes/sec to one database. PostgreSQL master became the bottleneck.

**Problem 2: Location updates flooding the database**

Every driver sends location every 4 seconds:
- 10,000 active drivers = 2,500 writes/sec just for locations
- These writes contend with trip writes for locks
- Replication lag: Replicas fall behind, reads become stale

**Problem 3: Geospatial queries are slow**

To find nearby drivers:
```sql
SELECT driver_id, lat, lon
FROM driver_locations
WHERE lat BETWEEN 37.7 AND 37.8
  AND lon BETWEEN -122.5 AND -122.4
  AND status = 'available'
ORDER BY distance(lat, lon, 37.77, -122.45)
LIMIT 10;
```

With millions of drivers, this query took 500-2000ms. Too slow for real-time dispatch.

**Problem 4: Schema changes require downtime**

To add a column:
```sql
ALTER TABLE trips ADD COLUMN surge_multiplier DECIMAL;
```

On a table with 100 million rows, this locks the table for minutes. All writes blocked. System is down.

### The First Attempt: Read Replicas and Sharding

**Attempt 1: Add more read replicas**

```
                [PostgreSQL Master] (writes)
                    |       |       |
            [Replica1]  [Replica2]  [Replica3]  (reads)
```

**Result**: Helped with read load, but write bottleneck remained. Replication lag grew (replicas falling 10+ seconds behind).

**Attempt 2: Manual sharding by city**

```
San Francisco → DB1
New York → DB2
London → DB3
...
```

**Result**: Each city's database was manageable, but:
- Cross-city trips broke (SFO → NYC)
- Ops overhead: 100 cities = 100 databases to manage
- Rebalancing nightmare when cities grow unevenly

**The realization**: **PostgreSQL's write scalability doesn't match Uber's growth curve. Need a database that scales writes horizontally.**

### The Second Attempt: Cassandra

Uber tried migrating to Cassandra (2013):

**Why Cassandra looked promising**:
- Write scalability: Distributes writes across nodes
- No single master bottleneck
- Good fit for time-series data (trip events)

**Why it didn't work**:

**Problem 1: Eventual consistency breaks business logic**

```
# Driver accepts trip
write_to_cassandra(driver_id=456, status='assigned')

# 100ms later, rider requests cancel
status = read_from_cassandra(driver_id=456)
# Returns 'available' (stale read, write not propagated yet)

# System allows assigning same driver to another trip → CONFLICT
```

Uber's business logic requires:
- Read-your-writes consistency (after I update driver status, I must see it)
- No duplicate assignments (one driver = one trip at a time)

**Problem 2: No secondary indexes that work**

Cassandra's secondary indexes are slow and inconsistent. Can't efficiently query:
- "Find all available drivers" (filter by status)
- "Find all trips in progress" (filter by status + time range)

**Problem 3: Schema tied to queries**

In Cassandra, you must design schema around access patterns. Uber's access patterns were evolving daily. Schema rigidity became a blocker.

**The realization**: **Off-the-shelf NoSQL databases make different trade-offs than Uber needs. Need to build custom.**

---

## Part 2: UNDERSTANDING (Second Pass)—Building Schemaless

### Schemaless: Uber's Custom Datastore

Uber built **Schemaless** (2015), a distributed datastore with these goals:

1. **High write throughput**: Millions of writes per second
2. **Read-your-writes consistency**: Strong consistency within a shard
3. **Flexible schema**: Support schema evolution without downtime
4. **Efficient range queries**: Fetch all trips for a user, in time order
5. **Built on MySQL**: Leverage existing MySQL expertise

**Architecture**:

```
Application
    ↓
Schemaless Client Library
    ↓
[Shard Router] (consistent hashing)
    ↓
┌─────────────┬─────────────┬─────────────┐
│  Shard 1    │  Shard 2    │  Shard 3    │
│  MySQL      │  MySQL      │  MySQL      │
│  (Master +  │  (Master +  │  (Master +  │
│   Replicas) │   Replicas) │   Replicas) │
└─────────────┴─────────────┴─────────────┘
```

### Data Model: Append-Only with Versioning

**Storage format**:

```sql
CREATE TABLE trips (
    partition_key UUID,        -- User ID or Trip ID
    sort_key VARCHAR(255),     -- Timestamp + sequence
    row_key VARCHAR(255),      -- Unique identifier
    body JSON,                 -- Actual data
    created_at BIGINT,         -- Timestamp
    PRIMARY KEY (partition_key, sort_key, row_key)
);
```

**Example data**:

```json
partition_key = "user:12345"
sort_key = "20231001120000_trip"
row_key = "trip:abc123"
body = {
    "trip_id": "abc123",
    "rider_id": "user:12345",
    "driver_id": "driver:456",
    "status": "requesting",
    "created_at": 1696161600
}
```

**Append-only updates**:

Instead of UPDATE, write a new version:

```
# Version 1 (trip created)
partition_key = "trip:abc123"
sort_key = "20231001120000_000"
body = {"status": "requesting", ...}

# Version 2 (driver assigned)
partition_key = "trip:abc123"
sort_key = "20231001120030_001"
body = {"status": "assigned", "driver_id": "driver:456", ...}

# Version 3 (trip started)
partition_key = "trip:abc123"
sort_key = "20231001120100_002"
body = {"status": "in_progress", ...}
```

**Reads**: Fetch latest version by reading last row in partition:

```sql
SELECT body FROM trips
WHERE partition_key = 'trip:abc123'
ORDER BY sort_key DESC
LIMIT 1;
```

### Sharding Strategy: Consistent Hashing

**Shard assignment**:

```python
def get_shard(partition_key, num_shards=64):
    hash_value = consistent_hash(partition_key)
    shard_id = hash_value % num_shards
    return shard_id

# Example
get_shard("user:12345") → Shard 27
get_shard("trip:abc123") → Shard 42
```

**Benefits**:

1. **Write distribution**: Each shard handles 1/64th of writes
2. **Independent scaling**: Add more shards as traffic grows
3. **Fault isolation**: One shard failure doesn't affect others

**Rebalancing**:

When adding shards (64 → 128):
- Use virtual nodes (like Dynamo)
- Migrate subset of keys from each old shard to new shards
- Double-write during migration (write to old and new)
- Cut over when migration complete

### Schema Evolution: JSON with Versioned Schemas

**Problem**: Traditional ALTER TABLE requires downtime.

**Schemaless solution**: Store data as JSON, validate schemas in application:

```python
# Version 1 schema
TripSchemaV1 = {
    "trip_id": str,
    "rider_id": str,
    "status": str,
}

# Version 2 schema (add field)
TripSchemaV2 = {
    "trip_id": str,
    "rider_id": str,
    "driver_id": str,  # NEW
    "status": str,
}

# Read code handles both versions
def read_trip(trip_id):
    data = schemaless.get(f"trip:{trip_id}")
    if "driver_id" in data:
        return TripV2(data)  # New schema
    else:
        return TripV1(data)  # Old schema
```

**Migration strategy**:

1. **Deploy code that reads both V1 and V2**
2. **Deploy code that writes V2** (all new writes use new schema)
3. **Background job migrates old V1 data to V2**
4. **After 100% migrated, remove V1 read code**

**Key benefit**: No downtime, no locked tables, rolling deployment.

### Consistency Model: Single-Shard Transactions

**Within a shard**: Use MySQL transactions for ACID guarantees

```python
def assign_driver_to_trip(trip_id, driver_id):
    with schemaless.transaction():
        # Read trip
        trip = schemaless.get(f"trip:{trip_id}")
        if trip.status != 'requesting':
            raise Exception("Trip not available")

        # Read driver
        driver = schemaless.get(f"driver:{driver_id}")
        if driver.status != 'available':
            raise Exception("Driver not available")

        # Update both (same shard if co-located)
        schemaless.put(f"trip:{trip_id}", {"status": "assigned", "driver_id": driver_id})
        schemaless.put(f"driver:{driver_id}", {"status": "assigned", "trip_id": trip_id})
```

**Cross-shard**: No distributed transactions

If trip and driver are on different shards, use **compensating transactions**:

```python
def assign_driver_to_trip(trip_id, driver_id):
    # Step 1: Assign driver (shard 1)
    try:
        schemaless.put(f"driver:{driver_id}", {"status": "assigned", "trip_id": trip_id})
    except:
        return ERROR

    # Step 2: Assign trip (shard 2)
    try:
        schemaless.put(f"trip:{trip_id}", {"status": "assigned", "driver_id": driver_id})
    except:
        # Rollback driver assignment
        schemaless.put(f"driver:{driver_id}", {"status": "available"})
        return ERROR

    return SUCCESS
```

**Eventual consistency**: Background workers reconcile inconsistencies (e.g., orphaned assignments).

---

## Part 3: RINGPOP—Consistent Hashing for Services

### The Service Discovery Problem

With 2,200+ microservices, how do they find each other?

**Traditional approach: Zookeeper**

```
Service A → Zookeeper (where is Service B?) → IP list
```

**Problems**:

1. **Single point of failure**: Zookeeper down = all services can't discover
2. **Operational complexity**: Maintaining Zookeeper cluster
3. **Latency**: Every request requires Zookeeper lookup

**Uber's solution: Ringpop**

Ringpop is a **gossip-based consistent hashing library**:

- No central coordinator (no Zookeeper)
- Decentralized membership (gossip protocol)
- Consistent hashing for request routing
- Sub-millisecond lookups (local hash table)

### How Ringpop Works

**Consistent hash ring**:

```
Ring: 0 ──────────────────────────────────── 2^32

Service A instances:
  A1: hash(A1_id) = 100
  A2: hash(A2_id) = 200
  A3: hash(A3_id) = 300

Request for key "user:12345":
  hash("user:12345") = 150
  → Route to A2 (first node clockwise from 150)
```

**Gossip protocol for membership**:

```python
class RingpopNode:
    def __init__(self, node_id):
        self.node_id = node_id
        self.ring = {}  # node_id → (status, incarnation, timestamp)

    def gossip_tick(self):
        # Every 100ms, pick random peer and exchange membership
        peer = random.choice(self.peers)
        my_view = self.ring.copy()
        peer_view = peer.get_membership()

        # Merge views
        for node, (status, incarnation, ts) in peer_view.items():
            if node not in my_view:
                self.ring[node] = (status, incarnation, ts)
            elif incarnation > my_view[node][1]:
                # Higher incarnation wins
                self.ring[node] = (status, incarnation, ts)

    def handle_request(self, key):
        # Hash key to ring
        target_node = self.lookup(key)

        if target_node == self.node_id:
            # I own this key, handle it
            return self.process(key)
        else:
            # Forward to owner
            return self.forward(target_node, key)

    def lookup(self, key):
        hash_value = consistent_hash(key)
        # Find first node clockwise from hash_value
        for node in sorted(self.ring.keys()):
            if node >= hash_value:
                return node
        return sorted(self.ring.keys())[0]  # Wrap around
```

**Benefits**:

1. **No single point of failure**: Any node can route requests
2. **Self-healing**: Nodes detect failures via gossip, re-route automatically
3. **Fast**: Lookup is O(log N) in local hash table
4. **Scalable**: Gossip converges in O(log N) rounds

### Ringpop in Production: Dispatch Service

**Dispatch service** (assigns riders to drivers):

```
100 instances of dispatch service
Each instance knows about all 100 via Ringpop

Rider "user:12345" requests trip:
  1. Request hits any dispatch instance (via load balancer)
  2. Instance computes: hash("user:12345") → 12345678
  3. Lookup in ring: Instance 47 owns this hash
  4. Forward request to Instance 47
  5. Instance 47 has in-memory state for "user:12345"
     (recent requests, retry count, etc.)
  6. Instance 47 processes dispatch
```

**Why this works**:

- All requests for same user go to same instance (sticky routing)
- Instance maintains local state (no database lookup for every request)
- If instance fails, Ringpop re-routes to next instance on ring

**Fault tolerance**:

```
Instance 47 crashes:
  1. Other instances detect via gossip (no heartbeat for 5 seconds)
  2. Instance 47 removed from ring
  3. Requests for user:12345 now route to Instance 52 (next on ring)
  4. Instance 52 doesn't have cached state, loads from database
  5. Continues processing
```

---

## Part 4: H3—Geospatial Indexing at Scale

### The Geospatial Problem

**Query**: "Find all available drivers within 1 mile of (37.7749, -122.4194)"

With millions of drivers, naively checking each driver's distance is too slow.

### Traditional Approaches

**Approach 1: Bounding box with database index**

```sql
SELECT driver_id FROM drivers
WHERE lat BETWEEN 37.7749 - 0.0145 AND 37.7749 + 0.0145
  AND lon BETWEEN -122.4194 - 0.0145 AND -122.4194 - 0.0145
  AND status = 'available';
```

**Problem**: Bounding box is approximate (includes corners farther than 1 mile). Need post-filter with exact distance calculation.

**Approach 2: Geohash**

Encode lat/lon as string: `(37.7749, -122.4194) → "9q8yy"`

Similar locations have common prefixes:
```
9q8yy  → San Francisco downtown
9q8yz  → San Francisco nearby
9q8yw  → San Francisco adjacent
```

**Problem**: Edge case at geohash boundaries. Two nearby points can have completely different prefixes if they're on opposite sides of a boundary.

### H3: Uber's Hexagonal Grid

**H3** (Hexagonal Hierarchical Geospatial Indexing System):

- Divide earth into hexagons at multiple resolutions
- Each hexagon has unique ID
- Neighbors have similar IDs

**Hierarchy**:

```
Resolution 0: 122 hexagons (entire continents)
Resolution 3: 41,162 hexagons (~100 km per hex)
Resolution 7: 4,248,624 hexagons (~1 km per hex)
Resolution 10: 703,982,516 hexagons (~100 m per hex)
Resolution 15: 4,149,663,077,122 hexagons (~1 m per hex)
```

**Example**:

```python
import h3

# Encode location to H3 index at resolution 9 (~200m hexagons)
lat, lon = 37.7749, -122.4194
h3_index = h3.geo_to_h3(lat, lon, resolution=9)
# → '8928308280fffff'

# Find neighbors (hexagons within 1 km)
neighbors = h3.k_ring(h3_index, k=5)
# → ['8928308280fffff', '8928308281fffff', ...]

# For each driver, store their current H3 index
# Database: driver_id → h3_index

# Query: Find drivers in any of these hexagons
nearby_drivers = db.query("""
    SELECT driver_id FROM drivers
    WHERE h3_index IN (?, ?, ?, ...)
      AND status = 'available'
""", neighbors)
```

**Why hexagons?**

1. **Uniform neighbors**: Each hexagon has exactly 6 neighbors (except pentagons at poles)
2. **Uniform distance**: Distance to all neighbors is approximately equal
3. **No edge cases**: Unlike squares or triangles, hexagons tile the plane smoothly

### H3 in Production: Dispatch Matching

**Driver location updates**:

```python
def driver_location_update(driver_id, lat, lon):
    # Compute H3 index at resolution 9
    h3_index = h3.geo_to_h3(lat, lon, 9)

    # Update in-memory index
    h3_to_drivers[h3_index].add(driver_id)

    # Remove from old index if moved hexagons
    if driver_id in driver_to_h3:
        old_h3 = driver_to_h3[driver_id]
        if old_h3 != h3_index:
            h3_to_drivers[old_h3].remove(driver_id)

    driver_to_h3[driver_id] = h3_index
```

**Dispatch query**:

```python
def find_nearby_drivers(rider_lat, rider_lon, max_distance_km=2):
    # Compute rider's H3 index
    rider_h3 = h3.geo_to_h3(rider_lat, rider_lon, 9)

    # Find hexagons within max distance
    # k=10 at resolution 9 covers ~2km radius
    nearby_hexagons = h3.k_ring(rider_h3, k=10)

    # Collect drivers in these hexagons
    candidates = []
    for hex_id in nearby_hexagons:
        candidates.extend(h3_to_drivers.get(hex_id, []))

    # Filter by exact distance and status
    nearby_drivers = []
    for driver_id in candidates:
        driver_lat, driver_lon = get_driver_location(driver_id)
        distance = haversine(rider_lat, rider_lon, driver_lat, driver_lon)
        if distance <= max_distance_km and is_available(driver_id):
            nearby_drivers.append((driver_id, distance))

    # Sort by distance
    nearby_drivers.sort(key=lambda x: x[1])
    return nearby_drivers[:10]  # Return top 10
```

**Performance**:

- H3 lookup: O(1) (hash table)
- Neighbor computation: O(1) (6 neighbors per hex)
- Candidate filtering: O(N) where N = drivers in hexagons (~100s)
- Total: <10ms for millions of drivers

---

## Part 5: PRODUCTION NUMBERS AND REAL-WORLD IMPACT

### Schemaless Performance

**Write throughput** (2018):

- Writes per second: 3 million+
- Peak: 10 million+ writes/sec during New Year's Eve
- Shards: 2,048 MySQL shards
- Write latency: p50 = 5ms, p99 = 50ms

**Comparison to monolith**:

| Metric | Monolith (2014) | Schemaless (2018) |
|--------|-----------------|-------------------|
| Max writes/sec | 10,000 | 10,000,000 |
| Write latency (p99) | 500ms | 50ms |
| Shards | 1 | 2,048 |
| Downtime for schema change | 10 minutes | 0 seconds |

### Ringpop at Scale

**Dispatch service** (2018):

- Service instances: 500+
- Requests per second: 1 million+
- Gossip convergence time: <1 second (for 500 nodes)
- Failover time: <100ms (gossip detects, re-routes)

**Benefit**: Eliminated Zookeeper, reduced dependencies, improved resilience.

### H3 Geospatial Performance

**Dispatch matching** (2018):

- Active drivers: 3 million+ globally
- Location updates: 750,000 per second (3M drivers × 1 update/4 sec)
- Match queries: 100,000 per second
- Match latency: p50 = 8ms, p99 = 40ms

**Comparison to PostgreSQL geospatial**:

| Metric | PostgreSQL (2014) | H3 + In-Memory (2018) |
|--------|-------------------|-----------------------|
| Match latency (p99) | 2000ms | 40ms |
| Active drivers supported | 50,000 | 3,000,000 |
| Storage | Database | In-memory index |

### Real-Time Dispatch Success

**Goal**: Match rider to driver in <1 second.

**2014 (monolith)**:
- Match time: p50 = 1000ms, p99 = 5000ms
- Failure rate: 5% (no drivers found due to slow queries)

**2018 (microservices + H3)**:
- Match time: p50 = 200ms, p99 = 800ms
- Failure rate: 0.5%

**Impact**: 10× faster matching, 10× higher success rate.

---

## Part 6: MASTERY (Third Pass)—Lessons and Patterns

### Lesson 1: Build vs Buy

**When Uber chose to build**:

1. **Schemaless**: No existing datastore met requirements (high writes, schema flexibility, MySQL-based)
2. **Ringpop**: Zookeeper didn't fit Uber's operational model (wanted decentralized)
3. **H3**: Existing geospatial indexes (geohash, quadtree) had edge cases

**When Uber used off-the-shelf**:

1. **MySQL**: Storage engine for Schemaless (leverage maturity, tooling)
2. **Kafka**: Messaging backbone (no need to reinvent)
3. **Redis**: Caching layer (standard tool)

**The pattern**: Build when requirements are unique, buy when standard tools suffice.

### Lesson 2: Incremental Migration

**Uber didn't rewrite everything at once**:

**Phase 1** (2015): Extract critical services (dispatch, payments) from monolith
**Phase 2** (2016): Migrate data to Schemaless shard-by-shard
**Phase 3** (2017): Decompose remaining monolith into microservices
**Phase 4** (2018): Optimize with H3, Ringpop, advanced patterns

**Key strategy**: **Strangler fig pattern**

1. New features go to microservices, not monolith
2. Monolith routes some traffic to microservices (dual-write)
3. When microservice proven stable, cut over 100% traffic
4. Delete code from monolith

**Benefit**: No "big bang" rewrite, continuous delivery, lower risk.

### Lesson 3: Embrace Eventual Consistency Where Possible

**Strong consistency needed**:

- Payments (exactly-once charging)
- Driver assignment (one driver = one trip)
- Ratings (prevent double-rating)

**Eventual consistency acceptable**:

- Trip history (OK if takes 1 second to appear)
- Earnings dashboard (OK if delayed by 1 minute)
- Heatmaps (OK if 5 minutes stale)

**Uber's approach**: Use Schemaless with strong consistency within shard, eventual consistency cross-shard. Most use cases fit within a shard (user's data co-located).

### Lesson 4: Operability Matters as Much as Scalability

**What makes Schemaless operable**:

1. **Built on MySQL**: Leverage existing MySQL expertise, tooling (backups, replication, monitoring)
2. **Automated sharding**: No manual shard management, system rebalances automatically
3. **Schema versioning**: Schema changes via code deploy, not database ALTER
4. **Observability**: Every shard emits metrics (write rate, latency, replication lag)

**What makes Ringpop operable**:

1. **No external dependencies**: Embedded in service, no separate cluster to maintain
2. **Self-healing**: Gossip detects failures, re-routes automatically
3. **Debuggable**: Each node exposes ring view via HTTP endpoint

**The pattern**: Systems that operators can understand, debug, and fix at 3 AM are more valuable than theoretically optimal but opaque systems.

### Lesson 5: Test in Production (with Guardrails)

Uber couldn't fully test microservices in staging:

- Staging doesn't have 1M requests/sec
- Staging doesn't have 3M active drivers
- Staging doesn't have real failure modes (network partitions, cascading failures)

**Uber's approach**:

1. **Shadow traffic**: Dual-write to new system, compare results with old system
2. **Canary deploys**: Route 1% → 10% → 50% → 100% of traffic gradually
3. **Feature flags**: Turn on new code path for small percentage of users
4. **Chaos testing**: Deliberately fail instances, shards, datacenters

**Example: Schemaless migration**

1. Week 1-4: Shadow write to Schemaless, read from PostgreSQL (validate)
2. Week 5-8: Read 10% of traffic from Schemaless, rest from PostgreSQL (canary)
3. Week 9-12: Read 50% from Schemaless
4. Week 13: Read 100% from Schemaless
5. Week 14+: Decommission PostgreSQL

**Total migration time**: 3-4 months per service, but zero downtime, low risk.

---

## Key Takeaways

### The Core Innovations

1. **Schemaless**: Horizontally scalable writes via sharding, flexible schema via JSON versioning
2. **Ringpop**: Decentralized service discovery and request routing via consistent hashing + gossip
3. **H3**: Efficient geospatial queries via hexagonal grid indexing
4. **Incremental migration**: Strangler fig pattern for zero-downtime monolith decomposition
5. **Operability-first**: Build systems operators can understand and debug

### The Trade-Offs

**What Uber gained**:

- 1000× write scalability (10K → 10M writes/sec)
- 50× faster geospatial queries (2000ms → 40ms)
- Zero downtime deployments
- Independent team velocity (2200+ services)

**What Uber sacrificed**:

- Strong consistency across shards (eventual consistency)
- Distributed transactions (compensating transactions instead)
- Simplicity (1 app → 2200 services, operational complexity)
- Developer experience (microservices learning curve)

### When to Use Uber's Patterns

**Schemaless-style datastore**:

- Good fit: High write throughput, flexible schema, shardable by key
- Poor fit: Complex queries (JOINs, aggregations), strong cross-shard consistency

**Ringpop-style coordination**:

- Good fit: Request routing, sticky sessions, partition tolerance
- Poor fit: Strong consistency (use Raft/Paxos), external clients (use load balancer)

**H3-style geospatial**:

- Good fit: Proximity queries, real-time location tracking, millions of entities
- Poor fit: Exact distance queries, rare lookups (database index sufficient)

### The Evidence Lens on Uber

Uber's architecture generates and preserves critical evidence:

- **Dispatch evidence**: H3 index proves driver is nearby
- **Assignment evidence**: Schemaless transaction proves driver assigned to exactly one trip
- **Consistency evidence**: Compensating transactions prove eventual correctness
- **Availability evidence**: Ringpop gossip proves service health

When evidence conflicts (e.g., driver assigned to two trips due to race), **background reconciliation** detects and resolves using business logic (cancel one trip, compensate rider).

**The pattern**: In high-throughput systems, generate evidence optimistically, detect conflicts asynchronously, repair in background.

---

## Next Steps

We've explored four successful distributed systems: Spanner (global consistency via TrueTime), Dynamo (availability via eventual consistency), Netflix (resilience via chaos), and Uber (real-time scale via custom datastores).

**Continue to**: [Chapter 15: Building Your First Distributed System](../chapter-15/index.md)

**Related chapters**:
- [Chapter 6: Replication](../chapter-06/index.md) - Sharding and partitioning strategies
- [Chapter 8: Membership and Failure Detection](../chapter-08/index.md) - Gossip protocols
- [Chapter 11: Observability](../chapter-11/index.md) - Monitoring at scale

---

**References**:
- Uber Engineering Blog: https://eng.uber.com/
- "Schemaless: Uber Engineering's Trip Datastore" (2016)
- "Ringpop: Scalable, Fault-Tolerant Application-Layer Sharding" (2015)
- "H3: Uber's Hexagonal Hierarchical Spatial Index" (2018)
- Fowler, Martin. "Strangler Fig Pattern" (2004)
