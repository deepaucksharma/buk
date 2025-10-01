# Security Context Capsules: Evidence-Based Trust
## Chapter 12 Framework Transformation

*Through the lens of the Unified Mental Model Authoring Framework 3.0*

---

## Introduction: Security as Evidence Collection

Traditional security operates on binary trust: you're either authenticated or not, authorized or not, inside the perimeter or not. But distributed systems require continuous verification across trust boundaries. Every service call crosses a potential security boundary. Every boundary crossing requires evidence of trustworthiness.

**Security Context Capsules** carry trust evidence across boundaries, enabling zero-trust architectures where every request must prove its legitimacy through cryptographic evidence, not network position.

---

## Part I: Security Guarantee Vectors

### Core Security Vector

```
G_security = ⟨Authenticity, Authorization, Integrity,
              Confidentiality, Non-repudiation, Availability⟩
```

Each dimension represents a security guarantee that must be evidenced:

| Dimension | Values | Evidence Required |
|-----------|---------|-------------------|
| **Authenticity** | None → Verified → Cryptographic | Identity tokens, certificates, signatures |
| **Authorization** | Open → Role-based → Attribute-based → Zero-trust | Permissions, policies, claims |
| **Integrity** | None → Checksum → HMAC → Digital signature | Hashes, MACs, signatures |
| **Confidentiality** | Plain → Transport → End-to-end → Perfect forward secrecy | Encryption keys, protocols |
| **Non-repudiation** | None → Logged → Signed → Notarized | Audit logs, signatures, timestamps |
| **Availability** | Best-effort → Protected → Guaranteed | Rate limits, quotas, SLAs |

### Authentication Vector Transformations

Different authentication mechanisms provide different guarantee vectors:

#### Password Authentication
```
G_password = ⟨Verified, Role-based, None,
               Transport, Logged, Best-effort⟩
```
- **Evidence**: Username + hashed password
- **Lifetime**: Session duration
- **Revocation**: Session invalidation
- **Weakness**: Replay attacks, credential stuffing

#### Multi-Factor Authentication (MFA)
```
G_mfa = ⟨Cryptographic, Role-based, None,
          Transport, Logged, Best-effort⟩
```
- **Evidence**: Password + TOTP/hardware token
- **Lifetime**: Shorter sessions
- **Revocation**: Token rotation
- **Strength**: Phishing resistant

#### Certificate-Based mTLS
```
G_mtls = ⟨Cryptographic, Attribute-based, Digital signature,
           End-to-end, Signed, Protected⟩
```
- **Evidence**: X.509 certificates
- **Lifetime**: Certificate validity
- **Revocation**: CRL/OCSP
- **Strength**: Machine-to-machine trust

#### Zero-Knowledge Proofs
```
G_zkp = ⟨Cryptographic, Attribute-based, Digital signature,
          Perfect forward secrecy, Notarized, Protected⟩
```
- **Evidence**: ZK proof of knowledge
- **Lifetime**: Proof validity
- **Revocation**: Proof expiration
- **Strength**: Privacy preserving

### Authorization Vector Composition

Authorization systems compose multiple evidence types:

```
G_authz = G_identity ∧ G_context ∧ G_resource
```

Where:
- **G_identity**: Who is making the request
- **G_context**: Under what conditions (time, location, device)
- **G_resource**: What they're accessing

Example: AWS IAM Policy Evaluation
```
G_aws = ⟨SigV4_signature, Policy-based, HMAC,
          Transport, CloudTrail, Rate-limited⟩

Evidence required:
- Identity: AWS credentials (access key, secret key)
- Context: Request signature with timestamp
- Resource: ARN + action
- Result: Allow/Deny with audit trail
```

---

## Part II: Security Context Capsules

### Capsule Structure

Security Context Capsules carry trust evidence across service boundaries:

```json
{
  "version": "1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "principal": {
    "identity": "user:alice@company.com",
    "authentication": {
      "method": "oauth2+mfa",
      "timestamp": "2024-01-15T10:00:00Z",
      "strength": "high",
      "evidence": {
        "idp": "auth.company.com",
        "mfa_type": "hardware_token",
        "session_id": "sess_abc123"
      }
    }
  },
  "authorization": {
    "permissions": ["read:documents", "write:drafts"],
    "constraints": {
      "ip_range": "10.0.0.0/8",
      "time_window": "business_hours",
      "data_classification": "internal"
    },
    "policy_version": "v2.3",
    "evaluation_context": {
      "resource": "doc:12345",
      "action": "read",
      "environment": "production"
    }
  },
  "device": {
    "id": "device_xyz789",
    "compliance": {
      "os_version": "14.2",
      "patch_level": "current",
      "antivirus": "active",
      "disk_encryption": "enabled",
      "last_scan": "2024-01-15T09:00:00Z"
    },
    "attestation": {
      "type": "tpm",
      "signature": "base64_signature",
      "certificate_chain": ["cert1", "cert2"]
    }
  },
  "cryptographic": {
    "signature_algorithm": "ES256",
    "signature": "base64_jwt_signature",
    "certificate_thumbprint": "sha256:abcd1234",
    "key_rotation_date": "2024-02-01"
  },
  "audit": {
    "correlation_id": "corr_123456",
    "originating_service": "frontend",
    "call_chain": ["frontend", "api-gateway", "auth-service"],
    "risk_score": 15,
    "anomaly_flags": []
  },
  "boundary": {
    "from": "dmz",
    "to": "internal",
    "classification_change": "public→internal",
    "encryption_required": true
  },
  "ttl": 300,
  "refresh_endpoint": "https://auth.company.com/refresh",
  "fallback": {
    "mode": "readonly",
    "permissions": ["read:public"],
    "reason": "degraded_verification"
  }
}
```

### Capsule Lifecycle

#### 1. Generation Phase
```
Principal → Authentication → Claims Generation → Signing
```
- User authenticates with IdP
- IdP generates claims based on attributes
- Claims signed into JWT/SAML token
- Token becomes initial capsule

#### 2. Enhancement Phase
```
Initial Capsule → Policy Evaluation → Context Addition → Re-signing
```
- Gateway evaluates policies
- Adds device compliance status
- Adds network context
- Signs enhanced capsule

#### 3. Propagation Phase
```
Service A → Capsule Validation → Forward to Service B
```
- Each service validates capsule signature
- Checks capsule TTL
- May add service-specific claims
- Forwards to downstream services

#### 4. Verification Phase
```
Capsule → Signature Check → Claims Validation → Authorization Decision
```
- Verify cryptographic signatures
- Validate claim constraints
- Check against local policies
- Make allow/deny decision

#### 5. Expiration Phase
```
TTL Expired → Refresh Attempt → New Capsule or Deny
```
- Capsule TTL expires
- Attempt refresh with refresh token
- Generate new capsule or deny access

---

## Part III: Security Mode Matrix

Security systems operate in different modes based on threat level and verification capability:

### Mode Definitions

| Mode | Authenticity | Authorization | Integrity | Availability | Use Case |
|------|-------------|---------------|-----------|--------------|----------|
| **Paranoid** | Cryptographic + biometric | Zero-trust with continuous verification | Digital signatures on every message | Rate limited to 10% capacity | Under active attack |
| **Strict** | Cryptographic MFA | Policy-based with audit | HMAC on sensitive data | Rate limited to 50% capacity | Normal production |
| **Standard** | Password + MFA | Role-based | Checksums | Full capacity | Internal services |
| **Relaxed** | Password only | Basic ACL | None | Burst capacity allowed | Development |
| **Emergency** | Break-glass token | Admin override | Logged only | No limits | Incident response |

### Mode Transition Evidence

Transitions between modes require evidence:

#### Standard → Strict (Threat Detection)
```json
{
  "trigger": "anomaly_detected",
  "evidence": {
    "type": "unusual_access_pattern",
    "confidence": 0.85,
    "details": {
      "user": "alice",
      "accessed_resources": 150,
      "normal_baseline": 10,
      "time_window": "5_minutes"
    }
  },
  "action": "elevate_to_strict",
  "additional_requirements": [
    "require_mfa_on_all_requests",
    "enable_detailed_audit_logging",
    "reduce_session_timeout_to_5min"
  ]
}
```

#### Strict → Paranoid (Active Attack)
```json
{
  "trigger": "attack_confirmed",
  "evidence": {
    "type": "credential_compromise",
    "indicators": [
      "multiple_failed_mfa_attempts",
      "requests_from_tor_exit_nodes",
      "privilege_escalation_attempts"
    ],
    "severity": "critical"
  },
  "action": "lockdown_mode",
  "measures": [
    "revoke_all_sessions",
    "require_biometric_verification",
    "enable_continuous_verification",
    "limit_to_essential_operations"
  ]
}
```

#### Paranoid → Emergency (System Failure)
```json
{
  "trigger": "authentication_system_failure",
  "evidence": {
    "type": "infrastructure_failure",
    "affected_systems": ["idp", "mfa_service"],
    "duration": "15_minutes",
    "impact": "cannot_authenticate_users"
  },
  "action": "break_glass_protocol",
  "controls": [
    "issue_time_limited_emergency_tokens",
    "log_all_actions_for_later_audit",
    "require_two_person_authorization",
    "automatic_revocation_after_1_hour"
  ]
}
```

### Mode-Specific Evidence Requirements

#### Paranoid Mode Evidence Chain
```
Request → Device Attestation → Biometric → MFA →
Continuous Behavioral Analysis → Authorization →
Crypto Signature → Audit Log → Response
```

Every link requires cryptographic evidence:
- Device: TPM attestation
- Biometric: Secure enclave verification
- MFA: Hardware token signature
- Behavior: ML anomaly score < threshold
- Authorization: Policy evaluation proof
- Signature: Request signing
- Audit: Immutable log entry

#### Emergency Mode Evidence Preservation
```
Break-glass Token → All Actions Logged →
Post-Incident Audit → Compliance Report
```

Evidence collected for later verification:
- Who activated emergency mode
- What actions were taken
- When normal mode restored
- Why emergency was necessary

---

## Part IV: Evidence Types for Security

### 1. Cryptographic Evidence

#### Digital Signatures
```
Evidence: Message + Signature + Public Key Certificate
Properties:
- Scope: Single message
- Lifetime: Perpetual (signature remains valid)
- Binding: Cryptographically bound to message
- Transitivity: Non-transitive (signature doesn't transfer)
- Revocation: Certificate revocation
- Cost: ~1ms per signature verification
```

#### Zero-Knowledge Proofs
```
Evidence: Proof + Verification Key
Properties:
- Scope: Specific claim
- Lifetime: Proof expiration
- Binding: Bound to prover's secret
- Transitivity: Non-transitive
- Revocation: Proof expiration
- Cost: ~10-100ms per proof
```

### 2. Behavioral Evidence

#### Anomaly Scores
```
Evidence: User actions + Baseline + Deviation score
Properties:
- Scope: User session
- Lifetime: Continuous evaluation
- Binding: Probabilistic
- Transitivity: Non-transitive
- Revocation: Score threshold adjustment
- Cost: ~10ms per evaluation
```

#### Reputation Scores
```
Evidence: Historical behavior + Peer attestations
Properties:
- Scope: Entity (user/service/device)
- Lifetime: Rolling window (e.g., 30 days)
- Binding: Statistically bound
- Transitivity: Partially transitive
- Revocation: Score degradation
- Cost: ~100ms per calculation
```

### 3. Environmental Evidence

#### Network Context
```
Evidence: Source IP + Geolocation + ASN + Reputation
Properties:
- Scope: Network connection
- Lifetime: Connection duration
- Binding: Weak (IPs can be spoofed)
- Transitivity: Non-transitive
- Revocation: Blocklist updates
- Cost: ~5ms per lookup
```

#### Device Compliance
```
Evidence: OS version + Patch level + Security tools status
Properties:
- Scope: Device
- Lifetime: Until next compliance check
- Binding: Device attestation
- Transitivity: Non-transitive
- Revocation: Compliance policy update
- Cost: ~1s per full check
```

---

## Part V: Cross-System Security Composition

### Federation Patterns

#### SAML Federation Capsule
```
Source IdP → SAML Assertion → SP Validation → Local Capsule
```

```xml
<saml:Assertion>
  <saml:Subject>
    <saml:NameID>alice@idp.com</saml:NameID>
  </saml:Subject>
  <saml:AuthnStatement>
    <saml:AuthnContext>
      <saml:AuthnContextClassRef>
        urn:oasis:names:tc:SAML:2.0:ac:classes:MultiFactor
      </saml:AuthnContextClassRef>
    </saml:AuthnContext>
  </saml:AuthnStatement>
  <saml:AttributeStatement>
    <saml:Attribute Name="role">
      <saml:AttributeValue>admin</saml:AttributeValue>
    </saml:Attribute>
  </saml:AttributeStatement>
  <ds:Signature>...</ds:Signature>
</saml:Assertion>
```

Converted to local capsule:
```json
{
  "principal": "alice@idp.com",
  "authentication_strength": "multifactor",
  "roles": ["admin"],
  "federation": {
    "protocol": "saml",
    "idp": "idp.com",
    "assertion_id": "assert_123"
  }
}
```

#### OAuth2/OIDC Flow Capsule
```
User → Authorization Server → Access Token → Resource Server
```

JWT access token as capsule:
```json
{
  "iss": "https://auth.company.com",
  "sub": "user:alice",
  "aud": "https://api.company.com",
  "exp": 1642360800,
  "iat": 1642357200,
  "scope": "read:data write:data",
  "amr": ["pwd", "mfa"],
  "acr": "urn:mace:incommon:iap:silver"
}
```

### Service Mesh Security

#### Istio Security Capsule (SPIFFE)
```
Service A → mTLS with SPIFFE ID → Envoy → Service B
```

SPIFFE Security capsule:
```json
{
  "spiffe_id": "spiffe://cluster.local/ns/default/sa/frontend",
  "certificate": {
    "subject": "spiffe://cluster.local/ns/default/sa/frontend",
    "issuer": "cluster.local",
    "not_before": "2024-01-15T10:00:00Z",
    "not_after": "2024-01-15T11:00:00Z",
    "san": ["frontend.default.svc.cluster.local"]
  },
  "workload": {
    "namespace": "default",
    "service_account": "frontend",
    "pod": "frontend-7d4b7c6-x2j4k",
    "node": "node-1"
  },
  "policies": [
    "allow:backend.default:read",
    "deny:database.prod:*"
  ]
}
```

---

## Part VI: Byzantine Fault Tolerance in Security

### Byzantine Security Model

In Byzantine environments, some actors are malicious:

```
G_byzantine = ⟨Cryptographic, Threshold-based,
                Byzantine-signatures, Encrypted,
                Multi-signed, Consensus-verified⟩
```

Requirements:
- N ≥ 3f + 1 nodes to tolerate f Byzantine nodes
- Threshold signatures (t-of-n)
- Multi-party computation
- Consensus on security decisions

### Threshold Signature Capsule

```json
{
  "request": "authorize_transaction",
  "threshold": "3-of-5",
  "signatures": [
    {
      "signer": "node1",
      "signature": "sig1",
      "share": "share1"
    },
    {
      "signer": "node2",
      "signature": "sig2",
      "share": "share2"
    },
    {
      "signer": "node3",
      "signature": "sig3",
      "share": "share3"
    }
  ],
  "combined_signature": "threshold_sig",
  "verification_key": "group_public_key",
  "policy": "require_3_of_5_for_transactions_over_10k"
}
```

### Consensus-Based Authorization

```
Request → Multiple Validators → Byzantine Consensus → Decision
```

Evidence of consensus:
```json
{
  "decision": "authorize",
  "validators": [
    {"id": "val1", "vote": "approve", "signature": "sig1"},
    {"id": "val2", "vote": "approve", "signature": "sig2"},
    {"id": "val3", "vote": "approve", "signature": "sig3"},
    {"id": "val4", "vote": "deny", "signature": "sig4"},
    {"id": "val5", "vote": "approve", "signature": "sig5"}
  ],
  "consensus": {
    "algorithm": "pbft",
    "round": 2,
    "threshold": "2f+1 where f=1",
    "result": "approved by 4 of 5"
  }
}
```

---

## Part VII: Security Sacred Diagrams

### 1. The Trust Boundary Guardian

```
        External World (Untrusted)
                |
                ↓
    ┌──────────────────────────────┐
    │   Perimeter (First Check)     │
    │  ┌────────────────────────┐  │
    │  │ • Rate Limiting         │  │
    │  │ • DDoS Protection       │  │
    │  │ • Geo-blocking          │  │
    │  └────────────────────────┘  │
    └──────────────────────────────┘
                |
                ↓ (Filtered Traffic)
    ┌──────────────────────────────┐
    │   Identity Verification       │
    │  ┌────────────────────────┐  │
    │  │ • Authentication        │  │
    │  │ • MFA Challenge         │  │
    │  │ • Device Attestation    │  │
    │  └────────────────────────┘  │
    └──────────────────────────────┘
                |
                ↓ (Authenticated)
    ┌──────────────────────────────┐
    │   Authorization Gateway       │
    │  ┌────────────────────────┐  │
    │  │ • Policy Evaluation     │  │
    │  │ • RBAC/ABAC            │  │
    │  │ • Context Checking      │  │
    │  └────────────────────────┘  │
    └──────────────────────────────┘
                |
                ↓ (Authorized + Capsule)
    ┌──────────────────────────────┐
    │   Service Mesh (Zero Trust)   │
    │  ┌────────────────────────┐  │
    │  │ • mTLS Between Services │  │
    │  │ • Service Identity       │  │
    │  │ • Continuous Validation  │  │
    │  └────────────────────────┘  │
    └──────────────────────────────┘
                |
                ↓ (Encrypted + Verified)
    ┌──────────────────────────────┐
    │   Data Layer (Protected)      │
    │  ┌────────────────────────┐  │
    │  │ • Encryption at Rest     │  │
    │  │ • Field-level Encryption │  │
    │  │ • Audit Logging          │  │
    │  └────────────────────────┘  │
    └──────────────────────────────┘
```

### 2. Evidence Flow Through Security Layers

```
User Request
    ↓
[Generate: Authentication Evidence]
    ├── Password Hash
    ├── MFA Token
    └── Biometric Data
         ↓
[Validate: Identity Provider]
    ├── Verify Credentials
    ├── Check MFA
    └── Issue Token → [ID Token]
                           ↓
[Enhance: API Gateway]
    ├── Add Device Context
    ├── Add Network Context
    └── Sign Capsule → [Security Capsule]
                             ↓
[Propagate: Service Mesh]
    ├── mTLS Handshake
    ├── SPIFFE Validation
    └── Forward Capsule → [Service A]
                                ↓
[Verify: Service A]
    ├── Validate Capsule Signature
    ├── Check Permissions
    ├── Evaluate Policies
    └── Make Decision → [Allow/Deny]
                             ↓
[Audit: Security Platform]
    ├── Log Decision
    ├── Update Analytics
    └── Detect Anomalies → [Alert if Suspicious]
```

### 3. Mode Transition State Machine

```
    ┌─────────────┐  Anomaly   ┌─────────────┐
    │   Standard  │ Detected    │    Strict   │
    │  (Default)  ├────────────→│  (Elevated) │
    └──────┬──────┘             └──────┬──────┘
           │                           │
           │                           │ Attack
     Peace │                           │ Confirmed
      Time │                           ↓
           │                    ┌─────────────┐
           │                    │   Paranoid  │
           │                    │  (Lockdown) │
           │                    └──────┬──────┘
           │                           │
           │                           │ System
           │                           │ Failure
           ↓                           ↓
    ┌─────────────┐            ┌─────────────┐
    │   Relaxed   │            │  Emergency  │
    │    (Dev)    │            │(Break-glass)│
    └─────────────┘            └─────────────┘

    Transition Evidence Required:
    Standard→Strict: Anomaly score > threshold
    Strict→Paranoid: Confirmed attack indicators
    Paranoid→Emergency: Auth system failure
    Any→Standard: Manual reset + audit
```

---

## Part VIII: Production Examples

### Example 1: Kubernetes Pod Security Capsule

When a pod needs to access a secret:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
  namespace: production
spec:
  serviceAccountName: app-service-account
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
  containers:
  - name: app
    image: secure-app:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

Generated Security Capsule:
```json
{
  "workload": {
    "pod": "secure-app",
    "namespace": "production",
    "service_account": "app-service-account",
    "uid": "pod-uuid-12345"
  },
  "security_context": {
    "run_as_user": 1000,
    "run_as_group": 2000,
    "non_root": true,
    "read_only_root": true,
    "no_privilege_escalation": true,
    "capabilities_dropped": ["ALL"]
  },
  "authorization": {
    "rbac_roles": ["secret-reader"],
    "allowed_secrets": ["app-secrets"],
    "namespace_isolation": true
  },
  "attestation": {
    "admission_controller": "validated",
    "pod_security_policy": "restricted",
    "image_signature": "verified",
    "image_scan": "passed"
  },
  "network": {
    "network_policy": "enforced",
    "service_mesh": "istio",
    "mtls": "required",
    "egress": "restricted"
  }
}
```

### Example 2: Database Access with Row-Level Security

Multi-tenant database access:

```sql
-- PostgreSQL Row Level Security Policy
CREATE POLICY tenant_isolation ON sensitive_data
    FOR ALL
    TO application_role
    USING (
        tenant_id = current_setting('app.tenant_id')::INT
        AND classification <= current_setting('app.clearance')::TEXT
    );
```

Security Capsule for Query:
```json
{
  "database_access": {
    "user": "app_user",
    "role": "application_role",
    "connection_id": "conn_789"
  },
  "session_context": {
    "tenant_id": 42,
    "clearance": "confidential",
    "source_ip": "10.0.1.5",
    "application": "reporting-service"
  },
  "query_authorization": {
    "allowed_tables": ["sensitive_data"],
    "row_filter": "tenant_id = 42",
    "column_mask": ["ssn", "credit_card"],
    "operation": "SELECT"
  },
  "audit": {
    "query_fingerprint": "SELECT * FROM sensitive_data WHERE...",
    "timestamp": "2024-01-15T10:35:00Z",
    "affected_rows_estimate": 1500
  }
}
```

### Example 3: CI/CD Pipeline Security

Code deployment with security gates:

```json
{
  "pipeline": {
    "id": "pipeline-123",
    "repository": "github.com/company/app",
    "branch": "main",
    "commit": "abc123def",
    "triggered_by": "user:developer@company.com"
  },
  "security_gates": {
    "sast": {
      "tool": "sonarqube",
      "status": "passed",
      "issues": {
        "critical": 0,
        "high": 0,
        "medium": 3
      }
    },
    "dependency_scan": {
      "tool": "snyk",
      "status": "passed",
      "vulnerabilities": {
        "critical": 0,
        "high": 1,
        "medium": 5
      }
    },
    "container_scan": {
      "tool": "trivy",
      "status": "passed",
      "cve_count": 2
    },
    "secrets_scan": {
      "tool": "trufflehog",
      "status": "passed",
      "secrets_found": 0
    }
  },
  "approval": {
    "required_approvers": 2,
    "approvals": [
      {
        "approver": "user:lead@company.com",
        "timestamp": "2024-01-15T09:00:00Z",
        "signature": "sig1"
      },
      {
        "approver": "user:security@company.com",
        "timestamp": "2024-01-15T09:30:00Z",
        "signature": "sig2"
      }
    ]
  },
  "deployment_authorization": {
    "environment": "production",
    "allowed": true,
    "restrictions": [
      "deploy_window:business_hours",
      "rollback_enabled:true",
      "canary_required:true"
    ]
  }
}
```

---

## Part IX: Transfer Tests

### Near Transfer: API Rate Limiting

Apply security capsule pattern to API rate limiting:

```json
{
  "rate_limit_capsule": {
    "client": {
      "api_key": "key_xyz",
      "tier": "premium",
      "identity": "customer:12345"
    },
    "quotas": {
      "requests_per_second": 100,
      "requests_per_day": 1000000,
      "burst_size": 500
    },
    "current_usage": {
      "second": 45,
      "day": 450000,
      "burst_tokens": 200
    },
    "evidence": {
      "valid_api_key": true,
      "payment_status": "current",
      "abuse_score": 0.1
    },
    "decision": "allow",
    "headers": {
      "X-RateLimit-Limit": "100",
      "X-RateLimit-Remaining": "55",
      "X-RateLimit-Reset": "1642357260"
    }
  }
}
```

### Medium Transfer: Healthcare HIPAA Compliance

Apply to patient data access:

```json
{
  "hipaa_security_capsule": {
    "user": {
      "id": "doctor:dr-smith",
      "role": "attending_physician",
      "department": "cardiology",
      "npi": "1234567890"
    },
    "patient_context": {
      "patient_id": "patient:98765",
      "relationship": "treating_physician",
      "consent": {
        "given": true,
        "scope": "treatment",
        "expiry": "2024-12-31"
      }
    },
    "access_request": {
      "resource": "medical_records",
      "purpose": "treatment",
      "data_types": ["labs", "imaging", "notes"],
      "time_range": "last_6_months"
    },
    "compliance": {
      "minimum_necessary": true,
      "break_glass": false,
      "encryption": "AES-256",
      "audit_logged": true
    },
    "authorization": {
      "granted": true,
      "restrictions": [
        "no_mental_health_records",
        "no_substance_abuse_records",
        "watermark_all_exports"
      ]
    }
  }
}
```

### Far Transfer: Autonomous Vehicle Security

Apply to vehicle-to-vehicle communication:

```json
{
  "v2v_security_capsule": {
    "vehicle": {
      "id": "vehicle:tesla:vin123",
      "location": {
        "lat": 37.7749,
        "lon": -122.4194,
        "accuracy_m": 1.5
      },
      "velocity": {
        "speed_mps": 25,
        "heading": 45
      }
    },
    "message": {
      "type": "emergency_brake",
      "timestamp": "2024-01-15T10:35:00.123Z",
      "ttl_ms": 100
    },
    "cryptographic": {
      "signature": "ecdsa_signature",
      "certificate": "vehicle_cert",
      "freshness": "nonce:abc123"
    },
    "trust_evaluation": {
      "sender_reputation": 0.95,
      "message_plausibility": 0.88,
      "location_verification": "confirmed",
      "behavior_consistency": 0.92
    },
    "decision": {
      "trust_level": "high",
      "action": "apply_emergency_brake",
      "confidence": 0.91
    }
  }
}
```

---

## Implementation Checklist

When implementing Security Context Capsules:

### Design Phase
- [ ] Identify all trust boundaries in the system
- [ ] Map authentication methods to guarantee vectors
- [ ] Define authorization policies and evidence requirements
- [ ] Design capsule schema for your domain
- [ ] Plan mode transitions and triggers

### Implementation Phase
- [ ] Implement capsule generation at authentication points
- [ ] Add capsule validation at service boundaries
- [ ] Configure mTLS for service-to-service communication
- [ ] Set up audit logging for all security decisions
- [ ] Implement capsule refresh mechanism

### Validation Phase
- [ ] Test mode transitions under load
- [ ] Verify capsule propagation across services
- [ ] Validate cryptographic signatures
- [ ] Test emergency break-glass procedures
- [ ] Measure performance impact of verification

### Operation Phase
- [ ] Monitor capsule validation failures
- [ ] Track authorization decision latencies
- [ ] Alert on anomalous access patterns
- [ ] Review audit logs regularly
- [ ] Update security policies based on evidence

---

## Conclusion: Evidence-Based Security

Security Context Capsules transform security from binary gates to continuous evidence evaluation. Every request carries proof of its trustworthiness. Every boundary crossing requires fresh evidence. Every security decision is logged and auditable.

This approach enables:
1. **Zero-trust architecture**: No implicit trust based on network location
2. **Defense in depth**: Multiple evidence types required
3. **Adaptive security**: Mode transitions based on threat level
4. **Compliance**: Complete audit trail of all decisions
5. **Performance**: Caching and propagation of validated evidence

Remember: In distributed systems, trust is not given—it's proven with evidence, carried in capsules, verified at every boundary, and revoked when violated.

---

*"Security is not a feature to be added, but evidence to be collected, validated, and enforced at every boundary crossing."*