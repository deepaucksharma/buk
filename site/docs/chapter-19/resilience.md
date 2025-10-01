# Resilience Engineering: Adapting to the Unexpected

## Beyond Robustness: When Design Envelopes Break

On December 28, 2020, Google experienced a global outage that took down Gmail, YouTube, Drive, and most Google services. The root cause? An internal storage quota system ran out of space. But not disk space - metadata space. A 6-year-old quota system had a limit that engineers forgot about. When it filled up, authentication failed globally.

Here's what makes this a resilience failure, not a robustness failure:

**Robustness thinking**: "We designed for 1 million users, we have 2 million capacity, we're robust."

**Resilience thinking**: "What happens when our design assumptions break? When we hit limits we didn't know existed?"

The Google outage happened because the system was robust (worked perfectly within design envelope) but not resilient (couldn't adapt when the envelope was exceeded). The failure was a **surprise** - a quota limit forgotten over 6 years. Robustness doesn't handle surprises. Resilience does.

This chapter explores **resilience engineering** - the discipline of designing systems that adapt to unexpected conditions, extend performance beyond design envelopes, and gracefully degrade rather than catastrophically fail. This is the frontier of distributed systems engineering: not just preventing known failures, but adapting to unknown unknowns.

## Resilience vs Robustness: The Fundamental Distinction

### Robustness: Strength Within Design Envelope

**Definition**: Ability to maintain performance within specified design conditions.

```
Robust System Characteristics:
  1. Designed for known failure modes
  2. Fixed capacity, predetermined responses
  3. Works perfectly within envelope
  4. Fails catastrophically outside envelope
  5. Brittle to surprises

Example: Fixed-size thread pool
  Design: 100 threads
  Within envelope (≤ 100 concurrent requests):
    ✓ All requests served
    ✓ Predictable performance

  Outside envelope (> 100 concurrent requests):
    ✗ Requests queued indefinitely
    ✗ Eventually: OOM crash
    ✗ Cliff failure (100% → 0% capacity)

Robustness Guarantee:
  IF (conditions ∈ design_envelope)
  THEN (system performs as specified)
  ELSE (no guarantees, likely failure)
```

### Resilience: Adaptation Beyond Design Envelope

**Definition**: Ability to adapt and continue providing value when conditions exceed design envelope.

```
Resilient System Characteristics:
  1. Anticipates surprises (unknown unknowns)
  2. Adaptive capacity, emergent responses
  3. Degrades gracefully outside envelope
  4. Continues to provide value under stress
  5. Flexible to surprises

Example: Adaptive thread pool with load shedding
  Design: 100 threads, load shedding above capacity
  Within envelope (≤ 100 concurrent requests):
    ✓ All requests served
    ✓ Predictable performance

  Beyond envelope (> 100 concurrent requests):
    ✓ High-priority requests served (70% capacity)
    ✓ Low-priority requests shed (30% rejected)
    ✓ No crash (bounded resources)
    ✓ Graceful degradation (100% → 70% capacity)

Resilience Guarantee:
  IF (conditions ∈ design_envelope)
  THEN (system performs as specified)
  ELSE (system adapts, degrades gracefully, maintains core value)
```

### Performance Comparison Under Stress

```
Performance vs Stress Graph:

Performance
    │
100%├──────────┐                 ╱────────────
    │          │                ╱   Resilient
    │          │               ╱    (Graceful
    │  Robust  │              ╱     Degradation)
 80%│          │             ╱
    │          │            ╱
    │          │           ╱
 60%├──────────┤          ╱
    │          │         ╱
    │          │        ╱
    │          │       ╱
 40%├──────────┤      ╱
    │          │     ╱
    │          │    ╱
 20%├──────────┤   ╱
    │          │  ╱
    │          │ ╱
  0%├──────────┴─╱────────╲
    │             ↓         ╲
    │          Cliff        ╲  Brittle
    │          Failure      ╲  (Sudden
    │                        ╲  Collapse)
    └────┬─────────┬──────────┬──────────┬─────→
      Normal   Design     Surprise   Extreme  Stress
      Range    Limit      Event      Event    Level

Key Observations:
  1. Robust: Perfect within design range, collapses outside
  2. Resilient: Good within design range, degrades outside
  3. Brittle: Works until sudden collapse (no warning)

Design Goal: Resilience > Robustness > Brittleness
```

### The Resilience-Robustness Trade-off

```
Trade-off Dimensions:

Robustness Optimization:
  ✓ Maximize performance within design envelope
  ✓ Simpler implementation (fixed responses)
  ✓ Lower overhead (no adaptation mechanisms)
  ✗ Brittle to surprises
  ✗ Catastrophic failures outside envelope

Resilience Optimization:
  ✓ Graceful degradation outside design envelope
  ✓ Adapts to unforeseen conditions
  ✓ Maintains core value under stress
  ✗ More complex implementation (adaptive logic)
  ✗ Higher overhead (monitoring, adaptation)
  ✗ Slightly lower peak performance (resources for adaptation)

Sweet Spot:
  Robust for common cases (optimize happy path)
  + Resilient for edge cases (graceful degradation)

Example:
  HTTP server with fixed thread pool (robust)
  + Adaptive timeout (resilient)
  + Load shedding (resilient)
  + Circuit breakers (resilient)
  = High performance normally, graceful degradation under stress
```

## Graceful Extensibility: The Core of Resilience

**Graceful Extensibility** (David Woods): "The ability to extend adaptive capacity into surprise events that challenge the boundaries of the design envelope."

### The Design Envelope

```
System Design Envelope:

  ┌─────────────────────────────────────────┐
  │         DESIGN ENVELOPE                 │
  │                                         │
  │  Known Conditions:                      │
  │    - Load: 1000-5000 req/s             │
  │    - Latency: P99 < 100ms              │
  │    - Error rate: < 0.1%                │
  │    - Node failures: 1-2 per day        │
  │                                         │
  │  System Guarantees:                     │
  │    - Availability: 99.9%                │
  │    - Throughput: 5000 req/s            │
  │    - Consistency: Linearizable          │
  │                                         │
  └─────────────────────────────────────────┘
       │                              │
       │  Surprise Events             │
       ↓  (Outside Envelope)          ↓

  - 10× traffic spike (50,000 req/s)
  - Network partition (regional failure)
  - Cascading failure (all dependencies down)
  - DDoS attack (malicious traffic)
  - Data corruption (silent bit flips)
  - Configuration error (wrong deploy)

Question: What happens when reality exceeds design?

Robust System: Collapses (design violated, no guarantees)
Resilient System: Adapts (extends capacity, degrades gracefully)
```

### Extending the Envelope

```
Graceful Extensibility Strategies:

1. Monitoring Boundary Conditions
   Detect when approaching design limits

   Signals:
     - Latency increasing (P99 approaching timeout)
     - Error rate increasing (approaching threshold)
     - Resource utilization increasing (CPU > 70%)
     - Queue depth increasing (approaching capacity)

   Action: Early warning (before hitting limits)

2. Adaptive Response Mechanisms
   Change behavior based on current conditions

   Examples:
     - Adaptive timeouts (adjust based on P99)
     - Dynamic resource allocation (autoscaling)
     - Request prioritization (shed low-priority)
     - Graceful degradation (disable non-essential features)

   Action: Extend capacity beyond design

3. Graceful Degradation Levels
   Predetermined hierarchy of service levels

   Level 0 (Full Service): All features, all users
   Level 1 (Core Service): Essential features, all users
   Level 2 (Critical Service): Essential features, priority users
   Level 3 (Read-Only): Read traffic only, writes blocked
   Level 4 (Static Fallback): Cached content, no backend

   Action: Maintain value at every level

4. Feedback and Learning
   Update design envelope based on surprises encountered

   Process:
     - Detect surprise (conditions outside envelope)
     - Respond with adaptation (extend capacity)
     - Learn from incident (update envelope)
     - Evolve system (add resilience mechanisms)

   Action: Continuous improvement
```

### Example: Netflix - Graceful Extensibility in Practice

```
Design Envelope (Original):
  - Handle regional AWS outage (fail to another region)
  - Load: Normal traffic patterns (evening peaks)
  - Dependencies: Assume microservices mostly healthy

Surprise Events Encountered:
  1. AWS S3 outage (2017): S3 down → many services broke
  2. Black Friday traffic (annual): 10× spike
  3. New content release: Sudden 50× spike on specific titles
  4. DDoS attack: Malicious traffic overwhelming systems

Graceful Extensibility Responses:

Event 1 (S3 Outage):
  Robust response: System down (S3 is dependency)
  Resilient response:
    - Fallback to cached metadata
    - Disable non-essential features (recommendations)
    - Serve core content (video playback continues)

  Result: Degraded service (90% functionality) vs total outage

Event 2 (Black Friday):
  Robust response: Overload, timeouts, crashes
  Resilient response:
    - Autoscaling (10× capacity)
    - Admission control (rate limiting)
    - Static content served from CDN (reduce backend load)

  Result: Handle 10× load gracefully

Event 3 (Content Release):
  Robust response: Hot shard overload (partition key: title_id)
  Resilient response:
    - Detect hot key (monitor per-key traffic)
    - Shard hot key (title_id_v1, title_id_v2, ...)
    - Distribute across multiple shards

  Result: Maintain performance despite skew

Event 4 (DDoS):
  Robust response: Overwhelm backend, total outage
  Resilient response:
    - Rate limiting (per-IP, per-user limits)
    - CAPTCHA challenges (distinguish human vs bot)
    - Geoblocking (block malicious regions)
    - CDN absorption (serve cached content, protect backend)

  Result: Legitimate users unaffected, attack mitigated

Pattern:
  Design envelope repeatedly challenged by surprises
  System adapts, extends capacity, maintains value
  This is graceful extensibility in action
```

## High Reliability Organizations (HRO): Lessons from High-Stakes Systems

High Reliability Organizations: Industries where failure is catastrophic (aviation, nuclear power, hospitals). They've developed resilience practices.

### Five Principles of HROs

#### Principle 1: Preoccupation with Failure

**Definition**: Treat every anomaly as a potential catastrophe, investigate thoroughly.

```
Distributed Systems Application:

HRO Mindset:
  "A single timeout is not just a timeout - it's a signal of
   potential cascading failure, resource exhaustion, or
   impending outage."

Practices:
  - Investigate every anomaly (not just outages)
  - Track near-misses (incidents that almost caused failure)
  - Assume small errors can cascade
  - Reward reporting problems (blameless postmortems)

Example: AWS
  - Every latency spike investigated
  - Near-miss incidents logged (even if no customer impact)
  - Culture: "See something, say something"

Contrast with Low Reliability:
  "Just a timeout, happens all the time, ignore it."
  → Timeout signals growing problem, ignored until outage
```

#### Principle 2: Reluctance to Simplify

**Definition**: Resist oversimplifying complex situations; embrace nuance.

```
Distributed Systems Application:

Oversimplification (Bad):
  "The service is down."
  "Network is slow."
  "Database is overloaded."

Nuanced Understanding (Good):
  "The service is responding to 80% of requests with 200 OK,
   but P99 latency has increased from 50ms to 500ms for the
   past 10 minutes, specifically for queries involving table X,
   correlating with a batch job that started at the same time."

Practices:
  - Detailed incident reports (not just "it's down")
  - Root cause analysis (multiple contributing factors)
  - Avoid blame (systems are complex, failures emergent)
  - Embrace uncertainty (don't force simple explanations)

Example: Google SRE
  - Detailed postmortems (10+ pages)
  - Timeline reconstructions (minute-by-minute)
  - Contributing factors (not single root cause)

Contrast with Low Reliability:
  "Server crashed, restart it, done."
  → Miss contributing factors, problem recurs
```

#### Principle 3: Sensitivity to Operations

**Definition**: Pay attention to frontline operations; operators know what's really happening.

```
Distributed Systems Application:

Operator Signals:
  - On-call engineers: "Alerts have been flapping"
  - Service owners: "Recent deploy feels slow"
  - Customer support: "Users reporting intermittent errors"

Value of Operators:
  - See patterns before metrics show them
  - Experience anomalies firsthand
  - Understand system quirks (tribal knowledge)

Practices:
  - Listen to on-call feedback
  - Empower operators (they can halt deploys, rollback)
  - Quick feedback loops (operator → engineer)
  - Respect tacit knowledge (not everything is in docs)

Example: Netflix
  - Engineers on-call for their services
  - Can halt global rollouts if issues detected
  - "You build it, you run it" culture

Contrast with Low Reliability:
  "Metrics look fine, ignore operator concerns."
  → Miss early warning signs, incident escalates
```

#### Principle 4: Commitment to Resilience

**Definition**: Invest in ability to recover, not just prevent failures.

```
Distributed Systems Application:

Prevention (Necessary but Insufficient):
  - Testing (unit, integration, end-to-end)
  - Code review (catch bugs before production)
  - Staging environments (test before deploy)

Recovery (Resilience):
  - Chaos engineering (inject failures, test recovery)
  - Runbooks (step-by-step incident response)
  - Fast rollback (automated rollback on errors)
  - Incident drills (practice response procedures)

Practices:
  - Assume failures will happen (not if, but when)
  - Test recovery paths (are runbooks up-to-date?)
  - Time to recovery (MTTR) more important than time between failures (MTBF)
  - Continuous resilience testing (GameDays, DiRT exercises)

Example: Google DiRT (Disaster Recovery Testing)
  - Annual drills: Simulate datacenter failures, network partitions
  - Test recovery procedures
  - Discover gaps in runbooks
  - Improve response time

Contrast with Low Reliability:
  "We test thoroughly, failures won't happen."
  → When failure happens, no recovery plan, prolonged outage
```

#### Principle 5: Deference to Expertise

**Definition**: In crisis, defer to whoever has most expertise, regardless of rank.

```
Distributed Systems Application:

Hierarchical Response (Bad):
  Manager: "I think we should restart the database."
  Engineer (who knows system): "That will cause split-brain."
  Manager: "Do it anyway, I'm in charge."
  → Wrong decision, outage escalates

Expert-Driven Response (Good):
  Manager: "What do you recommend?"
  Engineer: "We should drain traffic, then restart DB leader only."
  Manager: "Do it, you have authority."
  → Right decision, outage contained

Practices:
  - Incident Commander role (expert leads response, not manager)
  - Empower engineers (no need for VP approval to rollback)
  - Trust expertise (don't second-guess specialists)
  - Clear authority (incident commander decides, others execute)

Example: AWS Incident Response
  - Incident Commander role (rotates among senior engineers)
  - Full authority to make decisions (rollback, failover, traffic shifts)
  - Manager observes but doesn't override

Contrast with Low Reliability:
  "Wait for VP approval before rollback."
  → Delay, outage prolonged, customer impact amplified
```

## Resilience Patterns: Engineering Practices

### Pattern 1: Circuit Breaker

**Purpose**: Prevent cascading failures by stopping requests to failing service.

```
States:
  - Closed: Normal operation, requests flow
  - Open: Failures detected, requests blocked
  - Half-Open: Testing recovery, limited requests

Transitions:
  Closed → Open: Error rate > threshold (e.g., 50%)
  Open → Half-Open: After timeout (e.g., 30s)
  Half-Open → Closed: Test requests succeed
  Half-Open → Open: Test requests fail

Example:
  Service A calls Service B (payment service)

  Normal:
    Circuit: Closed
    A → B: 1000 req/s, 0.1% errors

  B Degrades:
    t=0s: B slow (latency 50ms → 500ms)
    t=10s: A timeouts increase (500ms > 200ms timeout)
    t=20s: Error rate = 60% (> 50% threshold)
    t=20s: Circuit Opens
      - A stops calling B
      - A returns cached response or error
      - B gets time to recover

  Recovery:
    t=50s: Circuit → Half-Open (after 30s timeout)
    t=50s: A sends 1 test request to B
    t=50s: B responds successfully (recovered)
    t=50s: Circuit → Closed
    t=50s: A resumes normal traffic to B

Resilience Benefit:
  Without circuit breaker:
    - A keeps calling B (amplifying B's overload)
    - Retry storms (timeouts → retries → more load)
    - A also fails (timeouts cascade)

  With circuit breaker:
    - A stops calling B (gives B time to recover)
    - No retry storms (circuit open = fail fast)
    - A continues serving (cached responses, degraded)
```

### Pattern 2: Bulkhead

**Purpose**: Isolate failures to prevent total system collapse.

```
Concept: Separate resource pools (like ship bulkheads compartmentalize flooding)

Example: Thread Pools per Tenant

Without Bulkhead:
  Shared thread pool: 100 threads
  Tenant A: 10 req/s (normal)
  Tenant B: 100 req/s (suddenly, bug causes infinite loop)

  Result:
    - Tenant B consumes all 100 threads
    - Tenant A starved (0 threads available)
    - Both tenants fail (noisy neighbor problem)

With Bulkhead:
  Separate thread pools:
    - Tenant A: 50 threads
    - Tenant B: 50 threads

  Tenant B bug:
    - Tenant B consumes all 50 threads (its pool)
    - Tenant A unaffected (separate pool)
    - Tenant B fails, Tenant A continues (isolation)

Resilience Benefit:
  Failure contained to one compartment (tenant, region, service)
  Other compartments continue operating
  Blast radius limited
```

### Pattern 3: Backpressure

**Purpose**: Slow down producer when consumer overloaded.

```
Problem: Producer overwhelms consumer

Without Backpressure:
  Producer: 1000 req/s
  Consumer: Capacity 500 req/s

  Result:
    - Queue grows unbounded
    - Consumer falls further behind
    - Eventually: OOM crash

With Backpressure:
  Consumer signals producer: "I'm full, slow down"

  Mechanism:
    - Queue depth monitored
    - When queue > threshold (e.g., 1000 items):
      - Consumer signals backpressure
      - Producer slows down (500 req/s)
    - When queue drains (< threshold):
      - Consumer removes backpressure
      - Producer resumes (1000 req/s)

Example: TCP Flow Control
  - Receiver advertises window size (buffer space available)
  - Sender limits transmission to window size
  - Window shrinks → sender slows
  - Window grows → sender speeds up

Resilience Benefit:
  System self-regulates (no manual intervention)
  Prevents overload (queue stays bounded)
  Graceful degradation (slower, not crashed)
```

### Pattern 4: Load Shedding

**Purpose**: Reject low-priority requests to serve high-priority ones.

```
Scenario: System at capacity, cannot serve all requests

Without Load Shedding:
  - Serve all requests (best effort)
  - All requests slow (queueing delay)
  - All requests eventually timeout
  - Result: 0% success rate (total failure)

With Load Shedding:
  - Prioritize requests (critical > normal > low)
  - At capacity:
    - Reject low-priority (10% of traffic)
    - Slow normal-priority (30% of traffic)
    - Serve critical-priority (60% of traffic)
  - Result: 90% success rate (graceful degradation)

Prioritization Strategies:
  - By request type (writes > reads)
  - By user tier (premium > free)
  - By endpoint (health checks > API calls)
  - By SLA (contracted customers > trial users)

Example: Netflix
  During overload:
    - Priority 0 (Critical): Video playback (must work)
    - Priority 1 (Important): Authentication, browsing
    - Priority 2 (Nice-to-have): Recommendations, ratings

  Shedding order: Priority 2 → Priority 1 → Priority 0

Resilience Benefit:
  Maintain core functionality (video plays)
  Degrade non-essential features (recommendations)
  Better partial service than total failure
```

### Pattern 5: Retry Budget

**Purpose**: Limit retries to prevent retry storms.

```
Problem: Unlimited retries amplify overload

Without Retry Budget:
  Request fails → Retry immediately → Fails again → Retry → ...

  Result:
    - 1 original request → 10 retries
    - 1000 original req/s → 10,000 req/s with retries
    - System overload (10× amplification)

With Retry Budget:
  Each client has retry budget (e.g., 10 retries per minute)

  Request fails:
    - Check budget: retries_used < 10?
    - If yes: retry (decrement budget)
    - If no: fail fast (budget exhausted)

  Budget resets every minute

Example:
  Client A: 100 req/s
  Error rate: 1%
  Retries per second: 1 req/s
  Retries per minute: 60 req/s

  Budget: 10 retries per minute

  Result:
    - Only 10 retries attempted (budget limit)
    - 50 failures fail fast (over budget)
    - Total traffic: 100 original + 10 retries = 110 req/s (not 160)

Resilience Benefit:
  Prevents retry storms (bounded amplification)
  Fails fast when overloaded (don't make problem worse)
  Protects backend from amplified load
```

### Pattern 6: Adaptive Timeout

**Purpose**: Adjust timeouts based on observed latency.

```
Problem: Fixed timeouts are brittle

Fixed Timeout (e.g., 100ms):
  Normal: P99 = 50ms → 100ms timeout is generous
  Overload: P99 = 200ms → 100ms timeout causes false failures

  Result: System appears down (all requests timeout)
          But actually just slow (requests would succeed at 200ms)

Adaptive Timeout:
  Timeout = P99 latency × safety factor (e.g., 2×)

  Normal: P99 = 50ms → Timeout = 100ms
  Overload: P99 = 200ms → Timeout = 400ms

  Timeout adjusts to current conditions

Example:
  Service A calls Service B

  Window: Last 1000 requests
  P99 latency: 80ms
  Timeout: 80ms × 2 = 160ms

  B becomes slow:
    - P99 increases: 80ms → 120ms → 180ms
    - Timeout adjusts: 160ms → 240ms → 360ms
    - Requests still succeed (longer timeout)

  B recovers:
    - P99 decreases: 180ms → 100ms → 50ms
    - Timeout adjusts: 360ms → 200ms → 100ms
    - Back to normal

Resilience Benefit:
  System adapts to changing conditions
  Avoids false failures (premature timeouts)
  Balances responsiveness (fast timeout) vs success rate (generous timeout)
```

## Chaos Engineering: Testing for Resilience

**Chaos Engineering** (Netflix): "The discipline of experimenting on a system to build confidence in its capability to withstand turbulent conditions in production."

### The Chaos Engineering Process

```
1. Define Steady State
   What does "normal" look like?

   Metrics:
     - Availability: 99.9%
     - Latency P99: < 100ms
     - Error rate: < 0.1%
     - Throughput: 5000 req/s

2. Hypothesize Steady State Continues
   "We believe the system will maintain steady state
    even when we inject failures."

3. Inject Failures (Independent Variable)
   Simulate real-world failures:
     - Instance termination (Chaos Monkey)
     - Network latency (Latency Monkey)
     - Network partition (Chaos Kong)
     - Resource exhaustion (CPU, memory, disk)
     - Data corruption (bit flips)

4. Observe Differences (Dependent Variable)
   Does system maintain steady state?

   Possible outcomes:
     ✓ Steady state maintained (system resilient)
     ✗ Steady state violated (found weakness)

5. Learn and Improve
   If weakness found:
     - Add resilience mechanism (circuit breaker, retry budget)
     - Improve monitoring (detect issue faster)
     - Update runbooks (incident response)

   Repeat experiment:
     - Verify fix works
     - Increase blast radius (bigger experiments)
```

### Chaos Experiments: Examples

#### Experiment 1: Instance Termination

```
Hypothesis:
  "System maintains 99.9% availability when random instances
   are terminated."

Setup:
  - Production traffic: 5000 req/s
  - Instances: 10 (each handles 500 req/s)
  - Chaos Monkey: Randomly terminates 1 instance

Observation:
  t=0: 10 instances, 5000 req/s, 0.1% errors
  t=30s: Chaos Monkey terminates instance #7
  t=30s: Traffic redistributed (9 instances, 555 req/s each)
  t=31s: Autoscaler detects, starts new instance
  t=35s: New instance healthy, joins pool
  t=35s: 10 instances, 5000 req/s, 0.1% errors

Result: ✓ Hypothesis confirmed (availability maintained)

Resilience mechanisms tested:
  - Load balancer health checks (detected failure)
  - Traffic redistribution (9 instances handled load)
  - Autoscaling (replaced failed instance)
```

#### Experiment 2: Network Partition

```
Hypothesis:
  "System maintains 99.9% availability when network partition
   isolates 1 of 3 regions."

Setup:
  - Regions: us-east, us-west, eu-west
  - Traffic: 5000 req/s (distributed across regions)
  - Chaos Kong: Simulates partition (us-east unreachable)

Observation:
  t=0: 3 regions, 5000 req/s, 0.1% errors
  t=60s: Chaos Kong partitions us-east
  t=60s: us-east traffic fails (DNS/routing)
  t=65s: DNS failover detects, routes to us-west + eu-west
  t=70s: 2 regions, 5000 req/s, 0.1% errors

Result: ✓ Hypothesis confirmed (availability maintained)

Resilience mechanisms tested:
  - DNS failover (detected partition)
  - Multi-region redundancy (2 regions sufficient)
  - Load redistribution (us-west + eu-west handled 5000 req/s)
```

#### Experiment 3: Dependency Failure

```
Hypothesis:
  "System maintains 90% functionality when payment service
   is unavailable."

Setup:
  - Services: Frontend → Payment → Database
  - Traffic: 5000 req/s (1000 req/s to payment)
  - Chaos: Block all traffic to payment service

Observation:
  t=0: All services healthy, 5000 req/s, 0.1% errors
  t=90s: Chaos blocks payment service
  t=90s: Frontend calls to payment timeout
  t=91s: Circuit breaker opens (payment errors > 50%)
  t=91s: Frontend serves browsing/search (4000 req/s)
  t=91s: Frontend blocks checkout (1000 req/s fails)
  t=91s: 4000 req/s success (80% functionality)

Result: ✗ Hypothesis violated (80% vs expected 90%)

Action:
  - Improve graceful degradation (cache payment status)
  - Update hypothesis (90% → 80% realistic)

Resilience mechanisms tested:
  - Circuit breaker (stopped calling payment)
  - Graceful degradation (core browsing works)
  - Partial functionality (better than total failure)
```

### Chaos Engineering: Maturity Levels

```
Level 1: Ad-hoc Chaos (Manual testing)
  - Engineer manually terminates instances
  - Infrequent (quarterly)
  - Staging environment only

Level 2: Scheduled Chaos (Chaos Monkey)
  - Automated failure injection
  - Regular (daily)
  - Production environment
  - Single failure type (instance termination)

Level 3: Continuous Chaos (GameDays)
  - Multiple failure types (instances, network, resources)
  - Regular (weekly GameDays)
  - Production environment
  - Larger blast radius (region, service)

Level 4: Advanced Chaos (Always-On Chaos)
  - Chaos running continuously
  - Production environment
  - Adaptive experiments (target weak spots)
  - Organization-wide practice

Level 5: Chaos as Culture
  - Engineers expect failures
  - Design for resilience (default)
  - Chaos experiments before launch (mandatory)
  - Continuous learning (every incident improves resilience)

Netflix is at Level 5 (Chaos as Culture)
Most orgs are at Level 1-2 (Ad-hoc or Scheduled)
```

## Safety-II: Learning from Success, Not Just Failure

**Safety-I** (Traditional): Learn from failures, prevent recurrence.
**Safety-II** (Resilient): Learn from success - how does the system succeed despite complexity?

### Safety-I vs Safety-II

```
Safety-I (Failure-Focused):
  Question: "What went wrong?"
  Goal: Eliminate failures (zero incidents)
  Assumption: Failures are preventable
  Method: Root cause analysis, prevent recurrence

  Limitation:
    - Assumes failures have single root cause (often false)
    - Assumes system is predictable (complex systems aren't)
    - Ignores how system succeeds most of the time

Safety-II (Success-Focused):
  Question: "What goes right? How does the system succeed?"
  Goal: Amplify resilience (adapt to failures)
  Assumption: Surprises are inevitable
  Method: Study routine operations, understand adaptations

  Benefit:
    - Recognizes operators adapt to keep system running
    - Identifies unwritten practices (tacit knowledge)
    - Learns from near-misses (incidents that almost happened)
```

### Resilience in Routine Operations

```
Example: On-Call Engineer Adaptations

Scenario: Latency spike detected (P99: 100ms → 300ms)

Routine Adaptation (Not in Runbook):
  1. Check recent deploys (was there a rollout?)
  2. Check batch jobs (is ETL running?)
  3. Check dependencies (is DB slow?)
  4. Check metrics (CPU, memory, disk)
  5. Hypothesis: ETL job caused spike
  6. Action: Throttle ETL job (reduce QPS)
  7. Result: Latency returns to normal (100ms)

This adaptation prevented an incident (latency didn't breach SLA).
No incident report (nothing "failed").
But engineer used resilience skills (diagnosis, adaptation, mitigation).

Safety-II Learning:
  "How did the engineer succeed in preventing the incident?"

  Skills:
    - Pattern recognition (similar to previous incidents)
    - System knowledge (ETL job can cause latency)
    - Quick action (throttled ETL before SLA breach)

  Amplification:
    - Document pattern (add to runbooks)
    - Automate response (auto-throttle ETL on latency spike)
    - Share knowledge (train other engineers)

Safety-I would miss this:
  No incident → No postmortem → No learning
```

## Measuring Resilience: Beyond Availability

Traditional metrics (availability, latency) measure robustness, not resilience. Need new metrics:

### Resilience Metric 1: Time to Detection (TTD)

```
Definition: How quickly is an anomaly detected?

Example:
  - Service degrades at t=0
  - Alert fires at t=5min
  - TTD = 5 minutes

Goal: Minimize TTD (detect early, respond faster)

Improvements:
  - Better monitoring (more granular metrics)
  - Anomaly detection (ML models)
  - Canary deployments (detect issues in small rollout)
```

### Resilience Metric 2: Time to Recovery (TTR)

```
Definition: How quickly is system restored to normal?

Example:
  - Incident starts at t=0
  - Root cause identified at t=10min
  - Mitigation deployed at t=20min
  - System recovered at t=30min
  - TTR = 30 minutes

Goal: Minimize TTR (recover fast)

Improvements:
  - Automated rollback (1-click recovery)
  - Circuit breakers (auto-recovery)
  - Runbooks (faster diagnosis)
```

### Resilience Metric 3: Degradation Gracefullness

```
Definition: How much functionality is maintained under stress?

Example:
  Dependency failure:
    - Without resilience: 0% functionality (total outage)
    - With resilience: 80% functionality (core features work)

  Gracefullness = 80% / 100% = 0.8

Goal: Maximize gracefullness (maintain value under stress)

Improvements:
  - Graceful degradation (disable non-essential features)
  - Caching (serve stale data)
  - Fallbacks (default responses)
```

### Resilience Metric 4: Adaptability

```
Definition: How well does system handle unforeseen conditions?

Measure: Incident types over time
  - Known incident (previously seen): Not surprising
  - Novel incident (never seen): Surprising

  Adaptability = Incidents resolved / Novel incidents

Example:
  Q1: 10 incidents, 8 novel, 7 resolved → Adaptability = 7/8 = 87.5%
  Q2: 12 incidents, 5 novel, 5 resolved → Adaptability = 5/5 = 100%

Goal: Increase adaptability (handle more surprises)

Improvements:
  - Chaos engineering (test novel scenarios)
  - Incident learning (update runbooks)
  - Automation (faster response)
```

## Conclusion: Designing for Resilience

Distributed systems operate in a complex, unpredictable environment:
- **Unknown unknowns**: Failures we haven't imagined
- **Surprise events**: Conditions outside design envelope
- **Emergent behaviors**: System-level failures from component interactions

Robustness is necessary but insufficient:
- Robustness: Works within design envelope
- Resilience: Adapts beyond design envelope

**Resilience Engineering Principles**:

1. **Graceful Extensibility**: Extend capacity into surprise events
2. **HRO Practices**: Preoccupation with failure, reluctance to simplify, sensitivity to operations, commitment to resilience, deference to expertise
3. **Resilience Patterns**: Circuit breakers, bulkheads, backpressure, load shedding, retry budgets, adaptive timeouts
4. **Chaos Engineering**: Continuously test resilience through failure injection
5. **Safety-II**: Learn from success (routine adaptations) not just failure
6. **Measure Resilience**: TTD, TTR, gracefullness, adaptability (not just availability)

The goal is not to prevent all failures (impossible in complex systems) but to **adapt gracefully when failures occur**. This is the essence of resilience engineering - designing systems that maintain value under conditions we cannot predict or prevent.

Distributed systems are complex. Resilience is how we survive complexity.
