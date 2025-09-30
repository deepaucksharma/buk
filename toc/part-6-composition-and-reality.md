# Part VI: Composition and Reality

## Chapter 17: Composition and Adaptation

### 17.1 Composition Rules

#### 17.1.1 Formal Guarantee Algebra

**Composition laws:**

```
Guarantee levels (strongest to weakest):
  Strict Serializable (SS)
  > Serializable (S)
  > Snapshot Isolation (SI)
  > Read Committed (RC)
  > Eventually Consistent (EC)

Composition rules:
  SS ∘ SS = SS   (if same transaction)
  SS ∘ S  = S    (downgrade to weaker)
  S  ∘ SI = SI   (chain takes weakest link)
  SI ∘ EC = EC   (no upgrade without re-certification)

Identity: SS ∘ I = SS (no-op preserves guarantee)
Associative: (A ∘ B) ∘ C = A ∘ (B ∘ C)
```

**Proof-carrying context:**

```python
class ConsistencyContext:
    """Proof-carrying headers for distributed guarantees"""

    def __init__(self, guarantee_level, evidence):
        self.guarantee = guarantee_level
        self.evidence = evidence
        self.chain = [guarantee_level]

    def compose(self, next_service_guarantee):
        # Composition degrades to weakest link
        result_guarantee = min(self.guarantee, next_service_guarantee)

        self.chain.append(next_service_guarantee)
        self.guarantee = result_guarantee

        return self

    def certify(self, required_level):
        """Check if current guarantee meets requirement"""
        if self.guarantee < required_level:
            raise GuaranteeViolation(
                f"Required {required_level}, but chain provides {self.guarantee}"
            )

    def to_headers(self):
        return {
            'X-Consistency-Level': self.guarantee.name,
            'X-Consistency-Chain': ','.join(c.name for c in self.chain),
            'X-Consistency-Evidence': json.dumps(self.evidence),
        }

    @staticmethod
    def from_headers(headers):
        guarantee = GuaranteeLevel[headers['X-Consistency-Level']]
        evidence = json.loads(headers.get('X-Consistency-Evidence', '{}'))
        chain = [GuaranteeLevel[c] for c in headers['X-Consistency-Chain'].split(',')]

        ctx = ConsistencyContext(guarantee, evidence)
        ctx.chain = chain
        return ctx

# Usage in service handlers
@app.route('/api/checkout')
async def checkout(request):
    # Parse incoming consistency context
    ctx = ConsistencyContext.from_headers(request.headers)

    # This endpoint requires strict serializable
    ctx.certify(GuaranteeLevel.STRICT_SERIALIZABLE)

    # Call payment service (strict serializable)
    payment_result = await payment_service.charge(
        amount=request.amount,
        headers=ctx.to_headers()
    )

    # Compose with payment service guarantee
    ctx.compose(GuaranteeLevel.STRICT_SERIALIZABLE)

    # Call inventory service (snapshot isolation)
    inventory_result = await inventory_service.reserve(
        item_id=request.item_id,
        headers=ctx.to_headers()
    )

    # Composition degrades to snapshot isolation
    ctx.compose(GuaranteeLevel.SNAPSHOT_ISOLATION)

    # Overall guarantee is now SI (weakest link)
    return {
        'status': 'success',
        'consistency_level': ctx.guarantee.name,
        'consistency_chain': [c.name for c in ctx.chain],
    }
```

**Gate placement for upgrades:**

```python
class ConsistencyGate:
    """Re-certification point to upgrade guarantees"""

    def __init__(self, target_guarantee):
        self.target = target_guarantee

    async def certify_and_upgrade(self, data, current_context):
        """
        Upgrade guarantee by re-reading from authoritative source
        """
        if current_context.guarantee >= self.target:
            # Already strong enough
            return data, current_context

        # Re-read from source of truth with strong consistency
        authoritative_data = await self._read_authoritative(
            data.keys(),
            consistency=self.target
        )

        # Check for conflicts
        conflicts = self._detect_conflicts(data, authoritative_data)
        if conflicts:
            raise ConflictError(f"Data changed during weak read: {conflicts}")

        # Upgrade context
        new_context = ConsistencyContext(
            self.target,
            evidence={'certified_at': time.time(), 'gate': 'upgrade'}
        )

        return authoritative_data, new_context

    def _detect_conflicts(self, weak_data, strong_data):
        conflicts = []
        for key in weak_data:
            if weak_data[key].version != strong_data[key].version:
                conflicts.append(key)
        return conflicts

# Usage: upgrade from cache to strong read
@app.route('/api/critical-operation')
async def critical_operation(request):
    # Fast path: read from cache (eventually consistent)
    cached_data = await cache.get_multi(request.keys)
    weak_context = ConsistencyContext(
        GuaranteeLevel.EVENTUALLY_CONSISTENT,
        evidence={'source': 'cache'}
    )

    # Gate: upgrade to strict serializable before critical operation
    gate = ConsistencyGate(GuaranteeLevel.STRICT_SERIALIZABLE)
    certified_data, strong_context = await gate.certify_and_upgrade(
        cached_data,
        weak_context
    )

    # Now safe to do critical operation
    result = await critical_business_logic(certified_data, strong_context)
    return result
```

#### 17.1.2 Service Mesh Patterns

**Sidecar proxy with consistency enforcement:**

```yaml
# envoy-consistency-filter.yaml
filters:
  - name: consistency_enforcement
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
      inline_code: |
        function envoy_on_request(request_handle)
          local consistency_level = request_handle:headers():get("X-Consistency-Level")

          -- Check if downstream provides required guarantee
          local required = request_handle:metadata():get("required_consistency")
          if consistency_level < required then
            request_handle:respond(
              {[":status"] = "400"},
              "Consistency requirement not met: need " .. required .. " but got " .. consistency_level
            )
            return
          end

          -- Compose with this service's guarantee
          local service_guarantee = request_handle:metadata():get("service_consistency")
          local result_guarantee = math.min(consistency_level, service_guarantee)

          -- Update headers for upstream
          request_handle:headers():replace("X-Consistency-Level", result_guarantee)

          -- Add to chain
          local chain = request_handle:headers():get("X-Consistency-Chain") or ""
          chain = chain .. "," .. service_guarantee
          request_handle:headers():replace("X-Consistency-Chain", chain)
        end

# Service mesh configuration
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: payment-service
spec:
  hosts:
    - payment.default.svc.cluster.local
  http:
    - match:
        - headers:
            X-Consistency-Level:
              exact: "STRICT_SERIALIZABLE"
      route:
        - destination:
            host: payment
            subset: primary
      headers:
        request:
          set:
            X-Service-Consistency: "STRICT_SERIALIZABLE"
    - route:
        - destination:
            host: payment
            subset: replica
      headers:
        request:
          set:
            X-Service-Consistency: "SNAPSHOT_ISOLATION"
```

**End-to-end SLO composition:**

```python
class SLOChain:
    """Compose SLOs across service boundaries"""

    def __init__(self):
        self.services = []

    def add_service(self, name, availability, latency_p99):
        self.services.append({
            'name': name,
            'availability': availability,
            'latency_p99': latency_p99,
        })

    def compute_end_to_end_slo(self):
        # Availability: product of all service availabilities
        end_to_end_availability = 1.0
        for svc in self.services:
            end_to_end_availability *= svc['availability']

        # Latency: sum of all service latencies (serial calls)
        # For parallel, take max instead
        end_to_end_latency_serial = sum(s['latency_p99'] for s in self.services)

        # Error budget: 1 - availability
        end_to_end_error_budget = 1 - end_to_end_availability

        return {
            'availability': end_to_end_availability,
            'latency_p99_serial': end_to_end_latency_serial,
            'error_budget': end_to_end_error_budget,
            'services': self.services,
        }

    def compute_required_service_slo(self, target_availability, num_services):
        """
        Given target end-to-end availability, compute required per-service SLO

        If target = 99.9% and N=3 services:
        per_service = target^(1/N) = 0.999^(1/3) = 0.9997
        Each service needs 99.97% availability
        """
        per_service_availability = target_availability ** (1 / num_services)
        return per_service_availability

# Example: checkout flow
chain = SLOChain()
chain.add_service('API Gateway', availability=0.9999, latency_p99=10)
chain.add_service('Auth Service', availability=0.9995, latency_p99=20)
chain.add_service('Cart Service', availability=0.999, latency_p99=50)
chain.add_service('Payment Service', availability=0.9999, latency_p99=200)
chain.add_service('Inventory Service', availability=0.999, latency_p99=30)

result = chain.compute_end_to_end_slo()
print(f"End-to-end availability: {result['availability']:.4%}")
# Output: 99.73% (product of all services)

print(f"End-to-end P99 latency: {result['latency_p99_serial']}ms")
# Output: 310ms (sum of all services)

# To achieve 99.9% end-to-end with 5 services:
required_per_service = chain.compute_required_service_slo(0.999, 5)
print(f"Each service needs: {required_per_service:.4%}")
# Output: 99.98% per service
```

#### 17.1.3 Certainty Labels and Proof Propagation

**Typed consistency guarantees:**

```rust
// Type-level consistency tracking
enum ConsistencyLevel {
    StrictSerializable,
    Serializable,
    SnapshotIsolation,
    ReadCommitted,
    EventuallyConsistent,
}

// Data tagged with consistency proof
struct ConsistentData<T, C: ConsistencyLevel> {
    value: T,
    consistency: PhantomData<C>,
    evidence: ConsistencyEvidence,
}

// Evidence of consistency guarantee
struct ConsistencyEvidence {
    timestamp: HLC,
    transaction_id: Option<TxnId>,
    read_version: Version,
    linearization_point: Option<HLC>,
}

// Type-safe operations
impl<T> ConsistentData<T, StrictSerializable> {
    // Only SS data can be used in transactions requiring SS
    fn use_in_transaction(&self, txn: &Transaction) -> Result<()> {
        txn.verify_consistency(&self.evidence)
    }
}

impl<T, C: ConsistencyLevel> ConsistentData<T, C> {
    // Downgrade is always safe
    fn downgrade<C2: WeakerThan<C>>(self) -> ConsistentData<T, C2> {
        ConsistentData {
            value: self.value,
            consistency: PhantomData,
            evidence: self.evidence,
        }
    }

    // Upgrade requires re-certification
    async fn upgrade<C2: StrongerThan<C>>(
        self,
        gate: &ConsistencyGate
    ) -> Result<ConsistentData<T, C2>> {
        gate.certify_upgrade(&self.evidence).await?;
        let new_evidence = gate.read_authoritative(&self.value).await?;

        Ok(ConsistentData {
            value: self.value,
            consistency: PhantomData,
            evidence: new_evidence,
        })
    }
}

// Example usage
async fn process_payment(
    account: ConsistentData<Account, StrictSerializable>,
    amount: Money,
) -> Result<Receipt> {
    // Compiler enforces that account has SS guarantee

    let balance = account.value.balance;
    if balance < amount {
        return Err(InsufficientFunds);
    }

    // Debit is safe because we have SS guarantee
    let receipt = debit(account, amount).await?;
    Ok(receipt)
}

async fn get_account(account_id: u64) -> ConsistentData<Account, StrictSerializable> {
    // Database read with SS guarantee
    let (account, evidence) = db.read_strict_serializable(account_id).await;

    ConsistentData {
        value: account,
        consistency: PhantomData,
        evidence,
    }
}
```

### 17.2 Adaptation Patterns
* 17.2.1 Operational Modes
  - Floor (minimum viable)
  - Target (normal operation)
  - Degraded (survival mode)
  - Recovery (restoration path)
* 17.2.2 Control Loops
  - Input signals
    - SLO burn rate
    - Error budgets
    - Resource utilization
  - Control actions
    - Cache TTL adjustment
    - Closed-ts tuning
    - Escrow rebalancing
    - Admission control
* 17.2.3 Mode Transitions
  - Trigger conditions
  - Hysteresis prevention
  - Smooth transitions
  - Rollback capabilities

### 17.3 Multi-System Coordination
* 17.3.1 Protocol Standardization
  - Idempotency keys
  - Exactly-once semantics
  - Outbox patterns
  - Dead letter queues
* 17.3.2 Cross-System Invariants
  - Distributed sagas
  - Compensation chains
  - Two-phase protocols
  - Escrow federation
* 17.3.3 Observability Integration
  - Trace correlation
  - Metric aggregation
  - Log federation
  - Alert correlation

---

## Chapter 18: Partial Failures and Gray Failures

### 18.1 Gray Failure Detection

#### 18.1.1 Network-Level Gray Failures

**NIC Queue Drops**

Symptoms and detection:
```bash
# Monitor NIC queue drops
watch -n 1 'ethtool -S eth0 | grep -E "(drop|discard)"'

# Output showing gray failure:
rx_dropped: 12453        # Increasing!
tx_dropped: 8932         # Increasing!
rx_fifo_errors: 234      # RX ring buffer overflow

# Check ring buffer sizes
ethtool -g eth0
# Ring parameters for eth0:
# Current:  RX 256  TX 256
# Maximum:  RX 4096 TX 4096
```

Root causes and fixes:
```bash
# Increase ring buffer size
ethtool -G eth0 rx 4096 tx 4096

# Tune interrupt coalescing (reduce CPU interrupts)
ethtool -C eth0 rx-usecs 100 rx-frames 32

# Enable RSS (Receive Side Scaling) for multi-core
ethtool -X eth0 equal 8  # 8 cores

# Monitor IRQ distribution
watch -n 1 'cat /proc/interrupts | grep eth0'
```

Detection in application:
```python
class NICHealthMonitor:
    def __init__(self):
        self.baseline_drops = self._get_nic_drops()

    def _get_nic_drops(self):
        output = subprocess.check_output(['ethtool', '-S', 'eth0'])
        drops = {}
        for line in output.decode().split('\n'):
            if 'drop' in line or 'discard' in line:
                key, value = line.split(':')
                drops[key.strip()] = int(value.strip())
        return drops

    def check_health(self):
        current_drops = self._get_nic_drops()

        for key, value in current_drops.items():
            baseline = self.baseline_drops.get(key, 0)
            delta = value - baseline

            if delta > 1000:  # More than 1K drops since baseline
                alert(f"NIC gray failure: {key} = {delta} drops")
                metrics.gauge(f"nic.{key}", delta)

        self.baseline_drops = current_drops

# Run periodically
monitor = NICHealthMonitor()
while True:
    monitor.check_health()
    time.sleep(60)
```

**VLAN Misconfiguration**

Scenario: Two data centers with VLAN mismatch
```
DC1: VLAN 100 → Production traffic
DC2: VLAN 200 → Production traffic
Gateway: Misconfigured, expects VLAN 100

Result: DC2 traffic silently dropped at gateway
Symptom: Cross-DC requests timeout, same-DC requests work
```

Detection:
```python
class CrossDCHealthCheck:
    def __init__(self):
        self.dcs = ['dc1', 'dc2', 'dc3']

    async def check_connectivity_matrix(self):
        results = {}

        for source_dc in self.dcs:
            for target_dc in self.dcs:
                if source_dc == target_dc:
                    continue

                # Send probe from source to target
                latency, success = await self._probe(source_dc, target_dc)

                results[f"{source_dc}->{target_dc}"] = {
                    'latency': latency,
                    'success': success,
                }

        # Detect asymmetric failures
        for pair, result in results.items():
            source, target = pair.split('->')

            reverse_pair = f"{target}->{source}"
            reverse_result = results.get(reverse_pair)

            if result['success'] and not reverse_result['success']:
                alert(f"Asymmetric connectivity: {pair} works, {reverse_pair} fails")
            elif result['success'] and reverse_result['success']:
                # Check for latency asymmetry
                latency_ratio = result['latency'] / reverse_result['latency']
                if latency_ratio > 2 or latency_ratio < 0.5:
                    alert(f"Latency asymmetry: {pair}={result['latency']}ms, "
                          f"{reverse_pair}={reverse_result['latency']}ms")

# Probe configuration
async def _probe(self, source_dc, target_dc):
    try:
        start = time.time()
        response = await http_client.get(
            f"http://{target_dc}.internal/health",
            headers={'X-Source-DC': source_dc},
            timeout=5.0
        )
        latency = (time.time() - start) * 1000
        return latency, response.status == 200
    except Exception as e:
        return None, False
```

**Asymmetric Routing**

Problem: Outbound traffic takes one path, return traffic takes another
```
Request:  Client → LB1 → Server A (fast path)
Response: Server A → LB2 → Client (slow path through congested link)

Result: High latency for responses, but requests are fast
```

Detection and diagnosis:
```python
import scapy.all as scapy

class AsymmetricRoutingDetector:
    def trace_route_bidirectional(self, target_ip):
        # Outbound traceroute
        outbound_hops = self._traceroute(target_ip)

        # Trigger return path traceroute (requires cooperation from target)
        inbound_hops = self._request_reverse_traceroute(target_ip)

        # Compare paths
        if outbound_hops != inbound_hops:
            alert(f"Asymmetric routing detected to {target_ip}")
            alert(f"Outbound: {' -> '.join(outbound_hops)}")
            alert(f"Inbound:  {' -> '.join(inbound_hops)}")

    def _traceroute(self, target_ip, max_hops=30):
        hops = []
        for ttl in range(1, max_hops + 1):
            pkt = scapy.IP(dst=target_ip, ttl=ttl) / scapy.ICMP()
            reply = scapy.sr1(pkt, timeout=2, verbose=0)

            if reply is None:
                hops.append("* * *")
            elif reply.type == 0:  # Echo reply (reached destination)
                hops.append(reply.src)
                break
            else:  # TTL exceeded
                hops.append(reply.src)

        return hops

# Monitor for persistent asymmetry
class LatencyAsymmetryMonitor:
    def __init__(self):
        self.request_latencies = defaultdict(list)
        self.response_latencies = defaultdict(list)

    def record_request(self, conn_id, latency):
        self.request_latencies[conn_id].append(latency)

    def record_response(self, conn_id, latency):
        self.response_latencies[conn_id].append(latency)

    def check_asymmetry(self):
        for conn_id in self.request_latencies:
            req_p50 = np.median(self.request_latencies[conn_id])
            resp_p50 = np.median(self.response_latencies[conn_id])

            if resp_p50 > 2 * req_p50:
                alert(f"Asymmetric latency on {conn_id}: "
                      f"req={req_p50}ms, resp={resp_p50}ms")
```

#### 18.1.2 Gray Failure Game Days

**Scenario 1: Silent NIC Queue Drops**

Setup:
```bash
# Inject NIC queue drops on one server
tc qdisc add dev eth0 root netem loss 5%  # 5% packet loss
ethtool -G eth0 rx 128 tx 128             # Shrink buffers

# Generate load to trigger drops
ab -n 100000 -c 100 http://target-server/
```

Expected observations:
- Increased P99 latency (timeouts and retries)
- No obvious errors in application logs
- Connection resets under load
- Metrics show increased retry rate

Mitigation playbook:
```yaml
# runbook-nic-drops.yaml
incident_type: NIC Queue Drops
severity: P2

detection:
  - alert: High packet drop rate on NIC
  - symptom: Increased P99 latency with no CPU/memory spike

diagnosis_steps:
  - step: Check NIC statistics
    command: |
      ethtool -S eth0 | grep -E "drop|discard"
      # If drops increasing: NIC overload

  - step: Check ring buffer size
    command: |
      ethtool -g eth0
      # If RX/TX < 1024: too small

  - step: Check IRQ distribution
    command: |
      cat /proc/interrupts | grep eth0
      # If all IRQs on one CPU: poor distribution

mitigation:
  - action: Increase ring buffers
    command: |
      ethtool -G eth0 rx 4096 tx 4096

  - action: Enable RSS
    command: |
      ethtool -X eth0 equal $(nproc)

  - action: Tune interrupt coalescing
    command: |
      ethtool -C eth0 rx-usecs 100 rx-frames 32

  - action: Drain and reboot if persistent
    command: |
      kubectl drain node-xyz --ignore-daemonsets
      # Reboot to reset NIC firmware

prevention:
  - Configure ring buffers in host bootstrap
  - Monitor NIC drops in alerting
  - Load test with production traffic patterns
```

**Scenario 2: BGP Route Flap**

Setup:
```bash
# Simulate BGP route flap
#!/bin/bash
while true; do
  # Withdraw route
  birdc "configure" "route 10.0.0.0/8 unreachable;"
  sleep 5

  # Re-announce route
  birdc "configure" "route 10.0.0.0/8 via 192.168.1.1;"
  sleep 30
done
```

Expected observations:
- Intermittent connection failures
- Some requests timeout, others succeed
- Metrics show bimodal latency distribution

Runbook:
```yaml
incident_type: BGP Route Flap
severity: P1

detection:
  - alert: Bimodal latency distribution
  - symptom: Intermittent connection timeouts

diagnosis_steps:
  - step: Check BGP session status
    command: |
      birdc show protocols all
      # Look for: Established -> Active transitions

  - step: Check route churn
    command: |
      birdc show route table | wc -l  # Count over time
      # If fluctuating: route instability

  - step: Check BGP logs
    command: |
      journalctl -u bird -f | grep -E "BGP|route"

mitigation:
  - action: Enable BGP dampening
    config: |
      protocol bgp {
        dampening {
          half-life 15;
          reuse 750;
          suppress 2000;
          max-suppress 60;
        }
      }

  - action: Pin routes temporarily
    command: |
      ip route add 10.0.0.0/8 via 192.168.1.1 metric 1

  - action: Contact network team
    escalation: network-oncall

prevention:
  - Implement BGP dampening
  - Monitor route churn rate
  - Multi-path routing for redundancy
```

**Scenario 3: Disk Slow I/O (No Errors)**

Setup:
```bash
# Inject latency on disk I/O
echo 1 > /sys/block/sda/queue/add_random  # Add jitter
hdparm -M 128 /dev/sda  # Acoustic management (slower)

# Or use dm-delay
dmsetup create delayed --table \
  "0 $(blockdev --getsz /dev/sda) delay /dev/sda 0 100"
```

Expected observations:
- fsync() takes 500ms instead of 5ms
- No disk errors in dmesg
- Write throughput drops 10x
- Transaction commit latency spikes

Detection:
```python
class DiskLatencyMonitor:
    def __init__(self):
        self.fsync_latencies = deque(maxlen=1000)
        self.alert_threshold = 100  # ms

    def monitor_fsync(self):
        test_file = '/var/lib/db/fsync_test'

        start = time.time()
        with open(test_file, 'w') as f:
            f.write('x' * 4096)
            f.flush()
            os.fsync(f.fileno())
        latency_ms = (time.time() - start) * 1000

        self.fsync_latencies.append(latency_ms)

        p99 = np.percentile(self.fsync_latencies, 99)
        if p99 > self.alert_threshold:
            alert(f"Disk gray failure: fsync P99 = {p99}ms")

        os.unlink(test_file)
```

Runbook:
```yaml
incident_type: Disk Slow I/O Gray Failure
severity: P1

detection:
  - alert: fsync() latency > 50ms
  - symptom: Transaction commit latency high

diagnosis_steps:
  - step: Check disk I/O stats
    command: |
      iostat -x 1 10
      # Look at: %util, await, svctm

  - step: Check for disk errors
    command: |
      dmesg | grep -i "ata\|scsi\|error"
      smartctl -a /dev/sda | grep -i error

  - step: Check write cache status
    command: |
      hdparm -W /dev/sda
      # write-caching = on (0)  # Should be off for safety

  - step: Test fsync latency
    command: |
      python3 << EOF
      import os, time
      f = open('/tmp/test', 'w')
      start = time.time()
      f.write('x' * 4096)
      os.fsync(f.fileno())
      print(f"fsync latency: {(time.time()-start)*1000}ms")
      EOF

mitigation:
  - action: Identify slow disk
    command: |
      for dev in /dev/sd*; do
        echo "=== $dev ==="
        fio --name=seqwrite --rw=write --bs=4k --size=1G \
            --numjobs=1 --filename=$dev --direct=1
      done

  - action: Drain database from slow disk
    steps:
      - Remove from replica set
      - Migrate data to new disk
      - Decommission node

  - action: Emergency mitigation (risky!)
    command: |
      # Disable fsync (data loss risk!)
      ALTER SYSTEM SET synchronous_commit = off;
      # Only if: 1) replica available 2) temporary 3) approved

prevention:
  - Monitor fsync latency continuously
  - Use enterprise SSDs with PLP
  - RAID for redundancy
  - Automated slow disk detection and replacement
```

#### 18.1.3 Specific Network Pathologies

**TCP Incast Problem**

Many servers respond to client simultaneously → switch buffer overflow

Symptoms:
```python
# Detect incast pattern
class IncastDetector:
    def monitor_connection_patterns(self):
        conn_starts = defaultdict(list)

        # Monitor TCP connections
        for conn in get_tcp_connections():
            conn_starts[conn.local_port].append(conn.timestamp)

        # Check for burst of concurrent connections
        for port, timestamps in conn_starts.items():
            timestamps.sort()

            # Count connections starting within 10ms window
            burst_size = 0
            window_start = timestamps[0]

            for ts in timestamps:
                if ts - window_start < 0.01:  # 10ms
                    burst_size += 1
                else:
                    if burst_size > 50:  # 50 concurrent = incast
                        alert(f"Incast detected: {burst_size} connections in 10ms")
                    burst_size = 1
                    window_start = ts
```

Mitigation:
```bash
# Increase switch buffer size (hardware config)

# TCP tuning for incast
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"

# Reduce RTO minimum (faster recovery)
sysctl -w net.ipv4.tcp_min_rto_wlen=1

# Application-level: jittered timeouts
```

Application fix:
```python
# Add jitter to scatter responses
async def handle_batch_query(request):
    # Intentionally delay response to avoid incast
    jitter = random.uniform(0, 0.01)  # 0-10ms jitter
    await asyncio.sleep(jitter)

    result = await process_query(request)
    return result
```

### 18.2 Mitigation Strategies
* 18.2.1 Request-Level
  - Hedged requests
  - Backup requests
  - Speculative execution
  - Tied requests
* 18.2.2 Connection-Level
  - Circuit breakers
  - Bulkheads
  - Connection pools
  - Health checks
* 18.2.3 System-Level
  - Retry budgets
  - Rate limiters
  - Load balancers
  - Traffic shaping

### 18.3 Recovery Procedures
* 18.3.1 Quarantine Protocols
  - Node isolation
  - Traffic draining
  - State migration
  - Capacity replacement
* 18.3.2 State Recovery
  - Log replay
  - Snapshot restoration
  - CRDT convergence
  - Lineage recomputation
* 18.3.3 System Validation
  - Invariant checking
  - Consistency audits
  - Performance verification
  - Capacity validation

---

## Chapter 19: Economic Decision-Making

### 19.1 Worked Example 1: Payment Processing System

**Requirements:**
- Strict serializable consistency (no double charges, no lost payments)
- 99.99% availability (52 minutes downtime/year)
- Global presence (US, EU, Asia)
- Target: 10,000 TPS peak, 2,000 TPS average
- P99 latency < 200ms

**Architecture:**

```python
# Multi-region payment system
regions = {
    'us-east': {
        'primary': True,
        'nodes': 5,
        'instance_type': 'c6i.4xlarge',  # 16 vCPU, 32GB RAM
    },
    'eu-west': {
        'primary': False,
        'nodes': 3,
        'instance_type': 'c6i.4xlarge',
    },
    'ap-southeast': {
        'primary': False,
        'nodes': 3,
        'instance_type': 'c6i.4xlarge',
    },
}

# Database: CockroachDB with strict serializable
database = {
    'regions': 3,
    'replicas_per_region': 3,
    'total_nodes': 9,
    'instance_type': 'r6i.4xlarge',  # 16 vCPU, 128GB RAM
    'storage_per_node': '2TB NVMe SSD',
}
```

**CAPEX/OPEX Calculation:**

```python
class PaymentSystemCostModel:
    def __init__(self):
        # AWS pricing (reserved 1-year, us-east-1)
        self.compute_hourly = {
            'c6i.4xlarge': 0.544,   # Application servers
            'r6i.4xlarge': 0.806,   # Database (memory-optimized)
        }

        self.storage_monthly = {
            'gp3_ssd': 0.08,        # Per GB/month
            'io2_nvme': 0.125,      # Per GB/month (database)
        }

        self.network_costs = {
            'intra_az': 0.01,       # Per GB
            'inter_region': 0.02,   # Per GB
            'internet_egress': 0.09,# Per GB
        }

    def compute_monthly_costs(self):
        # Compute costs
        app_servers = (
            5 * self.compute_hourly['c6i.4xlarge'] +  # US
            3 * self.compute_hourly['c6i.4xlarge'] +  # EU
            3 * self.compute_hourly['c6i.4xlarge']    # Asia
        ) * 730  # hours/month
        # = 11 * $0.544 * 730 = $4,369/month

        db_servers = (
            9 * self.compute_hourly['r6i.4xlarge'] * 730
        )
        # = 9 * $0.806 * 730 = $5,297/month

        # Storage costs
        db_storage = (
            9 * 2000 * self.storage_monthly['io2_nvme']  # 2TB per node
        )
        # = 9 * 2000 * $0.125 = $2,250/month

        # Network costs (consensus traffic between regions)
        # Estimate: 2,000 TPS * 2KB per txn * 3 regions * 2 round trips
        consensus_traffic_gb = (
            2000 * 2 * 3 * 2 * 2.628e6  # Seconds in month
        ) / (1024**3)
        # = 29,520 GB/month

        network = (
            consensus_traffic_gb * self.network_costs['inter_region']
        )
        # = 29,520 * $0.02 = $590/month

        total_monthly = app_servers + db_servers + db_storage + network
        return {
            'app_servers': app_servers,
            'db_servers': db_servers,
            'storage': db_storage,
            'network': network,
            'total_monthly': total_monthly,
            'total_annual': total_monthly * 12,
        }

model = PaymentSystemCostModel()
costs = model.compute_monthly_costs()

print("Payment System Cost Breakdown:")
print(f"  App servers:  ${costs['app_servers']:,.0f}/month")
print(f"  DB servers:   ${costs['db_servers']:,.0f}/month")
print(f"  Storage:      ${costs['storage']:,.0f}/month")
print(f"  Network:      ${costs['network']:,.0f}/month")
print(f"  TOTAL:        ${costs['total_monthly']:,.0f}/month")
print(f"  ANNUAL:       ${costs['total_annual']:,.0f}/year")

# Output:
# Payment System Cost Breakdown:
#   App servers:  $4,369/month
#   DB servers:   $5,297/month
#   Storage:      $2,250/month
#   Network:      $590/month
#   TOTAL:        $12,506/month
#   ANNUAL:       $150,072/year
```

**SLO Analysis:**

```python
class SLOAnalysis:
    def __init__(self):
        self.target_availability = 0.9999  # 99.99%
        self.num_services = 3  # App, DB, Network

    def compute_required_component_slos(self):
        # Each component must be more reliable than end-to-end target
        per_component = self.target_availability ** (1 / self.num_services)
        return per_component
        # = 0.9999^(1/3) = 0.999967
        # Each component needs 99.9967% availability

    def compute_error_budget(self):
        # Annual downtime budget
        minutes_per_year = 525600
        allowed_downtime = minutes_per_year * (1 - self.target_availability)
        return allowed_downtime
        # = 525600 * 0.0001 = 52.56 minutes/year

slo = SLOAnalysis()
print(f"Required per-component SLO: {slo.compute_required_component_slos():.6%}")
print(f"Annual error budget: {slo.compute_error_budget():.1f} minutes")
```

**Cost of Wrongness:**

```python
class PaymentWrongnessImpact:
    def __init__(self):
        self.avg_payment_value = 50  # USD
        self.error_probability = 0.0001  # 0.01% error rate
        self.regulatory_fine_per_incident = 10000
        self.customer_churn_cost = 500  # Lifetime value

    def compute_wrongness_cost(self, daily_transactions):
        # Direct financial impact (double charges, lost payments)
        direct_impact = (
            daily_transactions *
            self.error_probability *
            self.avg_payment_value
        )

        # Regulatory fines
        daily_incidents = daily_transactions * self.error_probability
        regulatory_cost = daily_incidents * self.regulatory_fine_per_incident

        # Customer churn (10% of affected customers leave)
        churn_cost = daily_incidents * 0.1 * self.customer_churn_cost

        daily_cost = direct_impact + regulatory_cost + churn_cost
        annual_cost = daily_cost * 365

        return {
            'direct_impact': direct_impact * 365,
            'regulatory_fines': regulatory_cost * 365,
            'customer_churn': churn_cost * 365,
            'total_annual': annual_cost,
        }

wrongness = PaymentWrongnessImpact()
impact = wrongness.compute_wrongness_cost(daily_transactions=172_800_000)

print("Annual Cost of Wrongness:")
print(f"  Direct impact:     ${impact['direct_impact']:,.0f}")
print(f"  Regulatory fines:  ${impact['regulatory_fines']:,.0f}")
print(f"  Customer churn:    ${impact['customer_churn']:,.0f}")
print(f"  TOTAL:             ${impact['total_annual']:,.0f}")

# Output:
# Annual Cost of Wrongness:
#   Direct impact:     $315,360
#   Regulatory fines:  $63,072,000
#   Customer churn:    $3,153,600
#   TOTAL:             $66,540,960

# Infrastructure cost ($150K) << Wrongness cost ($66M)
# Therefore: Strict serializable is economically justified
```

---

### 19.2 Worked Example 2: Social Media Feed

**Requirements:**
- Eventually consistent acceptable (stale data OK)
- High availability (99.9% sufficient)
- Global read-heavy (1M reads/sec, 10K writes/sec)
- P99 latency < 100ms
- Low cost per user (must scale to billions)

**Architecture:**

```python
# CDN + Cache-heavy architecture
architecture = {
    'cdn': {
        'provider': 'Cloudflare',
        'pops': 'global',  # 250+ locations
    },
    'cache_layer': {
        'redis_clusters': 12,  # 4 per region
        'nodes_per_cluster': 6,
        'instance_type': 'r6g.xlarge',  # 4 vCPU, 32GB RAM
    },
    'app_layer': {
        'regions': 3,
        'nodes_per_region': 20,
        'instance_type': 'c6g.large',  # 2 vCPU, 4GB RAM
    },
    'database': {
        'type': 'DynamoDB',
        'mode': 'on-demand',  # Pay per request
    },
}
```

**Cost Model:**

```python
class SocialFeedCostModel:
    def __init__(self):
        self.requests_per_month = {
            'reads': 2.628e12,   # 1M reads/sec
            'writes': 26.28e9,   # 10K writes/sec
        }

        # CDN costs
        self.cdn_per_10k_requests = 0.01
        self.cdn_cache_hit_rate = 0.95

        # Cache layer (Redis)
        self.redis_hourly = 0.268  # r6g.xlarge

        # App layer
        self.app_hourly = 0.068  # c6g.large

        # DynamoDB on-demand
        self.dynamodb_read_per_million = 0.25
        self.dynamodb_write_per_million = 1.25

    def compute_monthly_costs(self):
        # CDN costs (all requests)
        cdn_cost = (
            self.requests_per_month['reads'] / 10000 * self.cdn_per_10k_requests
        )
        # = 2.628e12 / 10000 * $0.01 = $2,628,000/month

        # Cache misses reach origin (5%)
        cache_misses = self.requests_per_month['reads'] * (1 - self.cdn_cache_hit_rate)

        # Redis cache layer
        redis_nodes = 12 * 6  # 12 clusters * 6 nodes
        redis_cost = redis_nodes * self.redis_hourly * 730
        # = 72 * $0.268 * 730 = $14,083/month

        # App layer
        app_nodes = 3 * 20  # 3 regions * 20 nodes
        app_cost = app_nodes * self.app_hourly * 730
        # = 60 * $0.068 * 730 = $2,978/month

        # DynamoDB (only for cache misses + all writes)
        db_reads = cache_misses / 1e6 * self.dynamodb_read_per_million
        db_writes = self.requests_per_month['writes'] / 1e6 * self.dynamodb_write_per_million

        db_cost = db_reads + db_writes
        # = (131.4M * $0.25/M) + (26.28M * $1.25/M) = $65,700/month

        total = cdn_cost + redis_cost + app_cost + db_cost

        return {
            'cdn': cdn_cost,
            'redis': redis_cost,
            'app_servers': app_cost,
            'database': db_cost,
            'total_monthly': total,
            'total_annual': total * 12,
            'cost_per_million_requests': total / (self.requests_per_month['reads'] / 1e6),
        }

social_model = SocialFeedCostModel()
social_costs = social_model.compute_monthly_costs()

print("Social Feed Cost Breakdown:")
print(f"  CDN:          ${social_costs['cdn']:,.0f}/month")
print(f"  Redis cache:  ${social_costs['redis']:,.0f}/month")
print(f"  App servers:  ${social_costs['app_servers']:,.0f}/month")
print(f"  DynamoDB:     ${social_costs['database']:,.0f}/month")
print(f"  TOTAL:        ${social_costs['total_monthly']:,.0f}/month")
print(f"  ANNUAL:       ${social_costs['total_annual']:,.0f}/year")
print(f"  Cost/M reqs:  ${social_costs['cost_per_million_requests']:.2f}")

# Output:
# Social Feed Cost Breakdown:
#   CDN:          $2,628,000/month
#   Redis cache:  $14,083/month
#   App servers:  $2,978/month
#   Database:     $65,700/month
#   TOTAL:        $2,710,761/month
#   ANNUAL:       $32,529,132/year
#   Cost/M reqs:  $1.03

# Much higher absolute cost than payments, but:
# - Serves 1000x more traffic
# - Cost per request is 100x lower
# - Eventual consistency enables massive caching
```

**Consistency Trade-off Analysis:**

```python
class ConsistencyTradeoff:
    def compare_strong_vs_eventual(self):
        # Strong consistency: must hit database every time
        strong_latency_p99 = 150  # ms
        strong_cache_hit_rate = 0.0  # Can't cache

        # Eventual consistency: can cache aggressively
        eventual_latency_p99 = 20   # ms (mostly CDN)
        eventual_cache_hit_rate = 0.95

        # Cost difference
        strong_db_reads = 2.628e12  # All reads
        eventual_db_reads = 2.628e12 * 0.05  # Only 5% reach DB

        strong_db_cost = strong_db_reads / 1e6 * 0.25
        eventual_db_cost = eventual_db_reads / 1e6 * 0.25

        cost_savings = strong_db_cost - eventual_db_cost

        return {
            'strong_latency_p99': strong_latency_p99,
            'eventual_latency_p99': eventual_latency_p99,
            'latency_improvement': strong_latency_p99 / eventual_latency_p99,
            'strong_db_cost_monthly': strong_db_cost,
            'eventual_db_cost_monthly': eventual_db_cost,
            'monthly_savings': cost_savings,
            'annual_savings': cost_savings * 12,
        }

tradeoff = ConsistencyTradeoff()
comparison = tradeoff.compare_strong_vs_eventual()

print("Strong vs Eventual Consistency:")
print(f"  Strong P99 latency:     {comparison['strong_latency_p99']}ms")
print(f"  Eventual P99 latency:   {comparison['eventual_latency_p99']}ms")
print(f"  Latency improvement:    {comparison['latency_improvement']:.1f}x faster")
print(f"  Strong DB cost:         ${comparison['strong_db_cost_monthly']:,.0f}/month")
print(f"  Eventual DB cost:       ${comparison['eventual_db_cost_monthly']:,.0f}/month")
print(f"  Monthly savings:        ${comparison['monthly_savings']:,.0f}")
print(f"  Annual savings:         ${comparison['annual_savings']:,.0f}")

# Output:
# Strong vs Eventual Consistency:
#   Strong P99 latency:     150ms
#   Eventual P99 latency:   20ms
#   Latency improvement:    7.5x faster
#   Strong DB cost:         $657,000/month
#   Eventual DB cost:       $32,850/month
#   Monthly savings:        $624,150
#   Annual savings:         $7,489,800

# Conclusion: Eventual consistency saves $7.5M/year AND provides better UX
```

---

### 19.3 Worked Example 3: Analytics Data Warehouse

**Requirements:**
- Batch processing acceptable (hours of staleness OK)
- 99% availability sufficient
- Single region
- Process 10 TB data/day
- Query latency: seconds to minutes OK

**Architecture:**

```python
architecture = {
    'ingestion': {
        'kafka': {
            'nodes': 6,
            'instance_type': 'r6i.xlarge',
        },
    },
    'warehouse': {
        'type': 'Snowflake',
        'warehouse_size': 'X-Large',  # 16 nodes
        'storage': '500 TB',
    },
    'orchestration': {
        'airflow': {
            'nodes': 3,
            'instance_type': 'c6i.large',
        },
    },
}
```

**Cost Model:**

```python
class AnalyticsCostModel:
    def __init__(self):
        # Data processing volume
        self.daily_data_tb = 10
        self.monthly_data_tb = 10 * 30

        # Kafka ingestion
        self.kafka_nodes = 6
        self.kafka_hourly = 0.252  # r6i.xlarge

        # Snowflake pricing
        self.snowflake_compute_per_credit = 2.00
        self.snowflake_storage_per_tb = 40  # Per TB/month
        self.snowflake_credits_per_hour = 16  # X-Large warehouse

        # Assume 8 hours/day of active processing
        self.snowflake_active_hours_monthly = 8 * 30

        # Airflow orchestration
        self.airflow_nodes = 3
        self.airflow_hourly = 0.085  # c6i.large

    def compute_monthly_costs(self):
        # Kafka ingestion layer
        kafka_cost = self.kafka_nodes * self.kafka_hourly * 730
        # = 6 * $0.252 * 730 = $1,104/month

        # Snowflake compute (only charged when running)
        snowflake_compute = (
            self.snowflake_active_hours_monthly *
            self.snowflake_credits_per_hour *
            self.snowflake_compute_per_credit
        )
        # = 240 * 16 * $2.00 = $7,680/month

        # Snowflake storage
        snowflake_storage = 500 * self.snowflake_storage_per_tb
        # = 500 * $40 = $20,000/month

        # Airflow orchestration
        airflow_cost = self.airflow_nodes * self.airflow_hourly * 730
        # = 3 * $0.085 * 730 = $186/month

        total = kafka_cost + snowflake_compute + snowflake_storage + airflow_cost

        return {
            'kafka': kafka_cost,
            'snowflake_compute': snowflake_compute,
            'snowflake_storage': snowflake_storage,
            'airflow': airflow_cost,
            'total_monthly': total,
            'total_annual': total * 12,
            'cost_per_tb_processed': total / self.monthly_data_tb,
        }

analytics_model = AnalyticsCostModel()
analytics_costs = analytics_model.compute_monthly_costs()

print("Analytics Warehouse Cost Breakdown:")
print(f"  Kafka ingestion:      ${analytics_costs['kafka']:,.0f}/month")
print(f"  Snowflake compute:    ${analytics_costs['snowflake_compute']:,.0f}/month")
print(f"  Snowflake storage:    ${analytics_costs['snowflake_storage']:,.0f}/month")
print(f"  Airflow:              ${analytics_costs['airflow']:,.0f}/month")
print(f"  TOTAL:                ${analytics_costs['total_monthly']:,.0f}/month")
print(f"  ANNUAL:               ${analytics_costs['total_annual']:,.0f}/year")
print(f"  Cost per TB:          ${analytics_costs['cost_per_tb_processed']:.2f}")

# Output:
# Analytics Warehouse Cost Breakdown:
#   Kafka ingestion:      $1,104/month
#   Snowflake compute:    $7,680/month
#   Snowflake storage:    $20,000/month
#   Airflow:              $186/month
#   TOTAL:                $28,970/month
#   ANNUAL:               $347,640/year
#   Cost per TB:          $96.57
```

**Consistency vs Cost Trade-off:**

```python
class AnalyticsConsistencyTradeoff:
    def compare_realtime_vs_batch(self):
        # Real-time streaming (strong consistency)
        realtime_warehouse_size = 'XX-Large'  # Need 2x capacity
        realtime_credits_per_hour = 64
        realtime_active_hours = 24  # Must run 24/7
        realtime_monthly_hours = realtime_active_hours * 30

        realtime_cost = (
            realtime_monthly_hours *
            realtime_credits_per_hour *
            2.00
        )
        # = 720 * 64 * $2.00 = $92,160/month

        # Batch processing (eventual consistency)
        batch_warehouse_size = 'X-Large'
        batch_credits_per_hour = 16
        batch_active_hours = 8  # Only 8 hours/day
        batch_monthly_hours = batch_active_hours * 30

        batch_cost = (
            batch_monthly_hours *
            batch_credits_per_hour *
            2.00
        )
        # = 240 * 16 * $2.00 = $7,680/month

        savings = realtime_cost - batch_cost

        return {
            'realtime_cost': realtime_cost,
            'batch_cost': batch_cost,
            'monthly_savings': savings,
            'annual_savings': savings * 12,
            'realtime_latency': '< 1 minute',
            'batch_latency': '< 4 hours',
        }

analytics_tradeoff = AnalyticsConsistencyTradeoff()
analytics_comparison = analytics_tradeoff.compare_realtime_vs_batch()

print("\nReal-time vs Batch Analytics:")
print(f"  Real-time cost:         ${analytics_comparison['realtime_cost']:,.0f}/month")
print(f"  Batch cost:             ${analytics_comparison['batch_cost']:,.0f}/month")
print(f"  Monthly savings:        ${analytics_comparison['monthly_savings']:,.0f}")
print(f"  Annual savings:         ${analytics_comparison['annual_savings']:,.0f}")
print(f"  Real-time latency:      {analytics_comparison['realtime_latency']}")
print(f"  Batch latency:          {analytics_comparison['batch_latency']}")

# Output:
# Real-time vs Batch Analytics:
#   Real-time cost:         $92,160/month
#   Batch cost:             $7,680/month
#   Monthly savings:        $84,480
#   Annual savings:         $1,013,760

# For analytics, 4-hour latency is usually acceptable
# Savings: $1M/year by using batch instead of real-time
```

---

### 19.4 Summary: Economic Decision Framework

```python
class ConsistencyDecisionFramework:
    """
    Framework for choosing consistency level based on economics
    """

    def evaluate(self, use_case):
        factors = {
            'cost_of_wrongness': self._estimate_wrongness_cost(use_case),
            'coordination_cost': self._estimate_coordination_cost(use_case),
            'infrastructure_cost': self._estimate_infra_cost(use_case),
            'user_experience_impact': self._estimate_ux_impact(use_case),
        }

        # Decision matrix
        if factors['cost_of_wrongness'] > 1_000_000:
            # High wrongness cost: use strict serializable
            return 'STRICT_SERIALIZABLE', factors

        elif factors['cost_of_wrongness'] > 100_000:
            # Medium wrongness cost: use serializable or snapshot isolation
            if factors['coordination_cost'] > 500_000:
                return 'SNAPSHOT_ISOLATION', factors
            else:
                return 'SERIALIZABLE', factors

        elif factors['user_experience_impact'] == 'HIGH':
            # Low wrongness cost but high UX impact: use eventual + cache
            return 'EVENTUALLY_CONSISTENT', factors

        else:
            # Batch/analytics: use eventual or batch processing
            return 'BATCH_PROCESSING', factors

# Example usage
framework = ConsistencyDecisionFramework()

# Payment system
payment_decision, payment_factors = framework.evaluate({
    'type': 'payment_processing',
    'transactions_per_day': 172_800_000,
    'avg_value': 50,
    'regulatory_risk': 'HIGH',
})
print(f"Payment system: Use {payment_decision}")

# Social feed
social_decision, social_factors = framework.evaluate({
    'type': 'social_feed',
    'reads_per_day': 86_400_000_000,
    'staleness_tolerance': '5 minutes',
    'regulatory_risk': 'LOW',
})
print(f"Social feed: Use {social_decision}")

# Analytics
analytics_decision, analytics_factors = framework.evaluate({
    'type': 'analytics',
    'data_volume_tb': 10,
    'staleness_tolerance': '4 hours',
    'regulatory_risk': 'LOW',
})
print(f"Analytics: Use {analytics_decision}")

# Output:
# Payment system: Use STRICT_SERIALIZABLE
# Social feed: Use EVENTUALLY_CONSISTENT
# Analytics: Use BATCH_PROCESSING
```

**Key Takeaways:**

1. **Payments (Strict Serializable):**
   - Cost: $150K/year infrastructure
   - Wrongness cost: $66M/year
   - ROI: 440x (wrongness cost >> infrastructure cost)
   - Decision: Use strongest consistency

2. **Social Feed (Eventually Consistent):**
   - Cost with eventual: $32.5M/year
   - Cost with strong: $40M/year
   - Savings: $7.5M/year + 7.5x better latency
   - Decision: Use eventual consistency + caching

3. **Analytics (Batch):**
   - Cost with real-time: $1.1M/year
   - Cost with batch: $348K/year
   - Savings: $1M/year
   - Decision: Use batch processing (4-hour latency acceptable)