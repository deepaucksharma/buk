# Facebook's BGP Outage: The Day the Internet Forgot Facebook Existed

## The Incident: October 4, 2021, 15:39 UTC

> "We didn't just go offline. We vanished. Every Facebook IP address disappeared from the global routing tables. It was as if we had never existed on the internet. And the irony? We couldn't access our own systems to fix it."

At 15:39 UTC on October 4, 2021, a routine maintenance operation on Facebook's backbone network triggered a BGP configuration audit. The audit detected what it thought was an error and executed its safety mechanism: withdraw ALL BGP route advertisements for Facebook, Instagram, and WhatsApp from the global internet.

Within seconds, Facebook's IP addresses became unreachable worldwide. Within minutes, the cascading effects began: DNS servers couldn't be reached (they were inside the unreachable network). Remote access systems couldn't be reached. Monitoring systems couldn't be reached. The engineers who could fix the problem couldn't access the systems that needed fixing.

This was not just an outage. This was a **lock-out scenario** where the safety mechanism designed to prevent bad configurations instead created an unfixable situation. Recovery required physical access to data centers, but even the badge systems needed network connectivity.

It took **6 hours and 13 minutes** to restore service. The cost: $100 million in revenue, 6% stock price drop, and 3.5 billion users disconnected from their primary communication platform.

This chapter analyzes how a **network-layer failure** collapsed all higher-layer guarantees, why **automation without escape hatches** creates lock-out scenarios, and what a principled approach to BGP configuration management could have prevented.

### Timeline with Guarantee Vectors and Network Visibility

```
15:39:00 UTC - Maintenance command issued on backbone routers
  G = ⟨Global, Causal, RA, Fresh(CDN), Idem(request_id), Auth(oauth)⟩
  Network: Facebook IPs globally routable
       ↓
15:39:12 UTC - BGP configuration audit detects perceived issue
  G = ⟨Global, Causal, RA, Fresh(CDN), Idem(request_id), Auth(oauth)⟩
  Network: Audit running, routes still advertised
       ↓
15:39:18 UTC - Audit FAILS, triggers safety mechanism
  G = ⟨Global → None, Causal → None, RA → None, Fresh → None, Idem → None, Auth → None⟩
  Network: ALL BGP routes withdrawn
  [COMPLETE COLLAPSE - Facebook invisible to internet]
       ↓
15:40:00 UTC - DNS resolution fails globally
  G = ⟨None, None, None, None, None, None⟩
  Network: No routes to Facebook DNS servers
  Effect: facebook.com unreachable
       ↓
15:45:00 UTC - Engineers realize the scope: TOTAL LOCK-OUT
  G = ⟨None⟩
  Network: Can't remote into data centers (no routes)
  Control Plane: Can't access management systems
  Evidence: Can't even see what's wrong (monitoring unreachable)
       ↓
16:00:00 UTC - Physical access to data centers required
  G = ⟨Local, None, None, None, None, Auth(physical)⟩
  Network: On-site only
  Problem: Badge systems need network (Catch-22!)
       ↓
18:00:00 UTC - Physical access obtained, BGP routes being restored
  G = ⟨Regional → Global, None → Causal, None → RA, ...⟩
  Network: Routes propagating through global BGP
       ↓
21:52:00 UTC - Services fully restored
  G = ⟨Global, Causal, RA, Fresh(CDN), Idem(request_id), Auth(oauth)⟩
  Network: Facebook IPs globally routable again
```

**The core failure**: Network reachability is the **foundation** of all distributed system guarantees. When BGP failed:
1. All higher-layer guarantees collapsed to ⟨None⟩
2. No out-of-band access for recovery
3. Safety mechanism had no escape hatch
4. Lock-out: Can't fix systems without accessing systems

## Part I: The Three-Layer Analysis

### Layer 1: Physics (The Eternal Truths)

**Truth 1: Network reachability is the foundation layer**

Every distributed system guarantee requires network connectivity:

```
Application Layer (HTTP/HTTPS)
    ↓ requires
Transport Layer (TCP/UDP)
    ↓ requires
Network Layer (IP routing via BGP)
    ↓ requires
Link Layer (physical connectivity)

If Network Layer fails → ALL higher layers fail
```

**Physics says**: You can't operate a distributed system without a network. BGP is how the internet knows how to route packets to your IP addresses.

**Facebook's guarantee stack collapse**:

```python
# Normal operation: Full stack
application = ⟨Global, Causal, RA, Fresh(CDN), Idem, Auth(oauth)⟩
transport = ⟨Global, Causal, RA, Fresh, Idem, Auth⟩
network = ⟨Global, None, RA, Fresh(routing), None, None⟩
link = ⟨Local, None, RA, Fresh(wire), None, None⟩

# Composition: Meet of all layers
G_facebook = meet(application, transport, network, link)
           = ⟨Global, None, RA, Fresh(CDN), None, Auth(oauth)⟩

# BGP failure: Network layer collapses
network_failed = ⟨None, None, None, None, None, None⟩

# Everything collapses
G_facebook_down = meet(application, transport, network_failed, link)
                = ⟨None, None, None, None, None, None⟩
```

**Key insight**: Network layer failure is **catastrophic** because it's foundational. Application-layer redundancy, transport-layer retries, authentication tokens—all become irrelevant when packets can't route.

**Truth 2: The lock-out paradox**

To fix a broken system, you need to access that system. But to access a system, the system must be reachable.

```python
class LockOutParadox:
    """The catch-22 of network outages"""

    def fix_network_outage(self):
        # To fix: Need to access routers
        # To access routers: Need network connectivity
        # Network connectivity: Broken!
        # Result: LOCKED OUT

        if not self.can_access_routers():
            # Can't fix what you can't reach
            raise LockOutError("Need physical access")

    def can_access_routers(self):
        # Try SSH
        if self.ssh_to_router():
            return True  # Won't work - no network!

        # Try management network
        if self.access_management_network():
            return True  # Won't work if it's in same BGP!

        # Try out-of-band access
        if self.out_of_band_access_exists():
            return True  # Facebook didn't have this!

        return False  # Locked out
```

**Truth 3: Evidence disappears when networks partition**

All evidence about system state requires network communication to collect:

```python
class EvidenceDuringOutage:
    """What you can't see when network is down"""

    # Normal: Rich evidence
    normal_evidence = {
        'metrics': 'CloudWatch/Prometheus collecting every second',
        'logs': 'Centralized log aggregation',
        'traces': 'Distributed tracing',
        'health_checks': 'Active health monitoring',
        'alerts': 'PagerDuty/Slack notifications'
    }

    # Network down: NO evidence
    outage_evidence = {
        'metrics': 'UNREACHABLE - monitoring system can\'t reach hosts',
        'logs': 'UNREACHABLE - log servers can\'t be reached',
        'traces': 'UNREACHABLE - tracing backend inaccessible',
        'health_checks': 'FAILING - but is it down or unreachable?',
        'alerts': 'UNREACHABLE - alert systems can\'t reach engineers'
    }

    # Only evidence: External observation
    external_evidence = {
        'dns_lookups': 'NXDOMAIN - Facebook doesn\'t exist',
        'ping': 'Host unreachable',
        'traceroute': 'Dead-ends before reaching Facebook',
        'bgp_looking_glass': 'No routes advertised'
    }
```

**The evidence crisis**: During Facebook's outage, internal evidence was inaccessible. Engineers could only observe from outside that Facebook had disappeared from the internet.

### Layer 2: Patterns (Design Strategies)

**Pattern 1: BGP routing as distributed consensus**

BGP is how the internet reaches consensus on routing:

```python
class BGPConsensus:
    """BGP is a distributed agreement protocol"""

    def __init__(self):
        # Facebook announces: "I am reachable at these IPs"
        self.announcements = {
            '157.240.0.0/16': 'AS32934 (Facebook)',
            '31.13.64.0/18': 'AS32934 (Facebook)',
            '2a03:2880::/32': 'AS32934 (Facebook IPv6)'
        }

    def advertise_routes(self):
        """Announce to the world: these IPs are reachable via us"""

        # Send BGP advertisements to peer routers
        for prefix, asn in self.announcements.items():
            bgp_advertisement = {
                'prefix': prefix,
                'origin_as': asn,
                'as_path': [32934],  # Just Facebook
                'next_hop': self.router_ip
            }

            # Send to all BGP peers
            for peer in self.bgp_peers:
                peer.send_advertisement(bgp_advertisement)

        # Global consensus emerges:
        # - ISPs learn routes
        # - Internet routers update routing tables
        # - Packets can now reach Facebook

    def withdraw_routes(self):
        """Announce to the world: these IPs are NO LONGER reachable via us"""

        for prefix in self.announcements.keys():
            bgp_withdrawal = {
                'prefix': prefix,
                'withdrawn': True
            }

            # Send to all BGP peers
            for peer in self.bgp_peers:
                peer.send_withdrawal(bgp_withdrawal)

        # Global consensus emerges:
        # - ISPs remove routes
        # - Internet routers delete routing entries
        # - Packets can NO LONGER reach Facebook
        # - Facebook has vanished from the internet!
```

**What went wrong**: Facebook's configuration audit incorrectly decided ALL routes should be withdrawn.

**Pattern 2: Out-of-band access for recovery**

Every critical system needs an escape hatch:

```python
class AccessLevels:
    """Multiple independent access paths"""

    def __init__(self):
        self.access_paths = [
            # Primary: In-band network access
            {
                'name': 'primary_network',
                'type': 'in_band',
                'dependency': 'BGP routing working',
                'reliability': 'HIGH (99.99%)',
                'available_during_bgp_failure': False
            },

            # Secondary: Management network
            {
                'name': 'management_network',
                'type': 'semi_out_of_band',
                'dependency': 'Separate network, but may share BGP',
                'reliability': 'MEDIUM (99.9%)',
                'available_during_bgp_failure': False  # Facebook's mistake!
            },

            # Tertiary: Out-of-band access
            {
                'name': 'console_servers',
                'type': 'out_of_band',
                'dependency': 'Serial console via separate ISP/network',
                'reliability': 'MEDIUM (95%)',
                'available_during_bgp_failure': True  # Facebook LACKED this!
            },

            # Last resort: Physical access
            {
                'name': 'physical_datacenter',
                'type': 'human',
                'dependency': 'Engineer travels to datacenter',
                'reliability': 'LOW (requires hours)',
                'available_during_bgp_failure': True  # Facebook's only option
            }
        ]

    def can_recover_from_bgp_failure(self):
        """Check if recovery is possible"""

        for path in self.access_paths:
            if path['available_during_bgp_failure']:
                return True, path['name']

        return False, 'LOCKED_OUT'

# Facebook's reality
facebook_access = AccessLevels()
can_recover, method = facebook_access.can_recover_from_bgp_failure()
# Returns: (True, 'physical_datacenter')
# Problem: Takes 2+ hours to dispatch engineers!
```

**Pattern 3: Safety mechanisms need escape hatches**

Automation that can't be overridden creates lock-out scenarios:

```python
class SafetyMechanismGoneWrong:
    """The automation that locked Facebook out"""

    def bgp_configuration_audit(self, config):
        """Audit detects issues and auto-remediates"""

        # Check configuration validity
        issues = self.validate_config(config)

        if issues:
            # SAFETY MECHANISM: Withdraw routes on audit failure
            # PROBLEM: No manual override, no confirmation, no escape hatch

            log.critical(f"Configuration audit FAILED: {issues}")
            log.critical("SAFETY MECHANISM ACTIVATED: Withdrawing all routes")

            # THIS IS THE PROBLEM:
            # - No confirmation prompt
            # - No "are you sure?"
            # - No gradual withdrawal
            # - No validation that withdrawal would be recoverable
            # - No check if out-of-band access exists

            self.withdraw_all_bgp_routes()  # POINT OF NO RETURN

            # NOW LOCKED OUT:
            # - Can't undo (no network access)
            # - Can't see logs (no network access)
            # - Can't access routers (no network access)
            # - Can't even check if this was the right decision!

# What was needed:
class SafetyMechanismWithEscapeHatch:
    """Safety with recoverability"""

    def bgp_configuration_audit(self, config):
        issues = self.validate_config(config)

        if issues:
            # 1. Alert but don't auto-remediate critical systems
            self.alert_engineers(
                severity='CRITICAL',
                message=f'BGP audit detected issues: {issues}',
                action_required='Manual review required'
            )

            # 2. If auto-remediation is allowed, do it GRADUALLY
            if self.auto_remediation_enabled and issues.severity < CRITICAL:
                # Withdraw routes gradually
                self.gradual_route_withdrawal(
                    percentage_per_minute=10,
                    check_reachability_after_each_step=True,
                    abort_if_management_network_unreachable=True
                )

            # 3. NEVER withdraw ALL routes without escape hatch
            if self.out_of_band_access_verified():
                # Safe to proceed with aggressive remediation
                pass
            else:
                # NOT SAFE - require manual confirmation
                raise RequiresManualIntervention(
                    "No out-of-band access detected. "
                    "Refusing to auto-remediate BGP."
                )
```

### Layer 3: Implementation (The Tactics)

**The BGP Configuration Change That Broke Facebook**

```bash
# The maintenance command (intended to be routine)
# Goal: Update capacity on backbone routers between data centers

# What it did:
1. Connected to backbone routers
2. Ran configuration update command
3. Command modified BGP peering configuration
4. Triggered automated configuration audit

# The audit (oversimplified):
function audit_bgp_config() {
    # Check: Does this config have proper redundancy?
    # Check: Are all peers reachable?
    # Check: Are route advertisements consistent?

    # BUG: Audit logic had a flaw
    # It detected the backbone change as "disconnecting data centers"
    # (This was FALSE - it was just updating capacity)

    # Audit incorrectly concluded: "Network partition imminent"
    # Safety response: "Withdraw all routes to prevent split-brain"

    if audit_detects_issue:
        withdraw_all_bgp_routes()  # CATASTROPHIC MISTAKE
}

# What happened next:
- Facebook routers sent BGP WITHDRAW messages to all peers
- ISPs worldwide removed Facebook routes from their routing tables
- Within 60 seconds, Facebook was unreachable globally
- DNS queries for facebook.com returned NXDOMAIN
- 3.5 billion users saw "can't connect" errors
```

**The BGP Withdrawal**:

```python
class FacebookBGPOutage:
    """The technical sequence of events"""

    def __init__(self):
        self.facebook_asn = 32934
        self.facebook_prefixes = [
            '157.240.0.0/16',
            '31.13.64.0/18',
            '2a03:2880::/32'
        ]

    def normal_bgp_operation(self):
        """How Facebook announces its presence to the internet"""

        # Facebook's edge routers announce routes
        for prefix in self.facebook_prefixes:
            bgp_announcement = BGPMessage(
                type='ANNOUNCEMENT',
                prefix=prefix,
                as_path=[self.facebook_asn],
                origin='IGP',
                next_hop='<Facebook edge router IP>'
            )

            # Send to BGP peers (ISPs)
            self.send_to_peers(bgp_announcement)

        # Global routing tables now contain:
        # Destination: 157.240.0.0/16 → Next hop: Facebook (AS32934)
        # Result: Internet can reach Facebook

    def the_outage_trigger(self):
        """The configuration audit fails"""

        # Audit runs on backbone router config change
        audit_result = self.audit_bgp_configuration()

        if audit_result.status == 'FAILED':
            # CRITICAL DECISION POINT
            # Audit detected: "Potential network partition"
            # Decision: "Withdraw all routes to prevent split-brain"

            # THIS WAS THE MISTAKE:
            # - Audit was WRONG (no actual partition)
            # - Response was DISPROPORTIONATE (withdraw ALL routes)
            # - No safety check (would this lock us out?)

            self.emergency_route_withdrawal()

    def emergency_route_withdrawal(self):
        """The command that made Facebook disappear"""

        # Send BGP WITHDRAW to all peers
        for prefix in self.facebook_prefixes:
            bgp_withdrawal = BGPMessage(
                type='WITHDRAW',
                prefix=prefix
            )

            self.send_to_peers(bgp_withdrawal)

        # BGP propagation (fast!)
        # T+0 seconds: Facebook routers send withdrawals
        # T+5 seconds: Tier 1 ISPs remove routes
        # T+30 seconds: Most ISPs have removed routes
        # T+60 seconds: Facebook globally unreachable

        # DNS cascade:
        # - DNS queries for facebook.com go to Facebook's DNS servers
        # - Facebook's DNS servers are inside Facebook's IP space
        # - Facebook's IP space is no longer routable
        # - DNS queries fail: NXDOMAIN or timeout
        # - Result: facebook.com doesn't resolve

    def why_recovery_was_slow(self):
        """The lock-out problem"""

        # To fix: Need to re-announce BGP routes
        # To re-announce: Need to access routers
        # To access routers: Need network connectivity
        # Network connectivity: NONE (we withdrew all routes!)

        # Attempted recovery methods (all failed):
        attempts = [
            {
                'method': 'SSH to routers',
                'result': 'FAILED - no route to host',
                'time_wasted': '5 minutes'
            },
            {
                'method': 'VPN to management network',
                'result': 'FAILED - management network also unreachable',
                'time_wasted': '10 minutes'
            },
            {
                'method': 'Out-of-band console access',
                'result': 'FAILED - Facebook had no true OOB access',
                'time_wasted': '15 minutes realizing this'
            },
            {
                'method': 'Emergency BGP peer configuration',
                'result': 'FAILED - can\'t reach routers to configure',
                'time_wasted': '20 minutes'
            },
            {
                'method': 'Contact ISPs to manually route',
                'result': 'PARTIAL - ISPs confused, no authority to override',
                'time_wasted': '30 minutes'
            }
        ]

        # Final solution: Physical data center access
        recovery = {
            'method': 'Send engineers to data centers',
            'steps': [
                '1. Identify which data centers have backbone routers',
                '2. Dispatch engineers (travel time: 30-90 minutes)',
                '3. Physical access (badge system broken, needs manual override)',
                '4. Console into routers via serial cable',
                '5. Re-announce BGP routes manually',
                '6. Wait for global BGP propagation (30-60 minutes)',
                '7. Verify services recovering',
                '8. Gradual traffic restoration'
            ],
            'total_time': '6 hours 13 minutes'
        }

        return recovery
```

**The Badge System Catch-22**:

```python
class BadgeSystemIrony:
    """Even physical access was locked out"""

    def enter_data_center(self, engineer):
        """The badge system problem"""

        # Facebook's physical security uses networked badge system
        # System checks:
        # 1. Is badge valid?
        # 2. Is engineer authorized for this building?
        # 3. Is there an active security alert?
        # 4. Log entry in central database

        # ALL OF THESE REQUIRE NETWORK

        try:
            # Check badge against central database
            if self.central_auth_system.verify_badge(engineer.badge):
                self.unlock_door()
            else:
                self.deny_access()
        except NetworkUnreachable:
            # CATCH-22: Badge system can't verify without network
            # Network is down - that's why we're here!

            # Manual override required
            # - Call security team
            # - Security team verifies identity via phone/video
            # - Security manually unlocks doors
            # - Time wasted: 45-90 minutes per data center

            log.error(
                "Badge system unreachable. "
                "Requiring manual security override. "
                "This will delay recovery significantly."
            )
```

## Part II: Guarantee Vector Algebra

### Normal Operation Composition

Facebook's architecture with guarantee vectors:

```python
# Application layer
G_app = ⟨Global, Causal, RA, Fresh(CDN), Idem(request_id), Auth(oauth)⟩

# Transport layer (TCP)
G_transport = ⟨Global, Causal, RA, Fresh(connection), Idem(seq_num), Auth(tls)⟩

# Network layer (BGP routing)
G_network = ⟨Global, None, RA, Fresh(routing_table), None, None⟩

# BGP specifically
G_bgp = ⟨Global, None, RA, Fresh(bgp_convergence), None, None⟩

# Composition: Sequential through network stack
G_facebook = G_app ▷ G_transport ▷ G_network ▷ G_bgp
           = meet(G_app, G_transport, G_network, G_bgp)
           = ⟨Global, None, RA, Fresh(CDN), None, Auth(oauth)⟩
```

**Key insight**: Even though Facebook had strong application-layer guarantees, the network layer only provides ⟨Global, None, RA, ...⟩. But "Global" scope is CRITICAL—it means Facebook is reachable worldwide.

### BGP Failure: Scope Collapse

```python
# When BGP routes are withdrawn
G_network_failed = ⟨None, None, None, None, None, None⟩

# Composition fails
G_facebook_outage = G_app ▷ G_transport ▷ G_network_failed
                  = meet(..., ⟨None⟩)
                  = ⟨None, None, None, None, None, None⟩

# Interpretation:
# - Scope: None (not reachable at ANY scope)
# - Order: None (can't even send requests)
# - Visibility: None (no communication possible)
# - Recency: None (no data flows)
# - Idempotence: None (can't send requests)
# - Authentication: None (can't authenticate)

# COMPLETE COLLAPSE
```

**The foundational guarantee**: Network reachability is so fundamental that its loss collapses ALL other guarantees.

### Parallel Composition: Multiple Access Paths

```python
# What Facebook should have had
G_primary_network = ⟨Global, None, RA, Fresh(routing), None, None⟩
G_management_network = ⟨Regional, None, RA, Fresh(routing), None, None⟩
G_out_of_band = ⟨Local, None, RA, Fresh(serial), None, None⟩

# Parallel composition for recovery
G_recovery = G_primary_network || G_management_network || G_out_of_band
           = join(G_primary, G_management, G_oob)
           = ⟨Local ∨ Regional ∨ Global, None, RA, Fresh(best), None, None⟩

# Key property: If one path fails, others available
# If primary_network fails → can use management_network or OOB
# If management_network also fails → can use OOB
# If OOB exists → can ALWAYS recover (at least locally)

# Facebook's reality (missing OOB)
G_recovery_facebook = G_primary_network || G_management_network
                    = join(G_primary, G_management)
                    = ⟨Regional ∨ Global, None, RA, ...⟩

# Problem: Both paths relied on same BGP
# When BGP failed → BOTH paths failed → No recovery path
```

### Upgrade Path: From None to Global

```python
# Current state during outage
G_current = ⟨None, None, None, None, None, None⟩

# Target state
G_target = ⟨Global, Causal, RA, Fresh(CDN), Idem(request_id), Auth(oauth)⟩

# Upgrade requires generating NEW EVIDENCE
# But evidence generation requires NETWORK ACCESS
# This is the lock-out paradox

upgrade_path = [
    # Step 1: Physical access (generates local scope evidence)
    {
        'action': 'Engineer arrives at datacenter',
        'evidence': 'Physical presence, serial console access',
        'g_vector_upgrade': '⟨None⟩ → ⟨Local, None, None, None, None, Auth(physical)⟩'
    },

    # Step 2: Console access to routers (enables local control)
    {
        'action': 'Connect via serial console',
        'evidence': 'Direct router access, can see config',
        'g_vector_upgrade': '⟨Local, None, None, ...⟩ → ⟨Local, None, RA, Fresh(local), None, Auth(console)⟩'
    },

    # Step 3: Re-announce BGP routes (expands scope regionally)
    {
        'action': 'Issue BGP announcements',
        'evidence': 'BGP ANNOUNCEMENT messages sent to peers',
        'g_vector_upgrade': '⟨Local, ...⟩ → ⟨Regional, None, RA, Fresh(bgp_propagating), ...⟩'
    },

    # Step 4: BGP propagation (expands to global)
    {
        'action': 'Wait for internet-wide BGP convergence',
        'evidence': 'Route advertisements propagated globally',
        'g_vector_upgrade': '⟨Regional⟩ → ⟨Global, None, RA, Fresh(routing_table), None, None⟩'
    },

    # Step 5: Application services restart (restore full guarantees)
    {
        'action': 'Services begin handling traffic',
        'evidence': 'Health checks passing, traffic flowing',
        'g_vector_upgrade': '⟨Global, None, RA, ...⟩ → ⟨Global, Causal, RA, Fresh(CDN), Idem, Auth(oauth)⟩'
    }
]

# Timeline:
# Local: 30 minutes (travel + physical access)
# Regional: +30 minutes (BGP announcements + peer acceptance)
# Global: +60 minutes (full BGP propagation)
# Full: +4 hours (cautious traffic ramp-up, verification)
# Total: ~6 hours
```

**Key insight**: Upgrading from ⟨None⟩ back to ⟨Global⟩ requires sequential evidence generation, and each step has minimum time bounds (BGP propagation, physical travel).

### Composition Operators in Network Context

**Sequential (▷)**: Through network stack

```python
# Application layer depends on network layer
G_end_to_end = G_application ▷ G_network
             = meet(G_application, G_network)

# If G_network = ⟨None⟩, then G_end_to_end = ⟨None⟩
# Network layer failure is CATASTROPHIC
```

**Parallel (||)**: Multiple access paths

```python
# Multiple independent paths
G_access = G_primary || G_oob
         = join(G_primary, G_oob)

# If G_primary fails, G_oob provides fallback
# This is ESSENTIAL for recovery
```

**Downgrade (⤓)**: Automatic scope narrowing (Facebook didn't have this!)

```python
# What should have happened:
G_normal = ⟨Global, Causal, RA, Fresh(CDN), Idem, Auth⟩
         ⤓ [backbone capacity change detected]
G_cautious = ⟨Regional, Causal, RA, Fresh(CDN), Idem, Auth⟩
         # Narrow scope to regional, keep service running
         # Don't withdraw ALL routes!

# What actually happened:
G_normal = ⟨Global, Causal, RA, Fresh(CDN), Idem, Auth⟩
         ⤓ [audit failed]
G_catastrophic = ⟨None, None, None, None, None, None⟩
         # Collapsed to NOTHING
         # No gradual degradation, just off cliff
```

**Upgrade (↑)**: Recovery path (requires new evidence)

```python
# Recovery requires evidence generation
G_locked_out = ⟨None, None, None, None, None, None⟩
            ↑ [evidence: physical_access + console_access]
G_local = ⟨Local, None, RA, Fresh(serial), None, Auth(physical)⟩
            ↑ [evidence: bgp_announcements_sent]
G_regional = ⟨Regional, None, RA, Fresh(propagating), None, None⟩
            ↑ [evidence: global_bgp_convergence]
G_global = ⟨Global, None, RA, Fresh(routing), None, None⟩
            ↑ [evidence: application_health_checks]
G_normal = ⟨Global, Causal, RA, Fresh(CDN), Idem, Auth⟩
```

## Part III: Context Capsules

### Capsule at BGP Routing Boundary

**Normal operation**:

```python
bgp_routing_capsule = {
    'invariant': 'facebook_ips_globally_reachable',
    'evidence': {
        'type': 'bgp_announcements',
        'status': 'ACTIVE',
        'announced_prefixes': [
            '157.240.0.0/16',
            '31.13.64.0/18',
            '2a03:2880::/32'
        ],
        'peer_acceptance': 'All major ISPs have routes',
        'propagation_status': 'Global convergence complete',
        'last_announcement': '2021-10-04T15:39:00Z',
        'expires_at': None,  # BGP routes don't expire unless withdrawn
        'proof': 'bgp_looking_glass_shows_routes + internet_can_reach_us'
    },
    'boundary': 'facebook_edge_routers ↔ isp_routers',
    'scope': 'Global',
    'mode': 'target',
    'g_vector': '⟨Global, None, RA, Fresh(routing_table), None, None⟩',
    'operations': {
        'reach_facebook': 'ALLOW (globally)',
        'dns_resolution': 'ALLOW',
        'tcp_connection': 'ALLOW',
        'http_requests': 'ALLOW'
    },
    'fallback': 'withdraw_routes_on_audit_failure'  # THE PROBLEM!
}
```

**During outage** (after BGP withdrawal):

```python
bgp_outage_capsule = {
    'invariant': 'facebook_ips_globally_reachable',
    'evidence': {
        'type': 'bgp_withdrawals',
        'status': 'WITHDRAWN',  # CRITICAL!
        'announced_prefixes': [],  # NONE!
        'peer_acceptance': 'ISPs have removed all routes',
        'propagation_status': 'Facebook disappeared from internet',
        'last_withdrawal': '2021-10-04T15:39:18Z',
        'proof': 'bgp_looking_glass_shows_NO_routes + internet_cannot_reach_us',
        'reason': 'Automated audit failure triggered emergency withdrawal'
    },
    'boundary': 'facebook_edge_routers ↔ isp_routers',
    'scope': 'None',  # Not reachable at ANY scope!
    'mode': 'INVALID',  # System is invisible to internet
    'g_vector': '⟨None, None, None, None, None, None⟩',
    'operations': {
        'reach_facebook': 'IMPOSSIBLE (no routes)',
        'dns_resolution': 'FAILS (dns servers unreachable)',
        'tcp_connection': 'FAILS (no route to host)',
        'http_requests': 'FAILS (can\'t connect)'
    },
    'fallback': 'ACTIVATED - but now LOCKED OUT!',
    'recovery': 'Requires out-of-band access (MISSING!)'
}
```

**The lock-out capsule** (management network):

```python
management_network_capsule = {
    'invariant': 'engineers_can_access_infrastructure',
    'evidence': {
        'type': 'network_reachability',
        'status': 'UNREACHABLE',
        'problem': 'Management network ALSO depends on BGP',
        'proof': 'SSH connections timeout, VPN unreachable'
    },
    'boundary': 'engineer_laptop ↔ facebook_infrastructure',
    'scope': 'None',  # Can't reach from anywhere!
    'mode': 'INVALID',
    'g_vector': '⟨None, None, None, None, None, None⟩',
    'operations': {
        'ssh_to_servers': 'FAILS (no route)',
        'vpn_connect': 'FAILS (vpn_gateway unreachable)',
        'out_of_band_console': 'MISSING (should have this!)',
        'physical_access': 'ONLY OPTION (requires hours)'
    },
    'fallback': 'NOT_DEFINED - no escape hatch!',
    'recovery': 'Must physically travel to data centers'
}
```

### Capsule Operations

**restrict()** - Should have narrowed scope gradually:

```python
def restrict_capsule_gradually(capsule, issue_severity):
    """Narrow scope instead of collapsing to none"""

    if issue_severity == 'LOW':
        # Minor issue: Reduce scope but keep service
        return {
            **capsule,
            'scope': 'Regional',  # Global → Regional
            'g_vector': downgrade_vector(capsule['g_vector'], 'Regional'),
            'mode': 'degraded',
            'operations': {
                'reach_facebook': 'ALLOW (regional only)',
                'dns_resolution': 'ALLOW',
                'tcp_connection': 'ALLOW',
                'http_requests': 'ALLOW'
            },
            'evidence': mark_as_restricted(capsule['evidence'])
        }

    elif issue_severity == 'MEDIUM':
        # Moderate issue: Narrow to single datacenter
        return {
            **capsule,
            'scope': 'Local',  # Regional → Local
            'mode': 'floor',
            'operations': {
                'reach_facebook': 'ALLOW (single datacenter)',
                'dns_resolution': 'ALLOW (cached)',
                'tcp_connection': 'ALLOW (limited)',
                'http_requests': 'ALLOW (degraded)'
            }
        }

    # NEVER go to severity='CRITICAL' without escape hatch!
    elif issue_severity == 'CRITICAL' and not has_out_of_band_access():
        # REFUSE to degrade to None if no recovery path
        raise RefuseToLockOut(
            "Cannot withdraw all routes without out-of-band access. "
            "Manual intervention required."
        )

# What Facebook did:
# issue_severity = 'PERCEIVED_CRITICAL' (incorrectly assessed)
# Jumped straight to scope='None'
# No gradual degradation, no escape hatch check
```

**degrade()** - The fallback that locked Facebook out:

```python
def degrade_capsule_wrong(capsule, reason):
    """Facebook's mistake: Degrade to Nothing"""

    return {
        **capsule,
        'mode': 'INVALID',
        'scope': 'None',  # CATASTROPHIC
        'g_vector': '⟨None, None, None, None, None, None⟩',
        'operations': {
            'reach_facebook': 'IMPOSSIBLE',
            'dns_resolution': 'FAILS',
            'tcp_connection': 'FAILS',
            'http_requests': 'FAILS'
        },
        'degradation_reason': reason,
        'degraded_at': time.now(),
        'evidence': 'ALL_ROUTES_WITHDRAWN',
        'recovery_possible': False  # LOCKED OUT!
    }

def degrade_capsule_correct(capsule, reason):
    """What should have happened: Degrade but stay reachable"""

    # Check: Do we have out-of-band access?
    if not verify_out_of_band_access():
        # REFUSE to degrade beyond reachability
        log.error(
            "Cannot fully degrade BGP without OOB access. "
            "Degrading to 'floor' mode instead."
        )

        return {
            **capsule,
            'mode': 'floor',
            'scope': 'Local',  # Keep at least local reachability
            'g_vector': '⟨Local, None, RA, Fresh(limited), None, Auth(limited)⟩',
            'operations': {
                'reach_facebook': 'ALLOW (single datacenter only)',
                'dns_resolution': 'ALLOW (cached responses)',
                'tcp_connection': 'ALLOW (limited capacity)',
                'http_requests': 'ALLOW (degraded performance)',
                'management_access': 'ALLOW (engineers can still access)'
            },
            'degradation_reason': reason,
            'evidence': 'PARTIAL_ROUTES_MAINTAINED',
            'recovery_possible': True  # Can recover remotely!
        }
```

**recover()** - The painful physical access recovery:

```python
def recover_from_bgp_lockout():
    """Recovery when locked out"""

    recovery_steps = []

    # Step 1: Realize the scope of the problem
    step1 = {
        'action': 'Diagnose lock-out scenario',
        'time': 15,  # minutes
        'evidence': 'All remote access failing, BGP routes withdrawn',
        'g_vector': '⟨None⟩ → still ⟨None⟩'
    }
    recovery_steps.append(step1)

    # Step 2: Dispatch engineers to data centers
    step2 = {
        'action': 'Send engineers to physical locations',
        'time': 60,  # minutes (depends on proximity)
        'evidence': 'Engineer en route',
        'g_vector': '⟨None⟩ → still ⟨None⟩ (no change yet)'
    }
    recovery_steps.append(step2)

    # Step 3: Physical access (badge system issue!)
    step3 = {
        'action': 'Gain physical access to data center',
        'time': 45,  # minutes (badge system down, manual override)
        'evidence': 'Engineer inside data center',
        'g_vector': '⟨None⟩ → ⟨Local, None, None, None, None, Auth(physical)⟩'
    }
    recovery_steps.append(step3)

    # Step 4: Console access to routers
    step4 = {
        'action': 'Connect to routers via serial console',
        'time': 15,  # minutes
        'evidence': 'Direct console access to routers',
        'g_vector': '⟨Local⟩ → ⟨Local, None, RA, Fresh(console), None, Auth(console)⟩'
    }
    recovery_steps.append(step4)

    # Step 5: Re-announce BGP routes
    step5 = {
        'action': 'Manually configure BGP to re-announce routes',
        'time': 30,  # minutes (careful configuration)
        'evidence': 'BGP ANNOUNCEMENT messages sent',
        'g_vector': '⟨Local⟩ → ⟨Regional → Global, None, RA, Fresh(propagating), None, None⟩'
    }
    recovery_steps.append(step5)

    # Step 6: Wait for global BGP propagation
    step6 = {
        'action': 'BGP routes propagate across internet',
        'time': 60,  # minutes (internet-wide convergence)
        'evidence': 'ISPs adding routes back to routing tables',
        'g_vector': '⟨Regional⟩ → ⟨Global, None, RA, Fresh(routing), None, None⟩'
    }
    recovery_steps.append(step6)

    # Step 7: Services restart and verify
    step7 = {
        'action': 'Application services gradually resume',
        'time': 120,  # minutes (cautious ramp-up)
        'evidence': 'Traffic flowing, health checks passing',
        'g_vector': '⟨Global, None, RA, ...⟩ → ⟨Global, Causal, RA, Fresh(CDN), Idem, Auth⟩'
    }
    recovery_steps.append(step7)

    total_time = sum(step['time'] for step in recovery_steps)
    # 15 + 60 + 45 + 15 + 30 + 60 + 120 = 345 minutes = 5.75 hours
    # Actual: 6 hours 13 minutes (additional verification and caution)

    return recovery_steps, total_time
```

## Part IV: Five Sacred Diagrams

### Diagram 1: Invariant Lattice - Network Reachability Hierarchy

```
                    Global Reachability
              (All internet can reach Facebook)
                          |
                          |
                    Regional Reachability
              (Specific region can reach Facebook)
                    /           \
                   /             \
          Datacenter Reachable   ISP Reachable
         (Local data center     (Specific ISP
          can reach services)    has routes)
                  \              /
                   \            /
                Physical Access Only
            (Must be on-site to access)
                      |
                      |
                  No Access
            (Completely unreachable)


During Facebook BGP outage:

✓ Physical Access Only: Maintained (can enter data center)
✗ Datacenter Reachable: VIOLATED (no network routes)
✗ ISP Reachable: VIOLATED (ISPs removed routes)
✗ Regional Reachability: VIOLATED (no regional routes)
✗ Global Reachability: VIOLATED (Facebook invisible globally)

Result: Collapsed from Global to "Physical Only"
```

### Diagram 2: Evidence Flow - BGP Route Propagation

```
                  NORMAL OPERATION

[Facebook Edge Router]              [ISP Router (Tier 1)]
      |                                     |
      | BGP ANNOUNCEMENT:                  |
      | "157.240.0.0/16 via AS32934"       |
      |                                     |
      +----------BGP UPDATE MESSAGE------->+
      |                                     |
      |                                     | validates: path OK
      |                                     | accepts: adds to routing table
      |                                     |
   evidence:                             evidence:
   - route_announced=TRUE                - route_learned=TRUE
   - peers_notified=ALL                  - facebook_reachable=TRUE
   - status=ACTIVE                       - propagating_downstream=TRUE

            |                                     |
            v                                     v
   [Global routing tables contain Facebook routes]
   [Internet can reach 157.240.0.0/16]


                  DURING BGP WITHDRAWAL

[Facebook Edge Router]    BGP AUDIT FAILS    [ISP Router (Tier 1)]
      |                                              |
      | BGP WITHDRAWAL:                             |
      | "157.240.0.0/16 WITHDRAWN"                  |
      |                                              |
      +-----------BGP WITHDRAW MESSAGE------------->+
      |                                              |
      | NO MORE ANNOUNCEMENTS                        | validates: withdrawal legit
      |                                              | removes: deletes from routing table
      |                                              |
   evidence:                                      evidence:
   - route_announced=FALSE                        - route_learned=FALSE
   - status=WITHDRAWN                             - facebook_reachable=FALSE
   - reason=AUDIT_FAILURE                         - propagating_downstream=TRUE
      |                                              |
      v                                              v
   FACEBOOK INVISIBLE                           ISP PROPAGATES WITHDRAWAL
   (no routes announced)                        (downstream routers remove routes)

            |                                              |
            v                                              v
   [Global routing tables: NO Facebook routes]
   [Internet CANNOT reach Facebook]


              AFTER PHYSICAL RECOVERY

[Facebook Edge Router]    MANUAL REPAIR      [ISP Router (Tier 1)]
   (console access)                               |
      |                                           |
      | BGP ANNOUNCEMENT:                         |
      | "157.240.0.0/16 via AS32934"              |
      |                                            |
      +----------BGP UPDATE MESSAGE-------------->+
      |                                            |
   evidence:                                    evidence:
   - route_announced=TRUE                       - route_learned=TRUE
   - manual_override=TRUE                       - facebook_reachable=TRUE
   - status=RECOVERING                          - propagating_downstream=TRUE
      |                                            |
      v                                            v
   [Global routing tables: Facebook routes RESTORED]
   [Internet can reach Facebook again]
   [Propagation time: 30-60 minutes for global convergence]
```

### Diagram 3: Mode Transitions - From Reachable to Locked Out to Recovered

```
┌─────────────────────────────────────────────────────────────┐
│                        TARGET MODE                           │
│  Invariants: Global reachability, DNS resolution working    │
│  Evidence: BGP routes propagated globally                   │
│  G-vector: ⟨Global, Causal, RA, Fresh(CDN), Idem, Auth⟩     │
│  Operations: All traffic globally, remote admin access      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [backbone maintenance command issued]
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   AUDIT RUNNING MODE                         │
│  Invariants: Reachability maintained during audit           │
│  Evidence: Configuration being validated                    │
│  G-vector: ⟨Global, Causal, RA, Fresh(CDN), Idem, Auth⟩     │
│  Operations: All traffic continues normally                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [audit FAILS - perceived issue detected]
                       │ [safety mechanism: WITHDRAW ALL ROUTES]
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   BGP WITHDRAWN MODE                         │
│  Invariants: NONE - Facebook disappeared from internet      │
│  Evidence: BGP withdrawals propagated                       │
│  G-vector: ⟨None, None, None, None, None, None⟩             │
│  Operations: NO traffic possible, NO remote access          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [engineers realize: LOCKED OUT]
                       │ [all remote access fails]
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   NETWORK ISOLATED MODE                      │
│  Invariants: Facebook invisible, lock-out scenario          │
│  Evidence: Cannot access any systems remotely               │
│  G-vector: ⟨None, None, None, None, None, None⟩             │
│  Operations: NONE - must resort to physical access          │
│  Duration: Hours (travel time to data centers)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [engineers dispatched to data centers]
                       │ [physical access obtained]
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  PHYSICAL ACCESS MODE                        │
│  Invariants: On-site access available                       │
│  Evidence: Engineers in data center, serial console access  │
│  G-vector: ⟨Local, None, RA, Fresh(console), None, Auth(physical)⟩│
│  Operations: Console access to routers, manual config       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [BGP routes manually re-announced]
                       │ [routes propagating across internet]
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    RECOVERY MODE                             │
│  Invariants: Routes propagating, reachability returning     │
│  Evidence: BGP convergence in progress, traffic returning   │
│  G-vector: ⟨Regional → Global, None → Causal, RA, Fresh(propagating), Idem, Auth⟩│
│  Operations: Gradual traffic resumption, careful monitoring │
│  Duration: 60-90 minutes (BGP propagation + verification)   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ [global BGP convergence complete]
                       │ [services verified healthy]
                       ↓
                   (back to TARGET)


Facebook's actual path:

15:39:00 - TARGET (maintenance begins)
15:39:12 - AUDIT RUNNING
15:39:18 - BGP WITHDRAWN (catastrophic decision)
15:40:00 - NETWORK ISOLATED (locked out)
16:00:00 - Dispatch engineers
17:30:00 - PHYSICAL ACCESS obtained
18:00:00 - RECOVERY begins (BGP re-announcement)
21:52:00 - TARGET restored

Total: 6 hours 13 minutes
```

### Diagram 4: Guarantee Degradation - Network Stack Collapse

```
Components:  Scope      Order      Visibility  Recency      Idem       Auth
            ━━━━━━    ━━━━━━━    ━━━━━━━━━  ━━━━━━━━    ━━━━━━    ━━━━━━

Normal:     Global ─┐  Causal ─┐    RA ─┐    Fresh ─┐  request ─┐  oauth ─┐
(15:39)     Route  │  Order   │    Read │    CDN    │  _id     │  token  │
            d      │  ed      │    After│    cache  │          │         │
                   │          │    Write│           │          │         │
                   │          │         │           │          │         │
BGP         Global │  Causal  │    RA   │    Fresh  │  request │  oauth  │
Audit       Route  │  Order   │    Read │    CDN    │  _id     │  token  │
Running     d      │  ed      │    After│    cache  │          │         │
(15:39:12)         │          │    Write│           │          │         │
                   │          │         │           │          │         │
                   ↓          ↓         ↓           ↓          ↓         ↓
BGP         None   None     None     None        None       None
Withdrawn   NO     NO       NO       NO          NO         NO
(15:39:18)  ROUTES ORDER    VISIBILITY RECENCY   IDEM       AUTH
            │      │        │         │          │          │
            │      │        │         │          │          │
            └──────┴────────┴─────────┴──────────┴──────────┘
                              │
                              ↓
            COMPLETE COLLAPSE - ALL GUARANTEES LOST
            Network layer failure collapses entire stack

                    ↑ UPGRADE REQUIRES PHYSICAL ACCESS ↑

Physical    Local   None     RA       Fresh    None     Physical
Access      Only    │        console  serial   │        auth
(17:30)     On-     │        access   cable    │        (badge)
            site    │                          │
                    ↓                          ↓
BGP         Region  None     RA       Fresh    request  Session
Recovery    al→     │        Limited  propag   _id      based
(18:00)     Global  │        traffic  ating    │
                    ↓        │        BGP      │
                    ↓        ↓        ↓        ↓         ↓
Target:     Global  Causal   RA       Fresh    request  oauth
(21:52)     Route   Order    Read     CDN      _id      token
            d       ed       After    cache
                             Write
```

### Diagram 5: The Lock-Out Scenario - Can't Fix What You Can't Reach

```
              NORMAL OPERATION

Engineer @ Home                    Facebook Infrastructure
      |                                     |
      | SSH, VPN, remote admin              |
      | via INTERNET                        |
      |                                     |
      +----------can reach servers--------->+
      |                                     |
      | Deployment, config changes,         |
      | monitoring, incident response       |
      |                                     |
   Access: REMOTE                        Reachable: YES
   Evidence: SSH keys valid             G-vector: ⟨Global⟩
   Operations: ALL


              BGP WITHDRAWAL TRIGGERED

Engineer @ Home        BGP ROUTES          Facebook Infrastructure
      |              WITHDRAWN                   |
      | Try SSH...          ╳╳╳                 |
      | Try VPN...          ╳╳╳                 |
      | Try any remote...   ╳╳╳                 |
      |                                          |
      +----------CANNOT REACH----------╳╳╳      |
      |                                          |
      | NO ROUTES TO FACEBOOK                    |
      | Internet doesn't know how to              |
      | route packets to Facebook IPs            |
      |                                          |
   Access: NONE                             Reachable: NO
   Evidence: "No route to host"            G-vector: ⟨None⟩
   Operations: NONE                        Status: INVISIBLE


              THE LOCK-OUT PARADOX

      To FIX:                           To ACCESS:
   Need to access routers          Need network connectivity
         |                                    |
         +----------------╳╳╳-----------------+
                          |
                  BUT NETWORK IS DOWN!
                (that's the problem we're fixing)


              ATTEMPTED WORKAROUNDS (ALL FAIL)

Try: SSH via Internet          → FAIL (no routes)
Try: VPN via management net    → FAIL (management net also down)
Try: Emergency BGP peer        → FAIL (can't configure remotely)
Try: Call ISP to manually route → FAIL (ISPs removed routes as requested)
Try: Access monitoring system   → FAIL (monitoring needs network)
Try: Check logs                → FAIL (log system unreachable)


              ONLY SOLUTION: PHYSICAL ACCESS

Engineer @ Home          Travel Required       Data Center
      |                  (1-2 hours)                |
      |                      ↓                      |
      +------------DRIVE TO FACILITY--------------->+
      |                                             |
   Problem: Badge system ALSO down!                 |
   (needs network)                                  |
      |                                             |
      +---Manual security override required-------->+
      |     (30-60 minutes)                         |
      |                                             |
      +---Serial console access------------------->+
      |                                             |
   Finally: SERIAL CONSOLE                          |
   (doesn't need network)                           |
      |                                             |
      +---Issue BGP announcements------------------>+
      |                                             |
   Wait: BGP propagation across internet            |
   (30-60 minutes)                                  |
      |                                             |
      +---Routes restored-------------------------->+
      |                                             |
   Access: LOCAL → REMOTE                     Reachable: YES
   Operations: MANUAL → AUTOMATED            G-vector: ⟨None⟩ → ⟨Global⟩

Total time: 6+ hours
```

## Part V: Mode Matrix

```
┌──────────┬────────────────┬─────────────────┬───────────────────┬──────────────────┬───────────────────────┐
│ Mode     │ Invariants     │ Evidence        │ G-vector          │ Operations       │ Entry/Exit Triggers    │
│          │ Preserved      │ Required        │                   │ Allowed          │                       │
├──────────┼────────────────┼─────────────────┼───────────────────┼──────────────────┼───────────────────────┤
│ Target   │ • Global       │ • BGP routes    │ ⟨Global,          │ • All traffic    │ Entry: routes_verified│
│          │   reachability │   announced     │  Causal,          │   globally       │ Exit: audit_failure   │
│          │ • DNS resolves │ • ISPs have     │  RA,              │ • Remote admin   │   OR backbone_issue   │
│          │ • All services │   routes        │  Fresh(CDN),      │   access         │                       │
│          │   operational  │ • Health checks │  Idem(req_id),    │ • Full services  │                       │
│          │                │   passing       │  Auth(oauth)⟩     │                  │                       │
├──────────┼────────────────┼─────────────────┼───────────────────┼──────────────────┼───────────────────────┤
│Degraded  │ • Regional     │ • Partial BGP   │ ⟨Regional,        │ • Regional       │ Entry: partial_failure│
│(should   │   reachability │   routes        │  Causal,          │   traffic        │ Exit: full_failure    │
│have been │ • Some DNS     │ • Some ISPs     │  RA,              │ • Limited admin  │   OR routes_restored  │
│used!)    │   resolution   │   have routes   │  Fresh(CDN),      │   access         │                       │
│          │ • Core services│ • Partial health│  Idem(req_id),    │ • Core services  │                       │
│          │   working      │   checks        │  Auth(cache)⟩     │   only           │                       │
├──────────┼────────────────┼─────────────────┼───────────────────┼──────────────────┼───────────────────────┤
│BGP       │ • NONE         │ • NONE          │ ⟨None,            │ • NO traffic     │ Entry: all_routes_    │
│Withdrawn │ • Facebook     │ • BGP withdrawn │  None,            │   possible       │   withdrawn           │
│(actual)  │   invisible    │ • No routes     │  None,            │ • NO remote      │ Exit: physical_access │
│          │ • Network      │   anywhere      │  None,            │   access         │   AND bgp_restored    │
│          │   isolated     │                 │  None,            │ • NO operations  │                       │
│          │                │                 │  None⟩            │                  │                       │
├──────────┼────────────────┼─────────────────┼───────────────────┼──────────────────┼───────────────────────┤
│Physical  │ • Local access │ • Engineer      │ ⟨Local,           │ • Console access │ Entry: engineer_      │
│Access    │   only         │   on-site       │  None,            │   to routers     │   on_site             │
│          │ • Serial       │ • Physical      │  RA,              │ • Manual config  │ Exit: bgp_routes_     │
│          │   console      │   presence      │  Fresh(console),  │ • Can issue BGP  │   announced           │
│          │   working      │ • Badge/auth    │  None,            │   commands       │                       │
│          │                │   verified      │  Auth(physical)⟩  │                  │                       │
├──────────┼────────────────┼─────────────────┼───────────────────┼──────────────────┼───────────────────────┤
│Recovery  │ • Routes       │ • BGP announces │ ⟨Regional→Global, │ • Gradual traffic│ Entry: bgp_announces  │
│          │   propagating  │   sent          │  None→Causal,     │   restoration    │ Exit: global_bgp_     │
│          │ • Partial      │ • Some ISPs     │  RA,              │ • Careful        │   convergence AND     │
│          │   reachability │   accepting     │  Fresh(propagate),│   monitoring     │   health_checks_pass  │
│          │ • Services     │ • Services      │  Idem(req_id),    │ • Verification   │                       │
│          │   starting     │   healthy       │  Auth(session)⟩   │   steps          │                       │
└──────────┴────────────────┴─────────────────┴───────────────────┴──────────────────┴───────────────────────┘
```

### What Facebook Actually Did vs. What Mode Matrix Prescribes

```python
# What happened (catastrophic)
15:39:12 - Audit running on config change → Continued normal operation (OK)
15:39:18 - Audit FAILED → Withdrew ALL routes (CATASTROPHIC)
15:39:30 - Realized locked out → Panic (TOO LATE)
16:00:00 - Decided need physical access → Dispatch engineers
21:52:00 - Finally recovered → 6+ hours total

# What Mode Matrix prescribes (principled)
15:39:12 - Config change detected
        → Run audit in SIMULATION MODE first
        → Verify: "Would this lock us out?"
        → Answer: "YES - no out-of-band access"
        → Decision: REFUSE to auto-remediate

# Alternative if audit must proceed:
15:39:18 - Audit detects issue (even if false positive)
        → DON'T withdraw ALL routes
        → Transition Target → Degraded
        → Narrow scope from Global → Regional
        → Maintain reachability for recovery

# If issue is truly critical:
15:39:18 - Issue requires aggressive response
        → Check: has_out_of_band_access()?
        → Answer: NO
        → Decision: REFUSE to lock out
        → Alert: "Manual intervention required"
        → Wait for human engineer to:
          1. Verify the issue is real
          2. Verify out-of-band access exists
          3. Approve aggressive remediation

# Recovery from any degraded state:
Any time - Issue resolved or was false positive
        → Transition Degraded → Target
        → Gradually restore routes
        → Verify health at each step
        → Duration: Minutes (not hours)
```

## Part VI: Evidence Lifecycle Analysis

### BGP Route Announcement Evidence

**Phase 1: Generated**

```python
class BGPRouteEvidence:
    def generate(self, prefix, asn):
        """Edge router generates BGP announcement"""
        return {
            'type': 'bgp_announcement',
            'prefix': prefix,
            'origin_as': asn,
            'as_path': [asn],
            'next_hop': self.router_ip,
            'timestamp': time.now(),
            'scope': 'global',
            'lifetime': None,  # BGP routes don't expire unless withdrawn
            'binding': f"router@{self.router_id}",
            'cost_generation': 'cheap (BGP message)',
            'cost_verification': 'network propagation time'
        }
```

**Phase 2: Validated**

```python
class ISPRouterValidation:
    def validate(self, bgp_announcement):
        """ISP router validates BGP announcement"""

        # 1. AS path valid?
        if not self.verify_as_path(bgp_announcement.as_path):
            return ValidationResult.INVALID_PATH

        # 2. Prefix authorized?
        if not self.verify_prefix_authorization(bgp_announcement.prefix, bgp_announcement.origin_as):
            return ValidationResult.UNAUTHORIZED

        # 3. No conflicting routes?
        if self.has_conflicting_route(bgp_announcement.prefix):
            return ValidationResult.CONFLICT

        # 4. Add to routing table
        self.routing_table.add_route(
            prefix=bgp_announcement.prefix,
            next_hop=bgp_announcement.next_hop,
            as_path=bgp_announcement.as_path
        )

        # 5. Propagate to downstream routers
        self.propagate_to_peers(bgp_announcement)

        return ValidationResult.VALID
```

**Phase 3: Active**

```python
class ActiveBGPEvidence:
    """BGP route is globally propagated and active"""

    def is_active(self, prefix):
        return (
            self.route_announced and
            self.isp_acceptance_rate > 0.95 and  # 95%+ ISPs have route
            self.global_propagation_complete and
            not self.withdrawal_pending
        )

    # During this phase:
    # - Internet can reach Facebook
    # - DNS resolution works
    # - Connections succeed
    # - G-vector: ⟨Global, ..., Fresh(routing), ...⟩
    # - Mode: Target
```

**Phase 4: Withdrawn**

```python
class WithdrawnBGPEvidence:
    """BGP route explicitly withdrawn"""

    def withdraw_route(self, prefix, reason):
        # Send BGP WITHDRAW message
        withdrawal = BGPMessage(
            type='WITHDRAW',
            prefix=prefix,
            reason=reason,
            timestamp=time.now()
        )

        # Propagate withdrawal
        for peer in self.bgp_peers:
            peer.send_withdrawal(withdrawal)

        # ISPs remove from routing tables
        # Propagation: 30-60 seconds for most of internet
        # Result: Facebook becomes unreachable

        return {
            'status': 'WITHDRAWN',
            'reason': reason,
            'propagation_start': time.now(),
            'expected_propagation_complete': time.now() + 60,
            'recovery_possible': has_out_of_band_access()  # FALSE for Facebook!
        }

    # During this phase:
    # - Internet CANNOT reach Facebook
    # - DNS resolution FAILS
    # - Connections FAIL
    # - G-vector: ⟨None, None, None, None, None, None⟩
    # - Mode: BGP Withdrawn (locked out)
```

**Phase 5: The Problem - Can't Re-Generate Evidence**

```python
class CannotRegenerateEvidence:
    """The lock-out problem"""

    def try_to_re_announce_routes(self):
        # To re-announce BGP routes:
        # 1. Need to access edge routers
        # 2. Need to issue BGP ANNOUNCEMENT
        # 3. Need to configure router

        # But HOW to access edge routers?
        try:
            # Try SSH
            self.ssh_to_router(self.edge_router_ip)
        except NoRouteToHost:
            # Can't SSH - no network routes!
            pass

        try:
            # Try management network
            self.access_via_management_network()
        except NoRouteToHost:
            # Management network ALSO down!
            pass

        try:
            # Try out-of-band access
            self.access_via_out_of_band()
        except NotConfigured:
            # Facebook didn't have true OOB access!
            pass

        # LOCKED OUT: Cannot generate new evidence
        # Old evidence: WITHDRAWN (routes gone)
        # New evidence: CANNOT GENERATE (no access)
        # Result: Stuck at ⟨None⟩

        raise LockOutError(
            "Cannot re-announce BGP routes without physical access. "
            "Dispatch engineers to data centers."
        )
```

**Phase 6: Recovery (Physical Access Required)**

```python
class BGPRecoveryViaPhysicalAccess:
    """Generating new evidence requires human intervention"""

    def recover(self):
        # Step 1: Human travels to data center
        engineer = self.dispatch_engineer_to_datacenter()
        # Evidence: Human presence
        # Time: 1-2 hours

        # Step 2: Physical access to building
        engineer.enter_datacenter(requires_manual_badge_override=True)
        # Evidence: Inside data center
        # Time: 30-60 minutes (badge system down!)

        # Step 3: Console access to router
        console = engineer.connect_serial_console(self.edge_router)
        # Evidence: Direct console access
        # G-vector upgrade: ⟨None⟩ → ⟨Local, None, RA, Fresh(console), None, Auth(physical)⟩
        # Time: 15 minutes

        # Step 4: Re-announce BGP routes
        console.execute("router bgp 32934")
        console.execute("announce 157.240.0.0/16")
        console.execute("announce 31.13.64.0/18")
        # Evidence: BGP ANNOUNCEMENT messages sent
        # G-vector upgrade: ⟨Local⟩ → ⟨Regional → Global, None, RA, Fresh(propagating), ...⟩
        # Time: 30 minutes for careful configuration

        # Step 5: Wait for global BGP propagation
        self.wait_for_bgp_convergence()
        # Evidence: ISPs re-add routes to routing tables
        # G-vector upgrade: ⟨Regional⟩ → ⟨Global, None, RA, Fresh(routing), None, None⟩
        # Time: 60 minutes

        # Step 6: Verify services
        self.verify_services_healthy()
        # Evidence: Health checks passing, traffic flowing
        # G-vector upgrade: ⟨Global, None, RA, ...⟩ → ⟨Global, Causal, RA, Fresh(CDN), Idem, Auth⟩
        # Time: 120 minutes (cautious ramp-up)

        # Total: 6+ hours
```

### Evidence Properties

**Scope**: Global (BGP announcements propagate across entire internet)

**Lifetime**: Indefinite (until explicitly withdrawn)

**Binding**: Bound to specific AS (Autonomous System) - Facebook AS32934

**Transitivity**: **TRANSITIVE** - ISPs propagate to other ISPs, routes spread globally

**Revocation**:
- Explicit: BGP WITHDRAW message
- Implicit: AS becomes unreachable (rare)

**Cost**:
- Generation: Very cheap (single BGP message)
- Verification: Medium (BGP propagation time 30-60 seconds)
- Recovery from withdrawal: Very expensive (requires physical access if locked out)

### Evidence During Facebook Outage

```
Timeline:

15:39:00 - Evidence Active
  routes_announced=['157.240.0.0/16', '31.13.64.0/18', '2a03:2880::/32']
  propagation=GLOBAL, acceptance=99%+

15:39:18 - Evidence Withdrawn (CATASTROPHICALLY)
  routes_announced=[]  # ALL WITHDRAWN!
  propagation=GLOBAL (withdrawal propagating)
  acceptance=0% (ISPs removing routes)
  reason='Audit failure triggered safety mechanism'

15:40:00 - Evidence Absent
  routes_announced=[]
  propagation=COMPLETE (all ISPs removed routes)
  facebook_reachable=FALSE
  can_regenerate_evidence=FALSE (locked out!)

16:00:00 - Attempt Recovery (FAILS)
  tried_ssh=FAILED
  tried_vpn=FAILED
  tried_oob=NOT_AVAILABLE
  decision='Need physical access'

17:30:00 - Physical Access Obtained
  engineer_on_site=TRUE
  console_access=AVAILABLE
  can_regenerate_evidence=TRUE

18:00:00 - New Evidence Being Generated
  routes_re_announced=TRUE
  propagation=IN_PROGRESS
  acceptance=10% → 30% → 60% → 95%

21:52:00 - Evidence Active Again
  routes_announced=['157.240.0.0/16', '31.13.64.0/18', '2a03:2880::/32']
  propagation=GLOBAL, acceptance=99%+
  facebook_reachable=TRUE
```

## Part VII: Dualities - The Tensions That Defined the Outage

### Duality 1: Safety ↔ Availability

**Invariant at stake**: Network reachability

**The tension**:
- Safety: Withdraw routes on perceived issues (prevents bad configs from propagating)
- Availability: Keep routes announced (allows users to reach services)

**Facebook's choice during audit failure**:
```python
# Chose SAFETY over AVAILABILITY (extreme)
safety_priority = True   # Withdraw ALL routes on audit failure
availability_priority = False  # Sacrifice reachability entirely

# Result: Complete outage for 6+ hours
```

**What evidence allows movement along spectrum?**
- Strong evidence (out-of-band access exists) → Can prioritize safety
- Weak evidence (no OOB access) → Must prioritize availability
- Facebook had NO OOB access but chose safety anyway → Lock-out

**Which mode?**
- Should have been: Degraded mode (narrow scope, maintain some reachability)
- Actually was: BGP Withdrawn (zero reachability, locked out)

### Duality 2: Automation ↔ Manual Override

**Invariant at stake**: Human control over critical decisions

**The tension**:
- Automation: Fast response, consistent decisions, no human error
- Manual Override: Human judgment, consideration of context, can abort

**Facebook's audit system**:
```python
# Pure automation, no escape hatch
def bgp_audit():
    if audit_fails():
        withdraw_all_routes()  # AUTOMATIC, NO CONFIRMATION
        # No "are you sure?"
        # No manual approval for critical action
        # No ability to abort
        # No verification that recovery is possible

# Should have been hybrid:
def bgp_audit_safe():
    if audit_fails():
        if issue_severity < CRITICAL:
            auto_remediate()  # OK for minor issues
        else:
            alert_human()  # Require approval for critical
            if no_out_of_band_access():
                refuse_to_auto_remediate()  # Don't lock out!
```

**Evidence movement**:
- Automation evidence: "Audit detected issue" (machine judgment)
- Manual evidence: "Human verified issue + recovery possible" (human judgment)
- Facebook relied only on automation evidence → Catastrophic decision

### Duality 3: Remote ↔ Physical

**Invariant at stake**: Access to infrastructure

**The tension**:
- Remote: Fast, convenient, scalable (requires network)
- Physical: Slow, inconvenient, limited (doesn't require network)

**Facebook's architecture**:
```python
# All eggs in remote basket
access_paths = {
    'ssh': 'REQUIRES_NETWORK',
    'vpn': 'REQUIRES_NETWORK',
    'management_network': 'REQUIRES_NETWORK',
    'out_of_band_console': 'MISSING',  # Should have this!
    'physical': 'LAST_RESORT'
}

# When network failed → NO access except physical
# Physical access: 2+ hours to dispatch + travel
```

**What was needed**:
```python
# Defense in depth
access_paths = {
    'ssh': 'PRIMARY (requires network)',
    'vpn': 'SECONDARY (requires different network)',
    'oob_console': 'TERTIARY (serial connection via separate ISP)',
    'physical': 'LAST RESORT (always works)'
}

# With OOB: Recovery in minutes
# Without OOB: Recovery in hours (Facebook's reality)
```

### Duality 4: Centralized ↔ Distributed

**Invariant at stake**: Control plane architecture

**The tension**:
- Centralized: Easy to manage, consistent state (single point of failure)
- Distributed: Resilient, no SPOF (harder to maintain consistency)

**Facebook's centralized control plane**:
```python
# Centralized BGP configuration management
# Single audit system decides for ALL edge routers
# When audit fails → ALL routers withdraw routes
# No regional autonomy, no gradual degradation

class CentralizedBGPControl:
    def audit_and_remediate(self):
        result = self.central_audit()

        if result.failed:
            # Apply decision to ALL routers
            for router in self.all_edge_routers:
                router.withdraw_all_routes()  # SPOF decision!

            # Result: Total outage
```

**Distributed alternative**:
```python
# Distributed control with regional autonomy
class DistributedBGPControl:
    def audit_and_remediate(self):
        for region in self.regions:
            result = region.local_audit()

            if result.failed:
                # Regional decision
                if region.has_out_of_band_access():
                    region.withdraw_routes()  # Safe, can recover
                else:
                    region.alert_and_degrade()  # Don't lock out!

                # Other regions continue operating
                # Blast radius: Single region (not global)
```

### Duality 5: Fail-Safe ↔ Fail-Operational

**Invariant at stake**: System behavior during failures

**The tension**:
- Fail-safe: Halt on errors (safe but unavailable)
- Fail-operational: Continue with degradation (available but risky)

**Facebook's fail-safe approach**:
```python
# Fail-safe: Withdraw routes on audit failure
# Philosophy: "Better offline than broken"
# Problem: Didn't consider that "offline" = "locked out"

class FailSafeBGP:
    def handle_audit_failure(self):
        # Fail-safe: Stop announcing routes
        self.withdraw_all_routes()
        # Safe: Won't propagate bad config
        # Problem: Unavailable for 6+ hours
```

**Fail-operational alternative**:
```python
# Fail-operational: Degrade gracefully
# Philosophy: "Better degraded than offline"

class FailOperationalBGP:
    def handle_audit_failure(self):
        # Fail-operational: Narrow scope but stay reachable
        self.transition_to_degraded_mode()
        # Degraded: Regional instead of Global
        # Benefit: Can recover remotely in minutes
```

### Duality 6: Evidence ↔ Trust

**Invariant at stake**: Configuration correctness

**The tension**:
- Evidence: Verify every config change (slow, safe)
- Trust: Assume configs are correct (fast, risky)

**Facebook's audit system (evidence-based)**:
```python
# Evidence-based: Audit detected (false) issue
# Decision: Don't trust the new config
# Action: Withdraw routes (safety mechanism)
# Problem: Audit was WRONG (false positive)

class EvidenceBasedAudit:
    def validate_config(self, config):
        # Collect evidence: Does config look valid?
        evidence = self.analyze_config(config)

        if evidence.indicates_problem:
            # Don't trust config, withdraw routes
            return AUDIT_FAILED

        return AUDIT_PASSED

# Facebook's mistake:
# - Audit evidence was WRONG (false positive)
# - Trusted the audit more than the config
# - No mechanism to verify audit correctness
# - No human review for critical decisions
```

### Duality 7: Fast Recovery ↔ Safe Recovery

**Invariant at stake**: Recovery time vs. correctness

**The tension**:
- Fast: Restore service quickly (might propagate problem)
- Safe: Verify everything (takes longer)

**Facebook's recovery approach**:
```python
# Chose SAFE over FAST
# Took 6+ hours to:
# - Dispatch engineers (could have been faster with standby)
# - Physical access (delayed by badge system issues)
# - Careful BGP re-announcement (cautious, verified each step)
# - Gradual traffic ramp-up (very conservative)

# Alternative (faster but riskier):
# - Emergency BGP peers (pre-configured, not done)
# - Aggressive re-announcement (might propagate issue if audit was correct)
# - Rapid traffic restoration (might overload recovering systems)
```

## Part VIII: Transfer Tests

### Near Transfer: Apply to DNS Outage

**Scenario**: Your authoritative DNS servers become unreachable due to network routing issue.

**Test 1**: Map the G-vector degradation
```python
# Answer:
normal = '⟨Global, None, RA, Fresh(dns_ttl), Idem(query), Auth(dnssec)⟩'

# DNS servers unreachable
unreachable = '⟨None, None, None, None, None, None⟩'

# Users rely on cached DNS
cached = '⟨Global, None, RA, EO, Idem, Auth(cached)⟩'
# Eventually: Caches expire, users can't resolve domain
```

**Test 2**: What's similar to Facebook BGP case?
```python
# Answer:
# - Network unreachability makes service invisible
# - DNS resolution failure cascades to all dependent services
# - Can't fix DNS servers if can't reach them (lock-out)
# - Need out-of-band access for recovery

# Differences:
# - DNS has TTL (cached values work temporarily)
# - BGP withdrawal was immediate (no cache)
```

**Test 3**: What mode matrix would prevent similar outage?
```python
# Answer:
dns_modes = {
    'Target': {
        'g_vector': '⟨Global, None, RA, Fresh(ttl), Idem, Auth(dnssec)⟩',
        'operations': {'resolve': 'ALLOW', 'update': 'ALLOW'}
    },
    'Degraded': {
        'g_vector': '⟨Regional, None, RA, BS(cached_ttl), Idem, Auth(cached)⟩',
        'operations': {
            'resolve': 'ALLOW (from regional servers)',
            'update': 'QUEUE for later'
        }
    },
    'Floor': {
        'g_vector': '⟨Local, None, RA, EO, Idem, None⟩',
        'operations': {
            'resolve': 'SERVE_STALE_CACHE',
            'update': 'REJECT'
        },
        'fallback': 'Emergency DNS via out-of-band network'
    }
}

# Key: NEVER degrade to ⟨None⟩ without escape hatch
```

### Medium Transfer: Apply to Certificate Expiration Lock-Out

**Scenario**: Your SSL certificates expire, and the certificate management system requires valid certificates to access it (Catch-22).

**Test 1**: Map to Facebook's lock-out problem
```python
# Answer:
# Facebook lock-out: Need network to fix network
# Certificate lock-out: Need valid cert to renew cert

# Both are "can't fix without access" scenarios

# G-vector for cert system:
normal = '⟨Global, None, RA, Fresh(cert_validity), Idem, Auth(tls)⟩'

# Cert expired:
expired = '⟨None, None, None, None, None, None⟩'
# Can't access cert renewal system (requires valid cert)
# Locked out!
```

**Test 2**: What escape hatch is needed?
```python
# Answer:
escape_hatches = {
    'temporary_cert': 'Short-lived cert issued via different path',
    'alternative_auth': 'Username/password for emergency access',
    'out_of_band_renewal': 'Cert renewal via separate network',
    'manual_override': 'Human can approve cert renewal offline'
}

# Similar to Facebook needing out-of-band network access
```

**Test 3**: Design mode matrix for cert management
```python
# Answer:
cert_modes = {
    'Target': {
        'invariant': 'valid_certificates',
        'evidence': 'cert_not_expired + chain_valid',
        'g_vector': '⟨Global, None, RA, Fresh(validity), Idem, Auth(tls)⟩',
        'operations': {'renew': 'ALLOW', 'access': 'ALLOW'}
    },

    'Expiring': {
        'invariant': 'cert_expiring_soon',
        'evidence': 'time_until_expiry < 7_days',
        'g_vector': '⟨Global, None, RA, Fresh(valid), Idem, Auth(tls)⟩',
        'operations': {
            'renew': 'URGENT',
            'access': 'ALLOW',
            'alert': 'CRITICAL - renew or will be locked out'
        }
    },

    'Expired': {
        'invariant': 'cert_expired_but_recoverable',
        'evidence': 'alternative_auth_available',
        'g_vector': '⟨Local, None, RA, None, Idem, Auth(alternative)⟩',
        'operations': {
            'renew': 'ALLOW via alternative auth',
            'access': 'ALLOW via out-of-band',
            'tls_access': 'BLOCKED (cert invalid)'
        },
        'escape_hatch': 'Username/password or physical access'
    }
}

# Key lesson from Facebook: ALWAYS have alternative auth path
```

### Far Transfer: Apply to Smart Home Hub Outage

**Scenario**: Your smart home hub (controls locks, lights, thermostat) requires internet connectivity to function. Internet goes down. You're locked out of your house.

**Test 1**: Map to Facebook's network layer dependency
```python
# Answer:
# Smart home: All control depends on internet connectivity
# Facebook: All operations depend on BGP routing

# Normal operation:
G_smart_home = '⟨Global, None, RA, Fresh(cloud), Idem, Auth(app)⟩'
#               All control via cloud/internet

# Internet down:
G_internet_down = '⟨None, None, None, None, None, None⟩'
# Can't control locks (locked out!)
# Can't control lights (dark!)
# Can't adjust thermostat (uncomfortable!)
```

**Test 2**: What's the physical layer equivalent?
```python
# Answer:
# Facebook: Physical datacenter access (serial console)
# Smart home: Physical key (mechanical lock override)

physical_access = {
    'facebook': 'Serial console to routers',
    'smart_home': 'Physical key to lock',
    'both': 'Requires being physically present'
}

# Lesson: ALWAYS have physical fallback
```

**Test 3**: Design guarantee degradation for smart home
```python
# Answer:
smart_home_architecture = {
    'Target': {
        'g_vector': '⟨Global, None, RA, Fresh(cloud), Idem, Auth(app)⟩',
        'operations': {
            'lock_control': 'Via app/cloud',
            'light_control': 'Via app/cloud',
            'thermostat': 'Via app/cloud'
        }
    },

    'Degraded': {
        'g_vector': '⟨Local, None, RA, BS(cached), Idem, Auth(local)⟩',
        'operations': {
            'lock_control': 'Via local Bluetooth',
            'light_control': 'Via local switches',
            'thermostat': 'Via device buttons',
            'alert': 'Internet down, using local control'
        }
    },

    'Floor': {
        'g_vector': '⟨Local, None, RA, None, None, Auth(physical)⟩',
        'operations': {
            'lock_control': 'Physical key',
            'light_control': 'Wall switches',
            'thermostat': 'Manual controls'
        }
    }
}

# Key insight: Never FULLY depend on network
# ALWAYS have local fallback
# Just like Facebook needed out-of-band access
```

**Test 4**: Compare lock-out scenarios
```python
# Similarities across Facebook, Certs, Smart Home:
common_patterns = {
    'foundation_layer_failure': {
        'facebook': 'Network (BGP)',
        'certs': 'Authentication (TLS)',
        'smart_home': 'Connectivity (Internet)'
    },

    'lock_out_mechanism': {
        'facebook': 'Can\'t access routers without network',
        'certs': 'Can\'t renew cert without valid cert',
        'smart_home': 'Can\'t unlock door without internet'
    },

    'recovery_requirement': {
        'facebook': 'Physical datacenter access',
        'certs': 'Alternative authentication',
        'smart_home': 'Physical key'
    },

    'prevention': {
        'facebook': 'Should have had out-of-band network',
        'certs': 'Should have alternative auth',
        'smart_home': 'Should have local control'
    }
}

# Universal lesson:
# "Always have an escape hatch that doesn't depend on the system being fixed"
```

## Part IX: Canonical Lenses (STA + DCEH)

### STA Triad

**State**: What was unreachable and how

```python
# State analysis during outage
state_analysis = {
    # Network state
    'bgp_routes': {
        'before': ['157.240.0.0/16', '31.13.64.0/18', '2a03:2880::/32'],
        'after': [],  # ALL WITHDRAWN
        'impact': 'Facebook IPs not routable globally'
    },

    # DNS state
    'dns_resolution': {
        'before': 'facebook.com resolves to 157.240.x.x',
        'after': 'NXDOMAIN or timeout',
        'problem': 'DNS servers are inside unreachable network'
    },

    # Service state
    'facebook_services': {
        'before': '3.5 billion users connected',
        'after': '0 users connected',
        'problem': 'Services running but unreachable'
    },

    # Access state
    'engineer_access': {
        'before': 'Remote access via SSH/VPN',
        'after': 'NO remote access (locked out)',
        'workaround': 'Physical datacenter access required'
    }
}
```

**Time**: How long each phase took

```python
# Time analysis during outage
time_analysis = {
    # BGP withdrawal propagation (very fast!)
    'bgp_withdrawal': {
        'start': '15:39:18',
        'isp_tier1_propagation': '15:39:23 (+5 seconds)',
        'isp_tier2_propagation': '15:39:48 (+30 seconds)',
        'global_convergence': '15:40:18 (+60 seconds)',
        'facebook_invisible': '15:40:18 (1 minute total)'
    },

    # Detection and diagnosis
    'incident_response': {
        'users_notice': '15:40:00 (immediate)',
        'engineers_alerted': '15:41:00 (+2 minutes)',
        'scope_understood': '15:50:00 (+11 minutes)',
        'lock_out_realized': '15:55:00 (+16 minutes)',
        'physical_access_decided': '16:00:00 (+21 minutes)'
    },

    # Physical recovery (very slow!)
    'physical_recovery': {
        'engineers_dispatched': '16:00:00',
        'travel_time': '16:00:00 to 17:30:00 (90 minutes)',
        'badge_system_override': '17:30:00 to 18:00:00 (30 minutes)',
        'console_access_obtained': '18:00:00',
        'bgp_re_announced': '18:30:00 (+30 minutes)',
        'global_propagation': '18:30:00 to 19:30:00 (60 minutes)',
        'services_verified': '19:30:00 to 21:52:00 (142 minutes)',
        'full_recovery': '21:52:00 (6 hours 13 minutes total)'
    },

    # Key insight: Withdrawal was instant, recovery took hours
    'asymmetry': {
        'time_to_break': '1 minute (BGP withdrawal)',
        'time_to_fix': '373 minutes (6 hours 13 minutes)',
        'ratio': '373:1 (373x longer to fix than break!)'
    }
}
```

**Agreement**: How BGP consensus broke and reformed

```python
# Agreement analysis during outage
agreement_analysis = {
    # BGP is a consensus protocol
    'bgp_consensus': {
        'normal': 'All ISPs agree: Facebook reachable via AS32934',
        'withdrawal': 'Facebook announces: We are NO LONGER reachable',
        'propagation': 'ISPs update consensus: Facebook unreachable',
        'result': 'Global agreement: Facebook doesn\'t exist on internet'
    },

    # Consensus formation (BGP convergence)
    'convergence_speed': {
        'withdrawal': '60 seconds (fast - removed routes)',
        'recovery': '60+ minutes (slow - added routes + verification)',
        'asymmetry': 'Easier to agree something is gone than something is back'
    },

    # What agreement was needed for recovery:
    'recovery_consensus': {
        'facebook_to_isp': 'Facebook announces: We are back',
        'isp_validation': 'ISPs verify: Announcement looks legitimate',
        'isp_acceptance': 'ISPs add routes back to tables',
        'isp_propagation': 'ISPs tell other ISPs',
        'global_consensus': 'Internet agrees: Facebook reachable again',
        'time_required': '30-60 minutes for global convergence'
    }
}
```

### DCEH Planes

**Data Plane**: User traffic (completely blocked)

```python
# Data plane during outage
data_plane = {
    # User requests
    'http_requests': {
        'normal_rate': '100+ million requests/second',
        'outage_rate': '0 requests/second',
        'user_experience': 'Connection timeout or "can\'t reach server"',
        'impact': '3.5 billion users unable to access'
    },

    # DNS queries
    'dns_queries': {
        'normal_rate': '10+ million queries/second',
        'outage_rate': '10+ million queries/second (still trying!)',
        'response': 'NXDOMAIN or timeout',
        'problem': 'DNS servers unreachable (inside Facebook network)'
    },

    # Mobile apps
    'mobile_apps': {
        'facebook_app': 'Can\'t connect to servers',
        'instagram_app': 'Can\'t load feed',
        'whatsapp': 'Can\'t send messages',
        'impact': 'Users thought apps were broken'
    },

    # What should have happened:
    'graceful_degradation': {
        'should_have': 'Degraded mode with cached content',
        'actually_got': 'Complete failure, no fallback',
        'lesson': 'Data plane needs graceful degradation path'
    }
}
```

**Control Plane**: Management operations (locked out)

```python
# Control plane during outage
control_plane = {
    # Engineering access
    'engineer_operations': {
        'ssh': 'FAILED - no route to host',
        'vpn': 'FAILED - VPN endpoint unreachable',
        'management_network': 'FAILED - also depends on BGP',
        'out_of_band': 'NOT AVAILABLE (missing!)',
        'only_option': 'Physical datacenter access'
    },

    # Automation systems
    'automated_controls': {
        'deployment_system': 'Can\'t reach servers',
        'monitoring': 'Can\'t collect metrics',
        'alerting': 'Can\'t reach alert endpoints',
        'self_healing': 'Can\'t execute fixes (no access)'
    },

    # The irony
    'control_plane_paradox': {
        'problem': 'BGP misconfiguration',
        'solution': 'Reconfigure BGP',
        'access_required': 'Network connectivity',
        'status': 'Network down (that\'s the problem!)',
        'result': 'Lock-out - can\'t fix what you can\'t reach'
    }
}
```

**Evidence Plane**: Observability (blind)

```python
# Evidence plane during outage
evidence_plane = {
    # Internal evidence (all inaccessible)
    'internal_monitoring': {
        'metrics': 'UNREACHABLE - can\'t reach Prometheus/Grafana',
        'logs': 'UNREACHABLE - can\'t reach log aggregators',
        'traces': 'UNREACHABLE - can\'t reach tracing systems',
        'health_checks': 'FAILING - but is it down or unreachable?',
        'dashboards': 'UNREACHABLE - can\'t load dashboards'
    },

    # External evidence (only available evidence!)
    'external_monitoring': {
        'user_reports': 'Twitter exploding with "Facebook is down"',
        'status_checkers': 'downdetector.com showing outage',
        'bgp_looking_glass': 'No Facebook routes visible',
        'ping': 'Host unreachable',
        'traceroute': 'Dead-ends before Facebook network',
        'dns': 'NXDOMAIN for facebook.com'
    },

    # Evidence gap
    'what_engineers_couldnt_see': {
        'server_status': 'Are servers running? (Couldn\'t tell)',
        'service_health': 'Are services healthy? (Couldn\'t tell)',
        'database_state': 'Is data intact? (Couldn\'t tell)',
        'only_knew': 'BGP routes withdrawn, Facebook unreachable'
    },

    # Evidence-based decisions
    'decisions_made_blind': {
        'assume_services_running': 'Likely true (no reason they\'d crash)',
        'assume_data_intact': 'Likely true (storage systems separate)',
        'problem_is_bgp': 'Confirmed by external BGP looking glass',
        'solution_is_physical_access': 'Only option given lock-out'
    }
}
```

**Human Plane**: Engineer actions and mental models

```python
# Human plane during outage
human_plane = {
    # Initial response
    'engineer_mental_model': {
        'first_thought': '"Why can\'t I SSH to servers?"',
        'second_thought': '"Is network down? Check VPN."',
        'third_thought': '"VPN also down? Check management network."',
        'fourth_thought': '"Everything unreachable? OH NO - BGP!"',
        'realization': '"We withdrew ALL our BGP routes. We\'re LOCKED OUT."',
        'panic': '"We can\'t fix this remotely. Need physical access."'
    },

    # Decision making under pressure
    'critical_decisions': {
        '15:45': {
            'decision': 'Try all remote access methods',
            'result': 'All failed',
            'time_cost': '15 minutes'
        },
        '16:00': {
            'decision': 'Dispatch engineers to data centers',
            'rationale': 'Only option - need physical access',
            'time_cost': '90 minutes travel time'
        },
        '17:30': {
            'decision': 'Override badge system manually',
            'rationale': 'Badge system also down (needs network)',
            'time_cost': '30 minutes'
        },
        '18:00': {
            'decision': 'Console into routers, re-announce BGP carefully',
            'rationale': 'Don\'t want to cause another issue',
            'time_cost': '30 minutes careful configuration'
        },
        '18:30': {
            'decision': 'Gradual traffic ramp-up',
            'rationale': 'Verify services healthy at each step',
            'time_cost': '3+ hours cautious recovery'
        }
    },

    # Lessons learned
    'human_factors': {
        'automation_trust': 'Trusted audit system too much (false positive)',
        'no_escape_hatch': 'Didn\'t have manual override for critical decision',
        'no_oob_access': 'Didn\'t prioritize out-of-band access (seemed unnecessary)',
        'badge_system_irony': 'Even physical security relied on network',
        'recovery_stress': '6 hours of high-pressure incident response'
    }
}
```

## Part X: Lessons Through the Framework Lens

### Lesson 1: Network Reachability is Foundational

**What Facebook learned**:
```python
g_application = '⟨Global, Causal, RA, Fresh(CDN), Idem, Auth⟩'
g_network = '⟨Global, None, RA, Fresh(routing), None, None⟩'

# Application depends on network
g_end_to_end = g_application ▷ g_network
             = meet(g_application, g_network)

# If network fails:
g_network_failed = '⟨None, None, None, None, None, None⟩'
g_end_to_end = meet(g_application, g_network_failed)
             = '⟨None, None, None, None, None, None⟩'

# COMPLETE COLLAPSE
```

**Framework insight**: Network layer is so foundational that its failure collapses ALL higher-layer guarantees. No amount of application-layer redundancy helps if packets can't route.

**Architectural principle**: Always have multiple independent network paths, including at least one that doesn't depend on the production BGP infrastructure.

### Lesson 2: Safety Mechanisms Need Escape Hatches

**Facebook's failure**: Safety mechanism without override

```python
# What they had:
def bgp_audit():
    if audit_fails():
        withdraw_all_routes()  # No escape hatch!
        # LOCKED OUT

# What they needed:
def bgp_audit_safe():
    if audit_fails():
        if has_out_of_band_access():
            withdraw_routes()  # Safe - can recover
        else:
            alert_human_for_approval()  # Don't lock out!
```

**Framework principle**: Before any automated action that could cause lock-out:
1. Verify recovery path exists (out-of-band access)
2. If no recovery path, REQUIRE human approval
3. Never automate irreversible actions without escape hatch

### Lesson 3: Lock-Out Scenarios Require Defense in Depth

**Facebook's single point of failure**: All access via BGP-routed network

```python
# What they had:
access_paths = ['ssh', 'vpn', 'management_network']
# ALL depend on BGP routing
# BGP fails → ALL paths fail → LOCKED OUT

# What they needed:
access_paths = [
    'ssh via production network',      # Primary
    'vpn via separate ISP',            # Secondary
    'console server via 4G/LTE',       # Tertiary
    'physical datacenter access'       # Last resort
]
# Multiple INDEPENDENT paths
# Even if BGP fails, other paths available
```

**Framework insight**: Out-of-band access is not a luxury, it's a necessity. Every critical system must have an access path that doesn't depend on the system being fixed.

### Lesson 4: Evidence Disappears When Network Partitions

**Facebook's blindness during outage**:
```python
# Normal: Rich evidence
internal_evidence = ['metrics', 'logs', 'traces', 'health_checks']

# Outage: No evidence
internal_evidence = []  # All unreachable!

# Only external evidence:
external_evidence = ['user_reports', 'bgp_looking_glass', 'social_media']
```

**Framework principle**: Design observability with assumption that internal network will fail. Need external monitoring that doesn't depend on production network.

### Lesson 5: Recovery Time Asymmetry

**Facebook's reality**:
```python
time_to_break = 1 minute  # BGP withdrawal propagates fast
time_to_fix = 373 minutes  # Physical access + recovery

asymmetry_ratio = 373:1
```

**Framework insight**: Systems that fail quickly but recover slowly are dangerous. Design for:
1. Slower, more cautious degradation (don't jump straight to ⟨None⟩)
2. Faster recovery paths (out-of-band access)
3. Graceful degradation (floor mode that maintains some reachability)

### Lesson 6: Automation Without Override is Dangerous

**The BGP audit mistake**:
```python
# Audit detected issue (false positive)
# Automation kicked in (no human judgment)
# Withdrew ALL routes (no confirmation)
# Locked out engineers (no escape hatch)
# Recovery took 6+ hours (catastrophic)
```

**Framework principle**: Critical decisions require human judgment:
- Automation for speed: Minor issues, reversible actions
- Human approval for: Major issues, irreversible actions, no-escape-hatch scenarios

## Mental Model Summary

**Facebook's outage through the framework**:

1. **G-vectors collapsed** from `⟨Global, Causal, RA, Fresh(CDN), Idem, Auth⟩` to `⟨None, None, None, None, None, None⟩` because:
   - BGP routes withdrawn (network layer failure)
   - Network layer is foundational
   - All higher layers depend on network reachability
   - Scope collapsed: Global → None

2. **Lock-out scenario** occurred because:
   - All access paths depended on BGP routing
   - No out-of-band access configured
   - Can't fix routers without reaching routers
   - Physical access required (2+ hours)

3. **Safety mechanism backfired**:
   - Audit detected perceived issue
   - Automated response: Withdraw ALL routes
   - No escape hatch, no confirmation
   - Safety mechanism created unfixable situation

4. **Evidence plane blind**:
   - Internal monitoring unreachable
   - Logs unreachable
   - Metrics unreachable
   - Only external evidence available
   - Engineers operating blind

5. **Recovery required physical intervention**:
   - Dispatch engineers to data centers
   - Serial console access (only path)
   - Manual BGP re-announcement
   - 6+ hours total recovery time

**The revolutionary insight**: If Facebook had:
1. **Out-of-band access** → Could recover in minutes (not hours)
2. **Gradual degradation** → Could narrow to regional instead of withdrawing all routes
3. **Escape hatch in audit** → Could require human approval for critical decisions
4. **Mode matrix** → Could transition Target → Degraded → Floor (not Target → None)

**The broader lesson**: Network reachability is THE foundational guarantee. When it fails, EVERYTHING fails. Therefore:
- Always have independent access paths
- Never automate network changes without escape hatches
- Design for graceful degradation (don't collapse to ⟨None⟩)
- Out-of-band access is mandatory, not optional

This is the power of the framework: Understanding that network layer failures cascade catastrophically, and designing systems with defense in depth, escape hatches, and recovery paths that don't depend on the failing system.

---

**Context capsule for next case study**:
```
{
  invariant: "Foundation_Layer_Criticality",
  evidence: "BGP_teaches_network_is_foundational",
  boundary: "infrastructure_dependencies",
  mode: "analyzing_cascade_patterns",
  g_vector: "⟨Global, Causal, RA, BS(examples), Idem, Auth(research)⟩"
}
```

Continue to [Cloudflare Regex Outage →](cloudflare-regex.md)
