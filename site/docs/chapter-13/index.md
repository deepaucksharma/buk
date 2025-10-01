# Chapter 13: Security in Distributed Systems

## Introduction: The Castle That Became a City

In distributed systems, you're not securing a castle—you're securing a city where every building has doors, windows, and tunnels you didn't know existed.

When Equifax lost 147 million records in 2017, they weren't breached through sophisticated attacks on their core security systems. An attacker exploited a known vulnerability in Apache Struts—a web framework—on a single edge server. That server could access internal systems. Those systems could access databases. The breach spread through the architecture like water finding cracks in a dam. The attackers had access for **four months** before detection.

This wasn't a failure of encryption, firewalls, or access control lists. It was a failure of **invariant preservation under adversarial conditions**. Security in distributed systems isn't about building walls—it's about preserving authenticity, integrity, and confidentiality properties across trust boundaries when active adversaries try to violate them.

### Security as Invariant Preservation

Throughout this book, we've framed distributed systems as machines for preserving invariants by converting uncertainty into evidence. Security is the most adversarial form of this challenge:

- **Normal operation**: Uncertainty comes from physics (network delays, clock skew, partitions)
- **Security operation**: Uncertainty comes from adversaries actively trying to violate invariants

In both cases, the solution is the same: generate evidence, verify it at boundaries, degrade gracefully when evidence is missing or expired, and preserve essential invariants in all modes.

The security invariants we protect:

1. **AUTHENTICITY**: Only authorized principals can perform actions
2. **INTEGRITY**: Data is unmodified from its authorized source
3. **CONFIDENTIALITY**: Information is visible only to authorized principals
4. **AVAILABILITY**: Legitimate requests are served within bounds
5. **ACCOUNTABILITY**: Actions are attributable to identified principals

These aren't separate concerns—they compose. A system preserving authenticity generates identity evidence (tokens, certificates). That evidence has scope (which resources), lifetime (expiration), and binding (which principal). When evidence expires or crosses boundaries, the system must re-verify or degrade to a safe mode.

### Why Traditional Security Fails at Scale

Perimeter security—the "castle model"—assumes:

- Clear inside/outside boundary
- Trust everything inside
- Monitor/restrict what crosses the boundary
- Centralized enforcement

Distributed systems violate every assumption:

- **No clear boundary**: Services span data centers, clouds, edge locations
- **Can't trust inside**: Compromised containers, supply chain attacks, insider threats
- **Boundaries everywhere**: Every service call crosses a trust boundary
- **Decentralized enforcement**: Each node must independently verify and enforce

The Solar Winds attack (2020) demonstrated this perfectly. Attackers compromised the build system of network management software used by 18,000 organizations including Fortune 500 companies and government agencies. The malicious code was **signed with legitimate certificates**, passed through security scans, and was trusted by perimeter defenses. Once inside, it provided backdoor access for **nine months** before detection.

This is a supply chain attack violating the authenticity invariant. The evidence (code signature) was valid but generated through a compromised process. Traditional security said "trust signed code." Modern security says "verify continuously, trust nothing, assume breach."

### What This Chapter Will Transform

By the end, you'll understand:

1. **The distributed attack surface**: Network, application, infrastructure, identity, and consensus attack vectors
2. **Zero Trust architecture**: Never trust, always verify—with evidence
3. **Encryption everywhere**: At rest, in transit, and in use
4. **Service mesh security**: mTLS, identity, and authorization at every hop
5. **Byzantine fault tolerance**: Consensus under adversarial conditions
6. **Supply chain security**: SBOM, provenance, and attestation
7. **Security monitoring**: Detection, incident response, and forensics
8. **Compliance frameworks**: SOC2, ISO27001, GDPR, HIPAA

More importantly, you'll learn to **think in security invariants**: What property am I protecting? What evidence proves it's preserved? What happens when evidence expires? How do I degrade safely?

### The Security Mental Model

Security follows the same evidence lifecycle as the rest of the book:

```
Generate Evidence (authenticate) →
Propagate Evidence (attach to requests) →
Verify Evidence (at every boundary) →
Use Evidence (authorize actions) →
Expire Evidence (time-bound validity) →
Renew/Revoke Evidence (lifecycle management)
```

Every security mechanism fits this pattern:

- **mTLS**: Generate (certificate), Propagate (TLS handshake), Verify (certificate chain), Use (authorize connection), Expire (certificate lifetime), Renew (rotation)
- **JWT tokens**: Generate (sign), Propagate (Authorization header), Verify (signature + claims), Use (RBAC decision), Expire (exp claim), Renew (refresh token)
- **Audit logs**: Generate (action record), Propagate (to logging service), Verify (integrity hash), Use (forensics), Expire (retention), Renew (archival)

When security fails, it's usually because evidence is:

- **Missing**: No verification at a boundary (Equifax)
- **Expired**: Stale credentials still accepted (Capital One)
- **Invalid**: Compromised but trusted (Solar Winds)
- **Insufficient**: Weak evidence for strong claims (cryptocurrency exploits)

Let's begin with real breaches that illustrate each failure mode.

---

## Part 1: Intuition (First Pass) — The Felt Need

### The Equifax Breach (2017): Missing Evidence at Boundaries

**The Setup**: Equifax operated a dispute resolution web portal. This portal used Apache Struts, a Java web framework. In March 2017, a critical vulnerability (CVE-2017-5638) was disclosed: attackers could execute arbitrary code by sending a malicious `Content-Type` header.

**The Timeline**:

- March 7: Vulnerability disclosed, patch available
- March 8: Equifax security team notified
- March 9: Equifax scanned systems but **missed the vulnerable portal**
- May 13: Attackers exploited the vulnerability
- May-July: Attackers had access for **76 days**, exfiltrating data
- July 29: Equifax discovered the breach
- September 7: Public disclosure

**What Failed**:

The portal had access to internal databases containing 147 million records. The security failure wasn't at the perimeter (the portal was public) or at the database (it had access controls). The failure was **missing verification at the boundary between the compromised portal and internal systems**.

In evidence terms:

- **Missing Evidence**: The portal's credentials to access internal databases never expired
- **No Boundary Verification**: Internal systems trusted requests from the portal without re-verifying identity or intent
- **No Degradation**: When the portal was compromised, there was no mechanism to detect abnormal access patterns and degrade to a restricted mode
- **No Segmentation**: One compromised component could access everything it was "authorized" for, with no further checks

**The Invariant Violation**:

**AUTHENTICITY** was violated. The system couldn't distinguish "legitimate portal making authorized queries" from "attacker using stolen portal credentials."

**The Fix (Zero Trust)**:

Modern architecture would:

1. **Short-lived credentials**: Portal gets time-bound tokens (15 min), must constantly re-authenticate
2. **Scope limitation**: Each token scoped to specific queries, not "all database access"
3. **Continuous verification**: Every query verified against expected patterns
4. **Anomaly detection**: 5x increase in query volume triggers degraded mode (rate limiting)
5. **Micro-segmentation**: Portal can only access dispute data, not all customer records

This is **evidence-based security**: Generate fresh evidence frequently, verify at every boundary, degrade when patterns don't match expectations.

### The Solar Winds Breach (2020): Invalid But Trusted Evidence

**The Setup**: Solar Winds produced Orion, network monitoring software used by 18,000+ organizations. Attackers compromised the **build system** and inserted malicious code into legitimate software updates.

**The Attack Vector**:

1. Compromise build server (likely through supply chain or credential theft)
2. Inject backdoor code into Orion updates
3. Sign the malicious updates with **legitimate Solar Winds certificates**
4. Distribute through normal update channels
5. Customers install "trusted" updates
6. Backdoor provides persistent access

**What Failed**:

The evidence (code signature) was **cryptographically valid** but **semantically invalid**. The signature proved "this code came from Solar Winds' build system" but not "this code is safe" or "this code matches reviewed source."

**The Invariant Violation**:

**INTEGRITY** was violated. The code was modified from its intended form, but the evidence (signature) didn't reflect this because the signing process itself was compromised.

**The Deep Problem**:

Trust is transitive but verification isn't. Organizations trusted Solar Winds, so they trusted signed updates. But Solar Winds' signing process trusted the build system, which was compromised. The chain of trust had a broken link, but the evidence didn't reveal it.

**The Fix (Provenance + Attestation)**:

Modern supply chain security requires:

1. **SBOM (Software Bill of Materials)**: Cryptographic inventory of all components
2. **Build provenance**: Evidence that code was built from specific source commits
3. **Reproducible builds**: Independent verification that source → binary is deterministic
4. **SLSA framework**: Multiple attestations (source, build, dependencies) that compose
5. **Continuous verification**: Runtime checks that loaded code matches expected hashes

This is **evidence composition**: Each stage generates evidence that the next stage verifies. Compromise at one stage should be detectable by verifying the full chain.

### The Cryptocurrency Bridge Attacks (2021-2023): Insufficient Evidence

**The Setup**: Blockchain bridges allow transferring assets between different chains (e.g., Ethereum ↔ Binance Smart Chain). The Ronin bridge held $600M in assets. The Wormhole bridge held $320M.

**How Bridges Work**:

1. User deposits 10 ETH on Ethereum into the bridge contract
2. Validators observe the deposit and sign a message
3. When enough validators sign (e.g., 5 of 9), the bridge mints 10 "wrapped ETH" on the target chain
4. This is **consensus**: converting uncertain deposit into certain minting authority

**The Ronin Attack (March 2022)**:

Attackers compromised 5 of 9 validator keys. With the majority, they could sign fraudulent withdrawal messages claiming "these addresses deposited assets" when they hadn't. The bridge minted wrapped tokens, and the attackers drained $625M.

**What Failed**:

The threshold was **insufficient evidence**. 5-of-9 means the system can tolerate 4 Byzantine (malicious) validators. But if 5 validators are controlled by related parties or use similar security practices, compromising all 5 is feasible.

This is the Byzantine generals problem: how many malicious participants can you tolerate? Classical BFT requires **3f+1 total nodes to tolerate f Byzantine nodes**. Ronin's 5-of-9 could tolerate 2 Byzantine nodes, but 5 were compromised.

**The Wormhole Attack (February 2022)**:

Attackers exploited a signature verification bug in the bridge contract. The contract failed to verify that the signers were actually authorized validators. The attacker generated signatures from unauthorized keys, and the contract accepted them. $320M stolen.

**What Failed**:

The evidence was **not properly verified**. The contract checked "are there enough signatures?" but not "are these signatures from authorized validators?" This is like accepting a passport without checking it's from a recognized country.

**The Invariant Violation**:

**AUTHENTICITY** and **INTEGRITY** both violated. The authorization to mint tokens came from unauthorized or compromised sources, and the evidence verification was incomplete.

**The Fix (BFT + Verification)**:

Secure bridges require:

1. **Higher thresholds**: 3f+1 validators, geographically and organizationally distributed
2. **Complete verification**: Check signature validity **and** signer authorization
3. **Economic security**: Validators stake collateral that's slashed for misbehavior
4. **Time locks**: Large withdrawals have delays, allowing dispute resolution
5. **Anomaly detection**: Unusual withdrawal patterns trigger additional verification

This is **evidence with stakes**: Validators put capital at risk, making Byzantine behavior economically irrational.

### Common Patterns in Security Failures

All three breaches share patterns:

1. **Evidence missing at critical boundaries** (Equifax: portal → database)
2. **Evidence trusted without continuous verification** (Solar Winds: signed code)
3. **Evidence insufficient for the security model** (Crypto: threshold too low)
4. **No degraded mode when evidence weakens** (all three: binary trust/distrust)

The lesson: **Security is evidence lifecycle management under adversarial conditions.**

---

## Part 2: Understanding (Second Pass) — The Mechanisms

### The Distributed Attack Surface

In centralized systems, you defend a perimeter. In distributed systems, **every component is a potential entry point**, and **every boundary is a potential vulnerability**.

#### Five Attack Surfaces

**1. Network Layer**

Attacks that exploit network protocols and topology:

- **Man-in-the-middle (MITM)**: Intercept and modify traffic between nodes
- **DNS hijacking**: Redirect requests to attacker-controlled servers
- **BGP hijacking**: Reroute internet traffic at the routing layer
- **DDoS amplification**: Use reflection to overwhelm targets
- **SSL stripping**: Downgrade HTTPS to HTTP

**Example**: In 2018, attackers hijacked BGP routes to redirect traffic destined for Amazon's Route53 DNS to attacker-controlled servers. They obtained valid TLS certificates through DNS validation (because they controlled DNS responses). Users saw valid HTTPS but were talking to attackers.

**Invariant threatened**: **AUTHENTICITY** (am I talking to who I think I am?)

**2. Application Layer**

Attacks that exploit application logic and interfaces:

- **Injection attacks**: SQL injection, command injection, log injection
- **Deserialization exploits**: Malicious objects that execute code when deserialized
- **SSRF (Server-Side Request Forgery)**: Trick server into making requests on attacker's behalf
- **XXE (XML External Entity)**: Exploit XML parsing to read files or make requests
- **Logic flaws**: Exploit business logic (e.g., race conditions in payment systems)

**Example**: Capital One breach (2019). Attacker exploited SSRF in a WAF (Web Application Firewall) to request EC2 instance metadata (`http://169.254.169.254/latest/meta-data/iam/security-credentials/`). This returned IAM credentials for the WAF's role, which had excessive S3 permissions. 100M credit applications stolen.

**Invariant threatened**: **AUTHENTICITY** and **CONFIDENTIALITY** (server impersonated legitimate user; accessed unauthorized data)

**3. Infrastructure Layer**

Attacks targeting the execution environment:

- **Container escape**: Break out of container to access host
- **Kernel exploits**: Exploit OS vulnerabilities to gain privilege
- **Hypervisor breakout**: Escape VM to access hypervisor or other VMs
- **Side-channel attacks**: Extract secrets through timing, power, or electromagnetic analysis
- **Supply chain**: Compromise dependencies, build tools, or base images

**Example**: RunC vulnerability (CVE-2019-5736). Attacker could exploit a container to overwrite the host's RunC binary, then gain root on the host when any container started. This threatened multi-tenant systems where containers from different customers ran on the same host.

**Invariant threatened**: **ISOLATION** (tenants should not affect each other)

**4. Identity Layer**

Attacks targeting authentication and authorization:

- **Credential stuffing**: Use leaked passwords from other sites
- **Session hijacking**: Steal session tokens to impersonate users
- **Privilege escalation**: Exploit bugs to gain higher privileges
- **Token replay**: Reuse captured tokens beyond their intended scope
- **Identity confusion**: Confuse system about which principal is acting

**Example**: Okta breach (2022). Attacker compromised a third-party contractor's laptop, which had access to Okta's internal systems. The contractor had MFA, but the laptop had a valid session. Attacker accessed customer support tools that could reset MFA for customer tenants. This is a **boundary crossing failure**: contractor's access was trusted the same as internal employee's.

**Invariant threatened**: **AUTHENTICITY** (who is this principal really?)

**5. Consensus Layer**

Attacks targeting distributed agreement:

- **Sybil attacks**: Create many fake identities to overwhelm voting
- **51% attacks**: Control majority of consensus power to rewrite history
- **Eclipse attacks**: Isolate a node so it sees a false view of the network
- **Time manipulation**: Exploit timestamp-based logic
- **Censorship**: Prevent specific transactions from being included

**Example**: Bitcoin Gold 51% attack (2018). Attacker rented enough mining power to control >51% of hashrate for a few hours. They double-spent, sending funds to exchanges, withdrawing, then reorganizing the blockchain to return the funds to themselves. $18M stolen.

**Invariant threatened**: **UNIQUENESS** and **ORDER** (only one transaction should spend each coin; history should be immutable)

### Zero Trust Architecture

**Traditional model**: "Trust but verify" → Trust inside the perimeter, verify at the edge

**Zero Trust model**: "Never trust, always verify" → Trust nothing, verify everything

#### Core Principles

1. **Assume breach**: Operate as if adversaries are already inside
2. **Verify explicitly**: Every request authenticated, authorized, and encrypted
3. **Least privilege**: Minimum necessary access for minimum necessary time
4. **Micro-segmentation**: Isolate workloads; breach doesn't spread

#### The Evidence Flow

In Zero Trust, every request carries evidence and faces verification:

```
Client Request
  ↓
[Generate Identity Evidence]
  ↓ (mTLS certificate or JWT token)
[Verify at Service Boundary]
  ↓ (check signature, claims, expiration)
[Generate Authorization Evidence]
  ↓ (policy evaluation result)
[Execute with Least Privilege]
  ↓
[Generate Audit Evidence]
  ↓ (log action with full context)
[Return Response]
```

**At every step, evidence is generated and verified.**

#### Authentication: Multi-Factor Verification

```python
class ZeroTrustAuthenticator:
    def __init__(self):
        self.risk_engine = RiskEngine()
        self.policy_engine = PolicyEngine()

    def authenticate_request(self, request):
        # Multi-factor evidence collection
        identity = self.verify_identity(request)  # Who claims to be making request?
        device = self.verify_device(request)      # From trusted device?
        location = self.verify_location(request)  # From expected location?
        behavior = self.verify_behavior(request)  # Matches historical patterns?

        # Evidence composition → risk score
        risk_score = self.risk_engine.calculate(
            identity, device, location, behavior
        )

        # Adaptive authentication based on evidence strength
        if risk_score > 0.8:
            # Evidence insufficient for high-risk action
            return self.deny(reason="High risk score")
        elif risk_score > 0.5:
            # Evidence marginal → require additional evidence
            return self.require_mfa(factors=['SMS', 'TOTP'])
        else:
            # Evidence sufficient → allow with monitoring
            return self.allow_with_enhanced_logging()
```

**Evidence types**:

- **Identity**: Password + MFA (something you know + have)
- **Device**: Certificate or TPM attestation (something the device has)
- **Location**: IP geolocation, ASN (contextual evidence)
- **Behavior**: ML model on historical access patterns (probabilistic evidence)

**Composition**: More evidence types → stronger authenticity guarantee. Weak evidence → require additional factors or deny.

#### Authorization: Policy as Code

```python
class ZeroTrustAuthorizer:
    def __init__(self):
        self.opa_engine = OPAEngine()  # Open Policy Agent

    def authorize_action(self, principal, resource, action):
        # Gather all relevant policies
        policies = self.get_policies(principal, resource)

        # Evaluate each policy (OPA-style)
        decisions = []
        for policy in policies:
            decision = self.opa_engine.evaluate(
                policy,
                {
                    'principal': principal,
                    'resource': resource,
                    'action': action,
                    'time': time.now(),
                    'context': self.get_request_context()
                }
            )
            decisions.append(decision)

        # Combine decisions (deny wins)
        if any(d.effect == 'DENY' for d in decisions):
            return AuthzDecision.DENY
        elif any(d.effect == 'ALLOW' for d in decisions):
            return AuthzDecision.ALLOW
        else:
            # Default deny: no policy allowed it
            return AuthzDecision.DENY
```

**Key insight**: Authorization is **evidence-based decision making**. The evidence is:

- **Principal's identity claims** (from authentication)
- **Resource's access policies** (from policy store)
- **Action's requirements** (read vs. write vs. delete)
- **Contextual signals** (time, location, recent activity)

The policy engine **generates authorization evidence**: "Principal P is allowed to perform action A on resource R at time T because policy Π says so."

This evidence is:

- **Scoped**: Valid only for this (P, R, A) tuple
- **Time-bound**: Valid only near time T (policies can change)
- **Non-transitive**: Cannot be delegated without explicit re-authorization

#### mTLS: Mutual Authentication

Traditional TLS: Client verifies server's identity (certificate). Server may verify client through other means (password, token).

**mTLS**: Both sides present certificates. Identity is cryptographic, not password-based.

```yaml
# Service mesh mTLS configuration
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT  # Reject any connection without mTLS

---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: frontend-to-backend
spec:
  selector:
    matchLabels:
      app: backend
  rules:
  - from:
    - source:
        principals:
        - "cluster.local/ns/production/sa/frontend"
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/*"]
```

**Evidence flow in mTLS**:

1. **Generate**: Each service gets a certificate (identity evidence) from a CA
2. **Propagate**: During TLS handshake, both sides present certificates
3. **Verify**: Each side verifies the other's certificate chain back to trusted CA
4. **Bind**: TLS session is bound to these identities
5. **Use**: Authorization policies use the verified identity
6. **Expire**: Certificates have short lifetimes (often 24 hours), auto-rotated

**Why mTLS for Zero Trust**:

- **Strong authentication**: Cryptographic identity, not passwords
- **No bearer tokens**: Can't steal and replay (session is bound to certificate)
- **Short-lived**: Compromise window is limited
- **Automatic**: Service mesh handles it; developers don't see it

### Encryption Everywhere

Security requires preserving **CONFIDENTIALITY** and **INTEGRITY** at all times and locations.

#### Three States of Data

**1. Data at Rest**

Data stored on disk must be encrypted so that physical access to storage doesn't compromise confidentiality.

```python
class DataAtRestEncryption:
    def __init__(self):
        self.kms = KMSClient()  # Key Management Service

    def encrypt(self, data, context):
        # Generate data encryption key (DEK)
        dek = os.urandom(32)  # 256-bit key

        # Encrypt data with DEK (AES-256-GCM)
        iv = os.urandom(12)
        cipher = AES.new(dek, AES.MODE_GCM, nonce=iv)
        ciphertext, tag = cipher.encrypt_and_digest(data)

        # Encrypt DEK with KEK (Key Encryption Key from KMS)
        encrypted_dek = self.kms.encrypt(
            key_id='master-key-id',
            plaintext=dek,
            context=context  # Binding to tenant/purpose
        )

        # Store: ciphertext + encrypted DEK + IV + tag
        return {
            'ciphertext': ciphertext,
            'encrypted_dek': encrypted_dek,
            'iv': iv,
            'tag': tag,
            'algorithm': 'AES-256-GCM',
            'context': context
        }

    def decrypt(self, encrypted_data):
        # Decrypt DEK using KMS
        dek = self.kms.decrypt(
            ciphertext=encrypted_data['encrypted_dek'],
            context=encrypted_data['context']
        )

        # Decrypt data with DEK
        cipher = AES.new(dek, AES.MODE_GCM, nonce=encrypted_data['iv'])
        plaintext = cipher.decrypt_and_verify(
            encrypted_data['ciphertext'],
            encrypted_data['tag']
        )

        return plaintext
```

**Envelope encryption**: Data encrypted with DEK, DEK encrypted with KEK. This allows:

- **Key rotation**: Rotate KEK without re-encrypting all data
- **Access control**: KMS enforces who can decrypt KEKs
- **Audit**: All decryption requests go through KMS and are logged

**Evidence**: The encrypted DEK is evidence that "only principals authorized to use this KMS key can decrypt this data."

**2. Data in Transit**

Data moving between nodes must be encrypted so that network access doesn't compromise confidentiality.

```python
class DataInTransitEncryption:
    def establish_connection(self, server):
        # TLS 1.3 handshake
        # 1. Client Hello: supported ciphers, extensions
        client_hello = self.create_client_hello()

        # 2. Server Hello: chosen cipher, certificate, key exchange
        server_hello = server.process_client_hello(client_hello)

        # 3. Verify server certificate
        if not self.verify_certificate(server_hello.certificate):
            raise SecurityError("Invalid server certificate")

        # 4. Key exchange (ECDHE for forward secrecy)
        shared_secret = self.ecdhe_key_exchange(server_hello.key_share)

        # 5. Derive session keys
        keys = self.derive_keys(shared_secret)

        # 6. Encrypted communication
        return TLSSession(keys)
```

**Forward secrecy**: Even if the server's private key is later compromised, past sessions can't be decrypted because session keys were derived from ephemeral ECDHE keys.

**Evidence**: The TLS certificate is evidence of server identity. The session keys are evidence that this connection is confidential.

**3. Data in Use**

Data being processed in memory is vulnerable if an attacker gains access to the process or hardware.

```python
class DataInUseEncryption:
    def __init__(self):
        self.enclave = SecureEnclave()

    def process_sensitive_data(self, encrypted_data):
        # Load encrypted data into secure enclave
        enclave_handle = self.enclave.create()

        # Decrypt inside enclave (using enclave's sealed keys)
        plaintext = enclave_handle.decrypt(encrypted_data)

        # Process inside enclave
        result = enclave_handle.execute(self.computation, plaintext)

        # Encrypt result before leaving enclave
        encrypted_result = enclave_handle.encrypt(result)

        # Destroy enclave (clears all memory)
        enclave_handle.destroy()

        return encrypted_result
```

**Secure enclaves** (Intel SGX, ARM TrustZone, AMD SEV): Hardware-isolated execution environment. Even the OS can't see inside.

**Homomorphic encryption**: Perform computations on encrypted data without decrypting.

```python
class HomomorphicEncryption:
    def __init__(self):
        self.context = self.create_he_context()

    def encrypted_sum(self, encrypted_values):
        # Sum in encrypted domain
        result = self.context.zero()
        for enc_val in encrypted_values:
            result = self.context.add(result, enc_val)
        return result

    def private_analytics(self, encrypted_data):
        # Compute average without seeing individual values
        encrypted_sum = self.encrypted_sum(encrypted_data)
        count = len(encrypted_data)
        encrypted_avg = self.context.multiply_plain(encrypted_sum, 1.0 / count)
        return encrypted_avg
```

**Use case**: Medical research. Hospitals encrypt patient data with homomorphic encryption. Researchers compute statistics (average age, correlation between treatments and outcomes) without ever seeing individual patient data.

**Evidence**: The encrypted result proves "this computation was performed correctly on the data" without revealing the data.

### Service Mesh Security Model

A service mesh provides security infrastructure as a **transparent layer** below applications.

#### Four Security Pillars

**1. Identity (SPIFFE/SPIRE)**

Every service gets a cryptographic identity.

```yaml
# SPIFFE ID format
spiffe://trust-domain/namespace/production/service/backend

# Certificate attributes:
Subject: service-backend
SAN: spiffe://prod.example.com/ns/production/svc/backend
Issuer: SPIRE Server CA
Validity: 24 hours
```

**Evidence**: The certificate is evidence that "SPIRE CA attests this workload is the backend service in the production namespace."

**2. Authentication (mTLS)**

All service-to-service communication uses mTLS automatically.

```
Frontend → Sidecar Proxy → Network → Sidecar Proxy → Backend
  |            ↑                           ↑            |
  |            |                           |            |
  +--- Request |                           | Request ---+
               |                           |
          [mTLS Handshake]────────────[mTLS Handshake]
          Uses frontend cert            Uses backend cert
```

**Evidence flow**:

1. Frontend makes HTTP request to backend
2. Frontend's sidecar intercepts, initiates mTLS to backend's sidecar
3. Both sidecars exchange and verify certificates
4. Encrypted tunnel established
5. Request flows through tunnel
6. Backend's sidecar verifies authorization policy before forwarding to backend

**3. Authorization (Policy Engine)**

Centralized policy enforcement.

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: backend-authz
spec:
  selector:
    matchLabels:
      app: backend
  rules:
  # Allow frontend to call /api/*
  - from:
    - source:
        principals: ["cluster.local/ns/prod/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/*"]
    when:
    - key: request.headers[x-tenant-id]
      values: ["tenant-*"]

  # Deny all other access
  action: DENY
```

**Evidence**: The authorization decision is evidence that "this request matches policy P, which allows it."

**4. Observability (Telemetry)**

All security events are logged and traced.

```
Access Log Entry:
{
  "timestamp": "2023-10-01T14:32:01Z",
  "source": {
    "identity": "spiffe://prod.example.com/ns/prod/svc/frontend",
    "ip": "10.0.1.5"
  },
  "destination": {
    "identity": "spiffe://prod.example.com/ns/prod/svc/backend",
    "ip": "10.0.2.3"
  },
  "request": {
    "method": "POST",
    "path": "/api/orders",
    "headers": {"x-tenant-id": "tenant-42"}
  },
  "response": {
    "status": 200,
    "duration_ms": 42
  },
  "policy": {
    "matched": "backend-authz",
    "decision": "ALLOW"
  }
}
```

**Evidence**: The log is forensic evidence that "this request occurred with these properties and was allowed by this policy."

### Secrets Management

Secrets (passwords, API keys, certificates) are high-value targets. They must be:

- **Generated** securely
- **Stored** encrypted
- **Distributed** on demand with access control
- **Rotated** frequently
- **Audited** for every access

```python
class SecretsManager:
    def __init__(self):
        self.vault = VaultClient()
        self.rotation_schedule = {}

    def get_secret(self, path, version=None):
        # 1. Authenticate caller
        caller_identity = self.get_caller_identity()

        # 2. Authorize access
        if not self.is_authorized(caller_identity, path, 'read'):
            self.audit_log('SECRET_ACCESS_DENIED', path, caller_identity)
            raise AuthorizationError()

        # 3. Fetch secret (versioned)
        secret = self.vault.get_secret(path, version)

        # 4. Create lease (time-bound access)
        lease_id = self.vault.create_lease(
            path=path,
            ttl=3600,  # 1 hour
            renewable=True
        )

        # 5. Audit log
        self.audit_log('SECRET_ACCESS_GRANTED', path, caller_identity, lease_id)

        # 6. Schedule rotation if needed
        if self.should_rotate(path):
            self.schedule_rotation(path)

        return {
            'value': secret,
            'lease_id': lease_id,
            'ttl': 3600,
            'renewable': True
        }

    def rotate_secret(self, path):
        # 1. Generate new secret
        new_secret = self.generate_secret(path)

        # 2. Store new version (old versions remain accessible)
        version = self.vault.put_secret(path, new_secret)

        # 3. Notify consumers to refresh
        self.notify_rotation(path, version)

        # 4. Update rotation timestamp
        self.rotation_schedule[path] = time.now()

        # 5. Audit log
        self.audit_log('SECRET_ROTATED', path, version)
```

**Evidence lifecycle**:

- **Secret value**: Evidence of authorization to access a resource
- **Lease**: Evidence that access is time-bound
- **Audit log**: Evidence that access was granted and to whom

**Why rotation**:

If a secret is compromised, rotation limits the window of vulnerability. Short-lived secrets (1 hour) mean compromise detected in hour 2 has already expired.

### Byzantine Fault Tolerance

So far, we've discussed security against **external attackers**. But what if **internal nodes are malicious**?

This is the **Byzantine generals problem**: How do honest nodes reach consensus when some nodes are actively malicious?

#### Classical BFT: PBFT (Practical Byzantine Fault Tolerance)

To tolerate **f Byzantine nodes**, you need **3f + 1 total nodes**.

**Why 3f + 1?**

- **f nodes** can be Byzantine (arbitrary behavior)
- **f nodes** might be slow/crashed (indistinguishable from Byzantine)
- You need **f + 1 honest, responsive nodes** to form a quorum
- Total: f (Byzantine) + f (crashed) + f+1 (honest quorum) = 3f + 1

**PBFT Protocol** (simplified):

```python
class PBFTNode:
    def __init__(self, node_id, total_nodes):
        self.node_id = node_id
        self.total_nodes = total_nodes
        self.f = (total_nodes - 1) // 3  # Byzantine tolerance
        self.view = 0  # Current leader view

    def propose(self, request):
        # Only the leader proposes
        if not self.is_leader():
            raise NotLeaderError()

        # Phase 1: Pre-Prepare (leader broadcasts proposal)
        pre_prepare = {
            'type': 'PRE-PREPARE',
            'view': self.view,
            'sequence': self.next_sequence(),
            'request': request,
            'signature': self.sign(request)
        }
        self.broadcast(pre_prepare)

    def on_pre_prepare(self, msg):
        # Verify it's from the expected leader
        if not self.verify_leader(msg):
            return

        # Phase 2: Prepare (all nodes broadcast agreement)
        prepare = {
            'type': 'PREPARE',
            'view': msg['view'],
            'sequence': msg['sequence'],
            'digest': hash(msg['request']),
            'node_id': self.node_id,
            'signature': self.sign(msg)
        }
        self.broadcast(prepare)

    def on_prepare(self, msg):
        # Collect prepare messages
        self.prepares[msg['sequence']].append(msg)

        # Once we have 2f prepares (from different nodes)
        if len(self.prepares[msg['sequence']]) >= 2 * self.f:
            # Phase 3: Commit (broadcast commitment)
            commit = {
                'type': 'COMMIT',
                'view': msg['view'],
                'sequence': msg['sequence'],
                'digest': msg['digest'],
                'node_id': self.node_id,
                'signature': self.sign(msg)
            }
            self.broadcast(commit)

    def on_commit(self, msg):
        # Collect commit messages
        self.commits[msg['sequence']].append(msg)

        # Once we have 2f + 1 commits (quorum of honest nodes)
        if len(self.commits[msg['sequence']]) >= 2 * self.f + 1:
            # Execute the request
            self.execute(msg['sequence'])
```

**Evidence at each phase**:

- **Pre-Prepare**: Leader's signature is evidence "I propose this request"
- **Prepare**: 2f prepare signatures are evidence "enough nodes saw the proposal"
- **Commit**: 2f+1 commit signatures are evidence "a quorum agrees to execute"

**Why three phases?**

- **Pre-Prepare**: Establishes what to agree on
- **Prepare**: Ensures all honest nodes see the same proposal (Byzantine leader can't send different proposals to different nodes)
- **Commit**: Ensures enough nodes committed to execute (prevents rollback)

**Cost**: 3 phases × O(n²) messages (every node sends to every node). This is expensive but necessary for Byzantine tolerance.

#### Modern BFT: HotStuff

HotStuff (used by Diem/Libra) reduces to **linear communication** (O(n) messages per phase) by using threshold signatures.

```python
class HotStuffNode:
    def propose(self, request):
        # Leader creates proposal
        proposal = {
            'request': request,
            'view': self.view,
            'parent': self.last_committed,
            'signature': self.sign(request)
        }
        self.broadcast(proposal)

    def on_proposal(self, proposal):
        # Verify and vote
        if self.verify_proposal(proposal):
            vote = {
                'view': proposal['view'],
                'digest': hash(proposal),
                'partial_signature': self.partial_sign(proposal)
            }
            self.send_to_leader(vote)

    def on_votes(self, votes):
        # Leader collects votes
        if len(votes) >= 2 * self.f + 1:
            # Combine partial signatures into threshold signature
            threshold_sig = self.combine_signatures(votes)

            # Broadcast QC (Quorum Certificate)
            qc = {
                'view': self.view,
                'digest': votes[0]['digest'],
                'threshold_signature': threshold_sig
            }
            self.broadcast(qc)
```

**Evidence**: The threshold signature is cryptographic proof that 2f+1 nodes voted. Anyone can verify it, and it's much smaller than 2f+1 individual signatures.

**Why this matters for security**:

BFT consensus is how you get agreement when you **can't trust the nodes**. This is essential for:

- **Blockchains**: Validators might be malicious
- **Multi-party computation**: Participants might cheat
- **Cross-organization systems**: Parties might have conflicting interests

### Supply Chain Security

The Solar Winds breach showed that **the build and distribution process is an attack vector**. Supply chain security addresses this.

#### Software Bill of Materials (SBOM)

An SBOM is a cryptographic inventory of all components in a software artifact.

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "serialNumber": "urn:uuid:3e671687-395b-41f5-a30f-a58921a69b79",
  "version": 1,
  "metadata": {
    "timestamp": "2023-10-01T12:00:00Z",
    "component": {
      "name": "my-application",
      "version": "2.1.0"
    }
  },
  "components": [
    {
      "type": "library",
      "name": "express",
      "version": "4.18.2",
      "purl": "pkg:npm/express@4.18.2",
      "hashes": [
        {
          "alg": "SHA-256",
          "content": "3c4b4b1aa5ae9deae7f..."
        }
      ],
      "licenses": [{"id": "MIT"}],
      "vulnerabilities": []
    },
    {
      "type": "library",
      "name": "lodash",
      "version": "4.17.21",
      "purl": "pkg:npm/lodash@4.17.21",
      "hashes": [
        {
          "alg": "SHA-256",
          "content": "a1b2c3d4e5f..."
        }
      ],
      "licenses": [{"id": "MIT"}],
      "vulnerabilities": [
        {
          "id": "CVE-2021-23337",
          "severity": "HIGH",
          "description": "Command injection in template"
        }
      ]
    }
  ]
}
```

**Evidence**: The SBOM is evidence that "this artifact contains exactly these components with these versions and hashes."

**Why this matters**:

- **Vulnerability management**: Know if you're affected by CVE-2021-23337
- **License compliance**: Ensure you're not using GPL code in proprietary software
- **Provenance**: Verify artifacts haven't been tampered with

#### SLSA Framework (Supply-chain Levels for Software Artifacts)

SLSA defines levels of supply chain security:

**Level 1**: Build process exists and is documented

**Level 2**: Build service generates signed provenance

**Level 3**: Source and build are verified; provenance is tamper-proof

**Level 4**: Hermetic, reproducible builds; 2-person review

**Provenance attestation**:

```json
{
  "_type": "https://in-toto.io/Statement/v0.1",
  "subject": [
    {
      "name": "my-app",
      "digest": {"sha256": "abc123..."}
    }
  ],
  "predicateType": "https://slsa.dev/provenance/v0.2",
  "predicate": {
    "builder": {
      "id": "https://github.com/slsa-framework/slsa-github-generator/.github/workflows/builder.yml@v1.2.0"
    },
    "buildType": "https://github.com/slsa-framework/slsa-github-generator/build@v1",
    "invocation": {
      "configSource": {
        "uri": "git+https://github.com/myorg/myapp@refs/heads/main",
        "digest": {"sha1": "def456..."},
        "entryPoint": ".github/workflows/build.yml"
      }
    },
    "metadata": {
      "buildStartedOn": "2023-10-01T12:00:00Z",
      "buildFinishedOn": "2023-10-01T12:05:00Z"
    },
    "materials": [
      {
        "uri": "git+https://github.com/myorg/myapp@refs/heads/main",
        "digest": {"sha1": "def456..."}
      }
    ]
  }
}
```

**Evidence chain**:

1. **Source provenance**: Code came from git commit `def456`
2. **Build provenance**: Built by GitHub Actions workflow at specific commit
3. **Artifact provenance**: Output artifact has hash `abc123`
4. **Signature**: Entire provenance signed by build system

**Verification**: Deployment system can verify "this artifact was built from reviewed source code by the legitimate build system."

#### Container Security

Containers are a major attack surface. Security requires:

**1. Minimal base images**

```dockerfile
# Bad: Full OS (hundreds of packages, many vulnerabilities)
FROM ubuntu:22.04

# Good: Distroless (only runtime dependencies, no shell)
FROM gcr.io/distroless/static-debian11
```

**2. Vulnerability scanning**

```dockerfile
FROM alpine:3.18@sha256:abc123... AS builder

# Scan the image
RUN apk add --no-cache trivy && \
    trivy image --severity HIGH,CRITICAL --exit-code 1 .

# Build application
COPY src/ /app/
RUN build...

# Final image: minimal and scanned
FROM scratch
COPY --from=builder /app/binary /app/binary
USER nobody
ENTRYPOINT ["/app/binary"]
```

**3. Image signing**

```bash
# Sign the image
cosign sign --key cosign.key myregistry/myapp:v1.0

# Verify before deployment
cosign verify --key cosign.pub myregistry/myapp:v1.0
```

**Evidence**: The signature is evidence that "this image was built by the authorized publisher and hasn't been modified."

---

## Part 3: Mastery (Third Pass) — Composition and Operations

### Security as Evidence Lifecycle

Every security mechanism we've discussed follows the same **evidence lifecycle**:

```
┌─────────────────────────────────────────────────┐
│                 EVIDENCE LIFECYCLE               │
├─────────────────────────────────────────────────┤
│                                                  │
│  Generate → Propagate → Verify → Use → Expire  │
│     ↓          ↓          ↓       ↓       ↓    │
│   Cert      Request    Boundary  Authz   Renew  │
│   Token     Header     Check     Policy  Revoke │
│   Hash      Capsule    Validate  Allow   Archive│
│   Audit     Context    Signature Deny    Rotate │
│                                                  │
└─────────────────────────────────────────────────┘
```

#### Security Evidence Types

**1. Identity Evidence**

Proves "I am principal P"

- **Examples**: Certificates, JWT tokens, API keys, biometrics
- **Scope**: Which systems recognize this identity
- **Lifetime**: Certificate validity period, token expiration
- **Binding**: To public/private key pair, to session, to device
- **Verification**: Signature check, certificate chain validation
- **Revocation**: CRL (Certificate Revocation List), OCSP (Online Certificate Status Protocol)

**2. Integrity Evidence**

Proves "This data is unmodified"

- **Examples**: Cryptographic hashes, digital signatures, MACs, Merkle proofs
- **Scope**: Which data is covered (file, message, transaction)
- **Lifetime**: Unlimited (hash never expires) but signature key might
- **Binding**: To specific content (collision-resistant hash)
- **Verification**: Recompute hash, verify signature
- **Revocation**: Signing key revocation

**3. Authorization Evidence**

Proves "Principal P is allowed to do action A"

- **Examples**: ACLs, OAuth scopes, RBAC roles, policy evaluation results
- **Scope**: Which resources and actions are authorized
- **Lifetime**: Until policy changes or session expires
- **Binding**: To specific principal and resource
- **Verification**: Policy engine evaluation
- **Revocation**: Policy update, session termination

**4. Audit Evidence**

Proves "Action A occurred at time T"

- **Examples**: Logs, traces, blockchain records
- **Scope**: Which actions are recorded
- **Lifetime**: Retention period (often years for compliance)
- **Binding**: To principal, resource, timestamp
- **Verification**: Log integrity (hash chain), immutable storage
- **Revocation**: Cannot be revoked (immutable record)

**5. Attestation Evidence**

Proves "System S is in state X"

- **Examples**: TPM attestation, SGX remote attestation, SBOM signatures
- **Scope**: Which system components are attested
- **Lifetime**: Until system state changes
- **Binding**: To hardware (TPM) or enclave (SGX)
- **Verification**: Attestation service validates measurement
- **Revocation**: Measurement change (patch, compromise)

### The Security Invariant Hierarchy

Security invariants build on the fundamental invariants from earlier chapters.

**Fundamental Security Invariants**:

**1. AUTHENTICITY**: Actions originate from identified, authorized principals

- **Threat**: Impersonation, credential theft, privilege escalation
- **Protection**: Strong authentication, MFA, certificate-based identity
- **Evidence**: Identity tokens, certificates, signatures
- **Degradation**: Deny access if identity cannot be verified
- **Repair**: Re-authenticate, rotate credentials

**2. INTEGRITY**: Data is unmodified from its authorized source

- **Threat**: Tampering, injection, man-in-the-middle
- **Protection**: Digital signatures, MACs, hash verification
- **Evidence**: Signatures, hashes, Merkle proofs
- **Degradation**: Reject modified data
- **Repair**: Re-fetch from source, restore from backup

**3. CONFIDENTIALITY**: Information is visible only to authorized principals

- **Threat**: Eavesdropping, unauthorized access, data leaks
- **Protection**: Encryption (at rest, in transit, in use), access control
- **Evidence**: Encrypted blobs, access logs, decryption authorization
- **Degradation**: Deny access to sensitive data
- **Repair**: Rotate keys if compromised, revoke access

**Derived Security Invariants**:

**4. AUTHORIZATION**: Actions are permitted by policy

- **Built from**: Authenticity (who) + policy (what)
- **Threat**: Privilege escalation, confused deputy
- **Protection**: RBAC, ABAC, policy engines
- **Evidence**: Authorization decision logs
- **Degradation**: Default deny, least privilege

**5. NON-REPUDIATION**: Actions are attributable and provable

- **Built from**: Authenticity + Integrity (signatures bind identity to action)
- **Threat**: Denial of action, forged attribution
- **Protection**: Digital signatures, audit logs, blockchain
- **Evidence**: Signed statements, immutable logs
- **Degradation**: Cannot degrade (requirement is proof)

**6. AVAILABILITY** (under attack): Legitimate requests are served despite adversarial load

- **Built from**: Rate limiting + prioritization + Byzantine tolerance
- **Threat**: DDoS, resource exhaustion, censorship
- **Protection**: Rate limiting, CAPTCHA, Byzantine consensus
- **Evidence**: Request quotas, authenticated clients
- **Degradation**: Prioritize authenticated/paying users, shed load

**Composite Security Invariants**:

**7. ISOLATION**: Actions in one domain don't affect another

- **Built from**: Confidentiality + Integrity + Authorization
- **Threat**: Container escape, side channels, noisy neighbors
- **Protection**: Namespace isolation, resource limits, sandboxing
- **Evidence**: Resource accounting, access logs
- **Degradation**: Kill misbehaving processes

**8. FRESHNESS** (under attack): Data is recent and attacker cannot replay old data

- **Built from**: Integrity + Temporal ordering
- **Threat**: Replay attacks, stale data injection
- **Protection**: Nonces, timestamps, sequence numbers
- **Evidence**: Signed timestamps, monotonic counters
- **Degradation**: Reject data outside freshness window

### The Security Mode Matrix

Security operates in modes just like other system properties. The key difference: **adversarial conditions** trigger transitions.

#### Target Mode (Normal Security Posture)

**Preserved Invariants**:

- All five fundamental invariants (Authenticity, Integrity, Confidentiality, Authorization, Non-repudiation)
- All requests authenticated and authorized
- All data encrypted at rest and in transit
- All actions audited

**Required Evidence**:

- Valid identity tokens (unexpired, properly signed)
- mTLS certificates with valid chains
- Authorization policy evaluations
- Audit logs with integrity protection

**Allowed Operations**:

- All operations, subject to authorization
- Evidence lifetime: normal (e.g., 24h for certs, 1h for tokens)

**User-Visible Contract**:

"All security guarantees are in effect. Your data is protected and access is controlled."

**Entry Condition**: All security systems healthy, no active threats detected

**Exit Trigger**: Threat detected, evidence expired, verification failed

#### Degraded Mode (Under Attack or Partial Failure)

**Preserved Invariants** (Floor):

- Authenticity (no unauthenticated access)
- Integrity (reject tampered data)
- Confidentiality of critical data (other data may be unavailable)
- Non-repudiation (continue auditing)

**Relaxed Invariants**:

- Availability may be reduced (rate limiting, CAPTCHA)
- Some features may be disabled
- Latency may increase (additional verification)

**Required Evidence**:

- Stronger authentication (additional MFA factor)
- Fresh evidence only (shorter lifetimes)
- Additional verification (anomaly detection)

**Allowed Operations**:

- Critical operations only (read-only, essential writes)
- Enhanced monitoring and logging
- Limited rate for new connections

**User-Visible Contract**:

"We've detected unusual activity. Security is enhanced, and some features are temporarily limited."

**Entry Trigger**:

- Threat detected (DDoS, brute force, suspicious patterns)
- Partial system failure (some auth nodes down)
- Evidence approaching expiration

**Exit Trigger**: Threat mitigated, systems recovered, evidence renewed

#### Floor Mode (Confirmed Breach or Critical Failure)

**Preserved Invariants** (Absolute Minimum):

- Authenticity (deny all access except recovery team)
- Integrity (reject all data writes)
- Non-repudiation (log all attempts)

**Suspended Invariants**:

- Availability (system may be unavailable to users)
- Confidentiality (focus is on preventing further damage)

**Required Evidence**:

- Out-of-band authentication (hardware tokens, phone calls)
- Multi-party authorization (2+ admins to act)
- Real-time monitoring (no batched logs)

**Allowed Operations**:

- Read-only access for investigation
- No writes except by recovery team
- Forensic data collection
- Revocation of all credentials

**User-Visible Contract**:

"Security incident in progress. Service is unavailable while we investigate and recover."

**Entry Trigger**:

- Confirmed breach
- Critical evidence failure (CA compromised, master keys leaked)
- Multiple simultaneous attacks

**Exit Trigger**: Incident resolved, systems verified clean, new evidence generated

#### Recovery Mode (Post-Incident)

**Preserved Invariants**:

- All fundamental invariants being re-established
- Stronger verification than target mode
- Complete audit trail of recovery

**Required Evidence**:

- New credentials (all old ones revoked)
- System integrity verification (clean install, verified hashes)
- Provenance of all code and data (SBOM, attestation)

**Allowed Operations**:

- Gradual re-enabling of features
- Enhanced monitoring during ramp-up
- Controlled rollback capability

**User-Visible Contract**:

"Incident resolved. Services are returning with enhanced security. We're monitoring closely."

**Entry Trigger**: Floor mode complete, threat eliminated

**Exit Trigger**: All systems verified, full operation restored, monitoring shows normal patterns

### Security Context Capsule

Just as we propagate guarantees through context capsules, we propagate security context:

```python
class SecurityCapsule:
    def __init__(self):
        # Core fields (always present)
        self.invariant = None        # Which security property
        self.evidence = None         # Proof of the property
        self.boundary = None         # Valid scope/domain
        self.mode = None            # Security mode (Target/Degraded/Floor/Recovery)
        self.fallback = None        # What to do if verification fails

        # Optional fields
        self.identity = None        # Principal identity
        self.authorization = None   # Authorization decision
        self.trace = None          # Request trace ID
        self.risk_score = None     # Calculated risk
        self.obligations = None    # What recipient must verify
```

**Example: API Request**

```python
# Client generates capsule
capsule = SecurityCapsule(
    invariant='AUTHENTICITY',
    evidence={
        'type': 'JWT',
        'token': 'eyJhbG...',
        'signature': 'verified',
        'issued_at': '2023-10-01T12:00:00Z',
        'expires_at': '2023-10-01T13:00:00Z'
    },
    boundary={
        'scope': 'api.example.com',
        'path': '/api/orders/*'
    },
    mode='TARGET',
    fallback='DENY',
    identity={
        'principal': 'user@example.com',
        'tenant': 'tenant-42',
        'roles': ['user', 'customer']
    },
    trace='req-abc123'
)

# API gateway verifies capsule
def verify_capsule(capsule):
    # Check evidence is valid
    if not verify_jwt(capsule.evidence['token']):
        return capsule.fallback  # DENY

    # Check evidence hasn't expired
    if time.now() > capsule.evidence['expires_at']:
        return 'EXPIRED'

    # Check scope matches request
    if not request.path.startswith(capsule.boundary['path']):
        return 'OUT_OF_SCOPE'

    # Check mode allows operation
    if capsule.mode == 'FLOOR':
        return 'DEGRADED'  # Only critical ops allowed

    return 'ALLOW'

# Downstream service receives capsule (possibly enriched)
capsule_enriched = SecurityCapsule(
    invariant='AUTHORIZATION',
    evidence={
        'type': 'PolicyDecision',
        'policy': 'orders-read-policy',
        'decision': 'ALLOW',
        'evaluated_at': '2023-10-01T12:00:05Z'
    },
    boundary={
        'scope': 'orders-service',
        'resource': 'orders/12345'
    },
    mode='TARGET',
    fallback='DENY',
    identity=capsule.identity,  # Carried forward
    trace=capsule.trace,        # Carried forward
    obligations={
        'verify_tenant': True,   # Must check tenant matches
        'log_access': True       # Must log this access
    }
)
```

**Capsule operations at boundaries**:

**1. Verify**: Check evidence is valid, unexpired, and sufficient

**2. Enrich**: Add authorization decision, risk score

**3. Restrict**: Narrow scope as request goes deeper

**4. Propagate**: Carry identity and trace through call chain

**5. Degrade**: Apply fallback if verification fails

### Advanced Security Mechanisms

#### Secure Multi-Party Computation (MPC)

Multiple parties jointly compute a function without revealing their inputs to each other.

```python
class SecureMPC:
    """
    Example: Secure salary comparison
    Alice and Bob want to know who earns more without revealing salaries
    """
    def __init__(self, parties):
        self.parties = parties

    def secret_share(self, secret, threshold):
        """
        Shamir's Secret Sharing: Split secret into shares
        Any `threshold` shares can reconstruct, fewer cannot
        """
        # Choose random polynomial of degree (threshold - 1)
        # The constant term is the secret
        polynomial = [secret] + [random.randint(0, PRIME) for _ in range(threshold - 1)]

        # Evaluate polynomial at different points for each party
        shares = []
        for i, party in enumerate(self.parties):
            x = i + 1
            y = self.evaluate_polynomial(polynomial, x)
            shares.append((x, y))

        return shares

    def secure_comparison(self, alice_value, bob_value):
        """
        Compare without revealing values using Yao's Garbled Circuits
        """
        # Create a circuit for comparison (alice_value > bob_value)
        circuit = self.create_comparison_circuit()

        # Alice garbles the circuit
        garbled_circuit = self.garble_circuit(circuit)

        # Alice provides input labels for her value (without revealing value)
        alice_labels = self.get_input_labels(garbled_circuit, alice_value)

        # Bob uses oblivious transfer to get labels for his value
        bob_labels = self.oblivious_transfer(garbled_circuit, bob_value)

        # Bob evaluates the garbled circuit
        result = self.evaluate_garbled(garbled_circuit, alice_labels, bob_labels)

        # Result is boolean: True if alice_value > bob_value
        return result  # Neither party learned the other's value
```

**Use case**: Privacy-preserving analytics. Multiple hospitals compute aggregate statistics (average treatment outcome) without sharing patient data.

**Invariants**:

- **Confidentiality**: Inputs remain secret
- **Integrity**: Computation is correct
- **Availability**: Result is computable

**Evidence**: Zero-knowledge proofs that computation was done correctly without revealing inputs.

#### Homomorphic Encryption

Compute on encrypted data without decrypting.

```python
class HomomorphicEncryption:
    def __init__(self):
        self.context = self.create_paillier_context()

    def encrypt(self, plaintext):
        # Paillier encryption is additively homomorphic
        r = random.randint(1, self.context.n)
        c = (pow(self.context.g, plaintext, self.context.n_squared) *
             pow(r, self.context.n, self.context.n_squared)) % self.context.n_squared
        return c

    def add_encrypted(self, c1, c2):
        # Adding encrypted values: E(m1) * E(m2) = E(m1 + m2)
        return (c1 * c2) % self.context.n_squared

    def multiply_plain(self, ciphertext, plaintext):
        # Multiply encrypted by plaintext: E(m1)^m2 = E(m1 * m2)
        return pow(ciphertext, plaintext, self.context.n_squared)

    def private_sum(self, encrypted_values):
        # Sum encrypted values without decrypting
        result = 1  # Multiplicative identity
        for enc_val in encrypted_values:
            result = self.add_encrypted(result, enc_val)
        return result

    def private_average(self, encrypted_values):
        # Compute average without seeing individual values
        encrypted_sum = self.private_sum(encrypted_values)
        count = len(encrypted_values)
        # Divide by count (not directly supported, so multiply by 1/count)
        # In practice, return sum and count, let authorized party decrypt and divide
        return encrypted_sum, count
```

**Use case**: Cloud computing on sensitive data. Upload encrypted medical records to cloud. Cloud computes statistics for research without seeing individual records. Only researcher with decryption key sees results.

**Invariants**:

- **Confidentiality**: Data never decrypted in untrusted environment
- **Integrity**: Computations are verifiably correct
- **Availability**: Can perform useful computations despite encryption

**Limitation**: Currently practical only for simple operations (addition, multiplication). Full homomorphic encryption (arbitrary circuits) is still too slow for production.

### Production Security Operations

#### Security Monitoring and Detection

Security isn't static—it's continuous monitoring and response.

```python
class SecurityMonitor:
    def __init__(self):
        self.rules = self.load_detection_rules()
        self.ml_model = self.load_anomaly_model()
        self.baseline = self.load_behavioral_baseline()

    def analyze_events(self, events):
        threats = []

        # 1. Rule-based detection (known attack patterns)
        for event in events:
            for rule in self.rules:
                if rule.matches(event):
                    threats.append({
                        'type': 'RULE_MATCH',
                        'rule': rule.name,
                        'severity': rule.severity,
                        'event': event,
                        'confidence': 'HIGH'
                    })

        # 2. Anomaly detection (deviations from normal)
        features = self.extract_features(events)
        anomaly_score = self.ml_model.predict(features)

        if anomaly_score > 0.8:
            threats.append({
                'type': 'ANOMALY',
                'score': anomaly_score,
                'features': features,
                'severity': 'MEDIUM' if anomaly_score < 0.9 else 'HIGH',
                'confidence': 'MEDIUM'
            })

        # 3. Behavioral analysis (deviation from baseline)
        for principal in self.get_active_principals(events):
            behavior = self.analyze_behavior(principal, events)
            baseline = self.baseline.get(principal)

            if self.deviates_significantly(behavior, baseline):
                threats.append({
                    'type': 'BEHAVIORAL',
                    'principal': principal,
                    'deviation': self.calculate_deviation(behavior, baseline),
                    'severity': 'MEDIUM',
                    'confidence': 'MEDIUM'
                })

        # 4. Correlation (multiple weak signals → strong signal)
        correlated = self.correlate_threats(threats, events)

        return correlated

    def correlate_threats(self, threats, events):
        # Example: Multiple failed logins + successful login + data access
        # = likely compromised account

        correlations = []

        # Group by principal
        by_principal = defaultdict(list)
        for threat in threats:
            principal = threat.get('principal') or threat.get('event', {}).get('principal')
            if principal:
                by_principal[principal].append(threat)

        # Look for patterns
        for principal, principal_threats in by_principal.items():
            # Pattern: Brute force followed by access
            failed_logins = [t for t in principal_threats if 'failed_login' in str(t)]
            successful_access = [t for t in principal_threats if 'access' in str(t)]

            if len(failed_logins) >= 5 and len(successful_access) >= 1:
                correlations.append({
                    'type': 'COMPROMISED_ACCOUNT',
                    'principal': principal,
                    'evidence': failed_logins + successful_access,
                    'severity': 'CRITICAL',
                    'confidence': 'HIGH'
                })

        return correlations
```

**Detection layers**:

1. **Signature-based**: Known attack patterns (SQL injection, path traversal)
2. **Anomaly-based**: Statistical deviations (10x increase in API calls)
3. **Behavioral**: Changes in user/system behavior (accessing data never touched before)
4. **Correlation**: Multiple weak signals form strong signal

#### Incident Response

When a threat is detected, incident response activates.

```python
class IncidentResponse:
    def __init__(self):
        self.playbooks = self.load_playbooks()
        self.severity_levels = {
            'CRITICAL': {'sla': 15, 'escalation': ['ciso', 'cto', 'ceo']},
            'HIGH': {'sla': 60, 'escalation': ['security-team', 'oncall']},
            'MEDIUM': {'sla': 240, 'escalation': ['security-team']},
            'LOW': {'sla': 1440, 'escalation': []}
        }

    def respond(self, incident):
        # 1. Classify severity and type
        classification = self.classify(incident)
        severity = classification['severity']
        incident_type = classification['type']

        # 2. Start incident tracking
        incident_id = self.create_incident_record(incident, classification)

        # 3. Escalate based on severity
        self.escalate(incident_id, severity)

        # 4. Execute playbook
        playbook = self.playbooks[incident_type]

        for step in playbook.steps:
            result = self.execute_step(step, incident)
            self.log_step_result(incident_id, step, result)

            # Check if step requires human approval
            if step.requires_approval:
                approval = self.wait_for_approval(incident_id, step)
                if not approval:
                    self.log_step_skipped(incident_id, step)
                    continue

        # 5. Post-incident activities
        self.create_forensic_timeline(incident_id)
        self.preserve_evidence(incident_id)
        self.schedule_postmortem(incident_id)

        return incident_id

    def execute_step(self, step, incident):
        if step.type == 'CONTAIN':
            # Isolate affected systems
            return self.contain_threat(step.params, incident)

        elif step.type == 'ERADICATE':
            # Remove malicious artifacts
            return self.eradicate_threat(step.params, incident)

        elif step.type == 'RECOVER':
            # Restore service
            return self.recover_systems(step.params, incident)

        elif step.type == 'NOTIFY':
            # Inform stakeholders
            return self.notify_stakeholders(step.params, incident)

    def contain_threat(self, params, incident):
        """
        Containment: Stop the breach from spreading
        """
        actions = []

        # Isolate affected systems (network segmentation)
        for system in incident['affected_systems']:
            self.apply_network_isolation(system)
            actions.append(f"Isolated {system}")

        # Revoke compromised credentials
        for principal in incident['compromised_principals']:
            self.revoke_all_sessions(principal)
            self.revoke_credentials(principal)
            actions.append(f"Revoked credentials for {principal}")

        # Enable enhanced monitoring
        self.enable_enhanced_logging(incident['scope'])
        actions.append("Enabled enhanced logging")

        # Transition to floor mode
        for service in incident['affected_services']:
            self.set_security_mode(service, 'FLOOR')
            actions.append(f"Set {service} to FLOOR mode")

        return {'actions': actions, 'status': 'CONTAINED'}
```

**Incident response phases** (NIST framework):

1. **Preparation**: Playbooks, tools, training (before incident)
2. **Detection & Analysis**: Identify and understand the incident
3. **Containment**: Stop the damage from spreading
4. **Eradication**: Remove the threat completely
5. **Recovery**: Restore normal operations
6. **Post-Incident**: Learn and improve

**Evidence during incident**:

- **Detection evidence**: Logs, alerts that triggered response
- **Forensic evidence**: Artifacts from compromised systems (malware, logs, memory dumps)
- **Timeline evidence**: Sequence of events reconstructed from logs
- **Remediation evidence**: Actions taken and their results

### Case Studies: Learning from Breaches

#### The Kubernetes Privilege Escalation (CVE-2018-1002105)

**The Vulnerability**:

Kubernetes API server has a feature for "exec" and "port-forward" operations. These use an HTTP upgrade to establish a WebSocket connection. The vulnerability: after the upgrade, the API server stopped authenticating requests. An attacker with minimal permissions could send crafted requests to access any resource with cluster-admin privileges.

**Invariant Violated**: **AUTHORIZATION** — requests were executed without verifying the principal had permission.

**Evidence Failure**: After protocol upgrade, the authentication evidence (token) was not re-verified for subsequent requests.

**Impact**: All Kubernetes clusters affected. Attacker with any credentials could become admin.

**Fix**:

- Re-verify authentication after protocol upgrade
- Enforce authorization checks on all requests, regardless of connection type

**Lesson**: **Every boundary must verify evidence.** Protocol transitions are boundaries.

#### The Capital One Breach (2019)

**The Attack**:

Capital One used AWS. They had a WAF (Web Application Firewall) with overly broad IAM permissions. An attacker exploited SSRF (Server-Side Request Forgery) in the WAF to access the EC2 instance metadata service, which returned IAM credentials for the WAF's role. Those credentials had permission to list and read S3 buckets. 100M credit applications stolen.

**Invariant Violated**: **LEAST PRIVILEGE** and **ISOLATION**

**Evidence Failure**:

- WAF had excessive permissions (could read all S3 buckets)
- IMDSv1 provided credentials without verifying the request originated from the instance (not a forwarded request)

**Impact**: $80M fine from regulators, massive reputational damage.

**Fix**:

- Least privilege: WAF should only access specific S3 buckets it needs
- IMDSv2: Requires a session token obtained via a PUT request (can't be forwarded via SSRF)
- Network segmentation: WAF shouldn't have unrestricted network access to metadata service

**Lesson**: **Principle of least privilege.** Every component should have the minimum permissions to do its job, and no more.

#### The Okta Breach (2022)

**The Attack**:

A third-party contractor working for Okta had their laptop compromised. The laptop had an active session to Okta's internal support tools. The attacker used the session to access customer support tools that could reset MFA for customer tenants. The compromise went undetected for months.

**Invariant Violated**: **AUTHENTICITY** (contractor's access trusted as internal employee)

**Evidence Failure**:

- Long-lived session (evidence didn't expire quickly)
- No continuous verification (session was trusted without re-checking)
- No isolation between contractor and employee access

**Impact**: Access to customer tenant administration for hundreds of customers.

**Fix**:

- Short-lived sessions for high-privilege tools
- Continuous verification (re-authenticate frequently)
- Separate access tiers (contractors get restricted access)
- Enhanced monitoring (detect unusual access patterns)

**Lesson**: **Zero Trust.** Don't trust insiders. Verify continuously. Assume breach.

#### The LastPass Incidents (2022-2023)

**The Sequence**:

1. August 2022: Attacker compromised a DevOps engineer's home computer
2. Attacker accessed LastPass development environment via the engineer's credentials
3. Attacker stole source code and proprietary technical information
4. November 2022: Using knowledge from source code, attacker targeted another employee
5. December 2022: Attacker gained access to cloud storage containing encrypted customer vault backups
6. Backups included encrypted vaults + metadata (URLs, folder names)

**Invariants Violated**:

- **AUTHENTICITY**: Compromised employee credentials
- **CONFIDENTIALITY**: Vault backups accessed
- **ISOLATION**: Development environment compromise led to production access

**Evidence Failure**:

- Employee credentials were long-lived and sufficient for broad access
- No detection of unusual access patterns
- Backups were accessible with single set of credentials (no multi-party authorization)

**Impact**:

- Attackers can brute-force weak master passwords offline
- Metadata leaked (which sites users have accounts for)
- Trust in password manager severely damaged

**Fix** (industry-wide learnings):

- Defense in depth: Compromise of one system shouldn't lead to crown jewels
- Encrypted backups should require multiple keys (split key custody)
- Anomaly detection on access to critical data
- Assume employees can be compromised (Zero Trust)

**Lesson**: **Defense in depth.** One compromised component should not lead to complete breach.

### Compliance and Regulatory Frameworks

Security isn't just about preventing breaches—it's about demonstrating compliance with regulations and standards.

#### Common Frameworks

**SOC 2 (Service Organization Control 2)**:

Trust Services Criteria:

- **Security (CC6)**: Protection against unauthorized access
- **Availability (CC7)**: System is available for operation and use
- **Confidentiality (CC8)**: Confidential information is protected
- **Privacy (CC9)**: Personal information is collected, used, retained, and disposed properly

**ISO 27001**:

Information Security Management System (ISMS) with 114 controls across 14 domains:

- Access control, cryptography, physical security, operations security, communications security, etc.

**GDPR (General Data Protection Regulation)**:

EU regulation for data privacy:

- Right to be forgotten (data deletion)
- Data portability
- Consent management
- Breach notification (72 hours)

**HIPAA (Health Insurance Portability and Accountability Act)**:

US healthcare data protection:

- Administrative safeguards (policies, training)
- Physical safeguards (facility access)
- Technical safeguards (encryption, access control)

#### Mapping Security to Compliance

```python
class ComplianceMapper:
    def __init__(self):
        self.frameworks = {
            'SOC2': {
                'CC6.1': 'Logical access controls prevent unauthorized access',
                'CC6.2': 'Authentication mechanisms verify identity',
                'CC6.3': 'Network segmentation isolates sensitive data',
                'CC6.6': 'Encryption protects data at rest and in transit',
                'CC7.2': 'System availability is monitored and maintained'
            },
            'ISO27001': {
                'A.9': 'Access control',
                'A.10': 'Cryptography',
                'A.12': 'Operations security',
                'A.13': 'Communications security',
                'A.14': 'System acquisition, development, and maintenance'
            },
            'GDPR': {
                'Article 25': 'Data protection by design and by default',
                'Article 32': 'Security of processing',
                'Article 33': 'Breach notification'
            }
        }

    def assess_compliance(self, security_controls):
        """
        Map implemented controls to framework requirements
        """
        compliance_status = {}

        for framework, requirements in self.frameworks.items():
            compliance_status[framework] = {}

            for req_id, req_desc in requirements.items():
                # Find controls that satisfy this requirement
                satisfying_controls = [
                    control for control in security_controls
                    if self.control_satisfies(control, req_desc)
                ]

                compliance_status[framework][req_id] = {
                    'requirement': req_desc,
                    'status': 'MET' if satisfying_controls else 'GAP',
                    'controls': satisfying_controls
                }

        return compliance_status

    def generate_evidence(self, control):
        """
        Generate evidence for auditors
        """
        evidence = {
            'control': control.name,
            'description': control.description,
            'artifacts': []
        }

        # Configuration evidence
        if control.type == 'technical':
            evidence['artifacts'].append({
                'type': 'configuration',
                'data': self.export_configuration(control)
            })

        # Log evidence
        evidence['artifacts'].append({
            'type': 'logs',
            'sample': self.get_log_sample(control, days=30)
        })

        # Test evidence
        evidence['artifacts'].append({
            'type': 'test_results',
            'data': self.run_control_test(control)
        })

        return evidence
```

**Key insight**: Compliance requires **evidence of controls**. Auditors need to see:

- **Configuration**: How the control is implemented
- **Logs**: Evidence it's operating continuously
- **Tests**: Proof it works as intended

This maps directly to our security evidence model.

## Synthesis: Security as Invariant Preservation

### The Security Mindset: Think Like an Attacker

To secure a system, you must think like an attacker:

**1. What's the weakest link?**

Attackers find the easiest path. You must identify it first.

- Is it a forgotten admin panel?
- An over-permissioned service account?
- A third-party dependency with known CVEs?

**2. What assumptions are made?**

Every assumption is a potential vulnerability.

- "Users will use strong passwords" (they won't)
- "Internal network is trusted" (it's not)
- "Certificates will be validated" (check for bugs)

**3. What's the blast radius?**

If one component is compromised, what can the attacker reach?

- Can they pivot to other systems?
- Can they escalate privileges?
- Can they persist undetected?

**4. What evidence remains?**

Can you detect the attack? Can you prove what happened?

- Are there audit logs?
- Can logs be tampered with?
- Can you reconstruct the timeline?

### Design Principles for Secure Distributed Systems

**1. Defense in Depth**

Multiple layers of security. Compromise of one layer doesn't lead to total breach.

- Network security (firewall, segmentation)
- Application security (input validation, CSRF protection)
- Data security (encryption, access control)
- Identity security (MFA, least privilege)

**2. Least Privilege**

Minimum necessary access for minimum necessary time.

- Services get scoped credentials (not admin)
- Tokens have short lifetimes (1 hour, not 1 year)
- Permissions are specific (read bucket X, not read all buckets)

**3. Fail Secure**

When things go wrong, default to safe state.

- Can't verify identity? Deny access.
- Can't decrypt data? Don't proceed.
- Can't reach authorization service? Default deny or degrade to read-only.

**4. Complete Mediation**

Check authorization on **every** request, not just the first.

- Don't cache authorization decisions indefinitely
- Re-verify when context changes (permissions revoked, user moved tenants)

**5. Open Design**

Security should not rely on obscurity.

- Publish your security architecture
- Use standard, vetted cryptography
- Assume attackers know your implementation

**6. Separation of Privilege**

Require multiple conditions or parties for sensitive actions.

- Deleting data requires both user request and admin approval
- Accessing production requires MFA + VPN + time-based access
- Deploying code requires code review + CI tests + manual approval

**7. Least Common Mechanism**

Minimize shared resources that could be abused.

- Multi-tenant systems: isolate tenant data (don't share tables)
- Shared caches: prevent one tenant from evicting another's data
- Shared compute: resource limits prevent DoS

**8. Psychological Acceptability**

Security must be usable, or it will be circumvented.

- MFA should be convenient (push notifications, not typing codes)
- Key rotation should be automatic (not manual)
- Monitoring should have low false positives (or it will be ignored)

### The Future of Distributed Security

#### Emerging Threats

**1. Quantum Computing**

Current cryptography (RSA, ECC) will be broken by quantum computers. Estimated 10-20 years.

**Threat**: Attackers can "harvest now, decrypt later"—collect encrypted data today, decrypt when quantum computers exist.

**Response**: Post-quantum cryptography (lattice-based, hash-based algorithms). NIST is standardizing these.

**2. AI-Powered Attacks**

Machine learning can:

- Generate convincing phishing emails (GPT models)
- Find vulnerabilities in code (automated fuzzing)
- Bypass CAPTCHAs (image recognition)
- Mimic user behavior (evade anomaly detection)

**Response**: AI-powered defense (automated threat hunting, behavioral analysis)

**3. IoT Proliferation**

Billions of devices with weak security:

- Default passwords
- No update mechanism
- Limited compute for cryptography

**Threat**: Massive botnets, widespread surveillance

**Response**: Secure by default, automatic updates, hardware security (TPM)

**4. Supply Chain Complexity**

Modern software has thousands of dependencies. Each is a potential vector.

**Threat**: Compromised dependencies (event-stream npm package, SolarWinds)

**Response**: SBOM, provenance tracking, continuous verification

**5. Deepfake Authentication**

AI-generated video and audio can impersonate anyone.

**Threat**: Bypass voice/video authentication, manipulate executives

**Response**: Liveness detection, multi-factor authentication, cryptographic identity

#### Emerging Solutions

**1. Confidential Computing**

Hardware-enforced isolation (Intel SGX, AMD SEV, ARM TrustZone):

- Data encrypted even from OS and hypervisor
- Attestation proves code is running in secure enclave

**Use case**: Multi-party computation on sensitive data (healthcare research, financial analysis)

**2. Decentralized Identity**

Self-sovereign identity: users control their identity, not corporations.

- Verifiable credentials (cryptographically signed by issuers)
- Selective disclosure (prove age > 18 without revealing exact age)
- No central authority that can be compromised

**3. Zero-Knowledge Proofs**

Prove knowledge of something without revealing it.

- Prove you have enough balance without revealing amount
- Prove compliance with regulation without revealing data
- Prove you computed correctly without revealing inputs

**Use case**: Privacy-preserving authentication, private transactions

**4. Blockchain for Integrity**

Immutable ledger for audit logs, supply chain tracking.

- Tamper-evident (changing history requires re-mining all subsequent blocks)
- Decentralized (no single point of failure)
- Transparent (all participants can verify)

**Use case**: Audit logs, SBOM provenance, certificate transparency

**5. AI Defense Systems**

Machine learning for:

- Automated threat hunting (find anomalies in petabytes of logs)
- Behavioral analysis (detect account compromise)
- Vulnerability discovery (find bugs before attackers)

**Challenge**: Adversarial ML (attackers poison training data or evade detection)

## Exercises

### Conceptual

**1. Design Zero Trust Architecture**

For an e-commerce application with frontend, API gateway, order service, payment service, and database:

- What identities exist?
- What evidence does each component generate?
- What boundaries require verification?
- How do you handle evidence expiration?
- What are the degraded modes?

**2. Plan Key Rotation Strategy**

Design a key rotation strategy for:

- TLS certificates (mTLS between services)
- Database encryption keys
- JWT signing keys

For each:

- What is the rotation frequency?
- How do you avoid downtime during rotation?
- How do you handle old data encrypted with old keys?

**3. Create Threat Model**

For a distributed file storage system:

- What are the security invariants?
- What are the attack surfaces?
- What evidence is needed at each boundary?
- How do you degrade if evidence is missing?

**4. Design RBAC System**

For a multi-tenant SaaS application:

- What roles exist (admin, user, billing, support)?
- What resources exist (tenants, users, data, configurations)?
- What actions are possible (read, write, delete, admin)?
- How do you enforce authorization at boundaries?

**5. Plan Incident Response**

For a detected compromise of a service account:

- What is the containment strategy?
- What evidence do you preserve?
- How do you eradicate the threat?
- How do you recover?

### Implementation

**1. Implement mTLS**

Create a service mesh sidecar that:

- Terminates mTLS connections
- Verifies certificate chains
- Extracts identity from certificates
- Enforces authorization policies

**2. Build JWT Validation**

Implement a JWT middleware that:

- Verifies signature (RS256)
- Checks expiration
- Validates issuer and audience claims
- Extracts roles and scopes
- Enforces RBAC based on scopes

**3. Create HMAC Signing**

Implement request signing:

- Client signs requests with HMAC-SHA256
- Server verifies signatures
- Include timestamp to prevent replay
- Use nonce for idempotence

**4. Implement Rate Limiting**

Build a distributed rate limiter:

- Token bucket algorithm
- Distributed state (Redis)
- Per-principal and per-IP limits
- Degraded mode (stricter limits during DDoS)

**5. Build Audit Logging**

Implement tamper-evident audit logs:

- Hash chain (each log entry includes hash of previous)
- Periodic checkpoints to immutable storage
- Verification tool to detect tampering

### Production Analysis

**1. Security Assessment**

Assess a production system:

- What are the authentication mechanisms?
- Where are the trust boundaries?
- Is evidence verified at every boundary?
- What happens when evidence expires?
- Are there degraded modes?

**2. Penetration Testing**

Conduct authorized testing:

- Can you bypass authentication?
- Can you escalate privileges?
- Can you access other tenants' data?
- Can you modify audit logs?

**3. Compliance Audit**

Audit against a framework (SOC2, ISO27001):

- What controls are implemented?
- What evidence exists for each control?
- What gaps exist?
- What is the remediation plan?

**4. Incident Simulation**

Run a tabletop exercise:

- Simulate a breach (e.g., compromised credentials)
- Execute incident response playbook
- Identify gaps in playbook
- Update and improve

**5. Supply Chain Review**

Review dependencies:

- Generate SBOM
- Check for known vulnerabilities (CVE database)
- Verify signatures on packages
- Assess update strategy

## Key Takeaways

**1. Security is Invariant Preservation Under Adversarial Conditions**

Security invariants (authenticity, integrity, confidentiality) are preserved through evidence generation, verification at boundaries, and graceful degradation when evidence is missing or expired.

**2. Zero Trust is the New Perimeter**

Traditional perimeter security fails in distributed systems. Zero Trust means verify every request, at every boundary, continuously.

**3. Encryption Everywhere is Table Stakes**

Data must be protected at rest, in transit, and in use. Encryption is no longer optional—it's fundamental.

**4. Supply Chain is the New Attack Vector**

Attackers target the weakest link: build systems, dependencies, third-party services. SBOM and provenance tracking are essential.

**5. Detection is as Important as Prevention**

Perfect prevention is impossible. Monitoring, anomaly detection, and incident response are critical.

**6. Incident Response Must Be Rehearsed**

Playbooks and tabletop exercises prepare teams for real incidents. Under pressure, people follow practiced procedures.

**7. Compliance is Necessary But Not Sufficient**

Meeting SOC2 or ISO27001 doesn't mean you're secure—it means you've documented your controls. Continuous verification is essential.

**8. Security is Evidence Lifecycle Management**

Generate evidence, propagate it, verify it at boundaries, use it for decisions, expire it, and renew or revoke it. This unifying model applies to all security mechanisms.

## Further Reading

**Foundational**:

- *Security Engineering* by Ross Anderson
- *The Tangled Web* by Michal Zalewski
- *Cryptography Engineering* by Ferguson, Schneier, Kohno

**Frameworks and Standards**:

- NIST Cybersecurity Framework
- NIST Zero Trust Architecture (SP 800-207)
- OWASP Top 10
- CIS Controls

**Distributed Systems Security**:

- *Site Reliability Engineering* (Google), Security chapter
- *Building Secure and Reliable Systems* (Google)
- *Byzantine Fault Tolerance: Theory and Practice*

**Supply Chain**:

- SLSA Framework documentation
- SBOM (CycloneDX, SPDX) specifications
- in-toto attestation framework

**Compliance**:

- SOC 2 Trust Services Criteria
- ISO/IEC 27001:2013
- GDPR official text
- HIPAA Security Rule

**Advanced Topics**:

- *A Graduate Course in Applied Cryptography* by Boneh and Shoup
- *Secure Multi-Party Computation* surveys
- *Zero-Knowledge Proofs* (SNARK, STARK) research

---

**In essence**: Security in distributed systems is preserving authenticity, integrity, and confidentiality invariants by generating evidence, verifying it at every boundary, and degrading gracefully when evidence is insufficient—all while assuming adversaries actively try to violate your assumptions. Zero Trust architecture, encryption everywhere, Byzantine fault tolerance, and supply chain security are the mechanisms that enable this evidence-based security model at scale.
