# Chapter 11: Systems That Never Sleep - Planet-Scale Infrastructure

## Introduction: Operating at the Scale of Civilization

While you sleep tonight, billions of requests will flow through systems that haven't experienced a full outage in years.

When you search for something on Google at 3 AM, when you stream a show on Netflix on New Year's Eve, when you video call family across continents, when you check your bank balance while traveling—you're interacting with infrastructure operating at planet scale. These aren't just "big systems." They're systems designed to serve humanity as if distance, time zones, and continents don't exist.

This chapter explores what it takes to build and operate systems at planetary scale: the invariants that must hold across oceans, the evidence that must flow between continents, the modes that must degrade gracefully when regions fail, and the human systems required to operate infrastructure that never stops serving.

### Why Planet-Scale Matters

Most engineers will never build Google or Amazon. But understanding planet-scale systems transforms how you think about any distributed system:

**Before**: "We need five nines availability (99.999%)."
**After**: "Five nines means 5 minutes of downtime per year. At our revenue ($50K/minute), that's acceptable. But we need regional isolation so a datacenter failure doesn't exceed our budget. Our floor mode must preserve payment integrity while degrading search features."

**Before**: "This endpoint is slow (500ms p99)."
**After**: "500ms exceeds our fresh-read budget (200ms). We need bounded-staleness reads from local replicas with explicit δ=10s. That preserves our user experience invariant while reducing cross-region coordination."

**Before**: "Our monitoring is overwhelming—too many alerts."
**After**: "We're alerting on symptoms, not invariant violations. We need evidence-based alerts: lease expiry, quorum loss, staleness bound exceeded. Each alert maps to a specific degradation mode with a runbook."

### What This Chapter Will Transform

By the end, you'll understand:

1. **The Reality of 24/7/365**: What it takes to run systems that truly never stop serving users globally
2. **Regional Architecture**: How Google, Amazon, Meta, and Microsoft structure infrastructure across continents
3. **The Evidence Infrastructure**: Monitoring, observability, and evidence generation at planetary scale
4. **Invariants Across Continents**: Which guarantees must hold globally vs regionally vs locally
5. **Operational Modes at Scale**: How systems degrade when regions fail, how they recover, how humans operate them
6. **The Economics**: Cost per request, efficiency at scale, the business case for planet-scale
7. **Building It Yourself**: Principles and patterns you can apply at any scale

More crucially, you'll learn the **meta-pattern**: planet-scale systems succeed not by preventing all failures, but by **making failure normal, expected, and handled automatically**. The difference between large systems and planet-scale systems isn't size—it's the philosophy of embracing failure as the default operating mode.

### The Primary Invariant: AVAILABILITY

**Definition**: The system remains operational and serves user requests within bounded latency, globally, despite regional failures.

This isn't "high availability" (99.9% or 99.99%). This is **continuous availability** with graceful, principled degradation:

- A Google Search outage means "Google is down" becomes international news—it's that rare
- Netflix serves 200M+ subscribers across 190 countries without noticeable regional failures
- WhatsApp handles 100B+ messages per day with imperceptible degradation when datacenters fail
- Amazon serves billions of requests during Prime Day without the shopping experience breaking

**Supporting Invariants**:

- **PERFORMANCE**: Response times remain bounded globally (typically p99 <200ms for interactive services)
- **DURABILITY**: Data survives regional disasters (99.999999999% for S3 means losing 1 object per 100 billion per year)
- **CONSISTENCY**: Appropriate consistency level for each use case (not "always strong," but "explicitly chosen and maintained")
- **COMPLIANCE**: Regional regulations met (GDPR, data residency, privacy laws)

**Threat Model**:
- Regional disasters (hurricanes, earthquakes, power grid failures)
- Network partitions (undersea cable cuts, routing errors)
- Software bugs deployed globally (bad config, code regression)
- Cascading failures (overload in one region overwhelming others)
- Human errors (operator mistakes, misconfigurations)

The challenge: maintain the invariant across oceans, time zones, and regulatory boundaries while handling failures that affect millions of users simultaneously.

### The Conservation Principle

Throughout this chapter, observe the **conservation of evidence at scale**: the amount of evidence required to maintain invariants scales linearly with geographic distribution.

A single-datacenter system needs evidence within milliseconds (local network latency). A planet-scale system needs evidence across hundreds of milliseconds (intercontinental latency). This means:

- **More replication**: Evidence must exist in multiple regions to survive regional failures
- **More monitoring**: Evidence must be generated everywhere to detect failures anywhere
- **More automation**: Humans cannot generate or verify evidence at this scale and speed
- **More cost**: Evidence generation, propagation, and verification consume resources proportional to scale

Planet-scale isn't "big"—it's a phase transition where manual operation becomes impossible and automation becomes survival.

Let's begin with the always-on expectation—the user experience that planet-scale systems must deliver.

---

## Part 1: INTUITION (First Pass) — The Felt Need

### The New Year's Eve Problem

It's December 31st, 11:59 PM. In exactly 60 seconds, billions of people across the planet will simultaneously:

- Send "Happy New Year!" messages on WhatsApp (100B messages in the next hour)
- Post celebration videos on social media (500M photos/videos on Instagram/Facebook)
- Video call family across continents (500M concurrent calls on Zoom/FaceTime)
- Search for "fireworks near me" (1B+ searches on Google)
- Stream live events (200M+ streams on YouTube/Netflix)

This isn't gradual load. This is a **synchronized global spike** crossing time zones for 24 hours straight.

**What doesn't happen**:

- WhatsApp doesn't go down (despite 5× normal message volume)
- Instagram doesn't stop accepting uploads (despite 10× normal photo volume)
- Google Search doesn't slow down (despite coordinated surge)
- YouTube streams don't buffer (despite unprecedented concurrent viewers)

**What does happen** (invisibly):

At 11:00 PM (1 hour before):
- Load predictions trigger autoscaling (10,000+ additional servers spun up)
- Cache pre-warming begins (popular content replicated to edge locations)
- Database read replicas provisioned (handle search queries without impacting writes)
- Circuit breaker thresholds adjusted (higher tolerance for transient failures)
- On-call engineers alerted (all hands standby)

At 11:59 PM:
- Request rate spikes from 1M/sec to 5M/sec
- 80% of requests served from edge caches (geographic proximity, <50ms latency)
- Database writes queued and batched (eventual consistency acceptable for likes/views)
- Failed requests automatically retried (with exponential backoff)
- Degraded mode entered in some regions (non-essential features disabled: "People You May Know" recommendations off, "Trending" temporarily stale)

At 12:05 AM:
- Load begins to normalize
- Autoscaling gradually removes extra servers
- Caches expire old content
- Degraded mode exits (full features restored)
- Post-mortem begins (what went well, what needs improvement)

**The user experience**: Seamless. Messages delivered. Photos uploaded. Searches returned. Streams played. No one noticed the infrastructure gymnastics.

**The failure that didn't happen**: In 2013, Instagram went down on New Year's Eve. Messages lost. Photos failed to upload. Users frustrated. Competitors gained users. Instagram's reliability reputation damaged. Cost: immeasurable.

This is the **always-on expectation**: users expect systems to work flawlessly at the most critical moments. Planet-scale systems meet this expectation through:

1. **Regional isolation**: Failures contained to one region don't propagate globally
2. **Automatic failover**: Traffic rerouted transparently when regions fail
3. **Graceful degradation**: Non-essential features disabled before core functionality fails
4. **Evidence-based operation**: Every decision (scale up, degrade, fail over) based on metrics, not guesses
5. **Human preparation**: Teams drilled, runbooks tested, on-call ready

### The Global User Problem

It's 9 AM in New York. You search for "coffee shops near me" on Google. Response time: 50ms.

It's simultaneously 2 PM in London, 10 PM in Tokyo, 11 PM in Sydney.

**The constraint**: Speed of light. Light travels ~300,000 km/second. But:

- New York to London: 5,500 km / 300,000 km/s = 18ms (one way, ideal)
- Reality: Fiber optic cables (refractive index), routing hops, processing = ~40ms one way, 80ms round-trip
- New York to Tokyo: ~220ms round-trip
- New York to Sydney: ~250ms round-trip

**The problem**: If Google served all search requests from a single datacenter in California:

- New York users: 40ms (California) + processing = 60ms (acceptable)
- London users: 80ms (Atlantic crossing) + 40ms (to California) + processing = 140ms (slow)
- Tokyo users: 100ms (Pacific crossing) + processing = 120ms (slow)
- Sydney users: 130ms (Pacific crossing) + processing = 150ms (unacceptable)

Google's user experience target: <100ms for 95% of searches globally. This is **impossible** from a single location due to speed-of-light constraints.

**The solution**: Regional presence. Google has:

- **23+ data centers** globally (regions)
- **150+ edge locations** (Points of Presence)
- **Private global network** (not public internet)

When you search in Sydney:

1. **Request hits edge location** in Sydney (5ms)
2. **Edge serves cached results** if query is popular ("weather Sydney")
3. **If not cached**, request routed to **nearest regional datacenter** (Melbourne, 50ms round-trip)
4. **Regional datacenter** has index replicas for your region
5. **Results returned** to edge, cached, served to you
6. **Total latency**: 55ms (5ms edge + 50ms regional)

**The evidence flow**:

```
User (Sydney) → Edge (Sydney, 5ms)
                  ↓
                  Cache miss?
                  ↓
                Regional DC (Melbourne, 25ms) → Index lookup → Results
                  ↓
                Results cached at edge (for next user)
                  ↓
                User (Sydney) ← 55ms total
```

**Invariant**: PERFORMANCE — p95 latency <100ms globally.

**Evidence**: Per-region latency metrics, cache hit rates, round-trip time measurements.

**Mode Matrix**:
- **Target**: Edge cache hit rate >80%, regional latency <50ms
- **Degraded**: Edge cache miss, must query regional DC (latency <100ms)
- **Floor**: Regional DC unreachable, serve stale cache or fallback region (latency <200ms, marked as potentially stale)

**The human challenge**: You cannot manually optimize latency for users in 195 countries. You need:

- **Automatic edge cache population** (based on query patterns)
- **Intelligent routing** (GeoDNS, latency-based routing)
- **Regional replica placement** (data near users)
- **Evidence-based monitoring** (alerts on p95 latency violations, not arbitrary thresholds)

### The Cost of One Minute Down

It's October 4, 2021, 11:51 AM ET. Facebook, Instagram, WhatsApp—all go offline simultaneously.

**Cause**: BGP (Border Gateway Protocol) misconfiguration. Facebook's DNS servers became unreachable. The world couldn't resolve `facebook.com`, `instagram.com`, `whatsapp.com`. From the internet's perspective, Facebook ceased to exist.

**Duration**: 6 hours, 16 minutes.

**Impact**:

**Business**:
- **Revenue loss**: $100M+ (Facebook makes ~$300M/day in ad revenue)
- **Stock price drop**: -5% ($40B market cap loss)
- **User impact**: 3.5 billion users unable to access services

**Operational**:
- **Internal tools down**: Facebook employees use Facebook Workplace for communication. They couldn't coordinate. Badge systems tied to the network stopped working—engineers couldn't enter buildings to fix the problem.
- **Manual intervention required**: Engineers had to physically drive to data centers, gain physical access (without badge systems), manually reconfigure routers.

**Reputational**:
- **International news**: "Facebook is down" dominated global headlines
- **Competitor gains**: Telegram gained 70M new users in one day
- **Regulatory scrutiny**: Governments questioned centralized social media infrastructure

**What went wrong** (simplified):

1. **BGP configuration change** pushed to routers (routine maintenance)
2. **Validation tools failed** to catch error (missed evidence)
3. **Configuration withdrew all BGP routes** announcing Facebook's network to the internet
4. **Cascading effect**: DNS servers became unreachable → users couldn't resolve domain names → services appeared down
5. **Internal tools down**: Engineers couldn't access internal systems to diagnose/fix (dependency on same infrastructure)

**Invariant violated**: AVAILABILITY — System must remain reachable globally.

**Evidence missing**:
- **Pre-deployment validation** of BGP config failed
- **Redundant control plane** didn't exist (internal tools on same network)
- **Manual override** required physical presence (no out-of-band management)

**Mode failure**: System went directly from **Target** → **Complete failure**, skipping **Degraded** and **Floor** modes. No graceful degradation.

**Lessons**:

1. **Validation is evidence**: Configuration changes must be validated by independent systems before deployment
2. **Redundancy across failure domains**: Internal tools must not depend on the same infrastructure they manage
3. **Out-of-band access**: Manual override must be possible without the primary network
4. **Graceful degradation**: System should degrade (partial service) rather than fail completely
5. **Cost of downtime**: 6 hours = $100M+ direct loss, $40B market cap impact. One minute down at Facebook's scale = $270K lost revenue + immeasurable reputation damage.

**At planet scale, availability isn't a feature—it's an existential requirement.** Users, businesses, and entire economies depend on these systems. Downtime isn't just inconvenient; it's catastrophic.

### The 3 AM Incident

It's 3 AM. You're on-call for a planet-scale service (100M+ requests/day, 50+ regions).

Your phone vibrates. PagerDuty alert:

```
CRITICAL: Region US-EAST-1 - Replica lag >30s
Duration: 5 minutes
Impact: 15% of read traffic affected
Runbook: https://wiki/runbooks/replica-lag
```

You're groggy. You check the dashboard:

- **US-EAST-1**: Primary database serving writes normally. Replica database lagging 45 seconds (should be <1s).
- **Impact**: Read queries hitting replica get stale data. Write queries hitting primary unaffected.
- **Affected users**: 15% of global traffic (US East Coast users during their evening hours).

**The decision tree**:

**Option 1: Wait and monitor**
- Replica lag might self-resolve (transient spike, will catch up)
- Risk: Lag increases, users see very stale data (minutes old)
- Evidence needed: Lag trend (increasing or decreasing?)

**Option 2: Fail over reads to another region**
- Redirect US-EAST-1 reads to US-WEST-1 (healthy)
- Downside: Increased latency (East Coast users hitting West Coast datacenter, +50ms)
- Evidence needed: US-WEST-1 capacity (can it handle +15% traffic?)

**Option 3: Disable read replica, force reads to primary**
- Guaranteed fresh data (no lag)
- Downside: Primary handles all traffic (writes + reads), risk of overload
- Evidence needed: Primary capacity (CPU, connections available)

**Option 4: Enter degraded mode**
- Mark US-EAST-1 reads as "potentially stale" (return staleness metadata)
- Continue serving from replica
- Downside: Application must handle staleness explicitly
- Evidence needed: Application supports staleness metadata

You check the evidence:

- **Lag trend**: Increasing (45s → 52s → 61s). Not self-resolving.
- **US-WEST-1 capacity**: 40% CPU, can handle +15% traffic. ✓
- **Primary capacity**: 75% CPU, 80% connections. Risky to add read load. ✗
- **Application staleness support**: Implemented but not widely deployed. Partial. △

**The decision**: Fail over reads to US-WEST-1. Accept increased latency (50ms → 100ms) to preserve freshness invariant.

You execute the runbook:

```bash
# Update GeoDNS to route US-EAST-1 reads to US-WEST-1
$ kubectl annotate region us-east-1 read-failover=us-west-1

# Monitor impact
$ watch 'curl -s https://metrics/api/latency?region=us-east-1 | jq .p95'
```

**Result**:
- Latency increases: 50ms → 95ms (p95). Within acceptable range (<100ms SLA). ✓
- Staleness eliminated: Reads now fresh. ✓
- US-WEST-1 load increases: 30% → 48% CPU. Acceptable. ✓
- Alert resolves after 15 minutes (replica catches up, failover reverted automatically). ✓

**Post-incident**:
- **Root cause**: Database vacuum process consumed I/O, starved replication stream.
- **Fix**: Tune vacuum schedule, increase I/O priority for replication.
- **Prevention**: Add monitoring for vacuum I/O impact, alert before lag occurs.
- **Evidence improvement**: Add predictive lag monitoring (trend, not threshold).

**What made this manageable**:

1. **Evidence-based alerting**: Alert included impact (15% traffic), duration (5 min), runbook link
2. **Clear decision tree**: Runbook outlined options with trade-offs
3. **Capacity visibility**: Dashboards showed regional capacity in real-time
4. **Automatic failover capability**: One command to reroute traffic
5. **Automatic recovery**: System reverted failover when replica caught up
6. **Blameless post-mortem**: Focus on system improvement, not human blame

**What would make this nightmare at smaller scale**:

1. **No runbook**: Engineer guesses, makes wrong decision, causes outage
2. **No capacity visibility**: Fails over to overloaded region, cascading failure
3. **Manual failover**: Requires editing configs, restarting services, DNS propagation delay
4. **No automatic recovery**: Engineer forgets to revert, pays cross-region costs indefinitely
5. **Blame culture**: Engineer afraid to make decisions, waits for escalation, impact grows

**The human factor at planet scale**: Incidents happen when humans sleep. Systems must be:

- **Self-diagnosing**: Evidence collection automatic
- **Self-healing**: Common failures resolved automatically (replica lag → automatic failover)
- **Operator-friendly**: When humans needed, clear actions with known trade-offs
- **Blameless**: Encourage fast decisions, learn from mistakes, improve systems

### The Pattern: Planet-Scale is a Different Game

These stories illustrate the phase transition from "large systems" to "planet-scale systems":

**Large systems**:
- Serve millions of users
- Operate in one or a few regions
- Tolerate brief outages (99.9% = 8 hours/year downtime)
- Manual operation during business hours
- Humans in the loop for most decisions

**Planet-scale systems**:
- Serve billions of users
- Operate in dozens of regions across continents
- Cannot tolerate outages (99.99%+ = <1 hour/year downtime)
- Automated operation 24/7/365
- Humans handle only exceptional cases

The difference isn't size—it's **philosophy**:

- **Embrace failure**: Assume failures happen constantly (hardware, network, software, human). Design for failure as normal.
- **Automate everything**: Humans cannot react fast enough or stay awake 24/7. Automation is survival, not optimization.
- **Evidence-driven**: Every decision based on metrics, not intuition. Alerts map to invariant violations, not arbitrary thresholds.
- **Graceful degradation**: Systems have explicit modes (target, degraded, floor, recovery) with known trade-offs.
- **Economic optimization**: Cost per request matters. Efficiency improvements compound across billions of requests.

Let's now build mental models of how planet-scale systems actually work.

---

## Part 2: UNDERSTANDING (Second Pass) — Building Mental Models

### Google's Infrastructure: The Pioneer

Google invented much of modern planet-scale infrastructure out of necessity. In the early 2000s, no commercial systems could handle billions of searches per day. Google built its own: custom servers, custom storage, custom networks, custom everything.

#### The Physical Layer

**Global Footprint** (as of 2024):

- **23+ data center regions** (US: 9, Europe: 6, Asia-Pacific: 7, South America: 1)
- **150+ edge Points of Presence** (CDN nodes near users)
- **Private submarine cables**: Google owns/leases fiber optic cables crossing oceans (Atlantic, Pacific, Indian)
- **100+ Tbps network capacity** (multiple terabits per second between regions)

**Why private infrastructure?**

**Problem**: Public internet has unpredictable latency (routing, congestion), limited capacity (shared with everyone), potential for eavesdropping.

**Solution**: Google routes most inter-datacenter traffic over its own fiber, bypassing the public internet entirely.

**Evidence**: Google can guarantee latency bounds between datacenters (40ms US East-West, 120ms US-Europe) because they control the entire path. Public internet offers no such guarantees.

**Network Architecture**:

**B4 (Software-Defined WAN)**:
- Connects Google datacenters globally
- Software-defined routing (centralized controller decides paths)
- Traffic engineering (optimize bandwidth usage)
- Multi-path routing (use multiple cables simultaneously for bandwidth)

**Jupiter (Datacenter Network)**:
- Connects servers within a datacenter
- Multi-stage Clos topology (non-blocking, any-to-any communication)
- 1 Pbps (petabit per second) bisection bandwidth in largest datacenters

**Edge Network**:
- Users connect to nearest edge location (150+ globally)
- Edge terminates TLS (reduces latency—no roundtrip to datacenter for handshake)
- Edge caches static content (YouTube videos, Search results for popular queries)

**The evidence flow**:

```
User → Edge (5-20ms) → Cache hit?
         ↓ Yes: Serve from cache (5-20ms total)
         ↓ No: Query regional datacenter
                  ↓
         Regional DC (30-80ms) → Cache result → Serve user
                  ↓
         Edge caches for next user
```

#### The Software Stack

Google's software is layered, with each layer providing guarantees to the one above:

```
Applications (Search, YouTube, Gmail, Maps, Drive)
         ↓
Frameworks (MapReduce, Flume, MillWheel, Dataflow)
         ↓
Storage (Bigtable, Spanner, Colossus, Megastore)
         ↓
Infrastructure (Borg, Chubby, GFS → Colossus)
         ↓
Hardware (Custom servers, Jupiter, B4)
```

Each layer abstracts the one below:

- **Hardware** provides compute, storage, network
- **Infrastructure** provides resource allocation (Borg), coordination (Chubby), distributed file system (Colossus)
- **Storage** provides structured data (Bigtable), globally-consistent data (Spanner)
- **Frameworks** provide data processing (MapReduce), stream processing (MillWheel)
- **Applications** implement user-facing features

**Invariant**: Each layer preserves invariants for the layer above, abstracting away complexity below.

#### Borg: The Orchestration Pioneer

**What it does**: Borg is Google's cluster orchestration system (like Kubernetes, which Google open-sourced based on Borg's lessons).

**Purpose**: Allocate resources (CPU, memory, disk, network) across tens of thousands of servers to millions of jobs.

**Abstractions**:

**Job**: A collection of tasks (e.g., "Web search serving" job has 10,000 tasks running across servers).

**Task**: A single running instance (container).

**Alloc**: A reserved set of resources on a machine (tasks run inside allocs).

**Priority**: Jobs have priority (0-450). Higher priority jobs can preempt lower priority.

**Quota**: Teams have resource quotas (you can run 100,000 cores, 500 TB RAM).

**Architecture**:

```
BorgMaster (5 replicas, Paxos for consensus)
    ↓
Scheduler (decides task → machine placement)
    ↓
Borglets (agent on each machine, runs tasks)
```

**BorgMaster** maintains cluster state:
- Which tasks are running where
- Which machines are healthy
- Which jobs need more/fewer tasks (autoscaling)

**Scheduler** decides task placement based on:
- Resource requirements (task needs 4 cores, 16 GB RAM)
- Constraints (must run in US-EAST-1, on SSD-equipped machines)
- Priority (higher priority tasks preempt lower priority)
- Utilization (pack efficiently, reduce wasted resources)

**Invariants preserved**:

1. **Resource isolation**: Tasks don't interfere (containers, cgroups)
2. **Priority enforcement**: High-priority tasks always get resources (preemption)
3. **Fault tolerance**: BorgMaster uses Paxos (majority quorum survives failures)
4. **Quota enforcement**: Teams can't exceed allocated resources

**Evidence mechanisms**:

- **Health checks**: BorgMaster pings Borglets every few seconds (evidence of machine health)
- **Task state**: Each task has state (PENDING, RUNNING, FAILED), tracked centrally
- **Resource usage**: Borglets report actual CPU/memory usage (evidence for quota enforcement)
- **Scheduling decisions**: Logged and auditable (why did this task land on this machine?)

**Mode matrix**:

- **Target**: All machines healthy, scheduler placing tasks optimally, jobs scaling as needed
- **Degraded**: Some machines failed, scheduler redistributing tasks, may take minutes to re-place
- **Floor**: BorgMaster minority partition (cannot accept new jobs, existing jobs continue running)
- **Recovery**: BorgMaster majority restored, reconciling task state, re-scheduling failed tasks

**Why Borg matters**: At Google's scale (millions of tasks across hundreds of thousands of machines), manual placement is impossible. Borg enables:

- **Efficient utilization**: Machines run at 60-70% average (vs 10-15% without orchestration)
- **Automatic failure recovery**: Failed tasks restarted automatically within seconds
- **Rolling updates**: Deploy new software without downtime (gradually replace tasks)
- **Multi-tenancy**: Mix batch jobs (low priority, use spare capacity) with serving jobs (high priority, guaranteed resources)

Kubernetes (open-sourced in 2014) brought Borg's ideas to the world.

#### Spanner: The Global Database

**What it does**: Spanner is Google's globally-distributed SQL database with strong consistency across continents.

**The impossibility it defies**: CAP theorem says you can't have consistency + availability during partitions. PACELC says you trade latency for consistency even without partitions.

**Spanner's approach**: Choose consistency. During partitions, minority regions become unavailable. Accept higher latency for global transactions (cross-continent writes take 100-300ms).

**The key innovation: TrueTime API**

**Problem**: Ordering events across datacenters requires synchronized clocks. But clocks drift. NTP (Network Time Protocol) can sync clocks to ~1ms, but that's not good enough for ordering events at microsecond granularity.

**Solution**: TrueTime provides time as an interval, not a point:

```cpp
struct TTInterval {
  int64_t earliest;  // earliest possible current time
  int64_t latest;    // latest possible current time
};

TTInterval now = TT.now();
// now.earliest <= actual time <= now.latest
```

**How it works**:
- GPS receivers and atomic clocks in each datacenter (authoritative time sources)
- Time masters sync with GPS/atomic clocks
- Time daemons on each machine sync with time masters
- TrueTime API returns interval based on worst-case clock drift

**Guarantee**: `TT.now().earliest <= actual_time <= TT.now().latest`

Typical uncertainty: 1-7ms (depends on time since last sync, local clock quality).

**Using TrueTime for ordering**:

```cpp
// Assign timestamp to transaction
start_time = TT.now().latest;  // latest possible time

// Wait out uncertainty
while (TT.now().earliest < start_time) {
  sleep(1ms);
}
// Now we KNOW start_time is in the past

// Commit transaction with timestamp start_time
commit(transaction, start_time);
```

**Invariant**: External consistency (if transaction A completes before transaction B starts, A's timestamp < B's timestamp).

**Evidence**: TrueTime intervals provide verifiable proof of ordering without requiring perfect clock synchronization.

**Architecture**:

```
Spanner Deployment (global)
    ↓
Zones (groups of servers in same datacenter)
    ↓
Spanservers (serve data)
    ↓
Tablet (key range, replicated via Paxos)
```

Each tablet (horizontal shard) is replicated across 3+ zones using Paxos. Writes require majority quorum. Reads can be local (if sufficiently stale) or quorum (if must be fresh).

**Read modes**:

**Strong reads** (linearizable):
- Read from leader (guaranteed fresh)
- Or read from follower with read-time > last-committed-time (wait until follower catches up)
- Latency: Local reads <10ms, cross-region reads 50-200ms

**Stale reads** (bounded staleness):
- Read from local follower, accept staleness
- Application specifies max staleness (10s old is acceptable)
- Latency: <10ms (local)

**Evidence**:
- Strong reads: Leader lease + safe time proof
- Stale reads: Explicit staleness bound δ

**Why Spanner matters**:

Before Spanner, "globally distributed SQL database with strong consistency" was considered impossible (CAP theorem). Spanner proved it's possible by:

1. **Choosing consistency over availability**: Minority partitions become unavailable
2. **Using TrueTime**: Novel approach to time synchronization enables global ordering
3. **Accepting latency cost**: Cross-region writes are slow (100-300ms), but acceptable for use cases like financial transactions

**Production stats**:

- Powers Google's most critical services: AdWords (billions in revenue), Google Play, Google Photos
- Trillions of queries per month
- 99.999% availability (5-minute downtime per year across all regions)
- Replication across 3-5 regions (tolerate 1-2 region failures)

### Amazon's Scale: The Everything Store

Amazon runs AWS (Amazon Web Services), the world's largest cloud provider. Understanding AWS reveals planet-scale from a different angle: multi-tenancy (millions of customers sharing infrastructure).

#### AWS Global Infrastructure

**Regions** (31 as of 2024):
- Isolated geographic areas (US-EAST-1, EU-WEST-1, AP-SOUTHEAST-1, etc.)
- Each region has multiple Availability Zones

**Availability Zones** (99 total):
- Isolated datacenters within a region (typically 3-6 per region)
- Separate power, networking, cooling (failures don't cascade between AZs)
- Low-latency connection between AZs in same region (<2ms)

**Edge Locations** (450+):
- CloudFront CDN nodes near users
- Route 53 DNS servers (globally distributed)
- Lambda@Edge (serverless compute at edge)

**Local Zones** (19):
- Smaller deployments in metro areas (Los Angeles, Boston, etc.)
- Lower latency for users not near full regions

**Outposts**:
- AWS hardware in customer datacenters (hybrid cloud)

**Why this structure?**

**Invariant**: Isolation. Failures in one AZ or region don't propagate.

**Evidence**: Each AZ has independent power (from separate grids), independent network connectivity (multiple ISP uplinks), physical separation (far enough to survive localized disasters like fires, close enough for low latency).

#### The Service Ecosystem

AWS offers 200+ services. Key ones for planet-scale:

**Compute**:
- EC2 (virtual machines)
- Lambda (serverless functions)
- ECS/EKS (containers)
- Fargate (serverless containers)

**Storage**:
- S3 (object storage, 11 nines durability)
- EBS (block storage for EC2)
- EFS (file storage)
- Glacier (archival)

**Databases**:
- RDS (managed relational: MySQL, PostgreSQL, etc.)
- DynamoDB (NoSQL, planet-scale)
- Aurora (MySQL/PostgreSQL compatible, global)
- ElastiCache (Redis, Memcached)

**Networking**:
- VPC (virtual private cloud)
- Route 53 (DNS, global routing)
- CloudFront (CDN)
- Direct Connect (private link to AWS)

**The philosophy**: Primitives, not solutions. AWS provides building blocks. Customers assemble them.

**Evidence**: AWS publishes SLAs (Service Level Agreements) for each service. For example:

- **EC2**: 99.99% availability per region (if you use multiple AZs)
- **S3**: 99.99% availability, 99.999999999% durability (11 nines)
- **DynamoDB**: 99.99% availability (single region), 99.999% (global tables)

If AWS misses SLA, customers get credits (money back). This creates economic incentive for reliability.

#### DynamoDB: Planet-Scale NoSQL

**What it is**: Fully managed NoSQL database, automatic scaling, single-digit millisecond latency, global replication.

**Why it exists**: Amazon needed a database for shopping cart (must be available during Black Friday, even if a datacenter fails). Relational databases prioritize consistency over availability (CP in CAP). Amazon needed AP (available, partition-tolerant).

**Key ideas**:

**1. Consistent Hashing for Distribution**

Problem: Distribute data across thousands of servers. Traditional hashing (hash(key) % N) requires reshuffling all data when servers added/removed.

Solution: Consistent hashing. Servers form a ring. Keys hashed to ring positions. Each key served by the next server clockwise on the ring.

```python
# Simplified consistent hashing
class ConsistentHash:
    def __init__(self):
        self.ring = {}  # position -> server
        self.sorted_keys = []

    def add_server(self, server):
        # Add server to ring at hash(server) position
        position = hash(server)
        self.ring[position] = server
        self.sorted_keys = sorted(self.ring.keys())

    def get_server(self, key):
        # Find first server >= hash(key) on ring
        key_hash = hash(key)
        for position in self.sorted_keys:
            if position >= key_hash:
                return self.ring[position]
        # Wrap around
        return self.ring[self.sorted_keys[0]]
```

**Benefit**: Adding/removing servers only affects adjacent keys (1/N of data), not all data.

**2. Replication for Durability**

Each key replicated to N servers (typically N=3). Original DynamoDB paper used N=3, with replicas on the next 2 servers clockwise on the ring.

**3. Quorum for Consistency**

- **W**: Write quorum (how many replicas must ack a write). Typically W=2.
- **R**: Read quorum (how many replicas must respond to a read). Typically R=2.
- **N**: Total replicas. Typically N=3.

**Guarantee**: If W + R > N, reads see all writes (at least one replica in read set participated in the write).

Example: N=3, W=2, R=2. W+R=4 > 3. Every read sees the latest write.

**Trade-off**: Lower W or R → lower latency (fewer servers to wait for), but weaker consistency.

```python
# Quorum read/write
class QuorumStore:
    def write(self, key, value):
        servers = self.get_replicas(key, N=3)
        acks = 0
        for server in servers:
            if server.write(key, value):
                acks += 1
            if acks >= W:  # W=2
                return SUCCESS
        return FAILURE  # Didn't get quorum

    def read(self, key):
        servers = self.get_replicas(key, N=3)
        responses = []
        for server in servers:
            responses.append(server.read(key))
            if len(responses) >= R:  # R=2
                # Return latest value (highest version)
                return max(responses, key=lambda r: r.version)
        return FAILURE  # Didn't get quorum
```

**4. Hinted Handoff for Availability**

Problem: If a replica is down during a write, do we fail the write (unavailable) or succeed with fewer replicas (less durable)?

DynamoDB's solution: **Hinted handoff**. If a replica is down, write to a different server with a "hint" that this data belongs to the down server. When the down server recovers, the hint is delivered.

```python
def write_with_handoff(key, value):
    primary_servers = get_replicas(key, N=3)
    acks = 0

    for server in primary_servers:
        if server.is_available():
            server.write(key, value)
            acks += 1
        else:
            # Write hint to another server
            hint_server = get_alternative_server()
            hint_server.store_hint(server, key, value)
            acks += 1  # Count hint as ack

        if acks >= W:
            return SUCCESS
```

**Invariant**: Writes succeed even if some replicas are down (availability).

**Evidence**: Hinted handoff ensures writes eventually reach all replicas (eventual consistency), even if some are temporarily unavailable.

**5. Conflict Resolution**

Problem: During network partition, two replicas might accept conflicting writes (same key, different values). How do we resolve?

Options:
- **Last-write-wins** (LWW): Use timestamp. Latest write wins. Simple, but loses data if clocks skew.
- **Vector clocks**: Track causality. If writes are concurrent (neither causally preceded the other), application resolves conflict (merge shopping carts, for example).

DynamoDB uses **version numbers** and allows application-level conflict resolution.

**Evidence**: Vector clocks provide causal ordering evidence, allowing application to make informed merge decisions.

**Production stats**:

- **10 trillion requests/day** across all DynamoDB tables
- **20M requests/second** peak
- **Single-digit millisecond** p99 latency
- **Exabytes of data** stored
- **Global tables**: Replicate data across multiple regions, <1s replication lag

**Why DynamoDB matters**: Proved that AP (available, partition-tolerant) databases can operate at planet scale with predictable performance. Influenced Cassandra, Riak, Azure Cosmos DB.

#### S3: Eleven Nines of Durability

**What it is**: Object storage. Store files (images, videos, backups, logs) as objects with unique keys.

**The guarantee**: 99.999999999% durability (11 nines). This means if you store 10 billion objects, you'll lose 1 object per year, on average.

**How it achieves this**:

**1. Replication Across Availability Zones**

Every object stored in S3 is automatically replicated to at least 3 Availability Zones in the region.

**Probability of data loss**:
- Assume each AZ has 0.1% annual failure rate (99.9% availability)
- Probability all 3 AZs fail simultaneously: (0.001)^3 = 0.000000001 = 0.0000001%
- Durability: 99.9999999% (9 nines)

But S3 claims 11 nines. How?

**2. Automatic Error Detection and Repair**

S3 constantly verifies data integrity:
- **Checksums**: Every object has a checksum (SHA-256 or MD5). On read, S3 verifies checksum. If mismatch, repair from replica.
- **Background scrubbing**: S3 continuously reads objects in the background, verifies checksums, repairs any corruption.
- **Bit rot detection**: Silent data corruption (cosmic rays flipping bits in storage) detected and repaired.

**Evidence**: Checksums are cryptographic proof of data integrity.

**3. Versioning**

S3 supports versioning. If you overwrite or delete an object, previous versions are retained (unless explicitly deleted). This protects against accidental deletion or corruption.

**4. Object Lock**

For compliance (financial, medical), S3 supports WORM (Write Once Read Many) mode. Objects cannot be deleted or modified for a specified retention period.

**Invariant**: Data durability. Objects, once written, are not lost.

**Evidence**:
- Multi-AZ replication (geographic diversity)
- Checksums (integrity verification)
- Versioning (protection against accidental loss)
- Background scrubbing (proactive repair)

**Production stats**:

- **100 trillion objects** stored
- **Exabytes of data** (Amazon doesn't publish exact number, but estimated >200 exabytes)
- **Millions of requests/second** globally
- **99.99% availability** SLA
- **99.999999999% durability** (11 nines)

**Why S3 matters**: Set the standard for cloud object storage. Every cloud provider now offers S3-compatible storage (Google Cloud Storage, Azure Blob Storage). Entire businesses built on top of S3 (backup, archival, media storage, data lakes).

### Meta's Social Scale: Billions of Connections

Meta (Facebook/Instagram/WhatsApp) operates at a scale defined by connections, not just users:

- **3.9 billion monthly active users** across all apps (2024)
- **Social graph**: Billions of users, hundreds of billions of friendships/follows
- **100 billion messages/day** (WhatsApp)
- **4 billion video streams/day** (Facebook/Instagram)
- **350 million photos/day** (Instagram)
- **500 TB/day** of new data

The challenge: Not just storing data, but **traversing relationships** (friends, followers, likes, comments) at planet scale.

#### TAO: The Social Graph Store

**What it is**: TAO (The Associations and Objects) is Meta's distributed data store for the social graph.

**The problem**: Relational databases don't scale for graph queries. Finding "friends of friends" or "people who liked this post" requires joins across billions of rows. Too slow.

**The model**:

**Objects**: Users, posts, photos, comments (anything with an ID).

**Associations**: Relationships between objects (user→friend→user, user→likes→post, post→has→comment).

```cpp
struct Object {
    int64_t id;        // unique object ID
    int32_t type;      // object type (USER, POST, PHOTO, etc.)
    map<string, string> data;  // key-value attributes
};

struct Association {
    int64_t id1;       // source object
    int32_t atype;     // association type (FRIEND, LIKES, COMMENT, etc.)
    int64_t id2;       // destination object
    int64_t time;      // creation time (for ordering)
    map<string, string> data;  // key-value attributes
};
```

**Example**: "Alice likes Bob's post"
- Object: Alice (user)
- Object: Post (Bob's post)
- Association: Alice --LIKES--> Post

**Queries**:

```cpp
// Get all of Alice's friends
assoc_range(Alice.id, FRIEND)

// Get all likes on Bob's post
assoc_range(Post.id, LIKES)

// Get all posts Alice liked
assoc_range(Alice.id, LIKES)
```

**The architecture**:

```
Applications (Facebook/Instagram/WhatsApp)
         ↓
TAO (cache layer, read-through)
         ↓
MySQL (storage layer, sharded)
```

TAO is a **cache** on top of MySQL. All reads hit TAO first. If cached, return immediately. If not cached, query MySQL, cache result, return.

**Why cache-first?**

- **Read-heavy**: Social graph is 99%+ reads (viewing posts, profiles) vs writes (posting, liking).
- **Hot data**: Most reads hit small portion of data (popular users, trending posts).
- **Cache hit rate**: TAO achieves >95% cache hit rate. Most requests never hit MySQL.

**Sharding**:

MySQL is sharded by object ID. Each shard stores a range of IDs.

TAO cache is replicated across datacenters. Each datacenter has full cache (or subset, for regional data).

**Consistency**:

- **Writes**: Go to MySQL (master database), then invalidate cache.
- **Reads**: Hit cache (may be stale until invalidation propagates).

**Guarantee**: Eventual consistency. Reads may see stale data briefly (seconds), but eventually see all writes.

**Evidence**: Invalidation messages propagate from MySQL to all TAO caches. Evidence of write completion.

**Why TAO matters**: Enables billions of people to interact socially (view friends, like posts, comment) with sub-10ms latency despite the social graph having hundreds of billions of edges.

#### Haystack: Photo Storage

**The problem**: Facebook stores hundreds of billions of photos. Traditional file systems (store each photo as a file) have problems:

- **Metadata overhead**: Each file requires inode (metadata). For billions of files, metadata exceeds actual data size.
- **Disk seeks**: Accessing a file requires seeking to inode, then seeking to data. At HDD speeds (10ms seek), this limits throughput.

**The solution: Haystack**

**Idea**: Store multiple photos per file. Append photos to large files (100 GB each). Index maps photo ID → (file, offset).

```
Haystack File (100 GB):
[Photo 1][Photo 2][Photo 3]...[Photo 1000000]

Index:
Photo 1 → (File A, offset 0)
Photo 2 → (File A, offset 50000)
Photo 3 → (File A, offset 120000)
...
```

**Benefit**:
- **One seek per read**: Seek to offset, read photo. No metadata seek.
- **Append-only writes**: New photos appended to current file. When file full, start new file.
- **Compact metadata**: Index in memory (photo ID → offset), not on disk.

**Replication**: Each photo stored in 3+ Haystack files (different servers, different failure domains).

**CDN integration**: Popular photos served from CDN (edge cache). Haystack only hit for long-tail (unpopular photos).

**Invariant**: Photo durability (photos not lost) and retrieval performance (one seek per read).

**Evidence**: Replication across servers, checksums for integrity.

**Why Haystack matters**: Enabled Facebook to scale photo storage beyond what traditional file systems could handle, with custom-built solution optimized for their workload.

### Microsoft Azure's Approach: Enterprise Planet-Scale

Azure is Microsoft's cloud, targeting enterprises (businesses) as primary customers. Different design priorities than AWS (which targets startups/tech companies).

#### Global Footprint

- **60+ regions** (more than AWS, covers more geographies)
- **170+ datacenters**
- **130,000+ miles of fiber** (private network)
- **180+ edge locations**

**Why so many regions?** Enterprise customers need data residency (store data in specific countries for legal compliance). Azure offers more regions to meet these needs.

#### Cosmos DB: Globally Distributed Database

**What it is**: Multi-model database (document, key-value, graph, column-family), globally distributed, multiple consistency levels.

**The key idea**: Let the application choose consistency level per request. Not "the database is strongly consistent" or "eventually consistent," but "this request is strongly consistent, that request is eventually consistent."

**Five consistency levels** (spectrum from strong to weak):

**1. Strong** (Linearizable):
- Reads guaranteed to see latest write
- Writes must reach majority quorum before acknowledged
- Highest latency (cross-region coordination)
- **Guarantee vector**: `⟨Global, Lx, SER, Fresh(φ), Idem, Auth⟩`

**2. Bounded Staleness** (Time-bounded):
- Reads may lag behind writes by at most K versions or T time
- Application specifies K (e.g., 10 versions) or T (e.g., 5 seconds)
- Lower latency than strong, guarantee on staleness bound
- **Guarantee vector**: `⟨Global, —, SI, BS(δ=T), Idem, Auth⟩`

**3. Session** (Per-client consistency):
- Reads see all writes from same session (same user)
- Different sessions may see different versions
- Implemented with session tokens (evidence of session context)
- **Guarantee vector**: `⟨Session, Causal, RA, Fresh(session), Idem, Auth⟩`

**4. Consistent Prefix** (Causal without gaps):
- Reads see writes in order (no gaps in version sequence)
- But may not see the latest write
- **Guarantee vector**: `⟨Global, Causal, RA, EO, Idem, Auth⟩`

**5. Eventual** (Weakest):
- Reads may see any version
- Eventually (given enough time with no writes), all replicas converge
- Lowest latency (local reads, no coordination)
- **Guarantee vector**: `⟨Local, —, —, EO, Idem, Auth⟩`

**Application choice**:

```csharp
// Strong consistency (financial transaction)
var response = await container.ReadItemAsync<Account>(
    id,
    partitionKey,
    new ItemRequestOptions { ConsistencyLevel = ConsistencyLevel.Strong }
);

// Bounded staleness (dashboard, 10s staleness acceptable)
var response = await container.ReadItemAsync<Metrics>(
    id,
    partitionKey,
    new ItemRequestOptions { ConsistencyLevel = ConsistencyLevel.BoundedStaleness }
);

// Eventual (analytics, freshness not critical)
var response = await container.ReadItemAsync<Log>(
    id,
    partitionKey,
    new ItemRequestOptions { ConsistencyLevel = ConsistencyLevel.Eventual }
);
```

**Evidence**:
- **Strong**: Commit certificates from majority quorum
- **Bounded Staleness**: Explicit δ (time or version bound)
- **Session**: Session tokens carried by client
- **Eventual**: None (best-effort)

**Why Cosmos DB matters**: First mainstream database to offer consistency as a spectrum, not a binary choice. Applications optimize latency vs consistency per-request, not per-database.

**Production stats**:

- **99.999% availability** SLA (multi-region writes)
- **<10ms p99 latency** (reads and writes)
- **Automatic partitioning** (scales to petabytes)
- **Turn-key global replication** (add region with one click)

### The Pattern: Evidence Infrastructure at Scale

Across Google, Amazon, Meta, Microsoft, the same patterns emerge:

**1. Regional Isolation**

Regions are failure domains. Failures in one region don't propagate to others.

**Evidence**: Independent power, network, control planes.

**2. Replication for Durability**

Data replicated across multiple failure domains (AZs, regions, datacenters).

**Evidence**: Quorum protocols, checksums, background verification.

**3. Caching for Performance**

Hot data cached close to users (edge, regional caches).

**Evidence**: Cache hit rates, time-to-live (TTL), invalidation messages.

**4. Automatic Failover**

When a component fails, traffic automatically routed to healthy component.

**Evidence**: Health checks, heartbeats, lease expiry.

**5. Graceful Degradation**

Systems degrade features (non-essential) before failing completely.

**Evidence**: Mode transitions based on capacity, error rates, latency.

**6. Observability**

Comprehensive monitoring, logging, tracing.

**Evidence**: Metrics (latency, error rate, throughput), logs (structured, searchable), traces (distributed, causally linked).

These patterns form the **evidence infrastructure** required for planet-scale operation.

---

## Part 3: MASTERY (Third Pass) — Evidence, Invariants, and Operation

### Evidence at Planet Scale

At planet scale, evidence serves multiple purposes:

**1. Health Evidence**: Is the system working?

**Metrics**:
- **Golden signals** (Google SRE): Latency, Traffic, Errors, Saturation
- **Request rate**: Requests per second (overall, per region, per service)
- **Error rate**: Errors per second, error percentage
- **Latency distribution**: p50, p95, p99, p99.9 (not average, which hides problems)
- **Saturation**: CPU, memory, disk, network utilization

**Collection**:
- **Push-based**: Services send metrics to central system (Prometheus, CloudWatch)
- **Pull-based**: Central system scrapes metrics from services (Prometheus)
- **Sampling**: High-volume metrics sampled (record 1% of requests, infer total)

**Evidence lifecycle**:
- **Generated**: Every request generates metrics (latency, status code)
- **Aggregated**: Metrics aggregated regionally (reduce data volume)
- **Analyzed**: Anomaly detection, alerting rules
- **Archived**: Retained for compliance, post-mortems (30-90 days typical)

**2. Capacity Evidence**: Can the system handle load?

**Metrics**:
- **Resource utilization**: CPU, memory, disk, network (per server, per region)
- **Request capacity**: Max requests per second before saturation
- **Headroom**: Spare capacity (operate at 60% to have 40% headroom for spikes)

**Usage**:
- **Autoscaling**: Add servers when CPU >70%, remove when <40%
- **Capacity planning**: Project future needs based on growth trends
- **Overload protection**: Reject requests when capacity exhausted (fail fast, don't cascade)

**3. Dependency Evidence**: What does the system depend on?

**Metrics**:
- **Service dependencies**: Service A calls Service B calls Service C (dependency graph)
- **Critical path**: Which dependencies are on the critical path (blocking user requests)?
- **Dependency health**: Latency, error rate of dependencies

**Usage**:
- **Circuit breakers**: If dependency failing, stop calling it (fail fast, reduce load)
- **Retries**: If dependency transiently failing, retry with backoff
- **Fallbacks**: If dependency unavailable, serve degraded experience (cached data, default values)

**Evidence**: Distributed tracing (trace requests across services, identify slow dependencies).

**4. Compliance Evidence**: Does the system meet regulatory requirements?

**Metrics**:
- **Data residency**: Data stored in correct region (GDPR: EU data in EU)
- **Access logs**: Who accessed what data when (audit trail)
- **Retention**: Data deleted after retention period (privacy)

**Usage**:
- **Audit reports**: Prove compliance to regulators
- **Incident response**: Identify unauthorized access
- **Privacy enforcement**: Ensure deletion requests honored

**Evidence**: Audit logs, retention policies, access control lists.

### Planet-Scale Invariants

At planet scale, invariants have **geographic scope**:

**Global Invariants** (must hold everywhere):

1. **Data Integrity**: Data not corrupted
   - **Evidence**: Checksums, replication, background scrubbing
   - **Mode**: Never degrade (corrupted data is unacceptable)

2. **Authenticity**: Only authorized users access data
   - **Evidence**: Authentication tokens, encryption, access logs
   - **Mode**: Never degrade (security is non-negotiable)

3. **Compliance**: Regional laws followed
   - **Evidence**: Data residency, audit logs, retention policies
   - **Mode**: Never degrade (legal requirement)

**Regional Invariants** (must hold per region, but can differ between regions):

1. **Availability**: System serves requests
   - **Evidence**: Health checks, request success rate
   - **Mode**: Degrade gracefully (disable features, not the entire system)

2. **Performance**: Latency within bounds
   - **Evidence**: p95/p99 latency
   - **Mode**: Degrade to stale reads, cached responses if fresh data too slow

3. **Consistency**: Data matches expected consistency level
   - **Evidence**: Replication lag, quorum responses
   - **Mode**: Degrade to weaker consistency (strong → bounded → eventual)

**Local Invariants** (hold per service/component):

1. **Resource Limits**: Service doesn't exceed quota
   - **Evidence**: CPU, memory, connection usage
   - **Mode**: Shed load (reject requests) before running out of resources

2. **Rate Limits**: Service doesn't overwhelm dependencies
   - **Evidence**: Requests per second to dependencies
   - **Mode**: Queue requests, apply backpressure

### The Mode Matrix for Planet-Scale Systems

Planet-scale systems have modes at **multiple levels**: global, regional, service.

#### Global Modes

**Target Mode** (Blue Skies):
- **State**: All regions healthy
- **Performance**: p95 latency <100ms globally
- **Availability**: 100% of users served
- **Consistency**: Strong where required, bounded staleness where acceptable
- **Evidence**: All health checks passing, no active incidents
- **Cost**: Optimized (scale down idle resources)

**Degraded Mode** (Storm Clouds):
- **State**: One or more regions impaired (but not down)
- **Performance**: p95 latency <200ms (acceptable, but slower)
- **Availability**: 99%+ users served (some timeouts, retries)
- **Consistency**: Bounded staleness increased (δ=10s → 30s), some strong reads degraded to bounded
- **Evidence**: Regional health checks failing, elevated error rates, increased latency
- **Actions**:
  - Disable non-essential features (recommendations, "trending," analytics)
  - Increase cache TTL (serve staler data)
  - Shed low-priority traffic (rate limit background jobs)
  - Increase alert thresholds (reduce noise, focus on critical issues)
- **Cost**: Higher (run extra capacity to absorb load from impaired regions)

**Floor Mode** (Hurricane):
- **State**: Multiple regions down or majority of capacity lost
- **Performance**: p95 latency <500ms (slow, but functional)
- **Availability**: 90%+ users served (essential services only)
- **Consistency**: Eventual only (strong consistency unavailable)
- **Evidence**: Multiple regions unreachable, cascading failures detected
- **Actions**:
  - Essential services only (authentication, core transactions)
  - Disable all non-essential services (feeds, search, recommendations)
  - Read-only mode (writes queued for later, not processed immediately)
  - Manual intervention (paging on-call, incident commander assigned)
- **Cost**: Maximum (run all available capacity, emergency scaling)

**Recovery Mode** (Clearing):
- **State**: Services returning to normal
- **Performance**: Gradually improving
- **Availability**: Gradually increasing
- **Consistency**: Gradually strengthening (eventual → bounded → strong)
- **Evidence**: Health checks recovering, error rates declining
- **Actions**:
  - Gradually restore features (prioritize most-used)
  - Process queued writes (catch up on deferred work)
  - Ramp traffic slowly (avoid thundering herd)
  - Monitor for secondary failures (overload from catch-up work)
- **Cost**: Elevated (run extra capacity during recovery)

#### Regional Modes

Each region has its own modes. Global mode is determined by the **worst regional mode**.

Example:

- **US-EAST-1**: Target mode (healthy)
- **EU-WEST-1**: Target mode (healthy)
- **AP-SOUTHEAST-1**: Degraded mode (database replica lag, increased latency)
- **Global mode**: Degraded (because one region degraded)

**Actions**:
- Users in AP-SOUTHEAST-1 experience slower responses (served from replicas with lag)
- Users in other regions unaffected
- Alerting: On-call notified of AP-SOUTHEAST-1 degradation

### Operational Patterns

#### Follow-the-Sun Operations

**The problem**: Planet-scale systems require 24/7 monitoring. No individual or team can be on-call 24/7 indefinitely (burnout).

**The solution**: Distribute on-call across time zones.

**Example**:

- **US-WEST team** (California): On-call 8 AM - 4 PM Pacific (covers American business hours)
- **EU-CENTRAL team** (Dublin): On-call 4 PM Pacific - 12 AM Pacific (covers European business hours)
- **ASIA-PACIFIC team** (Singapore): On-call 12 AM Pacific - 8 AM Pacific (covers Asian business hours)

**Handoff protocol**:

```python
class GlobalOncall:
    def __init__(self):
        self.regions = ['US-WEST', 'EU-CENTRAL', 'ASIA-PACIFIC']
        self.current_primary = None

    def handoff(self, from_region, to_region):
        # Overlap period (15-30 minutes)
        overlap_start = time.now()

        # Transfer context
        context = from_region.get_context()
        # Context includes:
        # - Active incidents
        # - Recent changes (deployments, config updates)
        # - Known issues (flaky test, expected elevated error rate)
        # - On-call notes (workarounds, escalation contacts)

        to_region.receive_context(context)

        # Verify readiness
        if not to_region.ready():
            # Incoming team not ready (incident in progress, etc.)
            # Extend shift
            from_region.extend_shift()
            return False

        # Transfer primary on-call role
        self.current_primary = to_region

        # Confirmation
        to_region.acknowledge()
        from_region.handoff_complete()

        return True
```

**Evidence**: Handoff logs, context transfer records, acknowledgment confirmations.

**Why it matters**: Enables continuous coverage without burning out individuals. Humans need sleep. Systems don't.

#### Chaos Engineering

**The problem**: You don't know if your system handles failures until failures happen. Waiting for real failures to test your resilience is risky.

**The solution**: Intentionally inject failures in production to verify resilience.

**Netflix's Chaos Monkey** (the pioneer):

- **Idea**: Randomly terminate instances in production
- **Goal**: Verify that services tolerate instance failures (automatic restart, no user impact)
- **Frequency**: Continuous (during business hours)

**Evolution**:

**Chaos Kong**: Terminate entire regions (simulate datacenter failure).

**Latency Monkey**: Inject artificial latency (simulate slow dependencies).

**Chaos Gorilla**: Simulate Availability Zone failure (multiple servers down).

**Principles**:

1. **Start small**: Kill one instance, verify no user impact, gradually increase scope
2. **Monitor impact**: If user-facing metrics (error rate, latency) affected, stop and fix
3. **Automate**: Chaos runs continuously, not manually
4. **Learn**: Every experiment teaches something (either "we handled this well" or "we need to fix X")

**Example chaos experiment**:

```yaml
# Chaos experiment: Terminate 10% of instances in us-east-1
experiment:
  name: "Instance failure tolerance"
  scope: "us-east-1"
  duration: "1 hour"

  actions:
    - type: "terminate_instances"
      percentage: 10
      services: ["api-server", "web-server"]

  steady_state:
    # What should remain true despite chaos
    - metric: "error_rate"
      threshold: "<1%"
    - metric: "p95_latency"
      threshold: "<200ms"

  abort_conditions:
    # Stop experiment if these are violated
    - metric: "error_rate"
      threshold: ">5%"
    - metric: "p95_latency"
      threshold: ">500ms"
```

**Evidence**: Experiment logs, metric dashboards, user-facing impact (should be zero).

**Why it matters**: Chaos engineering builds confidence. You know your system tolerates failures because you've tested it. This is the difference between "we think we're resilient" and "we've proven we're resilient."

#### Disaster Recovery

**The scenarios**:

1. **Region failure**: Entire datacenter/region offline (power outage, natural disaster, network partition)
2. **Data corruption**: Bug causes data corruption (bad deployment, software bug)
3. **Security breach**: Attacker gains access (requires isolating compromised systems)
4. **Human error**: Operator deletes critical data or config (requires restore)

**Recovery objectives**:

**RTO (Recovery Time Objective)**: How long until system operational again?

- **Critical systems** (payments, authentication): RTO = 5 minutes (automatic failover)
- **Important systems** (feeds, search): RTO = 30 minutes (manual intervention acceptable)
- **Non-critical systems** (analytics, recommendations): RTO = 4 hours (restore from backups)

**RPO (Recovery Point Objective)**: How much data loss is acceptable?

- **Financial transactions**: RPO = 0 (zero data loss, synchronous replication)
- **User-generated content** (posts, photos): RPO = 1 hour (asynchronous replication, may lose last hour)
- **Analytics data**: RPO = 1 day (restore from daily backup)

**Strategies**:

**1. Automatic failover** (for region failures):

```python
def detect_region_failure():
    if region.health_check_failures > 5:
        # Region unreachable, failover
        failover_to_backup_region()

def failover_to_backup_region():
    # Update GeoDNS to route traffic to backup region
    dns.update_region_routing('us-east-1', backup='us-west-2')

    # Promote backup database to primary
    database.promote_replica_to_master('us-west-2')

    # Scale up backup region (handle increased traffic)
    autoscaler.set_min_instances('us-west-2', instances=1000)

    # Alert on-call
    alert("Region us-east-1 failed, failed over to us-west-2")
```

**Evidence**: Health check failures, failover logs, traffic shift metrics.

**2. Point-in-time recovery** (for data corruption):

Databases support PITR (Point-In-Time Recovery). Restore database to a specific timestamp before corruption.

```sql
-- Restore database to 1 hour ago (before bad deployment)
RESTORE DATABASE mydb
FROM BACKUP
TO POINT IN TIME '2024-01-01 10:00:00';
```

**Evidence**: Backup logs, restore logs, data integrity verification.

**3. Immutable infrastructure** (for security breaches):

If a server is compromised, don't try to clean it. Terminate it, provision a new one from a clean image.

```bash
# Terminate compromised instance
aws ec2 terminate-instances --instance-ids i-1234567890abcdef0

# Autoscaler automatically provisions replacement from clean AMI
# No need to manually clean compromised system
```

**Evidence**: Termination logs, new instance provisioning logs.

### Case Studies

#### Google Search: The Always-Available Service

**The challenge**: Google Search must be available 24/7 globally. Even 1 minute of downtime becomes international news.

**The architecture**:

**Index serving**:
- **Global index** sharded across thousands of servers (each server holds a shard of the index)
- **Queries distributed** across shards (scatter-gather pattern)
- **Replication**: Each shard replicated 3+ times (tolerate server failures)

**Query processing**:
```
User query → Frontend (edge) → Query rewrite → Index lookup → Ranking → Results
```

**Frontend**:
- Edge locations (150+ globally)
- User connects to nearest edge
- Edge forwards query to regional datacenter

**Index lookup**:
- Query sent to all shards (scatter)
- Each shard returns top results from its portion of index
- Results merged (gather)
- Total time: <50ms (most shards respond in parallel)

**Ranking**:
- ML models score results (relevance)
- Personalization (based on user history, location)
- Total time: <20ms

**Result caching**:
- Popular queries cached at edge (no need to hit datacenter)
- Cache hit rate: ~30-40% (for very popular queries like "weather")

**Graceful degradation**:

If a shard is unavailable:
- Query still sent to all other shards
- Results merged (missing one shard's results, but still useful)
- User sees slightly fewer results (10 instead of 11, for example)
- No error, no "Google is down"

**Invariants**:
- **Availability**: Respond to every query (even if degraded)
- **Performance**: p95 latency <100ms
- **Relevance**: Top results are high-quality (ML models ensure this)

**Evidence**:
- Shard health checks (heartbeats every second)
- Query latency metrics (p50, p95, p99 per region)
- Cache hit rates (optimize for popular queries)

**Why it works**:
- **Redundancy**: Every component replicated (shards, frontends, caches)
- **Graceful degradation**: Partial failures tolerated (missing one shard still produces useful results)
- **Geographic distribution**: Users hit nearest edge (low latency)

**Statistics**:
- **10 billion queries/day** (115,000 queries/second average, higher during peak hours)
- **<100ms latency** p95 globally
- **99.99%+ availability** (downtime measured in seconds per year, not minutes)

#### Netflix: Chaos Engineering in Production

**The challenge**: Netflix streams video to 200M+ subscribers globally. Must remain available during peak hours (evenings, weekends). Any outage costs revenue and subscriber trust.

**The decision**: Embrace failure. Assume failures will happen. Design system to tolerate failures.

**Chaos Monkey** (introduced 2011):

- Randomly terminates instances in production during business hours
- Goal: Verify that instance failures don't impact streaming (automatic restart, load balancer reroutes traffic)

**Initial resistance**: "You want to intentionally break production?!"

**Response**: "Failures will happen anyway (hardware, software bugs, human errors). Better to test resilience on our schedule than discover fragility during a real outage."

**Results**:

- Discovered services that didn't handle instance failures gracefully (single points of failure)
- Fixed these issues (added redundancy, automatic restart, better error handling)
- Built confidence that system tolerates failures

**Evolution**:

**Simian Army** (expanded Chaos Monkey):

- **Latency Monkey**: Inject artificial latency (simulate slow dependencies)
- **Conformity Monkey**: Terminate instances not following best practices (e.g., missing health checks)
- **Doctor Monkey**: Terminate unhealthy instances (failing health checks)
- **Janitor Monkey**: Clean up unused resources (old instances, unattached volumes)
- **Security Monkey**: Find security vulnerabilities (open ports, expired certificates)
- **10-18 Monkey**: Simulate region failures (international content delivery)

**Chaos Kong** (2015):

- Simulate entire AWS region failure
- Conducted during business hours (intentionally, to test real-world resilience)
- Result: Streaming continued in other regions (users in failed region failed over to nearby region)
- Proved: Netflix can survive region failures without user impact

**Lessons**:

1. **Chaos builds confidence**: You know you're resilient because you've tested it
2. **Automate recovery**: Humans can't react fast enough; automation is required
3. **Degrade gracefully**: Lose some features (personalized recommendations), keep core function (streaming)
4. **Test in production**: Staging environments don't have real traffic, real data, real failures

**Statistics**:
- **1 billion hours/day** streamed globally
- **99.99%+ availability** (measured per region)
- **Regional failover**: Automatic, <5 minutes
- **Chaos experiments**: Continuous (not one-time tests)

#### Amazon Prime Day: Peak Traffic Planning

**The challenge**: Prime Day is Amazon's largest sales event (bigger than Black Friday). Traffic spikes 10-100× normal. Must handle peak load without outages.

**Preparation** (months in advance):

**1. Capacity planning**:
- Historical data: How much did traffic grow last year?
- Forecast: Assume 2× growth this year (conservative)
- Provision: 3× current capacity (buffer for unexpected spikes)

**2. Load testing**:
- Simulate Prime Day traffic in staging environment
- Gradually increase load (1×, 2×, 5×, 10× normal)
- Identify bottlenecks (databases, caches, network)
- Fix bottlenecks, re-test

**3. Game day exercises**:
- Practice incident response (what if database fails during Prime Day?)
- Run through runbooks (ensure every step tested)
- Practice failovers (primary region → backup region)

**4. Code freeze**:
- Two weeks before Prime Day: No new features deployed
- Only critical bug fixes allowed
- Reduce risk of introducing bugs right before peak traffic

**During Prime Day**:

**Autoscaling**:
- Servers automatically added when CPU >70%
- Scaling limits increased (normally max 100 servers, Prime Day max 1000)
- Pre-warming: Spin up servers before traffic arrives (avoid cold start delays)

**Monitoring**:
- All hands on deck (engineers, managers monitoring dashboards)
- War room (incident commanders ready to coordinate response)
- Tiered alerting (minor issues → team lead, major issues → VP)

**Graceful degradation**:
- Non-essential features disabled ("Customers who bought this also bought..." recommendations)
- Serve cached product pages (99% of browsing is top 1000 products)
- Queue checkout requests (if payment system overloaded, queue requests, process in order)

**Results** (Prime Day 2023):
- **375 million items purchased** globally
- **12 billion requests** to Amazon.com
- **Zero major outages** (minor issues, but core shopping experience unaffected)

**Lessons**:
1. **Plan for 3× expected load** (traffic always exceeds expectations)
2. **Test at scale** (load testing must simulate real traffic patterns)
3. **Practice incident response** (game days reveal gaps in runbooks)
4. **Degrade non-essential features** (keep core experience working)

### The Economics of Always-On

#### Cost of Availability

**The rule of nines**: Each additional nine of availability costs exponentially more.

```python
def availability_cost(nines):
    """
    Estimate cost to achieve N nines of availability.
    Based on industry estimates.
    """
    base_cost = 100000  # $100K for 99% availability

    costs = {
        2: base_cost,            # 99%: $100K (single server, basic monitoring)
        3: base_cost * 5,        # 99.9%: $500K (redundant servers, load balancer)
        4: base_cost * 25,       # 99.99%: $2.5M (multi-AZ, automatic failover)
        5: base_cost * 100,      # 99.999%: $10M (multi-region, chaos testing)
        6: base_cost * 500,      # 99.9999%: $50M (global footprint, custom hardware)
    }

    return costs.get(nines, base_cost * (5 ** nines))
```

**Why the exponential cost?**

**99% → 99.9%** (3.5 days/year → 8.7 hours/year):
- Add redundant servers (2× cost)
- Add load balancer (monitoring, failover)
- Total: 5× base cost

**99.9% → 99.99%** (8.7 hours/year → 52 minutes/year):
- Multi-AZ deployment (replicate across datacenters)
- Automatic failover (complex orchestration)
- 24/7 on-call (human cost)
- Total: 5× previous cost = 25× base cost

**99.99% → 99.999%** (52 minutes/year → 5 minutes/year):
- Multi-region deployment (global presence)
- Chaos engineering (dedicated team)
- Advanced monitoring (predict failures before they happen)
- Total: 4× previous cost = 100× base cost

**Trade-off**: Is the cost worth it?

**High-value services** (payments, trading):
- 1 minute down = $1M lost revenue
- 99.999% availability = $10M/year cost
- ROI: Prevents $50M+ in potential losses
- **Decision**: Worth it.

**Low-value services** (recommendation engine):
- 1 hour down = $10K lost revenue
- 99.99% availability = $2.5M/year cost
- ROI: Prevents <$100K in potential losses
- **Decision**: Not worth it. Accept lower availability, save cost.

#### Cost of Downtime

**Calculation**:

```python
def downtime_cost(revenue_per_minute, minutes_down, reputation_factor):
    """
    Calculate total cost of downtime.

    revenue_per_minute: Direct revenue lost
    minutes_down: Duration of outage
    reputation_factor: Multiplier for reputation damage (2-10×)
    """
    direct_loss = revenue_per_minute * minutes_down

    # Reputation loss (customers lost, brand damage)
    reputation_loss = direct_loss * reputation_factor

    # Engineering cost (time spent responding, fixing)
    engineering_cost = minutes_down * 1000  # $1000/minute (team of engineers)

    # Total cost
    total = direct_loss + reputation_loss + engineering_cost

    return total

# Example: E-commerce site, Black Friday
cost = downtime_cost(
    revenue_per_minute=50000,  # $50K/minute
    minutes_down=30,           # 30-minute outage
    reputation_factor=5        # 5× multiplier (Black Friday, customers switch to competitors)
)
# Direct loss: $50K × 30 = $1.5M
# Reputation loss: $1.5M × 5 = $7.5M
# Engineering: $1000 × 30 = $30K
# Total: $9.03M for 30 minutes
```

**Real examples**:

**Facebook outage (October 2021)**: 6 hours down
- Direct loss: $100M (ad revenue)
- Reputation: $40B market cap decline (stock price drop)
- Total: $40B+ (most due to reputation)

**Amazon Prime Day outage (2018)**: 1 hour down
- Direct loss: $100M (sales)
- Reputation: Unknown (but customers remembered)
- Total: $100M+ for 1 hour

**Stripe outage (2019)**: 2 hours degraded service
- Direct loss: Stripe didn't lose revenue (customers did)
- Reputation: Customers questioned reliability
- Total: Immeasurable (but many customers added backup payment providers)

#### Resource Optimization

**The goal**: Minimize cost while maintaining availability and performance.

**Strategies**:

**1. Right-sizing**:

- Most services over-provisioned (run at 20% CPU, could run at 60%)
- Right-size: Use smaller instances, pack more services per instance
- Savings: 50-70% (3× too large → right-sized)

**2. Autoscaling**:

- Scale up during peak hours (evenings, weekends)
- Scale down during off-peak hours (late night, weekdays)
- Savings: 30-50% (run fewer instances when traffic low)

**3. Reserved capacity**:

- Purchase reserved instances (commit to 1-3 years)
- Discount: 30-60% vs on-demand pricing
- Trade-off: Less flexibility (can't change instance type easily)

**4. Spot instances**:

- Use spare cloud capacity (AWS Spot, GCP Preemptible)
- Discount: 70-90% vs on-demand
- Trade-off: Instances can be terminated with 2 minutes notice
- Use case: Batch processing, fault-tolerant workloads

**5. Multi-cloud**:

- Use cheapest provider for each service
- AWS for compute, GCP for ML, Azure for Windows workloads
- Savings: 10-30% (competition drives prices down)
- Trade-off: Complexity (multiple platforms to manage)

**Evidence**: Cost metrics (dollars per request, dollars per user, dollars per GB transferred).

### Building Your Own Planet-Scale System

You probably won't build Google or Amazon. But you can apply planet-scale principles at any scale.

#### Design Principles

**1. Design for failure**

**Assumption**: Everything fails eventually (hardware, network, software, humans).

**Practice**:
- Redundancy: No single points of failure
- Timeouts: Every network call has a timeout (don't wait forever)
- Retries: Transient failures retried (with exponential backoff)
- Circuit breakers: Failing dependencies isolated (fail fast, don't cascade)
- Graceful degradation: Non-essential features disabled before core fails

**2. Automate everything**

**Assumption**: Humans are slow, error-prone, and need sleep.

**Practice**:
- Autoscaling: Automatically add/remove capacity
- Self-healing: Automatically restart failed services
- Automatic failover: Automatically switch to backup when primary fails
- Automatic rollback: Automatically revert bad deployments
- Chaos engineering: Automatically inject failures (test resilience)

**3. Measure everything**

**Assumption**: You can't improve what you don't measure.

**Practice**:
- Metrics: Latency, error rate, throughput (per service, per region)
- Logs: Structured, searchable, retained
- Traces: Distributed (follow requests across services)
- Alerts: Evidence-based (invariant violations, not arbitrary thresholds)
- Dashboards: Real-time visibility (for humans to understand system state)

**4. Cache aggressively**

**Assumption**: Computation is expensive, memory is cheap.

**Practice**:
- Edge caching: Serve static content from nearest edge
- Application caching: Cache database queries (Redis, Memcached)
- Database caching: Cache query results (query cache, result cache)
- DNS caching: Cache DNS lookups (reduce latency)
- CDN: Cache entire pages (Cloudflare, Fastly)

**5. Shard thoughtfully**

**Assumption**: Single servers don't scale infinitely.

**Practice**:
- Horizontal partitioning: Split data by key (user ID, tenant ID)
- Vertical partitioning: Split data by column (hot columns separate from cold)
- Functional partitioning: Split by function (users, orders, inventory separate)
- Time-based partitioning: Split by time (today's data separate from historical)

**6. Replicate globally**

**Assumption**: Data should be close to users.

**Practice**:
- Multi-region deployment: Deploy to multiple continents
- Active-active: All regions accept writes (harder, but lower latency)
- Active-passive: One region primary (writes), others backup (reads)
- Conflict resolution: Handle concurrent writes (last-write-wins, CRDTs, application merge)

**7. Degrade gracefully**

**Assumption**: Partial service is better than no service.

**Practice**:
- Essential vs non-essential: Identify core features vs nice-to-have
- Progressive degradation: Disable features in priority order
- Explicit modes: Target, Degraded, Floor, Recovery
- User communication: Tell users when degraded ("Some features temporarily unavailable")

**8. Version everything**

**Assumption**: Every change has risk.

**Practice**:
- API versioning: Old clients continue working (backward compatibility)
- Data versioning: Schema changes don't break old code
- Config versioning: Track config changes (rollback if bad)
- Infrastructure as code: Version control for infrastructure (Git for Terraform)

**9. Test constantly**

**Assumption**: Confidence comes from evidence, not belief.

**Practice**:
- Unit tests: Test individual functions
- Integration tests: Test service interactions
- Load tests: Test at scale (simulate peak traffic)
- Chaos tests: Test resilience (inject failures)
- Game days: Test incident response (practice makes perfect)

**10. Document religiously**

**Assumption**: Knowledge must transfer (people leave, new people join).

**Practice**:
- Runbooks: Step-by-step guides (how to handle common incidents)
- Architecture diagrams: Visual system overview
- API documentation: How to use each service
- Post-mortems: Learn from incidents (blameless, focus on system improvement)
- Decision logs: Why we made architectural choices (context for future)

#### Architecture Patterns

**Multi-region active-active**:

```yaml
Regions:
  US-East:
    Primary: true
    Services: [API, Database, Cache, Queue]
    Backup: EU-West
    Traffic: 40%  # GeoDNS routes US users here

  EU-West:
    Primary: true
    Services: [API, Database, Cache, Queue]
    Backup: US-East
    Traffic: 30%  # GeoDNS routes EU users here

  Asia-Pacific:
    Primary: true
    Services: [API, Database, Cache, Queue]
    Backup: US-West
    Traffic: 30%  # GeoDNS routes Asian users here

Traffic_Routing:
  GeoDNS: true              # Route by user location
  Latency-based: true       # Route to lowest latency region
  Failover: automatic       # If region down, route to backup
  Health_check: 10s         # Check region health every 10s

Data_Replication:
  Strategy: multi-master    # All regions accept writes
  Consistency: eventual     # Writes propagate asynchronously
  Conflict: last-write-wins # Timestamp-based conflict resolution
  Lag: <1s                  # Target replication lag <1 second

Failover:
  Detection: health checks + error rate
  Trigger: 3 consecutive failures OR error rate >10%
  Action: Update GeoDNS to route to backup region
  Recovery: Automatic when health checks pass
```

**Invariants**:
- **Availability**: System serves users even if one region fails
- **Performance**: Users routed to nearest region (low latency)
- **Consistency**: Eventual (acceptable for most use cases)

**Evidence**:
- Regional health checks (heartbeats, error rates)
- Replication lag (seconds behind primary)
- Failover logs (when, why, outcome)

### Monitoring at Scale

#### The Four Golden Signals (Google SRE)

**1. Latency**: Time to serve requests

**Metrics**:
- p50 (median), p95, p99, p99.9
- Separate read latency vs write latency
- Per region, per service

**Alert**: p99 latency >200ms for 5 minutes

**2. Traffic**: Requests per second

**Metrics**:
- Total requests/sec
- Read requests/sec vs write requests/sec
- Per region, per service

**Alert**: Traffic drops >50% (may indicate outage, not traffic change)

**3. Errors**: Failed requests per second

**Metrics**:
- HTTP 5xx errors (server errors)
- HTTP 4xx errors (client errors, less critical)
- Error rate (errors / total requests)
- Per region, per service

**Alert**: Error rate >1% for 5 minutes

**4. Saturation**: Resource utilization

**Metrics**:
- CPU utilization (per instance, per region)
- Memory utilization
- Disk I/O utilization
- Network bandwidth utilization

**Alert**: CPU >80% for 10 minutes (autoscale trigger)

#### Observability Stack

**Metrics** (time-series data):
- **Collection**: Prometheus (open-source), CloudWatch (AWS), Stackdriver (GCP)
- **Storage**: Time-series database (Prometheus TSDB, InfluxDB)
- **Visualization**: Grafana (dashboards)
- **Alerting**: Prometheus Alertmanager, PagerDuty

**Logs** (events):
- **Collection**: Fluentd, Logstash (ship logs to central system)
- **Storage**: Elasticsearch (searchable log storage)
- **Visualization**: Kibana (log search, analysis)
- **Retention**: 30-90 days (balance cost vs value)

**Traces** (distributed request tracking):
- **Instrumentation**: OpenTelemetry (generate trace spans)
- **Collection**: Jaeger, Zipkin (trace collectors)
- **Storage**: Cassandra, Elasticsearch (trace storage)
- **Visualization**: Jaeger UI, Zipkin UI (trace analysis)

**Events** (state changes):
- **Collection**: Custom event bus (Kafka, Kinesis)
- **Storage**: Event store (append-only log)
- **Visualization**: Custom dashboards (Grafana, Kibana)

**Example**:

User request generates:
- **Metrics**: Latency (50ms), status (200 OK)
- **Logs**: API gateway log, service logs, database logs
- **Trace**: Request trace across 5 services (10 spans)
- **Events**: "Order created" event published to Kafka

#### Alert Fatigue Management

**The problem**: Too many alerts → engineers ignore them → real incidents missed.

**Solutions**:

**1. Alert quality scoring**:

```python
def alert_quality_score(alert_history):
    """
    Score alerts by usefulness.
    High score = actionable, low score = noise.
    """
    total_alerts = len(alert_history)
    actionable = sum(1 for a in alert_history if a.action_taken)
    false_positives = sum(1 for a in alert_history if a.false_positive)

    score = actionable / total_alerts - (false_positives / total_alerts)
    return score

# Review alerts quarterly
# Disable alerts with score <0.3 (more noise than signal)
```

**2. Deduplication**:

Same issue generates multiple alerts (CPU high, latency high, error rate high). Deduplicate into one alert.

**3. Correlation**:

Related alerts grouped (all services in region X failing → "Region X down").

**4. Suppression**:

During known maintenance windows, suppress non-critical alerts.

**5. Escalation**:

- **P0** (critical): Page on-call immediately, escalate to manager if not resolved in 15 minutes
- **P1** (important): Alert on-call, escalate if not resolved in 1 hour
- **P2** (minor): Email team, resolve during business hours
- **P3** (informational): Log, no immediate action

**Evidence**: Alert quality metrics (false positive rate, action taken rate, time to resolve).

### The Human Factor

#### Building Global Teams

**The challenge**: Planet-scale systems require 24/7 operation. Teams must span time zones.

**Structure**:

- **Site Reliability Engineers** (SREs): Operate systems, on-call rotation
- **Software Engineers**: Build features, fix bugs
- **Data Engineers**: Build data pipelines, analytics
- **Security Engineers**: Protect systems, respond to threats
- **Manager**: Coordinate, prioritize, support team

**Distribution**:

- **US team**: California (product focus, most engineers)
- **EU team**: Dublin, London (follow-the-sun on-call, regional compliance)
- **APAC team**: Singapore, Tokyo (follow-the-sun on-call, regional growth)

**Communication**:

- **Async-first**: Most communication via docs, Slack (not meetings)
- **Overlap hours**: Core hours (e.g., 10 AM-2 PM Pacific) when all teams available
- **Video calls**: Weekly all-hands, daily standups (optional)
- **Documentation**: Everything written down (decisions, runbooks, architecture)

**Runbook standards**:

```markdown
# Runbook: High Database Replica Lag

## Symptoms
- Alert: "Replica lag >30s in region X"
- Dashboard: Replication lag graph spiking

## Impact
- Reads from replica return stale data
- Users may see outdated information

## Diagnosis
1. Check replication lag: `SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))`
2. Check primary database load: CPU, I/O
3. Check network between primary and replica

## Resolution

### Option 1: Wait (if lag <60s and decreasing)
- Monitor for 5 minutes
- If lag decreasing, self-resolves

### Option 2: Failover reads to another region (if lag >60s or increasing)
- Execute: `kubectl annotate region X read-failover=Y`
- Monitor latency impact (may increase 50-100ms)

### Option 3: Promote replica to primary (if primary unhealthy)
- **DO NOT** do this without consulting senior engineer
- Risk: Split-brain if primary recovers

## Escalation
- If lag >300s (5 minutes): Page database team
- If multiple regions affected: Page incident commander

## Post-incident
- Update: https://wiki/postmortems/YYYY-MM-DD-replica-lag
- Action items: Investigate root cause, prevent recurrence
```

**Evidence**: Runbook usage logs (which runbooks used, outcomes).

#### Incident Management

**Incident lifecycle**:

```python
class IncidentResponse:
    def __init__(self):
        self.phases = [
            'Detection',      # Alert fires
            'Triage',         # Assess severity, impact
            'Diagnosis',      # Find root cause
            'Mitigation',     # Stop the bleeding
            'Resolution',     # Fix root cause
            'Post-mortem'     # Learn, prevent recurrence
        ]

    def respond(self, incident):
        # 1. Detection (automatic)
        severity = self.classify_severity(incident)
        # P0: Critical (user-facing outage)
        # P1: Important (degraded, but functional)
        # P2: Minor (isolated issue)

        # 2. Triage (automatic + human)
        responders = self.get_responders(severity)
        # P0: Page on-call + incident commander
        # P1: Alert on-call
        # P2: Email team

        # 3. Communication (automatic)
        self.create_war_room(incident, responders)
        # Slack channel: #incident-2024-01-01-database-lag
        # Video call: For P0 incidents
        # Status page: Update external status page

        # 4. Timeline (automatic)
        self.start_timeline(incident)
        # Log every action, decision, observation
        # Timestamps: When did we first detect? When did we mitigate?

        # 5. Mitigation (human, aided by runbook)
        self.execute_runbook(incident.type)
        # Follow runbook steps
        # Log actions taken, outcomes

        # 6. Metrics (automatic)
        self.track_response_metrics(incident)
        # Time to detect, time to mitigate, time to resolve
        # User impact (error rate, affected users)
```

**Post-mortem template**:

```markdown
# Post-Mortem: Database Replica Lag (2024-01-01)

## Summary
On 2024-01-01 at 03:15 UTC, database replicas in US-EAST-1 experienced high replication lag (up to 300s). Reads from replicas returned stale data. Mitigated by failing over reads to US-WEST-2. Resolved when replica caught up at 04:30 UTC.

## Timeline
- 03:15 UTC: Alert fired (replica lag >30s)
- 03:18 UTC: On-call engineer acknowledged
- 03:20 UTC: Diagnosed root cause (vacuum process consuming I/O)
- 03:25 UTC: Executed failover to US-WEST-2
- 03:30 UTC: Mitigation complete (reads from US-WEST-2)
- 04:30 UTC: Replica caught up, failover reverted
- 04:35 UTC: Incident closed

## Impact
- Duration: 1 hour 15 minutes (detection to resolution)
- Users affected: 15% (US East Coast users)
- Impact: Stale reads (users saw outdated data, no data loss)
- Revenue: Negligible (browsing not affected, checkouts slightly delayed)

## Root Cause
Database vacuum process (nightly maintenance) consumed I/O bandwidth, starving replication stream. Vacuum not configured to yield to replication.

## Resolution
1. Immediate: Failed over reads to US-WEST-2 (mitigated stale reads)
2. Short-term: Tuned vacuum schedule (run during lower traffic hours)
3. Long-term: Increase I/O priority for replication, monitor vacuum I/O impact

## Lessons Learned
- **What went well**: Runbook clear, failover executed smoothly, automatic recovery worked
- **What didn't**: Alert threshold too low (30s lag normal during vacuum), should be 60s
- **Action items**:
  - [ ] Adjust alert threshold (30s → 60s)
  - [ ] Tune vacuum I/O priority (yield to replication)
  - [ ] Add predictive lag monitoring (alert on trend, not threshold)
  - [ ] Document vacuum schedule in runbook

## Action Items
| Item | Owner | Due Date | Status |
|------|-------|----------|--------|
| Adjust alert threshold | Alice | 2024-01-08 | Done |
| Tune vacuum priority | Bob | 2024-01-15 | In Progress |
| Add predictive monitoring | Charlie | 2024-01-31 | Not Started |
```

**Evidence**: Post-mortem document, action items tracked, completion verified.

**Blameless culture**: Focus on system improvement, not blaming individuals. Humans make mistakes. Systems should tolerate human mistakes.

---

## Synthesis: The Nature of Planet-Scale

### The Fundamental Challenges

**1. Physics**: Speed of light limits communication

- **Constraint**: Light travels 300,000 km/s. Fiber optic slower (refractive index). New York to Tokyo: 220ms round-trip (unavoidable).
- **Implication**: Global strong consistency requires >200ms latency (coordination across continents).
- **Response**: Trade consistency for latency (eventual, bounded staleness), or accept high latency (Spanner).

**2. Complexity**: Exponential interaction growth

- **Constraint**: N services → N² potential interactions. 10 services: 100 interactions. 100 services: 10,000 interactions.
- **Implication**: Reasoning about system behavior becomes impossible (too many interactions to understand).
- **Response**: Isolate interactions (service mesh, circuit breakers), explicit contracts (API versioning, SLAs).

**3. Economics**: Marginal cost pressures

- **Constraint**: At billions of requests, $0.01 savings per request = $10M+ savings annually.
- **Implication**: Efficiency optimization never stops (every millisecond, every byte, every CPU cycle matters).
- **Response**: Continuous optimization (caching, compression, efficient algorithms), economic trade-offs (cost vs latency vs consistency).

**4. Regulations**: Jurisdictional requirements

- **Constraint**: GDPR (EU data in EU), data residency laws (China, Russia), privacy regulations (CCPA, HIPAA).
- **Implication**: Data cannot freely move globally (must respect regional boundaries).
- **Response**: Regional data storage, cross-region replication with compliance, data sovereignty guarantees.

**5. Security**: Attack surface expansion

- **Constraint**: More servers, more regions, more services = more attack vectors.
- **Implication**: Security cannot be an afterthought (must be designed in from the start).
- **Response**: Defense in depth (encryption, authentication, authorization at every boundary), continuous monitoring, incident response.

### The Invariant Perspective

Planet-scale systems maintain invariants through:

**1. Redundancy**: Multiple everything

- No single point of failure
- Data replicated across regions
- Services replicated across instances
- Networks multi-homed (multiple ISP connections)

**Evidence**: Health checks, failover logs, replication lag metrics.

**2. Isolation**: Failure containment

- Regions isolated (failures don't cascade)
- Services isolated (circuit breakers)
- Tenants isolated (resource quotas)
- Blast radius limited (failures affect minimum scope)

**Evidence**: Failure domain boundaries, impact analysis (% users affected).

**3. Automation**: Human-speed isn't enough

- Autoscaling (add/remove capacity)
- Self-healing (restart failed services)
- Automatic failover (switch to backup)
- Automatic rollback (revert bad deployments)
- Chaos engineering (continuous resilience testing)

**Evidence**: Automation logs, success rates, time to recovery.

**4. Verification**: Continuous testing

- Unit tests (individual functions)
- Integration tests (service interactions)
- Load tests (scale simulation)
- Chaos tests (failure injection)
- Canary deployments (gradual rollout with automatic rollback)

**Evidence**: Test results, code coverage, deployment success rates.

**5. Evolution**: Constant improvement

- Post-mortems (learn from incidents)
- Metrics (measure everything)
- Experimentation (A/B tests, feature flags)
- Refactoring (improve code quality)
- Capacity planning (predict future needs)

**Evidence**: Improvement metrics (time to recovery decreasing, availability increasing), post-mortem action items completed.

### Design Philosophy Evolution

**From**: Preventing all failures
**To**: Embracing failure as normal

- Failures will happen (hardware, software, network, human)
- Design systems that tolerate failures (graceful degradation)
- Test resilience continuously (chaos engineering)

**From**: Manual operation
**To**: Autonomous systems

- Humans cannot react fast enough (incidents happen at 3 AM)
- Automate common tasks (scaling, failover, recovery)
- Humans handle exceptional cases only (complex incidents, strategic decisions)

**From**: Regional thinking
**To**: Global first

- Users are global (not confined to one region)
- Data should be close to users (low latency)
- Design multi-region from the start (not retrofit later)

**From**: Cost as constraint
**To**: Cost as feature

- Efficiency enables scale (better algorithms, better utilization)
- Cost optimization continuous (not one-time)
- Economic trade-offs explicit (latency vs cost, consistency vs cost)

### Future Directions

**1. Edge computing proliferation**

- Compute moving closer to users (not just in datacenters)
- Cloudflare Workers, Lambda@Edge, CDN compute
- Ultra-low latency (<10ms globally)
- Privacy (data processed locally, not sent to datacenter)

**2. 5G network integration**

- Higher bandwidth (gigabit speeds on mobile)
- Lower latency (<10ms mobile network latency)
- New use cases (AR/VR, autonomous vehicles, IoT)

**3. Quantum networking** (future)

- Quantum entanglement (instant communication, theoretically)
- Quantum key distribution (unbreakable encryption)
- Quantum sensors (ultra-precise time synchronization)

**4. Space-based infrastructure**

- Starlink, OneWeb (global satellite internet)
- Low-Earth orbit (LEO) satellites (lower latency than geostationary)
- Global coverage (rural areas, oceans, remote regions)

**5. AI-driven operations**

- Anomaly detection (ML models predict failures)
- Automatic remediation (AI decides mitigation strategy)
- Capacity planning (AI forecasts demand)
- Incident response (AI suggests runbook steps)

---

## Key Takeaways

**1. Planet-scale requires fundamental rethinking**

Small-scale intuitions don't apply. Manual operation impossible. Automation survival.

**2. Automation is not optional**

Humans are too slow, need sleep, make mistakes. Systems must self-heal, self-scale, self-protect.

**3. Failure is normal, plan for it**

Every component will fail eventually (hardware, software, network). Design systems that tolerate failures gracefully.

**4. Human factors matter as much as technical**

Best technology useless if operators can't understand it. Runbooks, observability, blameless culture critical.

**5. Cost optimization is continuous**

At billions of requests, tiny improvements compound. Efficiency never "done."

**6. Monitoring is existential**

You cannot operate what you cannot observe. Metrics, logs, traces, alerts are the evidence infrastructure.

**7. Evidence-based operation**

Every decision (scale, degrade, fail over) based on metrics, not intuition. Alerts map to invariant violations.

**8. The scale creates new physics**

Latency becomes unavoidable (speed of light). Coordination becomes expensive (cross-region). Eventual consistency becomes necessary.

**9. Invariants preserved through modes**

Systems have explicit modes (target, degraded, floor, recovery) with known guarantees in each mode.

**10. Global teams, follow-the-sun**

No individual operates 24/7. Teams distributed across time zones. Handoffs smooth, context transferred.

---

## Further Reading

### Books

**Site Reliability Engineering** (Google, 2016)
- The bible of operating planet-scale systems
- Google's practices: SLOs, error budgets, toil reduction, monitoring
- Free online: https://sre.google/sre-book/table-of-contents/

**The Site Reliability Workbook** (Google, 2018)
- Practical companion to SRE book
- Hands-on examples, case studies
- Free online: https://sre.google/workbook/table-of-contents/

**Building Secure and Reliable Systems** (Google, 2020)
- Security and reliability together (not separate concerns)
- Design patterns, frameworks
- Free online: https://sre.google/books/building-secure-reliable-systems/

**Designing Data-Intensive Applications** (Martin Kleppmann, 2017)
- Foundations of distributed data systems
- Deep dive into storage, replication, consistency

### Blogs

**High Scalability** (http://highscalability.com)
- Case studies of planet-scale architectures
- "How X scaled to Y users" series

**AWS Architecture Blog** (https://aws.amazon.com/blogs/architecture/)
- Best practices for AWS
- Reference architectures, case studies

**Google Cloud Blog** (https://cloud.google.com/blog)
- Deep dives into Google infrastructure
- Spanner, Borg, TrueTime explanations

**Netflix Tech Blog** (https://netflixtechblog.com)
- Chaos engineering, microservices at scale
- Real-world production stories

**Meta Engineering Blog** (https://engineering.fb.com)
- Social scale challenges
- TAO, Haystack, Presto deep dives

**The Morning Paper** (https://blog.acolyer.org)
- Academic papers explained
- Distributed systems research

### Papers

**MapReduce** (Google, 2004)
- Simplified large-scale data processing
- Influenced Hadoop, Spark

**Bigtable** (Google, 2006)
- Distributed storage system
- Influenced HBase, Cassandra

**Dynamo** (Amazon, 2007)
- Highly available key-value store
- Influenced DynamoDB, Cassandra, Riak

**Spanner** (Google, 2012)
- Globally distributed database with strong consistency
- TrueTime innovation

**TAO** (Facebook, 2013)
- Social graph at scale
- Read-heavy workload optimization

**Borg** (Google, 2015)
- Large-scale cluster management
- Influenced Kubernetes

### Courses

**Distributed Systems** (MIT 6.824)
- Graduate-level distributed systems
- Lectures, labs (build your own Raft, MapReduce, KV store)
- Free online: https://pdos.csail.mit.edu/6.824/

**Cloud Computing** (Berkeley CS294)
- Cloud infrastructure, economics, applications
- Lectures online

### Tools to Explore

**Kubernetes**: Container orchestration (based on Google's Borg)
**Prometheus**: Metrics and monitoring
**Grafana**: Dashboards and visualization
**Jaeger/Zipkin**: Distributed tracing
**Terraform**: Infrastructure as code
**Chaos Toolkit**: Chaos engineering experiments

---

**The journey to planet-scale is a journey of evidence, invariants, and automation. Every decision must be explicit. Every failure must be expected. Every human must be supported. This is the discipline of operating at the scale of civilization.**
