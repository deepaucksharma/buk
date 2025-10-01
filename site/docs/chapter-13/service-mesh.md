# Service Mesh: The Network Layer You Can Finally See

## Introduction: The Invisible Infrastructure

In 2016, engineers at Lyft faced a problem. They had 100+ microservices communicating over the network. Every service needed:
- Retry logic for failed requests
- Circuit breakers to prevent cascading failures
- Load balancing across instances
- Mutual TLS for security
- Request tracing for debugging
- Metrics collection for monitoring

Each team implemented these features differently. In Java. In Python. In Go. The same infrastructure logic, duplicated across every service, in every language, with bugs and inconsistencies everywhere.

Then they asked: **What if networking infrastructure wasn't library code in every service, but infrastructure that lived next to every service?**

This insight led to Envoy, and Envoy led to service meshes.

### The Service Mesh Mental Model

A service mesh is **infrastructure for service-to-service communication**. Instead of embedding networking logic in application code, you run a proxy next to each service that handles all network concerns.

```
WITHOUT Service Mesh:
App A ────[network logic in app]────► App B
      retry, timeout, TLS, metrics

WITH Service Mesh:
App A ────► Proxy A ══════════► Proxy B ────► App B
            [all network         [all network
             logic here]          logic here]
```

The application makes a simple HTTP/gRPC call to localhost. The proxy (sidecar) intercepts the request, applies policies, routes it intelligently, encrypts it, collects telemetry, and forwards it to the destination's proxy.

**The value proposition:**
- **Polyglot**: Works with any language (Java, Python, Go, Rust—doesn't matter)
- **Consistent**: Same behavior across all services
- **Observable**: Every request measured, traced, logged
- **Secure**: Encryption and authentication by default
- **Controllable**: Change behavior without changing code

### Why Service Meshes Emerged

The shift to microservices created a networking nightmare:

**Monolith (2010):**
```
┌──────────────────────────────┐
│                              │
│         Monolith             │
│  ┌──────┐    ┌───────┐      │
│  │Users │───►│Orders │      │
│  └──────┘    └───┬───┘      │
│               ▼   │          │
│         ┌──────────┐         │
│         │ Payment  │         │
│         └──────────┘         │
│                              │
└──────────────────────────────┘
    1 network call (localhost)
```

**Microservices (2020):**
```
┌────────┐     ┌────────┐     ┌─────────┐
│ Users  │────►│ Orders │────►│ Payment │
│Service │     │Service │     │ Service │
└────────┘     └────┬───┘     └─────────┘
                    │
                    ├──────►┌──────────┐
                    │       │Inventory │
                    │       │ Service  │
                    │       └──────────┘
                    │
                    └──────►┌──────────┐
                            │ Shipping │
                            │ Service  │
                            └──────────┘

    50+ network calls per user request
```

Each call can fail. Each call needs retry logic, timeouts, circuit breakers, rate limiting, authentication, encryption, monitoring, tracing.

**The old solution:** Write libraries for common functionality. Every team imports the library.

**The problem:**
- Library updates require redeploying all services
- Different languages need different implementations
- Libraries have bugs (timeouts don't work, retries are aggressive)
- No centralized control (can't change timeout globally)
- No universal observability (each service logs differently)

**The service mesh solution:** Move infrastructure out of application code into sidecar proxies. Update proxy configuration without redeploying applications.

## The Sidecar Proxy Pattern

The sidecar is the fundamental building block.

### What is a Sidecar?

A sidecar is an auxiliary container that runs in the same pod as your application container.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-sidecar
spec:
  containers:
  # Application container
  - name: app
    image: my-app:v1
    ports:
    - containerPort: 8080

  # Sidecar proxy container
  - name: envoy-proxy
    image: envoyproxy/envoy:v1.27.0
    ports:
    - containerPort: 15001  # Proxy inbound traffic
    - containerPort: 15000  # Proxy admin interface
```

Both containers:
- Share the same network namespace (same localhost, same IP)
- Share the same lifecycle (start together, stop together)
- Can share volumes for config files

### Traffic Interception

The sidecar intercepts all traffic to/from the application using iptables rules:

```bash
# Inbound traffic interception
# Redirect all inbound traffic to proxy (port 15001)
iptables -t nat -A PREROUTING -p tcp -j REDIRECT --to-port 15001

# Outbound traffic interception
# Redirect all outbound traffic to proxy (port 15001)
iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-port 15001

# Exceptions (don't intercept traffic to proxy itself)
iptables -t nat -A OUTPUT -p tcp -m owner --uid-owner 1337 -j RETURN
```

**The traffic flow:**

```
Inbound request:
  External → Pod IP:8080 → [iptables redirect] → Proxy:15001 → App:8080

Outbound request:
  App:8080 → other-service:8080 → [iptables redirect] → Proxy:15001 → External
```

The application is unaware. It thinks it's making normal network calls.

### Envoy Proxy: The Engine

Envoy (created by Lyft, now CNCF project) is the most popular service mesh proxy.

**Core features:**
- **Dynamic configuration**: Update config without restart
- **Advanced load balancing**: Round robin, least request, ring hash, random
- **Health checking**: Active and passive health checks
- **Circuit breaking**: Protect against cascading failures
- **Rate limiting**: Global and local rate limits
- **Observability**: Metrics, distributed tracing, access logs
- **TLS**: mTLS for service-to-service communication

**Envoy configuration example:**

```yaml
# Envoy configuration (simplified)
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 15001
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: backend_cluster
                  timeout: 5s
                  retry_policy:
                    retry_on: "5xx"
                    num_retries: 3
          http_filters:
          - name: envoy.filters.http.router

  clusters:
  - name: backend_cluster
    connect_timeout: 1s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: backend_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: backend-service
                port_value: 8080
    # Health checking
    health_checks:
    - timeout: 1s
      interval: 5s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: "/health"
    # Circuit breaking
    circuit_breakers:
      thresholds:
      - priority: DEFAULT
        max_connections: 1000
        max_pending_requests: 100
        max_requests: 1000
        max_retries: 3
```

## Service Mesh Implementations

### Istio: The Full-Featured Option

Istio is the most feature-rich service mesh. Developed by Google, IBM, and Lyft.

**Architecture:**

```
┌─────────────────────────────────────────────┐
│            Control Plane                     │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
│  │ istiod  │  │ Pilot    │  │ Citadel   │  │
│  │ (unified│  │(traffic  │  │(security/ │  │
│  │component│  │ mgmt)    │  │ certs)    │  │
│  └────┬────┘  └────┬─────┘  └─────┬─────┘  │
└───────┼────────────┼──────────────┼─────────┘
        │            │              │
        │  (config)  │   (certs)    │
        ▼            ▼              ▼
┌──────────────────────────────────────────────┐
│              Data Plane                       │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │App + 📦 │    │App + 📦 │    │App + 📦 │  │
│  │ Envoy   │◄──►│ Envoy   │◄──►│ Envoy   │  │
│  └─────────┘    └─────────┘    └─────────┘  │
│     Pod 1          Pod 2          Pod 3      │
└──────────────────────────────────────────────┘
```

**Istio concepts:**

**1. VirtualService (routing rules):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: backend-route
spec:
  hosts:
  - backend-service
  http:
  # Route 90% of traffic to v1
  - match:
    - headers:
        user-type:
          exact: "internal"
    route:
    - destination:
        host: backend-service
        subset: v2
      weight: 100

  # Route 90% to v1, 10% to v2 (canary deployment)
  - route:
    - destination:
        host: backend-service
        subset: v1
      weight: 90
    - destination:
        host: backend-service
        subset: v2
      weight: 10
```

**2. DestinationRule (traffic policies):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: backend-destination
spec:
  host: backend-service

  # Define subsets (versions)
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2

  # Traffic policy (applies to all subsets)
  trafficPolicy:
    # Load balancing
    loadBalancer:
      consistentHash:
        httpHeaderName: "user-id"  # Sticky sessions by user

    # Connection pool settings
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10
        http2MaxRequests: 100
        maxRequestsPerConnection: 2

    # Circuit breaking
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**3. Gateway (ingress/egress):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: frontend-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: frontend-cert
    hosts:
    - "app.example.com"

---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: frontend-route
spec:
  hosts:
  - "app.example.com"
  gateways:
  - frontend-gateway
  http:
  - match:
    - uri:
        prefix: "/api"
    route:
    - destination:
        host: backend-service
        port:
          number: 8080
```

**Production Istio configuration:**

```yaml
# IstioOperator for production deployment
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: production-istio
spec:
  # Use production profile
  profile: production

  # High availability control plane
  components:
    pilot:
      k8s:
        replicas: 3
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        hpaSpec:
          minReplicas: 3
          maxReplicas: 10
          metrics:
          - type: Resource
            resource:
              name: cpu
              target:
                type: Utilization
                averageUtilization: 80

  # Mesh configuration
  meshConfig:
    # Enable access logging
    accessLogFile: /dev/stdout
    accessLogFormat: |
      [%START_TIME%] "%REQ(:METHOD)% %REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%" %RESPONSE_CODE% %RESPONSE_FLAGS% %BYTES_RECEIVED% %BYTES_SENT% %DURATION% "%REQ(X-FORWARDED-FOR)%" "%REQ(USER-AGENT)%"

    # Distributed tracing
    enableTracing: true
    defaultConfig:
      tracing:
        sampling: 1.0  # 100% sampling (reduce in production)
        zipkin:
          address: zipkin.istio-system:9411

    # Automatic mTLS
    enableAutoMtls: true

    # Outbound traffic policy
    outboundTrafficPolicy:
      mode: REGISTRY_ONLY  # Only allow traffic to registered services
```

**Real-world Istio experience (Airbnb):**

Airbnb migrated to Istio in 2019. Key learnings:

1. **CPU overhead:** Envoy sidecar adds 10-20% CPU overhead per pod. Budget accordingly.
2. **Memory overhead:** Each Envoy sidecar uses 50-100 MB. With 1000 pods, that's 50-100 GB just for proxies.
3. **Latency:** Adds 1-2ms per hop (acceptable for most workloads).
4. **Complexity:** Istio has a steep learning curve. Invest in training.
5. **Debugging:** When something breaks, is it the app, Envoy, or Istio? New failure modes.

**Worth it?** Yes, for organizations with 50+ microservices. Below that, consider simpler options.

### Linkerd: The Lightweight Alternative

Linkerd (now Linkerd2) is a simpler, lighter service mesh focused on ease of use.

**Architecture:**

```
┌─────────────────────────────────────────┐
│         Control Plane                    │
│  ┌──────────┐  ┌──────────┐            │
│  │ Controller│  │ Identity │            │
│  │ (config)  │  │ (certs)  │            │
│  └─────┬────┘  └────┬─────┘            │
└────────┼────────────┼───────────────────┘
         │            │
         ▼            ▼
┌────────────────────────────────────────┐
│           Data Plane                    │
│  ┌──────────┐    ┌──────────┐         │
│  │App + 📦  │    │App + 📦  │         │
│  │Linkerd   │◄──►│Linkerd   │         │
│  │ Proxy    │    │ Proxy    │         │
│  └──────────┘    └──────────┘         │
└────────────────────────────────────────┘
```

**Key differences from Istio:**
- **Simpler:** Fewer concepts, easier to understand
- **Lighter:** Linkerd proxy (Rust-based) uses less memory than Envoy
- **Faster:** Lower latency overhead (< 1ms)
- **Less flexible:** Fewer features than Istio

**Linkerd installation:**

```bash
# Install Linkerd CLI
curl -sL https://run.linkerd.io/install | sh

# Install Linkerd control plane
linkerd install | kubectl apply -f -

# Verify installation
linkerd check

# Inject sidecar into namespace
kubectl annotate namespace production linkerd.io/inject=enabled

# Or inject into specific deployment
kubectl get deploy/app -o yaml | linkerd inject - | kubectl apply -f -
```

**Automatic mTLS:**

Linkerd automatically encrypts all service-to-service traffic. No configuration needed.

```bash
# Check mTLS status
linkerd -n production stat deploy

NAME      MESHED   SUCCESS   RPS   LATENCY_P50   LATENCY_P95   LATENCY_P99   TLS
app         3/3    100.00%   5.2rps      1ms           2ms           3ms      100%
backend     3/3    100.00%   5.2rps      2ms           4ms           6ms      100%
database    3/3    100.00%   5.2rps      5ms          10ms          15ms      100%
```

**Traffic splitting (canary):**

```yaml
apiVersion: split.smi-spec.io/v1alpha1
kind: TrafficSplit
metadata:
  name: backend-split
  namespace: production
spec:
  service: backend-service
  backends:
  - service: backend-v1
    weight: 900  # 90%
  - service: backend-v2
    weight: 100  # 10%
```

**Production consideration (financial services company):**

A financial services company chose Linkerd over Istio because:
- Regulatory compliance favored simpler systems (easier to audit)
- Linkerd's lower resource usage saved $200K/year in infrastructure costs
- Faster time to production (2 months vs 6 months estimated for Istio)

**Trade-off:** They later hit Linkerd's feature limitations (no advanced routing) and considered migrating to Istio.

### Consul Connect: The HashiCorp Option

Consul Connect is a service mesh built on top of HashiCorp Consul (service discovery and KV store).

**Unique features:**
- **Multi-platform:** Works on VMs, Kubernetes, bare metal
- **Multi-datacenter:** Native support for multiple datacenters
- **Intentions:** Simple policy model (Service A can/cannot talk to Service B)

**Architecture:**

```
┌─────────────────────────────────────────┐
│       Consul Servers (cluster)          │
│  ┌──────┐  ┌──────┐  ┌──────┐          │
│  │Server│  │Server│  │Server│          │
│  │  1   │  │  2   │  │  3   │          │
│  └──┬───┘  └──┬───┘  └──┬───┘          │
└─────┼────────┼────────┼────────────────┘
      │        │        │
      └────────┴────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐      ┌────▼────┐
│Consul  │      │Consul   │
│Agent + │      │Agent +  │
│Envoy   │◄────►│Envoy    │
│        │      │         │
│App     │      │App      │
└────────┘      └─────────┘
```

**Service registration:**

```hcl
# Service registration
service {
  name = "web"
  port = 8080

  connect {
    sidecar_service {
      proxy {
        upstreams = [
          {
            destination_name = "backend"
            local_bind_port  = 9191
          }
        ]
      }
    }
  }

  checks = [
    {
      http     = "http://localhost:8080/health"
      interval = "10s"
      timeout  = "1s"
    }
  ]
}
```

**Intentions (access control):**

```hcl
# Allow web service to call backend service
intention {
  source_name      = "web"
  destination_name = "backend"
  action           = "allow"
}

# Deny all other access to backend
intention {
  source_name      = "*"
  destination_name = "backend"
  action           = "deny"
}
```

**When to use Consul Connect:**
- Hybrid environments (Kubernetes + VMs)
- Multi-datacenter deployments
- Already using HashiCorp stack (Vault, Nomad, Terraform)

## Traffic Management Patterns

### Circuit Breaking

Prevent cascading failures by stopping requests to failing services.

**The problem:**

```
Service A → Service B → Service C
              (slow/failing)

1. Service C starts failing (high latency)
2. Service B waits for C responses
3. Service B's threads/connections exhaust
4. Service B becomes unresponsive
5. Service A waits for B responses
6. Service A's resources exhaust
7. Entire system down
```

**The solution (circuit breaker):**

```
Closed (normal) → Open (failing) → Half-Open (testing) → Closed
     ↓                ↓                    ↓
  Requests      Fail fast          Limited requests
  pass through  (no waiting)       (check if recovered)
```

**Circuit breaker states:**

1. **Closed:** Requests pass through normally
2. **Open:** After N consecutive failures, circuit opens. Requests fail immediately (no calls to backend)
3. **Half-Open:** After timeout, try a few requests. If they succeed, close the circuit. If they fail, stay open.

**Implementation (Istio):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: backend-circuit-breaker
spec:
  host: backend-service
  trafficPolicy:
    outlierDetection:
      # After 5 consecutive errors
      consecutiveErrors: 5
      # Check every 30 seconds
      interval: 30s
      # Eject for 30 seconds (open circuit)
      baseEjectionTime: 30s
      # Eject up to 50% of instances
      maxEjectionPercent: 50
      # Require 1 success to close (half-open → closed)
      minHealthPercent: 50
```

**Real failure prevented (video streaming company):**

A video streaming company had backend service calling recommendation service. One day:
- Recommendation service deployed a bug (infinite loop)
- All recommendation instances became unresponsive
- Backend service kept retrying (no circuit breaker)
- Backend exhausted connections
- Frontend couldn't reach backend
- Entire site down

**With circuit breaker:**
- Recommendation service starts failing
- Circuit breaker opens after 5 failures
- Backend immediately returns cached recommendations (fallback)
- Users see slightly stale recommendations but site stays up
- Recommendation service fixed and redeployed
- Circuit closes, normal service resumes

**Impact:** Prevented 30-minute outage. $500K+ in lost revenue avoided.

### Retry Logic

Automatically retry transient failures.

**When to retry:**
- Network glitches (packet loss)
- Service temporarily overloaded (503 Service Unavailable)
- Instance restarting (connection refused)

**When NOT to retry:**
- Client errors (400 Bad Request, 401 Unauthorized)
- Idempotency issues (POST requests that aren't idempotent)
- Server errors that won't recover (500 Internal Server Error with bug)

**Retry configuration (Istio):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: backend-retries
spec:
  hosts:
  - backend-service
  http:
  - route:
    - destination:
        host: backend-service
    timeout: 10s
    retries:
      # Retry on connection failures and 503 responses
      attempts: 3
      perTryTimeout: 3s
      retryOn: "5xx,reset,connect-failure,refused-stream"
```

**Exponential backoff:**

Don't retry immediately. Back off exponentially to avoid overwhelming the recovering service.

```python
import time
import random

def call_with_retry(service, max_retries=3):
    for attempt in range(max_retries):
        try:
            return service.call()
        except Exception as e:
            if attempt == max_retries - 1:
                raise  # Last attempt, give up

            # Exponential backoff: 1s, 2s, 4s
            wait_time = (2 ** attempt) + random.uniform(0, 1)  # Add jitter
            time.sleep(wait_time)
```

**Jitter:** Random variation prevents "thundering herd" (all clients retry at same time).

### Timeout Configuration

Set explicit timeouts to prevent hanging requests.

**The problem:**

```python
# No timeout - waits forever
response = requests.get("http://slow-service/")
```

If the service hangs, this request waits indefinitely. Thread/connection leaks.

**The solution:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: backend-timeouts
spec:
  hosts:
  - backend-service
  http:
  - route:
    - destination:
        host: backend-service
    timeout: 5s  # Total timeout
    retries:
      attempts: 3
      perTryTimeout: 1s  # Per-attempt timeout
```

**Timeout budget:**

```
Total timeout: 5s
  - Attempt 1: 1s timeout
  - Attempt 2: 1s timeout (after backoff)
  - Attempt 3: 1s timeout (after backoff)
  - Total: ~3-4s (depending on backoff)
```

**Production practice:** Set timeouts at every layer:

```
Load Balancer: 60s
  ├─► API Gateway: 30s
      ├─► Backend Service: 10s
          ├─► Database: 5s
```

Each layer's timeout should be shorter than the layer above.

### Load Balancing Algorithms

**1. Round Robin (default):**
```
Request 1 → Instance A
Request 2 → Instance B
Request 3 → Instance C
Request 4 → Instance A (repeat)
```

Simple, fair, but doesn't account for instance load.

**2. Least Request:**
```
Request → Instance with fewest active requests
```

Better than round robin. Accounts for instance load.

**3. Consistent Hash:**
```
hash(user_id) → Instance

Same user always goes to same instance (sticky sessions)
```

Useful for caching (each instance caches data for its users).

**4. Random:**
```
Request → Random instance
```

Surprisingly effective. Simpler than least request, nearly as good.

**Configuration (Istio):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: backend-lb
spec:
  host: backend-service
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "user-id"  # Hash by user ID
        minimumRingSize: 1024
```

### Canary Deployments

Gradually roll out new versions to reduce risk.

**The strategy:**

```
Phase 1: 95% → v1, 5% → v2 (canary)
  Monitor metrics. If good, proceed. If bad, rollback.

Phase 2: 90% → v1, 10% → v2
  Monitor. If good, proceed.

Phase 3: 75% → v1, 25% → v2
  Monitor. If good, proceed.

Phase 4: 50% → v1, 50% → v2
  Monitor. If good, proceed.

Phase 5: 0% → v1, 100% → v2
  Fully deployed.
```

**Implementation (Istio):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: backend-canary
spec:
  hosts:
  - backend-service
  http:
  - match:
    - headers:
        user-type:
          exact: "internal"
    route:
    - destination:
        host: backend-service
        subset: v2
      weight: 100
  - route:
    - destination:
        host: backend-service
        subset: v1
      weight: 95
    - destination:
        host: backend-service
        subset: v2
      weight: 5
```

**Automated canary with Flagger:**

Flagger automates canary deployments based on metrics.

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: backend
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend

  service:
    port: 8080

  # Canary analysis
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 5

    # Metrics to check
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500  # 500ms
      interval: 1m

    # Rollback conditions
    webhooks:
    - name: load-test
      url: http://flagger-loadtester/
      timeout: 5s
      metadata:
        cmd: "hey -z 1m -q 10 -c 2 http://backend:8080/"
```

**How it works:**
1. Deploy v2 with 0% traffic
2. Gradually increase traffic: 5%, 10%, 15%, ..., 50%
3. At each step, check metrics (success rate, latency)
4. If metrics are good, proceed to next step
5. If metrics are bad, rollback to v1
6. If all steps succeed, promote v2 to 100%

**Real-world canary (fintech company):**

A fintech company deployed a new payment service version with a canary:
- Phase 1 (5% traffic): Error rate spiked to 10% (normal: 0.1%)
- Automatic rollback triggered within 2 minutes
- Impact: 5% of users saw errors for 2 minutes
- Without canary: 100% of users would have seen errors

**Cost:** 2 minutes × 5% users = 0.1% of traffic affected

**Benefit:** Prevented impacting 100% of users for potentially 30 minutes

## Observability

### Distributed Tracing

Track requests across multiple services.

**The problem:**

```
User request → API Gateway → Service A → Service B → Service C → Database
                                                      ↓
                                                  Service D
```

Request takes 5 seconds. Where's the bottleneck?

**The solution (distributed tracing):**

Each service adds trace context to requests:

```
Trace ID: abc123
  Span 1 (API Gateway): 50ms
    Span 2 (Service A): 100ms
      Span 3 (Service B): 200ms
        Span 4 (Service C): 4500ms  ← BOTTLENECK
          Span 5 (Database): 4400ms  ← ROOT CAUSE
        Span 6 (Service D): 100ms
```

**Implementation (automatic with service mesh):**

Service mesh sidecars automatically add trace headers:

```
X-B3-TraceId: abc123def456
X-B3-SpanId: def456
X-B3-ParentSpanId: abc123
X-B3-Sampled: 1
```

**Viewing traces (Jaeger):**

```bash
# Install Jaeger
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.19/samples/addons/jaeger.yaml

# Forward port
kubectl port-forward -n istio-system svc/jaeger-query 16686:16686

# Open http://localhost:16686
```

**Example trace:**

```
Trace: User checkout request (5.2s total)
├─ API Gateway (50ms)
│  └─ Authentication (30ms)
├─ Cart Service (150ms)
│  ├─ Get cart from Redis (20ms)
│  └─ Validate items (130ms)
├─ Inventory Service (200ms)
│  ├─ Check stock (150ms)
│  └─ Reserve items (50ms)
├─ Payment Service (4500ms)  ← SLOW
│  ├─ Validate card (100ms)
│  ├─ Call payment gateway (4300ms)  ← VERY SLOW
│  │  ├─ Network (200ms)
│  │  └─ Payment processing (4100ms)  ← ROOT CAUSE
│  └─ Update database (100ms)
└─ Notification Service (100ms)
   └─ Send email (90ms)
```

**Root cause:** Payment gateway is slow. Investigate with gateway provider.

### Metrics Collection

Service mesh automatically collects metrics:

**Request metrics:**
- Requests per second (RPS)
- Error rate (%)
- Latency (p50, p95, p99)
- Success rate (%)

**Connection metrics:**
- Active connections
- Connection errors
- Connection timeouts

**Example metrics (Prometheus format):**

```
# Request rate
istio_requests_total{source="frontend",destination="backend",response_code="200"} 1234

# Request duration
istio_request_duration_milliseconds_bucket{le="100"} 900  # 900 requests < 100ms
istio_request_duration_milliseconds_bucket{le="500"} 1200  # 1200 requests < 500ms
istio_request_duration_milliseconds_bucket{le="1000"} 1234  # 1234 requests < 1000ms

# Success rate
istio_request_success_rate{source="frontend",destination="backend"} 0.998  # 99.8%
```

**Grafana dashboard:**

```
┌─────────────────────────────────────────────────┐
│          Backend Service Dashboard              │
├─────────────────────────────────────────────────┤
│  RPS:      1234 req/s   ↑ 10%                   │
│  Success:  99.8%        ↓ 0.1%                  │
│  P50:      50ms         → 0ms                   │
│  P95:      200ms        ↑ 20ms                  │
│  P99:      500ms        ↑ 100ms                 │
├─────────────────────────────────────────────────┤
│  [Graph: Request Rate over time]                │
│  [Graph: Latency percentiles over time]         │
│  [Graph: Error rate by endpoint]                │
└─────────────────────────────────────────────────┘
```

### Access Logs

Every request logged:

```json
{
  "timestamp": "2023-10-01T14:32:01Z",
  "source": {
    "workload": "frontend-v1",
    "namespace": "production",
    "ip": "10.0.1.5"
  },
  "destination": {
    "workload": "backend-v2",
    "namespace": "production",
    "ip": "10.0.2.3"
  },
  "request": {
    "method": "POST",
    "path": "/api/orders",
    "protocol": "HTTP/1.1",
    "user_agent": "Mozilla/5.0...",
    "headers": {
      "x-user-id": "user123",
      "x-request-id": "abc-def-123"
    }
  },
  "response": {
    "code": 200,
    "duration_ms": 42,
    "bytes": 1024
  },
  "tls": {
    "enabled": true,
    "version": "TLSv1.3"
  }
}
```

**Use cases:**
- Audit compliance (who accessed what?)
- Debugging (what was the request that failed?)
- Security (detect anomalous access patterns)

## Mental Model Summary

### Service Mesh Core Principles

1. **Sidecar Pattern**
   - Infrastructure runs alongside application
   - Application is unaware of service mesh
   - Network concerns separated from business logic

2. **Declarative Configuration**
   - Declare desired behavior (retry 3 times)
   - Mesh ensures it happens
   - No code changes needed

3. **Observability by Default**
   - Every request measured
   - Distributed tracing automatic
   - Metrics collected without instrumentation

4. **Security by Default**
   - mTLS automatic
   - Authentication/authorization enforced
   - Zero-trust networking

5. **Progressive Delivery**
   - Canary deployments
   - A/B testing
   - Traffic shifting
   - Blue-green deployments

### When to Use a Service Mesh

**Use a service mesh when:**
- 50+ microservices
- Polyglot environment (multiple languages)
- Need consistent behavior (retries, timeouts, circuit breakers)
- Compliance requirements (mTLS, audit logs)
- Complex traffic routing (canary, A/B testing)

**Don't use a service mesh when:**
- < 10 microservices (overhead not worth it)
- Monolith or small number of services
- Team lacks Kubernetes/networking expertise
- Latency budget is very tight (< 10ms)

### Service Mesh Trade-offs

**Pros:**
- Consistent networking behavior
- Observability without code changes
- Security by default
- Traffic control without deployments

**Cons:**
- Complexity (new failure modes)
- Resource overhead (CPU, memory)
- Latency overhead (1-2ms per hop)
- Learning curve

**Production reality:** Service meshes are powerful but complex. Start small. Enable gradually. Invest in training. Monitor carefully.

**Next:** [GitOps - Infrastructure as Code at Scale](./gitops.md)
