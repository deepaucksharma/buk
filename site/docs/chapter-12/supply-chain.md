# Supply Chain Security: Trust from Source to Production

## Introduction: The SolarWinds Catastrophe

On December 13, 2020, FireEye announced they had been hacked. The attackers stole Red Team tools—sophisticated hacking software used to test client security.

This was not a typical breach. The investigation revealed something far worse.

**The attack vector**: Between March and June 2020, attackers compromised SolarWinds' build system and injected malicious code into the Orion software update mechanism. That malicious update was:
- Digitally signed with SolarWinds' legitimate certificate
- Passed all security checks
- Automatically deployed to 18,000 customers via auto-update

**The victims**:
- Fortune 500 companies: Microsoft, Cisco, Intel, Nvidia, VMware
- US Government agencies: Treasury, State, Homeland Security, Pentagon, DOE
- Critical infrastructure operators worldwide

**The compromise depth**: Attackers had access for 9+ months before detection. They pivoted from SolarWinds to customer networks, stealing emails, source code, and classified information.

**The cost**:
- SolarWinds: $3.5B market cap loss, $100M+ remediation costs
- Victims: Unknown (likely billions in collective damage)
- National security: Immeasurable

**The lesson**: You can have perfect application security, network security, and encryption—but if your **supply chain** is compromised, none of it matters. The software you trust is the software that destroys you.

### What Is Supply Chain Security?

**Supply chain security** protects the entire lifecycle from source code to production:

1. **Source code**: Who committed it? Was it reviewed? Is it malicious?
2. **Dependencies**: What libraries do you use? Are they trustworthy? Are they compromised?
3. **Build process**: Where is code compiled? Can attackers inject malware during build?
4. **Artifacts**: Are container images, binaries, and packages tamper-proof?
5. **Deployment**: Does production run exactly what was built? No modifications?

**Traditional security** focuses on runtime: firewalls, intrusion detection, encryption.

**Supply chain security** focuses on provenance: trust the code before you run it.

### Why Supply Chain Attacks Are Increasing

**2015-2020**: Supply chain attacks increased by 430% (Sonatype 2021)

**Why**:
1. **Software dependencies are massive**: Average application has 200+ dependencies (npm), 500+ transitive dependencies
2. **Open source is everywhere**: 90%+ of applications use open-source libraries
3. **Automated pipelines**: CI/CD deploys code from source to production in minutes
4. **Single point of failure**: Compromise one popular library → compromise thousands of applications

**High-profile attacks**:
- **SolarWinds (2020)**: Build system compromised, 18,000 customers affected
- **Codecov (2021)**: Bash Uploader script compromised, customer CI/CD credentials stolen
- **Log4Shell (2021)**: Zero-day in Log4j library, billions of devices vulnerable
- **Event-stream (2018)**: npm package compromised, Bitcoin wallets targeted
- **ua-parser-js (2021)**: npm package hijacked, cryptocurrency miner injected

## Part 1: Dependency Management

### The Dependency Problem

Modern applications are built on hundreds of dependencies:

```python
# Example: A simple Python web application
import flask            # Web framework
import sqlalchemy       # Database ORM
import requests         # HTTP client
import jwt              # JSON Web Tokens
import bcrypt           # Password hashing
import redis            # Caching
import celery           # Background tasks
import prometheus_client # Metrics

# Each of these has its own dependencies (transitive dependencies)
# requests → urllib3 → cryptography → cffi → pycparser
# sqlalchemy → greenlet
# celery → kombu → amqp
```

**Total dependencies**: 20-30 direct dependencies → 200-300 transitive dependencies

**The risk**: Any one of these dependencies can be compromised. You're trusting hundreds of maintainers you've never met.

### Dependency Attacks: Real Examples

**Event-stream (2018)**:
- Popular npm package (2M downloads/week)
- Attacker gained maintainer access through social engineering
- Injected malicious code targeting Bitcoin wallets
- Stole cryptocurrency from users

**ua-parser-js (2021)**:
- npm package with 8M downloads/week
- Attacker hijacked maintainer account (weak password)
- Published versions with cryptocurrency miner and password stealer
- Millions of applications compromised

**Left-pad (2016)**:
- Developer removed 11-line npm package from registry
- Broke thousands of applications that depended on it
- Demonstrated fragility of npm ecosystem

### Dependency Security Scanning

**Step 1**: Know what you depend on.

```python
import subprocess
import json
from typing import List, Dict, Set
from dataclasses import dataclass
from packaging.version import parse as parse_version

@dataclass
class Dependency:
    """A software dependency"""
    name: str
    version: str
    direct: bool  # Direct dependency or transitive?

@dataclass
class Vulnerability:
    """Security vulnerability in dependency"""
    cve_id: str
    package: str
    affected_versions: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    fixed_version: str

class DependencyScanner:
    """
    Scan dependencies for security vulnerabilities

    Tools:
    - npm audit (Node.js)
    - pip-audit (Python)
    - Dependabot (GitHub)
    - Snyk
    - OWASP Dependency-Check
    """

    def __init__(self, project_path: str):
        self.project_path = project_path

    def scan_python_dependencies(self) -> List[Dependency]:
        """
        Scan Python dependencies using pip

        Returns: List of all dependencies (direct + transitive)
        """
        # Get installed packages
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            cwd=self.project_path,
            capture_output=True,
            text=True
        )

        packages = json.loads(result.stdout)

        # Get dependency tree
        result = subprocess.run(
            ["pipdeptree", "--json"],
            cwd=self.project_path,
            capture_output=True,
            text=True
        )

        dep_tree = json.loads(result.stdout)

        dependencies = []

        for pkg in dep_tree:
            # Direct dependency
            dependencies.append(Dependency(
                name=pkg["package"]["key"],
                version=pkg["package"]["installed_version"],
                direct=True
            ))

            # Transitive dependencies
            for dep in pkg["dependencies"]:
                dependencies.append(Dependency(
                    name=dep["key"],
                    version=dep["installed_version"],
                    direct=False
                ))

        return dependencies

    def check_vulnerabilities(self, dependencies: List[Dependency]) -> List[Vulnerability]:
        """
        Check dependencies for known vulnerabilities

        Uses: pip-audit, which queries PyPI's vulnerability database
        """
        result = subprocess.run(
            ["pip-audit", "--format=json"],
            cwd=self.project_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Vulnerabilities found
            audit_results = json.loads(result.stdout)

            vulnerabilities = []

            for vuln in audit_results.get("vulnerabilities", []):
                vulnerabilities.append(Vulnerability(
                    cve_id=vuln["id"],
                    package=vuln["name"],
                    affected_versions=vuln["version"],
                    severity=vuln.get("severity", "UNKNOWN"),
                    description=vuln["description"],
                    fixed_version=vuln.get("fixed_version", "None")
                ))

            return vulnerabilities

        return []

    def generate_sbom(self, dependencies: List[Dependency]) -> dict:
        """
        Generate Software Bill of Materials (SBOM)

        SBOM: Complete inventory of software components
        Standards: SPDX, CycloneDX
        """
        sbom = {
            "version": "1.0",
            "project": self.project_path,
            "timestamp": "2024-01-01T00:00:00Z",
            "dependencies": [
                {
                    "name": dep.name,
                    "version": dep.version,
                    "direct": dep.direct,
                    "purl": f"pkg:pypi/{dep.name}@{dep.version}"  # Package URL
                }
                for dep in dependencies
            ]
        }

        return sbom

    def check_license_compliance(self, dependencies: List[Dependency]) -> List[str]:
        """
        Check dependency licenses for compliance

        Some licenses (GPL) require releasing source code
        Corporate policies may ban certain licenses
        """
        # Query package metadata for licenses
        result = subprocess.run(
            ["pip-licenses", "--format=json"],
            cwd=self.project_path,
            capture_output=True,
            text=True
        )

        licenses = json.loads(result.stdout)

        # Banned licenses (example: GPL requires source release)
        banned = ["GPL-2.0", "GPL-3.0", "AGPL-3.0"]

        violations = []

        for pkg in licenses:
            if pkg["License"] in banned:
                violations.append(
                    f"{pkg['Name']} uses banned license: {pkg['License']}"
                )

        return violations

# Example usage
scanner = DependencyScanner("/path/to/project")

# Scan dependencies
dependencies = scanner.scan_python_dependencies()
print(f"Found {len(dependencies)} dependencies")

# Check for vulnerabilities
vulnerabilities = scanner.check_vulnerabilities(dependencies)
if vulnerabilities:
    print(f"Found {len(vulnerabilities)} vulnerabilities:")
    for vuln in vulnerabilities:
        print(f"  {vuln.cve_id}: {vuln.package} ({vuln.severity})")
        print(f"    Fix: Upgrade to {vuln.fixed_version}")

# Generate SBOM
sbom = scanner.generate_sbom(dependencies)
print(f"SBOM: {len(sbom['dependencies'])} components")

# Check license compliance
violations = scanner.check_license_compliance(dependencies)
if violations:
    print("License violations:")
    for violation in violations:
        print(f"  {violation}")
```

### Dependency Pinning and Lock Files

**Problem**: Unpinned dependencies can change without warning.

```python
# requirements.txt (BAD - no version pinning)
flask
sqlalchemy
requests

# Attacker publishes flask 3.0.0 with malicious code
# Next time you run "pip install -r requirements.txt", you get malware
```

**Solution**: Lock files specify exact versions.

```python
# requirements.txt (BETTER - version pinning)
flask==2.3.3
sqlalchemy==2.0.20
requests==2.31.0

# requirements.lock (BEST - includes transitive dependencies)
flask==2.3.3
  werkzeug==2.3.7
  jinja2==3.1.2
    markupsafe==2.1.3
  click==8.1.7
  itsdangerous==2.1.2
sqlalchemy==2.0.20
  greenlet==2.0.2
requests==2.31.0
  urllib3==2.0.4
  certifi==2023.7.22
  charset-normalizer==3.2.0
  idna==3.4
```

**Lock file generation**:
```python
class LockFileGenerator:
    """Generate lock files for reproducible builds"""

    def generate_python_lock(self, requirements_file: str) -> str:
        """
        Generate Python lock file using pip-compile

        pip-compile: Resolves dependencies and pins exact versions
        """
        result = subprocess.run(
            ["pip-compile", requirements_file, "--output-file", "requirements.lock"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("Lock file generated: requirements.lock")
            return "requirements.lock"
        else:
            print(f"Error generating lock file: {result.stderr}")
            return None

    def verify_lock_file(self, lock_file: str) -> bool:
        """
        Verify lock file matches current environment

        Detects if dependencies have changed since lock file was created
        """
        result = subprocess.run(
            ["pip-sync", "--dry-run", lock_file],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("Lock file matches current environment")
            return True
        else:
            print(f"Lock file out of sync: {result.stderr}")
            return False
```

### Private Package Repositories

**Problem**: Public registries (npm, PyPI) can be compromised.

**Solution**: Host internal packages in private registry.

```python
class PrivatePackageRegistry:
    """
    Private package registry for internal dependencies

    Benefits:
    - Control over package availability
    - Vulnerability scanning before allowing packages
    - Audit trail for package downloads
    - Offline operation (air-gapped environments)

    Tools:
    - Artifactory (JFrog)
    - Nexus (Sonatype)
    - PyPI server (Python)
    - Verdaccio (npm)
    """

    def __init__(self, registry_url: str):
        self.registry_url = registry_url

    def mirror_public_package(self, package_name: str, version: str):
        """
        Mirror public package to private registry

        Workflow:
        1. Download package from public registry (PyPI, npm)
        2. Scan for vulnerabilities
        3. Scan for malicious code
        4. If clean, upload to private registry
        5. Block direct access to public registry
        """
        # Download from public registry
        public_url = f"https://pypi.org/pypi/{package_name}/{version}/json"
        # ... download package

        # Scan for vulnerabilities
        vulnerabilities = self._scan_vulnerabilities(package_name, version)
        if vulnerabilities:
            print(f"Package {package_name}=={version} has vulnerabilities - not mirroring")
            return False

        # Scan for malicious code
        if self._scan_malicious_code(package_name, version):
            print(f"Package {package_name}=={version} contains malicious code - blocked")
            return False

        # Upload to private registry
        self._upload_to_private_registry(package_name, version)
        print(f"Package {package_name}=={version} mirrored successfully")
        return True

    def _scan_vulnerabilities(self, package_name: str, version: str) -> List[Vulnerability]:
        """Scan package for known vulnerabilities"""
        # Use pip-audit, Snyk, or OWASP Dependency-Check
        pass

    def _scan_malicious_code(self, package_name: str, version: str) -> bool:
        """
        Scan package for malicious code

        Techniques:
        - Static analysis (suspicious imports, obfuscated code)
        - Dynamic analysis (run in sandbox, monitor behavior)
        - Reputation scoring (new maintainer, sudden changes)
        """
        pass

    def _upload_to_private_registry(self, package_name: str, version: str):
        """Upload package to private registry"""
        pass
```

## Part 2: Software Bill of Materials (SBOM)

### What Is an SBOM?

**SBOM**: Complete inventory of software components, dependencies, and metadata.

**Think of it as**: Ingredient list for software (like nutrition labels on food).

**Why it matters**:
1. **Vulnerability response**: When Log4Shell was announced, companies with SBOMs identified affected systems in hours. Companies without SBOMs took weeks.
2. **License compliance**: Know which licenses you're using
3. **Supply chain transparency**: Understand your attack surface
4. **Regulatory compliance**: US Executive Order 14028 requires SBOMs for government software

### SBOM Standards

**SPDX** (Software Package Data Exchange):
- Linux Foundation standard
- ISO/IEC 5962:2021
- Machine-readable format (JSON, YAML, XML)

**CycloneDX**:
- OWASP standard
- Focused on security use cases
- Includes vulnerability data

### Generating SBOMs

```python
import json
import hashlib
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass, asdict

@dataclass
class Component:
    """SBOM component (package or library)"""
    name: str
    version: str
    type: str  # library, framework, application, operating-system, etc.
    purl: str  # Package URL (universal identifier)
    supplier: str
    licenses: List[str]
    hashes: Dict[str, str]  # SHA-256, SHA-512

class SBOMGenerator:
    """
    Generate Software Bill of Materials

    Standards: SPDX, CycloneDX
    """

    def __init__(self, project_name: str, project_version: str):
        self.project_name = project_name
        self.project_version = project_version

    def generate_cyclonedx_sbom(self, components: List[Component]) -> dict:
        """
        Generate SBOM in CycloneDX format

        CycloneDX schema: https://cyclonedx.org/schema/
        """
        sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "version": 1,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "component": {
                    "type": "application",
                    "name": self.project_name,
                    "version": self.project_version
                }
            },
            "components": [
                {
                    "type": comp.type,
                    "name": comp.name,
                    "version": comp.version,
                    "purl": comp.purl,
                    "supplier": {"name": comp.supplier},
                    "licenses": [{"license": {"id": lic}} for lic in comp.licenses],
                    "hashes": [
                        {"alg": alg.upper(), "content": hash_value}
                        for alg, hash_value in comp.hashes.items()
                    ]
                }
                for comp in components
            ]
        }

        return sbom

    def generate_spdx_sbom(self, components: List[Component]) -> dict:
        """
        Generate SBOM in SPDX format

        SPDX schema: https://spdx.github.io/spdx-spec/
        """
        sbom = {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": f"{self.project_name}-{self.project_version}",
            "documentNamespace": f"https://example.com/sbom/{self.project_name}-{self.project_version}",
            "creationInfo": {
                "created": datetime.utcnow().isoformat() + "Z",
                "creators": ["Tool: SBOM Generator"]
            },
            "packages": [
                {
                    "SPDXID": f"SPDXRef-{comp.name}",
                    "name": comp.name,
                    "versionInfo": comp.version,
                    "supplier": f"Organization: {comp.supplier}",
                    "licenseConcluded": " OR ".join(comp.licenses) if comp.licenses else "NOASSERTION",
                    "checksums": [
                        {"algorithm": alg.upper(), "checksumValue": hash_value}
                        for alg, hash_value in comp.hashes.items()
                    ],
                    "externalRefs": [
                        {
                            "referenceCategory": "PACKAGE-MANAGER",
                            "referenceType": "purl",
                            "referenceLocator": comp.purl
                        }
                    ]
                }
                for comp in components
            ]
        }

        return sbom

    def compute_package_hash(self, package_path: str) -> Dict[str, str]:
        """
        Compute cryptographic hashes of package

        Multiple algorithms for different use cases:
        - SHA-256: Standard security hash
        - SHA-512: Higher security (larger hash)
        """
        hashes = {}

        with open(package_path, "rb") as f:
            data = f.read()

        hashes["sha256"] = hashlib.sha256(data).hexdigest()
        hashes["sha512"] = hashlib.sha512(data).hexdigest()

        return hashes

# Example: Generate SBOM
generator = SBOMGenerator(
    project_name="my-application",
    project_version="1.0.0"
)

components = [
    Component(
        name="flask",
        version="2.3.3",
        type="library",
        purl="pkg:pypi/flask@2.3.3",
        supplier="Pallets",
        licenses=["BSD-3-Clause"],
        hashes={
            "sha256": "09c347a92aa7ff4a8e7f3206795f30d826654baf38b873d0744cd571ca609efc"
        }
    ),
    Component(
        name="sqlalchemy",
        version="2.0.20",
        type="library",
        purl="pkg:pypi/sqlalchemy@2.0.20",
        supplier="SQLAlchemy",
        licenses=["MIT"],
        hashes={
            "sha256": "ca8a5ff2aa7f3ade6c498aaafce25b1eaeabe4e42b73e25519183e4566a16fc6"
        }
    )
]

# Generate CycloneDX SBOM
sbom = generator.generate_cyclonedx_sbom(components)
print(json.dumps(sbom, indent=2))

# Save to file
with open("sbom.json", "w") as f:
    json.dump(sbom, f, indent=2)
```

### Using SBOMs for Vulnerability Response

**Scenario**: Log4Shell vulnerability announced (CVE-2021-44228).

**Without SBOM**: Manually search all repositories, deployments, containers for log4j usage. Takes days-weeks.

**With SBOM**: Query all SBOMs for log4j references. Identify affected systems in minutes.

```python
class SBOMVulnerabilityScanner:
    """
    Scan SBOMs for vulnerabilities

    Use case: Rapid response to new vulnerabilities (Log4Shell, etc.)
    """

    def __init__(self):
        self.sboms: List[dict] = []

    def load_sboms(self, sbom_directory: str):
        """Load all SBOMs from directory"""
        import os
        for filename in os.listdir(sbom_directory):
            if filename.endswith(".json"):
                with open(os.path.join(sbom_directory, filename)) as f:
                    self.sboms.append(json.load(f))

    def find_vulnerable_components(
        self,
        package_name: str,
        vulnerable_versions: List[str]
    ) -> List[Dict]:
        """
        Find all systems using vulnerable versions of package

        Example: Log4Shell
        - package_name: "log4j-core"
        - vulnerable_versions: ["2.0", "2.1", ..., "2.14.1"]
        """
        affected_systems = []

        for sbom in self.sboms:
            system_name = sbom["metadata"]["component"]["name"]
            system_version = sbom["metadata"]["component"]["version"]

            for component in sbom["components"]:
                if component["name"] == package_name:
                    if component["version"] in vulnerable_versions:
                        affected_systems.append({
                            "system": system_name,
                            "system_version": system_version,
                            "vulnerable_component": component["name"],
                            "vulnerable_version": component["version"]
                        })

        return affected_systems

# Example: Respond to Log4Shell
scanner = SBOMVulnerabilityScanner()
scanner.load_sboms("/path/to/sboms")

# Find all systems with vulnerable log4j
vulnerable_versions = [f"2.{i}" for i in range(15)]  # 2.0 through 2.14
affected = scanner.find_vulnerable_components("log4j-core", vulnerable_versions)

print(f"Found {len(affected)} systems affected by Log4Shell:")
for system in affected:
    print(f"  {system['system']} v{system['system_version']}: log4j {system['vulnerable_version']}")
```

## Part 3: Container Security Scanning

### The Container Security Problem

**Containers package entire runtime**: Application code + dependencies + OS libraries + base image.

**Attack surface**:
1. **Base image**: Ubuntu, Alpine, etc. may have vulnerabilities
2. **OS packages**: apt/yum packages may be outdated
3. **Application dependencies**: npm/pip packages may be vulnerable
4. **Application code**: Your own code may have bugs

**Example vulnerable container**:
```dockerfile
FROM ubuntu:18.04  # Outdated OS (missing security patches)

RUN apt-get update && apt-get install -y \
    python3.6 \  # Outdated Python (CVE-2020-8492)
    openssl   # Outdated OpenSSL (Heartbleed?)

COPY requirements.txt .
RUN pip3 install -r requirements.txt  # Vulnerable dependencies?

COPY app.py .
CMD ["python3", "app.py"]
```

### Container Scanning Tools

**Tools**:
- **Trivy** (Aqua Security): Open-source, comprehensive scanner
- **Grype** (Anchore): Open-source vulnerability scanner
- **Clair** (Quay): Open-source static analysis
- **Snyk Container**: Commercial scanner
- **Docker Scout**: Docker's built-in scanner

```python
import subprocess
import json
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class ContainerVulnerability:
    """Vulnerability in container image"""
    cve_id: str
    package: str
    version: str
    severity: str
    fixed_version: str
    description: str

class ContainerScanner:
    """
    Scan container images for vulnerabilities

    Uses: Trivy (open-source scanner)
    """

    def scan_image(self, image_name: str) -> List[ContainerVulnerability]:
        """
        Scan container image for vulnerabilities

        Trivy scans:
        - OS packages (apt, yum, apk)
        - Application dependencies (npm, pip, gem, etc.)
        - Known CVEs in base images
        """
        result = subprocess.run(
            [
                "trivy", "image",
                "--format", "json",
                "--severity", "HIGH,CRITICAL",  # Only show serious vulnerabilities
                image_name
            ],
            capture_output=True,
            text=True
        )

        scan_results = json.loads(result.stdout)

        vulnerabilities = []

        for target in scan_results.get("Results", []):
            for vuln in target.get("Vulnerabilities", []):
                vulnerabilities.append(ContainerVulnerability(
                    cve_id=vuln["VulnerabilityID"],
                    package=vuln["PkgName"],
                    version=vuln["InstalledVersion"],
                    severity=vuln["Severity"],
                    fixed_version=vuln.get("FixedVersion", "No fix available"),
                    description=vuln.get("Description", "")
                ))

        return vulnerabilities

    def scan_and_block(self, image_name: str) -> bool:
        """
        Scan image and block deployment if critical vulnerabilities found

        Policy: Block if any CRITICAL severity vulnerabilities
        """
        vulnerabilities = self.scan_image(image_name)

        critical_vulns = [
            v for v in vulnerabilities
            if v.severity == "CRITICAL"
        ]

        if critical_vulns:
            print(f"BLOCKING deployment of {image_name}")
            print(f"Found {len(critical_vulns)} CRITICAL vulnerabilities:")
            for vuln in critical_vulns:
                print(f"  {vuln.cve_id}: {vuln.package} {vuln.version}")
                print(f"    Fix: Upgrade to {vuln.fixed_version}")
            return False

        print(f"ALLOWING deployment of {image_name}")
        print(f"No CRITICAL vulnerabilities found")
        return True

    def generate_container_sbom(self, image_name: str) -> dict:
        """
        Generate SBOM for container image

        Includes all packages in all layers
        """
        result = subprocess.run(
            [
                "syft", image_name,
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )

        sbom = json.loads(result.stdout)
        return sbom

# Example: Scan container before deployment
scanner = ContainerScanner()

image = "myapp:latest"

# Scan for vulnerabilities
vulnerabilities = scanner.scan_image(image)
print(f"Found {len(vulnerabilities)} vulnerabilities in {image}")

# Block deployment if critical vulnerabilities
allowed = scanner.scan_and_block(image)

if allowed:
    # Deploy to production
    subprocess.run(["kubectl", "apply", "-f", "deployment.yaml"])
else:
    # Alert team to fix vulnerabilities
    print("Fix vulnerabilities before deploying")
```

### Minimal Base Images

**Problem**: Ubuntu base image is 72MB, includes hundreds of packages, large attack surface.

**Solution**: Use minimal base images (Alpine, distroless).

```dockerfile
# BAD: Large attack surface
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3 python3-pip
COPY app.py .
CMD ["python3", "app.py"]

# BETTER: Minimal base image (Alpine)
FROM python:3.11-alpine
COPY app.py .
CMD ["python3", "app.py"]

# BEST: Distroless (no shell, no package manager)
FROM gcr.io/distroless/python3
COPY app.py .
CMD ["python3", "app.py"]
```

**Size comparison**:
- Ubuntu base: 72 MB
- Alpine base: 5 MB (14× smaller)
- Distroless: 50 MB (but no shell, no package manager)

**Security comparison**:
- Ubuntu: 100+ packages, many unnecessary (bash, coreutils, etc.)
- Alpine: 20+ packages, minimal utilities
- Distroless: 10 packages, only runtime dependencies

**Trade-offs**:
- Alpine: Smaller, but uses musl libc (compatibility issues with some software)
- Distroless: Most secure, but debugging is hard (no shell)

## Part 4: Image Signing and Attestation

### The Trust Problem

**Problem**: How do you know the container image running in production is the one you built?

**Attack scenarios**:
1. **Registry compromise**: Attacker modifies image in container registry
2. **Man-in-the-middle**: Attacker intercepts image pull, serves malicious image
3. **Insider threat**: Malicious developer pushes backdoored image

**Solution**: **Image signing** — cryptographically sign images, verify signatures before running.

### Cosign and Sigstore

**Sigstore**: Open-source project for software signing and transparency.

**Cosign**: Tool for signing and verifying container images.

**How it works**:
1. Build container image
2. Sign image with private key
3. Store signature in container registry (alongside image)
4. Before deployment, verify signature with public key
5. Only run signed images

```python
import subprocess
from typing import Optional

class ImageSigner:
    """
    Sign and verify container images using Cosign

    Provides:
    - Cryptographic proof of image origin
    - Protection against tampering
    - Audit trail (who signed what, when)
    """

    def __init__(self, private_key_path: str, public_key_path: str):
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path

    def sign_image(self, image_name: str) -> bool:
        """
        Sign container image with private key

        Signature stored in container registry alongside image
        """
        result = subprocess.run(
            [
                "cosign", "sign",
                "--key", self.private_key_path,
                image_name
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"Image {image_name} signed successfully")
            return True
        else:
            print(f"Failed to sign image: {result.stderr}")
            return False

    def verify_image(self, image_name: str) -> bool:
        """
        Verify image signature before deployment

        If signature is invalid or missing, block deployment
        """
        result = subprocess.run(
            [
                "cosign", "verify",
                "--key", self.public_key_path,
                image_name
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"Image {image_name} signature verified")
            return True
        else:
            print(f"Image signature verification FAILED: {result.stderr}")
            return False

    def generate_attestation(self, image_name: str, metadata: dict) -> bool:
        """
        Generate attestation for image

        Attestation: Statement about image (who built it, when, from what source)

        Includes:
        - Build timestamp
        - Git commit hash
        - Builder identity
        - Build environment
        """
        import json
        import tempfile

        # Create attestation payload
        attestation = {
            "image": image_name,
            "builder": metadata.get("builder", "unknown"),
            "timestamp": metadata.get("timestamp"),
            "commit": metadata.get("commit_hash"),
            "branch": metadata.get("branch"),
            "repository": metadata.get("repository")
        }

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(attestation, f)
            attestation_file = f.name

        # Sign attestation
        result = subprocess.run(
            [
                "cosign", "attest",
                "--key", self.private_key_path,
                "--predicate", attestation_file,
                image_name
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"Attestation generated for {image_name}")
            return True
        else:
            print(f"Failed to generate attestation: {result.stderr}")
            return False

    def verify_attestation(self, image_name: str) -> Optional[dict]:
        """
        Verify and retrieve attestation

        Used for:
        - Auditing (who built this image?)
        - Compliance (was this built from approved source?)
        - Debugging (what commit does this image correspond to?)
        """
        result = subprocess.run(
            [
                "cosign", "verify-attestation",
                "--key", self.public_key_path,
                image_name
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Parse attestation
            import json
            attestation = json.loads(result.stdout)
            return attestation
        else:
            print(f"Attestation verification failed: {result.stderr}")
            return None

# Example: Sign and verify image
signer = ImageSigner(
    private_key_path="/path/to/private.key",
    public_key_path="/path/to/public.key"
)

image = "myregistry.com/myapp:v1.0.0"

# After building image, sign it
signer.sign_image(image)

# Generate build attestation
metadata = {
    "builder": "jenkins",
    "timestamp": "2024-01-01T12:00:00Z",
    "commit_hash": "abc123def456",
    "branch": "main",
    "repository": "github.com/company/myapp"
}
signer.generate_attestation(image, metadata)

# Before deployment, verify signature
if signer.verify_image(image):
    # Signature valid - deploy
    subprocess.run(["kubectl", "set", "image", "deployment/myapp", f"myapp={image}"])
else:
    # Signature invalid - block deployment
    print("Deployment blocked: invalid image signature")
```

### Admission Controllers (Kubernetes)

**Problem**: How do you enforce image signing policy across entire cluster?

**Solution**: **Admission controller** — validates all pod creation requests, blocks unsigned images.

```python
class KubernetesAdmissionController:
    """
    Kubernetes Admission Controller for image signing

    Enforces policy:
    - All images must be signed with trusted key
    - All images must pass vulnerability scan
    - All images must come from approved registries

    Implementation: ValidatingWebhookConfiguration
    """

    def __init__(self, trusted_keys: List[str], allowed_registries: List[str]):
        self.trusted_keys = trusted_keys
        self.allowed_registries = allowed_registries
        self.signer = ImageSigner(
            private_key_path="/path/to/key",
            public_key_path="/path/to/key.pub"
        )

    def validate_pod_creation(self, pod_spec: dict) -> tuple[bool, str]:
        """
        Validate pod creation request

        Called by Kubernetes API server before creating pod
        Returns: (allowed: bool, reason: str)
        """
        containers = pod_spec.get("spec", {}).get("containers", [])

        for container in containers:
            image = container["image"]

            # Check 1: Image from allowed registry?
            if not self._is_allowed_registry(image):
                return False, f"Image {image} from untrusted registry"

            # Check 2: Image signature valid?
            if not self.signer.verify_image(image):
                return False, f"Image {image} has invalid signature"

            # Check 3: Image passed vulnerability scan?
            scanner = ContainerScanner()
            if not scanner.scan_and_block(image):
                return False, f"Image {image} has critical vulnerabilities"

        return True, "All validation checks passed"

    def _is_allowed_registry(self, image: str) -> bool:
        """Check if image is from allowed registry"""
        for registry in self.allowed_registries:
            if image.startswith(registry):
                return True
        return False

# Example: Deploy admission controller
controller = KubernetesAdmissionController(
    trusted_keys=["/path/to/public.key"],
    allowed_registries=["myregistry.com", "gcr.io/myproject"]
)

# Kubernetes calls this webhook for every pod creation
pod_spec = {
    "spec": {
        "containers": [
            {"image": "myregistry.com/myapp:v1.0.0"}
        ]
    }
}

allowed, reason = controller.validate_pod_creation(pod_spec)
if allowed:
    print("Pod creation allowed")
else:
    print(f"Pod creation DENIED: {reason}")
```

## Part 5: CI/CD Security

### The CI/CD Attack Surface

**CI/CD pipelines** have privileged access to:
- Source code repositories
- Container registries
- Production infrastructure
- Secrets (API keys, credentials)

**Attack scenarios**:
1. **Compromised CI/CD credentials**: Attacker gains access to Jenkins, pushes malicious code to production
2. **Poisoned pipeline**: Attacker modifies CI/CD config (Jenkinsfile, .gitlab-ci.yml) to inject malware
3. **Dependency confusion**: Attacker publishes malicious package with same name as internal package, CI/CD downloads attacker's version

### Securing CI/CD Pipelines

```python
class SecureCI CD:
    """
    Secure CI/CD pipeline implementation

    Security principles:
    1. Least privilege (minimal permissions)
    2. Immutable infrastructure (rebuild, don't patch)
    3. Attestation (sign all artifacts)
    4. Audit logging (log all build steps)
    5. Secrets management (never hardcode secrets)
    """

    def __init__(self):
        self.scanner = ContainerScanner()
        self.signer = ImageSigner(
            private_key_path="/path/to/ci-key",
            public_key_path="/path/to/ci-key.pub"
        )

    def secure_build_pipeline(self, git_repo: str, commit_hash: str):
        """
        Secure build pipeline

        Steps:
        1. Clone source code (verify commit signature)
        2. Scan dependencies for vulnerabilities
        3. Build container image
        4. Scan image for vulnerabilities
        5. Sign image
        6. Generate SBOM
        7. Generate attestation
        8. Push to registry
        """
        # Step 1: Clone and verify
        if not self._verify_commit_signature(git_repo, commit_hash):
            raise Exception("Commit signature verification failed")

        # Step 2: Dependency scan
        scanner = DependencyScanner(f"/tmp/{git_repo}")
        vulnerabilities = scanner.check_vulnerabilities([])
        if vulnerabilities:
            raise Exception(f"Found {len(vulnerabilities)} vulnerabilities in dependencies")

        # Step 3: Build image
        image_name = f"myregistry.com/{git_repo}:{commit_hash[:8]}"
        self._build_image(git_repo, image_name)

        # Step 4: Container scan
        if not self.scanner.scan_and_block(image_name):
            raise Exception("Container scan failed")

        # Step 5: Sign image
        if not self.signer.sign_image(image_name):
            raise Exception("Image signing failed")

        # Step 6: Generate SBOM
        sbom_generator = SBOMGenerator(git_repo, commit_hash)
        # ... generate SBOM

        # Step 7: Generate attestation
        metadata = {
            "builder": "github-actions",
            "commit_hash": commit_hash,
            "repository": git_repo,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.signer.generate_attestation(image_name, metadata)

        # Step 8: Push to registry
        self._push_image(image_name)

        print(f"Build successful: {image_name}")

    def _verify_commit_signature(self, repo: str, commit: str) -> bool:
        """Verify Git commit signature (GPG-signed commits)"""
        result = subprocess.run(
            ["git", "verify-commit", commit],
            cwd=f"/tmp/{repo}",
            capture_output=True
        )
        return result.returncode == 0

    def _build_image(self, repo: str, image_name: str):
        """Build container image"""
        subprocess.run(
            ["docker", "build", "-t", image_name, "."],
            cwd=f"/tmp/{repo}"
        )

    def _push_image(self, image_name: str):
        """Push image to registry"""
        subprocess.run(["docker", "push", image_name])

# Example: Secure CI/CD pipeline
pipeline = SecureCI CD()

try:
    pipeline.secure_build_pipeline(
        git_repo="myapp",
        commit_hash="abc123def456"
    )
except Exception as e:
    print(f"Build failed: {e}")
    # Alert team, block deployment
```

## Mental Model: Supply Chain Security in Practice

**The Core Principle**: Trust, but verify. At every stage, from source to production.

### The Trust Chain

```
1. Source Code
   → Verify: Commit signatures (GPG)
   → Threat: Compromised developer account

2. Dependencies
   → Verify: Dependency scanning, SBOM
   → Threat: Malicious packages (npm, PyPI)

3. Build Process
   → Verify: Reproducible builds, attestation
   → Threat: Compromised CI/CD (SolarWinds)

4. Artifacts (Images, Binaries)
   → Verify: Image signing (Cosign), vulnerability scanning
   → Threat: Registry compromise

5. Deployment
   → Verify: Admission controller, signature verification
   → Threat: Man-in-the-middle, insider threat

6. Runtime
   → Verify: Runtime security (Falco, Seccomp)
   → Threat: Container escape, privilege escalation
```

### When Supply Chain Security Matters Most

**High-risk scenarios**:
1. **Financial services**: Attackers target payment systems
2. **Healthcare**: Patient data is valuable
3. **Government**: Nation-state adversaries
4. **Open-source maintainers**: Popular packages are targets (event-stream, ua-parser-js)

**Lower-risk scenarios**:
1. **Internal tools**: Smaller attack surface
2. **Prototype applications**: Not production-critical

**Decision framework**:
- **Critical systems**: Full supply chain security (SBOM, signing, scanning)
- **Important systems**: Dependency scanning + container scanning
- **Internal tools**: Basic dependency scanning

### The Cost-Benefit Analysis

**Cost of supply chain security**:
- **Tooling**: Trivy (free), Snyk ($100-1000/month), Artifactory ($5000+/year)
- **Engineering time**: 10-20% overhead on CI/CD pipeline
- **Operational complexity**: Managing keys, SBOMs, attestations

**Cost of supply chain breach**:
- **SolarWinds**: $3.5B+ market cap loss, immeasurable reputation damage
- **Codecov**: Customer credentials stolen, unknown impact
- **Event-stream**: Millions of applications compromised

**ROI**: Supply chain security costs $10K-100K/year. A single breach costs $1M-1B+. The ROI is overwhelming for any production system.

### Next Steps

Congratulations! You've completed the security chapter. You now understand:
- **Zero trust**: Identity-based security, mTLS, microsegmentation
- **Encryption**: TLS at scale, encryption at rest, key management
- **Byzantine security**: Defending against malicious actors in distributed consensus
- **Supply chain**: SBOM, image signing, dependency scanning

**Continue to Chapter 13** to explore the next topic in distributed systems.

