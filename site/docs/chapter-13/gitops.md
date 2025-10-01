# GitOps: Git as the Source of Truth for Infrastructure

## Introduction: The Audit Trail That Deploys Itself

In 2017, Weaveworks engineers faced a problem. They were deploying to Kubernetes dozens of times per day. Each deployment involved:
- Running kubectl commands
- Hoping they worked
- No audit trail of who changed what
- No easy way to rollback
- Drift between desired state (in Git) and actual state (in cluster)

Then they had an insight: **What if Git wasn't just for code? What if Git was the source of truth for infrastructure, and the infrastructure automatically synchronized itself with Git?**

This became GitOps—a paradigm where:
1. **Declarative infrastructure:** Everything defined as code in Git
2. **Git as single source of truth:** Desired state lives in version control
3. **Automated synchronization:** Agents automatically apply changes from Git
4. **Continuous reconciliation:** System continuously corrects drift

### The Mental Shift

**Traditional deployment (push-based):**
```bash
# Developer runs commands (push model)
kubectl apply -f deployment.yaml
helm upgrade myapp ./chart
terraform apply
```

**Problems:**
- Who ran this command? (audit trail gaps)
- What was changed? (no version history)
- How to rollback? (manual process)
- What if cluster differs from config? (drift undetected)

**GitOps deployment (pull-based):**
```
Developer → Git (commit) → Agent (pulls changes) → Cluster (applies)
```

**Advantages:**
- Audit trail: Every change is a Git commit
- Version history: Full history of infrastructure changes
- Rollback: `git revert` to undo changes
- Drift detection: Agent detects and corrects differences
- Disaster recovery: Recreate cluster from Git repo

### Why GitOps Emerged

The shift to cloud-native infrastructure created operational complexity:

**Pre-Kubernetes (2015):**
- Deploy application to servers via Ansible/Chef
- Infrastructure rarely changes
- Manual processes acceptable

**Post-Kubernetes (2020):**
- Deploy 100+ microservices
- Infrastructure changes daily
- Manual processes don't scale
- Need automation, audit trails, disaster recovery

GitOps answers: **How do we manage complex infrastructure at scale with reliability and auditability?**

## GitOps Principles

### Principle 1: Declarative Description

Everything is described declaratively, not imperatively.

**Imperative (bad):**
```bash
# How to achieve the state
kubectl create deployment app --image=app:v1
kubectl scale deployment app --replicas=3
kubectl expose deployment app --port=80
```

**Declarative (good):**
```yaml
# What the state should be
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
        image: app:v1
---
apiVersion: v1
kind: Service
metadata:
  name: app
spec:
  ports:
  - port: 80
```

**Why declarative?**
- Idempotent: Apply multiple times, same result
- Self-documenting: State is explicit
- Diffable: Compare desired vs actual state
- Rollback-friendly: Revert to previous declaration

### Principle 2: Versioned and Immutable

All configuration stored in version control (Git).

**Repository structure:**

```
infrastructure/
├── base/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── development/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patches/
│   └── production/
│       ├── kustomization.yaml
│       ├── replicas.yaml
│       └── resources.yaml
└── README.md
```

**Every change is a commit:**

```bash
# Developer makes change
git checkout -b increase-replicas
vim overlays/production/replicas.yaml  # Change replicas: 3 → 5
git add overlays/production/replicas.yaml
git commit -m "Scale production app to 5 replicas"
git push origin increase-replicas

# Pull request created
# Code review happens
# PR merged to main branch

# GitOps agent detects change in main
# Agent automatically applies to production cluster
```

**Audit trail:**

```bash
$ git log --oneline overlays/production/replicas.yaml

a1b2c3d Scale production app to 5 replicas (2023-10-01, Alice)
d4e5f6g Reduce replicas during low traffic (2023-09-28, Bob)
g7h8i9j Initial production configuration (2023-09-01, Alice)
```

Every change has:
- **Who:** Author and reviewer
- **What:** Exact changes (git diff)
- **When:** Timestamp
- **Why:** Commit message and PR description

### Principle 3: Pulled Automatically

Agents pull changes from Git and apply them to infrastructure.

**The reconciliation loop:**

```python
# GitOps agent (simplified)
def reconciliation_loop():
    while True:
        # 1. Fetch desired state from Git
        desired_state = git.pull('main')

        # 2. Get current state from cluster
        current_state = kubectl.get_all()

        # 3. Calculate difference
        diff = calculate_diff(desired_state, current_state)

        if diff:
            # 4. Apply changes
            for change in diff:
                kubectl.apply(change)
                log_change(change)

            # 5. Verify application
            verify_health()

        # 6. Wait and repeat
        time.sleep(sync_interval)  # e.g., 3 minutes
```

**Key insight:** The cluster pulls changes. Developers never `kubectl apply` directly.

### Principle 4: Continuously Reconciled

Agents continuously ensure actual state matches desired state (drift correction).

**Drift scenarios:**

**Scenario 1: Manual change**
```bash
# Someone manually changes replicas
$ kubectl scale deployment app --replicas=10

# GitOps agent detects drift
# Agent reverts to desired state (replicas=5)
# Manual change undone
```

**Scenario 2: Configuration drift**
```bash
# A pod crashes and doesn't restart properly
# Actual: 4 replicas running
# Desired: 5 replicas

# Agent detects missing replica
# Agent creates missing pod
# Drift corrected
```

**Scenario 3: Unauthorized deletion**
```bash
# Someone deletes a service
$ kubectl delete service app

# Agent detects missing service
# Agent recreates service
# Service restored
```

**Production benefit:** Drift correction prevents configuration decay. The cluster stays in sync with Git.

## ArgoCD: Declarative GitOps for Kubernetes

ArgoCD is the leading GitOps tool for Kubernetes.

### Architecture

```
┌──────────────────────────────────────────────────┐
│               Git Repository                      │
│  ┌─────────────────────────────────────────┐    │
│  │  infrastructure/                         │    │
│  │    ├── base/                             │    │
│  │    └── overlays/                         │    │
│  │         └── production/                  │    │
│  └─────────────────────────────────────────┘    │
└───────────────────┬──────────────────────────────┘
                    │
                    │ (poll every 3 min)
                    ▼
┌──────────────────────────────────────────────────┐
│            ArgoCD Server                          │
│  ┌────────────┐  ┌───────────┐  ┌────────────┐  │
│  │ API Server │  │Application│  │   Repo     │  │
│  │            │  │ Controller│  │   Server   │  │
│  └────────────┘  └───────────┘  └────────────┘  │
└───────────────────┬──────────────────────────────┘
                    │
                    │ (apply changes)
                    ▼
┌──────────────────────────────────────────────────┐
│          Kubernetes Cluster                       │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐ │
│  │ Pod    │  │ Pod    │  │ Pod    │  │ Pod    │ │
│  └────────┘  └────────┘  └────────┘  └────────┘ │
└──────────────────────────────────────────────────┘
```

### Installation

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

# Expose ArgoCD server
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Login to ArgoCD UI: https://localhost:8080
# Username: admin
# Password: (from above command)
```

### Creating an Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: production-app
  namespace: argocd
spec:
  # Git repository
  source:
    repoURL: https://github.com/myorg/infrastructure
    targetRevision: main
    path: overlays/production
    kustomize:
      version: v4.5.7

  # Destination cluster
  destination:
    server: https://kubernetes.default.svc
    namespace: production

  # Sync policy
  syncPolicy:
    automated:
      prune: true      # Delete resources not in Git
      selfHeal: true   # Correct drift automatically
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  # Health assessment
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/replicas  # Ignore HPA-managed replicas
```

**What this does:**
1. Monitors Git repo for changes (every 3 minutes)
2. When changes detected, syncs to cluster
3. If drift detected, automatically corrects (selfHeal)
4. Deletes resources removed from Git (prune)
5. Retries on failure with exponential backoff

### The Sync Process

**Manual sync:**
```bash
# Sync application manually
argocd app sync production-app

# Watch sync progress
argocd app wait production-app --health
```

**Automatic sync:**
```bash
# Developer commits change to Git
git commit -m "Update app image to v2"
git push

# ArgoCD detects change (within 3 minutes)
# ArgoCD applies change to cluster
# ArgoCD verifies health
# Status: Synced, Healthy
```

**Sync phases:**

```
1. PreSync (hooks run before sync)
   └─ Run database migrations
   └─ Backup current state

2. Sync (apply resources)
   └─ Apply manifests in order
   └─ Wait for readiness

3. PostSync (hooks run after sync)
   └─ Run smoke tests
   └─ Send notification

4. SyncFail (hooks run on failure)
   └─ Rollback changes
   └─ Alert on-call
```

**Sync hooks example:**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: app:v2
        command: ["python", "manage.py", "migrate"]
      restartPolicy: Never
```

### Multi-Cluster Management

ArgoCD can manage multiple clusters from one control plane.

```yaml
# Register external cluster
$ argocd cluster add prod-cluster-1 --name production-us-east
$ argocd cluster add prod-cluster-2 --name production-eu-west

# Deploy to multiple clusters
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: multi-cluster-app
  namespace: argocd
spec:
  generators:
  - list:
      elements:
      - cluster: production-us-east
        region: us-east-1
      - cluster: production-eu-west
        region: eu-west-1

  template:
    metadata:
      name: '{{cluster}}-app'
    spec:
      source:
        repoURL: https://github.com/myorg/infrastructure
        targetRevision: main
        path: overlays/{{region}}
      destination:
        name: '{{cluster}}'
        namespace: production
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

**Result:** One ApplicationSet creates two Applications, one for each cluster. Changes to Git deploy to both clusters automatically.

### Production Configuration

```yaml
# High-availability ArgoCD installation
apiVersion: argoproj.io/v1alpha1
kind: ArgoCD
metadata:
  name: argocd
  namespace: argocd
spec:
  # High availability
  ha:
    enabled: true
    redisProxyImage: haproxy:2.6.0
    redisProxyVersion: "2.6.0"

  # Controller (reconciliation engine)
  controller:
    replicas: 3
    resources:
      limits:
        cpu: "2000m"
        memory: "4Gi"
      requests:
        cpu: "500m"
        memory: "2Gi"

  # API Server
  server:
    replicas: 3
    resources:
      limits:
        cpu: "1000m"
        memory: "512Mi"
      requests:
        cpu: "250m"
        memory: "128Mi"
    ingress:
      enabled: true
      annotations:
        cert-manager.io/cluster-issuer: letsencrypt-prod
      hosts:
      - argocd.example.com
      tls:
      - secretName: argocd-tls
        hosts:
        - argocd.example.com

  # Repo Server
  repoServer:
    replicas: 3
    resources:
      limits:
        cpu: "1000m"
        memory: "512Mi"
      requests:
        cpu: "250m"
        memory: "128Mi"

  # Redis (state storage)
  redis:
    resources:
      limits:
        cpu: "500m"
        memory: "256Mi"
      requests:
        cpu: "100m"
        memory: "128Mi"

  # RBAC (role-based access control)
  rbac:
    policy: |
      g, engineering, role:admin
      g, sre, role:admin
      p, role:developer, applications, get, */*, allow
      p, role:developer, applications, sync, */*, allow
```

### Real-World ArgoCD Experience (SaaS Company)

A SaaS company with 200 microservices migrated to ArgoCD in 2021. Key learnings:

**Before ArgoCD:**
- 50+ kubectl commands per deployment
- No audit trail (who deployed what?)
- Frequent drift (manual changes not tracked)
- 30-minute deployments (manual steps)
- Rollbacks took 1 hour (manual revert)

**After ArgoCD:**
- Deployment = Git commit + merge
- Full audit trail (every change tracked)
- Zero drift (automatic correction)
- 5-minute deployments (automated)
- Rollbacks take 2 minutes (git revert)

**Metrics:**
- Deployment frequency: 5× increase (20/day → 100/day)
- Deployment failures: 60% reduction (drift eliminated)
- Mean time to recovery: 10× improvement (60 min → 6 min)
- Engineering time saved: 2 hours/day (no manual deploys)

**Cost:** 2 hours/day × 20 engineers × $200/hour = $8,000/day saved = $2M/year

## Flux: The CNCF GitOps Solution

Flux is another popular GitOps tool, now a CNCF graduated project.

### Architecture

```
┌──────────────────────────────────────────────────┐
│               Git Repository                      │
└────────────────────┬─────────────────────────────┘
                     │
                     │ (watch for changes)
                     ▼
┌──────────────────────────────────────────────────┐
│              Flux Components                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │   Source   │  │ Kustomize  │  │    Helm    │ │
│  │ Controller │→ │ Controller │  │ Controller │ │
│  └────────────┘  └────────────┘  └────────────┘ │
│  ┌────────────┐  ┌────────────┐                 │
│  │Notification│  │   Image    │                 │
│  │ Controller │  │Automation  │                 │
│  └────────────┘  └────────────┘                 │
└────────────────────┬─────────────────────────────┘
                     │
                     │ (apply manifests)
                     ▼
┌──────────────────────────────────────────────────┐
│          Kubernetes Cluster                       │
└──────────────────────────────────────────────────┘
```

### Installation

```bash
# Install Flux CLI
curl -s https://fluxcd.io/install.sh | sudo bash

# Bootstrap Flux on cluster
flux bootstrap github \
  --owner=myorg \
  --repository=infrastructure \
  --branch=main \
  --path=clusters/production \
  --personal

# This:
# 1. Installs Flux components in cluster
# 2. Creates Git repo (if doesn't exist)
# 3. Commits Flux manifests to repo
# 4. Configures Flux to watch repo
```

### GitRepository Source

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: infrastructure
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/myorg/infrastructure
  ref:
    branch: main
  secretRef:
    name: git-credentials
```

### Kustomization

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: production-apps
  namespace: flux-system
spec:
  interval: 5m
  path: ./overlays/production
  prune: true
  sourceRef:
    kind: GitRepository
    name: infrastructure
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: app
    namespace: production
  timeout: 5m
```

### Image Automation

Flux can automatically update container images when new versions are pushed to registry.

```yaml
# Image repository (watch for new tags)
apiVersion: image.toolkit.fluxcd.io/v1beta1
kind: ImageRepository
metadata:
  name: app-image
  namespace: flux-system
spec:
  image: docker.io/myorg/app
  interval: 1m

---
# Image policy (which tags to use)
apiVersion: image.toolkit.fluxcd.io/v1beta1
kind: ImagePolicy
metadata:
  name: app-policy
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: app-image
  policy:
    semver:
      range: '^1.0.0'  # Only 1.x.x versions

---
# Image update automation (update Git)
apiVersion: image.toolkit.fluxcd.io/v1beta1
kind: ImageUpdateAutomation
metadata:
  name: app-update
  namespace: flux-system
spec:
  interval: 1m
  sourceRef:
    kind: GitRepository
    name: infrastructure
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: fluxcdbot@users.noreply.github.com
        name: fluxcdbot
      messageTemplate: |
        Automated image update

        Automation name: {{ .AutomationObject }}

        Files:
        {{ range $filename, $_ := .Updated.Files -}}
        - {{ $filename }}
        {{ end -}}
  update:
    path: ./overlays/production
    strategy: Setters
```

**How it works:**
1. New image pushed to registry: `myorg/app:1.2.3`
2. Flux detects new tag (matches semver policy)
3. Flux updates manifest in Git (commits change)
4. Flux detects Git change
5. Flux applies to cluster

**Result:** Fully automated CI/CD pipeline. Push image → deployed to production automatically.

### Flux vs ArgoCD

| Feature | ArgoCD | Flux |
|---------|--------|------|
| **UI** | Rich web UI | No native UI (K9s, Weave GitOps) |
| **Multi-tenancy** | Built-in RBAC | Requires manual setup |
| **Helm support** | Native | Native |
| **Image automation** | Limited | First-class |
| **Complexity** | More complex | Simpler (fewer components) |
| **Community** | Large | Growing |
| **CNCF status** | Incubating | Graduated |

**When to use ArgoCD:** Need web UI, multi-tenancy, centralized management

**When to use Flux:** Prefer simplicity, native Kubernetes CRDs, image automation

## Terraform: Infrastructure as Code for Cloud Resources

Terraform manages infrastructure outside Kubernetes (VMs, databases, networking).

### Terraform Basics

**Configuration (HCL):**

```hcl
# provider.tf
terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state backend
  backend "s3" {
    bucket         = "myorg-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = "us-east-1"
}
```

**Resources:**

```hcl
# main.tf
# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "production-vpc"
    Environment = "production"
  }
}

# Subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "production-public-subnet"
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "production-cluster"
  cluster_version = "1.28"

  vpc_id     = aws_vpc.main.id
  subnet_ids = [aws_subnet.public.id]

  eks_managed_node_groups = {
    general = {
      min_size     = 3
      max_size     = 10
      desired_size = 5

      instance_types = ["m5.xlarge"]
      capacity_type  = "SPOT"

      labels = {
        Environment = "production"
        NodeGroup   = "general"
      }

      tags = {
        Environment = "production"
      }
    }
  }

  tags = {
    Environment = "production"
  }
}

# RDS Database
resource "aws_db_instance" "postgres" {
  identifier        = "production-db"
  engine            = "postgres"
  engine_version    = "15.3"
  instance_class    = "db.r5.large"
  allocated_storage = 100
  storage_encrypted = true

  db_name  = "appdb"
  username = "dbadmin"
  password = var.db_password  # Never hardcode!

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  skip_final_snapshot = false
  final_snapshot_identifier = "production-db-final-snapshot"

  tags = {
    Environment = "production"
  }
}
```

### Terraform Workflow

```bash
# 1. Initialize (download providers)
terraform init

# 2. Plan (preview changes)
terraform plan -out=tfplan

# Output:
# Terraform will perform the following actions:
#   # aws_eks_cluster.main will be created
#   + resource "aws_eks_cluster" "main" {
#       + arn                   = (known after apply)
#       + name                  = "production-cluster"
#       ...
#     }
# Plan: 45 to add, 0 to change, 0 to destroy

# 3. Apply (create resources)
terraform apply tfplan

# 4. Show current state
terraform show

# 5. Destroy (clean up)
terraform destroy
```

### Terraform State Management

**State file contains:**
- Current infrastructure state
- Resource metadata
- Dependency graph

**Never commit state to Git!** Use remote backend.

**S3 backend with locking:**

```hcl
terraform {
  backend "s3" {
    bucket         = "myorg-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"  # Prevents concurrent applies
  }
}
```

**DynamoDB table for locks:**

```hcl
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "Terraform Lock Table"
  }
}
```

**Why locking matters:**

```
Engineer A: terraform apply (in progress)
Engineer B: terraform apply (at same time)

Without locking:
  - Both read same state
  - Both make changes
  - Concurrent writes corrupt state
  - Infrastructure inconsistent

With locking:
  - Engineer A acquires lock
  - Engineer B waits (lock held)
  - Engineer A finishes
  - Lock released
  - Engineer B proceeds
```

### Terraform Modules

Reusable infrastructure components.

**Module structure:**

```
modules/
└── eks-cluster/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── README.md
```

**Using a module:**

```hcl
module "production_eks" {
  source = "./modules/eks-cluster"

  cluster_name = "production-cluster"
  vpc_id       = aws_vpc.main.id
  subnet_ids   = aws_subnet.public[*].id

  node_groups = {
    general = {
      instance_types = ["m5.xlarge"]
      min_size       = 3
      max_size       = 10
      desired_size   = 5
    }
    cpu_optimized = {
      instance_types = ["c5.2xlarge"]
      min_size       = 2
      max_size       = 20
      desired_size   = 5
    }
  }
}
```

**Module outputs:**

```hcl
# outputs.tf in module
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_ca_certificate" {
  description = "EKS cluster CA certificate"
  value       = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
  sensitive   = true
}

# Using module outputs
output "kubeconfig" {
  value = module.production_eks.cluster_endpoint
}
```

### Terraform in GitOps

**Repository structure:**

```
infrastructure/
├── terraform/
│   ├── environments/
│   │   ├── production/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── terraform.tfvars
│   │   └── staging/
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       └── terraform.tfvars
│   └── modules/
│       ├── eks-cluster/
│       ├── rds-database/
│       └── vpc/
└── kubernetes/
    ├── base/
    └── overlays/
```

**GitOps workflow:**

```
1. Developer commits Terraform change to Git
2. Pull request created
3. CI runs `terraform plan` (preview changes)
4. Team reviews plan
5. PR approved and merged
6. CD runs `terraform apply` (applies changes)
7. Infrastructure updated
```

**CI/CD pipeline (GitHub Actions):**

```yaml
name: Terraform

on:
  pull_request:
    paths:
    - 'terraform/**'
  push:
    branches:
    - main
    paths:
    - 'terraform/**'

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v2
      with:
        terraform_version: 1.5.0

    - name: Terraform Init
      run: terraform init
      working-directory: terraform/environments/production

    - name: Terraform Plan
      run: terraform plan -out=tfplan
      working-directory: terraform/environments/production

    - name: Terraform Apply
      if: github.ref == 'refs/heads/main'
      run: terraform apply -auto-approve tfplan
      working-directory: terraform/environments/production
```

## Pulumi: Infrastructure as Code in Real Programming Languages

Pulumi is like Terraform, but uses real programming languages (Python, TypeScript, Go, C#) instead of HCL.

### Why Pulumi?

**Terraform (HCL):**
```hcl
# Limited expressiveness
locals {
  subnet_count = 3
}

resource "aws_subnet" "public" {
  count             = local.subnet_count
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
}
```

**Pulumi (Python):**
```python
import pulumi
import pulumi_aws as aws

# Full power of Python
availability_zones = aws.get_availability_zones(state="available")

subnets = []
for i, az in enumerate(availability_zones.names[:3]):
    subnet = aws.ec2.Subnet(
        f"public-{i}",
        vpc_id=vpc.id,
        cidr_block=f"10.0.{i}.0/24",
        availability_zone=az,
        map_public_ip_on_launch=True,
        tags={"Name": f"public-subnet-{az}"}
    )
    subnets.append(subnet)

# Export subnet IDs
pulumi.export("subnet_ids", [s.id for s in subnets])
```

**Benefits:**
- Use familiar languages
- IDE autocompletion
- Type safety
- Loops, conditionals, functions
- Test with standard testing frameworks

### Pulumi Example (TypeScript)

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as eks from "@pulumi/eks";

// Configuration
const config = new pulumi.Config();
const clusterName = config.require("clusterName");
const desiredCapacity = config.requireNumber("desiredCapacity");

// VPC
const vpc = new aws.ec2.Vpc("main", {
    cidrBlock: "10.0.0.0/16",
    enableDnsHostnames: true,
    enableDnsSupport: true,
    tags: {
        Name: `${clusterName}-vpc`,
    },
});

// Subnets (using loop)
const subnets = [];
const azs = aws.getAvailabilityZones({ state: "available" });

for (let i = 0; i < 3; i++) {
    const subnet = new aws.ec2.Subnet(`public-${i}`, {
        vpcId: vpc.id,
        cidrBlock: `10.0.${i}.0/24`,
        availabilityZone: azs.then(azs => azs.names[i]),
        mapPublicIpOnLaunch: true,
        tags: {
            Name: `${clusterName}-public-${i}`,
        },
    });
    subnets.push(subnet);
}

// EKS Cluster
const cluster = new eks.Cluster("cluster", {
    name: clusterName,
    vpcId: vpc.id,
    subnetIds: subnets.map(s => s.id),
    instanceType: "m5.xlarge",
    desiredCapacity: desiredCapacity,
    minSize: 3,
    maxSize: 10,
    nodeAssociatePublicIpAddress: true,
});

// Export kubeconfig
export const kubeconfig = cluster.kubeconfig;
export const clusterEndpoint = cluster.eksCluster.endpoint;
```

### Pulumi State and Backends

Like Terraform, Pulumi needs state storage.

**Pulumi backends:**
- **Pulumi Cloud:** Managed SaaS (free for individuals)
- **Self-hosted:** S3, Azure Blob, GCS, local filesystem

```bash
# Use S3 backend
pulumi login s3://my-pulumi-state-bucket

# Deploy stack
pulumi up

# Preview changes
pulumi preview

# Destroy resources
pulumi destroy
```

### Testing Infrastructure Code

Pulumi supports unit tests (advantage over Terraform):

```typescript
// test.ts
import * as pulumi from "@pulumi/pulumi";
import { describe, it } from "mocha";
import { expect } from "chai";
import * as vpc from "./vpc";

pulumi.runtime.setMocks({
    newResource: function(args: pulumi.runtime.MockResourceArgs): {id: string, state: any} {
        return {
            id: args.inputs.name + "_id",
            state: args.inputs,
        };
    },
    call: function(args: pulumi.runtime.MockCallArgs) {
        return args.inputs;
    },
});

describe("VPC Infrastructure", function() {
    it("creates VPC with correct CIDR", function(done) {
        const infra = new vpc.VpcInfrastructure("test");

        pulumi.all([infra.vpc.cidrBlock]).apply(([cidr]) => {
            expect(cidr).to.equal("10.0.0.0/16");
            done();
        });
    });

    it("creates 3 subnets", function(done) {
        const infra = new vpc.VpcInfrastructure("test");

        expect(infra.subnets).to.have.lengthOf(3);
        done();
    });
});
```

## Disaster Recovery and Multi-Cluster Management

### Disaster Recovery Strategy

**Scenario:** Production cluster is destroyed (region outage, accidental deletion, data center fire).

**Recovery with GitOps:**

```bash
# 1. Provision new cluster (Terraform/Pulumi)
cd terraform/environments/production
terraform apply

# 2. Install ArgoCD/Flux
kubectl apply -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. Point ArgoCD to Git repo
argocd app create production-apps \
  --repo https://github.com/myorg/infrastructure \
  --path overlays/production \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace production \
  --sync-policy automated

# 4. Wait for sync
argocd app wait production-apps

# 5. Restore data from backups
kubectl exec -it backup-restore-pod -- restore-from-s3

# 6. Verify health
kubectl get pods -n production
kubectl get services -n production

# Total time: 20 minutes
```

**Without GitOps:**
- Find documentation (if it exists)
- Run kubectl commands manually (100+ commands)
- Hope you remember all the configurations
- Debug differences from production
- Total time: 4-8 hours (or days)

### Multi-Cluster Patterns

**Pattern 1: Hub and Spoke**

```
┌──────────────┐
│   Hub        │
│  (ArgoCD)    │
└──────┬───────┘
       │
       ├──────────┐
       │          │
   ┌───▼───┐  ┌──▼────┐
   │Spoke 1│  │Spoke 2│
   │(US)   │  │(EU)   │
   └───────┘  └───────┘
```

One ArgoCD instance manages multiple clusters.

**Pattern 2: Regional Independence**

```
┌──────────────┐      ┌──────────────┐
│   US Region  │      │   EU Region  │
│  ┌────────┐  │      │  ┌────────┐  │
│  │ArgoCD  │  │      │  │ArgoCD  │  │
│  └────────┘  │      │  └────────┘  │
│     ↓        │      │     ↓        │
│  Clusters    │      │  Clusters    │
└──────────────┘      └──────────────┘
```

Each region has its own GitOps control plane.

**Pattern 3: Hierarchical**

```
┌───────────────────────────┐
│     Global ArgoCD         │
│  (manages regional ones)  │
└─────────┬─────────────────┘
          │
     ┌────┴────┐
     │         │
┌────▼───┐ ┌──▼────┐
│US ArgoCD│ │EU ArgoCD│
└────┬────┘ └───┬────┘
     │          │
  Clusters   Clusters
```

Global ArgoCD deploys regional ArgoCDs, which manage local clusters.

## Mental Model Summary

### GitOps Core Principles

1. **Git as Single Source of Truth**
   - All configuration in version control
   - Git history = audit trail
   - Git commits = deployments

2. **Declarative Everything**
   - Describe what you want, not how to get there
   - Infrastructure as code
   - Idempotent operations

3. **Automated Synchronization**
   - Agents pull changes from Git
   - No manual kubectl/terraform commands
   - Continuous reconciliation

4. **Drift Correction**
   - Actual state continuously compared to desired state
   - Differences automatically corrected
   - Manual changes reverted

5. **Auditability**
   - Every change tracked (who, what, when, why)
   - Compliance built-in
   - Rollback is just `git revert`

### Tool Selection Guide

**ArgoCD:**
- Need web UI for developers
- Multi-tenancy requirements
- Large teams (50+ developers)
- Complex RBAC

**Flux:**
- Prefer Kubernetes-native (CRDs)
- Image automation critical
- Simpler architecture preferred
- Smaller teams

**Terraform:**
- Cloud infrastructure (VMs, networking, databases)
- Multi-cloud deployments
- Infrastructure outside Kubernetes
- Large ecosystem of providers

**Pulumi:**
- Prefer real programming languages
- Complex infrastructure logic
- Need unit testing
- TypeScript/Python expertise on team

### Production Best Practices

1. **Repository structure:** Separate infrastructure (Terraform) from applications (Kubernetes manifests)
2. **State management:** Always use remote backends with locking
3. **Testing:** Plan changes in CI before applying
4. **Secrets:** Never commit secrets; use external secret managers (Vault, Sealed Secrets)
5. **Monitoring:** Alert on sync failures, drift detection
6. **Disaster recovery:** Test cluster recreation regularly
7. **Multi-environment:** Use overlays/branches for dev/staging/production

**Next:** [When Orchestration Fails - Cascading Failures and Recovery](./orchestration-failures.md)
