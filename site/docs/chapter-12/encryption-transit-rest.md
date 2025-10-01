# Encryption in Transit and At Rest: Protecting Data Everywhere

## Introduction: The $143 Million Data Breach

On July 29, 2017, Equifax announced a data breach affecting 147 million people. Social security numbers, birth dates, addresses, and credit card numbers—stolen. The breach cost Equifax $1.4 billion in total damages, including a $575 million settlement with the FTC.

**The root cause**: An unpatched Apache Struts vulnerability. But that's not why the breach was catastrophic.

**Why it was catastrophic**: The stolen data was **unencrypted**. When attackers accessed the database, they read everything in plaintext. Social security numbers, credit card numbers, personal information—all immediately usable.

If that data had been encrypted at rest, the attackers would have needed to:
1. Breach the database (achieved)
2. Steal the encryption keys (separate system)
3. Decrypt billions of records (computationally expensive)

**The lesson**: Encryption is not about preventing breaches. It's about **making breaches useless**. When attackers can't read the data they stole, the breach becomes a security incident (bad) instead of a catastrophic loss (existential).

### Why Encryption Matters in Distributed Systems

Distributed systems have data everywhere:
- **In transit**: Requests flowing between services, across regions, over public internet
- **At rest**: Databases, object storage, backups, logs, caches
- **In use**: Memory, CPU registers, temporary files (hardest to protect)

Traditional systems had a perimeter: data inside the network was "safe." Distributed systems have no perimeter. Data flows through:
- Multiple clouds (AWS, GCP, Azure)
- Edge locations (CDNs, PoPs)
- Third-party APIs (payment processors, analytics)
- Employee devices (remote work)

**Without encryption**: Every network hop is a potential breach point. Every storage system is a potential target. Every log file is a potential leak.

**With encryption**: Data is protected at every layer:
- **TLS/SSL in transit**: Attackers intercepting network traffic see ciphertext
- **Encryption at rest**: Attackers stealing disks or database dumps see ciphertext
- **Key management**: Even with ciphertext, attackers need keys (stored separately)

### The Performance Trade-Off

Encryption is not free. It adds:
- **CPU overhead**: Encrypting and decrypting data consumes CPU cycles
- **Latency**: Cryptographic operations add milliseconds to requests
- **Complexity**: Key management, rotation, distribution, revocation

**Real-world costs**:
- **TLS handshake**: 1-2 round trips, adding 50-200ms to connection setup
- **Encryption throughput**: Modern AES encryption on commodity hardware: ~2-5 GB/s per core
- **Key operations**: HSM key operations: ~1000-10000 ops/second (bottleneck)

But the cost of **not** encrypting is existential:
- **Data breaches**: $4.35 million average cost per breach (IBM 2022)
- **Compliance violations**: GDPR fines up to 4% of global revenue
- **Reputation damage**: Equifax lost 1/3 of its market value after the breach

**The principle**: Encrypt everything by default. Optimize performance only when measurements show encryption is the bottleneck.

## Part 1: Encryption in Transit—TLS at Scale

### The Problem: Plaintext on the Wire

Without encryption, network traffic is readable by anyone:
- **On the LAN**: ARP spoofing, switch port mirroring
- **On WiFi**: Packet sniffing (Wireshark)
- **On the WAN**: BGP hijacking, ISP interception
- **In the cloud**: Compromised hypervisor, nosy cloud provider

**Example attack**: A user logs into a website over HTTP (not HTTPS). An attacker on the same WiFi network captures the traffic:
```
POST /login HTTP/1.1
Host: example.com
Content-Type: application/json

{"username": "alice", "password": "hunter2"}
```

Attacker now has Alice's credentials. Game over.

**With TLS**: Traffic is encrypted end-to-end:
```
[Encrypted binary data - unreadable without key]
```

Attacker sees traffic but cannot read credentials.

### TLS 1.3: The Modern Standard

TLS (Transport Layer Security) encrypts data in transit. TLS 1.3 (2018) is the current standard, improving on TLS 1.2:

**Key improvements**:
1. **Faster handshake**: 1 round trip (down from 2 in TLS 1.2)
2. **Stronger crypto**: Removed weak ciphers (RSA, SHA-1, MD5)
3. **Forward secrecy**: Mandatory Diffie-Hellman for ephemeral keys
4. **0-RTT resumption**: Subsequent connections can send data immediately

**TLS 1.3 handshake** (simplified):
```
Client → Server: ClientHello (supported ciphers, key share)
Server → Client: ServerHello (chosen cipher, key share, certificate, Finished)
Client → Server: Finished (confirms handshake, starts encrypted data)

Total: 1.5 round trips (or 1-RTT for new connections, 0-RTT for resumed)
```

**TLS 1.2 handshake** (for comparison):
```
Client → Server: ClientHello
Server → Client: ServerHello, Certificate, ServerHelloDone
Client → Server: ClientKeyExchange, ChangeCipherSpec, Finished
Server → Client: ChangeCipherSpec, Finished

Total: 2 round trips (adds 100-200ms on intercontinental connections)
```

### Production TLS Configuration

Here's production-grade TLS configuration for an HTTPS server:

```python
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

class SecureHTTPServer:
    """
    Production TLS configuration

    Security properties:
    - TLS 1.3 only (reject TLS 1.2 and earlier)
    - Strong ciphers only (AES-GCM, ChaCha20)
    - Forward secrecy (ephemeral Diffie-Hellman)
    - Certificate verification
    """

    def __init__(
        self,
        cert_file: str,
        key_file: str,
        ca_file: Optional[str] = None,
        require_client_cert: bool = False
    ):
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_file = ca_file
        self.require_client_cert = require_client_cert

    def create_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context with production security settings

        Follows Mozilla's "Modern" configuration:
        https://ssl-config.mozilla.org/
        """
        # Use TLS 1.3 only (most secure)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        # Minimum TLS version: 1.3 (reject 1.2 and earlier)
        context.minimum_version = ssl.TLSVersion.TLSv1_3

        # Load server certificate and private key
        context.load_cert_chain(
            certfile=self.cert_file,
            keyfile=self.key_file
        )

        # Cipher suites (TLS 1.3 - automatically secure)
        # TLS 1.3 only supports strong ciphers:
        # - TLS_AES_256_GCM_SHA384
        # - TLS_CHACHA20_POLY1305_SHA256
        # - TLS_AES_128_GCM_SHA256
        # No need to manually configure (weak ciphers removed)

        # Client certificate verification (for mTLS)
        if self.require_client_cert:
            context.verify_mode = ssl.CERT_REQUIRED
            if self.ca_file:
                context.load_verify_locations(cafile=self.ca_file)
        else:
            context.verify_mode = ssl.CERT_NONE

        # Additional security options
        context.check_hostname = False  # Disabled for server
        context.options |= ssl.OP_NO_COMPRESSION  # Prevent CRIME attack
        context.options |= ssl.OP_SINGLE_DH_USE   # Forward secrecy
        context.options |= ssl.OP_SINGLE_ECDH_USE # Forward secrecy

        # Session tickets (for 0-RTT resumption)
        # Note: 0-RTT has replay risk - disable for sensitive endpoints
        context.options |= ssl.OP_NO_TICKET  # Disable for max security

        return context

    def start_server(self, host: str = "0.0.0.0", port: int = 443):
        """Start HTTPS server with TLS"""
        context = self.create_ssl_context()

        httpd = HTTPServer((host, port), SimpleHTTPSHandler)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

        print(f"HTTPS server running on https://{host}:{port}")
        httpd.serve_forever()

class SimpleHTTPSHandler(BaseHTTPRequestHandler):
    """Simple HTTPS handler for demonstration"""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Secure Connection</h1></body></html>")

# Example usage
if __name__ == "__main__":
    server = SecureHTTPServer(
        cert_file="/etc/ssl/certs/server.crt",
        key_file="/etc/ssl/private/server.key",
        require_client_cert=False  # Set True for mTLS
    )
    server.start_server(port=8443)
```

### Certificate Management at Scale

TLS requires X.509 certificates for server authentication. At scale, certificate management is complex:

**Challenges**:
1. **Certificate lifecycle**: Issue, deploy, renew, revoke
2. **Multiple environments**: Dev, staging, production
3. **Multiple domains**: example.com, api.example.com, cdn.example.com
4. **Short lifespans**: 90-day certificates (Let's Encrypt default)
5. **Automation**: Manual renewal doesn't scale

**Solution**: Automated Certificate Management Environment (ACME) protocol

```python
import subprocess
from datetime import datetime, timedelta
from typing import List, Optional
import hashlib
import json

class CertificateManager:
    """
    Automated certificate management using Let's Encrypt

    Features:
    - Automatic renewal before expiration
    - Multiple domain support (SAN certificates)
    - Zero-downtime updates
    """

    def __init__(
        self,
        domain: str,
        additional_domains: List[str] = None,
        email: str = None
    ):
        self.domain = domain
        self.additional_domains = additional_domains or []
        self.email = email

    def issue_certificate(self) -> bool:
        """
        Issue new certificate using ACME (Let's Encrypt)

        Process:
        1. Generate key pair
        2. Create CSR (Certificate Signing Request)
        3. Prove domain ownership (HTTP-01 or DNS-01 challenge)
        4. Receive signed certificate
        """
        # Build certbot command
        cmd = [
            "certbot", "certonly",
            "--standalone",  # Use standalone mode (requires port 80)
            "--non-interactive",
            "--agree-tos",
            "-d", self.domain
        ]

        # Add additional domains (SAN certificate)
        for domain in self.additional_domains:
            cmd.extend(["-d", domain])

        if self.email:
            cmd.extend(["--email", self.email])

        # Run certbot
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"Certificate issued successfully for {self.domain}")
            return True
        else:
            print(f"Certificate issuance failed: {result.stderr}")
            return False

    def check_expiration(self) -> Optional[datetime]:
        """Check certificate expiration date"""
        cmd = [
            "openssl", "x509",
            "-in", f"/etc/letsencrypt/live/{self.domain}/cert.pem",
            "-noout", "-enddate"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Parse output: "notAfter=Dec 31 23:59:59 2023 GMT"
            date_str = result.stdout.split("=")[1].strip()
            expiration = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
            return expiration
        return None

    def needs_renewal(self, threshold_days: int = 30) -> bool:
        """Check if certificate needs renewal"""
        expiration = self.check_expiration()
        if not expiration:
            return True

        days_until_expiration = (expiration - datetime.utcnow()).days
        return days_until_expiration <= threshold_days

    def renew_certificate(self) -> bool:
        """
        Renew certificate (reissue with same domains)

        Let's Encrypt certificates expire after 90 days.
        Renew 30 days before expiration.
        """
        if not self.needs_renewal():
            print(f"Certificate for {self.domain} doesn't need renewal yet")
            return False

        cmd = ["certbot", "renew", "--non-interactive"]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"Certificate renewed successfully for {self.domain}")
            self._reload_services()
            return True
        else:
            print(f"Certificate renewal failed: {result.stderr}")
            return False

    def _reload_services(self):
        """
        Reload services to use new certificate

        Zero-downtime reload:
        1. New certificate written to disk
        2. Send SIGHUP to nginx/apache to reload config
        3. New connections use new cert
        4. Old connections complete on old cert
        """
        # Reload nginx
        subprocess.run(["nginx", "-s", "reload"])

        # Or reload systemd service
        # subprocess.run(["systemctl", "reload", "nginx"])

class CertificateMonitor:
    """
    Monitor certificates and renew automatically

    Run as cron job or systemd timer:
    0 0 * * * /usr/bin/python3 /opt/cert_monitor.py
    """

    def __init__(self, domains: List[str], email: str):
        self.domains = domains
        self.email = email

    def check_all_certificates(self):
        """Check all certificates and renew if needed"""
        for domain in self.domains:
            manager = CertificateManager(domain, email=self.email)

            if manager.needs_renewal():
                print(f"Renewing certificate for {domain}...")
                success = manager.renew_certificate()

                if success:
                    self._send_notification(
                        f"Certificate renewed for {domain}",
                        "success"
                    )
                else:
                    self._send_notification(
                        f"Certificate renewal FAILED for {domain}",
                        "error"
                    )

    def _send_notification(self, message: str, level: str):
        """Send alert (email, Slack, PagerDuty)"""
        # In production: integrate with alerting system
        print(f"[{level.upper()}] {message}")

# Example: Automated certificate management
if __name__ == "__main__":
    monitor = CertificateMonitor(
        domains=["example.com", "api.example.com", "cdn.example.com"],
        email="admin@example.com"
    )
    monitor.check_all_certificates()
```

### The Performance Impact of TLS

**TLS overhead** comes from two sources:

1. **Handshake latency**: Initial connection setup
   - TLS 1.3: 1-RTT (~50ms for US East-West, ~150ms for US-EU)
   - TLS 1.2: 2-RTT (~100ms for US East-West, ~300ms for US-EU)

2. **Encryption throughput**: Ongoing data transfer
   - AES-128-GCM: ~5 GB/s per core (hardware-accelerated)
   - ChaCha20-Poly1305: ~2 GB/s per core (software)

**Optimization strategies**:

```python
import time
from dataclasses import dataclass
from typing import Dict

@dataclass
class TLSPerformanceMetrics:
    """Metrics for TLS performance monitoring"""
    handshakes_per_second: float
    encryption_throughput_mbps: float
    cpu_usage_percent: float
    connection_reuse_ratio: float

class TLSOptimizer:
    """
    Optimize TLS performance for high-traffic systems

    Techniques:
    1. Session resumption (0-RTT)
    2. Connection pooling
    3. Hardware acceleration
    4. Load balancer TLS termination
    """

    def __init__(self):
        self.connection_pool: Dict[str, any] = {}
        self.session_cache: Dict[str, bytes] = {}

    def optimize_handshake_with_resumption(self):
        """
        TLS session resumption: avoid full handshake

        First connection: Full handshake (1-RTT)
        Subsequent connections: Resume session (0-RTT)

        Reduces latency by ~50-150ms per connection
        """
        # In TLS 1.3, session resumption uses PSK (Pre-Shared Key)
        # Server sends NewSessionTicket after handshake
        # Client uses ticket on next connection

        # Performance gain:
        # - Without resumption: 1-RTT handshake every connection
        # - With resumption: 0-RTT for 80%+ of connections
        # - For 10,000 req/s: saves 800-1500ms of aggregate latency per second

        pass

    def optimize_with_connection_pooling(self):
        """
        Connection pooling: reuse TCP connections

        HTTP/1.1: Keep-Alive (reuse connection for multiple requests)
        HTTP/2: Multiplexing (multiple requests on single connection)

        Avoids handshake entirely for subsequent requests
        """
        # Keep connections alive for 60 seconds
        # Reuse for all requests to same host

        # Performance gain:
        # - First request: Full TLS handshake
        # - Next 100 requests: No handshake (save 100 * 50ms = 5 seconds)

        pass

    def optimize_with_hardware_acceleration(self):
        """
        Hardware acceleration: offload crypto to dedicated hardware

        Options:
        - CPU AES-NI instructions (Intel, AMD)
        - Network card TLS offload (SmartNICs)
        - Hardware Security Module (HSM) for key operations

        Performance gain:
        - Software AES: ~500 MB/s per core
        - Hardware AES-NI: ~5 GB/s per core (10× faster)
        """
        # Check if AES-NI is available
        import subprocess
        result = subprocess.run(
            ["grep", "-m1", "aes", "/proc/cpuinfo"],
            capture_output=True
        )

        if result.returncode == 0:
            print("AES-NI hardware acceleration available")
            # OpenSSL automatically uses AES-NI when available
        else:
            print("AES-NI not available - using software crypto")

    def optimize_with_tls_termination(self):
        """
        TLS termination at load balancer

        Architecture:
        Client → [TLS] → Load Balancer → [Plaintext] → Backend Servers

        Benefits:
        - Centralized certificate management
        - Offload TLS from application servers
        - Hardware acceleration at load balancer

        Trade-off:
        - Plaintext on internal network (use service mesh for internal TLS)
        """
        pass

    def measure_performance(self) -> TLSPerformanceMetrics:
        """
        Measure TLS performance

        Key metrics:
        - Handshakes per second (capacity)
        - Encryption throughput (bandwidth)
        - CPU usage (cost)
        - Connection reuse ratio (efficiency)
        """
        # In production: integrate with monitoring system
        return TLSPerformanceMetrics(
            handshakes_per_second=5000,
            encryption_throughput_mbps=4000,
            cpu_usage_percent=25,
            connection_reuse_ratio=0.85
        )
```

### The Real-World Numbers

**Google's TLS deployment**:
- **Handshakes**: 10+ million per second globally
- **Overhead**: <1% CPU increase when TLS enabled across all services
- **Latency**: <10ms added latency for TLS handshake (with session resumption)

**Cloudflare's TLS deployment**:
- **TLS 1.3 adoption**: 60%+ of all HTTPS connections
- **Performance gain**: TLS 1.3 reduces handshake time by 40% vs TLS 1.2
- **0-RTT usage**: 20% of resumed connections use 0-RTT

**Lesson**: TLS performance is a solved problem. Modern hardware and protocols make encryption essentially free. There's no excuse not to encrypt everything in transit.

## Part 2: Encryption at Rest—Protecting Stored Data

### The Problem: Stolen Disks

Hard drives fail. Cloud storage gets misconfigured. Backups get lost. Laptops get stolen.

**Without encryption at rest**: An attacker with physical access to the storage medium can read all data. Plug the disk into another machine, mount the filesystem, and extract everything.

**With encryption at rest**: The disk contains only ciphertext. Without the encryption key, the data is unreadable.

### Block-Level vs File-Level Encryption

**Block-level encryption** (LUKS, dm-crypt, BitLocker):
- Encrypts entire disk or partition
- Transparent to applications (happens below filesystem)
- Key unlocks disk at boot time
- Performance: ~5% overhead on modern hardware with AES-NI

**File-level encryption** (eCryptfs, EncFS):
- Encrypts individual files or directories
- Each file can have different key
- More granular access control
- Performance: ~10-20% overhead

**Database-level encryption**:
- Encrypts data within database (Transparent Data Encryption)
- Application-transparent
- Key management integrated with database
- Performance: ~2-10% overhead

### Production Encryption at Rest: Database

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
import os
from typing import Tuple, Optional
import json

class EncryptedDatabase:
    """
    Database with encryption at rest

    Architecture:
    - Master key stored in HSM or KMS
    - Data keys derived from master key
    - Each record encrypted with unique IV
    - AEAD mode (AES-GCM) provides encryption + authentication
    """

    def __init__(self, master_key: bytes):
        """
        master_key: 256-bit key from KMS
        In production: fetch from AWS KMS, Google Cloud KMS, or HashiCorp Vault
        """
        self.master_key = master_key
        self.backend = default_backend()

    def encrypt_field(self, plaintext: str) -> Tuple[bytes, bytes, bytes]:
        """
        Encrypt a database field

        Returns: (ciphertext, iv, tag)
        - ciphertext: encrypted data
        - iv: initialization vector (unique per encryption)
        - tag: authentication tag (ensures integrity)
        """
        # Generate random IV (never reuse IVs with same key!)
        iv = os.urandom(12)  # 96 bits for GCM

        # Create cipher in GCM mode (authenticated encryption)
        cipher = Cipher(
            algorithms.AES(self.master_key),
            modes.GCM(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()

        # Encrypt
        ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()

        # Get authentication tag
        tag = encryptor.tag

        return ciphertext, iv, tag

    def decrypt_field(
        self,
        ciphertext: bytes,
        iv: bytes,
        tag: bytes
    ) -> Optional[str]:
        """
        Decrypt a database field

        Returns: plaintext or None if authentication fails
        """
        # Create cipher in GCM mode
        cipher = Cipher(
            algorithms.AES(self.master_key),
            modes.GCM(iv, tag),
            backend=self.backend
        )
        decryptor = cipher.decryptor()

        try:
            # Decrypt and verify authentication tag
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext.decode()
        except Exception:
            # Authentication failed - data was tampered with
            return None

    def store_encrypted_record(self, user_id: int, ssn: str, credit_card: str):
        """
        Store sensitive record with encryption

        In production: integrate with actual database
        """
        # Encrypt sensitive fields
        ssn_ciphertext, ssn_iv, ssn_tag = self.encrypt_field(ssn)
        cc_ciphertext, cc_iv, cc_tag = self.encrypt_field(credit_card)

        # Store in database (pseudocode)
        record = {
            "user_id": user_id,
            "ssn_ciphertext": ssn_ciphertext.hex(),
            "ssn_iv": ssn_iv.hex(),
            "ssn_tag": ssn_tag.hex(),
            "cc_ciphertext": cc_ciphertext.hex(),
            "cc_iv": cc_iv.hex(),
            "cc_tag": cc_tag.hex(),
        }

        # db.insert("users", record)
        print(f"Stored encrypted record for user {user_id}")
        return record

    def retrieve_encrypted_record(self, user_id: int) -> dict:
        """
        Retrieve and decrypt sensitive record

        In production: fetch from actual database
        """
        # Fetch from database (pseudocode)
        # record = db.query("SELECT * FROM users WHERE user_id = ?", user_id)

        # For demonstration, use stored record
        record = {
            "ssn_ciphertext": "...",
            "ssn_iv": "...",
            "ssn_tag": "...",
            "cc_ciphertext": "...",
            "cc_iv": "...",
            "cc_tag": "...",
        }

        # Decrypt sensitive fields
        ssn = self.decrypt_field(
            bytes.fromhex(record["ssn_ciphertext"]),
            bytes.fromhex(record["ssn_iv"]),
            bytes.fromhex(record["ssn_tag"])
        )

        credit_card = self.decrypt_field(
            bytes.fromhex(record["cc_ciphertext"]),
            bytes.fromhex(record["cc_iv"]),
            bytes.fromhex(record["cc_tag"])
        )

        return {
            "user_id": user_id,
            "ssn": ssn,
            "credit_card": credit_card
        }

# Example usage
master_key = os.urandom(32)  # 256-bit key from KMS
db = EncryptedDatabase(master_key)

# Store encrypted data
db.store_encrypted_record(
    user_id=12345,
    ssn="123-45-6789",
    credit_card="4111-1111-1111-1111"
)

# Retrieve and decrypt
record = db.retrieve_encrypted_record(user_id=12345)
print(record)
```

### Envelope Encryption: Key Management at Scale

**Problem**: With millions of records, encrypting each with the master key is risky:
- If master key is compromised, all data is compromised
- Key rotation requires re-encrypting all data (expensive)

**Solution**: **Envelope encryption** (used by AWS, Google Cloud, Azure)

**Architecture**:
1. **Master key** (KEK - Key Encryption Key): Stored in HSM/KMS, never leaves secure boundary
2. **Data keys** (DEK - Data Encryption Key): Generated per-record or per-file, encrypted with master key
3. **Encrypted data**: Encrypted with data key

**Flow**:
```
Encryption:
1. Generate random data key (DEK)
2. Encrypt data with DEK
3. Encrypt DEK with master key (KEK)
4. Store: encrypted_data + encrypted_DEK
5. Discard DEK from memory

Decryption:
1. Fetch encrypted_data + encrypted_DEK
2. Send encrypted_DEK to KMS → decrypt with KEK → receive DEK
3. Decrypt data with DEK
4. Discard DEK from memory
```

**Benefits**:
- Master key never leaves HSM/KMS (most secure)
- Data keys rotated per-record (limit blast radius)
- Master key rotation: only re-encrypt DEKs, not data (cheap)

```python
import os
from typing import Tuple, Dict
import base64

class EnvelopeEncryption:
    """
    Envelope encryption for scalable key management

    Used by:
    - AWS S3 (SSE-KMS)
    - Google Cloud Storage (CMEK)
    - Azure Storage (Customer-managed keys)
    """

    def __init__(self, kms_client):
        """
        kms_client: Client for Key Management Service
        In production: boto3 KMS client, Google Cloud KMS, etc.
        """
        self.kms_client = kms_client

    def encrypt_data(self, plaintext: bytes) -> Tuple[bytes, bytes]:
        """
        Encrypt data using envelope encryption

        Returns: (encrypted_data, encrypted_data_key)
        """
        # Step 1: Generate random data key (DEK)
        data_key = os.urandom(32)  # 256-bit AES key

        # Step 2: Encrypt data with DEK
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        iv = os.urandom(12)
        cipher = Cipher(
            algorithms.AES(data_key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        tag = encryptor.tag

        # Combine IV + ciphertext + tag
        encrypted_data = iv + ciphertext + tag

        # Step 3: Encrypt DEK with master key (via KMS)
        encrypted_data_key = self.kms_client.encrypt(data_key)

        # Step 4: Discard DEK from memory (security best practice)
        del data_key

        return encrypted_data, encrypted_data_key

    def decrypt_data(
        self,
        encrypted_data: bytes,
        encrypted_data_key: bytes
    ) -> bytes:
        """
        Decrypt data using envelope encryption
        """
        # Step 1: Decrypt DEK using master key (via KMS)
        data_key = self.kms_client.decrypt(encrypted_data_key)

        # Step 2: Decrypt data with DEK
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        # Extract IV, ciphertext, tag
        iv = encrypted_data[:12]
        tag = encrypted_data[-16:]
        ciphertext = encrypted_data[12:-16]

        cipher = Cipher(
            algorithms.AES(data_key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # Step 3: Discard DEK from memory
        del data_key

        return plaintext

class MockKMSClient:
    """
    Mock KMS client for demonstration
    In production: use AWS KMS, Google Cloud KMS, HashiCorp Vault
    """

    def __init__(self, master_key: bytes):
        self.master_key = master_key

    def encrypt(self, data_key: bytes) -> bytes:
        """Encrypt data key with master key"""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        iv = os.urandom(12)
        cipher = Cipher(
            algorithms.AES(self.master_key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data_key) + encryptor.finalize()
        tag = encryptor.tag

        return iv + ciphertext + tag

    def decrypt(self, encrypted_data_key: bytes) -> bytes:
        """Decrypt data key with master key"""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        iv = encrypted_data_key[:12]
        tag = encrypted_data_key[-16:]
        ciphertext = encrypted_data_key[12:-16]

        cipher = Cipher(
            algorithms.AES(self.master_key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        return plaintext

# Example usage
master_key = os.urandom(32)  # Stored in HSM/KMS
kms = MockKMSClient(master_key)
envelope = EnvelopeEncryption(kms)

# Encrypt large file
plaintext = b"Sensitive customer data..." * 1000
encrypted_data, encrypted_key = envelope.encrypt_data(plaintext)

print(f"Encrypted data size: {len(encrypted_data)} bytes")
print(f"Encrypted key size: {len(encrypted_key)} bytes")

# Decrypt
decrypted = envelope.decrypt_data(encrypted_data, encrypted_key)
assert decrypted == plaintext
print("Decryption successful!")
```

### Hardware Security Modules (HSMs)

**Problem**: Master keys must be protected with highest security. If master key is compromised, all encrypted data is compromised.

**Solution**: **Hardware Security Module (HSM)** — tamper-resistant hardware device that stores keys and performs cryptographic operations.

**Properties**:
1. **Keys never leave HSM**: Encryption/decryption happens inside HSM, keys never exported
2. **Tamper-resistant**: Physical attacks destroy keys before extraction
3. **FIPS 140-2 Level 3 certified**: Meets government/financial security standards
4. **Audit logging**: All operations logged for compliance

**Use cases**:
- Root certificate authority keys (issuing TLS certificates)
- Master encryption keys (envelope encryption)
- Payment card processing (PCI-DSS compliance)
- Code signing keys (software distribution)

**Performance characteristics**:
- **RSA operations**: 1000-10,000 per second (signing/verification)
- **AES operations**: 50,000-100,000 per second (encryption/decryption)
- **Latency**: 1-10ms per operation

**Cost**:
- **On-premise HSM**: $10,000-$50,000 per device (CapEx)
- **Cloud HSM** (AWS CloudHSM, Azure Dedicated HSM): $1-2 per hour (~$700-1400/month)

**When to use HSM**:
- Compliance requires FIPS 140-2 Level 3 (financial services, government)
- Protecting high-value keys (root CA, master encryption keys)
- High-stakes operations (code signing for OS updates, certificate issuance)

**When not to use HSM**:
- Low-value data (operational logs, temp files)
- Performance-critical path (HSM adds latency)
- Cost-sensitive systems (KMS is cheaper for most use cases)

## Part 3: Key Rotation and Compliance

### Why Key Rotation Matters

**Problem**: Long-lived keys accumulate risk:
- More time for attackers to steal key
- More data encrypted with single key (larger blast radius)
- More operations using key (more side-channel attack opportunities)

**Solution**: **Key rotation** — periodically replace old keys with new keys, re-encrypt data.

**Rotation frequency**:
- **TLS certificates**: 90 days (Let's Encrypt default)
- **Service mesh certificates**: 24 hours (mTLS)
- **Database master keys**: 1 year (AWS KMS default)
- **Data keys** (envelope encryption): Per-record (effectively continuous)

### Automated Key Rotation

```python
from datetime import datetime, timedelta
from typing import Dict, List
import os

class KeyRotationManager:
    """
    Automated key rotation

    Features:
    - Periodic rotation based on policy
    - Zero-downtime rotation (old and new keys valid during transition)
    - Audit logging
    """

    def __init__(self, kms_client):
        self.kms_client = kms_client
        self.rotation_policies: Dict[str, timedelta] = {}
        self.active_keys: Dict[str, bytes] = {}
        self.key_metadata: Dict[str, dict] = {}

    def register_key(
        self,
        key_id: str,
        rotation_period: timedelta = timedelta(days=90)
    ):
        """Register a key for automatic rotation"""
        self.rotation_policies[key_id] = rotation_period
        self.key_metadata[key_id] = {
            "created_at": datetime.utcnow(),
            "last_rotated": datetime.utcnow(),
            "rotation_count": 0
        }

    def rotate_key_if_needed(self, key_id: str) -> bool:
        """
        Check if key needs rotation and rotate if necessary

        Graceful rotation:
        1. Generate new key
        2. Mark old key as "deprecated" (still valid for decryption)
        3. Use new key for all new encryption
        4. Re-encrypt data with new key (background process)
        5. Delete old key after all data re-encrypted
        """
        if key_id not in self.rotation_policies:
            return False

        metadata = self.key_metadata[key_id]
        rotation_period = self.rotation_policies[key_id]
        time_since_rotation = datetime.utcnow() - metadata["last_rotated"]

        if time_since_rotation >= rotation_period:
            # Time to rotate
            new_key = self._generate_new_key(key_id)

            # Keep old key available (for decrypting existing data)
            old_key = self.active_keys.get(key_id)
            if old_key:
                self._archive_key(key_id, old_key)

            # Activate new key
            self.active_keys[key_id] = new_key
            metadata["last_rotated"] = datetime.utcnow()
            metadata["rotation_count"] += 1

            self._log_rotation(key_id, metadata["rotation_count"])

            # Schedule re-encryption of existing data
            self._schedule_reencryption(key_id, old_key, new_key)

            return True

        return False

    def _generate_new_key(self, key_id: str) -> bytes:
        """Generate new key via KMS"""
        return self.kms_client.generate_data_key(key_id)

    def _archive_key(self, key_id: str, old_key: bytes):
        """
        Archive old key (keep for decryption, don't use for encryption)

        Old keys remain valid for:
        - Decrypting existing data
        - Verifying old signatures
        """
        archive_key = f"{key_id}_archived_{datetime.utcnow().timestamp()}"
        # Store in KMS or secure key vault
        pass

    def _schedule_reencryption(self, key_id: str, old_key: bytes, new_key: bytes):
        """
        Re-encrypt all data with new key (background job)

        Process:
        1. Find all records encrypted with old_key
        2. Decrypt with old_key
        3. Encrypt with new_key
        4. Update database

        Rate-limited to avoid overwhelming database
        """
        # In production: enqueue background job
        # job_queue.enqueue(reencrypt_data, key_id, old_key, new_key)
        pass

    def _log_rotation(self, key_id: str, rotation_count: int):
        """Log key rotation for audit"""
        print(f"Rotated key {key_id} (rotation #{rotation_count})")

# Example usage
from unittest.mock import Mock

kms = Mock()
kms.generate_data_key = Mock(return_value=os.urandom(32))

rotation_manager = KeyRotationManager(kms)

# Register key for automatic rotation
rotation_manager.register_key(
    key_id="master-key-1",
    rotation_period=timedelta(days=90)
)

# Check and rotate if needed (run daily via cron)
rotation_manager.rotate_key_if_needed("master-key-1")
```

### Compliance Requirements

**Encryption is not optional** for many industries:

**PCI-DSS** (Payment Card Industry):
- Encrypt cardholder data at rest (Requirement 3.4)
- Encrypt cardholder data in transit over public networks (Requirement 4.1)
- Use strong cryptography (AES-256, RSA-2048+)
- Rotate encryption keys annually (Requirement 3.6.4)

**HIPAA** (Healthcare):
- Encrypt electronic protected health information (ePHI) at rest and in transit
- Implement key management procedures
- Conduct annual risk assessments

**GDPR** (EU Data Protection):
- "Encryption of personal data" as a security measure (Article 32)
- Data breaches of unencrypted data require notification
- Data breaches of encrypted data (with keys safe) may not require notification

**SOC 2** (Service Organization Controls):
- Encryption in transit and at rest for sensitive data
- Key management and rotation procedures
- Access controls for encryption keys

**Cost of non-compliance**:
- **PCI-DSS violation**: $5,000-$100,000 per month in fines, loss of payment processing
- **HIPAA violation**: $100-$50,000 per violation, up to $1.5M per year
- **GDPR violation**: Up to 4% of global annual revenue or €20M (whichever is greater)

**Cost of compliance**:
- Enable encryption at rest: ~$0 (AWS S3 SSE, RDS encryption free)
- TLS everywhere: ~$0 (Let's Encrypt free, minimal CPU overhead)
- Key management: ~$1/key/month (AWS KMS), ~$1000/month (CloudHSM)
- **Total**: $1000-10,000/month for full encryption stack

**ROI**: Single data breach costs $4.35M average (IBM 2022). Encryption costs $10K-100K per year. The ROI is overwhelming.

## Mental Model: Encryption Everywhere

**The Core Principle**: Encrypt by default. Decrypt only when necessary. Discard keys immediately.

### Data States and Encryption

1. **Data in transit** → **TLS/SSL**
   - Client ↔ Server: HTTPS (TLS 1.3)
   - Service ↔ Service: mTLS (mutual authentication)
   - Database ↔ Application: TLS connection

2. **Data at rest** → **Encryption at rest**
   - Databases: Transparent Data Encryption (TDE)
   - Object storage: Server-side encryption (SSE)
   - Filesystems: Block-level encryption (LUKS, BitLocker)
   - Backups: Encrypted before storage

3. **Data in use** → **Memory encryption** (emerging)
   - Intel SGX (Software Guard Extensions)
   - AMD SEV (Secure Encrypted Virtualization)
   - Confidential computing (Azure, GCP)

### The Threat Model

**What encryption protects against**:
- Network eavesdropping (TLS)
- Stolen disks/backups (encryption at rest)
- Database dumps (field-level encryption)
- Insider threats (key separation, access controls)

**What encryption does NOT protect against**:
- Application vulnerabilities (SQL injection still works)
- Compromised application servers (keys in memory)
- Social engineering (phishing for credentials)
- Supply chain attacks (malicious libraries)

**Encryption is necessary but not sufficient**. It's one layer in defense-in-depth.

### When Encryption Is Not Enough

**Equifax breach (2017)**:
- Had encryption at rest: ✓
- But: Application vulnerability (Apache Struts) allowed SQL injection
- Attacker queried database with application credentials
- Database decrypted data (application requested it)
- Attacker exfiltrated plaintext

**Lesson**: Encryption protects data at the storage layer. Application security is still critical.

### Performance vs Security Trade-Off

**Decision framework**:

1. **Always encrypt in transit**: TLS overhead is negligible (< 1% CPU)
2. **Always encrypt at rest for sensitive data**: Credit cards, SSNs, health records, credentials
3. **Consider NOT encrypting**: Logs, metrics, non-sensitive operational data (if storage cost or performance matters)
4. **Use hardware acceleration**: AES-NI makes encryption nearly free

**Real-world choice**: Most companies encrypt everything by default (storage is cheap, breaches are expensive).

### Next Steps

Encryption protects data from external attackers. But distributed systems face another threat: **internal attackers and Byzantine failures**. Continue to [Byzantine Security](./byzantine-security.md) to understand malicious actors in distributed consensus.

