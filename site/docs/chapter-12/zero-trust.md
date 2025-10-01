# Zero Trust Architecture: Never Trust, Always Verify

## Introduction: The Perimeter Died in 2015

At 3:42 PM on December 9, 2020, a nation-state adversary deployed malicious code into the SolarWinds Orion software update mechanism. Within hours, that update was digitally signed, packaged, and automatically deployed to 18,000 customers—including Fortune 500 companies, US federal agencies, and critical infrastructure operators.

The attacker didn't breach the perimeter through a firewall vulnerability or a stolen VPN credential. They **became the perimeter**. They operated from inside SolarWinds' build system, with legitimate credentials, passing all security checks, for months.

Traditional network security operates on a simple principle: **hard shell, soft interior**. Build a strong perimeter (firewalls, VPNs, network segmentation), verify identity at entry, then trust everything inside. Once you're in, you're trusted.

This model is dead.

**Zero trust** operates on the opposite principle: **never trust, always verify**. Every request, from every user, from every device, to every resource, is authenticated, authorized, and encrypted—regardless of network location. There is no "inside" and "outside." There is only "verified right now" and "not verified right now."

### Why Zero Trust Is the Default for Modern Systems

The perimeter model fails in distributed systems because:

1. **The perimeter is everywhere**: Services run across multiple clouds, edge locations, on-premise datacenters, employee devices, third-party APIs. There is no single network boundary to defend.

2. **Breaches are inevitable**: According to Verizon's 2023 Data Breach Investigations Report, the median time to compromise a network after initial access is 2 hours. The median time to detect that compromise is 21 days. Once inside, attackers move laterally with impunity.

3. **Internal threats exist**: 34% of breaches involve internal actors (Verizon DBIR 2023). Disgruntled employees, compromised credentials, supply chain attacks—trust cannot be assumed based on network position.

4. **Lateral movement is the kill chain**: The initial breach is rarely the goal. Attackers pivot, escalate privileges, and move laterally until they reach crown jewels (databases, secrets, admin consoles). Perimeter security does nothing to prevent this.

**Before zero trust**: "You're connected to the corporate VPN, so you can access the production database."
**After zero trust**: "You're connected to the VPN, your device is verified compliant, your identity is authenticated via MFA, you have explicit authorization for this database query, and the connection is encrypted with mutual TLS. Now you can access the database."

### The Core Principles

Zero trust is not a product or technology—it's an architectural philosophy built on five principles:

1. **Verify explicitly**: Authenticate and authorize based on all available data points (identity, device health, location, time, resource sensitivity). Never rely solely on network position.

2. **Use least privilege access**: Grant minimum permissions necessary, just-in-time and just-enough-access. Expire credentials frequently. Default deny.

3. **Assume breach**: Design assuming attackers are already inside. Minimize blast radius, segment access, encrypt everything, inspect all traffic.

4. **Verify continuously**: Security is not binary (authenticated or not). It's continuous. Re-verify identity, device health, and authorization on every request.

5. **Monitor everything**: Every authentication, authorization, and access attempt generates audit logs. Anomaly detection and threat intelligence identify compromised credentials or insider threats.

## Part 1: Identity as the Perimeter

### The Fundamental Shift

In zero trust, **identity replaces network location** as the primary security boundary:

**Traditional security**: "Are you on the trusted network?" → Trust
**Zero trust**: "Who are you? What device? What are you trying to access? Why?" → Verify → Trust (for this request only)

This requires:
- **Strong authentication**: Multi-factor authentication (MFA), passwordless authentication, hardware security keys
- **Device verification**: Ensure devices meet security posture requirements (patched, encrypted, managed)
- **Continuous authorization**: Check permissions on every request, not just at login
- **Context-aware policies**: Consider time, location, behavior patterns, risk score

### Implementing Identity-Based Access: Production Code

Here's a production-grade identity verification system that demonstrates zero trust principles:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
import jwt
import hashlib
import hmac
import secrets
import time

class RiskLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class DevicePosture:
    """Device security posture - continuously verified"""
    device_id: str
    os_version: str
    patch_level: str
    encryption_enabled: bool
    security_agent_running: bool
    last_verified: datetime
    compliance_score: float  # 0.0 to 1.0

    def is_compliant(self) -> bool:
        """Device must meet minimum security requirements"""
        # Verification must be recent (within 5 minutes)
        if (datetime.utcnow() - self.last_verified) > timedelta(minutes=5):
            return False

        # Hard requirements
        if not self.encryption_enabled:
            return False
        if not self.security_agent_running:
            return False

        # Compliance score threshold
        return self.compliance_score >= 0.8

@dataclass
class AccessContext:
    """Context for access decision - all available signals"""
    user_id: str
    device: DevicePosture
    source_ip: str
    source_country: str
    time_of_day: int  # Hour 0-23
    resource: str
    action: str

    # Behavioral signals
    normal_access_pattern: bool
    recent_failed_attempts: int
    concurrent_sessions: int

    def calculate_risk_level(self) -> RiskLevel:
        """Risk-based access decision"""
        risk_score = 0

        # Device risk
        if not self.device.is_compliant():
            risk_score += 40
        elif self.device.compliance_score < 0.9:
            risk_score += 10

        # Behavioral risk
        if not self.normal_access_pattern:
            risk_score += 20

        if self.recent_failed_attempts > 3:
            risk_score += 30

        if self.concurrent_sessions > 5:
            risk_score += 15

        # Temporal risk (access outside normal hours)
        if self.time_of_day < 6 or self.time_of_day > 22:
            risk_score += 10

        # Geographic risk (simplified - real systems use threat intel)
        high_risk_countries = ["XX", "YY", "ZZ"]  # Placeholder
        if self.source_country in high_risk_countries:
            risk_score += 25

        # Map score to risk level
        if risk_score >= 60:
            return RiskLevel.CRITICAL
        elif risk_score >= 40:
            return RiskLevel.HIGH
        elif risk_score >= 20:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

class ZeroTrustAuthenticator:
    """
    Zero trust authentication and authorization

    Principles:
    1. Verify identity explicitly (MFA required)
    2. Verify device posture continuously
    3. Context-aware access decisions
    4. Least privilege (explicit permissions only)
    5. Time-bound credentials (short-lived tokens)
    """

    def __init__(self, secret_key: bytes):
        self.secret_key = secret_key
        self.mfa_cache: Dict[str, datetime] = {}

    def authenticate_user(
        self,
        username: str,
        password_hash: str,
        mfa_token: str,
        context: AccessContext
    ) -> Optional[str]:
        """
        Authenticate user with MFA
        Returns short-lived access token
        """
        # Step 1: Verify credentials (password hash)
        if not self._verify_password(username, password_hash):
            self._log_failed_attempt(username, context)
            return None

        # Step 2: Require MFA (time-based one-time password)
        if not self._verify_mfa(username, mfa_token):
            self._log_failed_attempt(username, context)
            return None

        # Step 3: Verify device posture
        if not context.device.is_compliant():
            self._log_failed_attempt(
                username,
                context,
                reason="device_non_compliant"
            )
            return None

        # Step 4: Calculate risk level
        risk = context.calculate_risk_level()

        # Step 5: Risk-based token expiration
        if risk == RiskLevel.CRITICAL:
            # Deny high-risk access
            self._log_failed_attempt(username, context, reason="risk_too_high")
            return None
        elif risk == RiskLevel.HIGH:
            # Very short-lived token (5 minutes)
            ttl = timedelta(minutes=5)
        elif risk == RiskLevel.MEDIUM:
            # Short-lived token (15 minutes)
            ttl = timedelta(minutes=15)
        else:
            # Standard token (1 hour, still short-lived)
            ttl = timedelta(hours=1)

        # Step 6: Generate signed token
        token = self._generate_token(username, context, ttl)

        self._log_successful_auth(username, context, risk, ttl)

        return token

    def authorize_request(
        self,
        token: str,
        resource: str,
        action: str,
        context: AccessContext
    ) -> bool:
        """
        Authorize access to resource
        Verifies token AND re-checks device posture AND checks permissions
        """
        # Step 1: Verify token signature and expiration
        claims = self._verify_token(token)
        if not claims:
            return False

        user_id = claims["sub"]

        # Step 2: Re-verify device posture (continuous verification)
        # Device health can change between authentication and authorization
        if not context.device.is_compliant():
            self._log_authorization_failure(
                user_id,
                resource,
                action,
                context,
                reason="device_compliance_changed"
            )
            return False

        # Step 3: Check explicit permissions (least privilege)
        if not self._has_permission(user_id, resource, action):
            self._log_authorization_failure(
                user_id,
                resource,
                action,
                context,
                reason="insufficient_permissions"
            )
            return False

        # Step 4: Re-calculate risk (context may have changed)
        risk = context.calculate_risk_level()
        if risk == RiskLevel.CRITICAL:
            self._log_authorization_failure(
                user_id,
                resource,
                action,
                context,
                reason="risk_elevated"
            )
            return False

        self._log_authorization_success(user_id, resource, action, context)
        return True

    def _verify_password(self, username: str, password_hash: str) -> bool:
        """Verify password hash against stored credentials"""
        # In production: query user database with rate limiting
        stored_hash = self._get_password_hash(username)
        return hmac.compare_digest(password_hash, stored_hash)

    def _verify_mfa(self, username: str, mfa_token: str) -> bool:
        """
        Verify MFA token (TOTP, WebAuthn, or SMS)
        In production: integrate with MFA provider
        """
        # Check if MFA token is valid and not replayed
        expected_token = self._generate_totp(username)

        if not hmac.compare_digest(mfa_token, expected_token):
            return False

        # Prevent token reuse
        cache_key = f"{username}:{mfa_token}"
        if cache_key in self.mfa_cache:
            return False  # Token already used

        self.mfa_cache[cache_key] = datetime.utcnow()
        self._cleanup_mfa_cache()

        return True

    def _generate_token(
        self,
        user_id: str,
        context: AccessContext,
        ttl: timedelta
    ) -> str:
        """Generate signed JWT with short expiration"""
        now = datetime.utcnow()
        expiration = now + ttl

        payload = {
            "sub": user_id,  # Subject (user ID)
            "iat": int(now.timestamp()),  # Issued at
            "exp": int(expiration.timestamp()),  # Expiration
            "device_id": context.device.device_id,
            "source_ip": context.source_ip,
            "jti": secrets.token_urlsafe(16),  # Unique token ID (for revocation)
        }

        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify token signature and expiration"""
        try:
            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={"require": ["exp", "sub", "device_id"]}
            )
            return claims
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def _has_permission(self, user_id: str, resource: str, action: str) -> bool:
        """
        Check if user has explicit permission for resource:action
        In production: query policy engine or IAM system
        """
        # This would query a policy database
        # For now, simplified implementation
        permissions = self._get_user_permissions(user_id)
        return f"{resource}:{action}" in permissions

    def _generate_totp(self, username: str) -> str:
        """Generate time-based one-time password"""
        # Simplified TOTP generation
        # In production: use PyOTP or similar library
        secret = self._get_mfa_secret(username)
        timestamp = int(time.time() // 30)  # 30-second window
        message = f"{username}:{timestamp}".encode()
        token = hmac.new(secret, message, hashlib.sha256).hexdigest()[:6]
        return token

    def _cleanup_mfa_cache(self):
        """Remove expired MFA tokens from cache"""
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        self.mfa_cache = {
            k: v for k, v in self.mfa_cache.items()
            if v > cutoff
        }

    # Placeholder methods for external systems
    def _get_password_hash(self, username: str) -> str:
        """Query user database for password hash"""
        pass

    def _get_mfa_secret(self, username: str) -> bytes:
        """Query MFA secret for user"""
        pass

    def _get_user_permissions(self, user_id: str) -> List[str]:
        """Query user permissions from IAM"""
        pass

    def _log_failed_attempt(
        self,
        username: str,
        context: AccessContext,
        reason: str = "invalid_credentials"
    ):
        """Log failed authentication attempt for threat detection"""
        pass

    def _log_successful_auth(
        self,
        username: str,
        context: AccessContext,
        risk: RiskLevel,
        ttl: timedelta
    ):
        """Log successful authentication"""
        pass

    def _log_authorization_failure(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: AccessContext,
        reason: str
    ):
        """Log authorization failure"""
        pass

    def _log_authorization_success(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: AccessContext
    ):
        """Log authorization success"""
        pass
```

### Why This Implementation Embodies Zero Trust

1. **Verify explicitly**: Checks username, password, MFA, device posture, and context signals
2. **Continuous verification**: Re-checks device posture at authorization time, not just authentication
3. **Risk-based access**: Adjusts token lifetime based on risk level
4. **Least privilege**: Checks explicit permissions for each resource:action pair
5. **Short-lived credentials**: Tokens expire in 5 minutes to 1 hour, never indefinitely
6. **Comprehensive logging**: Every auth attempt, success or failure, is logged for threat detection

### The Real-World Impact

**Google BeyondCorp**: Google eliminated their corporate VPN in 2014, moving to a zero trust model where every request—from any network—is authenticated and authorized. Result: No VPN breaches, no lateral movement attacks, and employees can work securely from anywhere.

**Cloudflare Zero Trust**: After the 2020 VPN zero-day vulnerabilities (Pulse Secure, Citrix, Fortinet), Cloudflare moved 100% of internal applications behind their Zero Trust platform. No VPN, no network perimeter, every request authenticated and encrypted.

## Part 2: Service Mesh and Mutual TLS

### The Service-to-Service Trust Problem

In microservices architectures, services communicate constantly:
- Order Service → Inventory Service
- Inventory Service → Database
- API Gateway → Authentication Service → Order Service

Traditional approach: If Service A is inside the network, it can call Service B. No verification.

**The problem**: Once an attacker compromises one service, they can impersonate any service and access any resource. This is **lateral movement**—the primary kill chain in modern breaches.

**Zero trust solution**: **Mutual TLS (mTLS)** — Every service proves its identity to every other service on every request. Both client and server verify each other's certificates.

### Service Mesh: Zero Trust for Service Communication

A **service mesh** provides zero trust infrastructure for service-to-service communication:

1. **Identity for every service**: Each service gets a cryptographic identity (X.509 certificate)
2. **mTLS everywhere**: All service communication is encrypted and mutually authenticated
3. **Authorization policies**: Define which services can call which endpoints
4. **Automatic certificate rotation**: Certificates expire every 24 hours, automatically renewed
5. **Observability**: Every request is traced, logged, and monitored

### Production Service Mesh: Istio Configuration

Here's a production-grade zero trust service mesh configuration:

```python
# Service mesh configuration (Kubernetes + Istio)
# This would be YAML in production, shown as Python for explanation

from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ServiceIdentity:
    """Cryptographic identity for a service"""
    service_name: str
    namespace: str
    certificate_ttl_hours: int = 24  # Short-lived certificates

    def spiffe_id(self) -> str:
        """
        SPIFFE ID: Secure Production Identity Framework For Everyone
        Standard format for service identity
        """
        return f"spiffe://cluster.local/ns/{self.namespace}/sa/{self.service_name}"

@dataclass
class MTLSPolicy:
    """Mutual TLS policy for service communication"""
    mode: str  # STRICT, PERMISSIVE, or DISABLED

    def to_istio_config(self) -> Dict:
        """
        Convert to Istio PeerAuthentication resource
        STRICT = mTLS required for all communication
        """
        return {
            "apiVersion": "security.istio.io/v1beta1",
            "kind": "PeerAuthentication",
            "metadata": {
                "name": "default",
                "namespace": "production"
            },
            "spec": {
                "mtls": {
                    "mode": self.mode
                }
            }
        }

@dataclass
class AuthorizationPolicy:
    """
    Zero trust authorization: explicit allow list
    Default deny - only specified services can communicate
    """
    name: str
    namespace: str
    service: str
    rules: List[Dict]

    def to_istio_config(self) -> Dict:
        """
        Convert to Istio AuthorizationPolicy resource
        Implements least privilege access
        """
        return {
            "apiVersion": "security.istio.io/v1beta1",
            "kind": "AuthorizationPolicy",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace
            },
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app": self.service
                    }
                },
                "action": "ALLOW",
                "rules": self.rules
            }
        }

# Example: Order Service can only be called by API Gateway
order_service_policy = AuthorizationPolicy(
    name="order-service-authz",
    namespace="production",
    service="order-service",
    rules=[
        {
            # Only API Gateway can call Order Service
            "from": [{
                "source": {
                    "principals": [
                        "cluster.local/ns/production/sa/api-gateway"
                    ]
                }
            }],
            # Only on specific endpoints
            "to": [{
                "operation": {
                    "methods": ["GET", "POST"],
                    "paths": ["/api/v1/orders/*"]
                }
            }],
            # With valid JWT token
            "when": [{
                "key": "request.auth.claims[iss]",
                "values": ["https://auth.company.com"]
            }]
        }
    ]
)

# Example: Database can only be accessed by specific services
database_policy = AuthorizationPolicy(
    name="database-authz",
    namespace="production",
    service="postgres",
    rules=[
        {
            # Only Order Service and Inventory Service can access database
            "from": [{
                "source": {
                    "principals": [
                        "cluster.local/ns/production/sa/order-service",
                        "cluster.local/ns/production/sa/inventory-service"
                    ]
                }
            }]
        }
    ]
)

# Global mTLS policy: STRICT mode everywhere
mtls_policy = MTLSPolicy(mode="STRICT")
```

### How mTLS Works: The Handshake

When Order Service calls Inventory Service with mTLS:

```
1. Order Service initiates connection to Inventory Service

2. TLS Handshake:
   - Inventory Service sends its certificate (signed by mesh CA)
   - Order Service verifies certificate:
     * Is it signed by trusted CA?
     * Is it expired? (TTL = 24 hours)
     * Does SPIFFE ID match expected service?

3. Client Certificate:
   - Order Service sends its certificate
   - Inventory Service verifies:
     * Is it signed by trusted CA?
     * Is it expired?
     * Does SPIFFE ID match? (spiffe://cluster.local/ns/production/sa/order-service)

4. Authorization Policy Check:
   - Istio sidecar checks: Is order-service allowed to call this endpoint?
   - If policy exists and matches → Allow
   - If policy exists and doesn't match → Deny
   - If no policy exists → Default deny

5. Request proceeds over encrypted channel
   - Both identities verified
   - Authorization policy enforced
   - All traffic encrypted
```

### Certificate Rotation: The Hidden Complexity

Short-lived certificates (24 hours) are critical for zero trust, but they create operational complexity:

```python
class CertificateManager:
    """
    Automatic certificate rotation
    Certificates expire every 24 hours to limit blast radius
    """

    def __init__(self, ca_client, rotation_percentage: float = 0.5):
        self.ca_client = ca_client
        # Rotate at 50% of TTL (12 hours for 24-hour cert)
        self.rotation_percentage = rotation_percentage

    def rotate_if_needed(self, service: ServiceIdentity, current_cert):
        """
        Check if certificate needs rotation
        Rotate before expiration to prevent outages
        """
        ttl_seconds = service.certificate_ttl_hours * 3600
        rotation_threshold = ttl_seconds * self.rotation_percentage

        time_until_expiry = current_cert.not_valid_after - datetime.utcnow()

        if time_until_expiry.total_seconds() < rotation_threshold:
            # Time to rotate
            new_cert = self.ca_client.issue_certificate(
                spiffe_id=service.spiffe_id(),
                ttl_hours=service.certificate_ttl_hours
            )

            # Graceful rotation:
            # 1. Obtain new certificate
            # 2. Start accepting both old and new
            # 3. Start sending new certificate
            # 4. Wait for propagation
            # 5. Stop accepting old certificate

            return new_cert

        return current_cert
```

**Why short-lived certificates matter**: If a certificate is compromised, the attacker has at most 24 hours before it expires. With traditional certificates (valid for 1-2 years), compromised credentials grant long-term access.

### The Google Production Example

Google's internal service mesh handles:
- **2+ billion QPS** (queries per second) with mTLS on every request
- **Automatic certificate rotation** every 24 hours for millions of service instances
- **Fine-grained authorization policies** (service X can only call endpoint Y on service Z)
- **Zero trust by default**: No service trusts any other service without cryptographic proof

**Result**: When Google engineers discovered the Heartbleed vulnerability in OpenSSL (2014), they rotated all internal certificates within 24 hours. Because rotation was already automated and tested at scale, the response was seamless.

## Part 3: Network Microsegmentation

### The Blast Radius Problem

In a flat network, once an attacker compromises one service, they can pivot to any other service on the network. This is **lateral movement**:

1. Attacker compromises web application (SQL injection)
2. Pivots to application server
3. Pivots to database server
4. Exfiltrates entire customer database

Traditional networks are flat: everything can reach everything else. Zero trust requires **microsegmentation**: isolate every service, deny by default, allow only necessary communication.

### Software-Defined Perimeters

**Network policies** define which services can communicate, at the network level:

```python
from dataclasses import dataclass
from typing import List, Set

@dataclass
class NetworkSegment:
    """Isolated network segment for a service"""
    name: str
    allowed_ingress: Set[str]  # Which segments can send traffic here
    allowed_egress: Set[str]   # Which segments this can send traffic to

class MicrosegmentationPolicy:
    """
    Zero trust network segmentation
    Default deny: only explicit allow rules work
    """

    def __init__(self):
        # Define segments
        self.segments = {
            "public-web": NetworkSegment(
                name="public-web",
                allowed_ingress={"internet"},
                allowed_egress={"api-gateway"}
            ),
            "api-gateway": NetworkSegment(
                name="api-gateway",
                allowed_ingress={"public-web"},
                allowed_egress={"order-service", "auth-service"}
            ),
            "order-service": NetworkSegment(
                name="order-service",
                allowed_ingress={"api-gateway"},
                allowed_egress={"database", "inventory-service", "payment-service"}
            ),
            "inventory-service": NetworkSegment(
                name="inventory-service",
                allowed_ingress={"order-service"},
                allowed_egress={"database"}
            ),
            "payment-service": NetworkSegment(
                name="payment-service",
                allowed_ingress={"order-service"},
                allowed_egress={"external-payment-api"}
            ),
            "database": NetworkSegment(
                name="database",
                allowed_ingress={"order-service", "inventory-service"},
                allowed_egress=set()  # Database never initiates outbound connections
            ),
        }

    def can_communicate(self, source: str, destination: str) -> bool:
        """Check if source segment can reach destination segment"""
        if destination not in self.segments:
            return False

        dest_segment = self.segments[destination]
        return source in dest_segment.allowed_ingress

    def to_kubernetes_network_policy(self, segment_name: str) -> Dict:
        """
        Convert to Kubernetes NetworkPolicy resource
        Enforced at kernel level by CNI plugin
        """
        segment = self.segments[segment_name]

        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": f"{segment_name}-policy",
                "namespace": "production"
            },
            "spec": {
                "podSelector": {
                    "matchLabels": {
                        "segment": segment_name
                    }
                },
                # Default deny: only specified traffic allowed
                "policyTypes": ["Ingress", "Egress"],
                "ingress": [
                    {
                        "from": [
                            {
                                "podSelector": {
                                    "matchLabels": {
                                        "segment": source
                                    }
                                }
                            }
                            for source in segment.allowed_ingress
                        ]
                    }
                ],
                "egress": [
                    {
                        "to": [
                            {
                                "podSelector": {
                                    "matchLabels": {
                                        "segment": dest
                                    }
                                }
                            }
                            for dest in segment.allowed_egress
                        ]
                    }
                ]
            }
        }
```

### The Defense in Depth Model

Zero trust layers multiple security controls:

1. **Network layer**: Network policies prevent unauthorized communication
2. **Transport layer**: mTLS encrypts and authenticates all traffic
3. **Application layer**: Authorization policies verify permissions
4. **Data layer**: Encryption at rest protects stored data

**Example defense**:
- Attacker compromises web application (SQL injection)
- Tries to pivot to database
  - **Network policy blocks**: Web application is not in database's allowed_ingress
  - Even if network policy is bypassed:
    - **mTLS blocks**: Web application doesn't have database client certificate
    - Even if certificate is stolen:
      - **Authorization policy blocks**: Web application's SPIFFE ID is not authorized for database access
      - Even if authorization is bypassed:
        - **Database access controls block**: Application-level permissions deny access

**This is zero trust**: No single control is sufficient. Multiple layers verify identity and authorization at every step.

### Real-World Example: Capital One Breach (2019)

**What happened**:
- Attacker exploited SSRF vulnerability in web application
- Web application had overly permissive IAM role
- Role allowed listing and reading all S3 buckets
- Attacker exfiltrated 100 million customer records

**What zero trust would have prevented**:
1. **Least privilege**: Web application should only access its specific S3 bucket, not all buckets
2. **Network segmentation**: Web application should not have network access to IAM metadata endpoint
3. **Authorization policies**: Even with IAM credentials, should require explicit resource-level authorization
4. **Monitoring**: Anomalous S3 access (listing all buckets) should trigger alert

**Cost of breach**: $80 million fine, immeasurable reputation damage

**Cost of prevention**: IAM policy review (1 week of engineering time), network policy implementation (2 weeks), monitoring rules (1 week). Total: ~$50K investment to prevent $80M+ loss.

## Part 4: Identity and Access Management at Scale

### The Challenge: Thousands of Services, Millions of Requests

In a microservices system with 100 services, there are 100 × 99 = 9,900 possible service-to-service connections. Managing authorization policies manually is impossible.

**Zero trust IAM** requires:
1. **Automated policy generation**: Derive policies from actual traffic patterns
2. **Policy as code**: Version-controlled, tested, deployed like application code
3. **Dynamic authorization**: Policies updated without redeploying services
4. **Audit logs**: Every authorization decision logged for compliance

### Production IAM System

```python
from dataclasses import dataclass
from typing import List, Set, Dict, Optional
from datetime import datetime, timedelta
import json

@dataclass
class Permission:
    """A specific permission: resource + action"""
    resource: str  # e.g., "order-service:/api/v1/orders"
    action: str    # e.g., "read", "write", "delete"

    def matches(self, resource: str, action: str) -> bool:
        """Check if this permission grants access to resource:action"""
        # Support wildcards
        resource_match = (
            self.resource == resource or
            self.resource.endswith("/*") and resource.startswith(self.resource[:-2])
        )
        action_match = self.action == action or self.action == "*"
        return resource_match and action_match

@dataclass
class Role:
    """Collection of permissions"""
    name: str
    permissions: List[Permission]
    max_ttl: timedelta = timedelta(hours=1)  # Short-lived roles

@dataclass
class Policy:
    """Maps identities to roles"""
    identity: str  # SPIFFE ID or user ID
    roles: List[str]
    conditions: Dict[str, any]  # Context-based conditions

    def is_valid(self, context: Dict) -> bool:
        """Check if policy is valid for this context"""
        for key, expected_value in self.conditions.items():
            if context.get(key) != expected_value:
                return False
        return True

class IAMSystem:
    """
    Zero trust IAM system

    Features:
    - Least privilege: explicit allow only
    - Just-in-time access: temporary permission elevation
    - Context-aware: policies can depend on time, location, etc.
    - Audit everything: all decisions logged
    """

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.policies: List[Policy] = []
        self.temporary_grants: Dict[str, datetime] = {}

    def check_permission(
        self,
        identity: str,
        resource: str,
        action: str,
        context: Dict
    ) -> bool:
        """
        Check if identity has permission for resource:action

        Zero trust principles:
        1. Default deny
        2. Explicit allow only
        3. Context-aware
        4. Logged for audit
        """
        start_time = datetime.utcnow()

        # Find applicable policies for this identity
        applicable_policies = [
            policy for policy in self.policies
            if policy.identity == identity and policy.is_valid(context)
        ]

        if not applicable_policies:
            self._log_authz_decision(
                identity, resource, action, context,
                allowed=False, reason="no_applicable_policies",
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
            return False

        # Collect all permissions from applicable policies
        all_permissions: List[Permission] = []
        for policy in applicable_policies:
            for role_name in policy.roles:
                if role_name in self.roles:
                    role = self.roles[role_name]
                    all_permissions.extend(role.permissions)

        # Check if any permission grants access
        for permission in all_permissions:
            if permission.matches(resource, action):
                self._log_authz_decision(
                    identity, resource, action, context,
                    allowed=True, reason=f"granted_by_{permission.resource}:{permission.action}",
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
                return True

        # No permission matched
        self._log_authz_decision(
            identity, resource, action, context,
            allowed=False, reason="no_matching_permissions",
            duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
        )
        return False

    def grant_temporary_access(
        self,
        identity: str,
        role: str,
        duration: timedelta,
        justification: str,
        approved_by: str
    ):
        """
        Just-in-time access: temporary permission elevation

        Use case: Engineer needs to access production database for debugging.
        Grant read-only access for 1 hour, require approval and justification.
        """
        # Create temporary policy
        temp_policy = Policy(
            identity=identity,
            roles=[role],
            conditions={
                "temporary": True,
                "justification": justification,
                "approved_by": approved_by
            }
        )

        self.policies.append(temp_policy)

        # Schedule automatic revocation
        expiration = datetime.utcnow() + duration
        self.temporary_grants[identity] = expiration

        self._log_temporary_grant(
            identity, role, duration, justification, approved_by, expiration
        )

    def revoke_temporary_access(self, identity: str):
        """Revoke temporary access immediately"""
        self.policies = [
            p for p in self.policies
            if not (p.identity == identity and p.conditions.get("temporary"))
        ]

        if identity in self.temporary_grants:
            del self.temporary_grants[identity]

        self._log_temporary_revocation(identity)

    def cleanup_expired_grants(self):
        """Remove expired temporary grants"""
        now = datetime.utcnow()
        expired_identities = [
            identity for identity, expiration in self.temporary_grants.items()
            if expiration <= now
        ]

        for identity in expired_identities:
            self.revoke_temporary_access(identity)

    def analyze_unused_permissions(self) -> Dict[str, List[Permission]]:
        """
        Identify unused permissions for least privilege

        Zero trust principle: Continuously remove unused permissions
        """
        # In production: analyze audit logs to find never-used permissions
        # Return roles with permissions that haven't been used in 90 days
        pass

    def _log_authz_decision(
        self,
        identity: str,
        resource: str,
        action: str,
        context: Dict,
        allowed: bool,
        reason: str,
        duration_ms: float
    ):
        """
        Log every authorization decision for audit and threat detection

        Critical for:
        - Compliance (SOC 2, ISO 27001)
        - Threat detection (anomalous access patterns)
        - Debugging (why was this request denied?)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "authorization_decision",
            "identity": identity,
            "resource": resource,
            "action": action,
            "allowed": allowed,
            "reason": reason,
            "context": context,
            "duration_ms": duration_ms
        }

        # In production: send to centralized logging system
        print(json.dumps(log_entry))

    def _log_temporary_grant(
        self,
        identity: str,
        role: str,
        duration: timedelta,
        justification: str,
        approved_by: str,
        expiration: datetime
    ):
        """Log temporary access grant"""
        pass

    def _log_temporary_revocation(self, identity: str):
        """Log temporary access revocation"""
        pass

# Example usage
iam = IAMSystem()

# Define roles
iam.roles["order-reader"] = Role(
    name="order-reader",
    permissions=[
        Permission(resource="order-service:/api/v1/orders/*", action="read")
    ]
)

iam.roles["order-writer"] = Role(
    name="order-writer",
    permissions=[
        Permission(resource="order-service:/api/v1/orders/*", action="read"),
        Permission(resource="order-service:/api/v1/orders/*", action="write")
    ]
)

# Define policies
iam.policies.append(Policy(
    identity="spiffe://cluster.local/ns/production/sa/api-gateway",
    roles=["order-reader"],
    conditions={}
))

# Check permission
context = {
    "source_ip": "10.0.1.5",
    "time": datetime.utcnow().hour
}

allowed = iam.check_permission(
    identity="spiffe://cluster.local/ns/production/sa/api-gateway",
    resource="order-service:/api/v1/orders/12345",
    action="read",
    context=context
)
# Result: True (api-gateway has order-reader role)

allowed = iam.check_permission(
    identity="spiffe://cluster.local/ns/production/sa/api-gateway",
    resource="order-service:/api/v1/orders/12345",
    action="write",
    context=context
)
# Result: False (api-gateway doesn't have write permission)
```

### The Principle of Least Privilege in Production

**Example**: A payment service needs to:
1. Read payment methods from database
2. Call external payment processor API
3. Write transaction records to database

**Bad IAM policy** (overly permissive):
```
payment-service can:
- Read/write all database tables
- Call any external API
- Access all S3 buckets
```

**Good IAM policy** (least privilege):
```
payment-service can:
- Read from payments.payment_methods table
- Write to payments.transactions table
- Call api.stripe.com on port 443
- Nothing else (default deny)
```

**Why it matters**: If payment service is compromised, the attacker's access is limited to exactly what the service needs. They cannot access customer data in other tables, cannot call other APIs, cannot exfiltrate data to external systems.

## Part 5: Real Implementations and Lessons Learned

### Google BeyondCorp: The Original Zero Trust

**Timeline**:
- **2009**: Aurora attacks compromise Google's VPN
- **2011**: Google begins BeyondCorp project—eliminate VPN entirely
- **2014**: All internal applications moved to zero trust model
- **2017**: Google publishes BeyondCorp research papers

**Architecture**:
1. **No VPN**: Every request comes over public internet
2. **Device inventory**: Every device enrolled and verified continuously
3. **User and device context**: Every request includes identity + device posture
4. **Access proxy**: Centralized enforcement point checks authentication and authorization
5. **Dynamic access**: Permissions based on real-time context (location, time, device health)

**Results**:
- **Eliminated VPN attacks**: No VPN means no VPN vulnerabilities
- **Work from anywhere**: Employees connect securely from any network
- **Reduced complexity**: No split-tunnel VPN, no "inside" vs "outside" network
- **Better security**: Every request verified, regardless of source

**Lesson**: Zero trust is not just more secure—it's simpler. Eliminating the trusted network eliminates a class of attacks and operational complexity.

### Cloudflare Zero Trust: SaaS-ifying Zero Trust

**Problem**: Most companies cannot build Google-scale zero trust infrastructure.

**Solution**: Cloudflare offers zero trust as a service:
1. **Cloudflare Access**: Replace VPN with identity-aware proxy
2. **Cloudflare Gateway**: Secure DNS filtering and traffic inspection
3. **Cloudflare Tunnel**: Expose internal apps without opening firewall ports

**Architecture**:
- Internal application (e.g., admin dashboard) runs on-premise
- Cloudflare Tunnel establishes outbound connection to Cloudflare edge
- Users authenticate via SSO (Okta, Google, etc.) to Cloudflare Access
- Cloudflare Access verifies identity and device, proxies to internal app
- No VPN, no firewall rules, no exposed ports

**Results**:
- **Deployed in days**: No infrastructure to build
- **$20/user/month**: Cheaper than VPN + firewall + security tools
- **Zero-day immunity**: When VPN zero-days emerged in 2020, Cloudflare customers unaffected

**Lesson**: Zero trust is increasingly a solved problem. Buy, don't build (unless you're Google-scale).

### HashiCorp Boundary: Open Source Zero Trust

**Problem**: Infrastructure engineers need to SSH to servers, connect to databases, access internal tools.

**Traditional approach**: Bastion host (jump box) with SSH key management. Operational nightmare.

**Boundary approach**:
1. **No static credentials**: No SSH keys, no database passwords
2. **Brokered access**: Boundary generates short-lived credentials on demand
3. **Identity-based**: User authenticates to Boundary, Boundary authenticates to target
4. **Session recording**: All SSH and database sessions logged for audit

**Architecture**:
```
User → Boundary Controller (identity verification)
    → Boundary Worker (credential brokering)
    → Target (SSH server, database, Kubernetes)
```

**Lesson**: Zero trust applies to infrastructure access, not just application access.

## Mental Model: Zero Trust in Practice

**The Core Insight**: Security is not a property of the network. It's a property of every request.

### Traditional Security (Perimeter Model)
```
[Firewall] → [Inside = Trusted] → [Full Access]
```

**Problem**: Once inside, attacker has full access. Lateral movement is easy.

### Zero Trust Model
```
[Request] → [Verify Identity] → [Verify Device] → [Check Context] → [Check Permissions] → [Allow/Deny]
```

**Benefit**: Every request verified. Lateral movement requires re-authentication at every step.

### The Five Principles (Applied)

1. **Verify explicitly**
   - Before: "You're on the VPN, you can access the database"
   - After: "Your identity is verified (MFA), your device is compliant, your request is authorized, your connection is encrypted—now you can access the database"

2. **Use least privilege**
   - Before: "You have admin access to all production servers"
   - After: "You have read-only access to production logs for the next 1 hour (just-in-time access)"

3. **Assume breach**
   - Before: "We have a firewall, we're secure"
   - After: "We assume attackers are inside. Every service verifies every request. Blast radius is minimized."

4. **Verify continuously**
   - Before: "You authenticated this morning, you're good all day"
   - After: "Your token expires in 15 minutes. Your device health is re-checked on every request. Your location is monitored."

5. **Monitor everything**
   - Before: "We log successful logins"
   - After: "We log every authentication, authorization, and access attempt. Anomaly detection identifies compromised accounts."

### When to Use Zero Trust

**Use zero trust when**:
- You have multiple services communicating
- You have users accessing internal tools
- You have compliance requirements (SOC 2, ISO 27001, HIPAA)
- You have remote employees
- You have high-value assets (customer data, financial systems, IP)

**Don't use zero trust when**:
- You have a single-server application with no internal services (overkill)
- You have no sensitive data (the overhead isn't worth it)

**In practice**: Most production systems should use zero trust. The question is not "Should we?" but "How quickly can we implement it?"

### Next Steps

Zero trust secures **who** can access **what**. But distributed systems also need to secure **data in transit** and **data at rest**. Continue to [Encryption in Transit and At Rest](./encryption-transit-rest.md) to understand encryption strategies at scale.

