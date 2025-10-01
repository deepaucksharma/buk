# When Orchestration Fails: Cascading Failures and Recovery Strategies

## Introduction: The Illusion of Automation

In 2017, an engineer at GitLab accidentally deleted a production database. They expected replication to save them. It didn't—replication had been failing silently for weeks. 300GB of production data vanished.

The same year, an AWS S3 outage in us-east-1 took down a third of the internet. Not because of S3 itself, but because **S3 stored the health check data for AWS's own load balancers**. The load balancers couldn't check health. They assumed everything was down. They stopped routing traffic. Services that had nothing to do with S3 became unavailable.

These weren't failures of individual components. They were **failures of orchestration**—the complex dance of automation that keeps distributed systems running. When orchestration fails, the systems designed to provide reliability instead multiply failures.

### The Orchestration Paradox

Orchestration systems promise:
- Automatic failover (if a node dies, workload moves)
- Self-healing (if a container crashes, restart it)
- Resource optimization (pack workloads efficiently)
- High availability (tolerate failures)

But orchestration introduces:
- **New failure modes:** Controllers can crash, schedulers can bug out, state can corrupt
- **Cascading failures:** One failure triggers others exponentially
- **Emergent behavior:** Interactions create unexpected outcomes
- **Operational complexity:** More moving parts = more things to break

**The mental shift:** Orchestration doesn't eliminate failure. It **transforms** failure—from simple, localized problems into complex, distributed, cascading problems.

### What We'll Cover

This chapter examines:
1. **Cascading failures:** How small failures snowball
2. **Split-brain scenarios:** When consensus breaks
3. **Resource exhaustion:** When the cluster runs out of capacity
4. **Scheduler bugs:** When placement goes wrong
5. **Network policies gone wrong:** When security blocks critical traffic
6. **Recovery strategies:** How to recover when orchestration fails

Each section includes real production incidents, root causes, and prevention strategies.

## Cascading Failures: The Domino Effect

A cascading failure is when one failure triggers others, exponentially.

### Anatomy of a Cascade

```
Initial Failure → Secondary Failures → Tertiary Failures → System-Wide Failure
     (1 node)      (5 nodes)            (all nodes)          (total outage)
```

**Classic cascade:**

```
1. Node A fails (hardware issue)
   ↓
2. Pods on Node A marked for eviction
   ↓
3. Scheduler places pods on remaining nodes
   ↓
4. Remaining nodes now overloaded
   ↓
5. Overloaded nodes trigger OOM killer
   ↓
6. OOM kills pods (including critical system pods)
   ↓
7. Kubernetes detects pod failures
   ↓
8. Kubernetes tries to reschedule pods
   ↓
9. No capacity available (all nodes overloaded)
   ↓
10. More pods killed due to resource pressure
    ↓
11. Positive feedback loop (death spiral)
    ↓
12. Cluster becomes unusable
```

### Real Incident: The Black Friday Death Spiral (E-commerce Company, 2020)

**Setup:**
- 100-node Kubernetes cluster
- 2000 pods running (avg 20 pods/node)
- Black Friday: 10× traffic spike expected

**Timeline:**

**11:00 PM (Day before):**
- Engineering team scales up: 2000 → 3000 pods
- Horizontal Pod Autoscaler (HPA) configured for additional scaling

**12:00 AM (Black Friday starts):**
- Traffic spike begins
- HPA triggers: scale from 3000 to 5000 pods

**12:05 AM:**
- Scheduler places 2000 new pods
- Distribution uneven (bug in scheduler scoring)
- 10 nodes receive 100+ pods each (should be ~50 each)

**12:10 AM:**
- Overloaded nodes hit memory limits
- OOM killer starts terminating pods
- HPA sees pods dying → scales up more
- More pods scheduled → more overload

**12:15 AM:**
- 10 overloaded nodes become NotReady (kubelet crashes)
- 1000 pods evicted from those nodes
- Scheduler tries to place 1000 pods on 90 remaining nodes

**12:20 AM:**
- Remaining nodes can't handle 1000 additional pods
- Resource pressure spreads to all nodes
- More nodes become NotReady
- Cascading failure in full effect

**12:30 AM:**
- 40 nodes NotReady
- etcd under extreme load (constant pod status updates)
- API server overwhelmed (thousands of watch events/sec)
- Control plane degraded

**12:45 AM:**
- etcd request timeouts spike
- API server can't write to etcd
- New pods stuck in Pending (can't be scheduled)
- Existing pods can't update status
- Cluster effectively frozen

**1:00 AM:**
- Total outage
- Site down
- $2M in lost sales (first hour of Black Friday)

**Recovery:**
- Stop HPA (prevent more scaling)
- Manually drain overloaded nodes
- Force delete pods (bypass API server)
- Restart kubelet on recovered nodes
- Gradually restore traffic
- Total recovery time: 2 hours

**Root cause:**
1. **Scheduler bug:** Uneven pod distribution
2. **No pod distribution constraints:** No topology spread configured
3. **No resource limits:** Pods could request unbounded memory
4. **Aggressive HPA:** Scaled too fast without considering node capacity
5. **No circuit breakers:** System kept trying even when failing

**Prevention strategies:**

**1. Pod Topology Spread Constraints:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 5000
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1  # Max 1 pod difference between nodes
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

**2. Resource Limits (prevent unbounded growth):**
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"  # Hard limit (OOM if exceeded)
    cpu: "500m"
```

**3. Pod Disruption Budgets (limit concurrent disruptions):**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  minAvailable: 80%  # At least 80% must remain available
  selector:
    matchLabels:
      app: web-app
```

**4. Rate-limited HPA:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 3000
  maxReplicas: 6000
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60  # Wait 60s before scaling up
      policies:
      - type: Percent
        value: 50  # Max 50% increase at once
        periodSeconds: 60
      - type: Pods
        value: 100  # Max 100 pods at once
        periodSeconds: 60
      selectPolicy: Min  # Use the more conservative policy
```

**5. Node auto-scaling (add capacity, don't just reschedule):**
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: ClusterAutoscaler
spec:
  scaleDown:
    enabled: true
    delayAfterAdd: 10m  # Wait 10min after adding nodes before removing
    unneededTime: 10m
  scaleUp:
    enabled: true
    maxNodeProvisionTime: 15m
```

### Cascade Prevention Patterns

**Pattern 1: Circuit Breakers**

Stop the cascade by breaking the feedback loop.

```python
class ResourceCircuitBreaker:
    def __init__(self, threshold=0.8):
        self.threshold = threshold
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def check_resource_pressure(self, node):
        memory_usage = node.used_memory / node.total_memory
        cpu_usage = node.used_cpu / node.total_cpu

        if memory_usage > self.threshold or cpu_usage > self.threshold:
            return "HIGH_PRESSURE"
        return "NORMAL"

    def should_schedule_pod(self, node):
        if self.state == "OPEN":
            return False  # Circuit open, don't schedule

        pressure = self.check_resource_pressure(node)

        if pressure == "HIGH_PRESSURE":
            self.state = "OPEN"
            return False

        return True
```

**Pattern 2: Bulkheads (Isolation)**

Isolate failures to prevent spread.

```yaml
# Separate node pools for different workload types
---
apiVersion: v1
kind: Node
metadata:
  name: node-critical-1
  labels:
    workload-type: critical
    dedicated: critical
spec:
  taints:
  - key: workload-type
    value: critical
    effect: NoSchedule

---
# Critical pods (e.g., ingress, DNS)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ingress-controller
spec:
  template:
    spec:
      nodeSelector:
        workload-type: critical
      tolerations:
      - key: workload-type
        operator: Equal
        value: critical
        effect: NoSchedule
```

**Result:** If general workload nodes fail, critical services remain unaffected.

**Pattern 3: Backpressure (Limit Input Rate)**

Don't accept more work than you can handle.

```python
class BackpressureController:
    def __init__(self, max_inflight=1000):
        self.max_inflight = max_inflight
        self.inflight_requests = 0

    def accept_request(self, request):
        if self.inflight_requests >= self.max_inflight:
            # Reject request (HTTP 503 Service Unavailable)
            return {"status": 503, "message": "System overloaded"}

        self.inflight_requests += 1
        try:
            response = self.process_request(request)
            return response
        finally:
            self.inflight_requests -= 1
```

**In Kubernetes:**
```yaml
# Limit concurrent connections to pods
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: backend-circuit-breaker
spec:
  host: backend-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http1MaxPendingRequests: 100
        maxRequestsPerConnection: 2
```

## Split-Brain Scenarios: When Consensus Breaks

A split-brain occurs when nodes disagree about cluster state, often due to network partition.

### The Split-Brain Problem

```
Initial state:
┌──────────────────────────────────┐
│         Cluster                   │
│  ┌─────┐  ┌─────┐  ┌─────┐       │
│  │Node1│──│Node2│──│Node3│       │
│  └─────┘  └─────┘  └─────┘       │
│                                   │
│  Consensus: All nodes agree       │
└──────────────────────────────────┘

Network partition:
┌──────────────┐     ┌──────────────┐
│ Partition A  │  X  │ Partition B  │
│  ┌─────┐     │     │  ┌─────┐     │
│  │Node1│     │     │  │Node3│     │
│  └─────┘     │     │  └─────┘     │
│  ┌─────┐     │     │              │
│  │Node2│     │     │              │
│  └─────┘     │     │              │
│              │     │              │
│  Has quorum  │     │  No quorum   │
│  (2/3 nodes) │     │  (1/3 nodes) │
└──────────────┘     └──────────────┘
```

**Partition A (majority):**
- Has quorum (2 out of 3 nodes)
- Can write to etcd
- Can schedule pods
- Continues operating

**Partition B (minority):**
- No quorum (1 out of 3 nodes)
- etcd becomes read-only
- Can't schedule new pods
- Existing pods keep running

### Real Incident: The Multi-Datacenter Split-Brain (Financial Services, 2019)

**Setup:**
- Kubernetes cluster across 3 datacenters
- etcd: 5 nodes (2 in DC1, 2 in DC2, 1 in DC3)
- Worker nodes: 30 in DC1, 30 in DC2, 20 in DC3

**Incident:**

**2:00 PM:**
- Network issue between DC1 and DC2
- DC3 still connected to both
- etcd loses quorum (no majority in any single partition)

**2:05 PM:**
- All etcd nodes become read-only
- API server can read but can't write
- No new pods can be scheduled
- No deployments can be updated

**2:10 PM:**
- A pod crashes in DC1
- Kubernetes tries to restart it (requires write to etcd)
- Write fails (no quorum)
- Pod stays down

**2:20 PM:**
- More pods crash (normal attrition)
- None can be restarted
- Available capacity decreases

**2:30 PM:**
- HPA tries to scale (CPU high)
- Scale operation requires write to etcd
- Write fails
- No scaling happens

**2:45 PM:**
- Too many pods down
- Services degraded
- Customer impact

**Recovery (3:00 PM):**
- Network restored
- etcd regains quorum
- Pending writes flood in
- API server overwhelmed
- Recovery takes 30 minutes

**Root cause:**
- etcd distributed across 3 datacenters
- Network partition created split-brain
- No datacenter had quorum alone

**Prevention:**

**1. Proper etcd topology:**

```
Bad (3 datacenters):
DC1: 2 nodes  ┐
DC2: 2 nodes  ├─ No datacenter has majority
DC3: 1 node   ┘

Good (3 nodes in 1 datacenter):
DC1: 3 nodes     ← Majority in one location
DC2: 0 nodes        (can tolerate DC1-DC2 network partition)
DC3: 0 nodes

Good (5 nodes in 3 datacenters):
DC1: 2 nodes  ┐
DC2: 2 nodes  ├─ Majority (3) exists if DC3 + any other DC
DC3: 1 node   ┘
```

**2. Monitoring for split-brain:**

```python
def detect_split_brain():
    # Check etcd cluster health
    etcd_members = etcdctl.member_list()

    # Check if we have quorum
    healthy_members = [m for m in etcd_members if m.healthy]
    quorum_size = (len(etcd_members) // 2) + 1

    if len(healthy_members) < quorum_size:
        alert("CRITICAL: etcd lost quorum")
        alert(f"Healthy: {len(healthy_members)}, Need: {quorum_size}")

    # Check if API server can write
    try:
        kubectl.create_test_configmap()
        kubectl.delete_test_configmap()
    except WriteError:
        alert("CRITICAL: API server can't write to etcd")
```

**3. Graceful degradation:**

```yaml
# Configure API server to serve from cache when etcd unavailable
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
spec:
  containers:
  - name: kube-apiserver
    command:
    - kube-apiserver
    - --etcd-servers=https://etcd-1:2379,https://etcd-2:2379,https://etcd-3:2379
    - --etcd-compaction-interval=5m
    - --watch-cache-sizes=persistentvolumeclaims#1000,configmaps#1000
    - --watch-cache=true  # Serve reads from cache
```

### Split-Brain in Stateful Applications

Kubernetes split-brain is bad. Database split-brain is catastrophic.

**Scenario: PostgreSQL with replication:**

```
Initial state:
Primary ──► Replica 1
        └─► Replica 2

Network partition:
Primary (isolated)      Replica 1 + Replica 2
   │                           │
   ├─ Clients write here       ├─ Replicas promote one to primary
   └─ Data: Version A          └─ Clients write here
                                 └─ Data: Version B

When network heals:
   Two primaries, divergent data (DISASTER)
```

**Prevention: Fencing**

```python
class PostgreSQLFailover:
    def __init__(self):
        self.consensus = RaftConsensus()  # Use Raft for primary election

    def promote_replica(self, replica):
        # Check: Do we have consensus?
        if not self.consensus.has_quorum():
            raise Exception("Cannot promote: no quorum")

        # Fence old primary (prevent it from accepting writes)
        self.fence_old_primary()

        # Promote replica
        replica.promote_to_primary()

    def fence_old_primary(self):
        # Option 1: STONITH (Shoot The Other Node In The Head)
        # Forcibly power off the old primary
        power_management.power_off(old_primary)

        # Option 2: Network-level fencing
        # Block old primary's network access
        firewall.block(old_primary.ip)

        # Option 3: Application-level fencing
        # Revoke old primary's credentials
        db.revoke_write_privileges(old_primary)
```

**Key principle:** **Never have two primaries.** Use fencing to ensure old primary is truly dead before promoting new primary.

## Resource Exhaustion: When the Cluster Runs Dry

### CPU Throttling: The Silent Performance Killer

**The problem:**

Kubernetes CPU limits are enforced via Linux CFS (Completely Fair Scheduler) quotas.

```yaml
resources:
  requests:
    cpu: "500m"  # 0.5 cores (scheduler uses this)
  limits:
    cpu: "1000m"  # 1.0 cores (hard limit enforced by kernel)
```

**What happens:**
- Pod gets CPU time slices based on quota
- If pod uses more than limit, kernel throttles it
- Throttling = pod sleeps for remainder of time period
- Result: Latency spikes, timeouts, degraded performance

**Real incident: The Mysterious Latency Spikes (SaaS Company, 2021)**

**Symptoms:**
- API latency p99: normally 100ms, now 5000ms
- No obvious errors in logs
- CPU usage: 50% (plenty of headroom!)
- Memory: normal
- Network: normal

**Investigation:**

```bash
# Check CPU throttling
$ kubectl top pods
NAME          CPU(cores)   MEMORY(bytes)
api-pod-1     450m         512Mi

# Looks fine (under 1000m limit)

# But check throttling metrics
$ kubectl exec api-pod-1 -- cat /sys/fs/cgroup/cpu/cpu.stat
nr_periods 12345
nr_throttled 8901  # Throttled 72% of the time!
throttled_time 234567890123  # 234 seconds throttled
```

**Root cause:**
- Pod has 1000m (1 core) limit
- Application is multi-threaded (4 threads)
- Each thread can use 0.25 cores continuously (total 1.0)
- But bursts require more (all 4 threads active = 4 cores needed)
- Kernel throttles bursts aggressively
- Result: Latency spikes during bursts

**Fix:**

```yaml
# Option 1: Increase CPU limit
resources:
  requests:
    cpu: "500m"
  limits:
    cpu: "4000m"  # Allow bursting to 4 cores

# Option 2: Remove CPU limit entirely (use QoS Burstable)
resources:
  requests:
    cpu: "500m"
  # No limits = can use all available CPU
```

**Trade-off:**
- Higher limits: Better performance, but risk noisy neighbor (one pod hogs CPU)
- No limits: Best performance, but requires node-level isolation

**Production practice:**

```yaml
# Critical latency-sensitive pods: No CPU limits
apiVersion: v1
kind: Pod
metadata:
  name: api-pod
spec:
  containers:
  - name: app
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
      limits:
        memory: "1Gi"  # Always limit memory (OOM kills pod)
        # No CPU limit

# Background batch jobs: CPU limits OK
apiVersion: v1
kind: Pod
metadata:
  name: batch-job
spec:
  containers:
  - name: worker
    resources:
      requests:
        cpu: "100m"
        memory: "256Mi"
      limits:
        cpu: "500m"  # Limit batch jobs to prevent hogging
        memory: "512Mi"
```

### Memory Exhaustion: The OOM Killer

**The problem:**

Unlike CPU, memory can't be throttled. If a pod exceeds its memory limit, the kernel OOM (Out Of Memory) killer terminates it.

**OOM kill priority:**

```
1. Best Effort (no requests/limits) - killed first
2. Burstable (requests < usage < limits) - killed second
3. Guaranteed (requests = limits) - killed last
```

**Real incident: The OOM Death Spiral (Streaming Company, 2020)**

**Setup:**
- Video transcoding service
- Processes videos in memory
- No memory limits configured

**Timeline:**

**10:00 AM:**
- User uploads 4GB video file
- Transcoding pod loads entire file into memory
- Pod uses 5GB (no limit, so allowed)

**10:05 AM:**
- Node has 32GB memory
- 20 pods running, using 25GB total
- New pod starts, uses 5GB
- Total: 30GB (node at 94%)

**10:10 AM:**
- Another large video uploaded
- Pod uses 6GB
- Total: 31GB (node at 97%)

**10:15 AM:**
- One more pod needs 2GB
- Total would be 33GB (exceeds node capacity)
- OOM killer activates

**10:16 AM:**
- OOM kills largest pod (6GB transcoding job)
- Memory freed: 6GB
- Kubernetes sees pod died
- Kubernetes reschedules pod on same node (no memory limit = schedulable)
- Pod starts, loads video (6GB)
- Memory usage back to 31GB

**10:17 AM:**
- Another pod needs memory
- OOM kills again
- Same pod killed again
- Rescheduled again
- Death spiral continues

**Impact:**
- Transcoding jobs never complete
- Users see "processing" forever
- Team manually stops new uploads
- Recovery: Add memory limits

**Fix:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: transcoder
spec:
  template:
    spec:
      containers:
      - name: transcoder
        resources:
          requests:
            memory: "4Gi"  # Reserve 4GB
          limits:
            memory: "8Gi"  # Max 8GB
        # Reject videos > 8GB
        env:
        - name: MAX_VIDEO_SIZE
          value: "8589934592"  # 8GB in bytes
```

**Additional safeguard: Admission webhook**

```python
def validate_pod_memory(pod):
    for container in pod.containers:
        if not container.resources.limits.memory:
            return {
                "allowed": False,
                "message": "All pods must have memory limits"
            }

        memory_limit = parse_memory(container.resources.limits.memory)
        if memory_limit > 16 * 1024 * 1024 * 1024:  # 16GB
            return {
                "allowed": False,
                "message": "Memory limit cannot exceed 16GB"
            }

    return {"allowed": True}
```

### Disk Exhaustion: The Silent Killer

**The problem:**

Kubernetes nodes have limited disk space. When disk fills:
- kubelet can't write logs
- Container runtime can't pull images
- Pods can't write data
- Node becomes NotReady

**Real incident: The Log Explosion (Gaming Company, 2019)**

**Setup:**
- 100-node cluster
- Game servers write logs to stdout
- No log rotation configured

**Timeline:**

**Day 1:**
- Logs: 10MB/hour per pod
- 20 pods per node = 200MB/hour per node
- 100GB disk per node = 500 hours (20 days) capacity

**Day 7:**
- New game update deployed
- Update has verbose debug logging (not disabled in production)
- Logs: 1GB/hour per pod

**Day 8:**
- Nodes start filling up
- First node reaches 90% disk
- kubelet triggers garbage collection (deletes old logs)
- Disk space temporarily freed

**Day 9:**
- More nodes hit 90%
- Garbage collection can't keep up (logs generated faster than deleted)
- Nodes reach 100% disk

**Day 9, 2:00 PM:**
- 10 nodes at 100% disk
- kubelet can't write status updates
- kubelet crashes
- Node marked NotReady
- Pods evicted

**Day 9, 2:30 PM:**
- 30 nodes NotReady
- Cascading failure begins
- Pods rescheduled to remaining nodes
- Remaining nodes fill up faster (more pods = more logs)

**Day 9, 3:00 PM:**
- 80 nodes NotReady
- Cluster unusable
- Emergency maintenance

**Recovery:**

```bash
# SSH to nodes
for node in $(kubectl get nodes -o name); do
  ssh $node 'docker system prune -af'  # Delete unused images
  ssh $node 'journalctl --vacuum-size=1G'  # Trim system logs
  ssh $node 'find /var/log/pods -mtime +1 -delete'  # Delete old pod logs
done

# Restart kubelets
for node in $(kubectl get nodes -o name); do
  ssh $node 'systemctl restart kubelet'
done
```

**Prevention:**

**1. Configure log rotation:**

```yaml
# kubelet configuration
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
containerLogMaxSize: "10Mi"
containerLogMaxFiles: 5
```

**2. Set ephemeral storage limits:**

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    resources:
      limits:
        ephemeral-storage: "2Gi"  # Max 2GB disk usage
```

**3. Monitor disk usage:**

```yaml
# Prometheus alert
- alert: NodeDiskPressure
  expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1
  for: 5m
  annotations:
    summary: "Node {{ $labels.node }} has < 10% disk space"
```

**4. Eviction thresholds:**

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
evictionHard:
  nodefs.available: "10%"  # Evict pods when < 10% disk free
  nodefs.inodesFree: "5%"
evictionSoft:
  nodefs.available: "15%"
evictionSoftGracePeriod:
  nodefs.available: "2m"
```

## Scheduler Bugs: When Placement Goes Wrong

### The Unschedulable Pod Mystery

**Symptom:** Pods stuck in Pending state, even when nodes have capacity.

**Real incident: The Taints and Tolerations Mismatch (Healthcare Company, 2021)**

**Setup:**
- Dedicated nodes for HIPAA-compliant workloads
- Nodes tainted with `compliance=hipaa:NoSchedule`
- HIPAA pods should tolerate this taint

**Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: patient-records
spec:
  replicas: 10
  template:
    spec:
      containers:
      - name: app
        image: patient-records:v1
      tolerations:
      - key: "compliance"
        operator: "Equal"
        value: "hippa"  # TYPO! Should be "hipaa"
        effect: "NoSchedule"
```

**Result:**
- Pods can't schedule on HIPAA nodes (toleration typo)
- Pods can't schedule on general nodes (no toleration)
- All 10 replicas stuck in Pending
- Service unavailable

**Diagnosis:**

```bash
$ kubectl describe pod patient-records-abc123

Events:
  Type     Reason            Message
  ----     ------            -------
  Warning  FailedScheduling  0/50 nodes are available: 10 node(s) had taints that the pod didn't tolerate, 40 node(s) didn't match Pod's node affinity/selector
```

**Fix:** Correct the typo (`hippa` → `hipaa`)

**Prevention:**

```python
# Admission webhook to validate taints/tolerations
def validate_pod_tolerations(pod):
    # Get all node taints
    all_taints = set()
    for node in k8s.list_nodes():
        for taint in node.spec.taints:
            all_taints.add(taint.key)

    # Check if pod tolerates any existing taint
    for toleration in pod.spec.tolerations:
        if toleration.key in all_taints:
            return {"allowed": True}

    # Pod has tolerations but none match
    if pod.spec.tolerations:
        return {
            "allowed": False,
            "message": f"Pod tolerations don't match any node taints. Available taints: {all_taints}"
        }

    return {"allowed": True}
```

### The Scheduler Overload

**Problem:** Scheduler itself becomes a bottleneck.

**Real incident: The Batch Job Tsunami (Data Processing Company, 2020)**

**Setup:**
- Kubernetes cluster for data processing
- Batch jobs process data files
- Each job = 1 pod

**Incident:**

**3:00 AM:**
- Nightly ETL triggers
- Creates 10,000 jobs (10,000 pods)
- All submitted at once

**3:05 AM:**
- Scheduler tries to place 10,000 pods
- Scheduler runs scoring algorithm for each pod
- Scoring algorithm: O(pods × nodes × scoring_functions)
- 10,000 pods × 100 nodes × 10 scoring functions = 10M calculations

**3:10 AM:**
- Scheduler CPU: 100%
- Scheduler memory: 8GB → 12GB (growing)
- Scheduling rate: 10 pods/second (should be 100+)

**3:30 AM:**
- Scheduler OOMKilled (exceeded 16GB limit)
- Scheduler restarts
- Lost in-progress scheduling decisions
- Restarts from scratch (10,000 pods still pending)

**4:00 AM:**
- Scheduler crashes again
- Repeat cycle

**Root cause:**
- Too many pods submitted simultaneously
- Scheduler couldn't keep up
- No rate limiting on job creation

**Fix:**

**1. Rate-limit job creation:**

```python
class RateLimitedJobCreator:
    def __init__(self, max_per_minute=100):
        self.max_per_minute = max_per_minute
        self.created_this_minute = 0
        self.minute_start = time.time()

    def create_job(self, job):
        now = time.time()

        # Reset counter every minute
        if now - self.minute_start > 60:
            self.created_this_minute = 0
            self.minute_start = now

        # Check rate limit
        if self.created_this_minute >= self.max_per_minute:
            time.sleep(60 - (now - self.minute_start))
            self.created_this_minute = 0
            self.minute_start = time.time()

        # Create job
        k8s.create_job(job)
        self.created_this_minute += 1
```

**2. Use priorities for batch jobs:**

```yaml
apiVersion: v1
kind: PriorityClass
metadata:
  name: batch-low-priority
value: 100  # Low priority

---
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processing
spec:
  template:
    spec:
      priorityClassName: batch-low-priority  # Schedule after high-priority pods
```

**3. Increase scheduler resources:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: kube-scheduler
spec:
  containers:
  - name: kube-scheduler
    resources:
      requests:
        cpu: "2000m"
        memory: "4Gi"
      limits:
        cpu: "4000m"
        memory: "8Gi"
```

## Network Policies Gone Wrong: When Security Blocks Everything

### The Default Deny Disaster

**The problem:**

Network policies are additive. If you create a default-deny policy, nothing works unless explicitly allowed.

**Real incident: The Accidental Lockout (Fintech Startup, 2020)**

**Setup:**
- Team wants to implement zero-trust networking
- Reads best practice: "Start with default deny, then allow specific traffic"

**Action:**

```yaml
# Applied to production namespace (MISTAKE)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Ingress
  - Egress
```

**Immediate effects:**

**3:00 PM:**
- Policy applied
- All ingress traffic blocked
- All egress traffic blocked
- No exceptions

**3:01 PM:**
- Frontend can't reach backend
- Backend can't reach database
- Backend can't reach external APIs
- Nothing works

**3:02 PM:**
- Engineers try to debug
- Try to create allow policies
- Allow policies take 1-2 minutes to apply (controller lag)
- Meanwhile, customers see errors

**3:05 PM:**
- Team realizes mistake
- Try to delete default-deny policy
- Delete command times out (API server overloaded with network policy updates)

**3:10 PM:**
- Force delete policy via kubectl
- Network connectivity restored
- Total outage: 10 minutes
- Revenue lost: $50K

**Root cause:**
- Applied default-deny without allow rules
- No testing in staging environment
- No gradual rollout

**Correct approach:**

```bash
# Step 1: Create allow policies FIRST
kubectl apply -f allow-frontend-to-backend.yaml
kubectl apply -f allow-backend-to-database.yaml
kubectl apply -f allow-backend-to-external-api.yaml

# Step 2: Wait for policies to be active
sleep 60

# Step 3: Test connectivity
curl http://backend-service/health

# Step 4: Apply default-deny
kubectl apply -f default-deny.yaml

# Step 5: Monitor for denials
kubectl logs -n kube-system -l k8s-app=calico-node | grep denied
```

**Prevention: Network policy testing**

```python
def test_network_policies():
    """Test that critical paths are allowed"""

    test_cases = [
        ("frontend", "backend", 8080, True),  # Should be allowed
        ("frontend", "database", 5432, False),  # Should be blocked
        ("backend", "database", 5432, True),  # Should be allowed
        ("backend", "external-api", 443, True),  # Should be allowed
    ]

    for source, dest, port, should_succeed in test_cases:
        result = test_connection(source, dest, port)

        if result.success != should_succeed:
            raise AssertionError(
                f"Network policy test failed: "
                f"{source} → {dest}:{port} "
                f"expected {should_succeed}, got {result.success}"
            )
```

### The DNS Blackhole

**Problem:** Network policy blocks DNS queries.

**Common mistake:**

```yaml
# Default deny (blocks DNS!)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes:
  - Egress
```

**Result:**
- Pods can't resolve DNS names
- All service-to-service communication breaks
- Error: `Temporary failure in name resolution`

**Fix:**

```yaml
# Allow DNS queries
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  # Allow DNS queries to kube-dns/CoreDNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

## Recovery Strategies

### Emergency Recovery Playbook

**When orchestration fails completely:**

**Step 1: Stop the automation (break the loop)**

```bash
# Stop auto-scaling
kubectl delete hpa --all

# Stop cluster autoscaler
kubectl scale deployment cluster-autoscaler -n kube-system --replicas=0

# Stop deployments
kubectl scale deployment --all --replicas=0 -n <namespace>
```

**Step 2: Stabilize the control plane**

```bash
# Check etcd health
ETCDCTL_API=3 etcdctl endpoint health

# Check API server
kubectl get --raw /healthz

# If API server overloaded, restart it
kubectl delete pod -n kube-system -l component=kube-apiserver

# Check scheduler
kubectl get events | grep FailedScheduling
```

**Step 3: Clear backlog**

```bash
# Delete failed pods
kubectl delete pods --field-selector=status.phase=Failed --all-namespaces

# Delete evicted pods
kubectl get pods --all-namespaces | grep Evicted | awk '{print $2 " -n " $1}' | xargs kubectl delete pod

# Clear pending pods that will never schedule
kubectl delete pods --field-selector=status.phase=Pending --all-namespaces
```

**Step 4: Gradually restore**

```bash
# Start critical services first (priority order)
kubectl scale deployment ingress-controller --replicas=3
kubectl scale deployment coredns -n kube-system --replicas=3
kubectl scale deployment critical-backend --replicas=5

# Wait for health
kubectl rollout status deployment critical-backend

# Start less critical services
kubectl scale deployment general-backend --replicas=10

# Finally, re-enable automation
kubectl scale deployment cluster-autoscaler -n kube-system --replicas=1
```

### Disaster Recovery: Recreate from Git

**Scenario:** Cluster is completely destroyed.

**Recovery with GitOps:**

```bash
# 1. Provision new cluster (Terraform)
cd terraform/production
terraform apply

# 2. Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. Configure ArgoCD to sync from Git
argocd app create production \
  --repo https://github.com/myorg/infrastructure \
  --path overlays/production \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace production \
  --sync-policy automated

# 4. Wait for sync (5-10 minutes)
argocd app wait production

# 5. Restore data from backups
kubectl exec -n production postgres-0 -- pg_restore /backup/latest.dump

# 6. Verify
kubectl get pods -n production
curl https://api.example.com/health

# Total time: 30 minutes
```

### Chaos Engineering: Test Before It Happens

**Test failure scenarios proactively:**

```yaml
# Chaos Mesh: Kill random pods
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill-test
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
    - production
    labelSelectors:
      app: backend
  scheduler:
    cron: "@hourly"

---
# Test network partition
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-partition-test
spec:
  action: partition
  mode: all
  selector:
    namespaces:
    - production
    labelSelectors:
      app: backend
  direction: to
  target:
    selector:
      namespaces:
      - production
      labelSelectors:
        app: database
  duration: "30s"

---
# Test CPU pressure
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: cpu-stress-test
spec:
  mode: one
  selector:
    namespaces:
    - production
  stressors:
    cpu:
      workers: 4
      load: 100
  duration: "5m"
```

**Chaos testing cadence:**

```
Development: Daily
Staging: Weekly
Production: Monthly (off-peak hours)
```

**Metrics to watch during chaos testing:**
- Error rate
- Latency (p50, p95, p99)
- Throughput
- Time to recovery
- Alert firing

## Mental Model Summary

### Orchestration Failure Patterns

1. **Cascading Failures**
   - One failure triggers exponentially more
   - Positive feedback loops (death spirals)
   - Prevention: Circuit breakers, bulkheads, backpressure

2. **Split-Brain Scenarios**
   - Network partition creates multiple leaders
   - Divergent state = data corruption
   - Prevention: Proper quorum, fencing, consensus

3. **Resource Exhaustion**
   - CPU throttling: Silent performance killer
   - Memory OOM: Pods killed randomly
   - Disk full: Nodes become unusable
   - Prevention: Limits, monitoring, eviction thresholds

4. **Scheduler Failures**
   - Pods stuck in Pending
   - Scheduler overload
   - Placement bugs
   - Prevention: Validation, rate limiting, priorities

5. **Network Policy Mistakes**
   - Default deny blocks everything
   - DNS blackholes
   - Prevention: Test before applying, gradual rollout

### Recovery Principles

1. **Stop the automation:** Break feedback loops
2. **Stabilize control plane:** Fix etcd, API server, scheduler
3. **Clear backlog:** Delete failed/pending pods
4. **Gradual restore:** Critical services first
5. **Monitor continuously:** Watch for secondary failures

### Prevention Strategies

1. **Resource limits:** Prevent unbounded growth
2. **Pod disruption budgets:** Limit concurrent failures
3. **Topology spread:** Distribute workloads evenly
4. **Chaos engineering:** Test failure scenarios
5. **GitOps:** Disaster recovery from Git
6. **Monitoring:** Detect problems before they cascade
7. **Graceful degradation:** Degrade instead of fail

**The meta-lesson:** Orchestration is powerful but fragile. It prevents simple failures but enables complex ones. The key is **defense in depth**—multiple layers of protection, monitoring, and recovery procedures.

**Next:** Return to [Chapter 13: Orchestration Overview](./index.md)
