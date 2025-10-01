# Kubernetes Deep Dive: The Operating System for Distributed Applications

## Introduction: The Distributed Kernel

When you run a process on Linux, you don't think about which CPU core it runs on, which memory pages it gets, or how network packets reach it. The kernel abstracts all that away. You just say "run this" and the system figures it out.

Kubernetes does the same thing—but for distributed applications across hundreds of machines.

In 2014, Google open-sourced Kubernetes, distilling 15 years of internal experience running containers at planet scale (Borg and Omega systems). They weren't open-sourcing a tool. They were open-sourcing a **distributed operating system** that would become the foundation for modern cloud-native infrastructure.

### Why Kubernetes Won

Before Kubernetes, orchestrating containers meant:
- Writing custom scripts for each deployment
- Manually tracking which containers run where
- Building your own service discovery
- Implementing health checks and restarts manually
- Managing networking between nodes yourself
- Creating your own load balancing

After Kubernetes:
- Declare what you want: "Run 10 replicas of this container"
- Kubernetes figures out how to make it happen
- Self-healing: Crashed containers restart automatically
- Service discovery: Services find each other by name
- Load balancing: Traffic distributes automatically
- Rolling updates: Deploy new versions with zero downtime

The abstraction level shift is profound. You go from "how do I run containers?" to "what should my system look like?"

### The Mental Shift: From Imperative to Declarative

**Pre-Kubernetes (Imperative):**
```bash
# How to do things (imperative commands)
ssh node1 "docker run -d app:v1"
ssh node2 "docker run -d app:v1"
ssh node3 "docker run -d app:v1"
# Wait, node2 crashed
ssh node4 "docker run -d app:v1"  # Manual replacement
# Now we need v2
ssh node1 "docker stop app; docker run -d app:v2"
# ...repeat for each node...
```

**With Kubernetes (Declarative):**
```yaml
# What you want (declarative configuration)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: app:v2
```

You describe the desired state. Kubernetes continuously works to make reality match your declaration. This is the **reconciliation loop pattern**—the heart of Kubernetes.

## The Control Plane: The Brain of the Cluster

The control plane is where all decisions happen. It's the "kernel" of your distributed OS.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CONTROL PLANE                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   API    │  │   etcd   │  │Scheduler │  │Controller│   │
│  │  Server  │◄─┤(Storage) │  │          │  │ Manager  │   │
│  └────┬─────┘  └──────────┘  └────┬─────┘  └────┬─────┘   │
│       │                            │             │          │
└───────┼────────────────────────────┼─────────────┼──────────┘
        │                            │             │
        │         Network            │             │
        │                            │             │
┌───────┼────────────────────────────┼─────────────┼──────────┐
│       ▼                            ▼             ▼          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  kubelet │  │  kubelet │  │  kubelet │  │  kubelet │   │
│  ├──────────┤  ├──────────┤  ├──────────┤  ├──────────┤   │
│  │Container │  │Container │  │Container │  │Container │   │
│  │ Runtime  │  │ Runtime  │  │ Runtime  │  │ Runtime  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│     Node 1        Node 2        Node 3        Node 4       │
└──────────────────────────────────────────────────────────────┘
```

### Component 1: API Server (kube-apiserver)

The API server is the **front door** to Kubernetes. Everything talks to it—kubectl, controllers, kubelets, external systems. Nothing bypasses it.

**What it does:**
- Authenticates and authorizes requests
- Validates resource specifications
- Persists changes to etcd
- Serves the Kubernetes API
- Provides webhook extension points

**Production example:**
```yaml
# High-availability API server configuration
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - name: kube-apiserver
    image: registry.k8s.io/kube-apiserver:v1.28.0
    command:
    - kube-apiserver
    # Authentication
    - --client-ca-file=/etc/kubernetes/pki/ca.crt
    - --service-account-key-file=/etc/kubernetes/pki/sa.pub
    - --service-account-signing-key-file=/etc/kubernetes/pki/sa.key
    # Authorization
    - --authorization-mode=Node,RBAC
    # Admission controllers (enforcement of policies)
    - --enable-admission-plugins=NodeRestriction,PodSecurityPolicy,ResourceQuota
    # Storage (etcd)
    - --etcd-servers=https://etcd-1:2379,https://etcd-2:2379,https://etcd-3:2379
    - --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
    # Rate limiting (protect against overload)
    - --max-requests-inflight=400
    - --max-mutating-requests-inflight=200
    # Audit logging (compliance)
    - --audit-log-path=/var/log/kubernetes/audit.log
    - --audit-log-maxage=30
    - --audit-log-maxbackup=10
    - --audit-log-maxsize=100
```

**Why this matters in production:**

The API server is a **single point of failure** and a **performance bottleneck**. In production:

1. **Run multiple replicas** (typically 3+) behind a load balancer
2. **Configure rate limiting** to prevent abuse
3. **Enable audit logging** for compliance and debugging
4. **Monitor request latency** (p50, p99) and error rates

**Real failure scenario (2019, Reddit):**

Reddit's Kubernetes cluster experienced API server overload during a deployment. The issue:
- They deployed 1000+ pods simultaneously
- Each pod creation triggered watch notifications
- Watchers (controllers) queried the API server
- API server couldn't handle the load spike
- Request timeouts cascaded to more retries
- Cluster became unresponsive for 20 minutes

**The fix:**
- Implemented gradual rollouts (max 10 pods per second)
- Added API server rate limiting
- Configured pod priority classes (critical pods first)
- Increased API server replicas from 3 to 5

### Component 2: etcd (The Source of Truth)

etcd is a distributed key-value store that holds **all cluster state**. If etcd is lost, your cluster is gone.

**What it stores:**
- All Kubernetes objects (Pods, Services, Deployments, etc.)
- Secrets and ConfigMaps
- Resource versions and revision history
- Lease information for leader election

**The data model:**
```
/registry/
├── pods/
│   ├── default/
│   │   ├── app-pod-1
│   │   └── app-pod-2
│   └── kube-system/
│       └── kube-dns-pod
├── services/
│   └── default/
│       └── app-service
├── deployments/
│   └── default/
│       └── app-deployment
└── configmaps/
    └── default/
        └── app-config
```

**Production etcd configuration:**

```yaml
# etcd cluster member configuration
name: etcd-1
data-dir: /var/lib/etcd
wal-dir: /var/lib/etcd/wal

# Cluster configuration
initial-cluster: etcd-1=https://10.0.1.10:2380,etcd-2=https://10.0.1.11:2380,etcd-3=https://10.0.1.12:2380
initial-cluster-state: new
initial-cluster-token: etcd-cluster-1

# Client communication
listen-client-urls: https://0.0.0.0:2379
advertise-client-urls: https://10.0.1.10:2379

# Peer communication
listen-peer-urls: https://0.0.0.0:2380
initial-advertise-peer-urls: https://10.0.1.10:2380

# Security
client-cert-auth: true
trusted-ca-file: /etc/etcd/pki/ca.crt
cert-file: /etc/etcd/pki/server.crt
key-file: /etc/etcd/pki/server.key
peer-client-cert-auth: true
peer-trusted-ca-file: /etc/etcd/pki/ca.crt
peer-cert-file: /etc/etcd/pki/peer.crt
peer-key-file: /etc/etcd/pki/peer.key

# Performance tuning
heartbeat-interval: 100
election-timeout: 1000
snapshot-count: 10000
quota-backend-bytes: 8589934592  # 8 GB

# Compaction (prevent database bloat)
auto-compaction-mode: periodic
auto-compaction-retention: "8h"
```

**Why etcd is critical:**

etcd uses the **Raft consensus algorithm** to ensure consistency. With 3 nodes:
- Can tolerate 1 failure
- Requires 2 nodes for quorum
- If 2 nodes fail, cluster becomes read-only

With 5 nodes:
- Can tolerate 2 failures
- Requires 3 nodes for quorum
- Better availability, but more network overhead

**Real failure scenario (2020, Gaming company):**

A gaming company ran a 5-node etcd cluster. During a network partition:
- 2 nodes were isolated in one datacenter
- 3 nodes were in another datacenter
- The 3-node partition had quorum and continued operating
- The 2-node partition couldn't accept writes (no quorum)
- When the network healed, the 2-node partition had stale data
- Raft's consistency guarantee prevented data loss (2-node writes rejected)

**The lesson:** Always run etcd with odd numbers (3, 5, 7) and **never** split evenly across failure domains.

**Backing up etcd:**

```bash
# Backup etcd snapshot
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d-%H%M%S).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify snapshot
ETCDCTL_API=3 etcdctl snapshot status /backup/etcd-snapshot-20231001-120000.db

# Restore from snapshot (disaster recovery)
ETCDCTL_API=3 etcdctl snapshot restore /backup/etcd-snapshot-20231001-120000.db \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://10.0.1.10:2380,etcd-2=https://10.0.1.11:2380,etcd-3=https://10.0.1.12:2380 \
  --initial-advertise-peer-urls=https://10.0.1.10:2380
```

**Production practice:** Automate etcd backups every hour. Store snapshots in object storage (S3/GCS) with encryption. Test restores monthly.

### Component 3: Scheduler (kube-scheduler)

The scheduler **decides which node runs each pod**. It sounds simple, but the scheduler makes dozens of decisions per second considering hundreds of constraints.

**The scheduling algorithm:**

```python
# Simplified scheduler logic
def schedule_pod(pod, nodes):
    # Phase 1: Filtering (find feasible nodes)
    feasible_nodes = []
    for node in nodes:
        if can_run_on_node(pod, node):
            feasible_nodes.append(node)

    if not feasible_nodes:
        # Pod is unschedulable
        set_pod_status(pod, "Pending", "No nodes available")
        return None

    # Phase 2: Scoring (rank feasible nodes)
    scored_nodes = []
    for node in feasible_nodes:
        score = calculate_score(pod, node)
        scored_nodes.append((node, score))

    # Phase 3: Selection (pick best node)
    scored_nodes.sort(key=lambda x: x[1], reverse=True)
    best_node = scored_nodes[0][0]

    # Phase 4: Binding (assign pod to node)
    bind_pod_to_node(pod, best_node)
    return best_node

def can_run_on_node(pod, node):
    """Predicates/filters - hard constraints"""
    # Check 1: Does node have enough resources?
    if not has_sufficient_resources(node, pod):
        return False

    # Check 2: Does pod's selector match node labels?
    if not matches_node_selector(pod, node):
        return False

    # Check 3: Does pod tolerate node taints?
    if not tolerates_taints(pod, node):
        return False

    # Check 4: Are there conflicting pods (anti-affinity)?
    if has_anti_affinity_conflicts(pod, node):
        return False

    # Check 5: Are required ports available?
    if not has_available_ports(node, pod):
        return False

    # Check 6: Does node have required volumes?
    if not has_required_volumes(node, pod):
        return False

    return True

def calculate_score(pod, node):
    """Priorities - soft preferences"""
    score = 0

    # Prefer nodes with more available resources
    score += balance_resource_usage(node) * 10

    # Prefer spreading pods across nodes
    score += spread_pods_across_nodes(pod, node) * 8

    # Prefer nodes with pod's affinity rules
    score += affinity_score(pod, node) * 7

    # Prefer nodes in same zone as related pods
    score += topology_score(pod, node) * 6

    # Prefer nodes with fewer pods
    score += least_requested_priority(node) * 5

    # Custom scoring plugins
    score += custom_scoring_plugins(pod, node)

    return score
```

**Production scheduling constraints:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
spec:
  # Resource requests (scheduler uses these for placement)
  containers:
  - name: app
    image: web-app:v1
    resources:
      requests:
        memory: "256Mi"
        cpu: "500m"
      limits:
        memory: "512Mi"
        cpu: "1000m"

  # Node selector (hard constraint - must match)
  nodeSelector:
    disktype: ssd
    environment: production

  # Node affinity (prefer nodes with GPU, but not required)
  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: accelerator
            operator: In
            values:
            - gpu

    # Pod affinity (prefer running near cache pods)
    podAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - cache
          topologyKey: kubernetes.io/hostname

    # Pod anti-affinity (never run two replicas on same node)
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - web-app
        topologyKey: kubernetes.io/hostname

  # Tolerations (allow scheduling on tainted nodes)
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "database"
    effect: "NoSchedule"
```

**Real failure scenario (2021, E-commerce platform):**

An e-commerce platform ran a 100-node Kubernetes cluster. During Black Friday:
- Traffic spiked 10×
- Horizontal Pod Autoscaler (HPA) tried to scale from 50 to 500 pods
- Scheduler placed all new pods on 10 nodes (uneven distribution)
- Those 10 nodes became overloaded
- OOM killer started terminating pods
- HPA scaled up more (pods were dying)
- Positive feedback loop of death

**Why it happened:**
- Default scheduler prefers nodes with fewer pods
- But the first 10 nodes to accept pods became "least requested"
- Subsequent pods kept landing there
- No spreading was configured

**The fix:**
```yaml
# Pod topology spread constraints (force even distribution)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 500
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
      # This ensures pods spread evenly across nodes
      # maxSkew: 1 means difference between nodes <= 1 pod
```

**Custom schedulers:**

You can write custom schedulers for specialized workloads:

```go
// Custom scheduler for GPU workloads
package main

import (
    "context"
    "k8s.io/api/core/v1"
    "k8s.io/kubernetes/pkg/scheduler/framework"
)

type GPUScheduler struct{}

func (g *GPUScheduler) Name() string {
    return "gpu-scheduler"
}

func (g *GPUScheduler) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    node := nodeInfo.Node()

    // Check if pod requests GPU
    gpuRequest := getGPURequest(pod)
    if gpuRequest == 0 {
        return framework.NewStatus(framework.Success)
    }

    // Check if node has available GPU
    availableGPU := getAvailableGPU(node)
    if availableGPU < gpuRequest {
        return framework.NewStatus(framework.Unschedulable, "insufficient GPU")
    }

    // Check GPU type matches (Tesla vs Ampere)
    requiredGPUType := getRequiredGPUType(pod)
    nodeGPUType := getNodeGPUType(node)
    if requiredGPUType != "" && requiredGPUType != nodeGPUType {
        return framework.NewStatus(framework.Unschedulable, "GPU type mismatch")
    }

    return framework.NewStatus(framework.Success)
}

func (g *GPUScheduler) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    // Prefer nodes with most available GPU memory
    nodeInfo, err := g.frameworkHandle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.AsStatus(err)
    }

    availableGPUMemory := getAvailableGPUMemory(nodeInfo.Node())

    // Score 0-100 based on available GPU memory
    score := (availableGPUMemory / totalGPUMemory) * 100

    return score, framework.NewStatus(framework.Success)
}
```

### Component 4: Controller Manager (kube-controller-manager)

The controller manager runs **control loops** that watch the cluster state and make changes to move current state toward desired state.

**The reconciliation loop pattern:**

```python
# Generic controller pattern
def reconcile_loop(resource_type):
    while True:
        # Step 1: List current state
        current_state = api_server.list(resource_type)

        # Step 2: List desired state
        desired_state = api_server.list_desired(resource_type)

        # Step 3: Compare and reconcile
        for desired in desired_state:
            current = find_current(current_state, desired)

            if current is None:
                # Resource doesn't exist - create it
                create_resource(desired)
            elif current != desired:
                # Resource exists but differs - update it
                update_resource(desired)
            # else: resource matches desired state - do nothing

        # Step 4: Delete unwanted resources
        for current in current_state:
            if not exists_in_desired(desired_state, current):
                delete_resource(current)

        # Step 5: Wait and repeat
        time.sleep(reconcile_interval)
```

**Built-in controllers:**

Kubernetes ships with dozens of controllers. Key ones:

**1. Deployment Controller:**

Manages ReplicaSets to achieve declarative updates.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max 1 extra pod during update
      maxUnavailable: 1  # Max 1 unavailable pod during update
  template:
    spec:
      containers:
      - name: app
        image: web-app:v2
```

**What the Deployment controller does:**
1. Creates a new ReplicaSet for v2
2. Scales v2 ReplicaSet from 0 to 1 (now 4 pods total)
3. Scales v1 ReplicaSet from 3 to 2 (back to 3 pods total)
4. Scales v2 ReplicaSet from 1 to 2
5. Scales v1 ReplicaSet from 2 to 1
6. Scales v2 ReplicaSet from 2 to 3
7. Scales v1 ReplicaSet from 1 to 0
8. Deployment complete

**2. ReplicaSet Controller:**

Ensures the desired number of pod replicas are running.

```python
def replicaset_reconcile(replicaset):
    desired_replicas = replicaset.spec.replicas
    current_pods = list_pods_matching(replicaset.selector)
    current_replicas = len(current_pods)

    if current_replicas < desired_replicas:
        # Need more pods
        diff = desired_replicas - current_replicas
        for i in range(diff):
            create_pod(replicaset.template)

    elif current_replicas > desired_replicas:
        # Need fewer pods
        diff = current_replicas - desired_replicas
        pods_to_delete = select_pods_for_deletion(current_pods, diff)
        for pod in pods_to_delete:
            delete_pod(pod)

    # else: current == desired, nothing to do
```

**3. Node Controller:**

Monitors node health and evicts pods from unhealthy nodes.

```python
def node_reconcile():
    nodes = list_all_nodes()

    for node in nodes:
        # Check if node is healthy
        if not is_node_healthy(node):
            # Mark node as not ready
            set_node_condition(node, "Ready", "False")

            # Start eviction timer
            eviction_time = node.unhealthy_since + grace_period

            if time.now() > eviction_time:
                # Evict all pods from unhealthy node
                pods = list_pods_on_node(node)
                for pod in pods:
                    if is_critical_pod(pod):
                        # Give critical pods more time
                        continue

                    # Mark pod for deletion
                    delete_pod(pod)

                    # Controller will recreate on healthy node
```

**4. Service Controller:**

Creates load balancers and updates endpoints.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  type: LoadBalancer
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

**What the Service controller does:**
1. Creates a cloud load balancer (via cloud provider API)
2. Watches for pods matching selector
3. Updates Endpoints object with pod IPs
4. Configures load balancer to route to healthy endpoints
5. Removes endpoints when pods become unhealthy

**Production considerations:**

Controllers can fight each other. Example:

```yaml
# Deployment creates pods with 3 replicas
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3

---
# But HPA tries to scale based on CPU
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
```

**The conflict:**
- Deployment controller wants 3 replicas (spec.replicas: 3)
- HPA controller wants to scale based on CPU (currently 5 replicas)
- Both controllers fight over replica count

**The solution:**
Remove `spec.replicas` from Deployment when using HPA. HPA will manage the count.

### Component 5: kubelet (The Node Agent)

The kubelet is the agent that runs on every node. It's responsible for:
- Registering the node with the control plane
- Watching the API server for pods assigned to its node
- Running containers via the container runtime (containerd/CRI-O)
- Reporting node and pod status
- Running liveness/readiness probes

**kubelet configuration:**

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration

# Node registration
address: 0.0.0.0
port: 10250
readOnlyPort: 0  # Disable insecure port

# Authentication
authentication:
  x509:
    clientCAFile: /etc/kubernetes/pki/ca.crt
  webhook:
    enabled: true
  anonymous:
    enabled: false

# Authorization
authorization:
  mode: Webhook

# Resource management
maxPods: 110
podPidsLimit: 4096

# Eviction thresholds (when to kill pods)
evictionHard:
  memory.available: "100Mi"
  nodefs.available: "10%"
  nodefs.inodesFree: "5%"
evictionSoft:
  memory.available: "500Mi"
  nodefs.available: "15%"
evictionSoftGracePeriod:
  memory.available: "1m30s"
  nodefs.available: "2m"

# Image garbage collection
imageGCHighThresholdPercent: 85
imageGCLowThresholdPercent: 80

# Container runtime
containerRuntime: remote
containerRuntimeEndpoint: unix:///var/run/containerd/containerd.sock

# Logging
logging:
  format: json
  verbosity: 2
```

**The kubelet reconciliation loop:**

```python
def kubelet_sync_loop():
    while True:
        # Step 1: Get pods that should run on this node
        desired_pods = api_server.list_pods_for_node(my_node_name)

        # Step 2: Get pods currently running
        running_pods = container_runtime.list_pods()

        # Step 3: Reconcile
        for desired_pod in desired_pods:
            running_pod = find_pod(running_pods, desired_pod.uid)

            if running_pod is None:
                # Pod not running - start it
                start_pod(desired_pod)
            elif pod_spec_changed(desired_pod, running_pod):
                # Pod changed - restart it
                stop_pod(running_pod)
                start_pod(desired_pod)
            else:
                # Pod running correctly
                # Run health probes
                run_liveness_probe(running_pod)
                run_readiness_probe(running_pod)

        # Step 4: Kill pods that shouldn't be running
        for running_pod in running_pods:
            if not should_be_running(running_pod, desired_pods):
                stop_pod(running_pod)

        # Step 5: Report status to API server
        report_pod_status()
        report_node_status()

        # Step 6: Wait and repeat
        time.sleep(10)  # 10-second sync interval
```

**Real failure scenario (2020, Financial services company):**

A financial services company ran Kubernetes on bare metal. One night:
- A node's disk filled up (logs from a misbehaving pod)
- kubelet couldn't write to disk
- kubelet tried to evict pods but couldn't (disk full)
- kubelet crashed (couldn't write its own logs)
- Node reported as NotReady
- All pods on that node marked for eviction
- But kubelet was down, so pods kept running
- Zombie pods continued serving traffic
- Some requests routed to zombie pods (stale data)

**The fix:**
1. Reserve disk space for system components:
```yaml
evictionHard:
  nodefs.available: "10%"  # Reserve 10% for system
systemReserved:
  ephemeral-storage: "10Gi"  # Reserve 10GB for kubelet
```

2. Monitor disk usage and alert at 70%
3. Log rotation on all pods
4. Pod resource limits include ephemeral storage

## Production Configurations

### High Availability Control Plane

Running a production Kubernetes cluster requires HA control plane:

```yaml
# 3-node control plane with stacked etcd
┌─────────────────────────────────────────────────┐
│ Load Balancer (HAProxy/NGINX)                   │
│ VIP: 10.0.0.100:6443                            │
└────────┬────────────┬────────────┬──────────────┘
         │            │            │
    ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
    │Master-1 │  │Master-2 │  │Master-3 │
    │         │  │         │  │         │
    │API:6443 │  │API:6443 │  │API:6443 │
    │etcd:2379│  │etcd:2379│  │etcd:2379│
    └─────────┘  └─────────┘  └─────────┘
```

**Load balancer configuration (HAProxy):**

```conf
# /etc/haproxy/haproxy.cfg
global
    log /dev/log local0
    maxconn 4096

defaults
    mode tcp
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend kubernetes-api
    bind *:6443
    default_backend kubernetes-api-backend

backend kubernetes-api-backend
    option tcp-check
    balance roundrobin
    server master-1 10.0.1.10:6443 check
    server master-2 10.0.1.11:6443 check
    server master-3 10.0.1.12:6443 check
```

**Why 3 control plane nodes?**
- Can tolerate 1 failure (2/3 quorum)
- Even number (2 or 4) is worse (split-brain risk)
- 5 nodes can tolerate 2 failures but have higher latency

### Resource Management

**Node allocatable resources:**

```yaml
# What kubelet calculates as available for pods
Allocatable = Capacity - Reserved - Eviction Threshold

# Example node with 16 GB RAM
Capacity:              16 GB
- System Reserved:     -1 GB  (OS + system daemons)
- Kubelet Reserved:    -1 GB  (kubelet + container runtime)
- Eviction Threshold:  -500 MB (buffer before eviction)
= Allocatable:         13.5 GB (available for pods)
```

**Configure reservations:**

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
systemReserved:
  cpu: "1000m"
  memory: "1Gi"
  ephemeral-storage: "10Gi"
kubeReserved:
  cpu: "1000m"
  memory: "1Gi"
  ephemeral-storage: "10Gi"
evictionHard:
  memory.available: "500Mi"
  nodefs.available: "10%"
enforceNodeAllocatable:
- pods
- system-reserved
- kube-reserved
```

**Quality of Service (QoS) classes:**

Kubernetes assigns QoS classes based on resource requests/limits:

**1. Guaranteed (highest priority):**
```yaml
# requests == limits for all containers
resources:
  requests:
    memory: "1Gi"
    cpu: "1000m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

**2. Burstable (medium priority):**
```yaml
# requests < limits, or only requests specified
resources:
  requests:
    memory: "500Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

**3. BestEffort (lowest priority):**
```yaml
# No requests or limits specified
resources: {}
```

**Eviction order:**
When a node runs out of resources, kubelet evicts pods in order:
1. BestEffort pods (evicted first)
2. Burstable pods exceeding requests
3. Burstable pods within requests
4. Guaranteed pods (evicted last)

**Production practice:** Critical pods should be Guaranteed. Background jobs can be BestEffort.

### Network Policies

Control traffic between pods:

```yaml
# Default deny all ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress

---
# Allow frontend to backend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080

---
# Allow backend to database
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-database
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 5432
```

**Production practice:** Start with default-deny and explicitly allow necessary traffic. This limits blast radius of compromised pods.

## Real Failure Scenarios

### Scenario 1: The Cascading Node Failure

**The setup:**
- 50-node cluster running 2000 pods
- Node-to-pod ratio: 40 pods/node
- No pod disruption budgets configured

**The incident:**
1. One node has a kernel panic (hardware failure)
2. kubelet stops responding
3. Node controller marks node as NotReady after 40 seconds
4. Node controller starts evicting pods after 5 minutes
5. 40 pods marked for deletion
6. Scheduler places 40 new pods on remaining 49 nodes
7. Some nodes now overloaded (exceeded capacity)
8. Overloaded nodes trigger OOM killer
9. More pods killed, more rescheduling
10. Positive feedback loop

**The damage:**
- 5 nodes became overloaded and crashed
- 200 pods affected
- 15 minutes of degraded service
- $50K in lost revenue

**The fix:**

```yaml
# 1. Pod Disruption Budgets (limit concurrent disruptions)
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: web-app

---
# 2. Resource requests (prevent overcommit)
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"

---
# 3. Pod priority (evict low-priority pods first)
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000
globalDefault: false
description: "High priority for production apps"
```

### Scenario 2: The etcd Out-of-Space Crisis

**The setup:**
- 3-node etcd cluster
- Default etcd quota: 2 GB
- Monitoring not configured for etcd metrics

**The incident:**
1. Application creates many ConfigMaps (1000s)
2. Each ConfigMap stored in etcd
3. etcd database grows to 2 GB (quota limit)
4. etcd stops accepting writes (read-only mode)
5. API server can't write new objects
6. Deployments can't update
7. New pods can't be created
8. Cluster effectively frozen

**The symptoms:**
```bash
$ kubectl create deployment test --image=nginx
Error from server: etcdserver: mvcc: database space exceeded
```

**The emergency fix:**

```bash
# 1. Increase etcd quota (temporary)
etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  alarm disarm

# 2. Compact etcd history
etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  compact $(etcdctl endpoint status --write-out="json" | jq -r '.[0].Status.header.revision')

# 3. Defragment etcd
etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  defrag --cluster

# 4. Delete unnecessary objects
kubectl delete configmap --all -n temporary-namespace
```

**The permanent fix:**

```yaml
# etcd configuration
quota-backend-bytes: 8589934592  # 8 GB
auto-compaction-mode: periodic
auto-compaction-retention: "8h"

# Monitoring
- alert: EtcdDatabaseSpaceExceeded
  expr: etcd_mvcc_db_total_size_in_bytes / etcd_server_quota_backend_bytes > 0.8
  for: 5m
  annotations:
    summary: "etcd database size is {{ $value }}% of quota"
```

### Scenario 3: The DNS Meltdown

**The setup:**
- CoreDNS running as cluster DNS (2 replicas)
- 100 nodes, 3000 pods
- No DNS caching configured in applications

**The incident:**
1. Application makes DNS queries for every HTTP request
2. 10,000 requests/second = 10,000 DNS queries/second
3. CoreDNS pods at 100% CPU
4. DNS queries timeout (5-second timeout)
5. Applications retry DNS queries (exponential backoff not configured)
6. More DNS queries = more load on CoreDNS
7. Positive feedback loop

**The symptoms:**
```bash
$ kubectl logs app-pod
Error: dial tcp: lookup backend-service.production.svc.cluster.local: i/o timeout
```

**The fix:**

```yaml
# 1. Scale CoreDNS
kubectl scale deployment coredns -n kube-system --replicas=10

# 2. Configure DNS caching in applications
# Python example with dnspython
import dns.resolver
resolver = dns.resolver.Resolver()
resolver.cache = dns.resolver.Cache()  # Enable caching

# 3. Configure pod DNS policy
apiVersion: v1
kind: Pod
spec:
  dnsPolicy: ClusterFirst
  dnsConfig:
    options:
    - name: ndots
      value: "1"  # Reduce DNS search paths
    - name: timeout
      value: "2"  # Shorter timeout
    - name: attempts
      value: "2"  # Fewer attempts

# 4. Use NodeLocal DNSCache (caching DNS proxy on each node)
apiVersion: v1
kind: DaemonSet
metadata:
  name: node-local-dns
  namespace: kube-system
spec:
  template:
    spec:
      containers:
      - name: node-cache
        image: registry.k8s.io/dns/k8s-dns-node-cache:1.22.13
```

**Production practice:**
- Always run multiple CoreDNS replicas (1 per 10-20 nodes)
- Enable NodeLocal DNSCache
- Configure applications to cache DNS responses
- Monitor DNS query rate and latency

## Mental Model Summary

Kubernetes is a **distributed operating system** built on these principles:

### 1. Declarative Desired State
You declare what you want. Controllers continuously reconcile reality to match.

### 2. Reconciliation Loops
Every controller follows the same pattern:
```
Watch → Compare → Act → Repeat
```

### 3. Everything is an Object
Pods, Services, ConfigMaps—all are objects stored in etcd with:
- apiVersion (API group)
- kind (resource type)
- metadata (names, labels, annotations)
- spec (desired state)
- status (current state)

### 4. The Control Plane is a Distributed System
- API server: Front door (stateless, horizontally scalable)
- etcd: Source of truth (stateful, requires consensus)
- Scheduler: Placement engine (stateless, single active leader)
- Controllers: Reconciliation engines (stateless, single active leader per controller)

### 5. The Node is Autonomous
kubelet operates independently. If control plane dies, existing pods keep running.

### 6. Failure is Expected
Kubernetes assumes nodes fail, pods crash, networks partition. It continuously heals.

### 7. Composition Over Inheritance
Complex behaviors emerge from composing simple primitives:
- Deployment = ReplicaSet + Rolling update strategy
- StatefulSet = ReplicaSet + Stable network identity + Ordered deployment
- Job = Pod + Retry logic + Completion tracking

### 8. Everything is Asynchronous
No operation is synchronous. Create a pod → it goes to Pending → scheduler binds it → kubelet pulls image → pod runs. Each step is asynchronous.

### 9. Controllers Own Resources
Each resource type has an owning controller. Don't fight the controllers—they'll win.

### 10. Labels are Glue
Labels connect resources:
- Services find pods via labels
- ReplicaSets find pods via labels
- Network policies target pods via labels
- Everything uses labels for selection

**Next:** [Service Mesh - Traffic Management at Scale](./service-mesh.md)
