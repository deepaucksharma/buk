# Containers: The Shipping Revolution for Code

## Introduction

In 1956, Malcolm McLean revolutionized global trade by loading 58 shipping containers onto a converted tanker ship. Before containers, cargo was loaded and unloaded piece by piece—a slow, labor-intensive process that could take weeks. After containers, the same ship could be loaded in hours. The standardized metal box changed everything.

Sixty years later, Solomon Hykes and his team at dotCloud (later Docker Inc.) would trigger a similar revolution in software. But instead of standardizing how physical goods move around the world, they standardized how code moves from a developer's laptop to production servers.

### The Shipping Container Analogy

The parallels are striking:

**Before shipping containers:**
- Different ports had different loading equipment
- Goods were damaged during transfers
- Ships sat idle while being loaded
- Costs were prohibitively high
- International trade was limited

**Before software containers:**
- Different servers had different configurations
- Applications broke during deployment
- Servers sat idle due to inefficiency
- Infrastructure costs were high
- Deployment was risky and slow

**After standardization:**
- Any container fits any ship, truck, or crane
- Contents are protected and isolated
- Loading/unloading is fast and automated
- Costs dropped dramatically
- Global trade exploded

Sound familiar? This is exactly what happened to software deployment.

### Why Containers Changed Everything

The "works on my machine" problem was the bane of every developer's existence:

```bash
# Developer's laptop
$ python --version
Python 3.9.5

$ npm --version
7.19.0

$ ./run_app.sh
✓ Server started on port 8080
✓ Connected to database
✓ All tests passing

# Production server (6 hours later)
$ python --version
Python 2.7.16

$ npm --version
5.6.0

$ ./run_app.sh
✗ ModuleNotFoundError: No module named 'asyncio'
✗ SyntaxError: invalid syntax
✗ Everything is on fire
```

The conversation that followed was always the same:

**Developer:** "But it works on my machine!"
**Ops:** "Well, it doesn't work in production."
**Developer:** "Did you install all the dependencies?"
**Ops:** "I thought I did..."
**Developer:** "What version of Python are you running?"
**Ops:** "...the one that came with the OS?"

Containers solved this by packaging the application AND its entire runtime environment into a single, portable unit. Now the conversation is different:

**Developer:** "Here's the container image."
**Ops:** "Thanks, it's running."

### From "Works on My Machine" to Works Everywhere

The genius of containers isn't just isolation—it's the complete inversion of the deployment paradigm.

**Old way (configuration management):**
1. Write application code
2. Write deployment scripts
3. Document dependencies
4. Configure servers
5. Deploy and pray
6. Debug environment differences
7. Repeat for each environment

**New way (containers):**
1. Write application code
2. Write Dockerfile
3. Build image
4. Run anywhere
5. Done

The application and its environment become inseparable. They travel together, always in sync, always compatible.

### The Democratization of Deployment

Before containers, deploying complex applications required:
- Dedicated operations teams
- Extensive documentation
- Environment-specific scripts
- Deep system administration knowledge
- Costly infrastructure

After containers:
- Developers can deploy their own apps
- The Dockerfile IS the documentation
- One image works everywhere
- Docker handles the system stuff
- Run on anything from a Raspberry Pi to AWS

This democratization is perhaps the most profound impact. A solo developer can now deploy applications with the same sophistication as major corporations. The barrier to entry collapsed.

## The Pre-Container World

To truly appreciate containers, we need to understand the pain they eliminated. The pre-container world wasn't just inconvenient—it was fundamentally broken.

### The Dependency Hell

Every application is an iceberg. The code you write is just the tip. Below the surface lurks a massive tangle of dependencies:

```
Your Application (100 lines)
    ↓ depends on
Web Framework (10,000 lines)
    ↓ depends on
HTTP Library (5,000 lines)
    ↓ depends on
SSL Library (50,000 lines)
    ↓ depends on
Crypto Library (100,000 lines)
    ↓ depends on
System Libraries (1,000,000 lines)
    ↓ depends on
Operating System (10,000,000+ lines)
```

Each dependency has:
- Version requirements
- Transitive dependencies
- System library needs
- Configuration expectations
- Compilation requirements

The result? **Dependency hell:**

```bash
# Install Application A
$ pip install app-a
Collecting app-a
  Requires: library-x==1.2.0
  Installing library-x-1.2.0
✓ Success!

# Install Application B
$ pip install app-b
Collecting app-b
  Requires: library-x==2.0.0
  Found existing: library-x-1.2.0
  Uninstalling library-x-1.2.0
  Installing library-x-2.0.0
✓ Success!

# Run Application A
$ app-a
Error: library-x 1.2.0 required, found 2.0.0
✗ Failed!

# Welcome to dependency hell
```

Multiply this by dozens of applications on a single server, and you have chaos.

### Configuration Drift

In the old world, servers were **pets**, not **cattle**. Each one had a name, a history, and a unique configuration:

```
web-server-01 (The Original)
├── Installed: 2015-03-14
├── Ubuntu 14.04 (never upgraded)
├── Nginx 1.8.0
├── PHP 5.6 (compiled from source)
├── Custom SSL config (from that one midnight incident)
├── Mystery cronjob (added by intern, no documentation)
└── That one file someone edited directly (no one knows why)

web-server-02 (The Clone Attempt)
├── Installed: 2017-08-22
├── Ubuntu 16.04 (we upgraded this one)
├── Nginx 1.12.0
├── PHP 7.0 (from apt)
├── SSL config (copy-pasted, probably wrong)
├── Different cronjobs (best guess)
└── Missing that mystery file (oops)
```

These servers were **snowflakes**—each one unique, each one fragile, each one impossible to reproduce.

The problems:
- **Undocumented changes**: "Who edited that config file at 2 AM?"
- **Impossible reproduction**: "How do we create another server like this?"
- **Deployment roulette**: "Will this work on server-02? Maybe?"
- **Debugging nightmares**: "It works on one server but not the other..."

### The Deployment Dance

Deploying applications was a ritualistic dance of hope and fear:

**Step 1: The FTP Upload**
```bash
# Connect to production via FTP
ftp production.example.com
ftp> cd /var/www/html
ftp> put index.php
ftp> put app.php
ftp> put database.php
# Wait... did I update database.php locally?
# Better re-upload to be safe
ftp> put database.php
# Connection lost
# Start over
```

**Step 2: SSH and Pray**
```bash
ssh user@production.example.com

# Set permissions (copy-pasted from notes)
chmod 755 *.php
chown www-data:www-data *.php

# Restart service
sudo service apache2 restart

# Check if it worked
curl localhost
# 500 Internal Server Error
# Cool, cool, cool
```

**Step 3: The Debug Session**
```bash
# Check logs
tail -f /var/log/apache2/error.log
# [PHP Fatal error: Class not found]

# Check PHP version
php --version
# PHP 5.4.16 (Wait, production is on 5.4? My laptop has 7.2!)

# Try to install PHP 7.2
sudo apt-get install php7.2
# Unable to locate package php7.2

# Add repository
sudo add-apt-repository ppa:ondrej/php
# [30 minutes of dependency installation]

# Restart Apache
sudo service apache2 restart
# [apache2: Syntax error on line 140]

# Fix config
sudo nano /etc/apache2/apache2.conf
# [Make changes]

# Restart again
sudo service apache2 restart
# ✓ Success!

# Test the app
curl localhost
# 500 Internal Server Error
# Different error this time though! Progress!
```

This could go on for hours. Days, even.

**Step 4: Environment-Specific Builds**

Some teams tried to solve this with environment-specific builds:

```
deploy/
├── dev.env
├── staging.env
├── production.env
├── deploy-dev.sh
├── deploy-staging.sh
├── deploy-production.sh
├── rollback-dev.sh
├── rollback-staging.sh
├── rollback-production.sh
└── please-work.sh  # The nuclear option
```

Each script was slightly different, each environment had quirks, and nothing was truly reliable.

## Container Fundamentals

Now that we've lived through the pain, let's understand how containers solve it. At its core, a container is deceptively simple: **it's just a process with superpowers**.

### What Is a Container?

A container is NOT:
- A virtual machine (though it feels like one)
- A completely separate operating system
- Magic (though it feels like magic)

A container IS:
- A process running on your host OS
- Isolated using Linux kernel features
- Constrained in its resource usage
- Living in its own filesystem view

Here's the key insight: **Containers share the host kernel but have isolated everything else.**

```
Host OS (Linux Kernel)
    ├── Container 1
    │   ├── Own process tree
    │   ├── Own filesystem
    │   ├── Own network stack
    │   └── Own resource limits
    │
    ├── Container 2
    │   ├── Own process tree
    │   ├── Own filesystem
    │   ├── Own network stack
    │   └── Own resource limits
    │
    └── Container 3
        ├── Own process tree
        ├── Own filesystem
        ├── Own network stack
        └── Own resource limits
```

All three containers share the same kernel, but they can't see each other. It's like living in an apartment building—everyone shares the foundation, but each apartment is private.

### Linux Building Blocks

Containers aren't new technology. They're a clever combination of Linux features that have existed for years:

#### Namespaces: The Isolation Technology

Namespaces are the core isolation mechanism. They make processes believe they're alone in the world:

```c
// Types of namespaces
CLONE_NEWPID    // Process IDs - your process tree looks isolated
CLONE_NEWNET    // Network - your own network interfaces
CLONE_NEWNS     // Mount points - your own filesystem view
CLONE_NEWUTS    // Hostname - your own hostname
CLONE_NEWIPC    // IPC - your own message queues
CLONE_NEWUSER   // User IDs - your own user/group mapping
CLONE_NEWCGROUP // Cgroups - your own cgroup root
```

**PID Namespace Example:**

```bash
# On the host
$ ps aux
USER   PID  COMMAND
root     1  /sbin/init
root   123  nginx
root   456  postgres
root   789  python app.py

# Inside a container (PID namespace)
$ ps aux
USER   PID  COMMAND
root     1  python app.py  # This is actually PID 789 on the host!
```

The container's process thinks it's PID 1 (the init process), but the host knows it's really PID 789. This isolation prevents containers from seeing or killing each other's processes.

**Network Namespace Example:**

```bash
# Host has its network interfaces
$ ip addr
1: lo: <LOOPBACK,UP>
    inet 127.0.0.1/8
2: eth0: <BROADCAST,UP>
    inet 192.168.1.100/24

# Container has its own isolated network
$ docker exec container1 ip addr
1: lo: <LOOPBACK,UP>
    inet 127.0.0.1/8
10: eth0: <BROADCAST,UP>
    inet 172.17.0.2/16  # Different IP!
```

Each container has its own network stack—its own IP address, routing table, and firewall rules.

#### Control Groups (cgroups): The Resource Manager

Namespaces provide isolation, but cgroups provide **resource limits**. Without cgroups, a single container could consume all CPU, memory, or I/O, starving others.

```bash
# Limit CPU usage to 50%
echo 50000 > /sys/fs/cgroup/cpu/myapp/cpu.cfs_quota_us
echo 100000 > /sys/fs/cgroup/cpu/myapp/cpu.cfs_period_us
# This container gets 50,000 microseconds per 100,000 microsecond period = 50%

# Limit memory to 512MB
echo 536870912 > /sys/fs/cgroup/memory/myapp/memory.limit_in_bytes

# Limit disk I/O to 1MB/s read
echo "8:0 1048576" > /sys/fs/cgroup/blkio/myapp/blkio.throttle.read_bps_device
# 8:0 is the device (usually /dev/sda), 1048576 = 1MB in bytes
```

Cgroups track and limit:
- **CPU**: How much processor time
- **Memory**: How much RAM
- **I/O**: How much disk/network bandwidth
- **Devices**: Which devices can be accessed
- **PIDs**: How many processes can be created

#### Union Filesystems: The Efficiency Trick

Here's where containers get really clever. Instead of copying an entire OS for each container, they use **layered filesystems**:

```
┌─────────────────────────────┐
│   Container A Writable      │  ← Container A writes here
├─────────────────────────────┤
│   Application Layer         │  ← Your app code (shared)
├─────────────────────────────┤
│   Dependencies Layer        │  ← npm packages (shared)
├─────────────────────────────┤
│   Node.js Layer            │  ← Runtime (shared)
├─────────────────────────────┤
│   Base OS Layer (Ubuntu)    │  ← OS files (shared)
└─────────────────────────────┘
```

All layers except the top one are **read-only and shared**. When Container A wants to modify a file:

1. File is in read-only layer
2. File is copied to writable layer (copy-on-write)
3. Container modifies the copy
4. Original remains unchanged

This is why containers are so lightweight—they share all the common layers!

**Common Union Filesystems:**
- **OverlayFS**: Modern, fast, mainline kernel
- **AUFS**: Original Docker filesystem (legacy)
- **Device Mapper**: Block-level, used by Red Hat
- **Btrfs**: Copy-on-write filesystem
- **ZFS**: Advanced features, licensing issues

### Container vs VM: The Ultimate Showdown

People often confuse containers with VMs. Here's the definitive comparison:

| Aspect | Container | Virtual Machine |
|--------|-----------|-----------------|
| **Size** | 10-100 MB | 1-10 GB |
| **Startup** | Seconds | Minutes |
| **Resource Overhead** | ~0% (just process overhead) | 10-20% (hypervisor + guest OS) |
| **Isolation** | Process-level (shared kernel) | Full hardware virtualization |
| **Security** | Moderate (shared kernel) | Strong (separate kernel) |
| **Density** | 100s-1000s per host | 10s-100s per host |
| **Portability** | High (if same OS kernel) | Very High (any OS) |
| **Performance** | Near-native | 95-99% native |

**When to use Containers:**
- Microservices architectures
- CI/CD pipelines
- Developer environments
- Stateless applications
- High-density workloads

**When to use VMs:**
- Different OS requirements (Windows + Linux)
- Strong isolation needed (multi-tenant)
- Legacy applications
- Kernel-level customization
- Compliance requirements

**The Reality:**
Most modern architectures use **both**—VMs for strong isolation boundaries, containers for application density within those boundaries.

```
Cloud Provider
    └── Physical Server
        ├── VM 1 (Customer A)
        │   ├── Container 1
        │   ├── Container 2
        │   └── Container 3
        │
        └── VM 2 (Customer B)
            ├── Container 1
            ├── Container 2
            └── Container 3
```

This gives you the strong isolation of VMs with the efficiency of containers.

## Docker: The Game Changer

Docker didn't invent containers. Linux containers (LXC) existed years before. What Docker did was **make containers usable**.

### The Docker Innovation

Docker's innovation wasn't technical—it was experiential:

**Before Docker (LXC):**
```bash
# Create a container with LXC
sudo lxc-create -n mycontainer -t ubuntu
sudo lxc-start -n mycontainer
sudo lxc-attach -n mycontainer

# Configure networking
sudo lxc-attach -n mycontainer -- ip addr add 10.0.3.1/24 dev eth0
sudo lxc-attach -n mycontainer -- ip route add default via 10.0.3.254

# Install application
sudo lxc-attach -n mycontainer -- apt-get update
sudo lxc-attach -n mycontainer -- apt-get install nginx
sudo lxc-attach -n mycontainer -- service nginx start

# Share this setup with team?
# Write a 10-page manual and hope for the best
```

**After Docker:**
```dockerfile
# Dockerfile
FROM ubuntu
RUN apt-get update && apt-get install -y nginx
CMD ["nginx", "-g", "daemon off;"]
```

```bash
docker build -t myapp .
docker run -p 80:80 myapp
```

That's it. Two commands. The Dockerfile is the documentation, the executable, and the deployment script all in one.

### Docker Architecture

Understanding Docker's architecture helps demystify how it works:

```
┌─────────────────┐
│  Docker Client  │  ← CLI you interact with
│   (docker cli)  │
└────────┬────────┘
         │ REST API
         ↓
┌─────────────────┐
│  Docker Daemon  │  ← Manages containers
│   (dockerd)     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   containerd    │  ← High-level runtime
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│      runc       │  ← Low-level runtime (spawns containers)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│    Container    │  ← Your application
└─────────────────┘
```

**The flow:**
1. `docker run myapp` → Docker Client
2. Client sends request to Docker Daemon via REST API
3. Daemon asks containerd to start container
4. containerd calls runc to spawn the process
5. runc uses kernel features (namespaces, cgroups) to create container
6. Your application runs!

This layered architecture is why Docker became a standard—each layer can be swapped out. Don't like Docker CLI? Use another client. Want a different runtime? Use CRI-O. The interfaces are standardized.

### The Dockerfile Revolution

The Dockerfile is Docker's secret weapon. It's a **declarative recipe** for building images:

```dockerfile
# Multi-stage build example
FROM golang:1.19 AS builder
WORKDIR /app

# Copy dependency files first (better caching)
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

# Final stage - minimal image
FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/

# Copy only the binary from builder
COPY --from=builder /app/main .

CMD ["./main"]
```

This Dockerfile:
1. Uses Go 1.19 to build the application (builder stage)
2. Compiles a static binary
3. Creates a tiny Alpine Linux image (final stage)
4. Copies only the binary (not the entire Go toolchain)
5. Results in a ~15MB image instead of ~800MB

**The magic:**
- **Caching**: Each instruction creates a layer. Unchanged layers are cached.
- **Multi-stage**: Build in one stage, deploy in another
- **Reproducibility**: Same Dockerfile = same image, always
- **Documentation**: The Dockerfile IS the deployment guide

### Image Layers: The Efficiency Secret

Every Dockerfile instruction creates a **layer**. Layers are stacked and shared:

```dockerfile
FROM ubuntu:20.04          # Layer 1: Base OS (72MB)
RUN apt-get update         # Layer 2: Package index (15MB)
RUN apt-get install nginx  # Layer 3: Nginx (25MB)
COPY app /var/www          # Layer 4: Application (5MB)
                          # Total: 117MB
```

But here's the clever part:

```
Image A: ubuntu:20.04 + nginx + app1 = 117MB
Image B: ubuntu:20.04 + nginx + app2 = 117MB

Disk usage: 117MB + 5MB = 122MB (not 234MB!)
```

Layers 1-3 are **shared** between Image A and Image B. Only the application layer differs. Docker stores shared layers once.

**This is why:**
- Downloading images is fast (skip layers you have)
- Building images is fast (reuse cached layers)
- Storage is efficient (share common layers)

### Docker Commands Deep Dive

Let's move beyond `docker run hello-world` to production-ready commands:

**Building with BuildKit (Modern Docker builds):**

```bash
DOCKER_BUILDKIT=1 docker build \
  --cache-from myapp:latest \           # Use previous build as cache
  --build-arg VERSION=1.2.3 \           # Pass build-time variables
  --secret id=npm,src=$HOME/.npmrc \    # Mount secrets (not in layers!)
  --target production \                 # Build specific stage
  --platform linux/amd64 \              # Cross-platform builds
  -t myapp:1.2.3 \
  -t myapp:latest \
  .
```

**Running with Constraints (Production settings):**

```bash
docker run \
  --name myapp \
  --memory="512m" \                     # Memory limit
  --memory-swap="1g" \                  # Swap limit
  --cpus="0.5" \                        # CPU limit (50% of 1 core)
  --pids-limit=100 \                    # Max processes
  --restart=unless-stopped \            # Restart policy
  --health-cmd="curl -f http://localhost/health || exit 1" \
  --health-interval=30s \               # Check every 30s
  --health-timeout=3s \                 # Fail after 3s
  --health-retries=3 \                  # 3 failures = unhealthy
  -e DB_HOST=postgres \                 # Environment variables
  -v /data:/app/data \                  # Volume mount
  -p 8080:80 \                          # Port mapping
  --network=mynetwork \                 # Custom network
  myapp:1.2.3
```

**Advanced Networking:**

```bash
# Create overlay network (multi-host)
docker network create \
  --driver overlay \
  --subnet=10.0.0.0/16 \
  --ip-range=10.0.1.0/24 \
  --gateway=10.0.0.1 \
  --attachable \
  mynetwork

# Connect container to multiple networks
docker network connect backend myapp
docker network connect frontend myapp

# Inspect container networking
docker inspect myapp | jq '.[0].NetworkSettings'
```

**Volume Management:**

```bash
# Create named volume
docker volume create mydata

# Run with volume
docker run -v mydata:/app/data myapp

# Backup volume
docker run --rm \
  -v mydata:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/backup.tar.gz -C /source .

# Restore volume
docker run --rm \
  -v mydata:/target \
  -v $(pwd):/backup \
  alpine tar xzf /backup/backup.tar.gz -C /target
```

## Container Runtimes: Beyond Docker

Docker popularized containers, but it's not the only runtime. The industry standardized on **OCI (Open Container Initiative)**, allowing multiple implementations:

### containerd

Docker's own runtime, extracted into a separate project:

```bash
# Direct containerd usage
ctr images pull docker.io/library/nginx:latest
ctr run docker.io/library/nginx:latest mynginx

# Kubernetes uses containerd via CRI
crictl pull nginx:latest
crictl run nginx:latest
```

**Characteristics:**
- Industry standard
- CRI (Container Runtime Interface) compatible
- Used by Docker and Kubernetes
- Minimal overhead
- Stable and mature

### CRI-O

Built specifically for Kubernetes:

```bash
# CRI-O is used by Kubernetes, not directly by users
# But you can interact via crictl

crictl pull quay.io/crio/nginx:latest
crictl create nginx:latest
crictl start <container-id>
```

**Characteristics:**
- Kubernetes-native (no extra features)
- Minimal footprint
- OCI compliant
- Red Hat backed
- Simple and focused

### Firecracker

Amazon's microVM technology:

```bash
# Firecracker runs microVMs, not traditional containers
firectl \
  --kernel=vmlinux \
  --root-drive=rootfs.ext4 \
  --kernel-opts="console=ttyS0 reboot=k panic=1" \
  --cpu-count=2 \
  --mem-size=512
```

**Characteristics:**
- Boots in <125ms
- <5MB memory overhead
- Powers AWS Lambda and Fargate
- VM-level isolation with container-like speed
- KVM-based

### gVisor

Google's user-space kernel:

```bash
# Run with gVisor runtime
docker run --runtime=runsc nginx:latest
```

**Characteristics:**
- Implements syscalls in user-space
- Stronger isolation than normal containers
- Performance trade-off (20-40% overhead)
- Good for untrusted workloads
- Used in Google Cloud Run

**How it works:**
```
Container Process
    ↓ [System Call]
gVisor Sentry (User-space kernel)
    ↓ [Limited Safe Syscalls]
Host Kernel
```

Most syscalls never reach the host kernel—gVisor handles them in user-space.

### Kata Containers

The best of both worlds—VM isolation with container speed:

```bash
# Run with Kata runtime
docker run --runtime=kata-runtime nginx:latest
```

**Characteristics:**
- Each container in its own lightweight VM
- Hardware virtualization (Intel VT-x, AMD-V)
- Strong isolation
- Near-native performance
- Supported by Intel and OpenStack

**Architecture:**
```
Container
    ↓
Guest Kernel (in microVM)
    ↓
Hypervisor (QEMU/Firecracker)
    ↓
Host Kernel
```

## Container Security

Containers are **not** inherently secure. They share the host kernel, which is a massive attack surface. Security requires layers of defense:

### Attack Surface

The security boundary:

```
Container Process (Your app)
    ↓ [System Calls]
Seccomp Filter (Blocks dangerous syscalls)
    ↓ [Allowed Calls]
AppArmor/SELinux (Mandatory Access Control)
    ↓ [Policy Checks]
Capabilities (Fine-grained permissions)
    ↓ [Capability Checks]
Kernel
    ↓ [Hardware Instructions]
CPU/Memory/Devices
```

Each layer defends against different attacks.

### Security Layers

#### 1. Image Security

**The Problem:**
- Base images may have vulnerabilities
- Dependencies may be compromised
- Supply chain attacks are real

**The Solution:**

```bash
# Scan for vulnerabilities
trivy image myapp:latest

HIGH: CVE-2021-12345
  Package: openssl
  Installed: 1.1.1f
  Fixed: 1.1.1k
  Severity: HIGH

# Scan during build
docker build --security-opt seccomp=unconfined .

# Sign images (Sigstore/Cosign)
cosign sign myapp:latest

# Verify signatures before deployment
cosign verify myapp:latest
```

**Policy Enforcement:**

```yaml
# OPA/Gatekeeper policy
apiVersion: v1
kind: Policy
metadata:
  name: image-security
spec:
  images:
    - name: "*"
      required:
        - signedBy: "trusted-signer@company.com"
        - vulnerabilities:
            maxSeverity: MEDIUM
            maxCount: 0
        - baseImage:
            allowlist:
              - "gcr.io/distroless/*"
              - "alpine:latest"
```

#### 2. Runtime Security

**Run as non-root:**

```dockerfile
# Bad
FROM ubuntu
COPY app /app
CMD ["/app"]  # Runs as root!

# Good
FROM ubuntu
RUN useradd -m -u 1000 appuser
COPY app /app
RUN chown appuser:appuser /app
USER appuser
CMD ["/app"]
```

**Security Context (Kubernetes):**

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000

  # Drop all capabilities, add only what's needed
  capabilities:
    drop:
      - ALL
    add:
      - NET_BIND_SERVICE  # Only allow binding to ports <1024

  # Read-only root filesystem
  readOnlyRootFilesystem: true

  # Prevent privilege escalation
  allowPrivilegeEscalation: false

  # Use seccomp
  seccompProfile:
    type: RuntimeDefault
```

**Seccomp Profiles:**

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "syscalls": [
    {
      "names": ["read", "write", "open", "close", "stat"],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

This blocks all syscalls except the allowed ones.

#### 3. Network Security

**Network Policies:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-policy
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
    - Egress

  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080

  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

This creates a "zero trust" network—only explicitly allowed traffic flows.

### Supply Chain Security

Modern attacks target the build pipeline:

**SBOM (Software Bill of Materials):**

```bash
# Generate SBOM
syft myapp:latest -o json > sbom.json

# Attach to image
cosign attach sbom --sbom sbom.json myapp:latest

# Verify SBOM
cosign verify-attestation --type slsaprovenance myapp:latest
```

**Attestation:**

```bash
# Sign build attestations
cosign attest \
  --predicate attestation.json \
  --type slsaprovenance \
  myapp:latest
```

**Admission Control:**

```yaml
# Only allow signed images from trusted builders
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: enforce-image-policy
webhooks:
  - name: validate-image
    rules:
      - apiGroups: [""]
        resources: ["pods"]
        operations: ["CREATE", "UPDATE"]
    clientConfig:
      service:
        name: image-validator
        namespace: security
```

## Container Patterns

Containers enable new architectural patterns:

### Sidecar Pattern

**Problem:** Need to add functionality (logging, monitoring) without modifying the main application.

**Solution:** Run a helper container alongside the main container.

```yaml
spec:
  containers:
    # Main application
    - name: app
      image: myapp:latest
      ports:
        - containerPort: 8080
      volumeMounts:
        - name: logs
          mountPath: /var/log

    # Sidecar: Log shipper
    - name: log-shipper
      image: fluentd:latest
      volumeMounts:
        - name: logs
          mountPath: /var/log
      env:
        - name: FLUENTD_CONF
          value: fluentd.conf

  volumes:
    - name: logs
      emptyDir: {}
```

**Use Cases:**
- Log shipping
- Metrics collection
- Service mesh proxies (Envoy, Linkerd)
- Secret management
- Configuration hot-reloading

### Ambassador Pattern

**Problem:** Need to proxy/route traffic to external services.

**Solution:** Run a proxy container that handles the complexity.

```yaml
spec:
  containers:
    # Main application (talks to localhost:6379)
    - name: app
      image: myapp:latest
      env:
        - name: REDIS_HOST
          value: localhost
        - name: REDIS_PORT
          value: "6379"

    # Ambassador: Redis proxy
    - name: redis-proxy
      image: haproxy:latest
      ports:
        - containerPort: 6379
      volumeMounts:
        - name: config
          mountPath: /usr/local/etc/haproxy

  volumes:
    - name: config
      configMap:
        name: redis-proxy-config
```

The app thinks Redis is local, but the ambassador handles:
- Load balancing across Redis replicas
- Failover
- Retry logic
- Connection pooling

### Adapter Pattern

**Problem:** Need to present data in a different format.

**Solution:** Run an adapter container that transforms the output.

```yaml
spec:
  containers:
    # Legacy app (non-standard metrics)
    - name: app
      image: legacy-app:latest
      ports:
        - containerPort: 8080

    # Adapter: Translate to Prometheus format
    - name: prometheus-exporter
      image: custom-exporter:latest
      ports:
        - containerPort: 9090
      env:
        - name: APP_METRICS_URL
          value: http://localhost:8080/metrics
```

Prometheus scrapes port 9090, the adapter translates legacy metrics to Prometheus format.

### Init Container Pattern

**Problem:** Need to perform setup before the main container starts.

**Solution:** Use init containers that run to completion first.

```yaml
spec:
  initContainers:
    # Wait for database
    - name: wait-for-db
      image: busybox:latest
      command:
        - sh
        - -c
        - |
          until nc -z postgres 5432; do
            echo "Waiting for database..."
            sleep 2
          done

    # Run migrations
    - name: migrate
      image: myapp:latest
      command: ["./migrate.sh"]
      env:
        - name: DB_HOST
          value: postgres

  containers:
    - name: app
      image: myapp:latest
```

Init containers run **sequentially** and must succeed before the main container starts.

## Container Optimization

### Image Size Optimization

**Bad: 850MB**
```dockerfile
FROM node:14
WORKDIR /app
COPY . .
RUN npm install
CMD ["npm", "start"]
```

**Good: 95MB**
```dockerfile
FROM node:14-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:14-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
USER node
CMD ["node", "index.js"]
```

**Better: 50MB with Distroless**
```dockerfile
FROM node:14-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Distroless: No shell, no package manager, just runtime
FROM gcr.io/distroless/nodejs14
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
CMD ["index.js"]
```

**Why smaller is better:**
- Faster downloads
- Faster starts
- Less attack surface
- Lower storage costs
- Faster CI/CD

### Build Performance

**Cache Mounts (BuildKit):**

```dockerfile
# Cache pip packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Cache npm packages
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Cache Go modules
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
```

**Secrets (BuildKit):**

```dockerfile
# Don't bake secrets into layers!
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install

# Secret is mounted temporarily, not in final image
```

**Parallel Builds:**

```dockerfile
# Install packages in parallel
RUN apt-get update && \
    apt-get install -y \
      package1 \
      package2 \
      package3 \
      package4 \
      package5
```

### Runtime Performance

**JVM Optimization:**
```bash
docker run \
  -e JAVA_OPTS="-XX:MaxRAMPercentage=75.0 -XX:+UseContainerSupport" \
  myapp
```

**Node.js Optimization:**
```bash
docker run \
  -e NODE_OPTIONS="--max-old-space-size=1024 --max-semi-space-size=64" \
  myapp
```

**Python Optimization:**
```bash
docker run \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  myapp
```

## Production Considerations

### Logging

**Direct to stdout/stderr:**

```dockerfile
# Nginx example
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log
```

**Why?**
- Docker captures stdout/stderr automatically
- Works with all log collectors
- No log files to manage
- No disk space issues

### Health Checks

```dockerfile
HEALTHCHECK \
  --interval=30s \
  --timeout=3s \
  --start-period=5s \
  --retries=3 \
  CMD curl -f http://localhost/health || exit 1
```

**Or in code:**

```python
@app.route('/health')
def health():
    # Check database
    try:
        db.execute('SELECT 1')
    except:
        return 'unhealthy', 503

    # Check dependencies
    try:
        redis.ping()
    except:
        return 'unhealthy', 503

    return 'ok', 200
```

### Graceful Shutdown

```python
import signal
import sys
import time

def signal_handler(sig, frame):
    print('SIGTERM received, shutting down gracefully...')

    # Stop accepting new requests
    server.stop_accepting()

    # Wait for current requests to finish (max 30s)
    shutdown_start = time.time()
    while server.has_active_requests():
        if time.time() - shutdown_start > 30:
            print('Timeout reached, forcing shutdown')
            break
        time.sleep(0.1)

    # Close connections
    db.close()
    cache.close()

    print('Shutdown complete')
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

### Resource Limits

```yaml
resources:
  requests:
    memory: "128Mi"  # Guaranteed minimum
    cpu: "100m"      # 0.1 CPU core
  limits:
    memory: "256Mi"  # Hard limit (OOMKilled if exceeded)
    cpu: "500m"      # Throttled if exceeded
```

**Why both?**
- **Requests**: Used for scheduling (ensures resources available)
- **Limits**: Prevents resource hogging (protects other containers)

## Container Orchestration Preview

Running one container is easy. Running 1,000 containers? That's where orchestration comes in.

### Why Orchestration?

**Single Container Problems:**
- Dies = downtime
- Can't scale horizontally
- No load balancing
- Manual updates
- No service discovery

**Orchestration Solutions:**

**Kubernetes** (The winner)
- Industry standard
- Massive ecosystem
- Complex but powerful
- Runs anywhere

**Docker Swarm** (The simple one)
- Built into Docker
- Easy to learn
- Limited features
- Declining adoption

**Nomad** (The flexible one)
- Not just containers
- Simple operations
- HashiCorp ecosystem
- Good for hybrid workloads

**ECS/Fargate** (AWS)
- Tight AWS integration
- Serverless option (Fargate)
- Easy for AWS users
- Vendor lock-in

**Cloud Run** (Google)
- Fully serverless
- Auto-scaling to zero
- Simple deployment
- Limited control

## Common Pitfalls

### Running as Root

```dockerfile
# Bad
FROM ubuntu
COPY app /app
CMD ["/app"]  # root!

# Good
FROM ubuntu
RUN useradd -m appuser
COPY --chown=appuser:appuser app /app
USER appuser
CMD ["/app"]
```

**Why bad?**
- Container escape = root on host
- Increased blast radius
- Violates principle of least privilege

### Storing Secrets

```dockerfile
# Bad
ENV API_KEY=secret123
ENV DB_PASSWORD=hunter2

# Good
# Use secrets at runtime
docker run \
  --env-file secrets.env \
  myapp

# Or Kubernetes secrets
env:
  - name: API_KEY
    valueFrom:
      secretKeyRef:
        name: api-secret
        key: api-key
```

### Zombie Processes

```dockerfile
# Bad - npm/python/etc. doesn't reap zombies
CMD ["npm", "start"]

# Good - Use tini as PID 1
RUN apk add --no-cache tini
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "index.js"]
```

**Why?**
PID 1 has special responsibilities in Unix:
- Reaping zombie processes
- Forwarding signals
- Being the init system

npm/python/etc. aren't designed for this. Use a proper init system.

### Layer Bloat

```dockerfile
# Bad - Each RUN creates a layer
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y git
RUN curl -O https://example.com/file.tar.gz
RUN rm -rf /var/lib/apt/lists/*  # Doesn't reduce image size!

# Good - Single layer, cleanup in same step
RUN apt-get update && \
    apt-get install -y \
      curl \
      git && \
    curl -O https://example.com/file.tar.gz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

**Why?**
Layers are immutable. Deleting files in a later layer doesn't remove them from earlier layers.

### Ignoring .dockerignore

```
# .dockerignore
node_modules/
.git/
*.log
.env
dist/
coverage/
.DS_Store
Dockerfile*
docker-compose*
```

**Why?**
- Speeds up builds (less context to send)
- Prevents secrets from leaking
- Reduces image size
- Improves caching

## The Container Revolution Impact

### Developer Experience

**Before:**
- "Works on my machine" syndrome
- Environment setup takes days
- Inconsistent between developers
- Testing in production-like environments: impossible

**After:**
- Clone repo, run `docker-compose up`
- Onboarding takes minutes
- Everyone has identical environments
- Test exact production configuration locally

### Operations

**Before:**
- Snowflake servers
- Manual deployments
- Rollbacks are scary
- Resource waste (over-provisioning)

**After:**
- Immutable infrastructure
- Automated deployments
- Rollbacks are trivial (`docker run old-image`)
- Dense resource usage

### Business Impact

**Before:**
- Months to deploy new services
- High infrastructure costs
- Frequent outages
- Slow experimentation

**After:**
- Minutes to deploy new services
- Pay for what you use
- Blue-green deployments
- Rapid experimentation

## Summary

Containers fundamentally changed how we build, ship, and run applications. Let's recap the journey:

**The Problem:**
- "Works on my machine" was the norm
- Dependency hell was unavoidable
- Deployment was manual and error-prone
- Servers were pets, not cattle
- Infrastructure was expensive and slow

**The Solution:**
- **Isolation**: Namespaces gave each process its own view
- **Resource Control**: Cgroups prevented resource hogging
- **Efficiency**: Layer sharing made containers lightweight
- **Portability**: Standard format worked everywhere
- **Simplicity**: Dockerfile made deployment reproducible

**Key Innovations:**
1. **Process isolation without VMs** - Near-native performance
2. **Layered filesystem efficiency** - Share common layers
3. **Standard packaging format** - OCI specification
4. **Registry ecosystem** - DockerHub, Quay, ECR, etc.
5. **Developer-friendly tooling** - Simple CLI, great docs

**Lasting Impact:**
- **Microservices enablement**: Containers made microservices practical
- **DevOps acceleration**: Developers can own deployment
- **Cloud native foundation**: Containers are the primitive of cloud native
- **Kubernetes dominance**: Containers led to orchestration

**The Reality Today:**
- **Containers are the default**: New apps are containerized by default
- **Docker is a commodity**: The innovation is normalized
- **Security is paramount**: Container escapes are real threats
- **Orchestration is essential**: Running containers at scale requires Kubernetes

**The Future:**
- **WebAssembly containers**: Even smaller, faster, more portable
- **Unikernels**: Compile app + minimal OS into single binary
- **eBPF**: Kernel-level observability and security
- **Service mesh**: Network becomes intelligent

Containers aren't just a technology—they're a paradigm shift that enabled the cloud native revolution. Just as shipping containers transformed global trade by standardizing how goods move, software containers transformed software delivery by standardizing how code moves.

The question is no longer "Should we use containers?" but "How do we use them securely, efficiently, and at scale?"

That's where orchestration comes in...

---

Continue to [Orchestration →](orchestration.md)
