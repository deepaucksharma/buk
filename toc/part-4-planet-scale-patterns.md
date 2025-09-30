# Part IV: Planet-Scale Patterns

## Chapter 11: The Escrow Economy

### 11.1 Resource Management
* 11.1.1 Inventory Systems
  - Global visibility requirements
    - True global count: requires coordination
    - Eventual consistency: risk of oversell
    - Escrow approach: partitioned with local guarantees
  - Regional allocations
    - Static allocation at startup
    - Dynamic rebalancing during operation
    - Load-based redistribution
  - Local decrements
    - O(1) local operation
    - No network coordination
    - Fast path success
  - Reconciliation cycles
    - Periodic global count
    - Detect and correct drift
    - Rebalance escrow tokens

* 11.1.2 Mathematical Models with Stochastic Analysis
  - Token allocation formula
    ```
    T_region = T_global × weight_region

    Where weight is based on:
    - Historical demand: w_history
    - Current load: w_load
    - Geographic distribution: w_geo

    weight_region = (w_history × 0.5) + (w_load × 0.3) + (w_geo × 0.2)

    Example:
    T_global = 1000 seats
    Region A: historical 60%, current load 70%, geo 50%
      weight_A = 0.6×0.5 + 0.7×0.3 + 0.5×0.2 = 0.61
      T_A = 1000 × 0.61 = 610 seats

    Region B: historical 40%, current load 30%, geo 50%
      weight_B = 0.4×0.5 + 0.3×0.3 + 0.5×0.2 = 0.39
      T_B = 1000 × 0.39 = 390 seats
    ```

  - Refill cadence with safety factor
    ```
    Refill period: R = consumption_rate × latency × safety_factor

    Poisson arrival model:
    - Requests arrive at rate λ (requests/second)
    - Service time: μ (capacity/second)
    - Utilization: ρ = λ/μ

    Safety factor accounts for:
    1. Network latency variance (σ_latency)
    2. Burst traffic (95th percentile / mean)
    3. Failure recovery time

    safety_factor = 1 + (σ_latency / mean_latency) + (p95_rate / mean_rate)

    Worked Example:
    - λ = 100 requests/sec
    - μ = 150 requests/sec (capacity)
    - mean_latency = 50ms for refill
    - σ_latency = 10ms
    - p95_rate = 150 requests/sec

    safety_factor = 1 + (10/50) + (150/100) = 1 + 0.2 + 0.5 = 1.7

    Tokens needed for refill window:
    R = 100 req/s × 0.05s × 1.7 = 8.5 ≈ 9 tokens minimum

    Refill every: 9 tokens / 100 req/s = 90ms
    ```

  - Debt ceiling calculation
    ```
    D_max = escrow_tokens × risk_tolerance

    risk_tolerance depends on:
    - Cost of oversell (revenue loss, customer anger)
    - Probability of concurrent exhaustion

    Example:
    escrow_tokens = 100 per region
    If oversell cost = $1000/ticket
    If expected oversell = 5% of debt
    Then risk_tolerance should be: (acceptable_loss) / (oversell_cost × debt)

    If we accept $500 expected loss:
    risk_tolerance = $500 / ($1000 × debt)
    debt × 0.05 × $1000 = $500
    debt = 10 tickets maximum

    D_max = 100 × 0.1 = 10 tickets debt allowed
    ```

  - Oversell risk with tail probability bounds
    ```
    Poisson model for concurrent requests:
    P(X = k) = (λ^k × e^-λ) / k!

    Where λ = expected_concurrent_requests

    Tail probability (oversell risk):
    P(oversell) = P(X > capacity) = 1 - P(X ≤ capacity)

    Worked Example:
    capacity = 100 tokens
    λ = 95 (expected concurrent at peak)
    σ = √λ = 9.75 (std dev for Poisson)

    Using normal approximation (valid for λ > 30):
    P(X > 100) ≈ P(Z > (100.5 - 95)/9.75)
                ≈ P(Z > 0.564)
                ≈ 0.286 (28.6% chance of oversell!)

    To reduce to 1% risk:
    P(Z > z) = 0.01 → z = 2.33
    capacity_needed = 95 + 2.33 × 9.75 = 95 + 22.7 = 118 tokens

    Safety margin: 118 - 95 = 23 tokens (24%)
    ```

  - Complete worked example: Concert ticket sales
    ```
    Scenario:
    - Total seats: 10,000
    - Regions: US-East (50%), US-West (30%), EU (20%)
    - Expected peak: 1000 requests/sec globally
    - Network latency: 50ms mean, 20ms stddev
    - Burst factor: 2x at flash sale start

    Step 1: Initial allocation
    US-East: 10,000 × 0.50 = 5,000 tickets
    US-West: 10,000 × 0.30 = 3,000 tickets
    EU:      10,000 × 0.20 = 2,000 tickets

    Step 2: Refill calculation (US-East)
    λ_us_east = 500 req/s (50% of 1000)
    burst = 1000 req/s (2x)
    latency_95 = 50 + 2×20 = 90ms
    safety = 1 + (20/50) + (1000/500) = 1 + 0.4 + 2.0 = 3.4

    Tokens for refill window:
    R = 1000 × 0.09 × 3.4 = 306 tokens

    Refill interval: 306 / 500 = 0.612s ≈ 600ms
    (Check refill every 600ms, adjust if needed)

    Step 3: Oversell risk
    At peak: 1000 req/s × 0.1s window = 100 concurrent
    Capacity: 5000 tokens
    λ = 100, σ = 10
    P(exhaust) = P(X > 5000) ≈ 0 (extremely unlikely)

    But for one region going hot:
    If US-East sees 2000 req/s (surge):
    Concurrent in 100ms window = 200 requests
    Local capacity: 5000 tokens
    Can handle: 5000 / 200 = 25 windows = 2.5 seconds
    Refill time: 600ms
    Safe: 2500ms >> 600ms refill

    Conclusion: Configuration is safe with 3.4x safety factor
    ```

* 11.1.3 Multi-Level Escrow Rebalancing Algorithms
  - Push-based rebalancing (proactive)
    ```python
    def rebalance_push(global_pool, regions, interval=60s):
        """Redistribute tokens every interval based on utilization"""
        while True:
            wait(interval)

            # Collect utilization metrics
            utilization = {r: r.used / r.capacity for r in regions}

            # Identify hot and cold regions
            avg_util = mean(utilization.values())
            hot_regions = [r for r in regions if utilization[r] > avg_util * 1.5]
            cold_regions = [r for r in regions if utilization[r] < avg_util * 0.5]

            # Transfer tokens from cold to hot
            for cold in cold_regions:
                surplus = cold.capacity * (avg_util - utilization[cold])
                for hot in hot_regions:
                    deficit = hot.capacity * (utilization[hot] - avg_util)
                    transfer = min(surplus, deficit, global_pool.available)

                    cold.capacity -= transfer
                    hot.capacity += transfer
                    surplus -= transfer

            # Log rebalancing
            log(f"Rebalanced: {hot_regions} got tokens from {cold_regions}")
    ```

  - Pull-based rebalancing (reactive)
    ```python
    def handle_request_with_pull(region, request):
        """Request borrows from global pool on local exhaustion"""
        if region.available > 0:
            region.available -= 1
            return SUCCESS

        # Local exhausted, try to borrow
        borrowed = global_pool.try_borrow(amount=region.capacity * 0.1)
        if borrowed > 0:
            region.capacity += borrowed
            region.available += borrowed - 1
            return SUCCESS

        # Global pool exhausted
        return RETRY_LATER
    ```

  - Hybrid approach (production pattern)
    ```python
    class HybridEscrow:
        def __init__(self, global_capacity, num_regions):
            self.global_capacity = global_capacity
            self.regions = [Region(global_capacity // num_regions)
                           for _ in range(num_regions)]
            self.rebalance_interval = 10  # seconds
            self.borrow_threshold = 0.1   # Borrow when 10% remain

        def handle_request(self, region_id, request):
            region = self.regions[region_id]

            # Fast path: local tokens available
            if region.available > 0:
                region.available -= 1
                return SUCCESS

            # Slow path: try to borrow
            if region.available / region.capacity < self.borrow_threshold:
                self.try_rebalance(region_id)

            if region.available > 0:
                region.available -= 1
                return SUCCESS

            return EXHAUSTED

        def try_rebalance(self, region_id):
            """Pull tokens from other regions"""
            region = self.regions[region_id]
            target = region.capacity * 0.2  # Want 20% refill

            for other in self.regions:
                if other == region:
                    continue
                if other.available > other.capacity * 0.8:
                    # Other region has excess
                    transfer = min(other.available - other.capacity * 0.5,
                                   target)
                    other.available -= transfer
                    region.available += transfer
                    target -= transfer
                    if target <= 0:
                        break

        def periodic_rebalance(self):
            """Background task: proactive rebalancing"""
            # Run push-based algorithm every interval
            pass

    # Metrics
    # - Rebalance latency: 1-5ms (local transfer)
    # - Rebalance frequency: every 10s + on-demand
    # - Overhead: ~0.1% of capacity in transit
    ```

* 11.1.4 Flash Sale Patterns
  - Pre-allocation strategies
    - Reserve capacity per user/session
    - Time-based release (10k tickets at 10:00:00 sharp)
    - Progressive queue admission
  - Queue fairness
    - FIFO with random tie-breaking
    - Lottery selection (fair random subset)
    - Weighted queues (premium users)
  - Progressive disclosure
    - Batch admission: 100 users every second
    - Rate limit per user: 1 attempt per 5 seconds
    - Circuit breaker: if 95% fail, slow down admission
  - Graceful degradation
    - Show "Low inventory" warning at 20% remaining
    - Limit concurrent checkouts to 10x remaining
    - Auto-expire reservations after 5 minutes

### 11.2 Rate Limiting
* 11.2.1 Distributed Token Buckets
  - Local buckets
  - Synchronization strategies
  - Hierarchical limits
  - Burst handling
* 11.2.2 Global Rate Limiting
  - Eventual enforcement
  - Sliding windows
  - Token redistribution
  - Fairness algorithms
* 11.2.3 Adaptive Strategies
  - Load-based adjustment
  - Predictive allocation
  - Priority queues
  - SLO-based throttling

### 11.3 Quota Management
* 11.3.1 Multi-Dimensional Quotas
  - CPU quotas
  - Memory limits
  - Storage bounds
  - Network bandwidth
* 11.3.2 Hierarchical Enforcement
  - User → Application → Tenant
  - Inheritance rules
  - Override policies
  - Delegation patterns
* 11.3.3 Fair Sharing
  - Weighted fair queuing
  - Dominant resource fairness
  - Max-min fairness
  - Lottery scheduling

---

## Chapter 12: Hybrid Time at Scale

### 12.1 HLC Operations
* 12.1.1 Deployment Patterns
  - Cluster-wide setup
  - Service boundaries
  - Clock domain gateways
  - Session propagation
* 12.1.2 Failure Handling
  - Skew threshold responses
    - Degrade guarantees
    - Freeze strong paths
    - Alert operations
  - Recovery procedures
  - Clock resynchronization
  - HLC reset protocols
* 12.1.3 Cross-Service Integration
  - Header propagation
  - Gateway translation
  - Domain boundaries
  - Monotonic sessions

### 12.2 TrueTime Production
* 12.2.1 Infrastructure Requirements
  - GPS receiver deployment
  - Atomic clock selection
  - Redundancy architecture
  - Network time distribution
* 12.2.2 Operational Challenges
  - GPS jamming mitigation
  - Leap second handling
  - Multi-source validation
  - ε inflation drills
* 12.2.3 Monitoring and Alerting
  - ε distribution tracking
  - Commit-wait histograms
  - Clock health metrics
  - Drift detection

### 12.3 Bounded Staleness with Explicit Windows
* 12.3.1 Safe Timestamp Mechanics
  - Closed timestamp calculation
    - min(applied_index) - uncertainty
    - Conservative bound: max_clock_skew + replication_lag
  - Progress tracking
    - Watermark advancement
    - Quorum acknowledgment
  - Stability detection
    - All replicas caught up to T
    - Safe to GC older versions
  - Update propagation
    - Push to followers
    - Pull-based catch-up

* 12.3.2 Explicit Staleness Windows (Production Pattern)
  - Configuration examples
    ```yaml
    # CockroachDB-style
    read_consistency:
      level: follower_read
      max_staleness: 5s  # Explicit bound
      fallback_to_leader: true  # If no follower within bound

    # Cassandra-style
    consistency_level: LOCAL_QUORUM
    read_repair_chance: 0.1

    # Custom policy
    staleness_policy:
      strong_read:
        max_age: 0s
        target: leader
        cost: high_latency
      bounded_stale:
        max_age: 10s
        target: nearest_follower
        cost: low_latency
      eventual:
        max_age: 60s
        target: local_cache
        cost: lowest_latency
    ```

  - Application-level staleness control
    ```rust
    // Rust client example
    let read_options = ReadOptions {
        consistency: Consistency::BoundedStaleness {
            max_age: Duration::from_secs(5),
        },
        timeout: Duration::from_millis(100),
    };

    match client.get("key", read_options) {
        Ok(value) => {
            // Value is at most 5s stale
            println!("Value: {}, staleness: {}ms",
                     value.data, value.age_ms);
        }
        Err(StalenessBoundViolated) => {
            // No replica within 5s bound, fallback to leader
            let value = client.get("key", ReadOptions::strong())?;
        }
    }
    ```

  - Staleness vs latency tradeoffs
    ```
    Scenario: Global read from US-East, data in EU-West

    Strong read (leader):
    - Latency: 80ms (cross-Atlantic RTT)
    - Staleness: 0ms
    - Cost: $0.02 per 10k reads (egress)

    Bounded stale (5s window, local follower):
    - Latency: 2ms (local replica)
    - Staleness: 0-5s (avg ~2s in practice)
    - Cost: $0.001 per 10k reads (no egress)

    Eventual (local cache):
    - Latency: 0.1ms (in-memory)
    - Staleness: 0-60s (depends on write rate)
    - Cost: $0.0001 per 10k reads

    Tradeoff matrix:
    |                  | Strong | Bounded (5s) | Eventual |
    |------------------|--------|--------------|----------|
    | Latency (p50)    | 80ms   | 2ms          | 0.1ms    |
    | Latency (p99)    | 150ms  | 10ms         | 1ms      |
    | Cost per 10k     | $0.02  | $0.001       | $0.0001  |
    | Staleness        | 0      | 0-5s         | 0-60s    |
    | Use case         | Money  | Social feed  | Analytics|
    ```

* 12.3.3 Read Optimization Strategies
  - Follower read routing
    - Proximity-based selection
    - Load balancing across followers
    - Health checking
  - Staleness SLAs
    - Per-query staleness budget
    - Automatic leader fallback
    - Monitoring and alerting
  - Consistency tokens
    - Client-provided causality token
    - "Read your own writes" guarantee
    - Session consistency
  - Cache integration
    - Bounded-staleness cache
    - TTL-based invalidation
    - Proactive refresh

* 12.3.4 Global Snapshots
  - Snapshot isolation
    - Consistent snapshot timestamp
    - MVCC with garbage collection
  - Causal consistency
    - Happens-before tracking
    - Version vectors
  - External consistency
    - TrueTime-style wait
    - Hybrid logical clocks
  - Read timestamp selection
    ```sql
    -- Explicit snapshot timestamp
    SELECT * FROM orders
    AS OF SYSTEM TIME '2025-09-30 10:00:00';

    -- Bounded staleness
    SELECT * FROM products
    WITH STALENESS = '5s';

    -- Follower read (automatic)
    SELECT * FROM cache_table
    WITH CONSISTENCY = 'FOLLOWER';
    ```

---

## Chapter 13: Proof-Carrying State

### 13.1 Authenticated Structures
* 13.1.1 Merkle Tree Variants
  - Binary Merkle trees
  - Merkle Patricia tries
  - Verkle trees
    - Polynomial commitments
    - Proof size optimization
    - Update costs
  - Sparse Merkle trees
* 13.1.2 Proof Generation
  - Inclusion proofs
  - Exclusion proofs
  - Range proofs
  - Batch proofs
* 13.1.3 Verification Costs
  - Client-side verification
  - Proof size optimization
  - Caching strategies
  - Batch verification

### 13.2 Consensus Certificates
* 13.2.1 Certificate Structure
  - Quorum signatures
  - BLS aggregation
  - Threshold signatures
  - DKG protocols
* 13.2.2 Certificate Chains
  - Chain validation
  - Fork detection
  - Finality proofs
  - Checkpoint certificates
* 13.2.3 Light Clients
  - Minimal verification
  - Header chains
  - Fraud proofs
  - Data availability

### 13.3 Cross-System Trust
* 13.3.1 Attestation Infrastructure
  - Remote attestation
  - TEE integration
  - Freshness tokens
  - Evidence channels
* 13.3.2 Interoperability
  - Cross-chain bridges
  - State proofs
  - Relay networks
  - Atomic swaps
* 13.3.3 Compliance Proofs
  - Tamper-evident logs
  - Audit trails
  - Regulatory attestations
  - Privacy preservation

---

## Chapter 14: Planet-Scale Operations

### 14.1 Global DNS and Traffic Routing
* 14.1.1 GSLB (Global Server Load Balancing)
  - DNS-based routing patterns
    ```
    Anycast: Same IP advertised from multiple locations
    - Pros: Automatic failover, low latency
    - Cons: Connection disruption on route change
    - Use: CDN edge, DDoS mitigation

    GeoDNS: Return region-specific IPs
    - Pros: Sticky connections, explicit control
    - Cons: DNS caching delays, requires health checks
    - Use: Database replicas, regional services

    Weighted DNS: Probabilistic distribution
    - Pros: Gradual rollout, A/B testing
    - Cons: No session affinity, cache issues
    - Use: Canary deployments, traffic shaping
    ```

  - Health check architecture
    ```yaml
    health_check_config:
      global_controller:
        location: us-central1
        interval: 10s
        timeout: 5s
        failure_threshold: 3

      regional_endpoints:
        - region: us-east1
          endpoints:
            - ip: 10.0.1.100
              protocol: https
              path: /health
              expected_status: 200
          weights:
            healthy: 100
            degraded: 50
            unhealthy: 0

        - region: eu-west1
          endpoints:
            - ip: 10.1.2.100
              protocol: https
              path: /health

      dns_update_policy:
        ttl: 60s  # Low TTL for faster failover
        min_healthy_regions: 2
        on_failure:
          remove_from_dns: true
          alert: pagerduty
    ```

  - Operational playbook: Regional outage
    ```
    Scenario: AWS us-east-1 region outage

    T+0 (Detection):
    1. Health checks fail (3 consecutive at 10s intervals = 30s)
    2. Automated DNS update: remove us-east-1 from rotation
    3. Alert to on-call engineer

    T+1 min (DNS propagation):
    1. New DNS responses exclude us-east-1
    2. Clients with cached DNS (up to 60s TTL) still affected
    3. Anycast routes shift to us-west-2

    T+2 min (Traffic drained):
    1. 95% of clients using healthy regions
    2. Connection errors drop to baseline
    3. Capacity check: remaining regions handle 1.5x load

    T+5 min (Monitoring):
    1. Verify no user-facing errors
    2. Check rate limiting not triggered
    3. Monitor database replica lag

    Recovery (when region healthy):
    1. Wait for 5 consecutive healthy checks
    2. Gradually restore traffic: 10% → 50% → 100%
    3. Monitor for 30 minutes before declaring resolved
    ```

* 14.1.2 Multi-Cloud DNS Strategy
  - Cross-cloud routing
    ```
    Architecture:
    - Primary DNS: AWS Route53 (geo-routing)
    - Secondary DNS: Cloudflare (anycast)
    - Tertiary: Google Cloud DNS (backup)

    Failover hierarchy:
    1. AWS us-east-1 (primary)
    2. GCP us-central1 (secondary)
    3. Azure eastus (tertiary)

    DNS record example:
    api.example.com.  60 IN A 34.123.45.67   ; GCP primary
                      60 IN A 52.23.45.68    ; AWS backup
                      60 IN A 20.10.20.30    ; Azure tertiary
    ```

  - Cost implications
    ```
    DNS query costs (per million queries):
    - AWS Route53: $0.40 (geo) / $0.60 (latency-based)
    - Cloudflare: $0.20 (included in CDN)
    - Google Cloud DNS: $0.20

    Health check costs:
    - AWS Route53: $0.50 per endpoint per month
    - Google Cloud: $0.30 per endpoint per month
    - Checks from 3 regions × 10 endpoints = $15/month (AWS)

    Total DNS infrastructure:
    - 100M queries/month: $40 (AWS) or $20 (GCP/Cloudflare)
    - 30 health checked endpoints: $15-45/month
    - Total: ~$60-85/month for global DNS
    ```

### 14.2 Cross-Cloud PKI and Certificate Rotation
* 14.2.1 Certificate Management at Scale
  - Automated rotation strategy
    ```bash
    # cert-manager + Let's Encrypt (Kubernetes-native)
    apiVersion: cert-manager.io/v1
    kind: Certificate
    metadata:
      name: api-tls
    spec:
      secretName: api-tls-secret
      duration: 2160h  # 90 days
      renewBefore: 360h  # Renew 15 days before expiry
      issuerRef:
        name: letsencrypt-prod
        kind: ClusterIssuer
      dnsNames:
        - api.example.com
        - "*.api.example.com"
      privateKey:
        algorithm: ECDSA
        size: 256
    ```

  - Multi-region certificate distribution
    ```python
    # Certificate rotation pipeline
    def rotate_certificates():
        """Rotate TLS certs across all regions with zero downtime"""

        # Step 1: Generate new cert (central CA)
        new_cert = ca.issue_certificate(
            domains=["*.api.example.com"],
            lifetime=90days,
        )

        # Step 2: Distribute to all regions (parallel)
        regions = ["us-east1", "eu-west1", "asia-northeast1"]
        futures = []
        for region in regions:
            future = async_upload_cert(region, new_cert)
            futures.append(future)

        wait_all(futures, timeout=60s)

        # Step 3: Canary deployment (1 region)
        activate_cert(region="us-east1", cert=new_cert)
        wait(5 minutes)
        if error_rate("us-east1") > baseline:
            rollback(region="us-east1")
            alert("Certificate rotation failed")
            return

        # Step 4: Roll out to remaining regions (one at a time)
        for region in ["eu-west1", "asia-northeast1"]:
            activate_cert(region=region, cert=new_cert)
            wait(2 minutes)
            if error_rate(region) > baseline:
                rollback(region)
                alert(f"Rotation failed in {region}")
                return

        # Step 5: Verify all regions healthy
        for region in regions:
            assert cert_expiry(region) > 60days

        log("Certificate rotation successful")
    ```

* 14.2.2 Cross-Cloud mTLS
  - Service mesh certificate management
    ```yaml
    # Istio-style cross-cluster mTLS
    apiVersion: networking.istio.io/v1alpha3
    kind: DestinationRule
    metadata:
      name: api-mtls
    spec:
      host: api.example.com
      trafficPolicy:
        tls:
          mode: ISTIO_MUTUAL
          clientCertificate: /etc/certs/cert-chain.pem
          privateKey: /etc/certs/key.pem
          caCertificates: /etc/certs/root-cert.pem

    # Certificate rotation via SPIFFE/SPIRE
    spire_config:
      trust_domain: example.com
      workload_api_socket: /run/spire/sockets/agent.sock
      certificate_ttl: 1h  # Short-lived certs
      rotation_interval: 30m  # Rotate before expiry
    ```

  - Operational metrics
    ```
    Certificate lifecycle metrics:
    - cert_expiry_days{region="us-east1"} 45
    - cert_rotation_duration_seconds{region="us-east1"} 120
    - cert_rotation_errors_total{region="us-east1"} 0
    - mtls_handshake_failures_total{region="us-east1"} 3

    Alerting rules:
    - Alert: CertificateExpiringSoon
      expr: cert_expiry_days < 14
      for: 1h
      severity: warning

    - Alert: CertificateExpired
      expr: cert_expiry_days < 0
      for: 1m
      severity: critical
    ```

### 14.3 Egress Costs and Replication Strategy
* 14.3.1 Cloud Egress Pricing (2025)
  - Cost breakdown by provider
    ```
    AWS (per GB):
    - Same region: $0.00
    - Cross-region (US): $0.02
    - Cross-region (intercontinental): $0.08
    - To internet: $0.09 (first 10 TB/month)

    GCP (per GB):
    - Same region: $0.00
    - Cross-region (US): $0.01
    - Cross-region (intercontinental): $0.05
    - To internet: $0.12 (first 1 TB/month)

    Azure (per GB):
    - Same region: $0.00
    - Cross-region (US): $0.02
    - Cross-region (intercontinental): $0.08
    - To internet: $0.087

    Cloudflare (flat rate):
    - All egress: $0.00 (included in plan)
    - Bandwidth Alliance: $0.00 for partner services
    ```

  - Cost model for global replication
    ```python
    # Calculate monthly replication costs
    def replication_cost_model(
        write_rate_gb_per_day: float,
        num_regions: int,
        replication_topology: str,
    ):
        """
        Topology options:
        - full_mesh: every region replicates to every other
        - star: one primary, replicate to all secondaries
        - regional: replicate within continent only
        """

        if replication_topology == "full_mesh":
            # N regions → N*(N-1) connections
            connections = num_regions * (num_regions - 1)
            data_per_connection = write_rate_gb_per_day / num_regions

        elif replication_topology == "star":
            # Primary → all secondaries
            connections = num_regions - 1
            data_per_connection = write_rate_gb_per_day

        elif replication_topology == "regional":
            # 3 continents, replicate within each
            regions_per_continent = num_regions / 3
            connections = 3 * regions_per_continent * (regions_per_continent - 1)
            data_per_connection = write_rate_gb_per_day / num_regions

        # Cost calculation
        egress_cost_per_gb = 0.02  # Assume same-continent
        monthly_data = data_per_connection * 30
        monthly_cost = monthly_data * egress_cost_per_gb * connections

        return {
            "connections": connections,
            "monthly_data_gb": monthly_data * connections,
            "monthly_cost_usd": monthly_cost,
        }

    # Example: 100 GB/day writes, 9 regions
    full_mesh = replication_cost_model(100, 9, "full_mesh")
    # → 72 connections, 216 TB/month, $4320/month

    star = replication_cost_model(100, 9, "star")
    # → 8 connections, 24 TB/month, $480/month

    regional = replication_cost_model(100, 9, "regional")
    # → 18 connections, 54 TB/month, $1080/month
    ```

* 14.3.2 Cost-Optimized Replication Strategies
  - Hierarchical replication (recommended)
    ```
    Architecture:
    Tier 1: Primary writers (3 regions)
    - AWS us-east-1
    - GCP europe-west1
    - Azure eastasia

    Tier 2: Regional secondaries (6 regions)
    - AWS us-west-2 ← replicates from us-east-1
    - GCP us-central1 ← replicates from us-east-1
    - GCP europe-west2 ← replicates from europe-west1
    - Azure westeurope ← replicates from europe-west1
    - GCP asia-northeast1 ← replicates from eastasia
    - AWS ap-southeast-1 ← replicates from eastasia

    Cost savings:
    - Full mesh: 9×8 = 72 connections
    - Hierarchical: 3×2 + 6×1 = 12 connections
    - Reduction: 83% fewer egress costs

    Latency tradeoff:
    - Full mesh: 1-hop replication (50-100ms)
    - Hierarchical: 2-hop for tier-2 (100-200ms)
    - Acceptable for async replication
    ```

  - Read replica placement optimization
    ```python
    def optimize_read_replica_placement(
        user_distribution: Dict[str, float],  # region → % of users
        latency_sla_ms: int,
        egress_cost_per_gb: float,
        read_qps: int,
    ):
        """Find optimal read replica placement"""

        # Constraint: cover 95% of users within latency SLA
        # Objective: minimize egress cost

        # Greedy algorithm:
        replicas = []
        covered_users = 0.0

        while covered_users < 0.95:
            # Find region that covers most uncovered users
            best_region = max(
                user_distribution.items(),
                key=lambda r: (
                    users_within_latency(r[0], latency_sla_ms)
                    * (1 - covered_users)
                ),
            )

            replicas.append(best_region[0])
            covered_users += users_within_latency(
                best_region[0], latency_sla_ms
            )

        # Calculate costs
        replication_gb_per_day = (read_qps * 365 * 86400) / (10**9)
        egress_cost = len(replicas) * replication_gb_per_day * 30 * egress_cost_per_gb

        return {
            "replicas": replicas,
            "num_replicas": len(replicas),
            "coverage": covered_users,
            "monthly_egress_cost": egress_cost,
        }

    # Example: 40% US, 35% EU, 25% Asia, 50ms SLA
    result = optimize_read_replica_placement(
        user_distribution={
            "us-east1": 0.40,
            "europe-west1": 0.35,
            "asia-northeast1": 0.25,
        },
        latency_sla_ms=50,
        egress_cost_per_gb=0.02,
        read_qps=10000,
    )
    # → 3 replicas, 96% coverage, $518/month
    ```

### 14.4 Operational Playbooks
* 14.4.1 Cross-Region Failover Runbook
  ```
  Scenario: Primary region (us-east-1) becomes unavailable

  Pre-requisites:
  - [ ] Standby region (us-west-2) is up-to-date (lag < 5s)
  - [ ] DNS TTL is 60s or less
  - [ ] All engineers have access to failover controls

  Manual Failover Steps:
  1. Confirm outage (2 minutes)
     $ curl https://health.api.example.com/us-east-1
     $ check_dashboard --region us-east-1
     Decision: Proceed if error rate > 50% for 2 minutes

  2. Stop writes to primary (1 minute)
     $ kubectl scale deployment api --replicas=0 --namespace=us-east-1
     Wait for in-flight requests to drain (60s)

  3. Promote standby to primary (3 minutes)
     $ db_admin promote --region us-west-2
     $ wait_for_replication_lag --region us-west-2 --max-lag 0
     $ db_admin set-primary us-west-2

  4. Update DNS (1 minute)
     $ aws route53 change-resource-record-sets --hosted-zone-id Z123 \
       --change-batch file://failover-to-us-west-2.json
     Propagation: up to 60s (TTL)

  5. Restore traffic (2 minutes)
     $ kubectl scale deployment api --replicas=10 --namespace=us-west-2
     Monitor error rate: should drop to < 1% within 2 minutes

  6. Verify (5 minutes)
     $ check_dashboard --region us-west-2
     - Error rate < 1%
     - Latency p99 < 100ms
     - Database lag = 0
     $ announce_in_slack "Failover to us-west-2 complete"

  Total time: ~15 minutes
  RTO: 5 minutes (DNS + promotion)
  RPO: 5 seconds (replication lag)
  ```

* 14.4.2 Certificate Expiry Emergency
  ```
  Scenario: Production certificate expires unexpectedly

  Emergency Response:
  1. Immediate mitigation (0-5 minutes)
     - Disable HTTPS validation (temporary)
     - Route traffic through load balancer with valid cert
     - Communicate to users via status page

  2. Generate emergency certificate (5-10 minutes)
     $ certbot certonly --manual --preferred-challenges dns \
       --domains api.example.com
     - Add DNS TXT record for validation
     - Wait for cert issuance (2-5 minutes)

  3. Deploy new certificate (10-20 minutes)
     $ kubectl create secret tls api-tls --cert=fullchain.pem --key=privkey.pem
     $ kubectl rollout restart deployment/api
     - Rolling restart: 0 downtime
     - Verify TLS handshake succeeds

  4. Root cause analysis (post-incident)
     - Why did auto-renewal fail?
     - Update monitoring: alert 30 days before expiry
     - Add pre-expiry drill to quarterly schedule
  ```

* 14.4.3 Cost Spike Investigation
  ```
  Scenario: Cloud bill increased 3x unexpectedly

  Investigation Steps:
  1. Identify cost spike (10 minutes)
     $ cloud_cost_analyzer --start-date 2025-09-01 --end-date 2025-09-30
     Output:
     - Egress: $15,000 (↑200% from last month)
     - Compute: $5,000 (stable)
     - Storage: $2,000 (stable)

  2. Drill down into egress (20 minutes)
     $ analyze_egress --region us-east-1 --top-talkers 10
     Output:
     - 80% of egress: replication to asia-northeast1
     - 15% of egress: user downloads
     - 5% of egress: monitoring/logs

  3. Root cause (15 minutes)
     $ check_replication_config asia-northeast1
     Issue found: Full replication enabled for archival database
     Expected: Only incremental updates

  4. Remediation (30 minutes)
     $ set_replication_filter asia-northeast1 --databases=production
     $ disable_replication --database=archive --target=asia-northeast1
     Expected savings: $10,000/month

  5. Prevent recurrence
     - Add cost alert: notify if egress > $5,000/day
     - Quarterly cost review: identify trends
     - Document approved replication topology
  ```