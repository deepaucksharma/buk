# Security Mode Matrices: Adaptive Defense Through Evidence
## Dynamic Security Postures in Distributed Systems

*A framework for evidence-based security mode transitions*

---

## Introduction: Security as a Spectrum

Security is not binary—it's a spectrum of trust levels, each with different evidence requirements, performance impacts, and threat models. Systems must dynamically adapt their security posture based on current threats, available evidence, and operational requirements.

This document defines comprehensive mode matrices for security systems, showing how to transition between security levels based on evidence while maintaining system availability.

---

## Part I: Master Security Mode Matrix

### Core Security Modes

| Mode | Trust Model | Evidence Required | Performance Impact | Use Case |
|------|------------|-------------------|-------------------|----------|
| **Paranoid** | Zero Trust + Continuous Verification | Cryptographic + Biometric + Behavioral | 70% throughput reduction | Active attack detected |
| **Strict** | Zero Trust | Cryptographic + MFA | 30% throughput reduction | Production default |
| **Standard** | Trust but Verify | Password + MFA | 10% throughput reduction | Internal services |
| **Relaxed** | Perimeter Trust | Password only | Minimal impact | Development/Testing |
| **Emergency** | Break-glass Override | Emergency token | No verification overhead | System recovery |

### Detailed Mode Specifications

#### Paranoid Mode (Maximum Security)
```yaml
paranoid_mode:
  authentication:
    factors_required: 3
    methods:
      - password_complexity: high
      - hardware_token: required
      - biometric: required
    session_lifetime: 5_minutes
    continuous_verification: enabled

  authorization:
    model: zero_trust_continuous
    policy_evaluation: every_request
    privilege_elevation: disabled
    lateral_movement: blocked

  cryptography:
    tls_version: "1.3_only"
    cipher_suites:
      - TLS_AES_256_GCM_SHA384
    perfect_forward_secrecy: required
    certificate_pinning: enforced

  monitoring:
    log_level: debug
    log_everything: true
    anomaly_detection: real_time
    behavior_analysis: continuous

  rate_limiting:
    requests_per_second: 10
    burst_size: 20
    per_user_limit: 100_per_hour

  network:
    ip_allowlist: enforced
    geo_blocking: enabled
    tor_exit_nodes: blocked
    vpn_detection: alert
```

#### Strict Mode (Production Security)
```yaml
strict_mode:
  authentication:
    factors_required: 2
    methods:
      - password_complexity: medium
      - totp_or_sms: required
    session_lifetime: 30_minutes
    continuous_verification: disabled

  authorization:
    model: zero_trust
    policy_evaluation: cached_5_min
    privilege_elevation: sudo_mode
    lateral_movement: restricted

  cryptography:
    tls_version: "1.2+"
    cipher_suites:
      - TLS_AES_256_GCM_SHA384
      - TLS_AES_128_GCM_SHA256
    perfect_forward_secrecy: preferred
    certificate_pinning: optional

  monitoring:
    log_level: info
    log_security_events: true
    anomaly_detection: batch_5_min
    behavior_analysis: periodic

  rate_limiting:
    requests_per_second: 100
    burst_size: 500
    per_user_limit: 10000_per_hour

  network:
    ip_allowlist: optional
    geo_blocking: high_risk_only
    tor_exit_nodes: monitored
    vpn_detection: logged
```

#### Standard Mode (Balanced Security)
```yaml
standard_mode:
  authentication:
    factors_required: 2
    methods:
      - password_complexity: medium
      - optional_mfa: encouraged
    session_lifetime: 8_hours
    continuous_verification: disabled

  authorization:
    model: rbac
    policy_evaluation: cached_30_min
    privilege_elevation: password
    lateral_movement: allowed

  cryptography:
    tls_version: "1.2+"
    cipher_suites: standard_set
    perfect_forward_secrecy: optional
    certificate_pinning: disabled

  monitoring:
    log_level: warning
    log_security_events: true
    anomaly_detection: hourly
    behavior_analysis: daily

  rate_limiting:
    requests_per_second: 1000
    burst_size: 5000
    per_user_limit: unlimited

  network:
    ip_allowlist: disabled
    geo_blocking: disabled
    tor_exit_nodes: allowed
    vpn_detection: ignored
```

#### Relaxed Mode (Development)
```yaml
relaxed_mode:
  authentication:
    factors_required: 1
    methods:
      - password_complexity: low
      - mfa: optional
    session_lifetime: 24_hours
    continuous_verification: disabled

  authorization:
    model: basic_acl
    policy_evaluation: cached_1_hour
    privilege_elevation: none
    lateral_movement: unrestricted

  cryptography:
    tls_version: "1.0+"
    cipher_suites: all_available
    perfect_forward_secrecy: disabled
    certificate_pinning: disabled

  monitoring:
    log_level: error
    log_security_events: minimal
    anomaly_detection: disabled
    behavior_analysis: disabled

  rate_limiting:
    requests_per_second: unlimited
    burst_size: unlimited
    per_user_limit: unlimited

  network:
    ip_allowlist: disabled
    geo_blocking: disabled
    tor_exit_nodes: allowed
    vpn_detection: ignored
```

#### Emergency Mode (Break-glass)
```yaml
emergency_mode:
  authentication:
    factors_required: 1
    methods:
      - emergency_token: time_limited
    session_lifetime: 1_hour_max
    continuous_verification: disabled

  authorization:
    model: admin_override
    policy_evaluation: bypassed
    privilege_elevation: pre_authorized
    lateral_movement: unrestricted

  cryptography:
    tls_version: any_available
    cipher_suites: any_available
    perfect_forward_secrecy: optional
    certificate_pinning: disabled

  monitoring:
    log_level: audit_everything
    log_security_events: comprehensive
    anomaly_detection: disabled
    behavior_analysis: post_incident

  rate_limiting:
    requests_per_second: unlimited
    burst_size: unlimited
    per_user_limit: unlimited

  network:
    ip_allowlist: disabled
    geo_blocking: disabled
    tor_exit_nodes: allowed
    vpn_detection: ignored
```

---

## Part II: Mode Transition Matrix

### Transition Rules

| From → To | Evidence Required | Approval Needed | Automatic | Time Limit |
|-----------|------------------|-----------------|-----------|------------|
| Standard → Strict | Anomaly score > 0.7 | No | Yes | Until cleared |
| Strict → Paranoid | Attack indicators ≥ 3 | Security team | Yes | 1 hour max |
| Standard → Relaxed | Dev environment flag | No | Yes | Permanent |
| Any → Emergency | System failure + 2 approvers | VP Engineering | No | 1 hour max |
| Paranoid → Strict | No attacks for 1 hour | Security team | Yes | N/A |
| Strict → Standard | No anomalies for 24 hours | No | Yes | N/A |
| Emergency → Previous | Emergency expired | Automatic | Yes | N/A |

### Transition Evidence Requirements

#### Escalation to Strict Mode
```json
{
  "transition": "standard_to_strict",
  "timestamp": "2024-01-15T10:30:00Z",
  "evidence": {
    "anomaly_score": 0.75,
    "indicators": [
      {
        "type": "failed_login_spike",
        "value": 150,
        "baseline": 10,
        "deviation": "15x"
      },
      {
        "type": "unusual_access_pattern",
        "confidence": 0.82,
        "details": "accessing_multiple_unrelated_resources"
      }
    ]
  },
  "actions": [
    "enable_mfa_for_all",
    "reduce_session_timeout",
    "increase_logging",
    "notify_security_team"
  ]
}
```

#### Escalation to Paranoid Mode
```json
{
  "transition": "strict_to_paranoid",
  "timestamp": "2024-01-15T10:35:00Z",
  "evidence": {
    "attack_confirmed": true,
    "indicators": [
      {
        "type": "credential_stuffing",
        "attempts": 50000,
        "unique_ips": 1000,
        "success_rate": 0.02
      },
      {
        "type": "data_exfiltration_attempt",
        "volume_gb": 50,
        "destination": "unknown_ip"
      },
      {
        "type": "privilege_escalation",
        "user": "compromised_account",
        "attempted_action": "create_admin_user"
      }
    ]
  },
  "actions": [
    "revoke_all_sessions",
    "block_suspicious_ips",
    "enable_continuous_verification",
    "require_biometric",
    "limit_to_essential_operations"
  ]
}
```

#### Emergency Mode Activation
```json
{
  "transition": "any_to_emergency",
  "timestamp": "2024-01-15T10:40:00Z",
  "trigger": "authentication_system_failure",
  "evidence": {
    "failed_components": [
      "primary_idp",
      "backup_idp",
      "mfa_service"
    ],
    "impact": "no_user_authentication_possible",
    "affected_users": "all",
    "business_impact": "critical"
  },
  "approval": {
    "approver_1": {
      "name": "John Smith",
      "role": "VP_Engineering",
      "timestamp": "2024-01-15T10:41:00Z"
    },
    "approver_2": {
      "name": "Jane Doe",
      "role": "Security_Lead",
      "timestamp": "2024-01-15T10:41:30Z"
    }
  },
  "emergency_token": {
    "token": "EMERGENCY-2024-01-15-xyz789",
    "expires": "2024-01-15T11:40:00Z",
    "scope": "full_admin",
    "audit": "comprehensive"
  }
}
```

---

## Part III: Service-Specific Mode Matrices

### API Gateway Security Modes

| Mode | Auth Method | Rate Limit | WAF Rules | Response Time |
|------|------------|------------|-----------|---------------|
| **Paranoid** | mTLS + JWT + API Key | 10 req/s | All enabled | +200ms |
| **Strict** | JWT + API Key | 100 req/s | Critical only | +50ms |
| **Standard** | API Key only | 1000 req/s | Basic set | +10ms |
| **Relaxed** | Optional API Key | Unlimited | Monitoring | +5ms |
| **Emergency** | Bypass | Unlimited | Disabled | Baseline |

### Database Security Modes

| Mode | Connection | Encryption | Audit | Query Filtering |
|------|------------|------------|-------|-----------------|
| **Paranoid** | mTLS required | Column-level | Everything | All queries reviewed |
| **Strict** | TLS required | Table-level | Writes + Sensitive | Sensitive tables filtered |
| **Standard** | TLS preferred | Transport only | Writes only | No filtering |
| **Relaxed** | Plain allowed | None | Errors only | No filtering |
| **Emergency** | Any | Optional | Post-recovery | Disabled |

### Kubernetes Cluster Security Modes

| Mode | Pod Security | Network Policy | Image Scanning | Admission Control |
|------|--------------|----------------|----------------|-------------------|
| **Paranoid** | Restricted PSP | Deny-all default | Block on any CVE | All webhooks |
| **Strict** | Baseline PSP | Namespace isolation | Block on High CVE | Critical webhooks |
| **Standard** | Privileged allowed | Service isolation | Warn on CVE | Basic validation |
| **Relaxed** | No restrictions | Open | Optional | Disabled |
| **Emergency** | Bypass all | Open | Skip | Disabled |

---

## Part IV: Evidence-Driven Transitions

### Attack Detection Evidence Chain

```
Normal Operation
      ↓
[Anomaly Detection]
   Score: 0.3
      ↓
[Threshold Check]
   Score < 0.7
      ↓
Remain in Standard

      OR

[Anomaly Detection]
   Score: 0.8
      ↓
[Threshold Check]
   Score > 0.7
      ↓
Escalate to Strict
      ↓
[Attack Correlation]
   3+ indicators
      ↓
Escalate to Paranoid
```

### Evidence Types and Weights

| Evidence Type | Weight | Paranoid Threshold | Strict Threshold |
|---------------|--------|-------------------|------------------|
| Failed Login Spike | 0.3 | 50+ failures | 20+ failures |
| Geographic Anomaly | 0.2 | Impossible travel | New country |
| Time Anomaly | 0.1 | Non-business hours | Unusual hours |
| Resource Access | 0.2 | Unauthorized attempt | Unusual pattern |
| Data Volume | 0.2 | 10x baseline | 5x baseline |
| Privilege Escalation | 0.5 | Any attempt | Suspicious request |
| Known Attack Pattern | 0.8 | Pattern match | Partial match |
| Threat Intelligence | 0.6 | IP in threat feed | Suspicious ASN |

### Composite Score Calculation

```python
def calculate_threat_score(evidence):
    """Calculate weighted threat score from evidence"""
    score = 0
    weights_sum = 0

    for indicator in evidence:
        weight = EVIDENCE_WEIGHTS[indicator.type]
        value = normalize_indicator_value(indicator)
        score += weight * value
        weights_sum += weight

    # Normalize to 0-1 range
    if weights_sum > 0:
        score = score / weights_sum

    # Apply time decay for older evidence
    score = apply_time_decay(score, evidence.timestamp)

    return min(1.0, score)

def determine_security_mode(threat_score):
    """Determine appropriate security mode from threat score"""
    if threat_score >= 0.9:
        return "paranoid"
    elif threat_score >= 0.7:
        return "strict"
    elif threat_score >= 0.3:
        return "standard"
    else:
        return "relaxed"
```

---

## Part V: Mode-Specific Policies

### Authentication Policies by Mode

#### Paranoid Mode Authentication
```yaml
authentication_policy:
  name: paranoid_auth
  requirements:
    - password:
        min_length: 16
        complexity: high
        rotation: 30_days
        history: 12
    - mfa:
        type: hardware_token
        required: always
        timeout: 30_seconds
    - biometric:
        type: fingerprint_or_face
        required: true
        liveness_check: enabled
    - device:
        registered: required
        compliance: enforced
        attestation: required
    - location:
        geofencing: enabled
        vpn_blocked: true
        tor_blocked: true
  session:
    duration: 5_minutes
    idle_timeout: 2_minutes
    concurrent: 1
    binding: ip_and_device
  verification:
    continuous: true
    interval: 60_seconds
    methods: [behavior, location, device]
```

#### Emergency Mode Authentication
```yaml
authentication_policy:
  name: emergency_auth
  requirements:
    - emergency_token:
        format: "EMRG-YYYY-MM-DD-RANDOM"
        generation: two_person_rule
        validity: 60_minutes
        single_use: false
  session:
    duration: 60_minutes_max
    idle_timeout: none
    concurrent: unlimited
    binding: none
  audit:
    level: everything
    retention: permanent
    real_time_alert: true
  restrictions:
    - notification: all_admins
    - recording: session_replay
    - approval: post_facto_review
```

### Authorization Policies by Mode

#### Strict Mode Authorization
```yaml
authorization_policy:
  name: strict_authz
  model: zero_trust_rbac
  evaluation:
    cache: 5_minutes
    mode: pessimistic
  rules:
    - effect: deny
      principal: "*"
      resource: "*"
      action: "*"
    - effect: allow
      principal:
        authenticated: true
        mfa: true
        groups: [employees]
      resource:
        classification: [public, internal]
      action: [read]
    - effect: allow
      principal:
        authenticated: true
        mfa: true
        groups: [admins]
      resource: "*"
      action: "*"
      condition:
        - ip_range: 10.0.0.0/8
        - time: business_hours
        - approval: required_for_sensitive
```

---

## Part VI: Performance Impact Analysis

### Mode Performance Characteristics

| Operation | Paranoid | Strict | Standard | Relaxed | Emergency |
|-----------|----------|--------|----------|---------|-----------|
| Auth Latency | +500ms | +100ms | +50ms | +10ms | 0ms |
| Authz Latency | +200ms | +50ms | +20ms | +5ms | 0ms |
| Crypto Overhead | +100ms | +30ms | +10ms | +5ms | Optional |
| Logging Overhead | +50ms | +20ms | +10ms | +2ms | +30ms |
| **Total Overhead** | +850ms | +200ms | +90ms | +22ms | +30ms |
| **Throughput** | 30% | 70% | 90% | 98% | 100% |
| **CPU Usage** | +300% | +100% | +50% | +10% | +5% |
| **Memory Usage** | +200% | +80% | +40% | +10% | +20% |

### Capacity Planning by Mode

```yaml
capacity_requirements:
  paranoid:
    instances_needed: 10x_baseline
    cpu_cores: 32_per_instance
    memory_gb: 64_per_instance
    network_gbps: 10
    storage_iops: 50000

  strict:
    instances_needed: 3x_baseline
    cpu_cores: 16_per_instance
    memory_gb: 32_per_instance
    network_gbps: 5
    storage_iops: 20000

  standard:
    instances_needed: 1.5x_baseline
    cpu_cores: 8_per_instance
    memory_gb: 16_per_instance
    network_gbps: 2
    storage_iops: 10000

  relaxed:
    instances_needed: 1x_baseline
    cpu_cores: 4_per_instance
    memory_gb: 8_per_instance
    network_gbps: 1
    storage_iops: 5000
```

---

## Part VII: Mode Transition Orchestration

### Automated Transition Pipeline

```python
class SecurityModeOrchestrator:
    def __init__(self):
        self.current_mode = "standard"
        self.transition_history = []
        self.evidence_buffer = deque(maxlen=1000)

    def evaluate_mode_transition(self):
        """Continuously evaluate if mode transition needed"""
        while True:
            # Collect evidence
            evidence = self.collect_evidence()
            self.evidence_buffer.append(evidence)

            # Calculate threat score
            threat_score = self.calculate_composite_score()

            # Determine target mode
            target_mode = self.determine_target_mode(threat_score)

            # Execute transition if needed
            if target_mode != self.current_mode:
                self.execute_transition(target_mode, evidence)

            # Wait before next evaluation
            sleep(self.get_evaluation_interval())

    def execute_transition(self, target_mode, evidence):
        """Execute mode transition with all required changes"""
        transition = {
            "from": self.current_mode,
            "to": target_mode,
            "timestamp": datetime.utcnow(),
            "evidence": evidence,
            "actions": []
        }

        # Update authentication requirements
        transition["actions"].append(
            self.update_auth_requirements(target_mode)
        )

        # Update authorization policies
        transition["actions"].append(
            self.update_authz_policies(target_mode)
        )

        # Update rate limits
        transition["actions"].append(
            self.update_rate_limits(target_mode)
        )

        # Update monitoring level
        transition["actions"].append(
            self.update_monitoring(target_mode)
        )

        # Update network policies
        transition["actions"].append(
            self.update_network_policies(target_mode)
        )

        # Send notifications
        self.notify_stakeholders(transition)

        # Record transition
        self.transition_history.append(transition)
        self.current_mode = target_mode

        # Log for audit
        self.audit_log(transition)
```

### Transition Validation

```python
def validate_transition(from_mode, to_mode, evidence):
    """Validate if transition is allowed and safe"""

    # Check transition rules
    if not is_transition_allowed(from_mode, to_mode):
        raise InvalidTransitionError(f"Cannot transition from {from_mode} to {to_mode}")

    # Verify evidence sufficiency
    if not is_evidence_sufficient(to_mode, evidence):
        raise InsufficientEvidenceError(f"Insufficient evidence for {to_mode}")

    # Check approval requirements
    if requires_approval(from_mode, to_mode):
        approval = get_approval(from_mode, to_mode, evidence)
        if not approval:
            raise ApprovalRequiredError(f"Approval needed for {to_mode}")

    # Verify system capacity
    if not has_capacity_for_mode(to_mode):
        raise InsufficientCapacityError(f"Insufficient capacity for {to_mode}")

    # Test critical services
    if not test_mode_compatibility(to_mode):
        raise CompatibilityError(f"Services incompatible with {to_mode}")

    return True
```

---

## Part VIII: Monitoring and Alerting

### Mode-Specific Metrics

```yaml
metrics_by_mode:
  paranoid:
    authentication:
      - mfa_success_rate
      - biometric_failure_rate
      - continuous_verification_latency
      - session_timeout_count
    authorization:
      - policy_evaluation_time_p99
      - zero_trust_check_failures
      - privilege_escalation_attempts
    performance:
      - request_latency_p99
      - throughput_reduction_percent
      - cpu_utilization
      - memory_pressure
    security:
      - attack_attempts_blocked
      - anomaly_detection_rate
      - false_positive_rate

  strict:
    authentication:
      - mfa_adoption_rate
      - failed_login_rate
      - session_duration_avg
    authorization:
      - policy_cache_hit_rate
      - unauthorized_access_attempts
    performance:
      - request_latency_p95
      - throughput_vs_baseline
    security:
      - suspicious_activity_count
      - threat_score_avg

  standard:
    authentication:
      - login_success_rate
      - password_reset_rate
    authorization:
      - access_grant_rate
    performance:
      - request_latency_p50
      - error_rate
    security:
      - security_event_count
```

### Alert Thresholds by Mode

```yaml
alert_thresholds:
  paranoid:
    failed_auth_rate:
      threshold: 5_per_minute
      action: immediate_lockdown
    anomaly_score:
      threshold: 0.5
      action: investigate_immediately
    latency_p99:
      threshold: 2000ms
      action: scale_resources

  strict:
    failed_auth_rate:
      threshold: 20_per_minute
      action: increase_monitoring
    anomaly_score:
      threshold: 0.7
      action: notify_security
    latency_p99:
      threshold: 500ms
      action: investigate

  standard:
    failed_auth_rate:
      threshold: 50_per_minute
      action: log_and_monitor
    anomaly_score:
      threshold: 0.9
      action: create_ticket
    latency_p99:
      threshold: 200ms
      action: notify_ops
```

---

## Part IX: Recovery and Rollback

### Mode Recovery Procedures

#### Recovering from Paranoid Mode
```yaml
recovery_from_paranoid:
  prerequisites:
    - no_active_attacks_for: 1_hour
    - threat_score_below: 0.5
    - security_team_approval: true
  steps:
    1_assess:
      - review_attack_indicators
      - analyze_damage
      - identify_compromised_accounts
    2_stabilize:
      - patch_vulnerabilities
      - reset_compromised_credentials
      - update_security_rules
    3_transition:
      - gradually_reduce_restrictions
      - restore_normal_session_timeouts
      - re_enable_cached_authorization
    4_monitor:
      - watch_for_attack_resumption
      - track_performance_recovery
      - validate_user_access
  rollback_triggers:
    - threat_score_exceeds: 0.7
    - attack_indicators_detected: true
    - manual_override: security_team
```

#### Recovering from Emergency Mode
```yaml
recovery_from_emergency:
  prerequisites:
    - primary_auth_system: online
    - audit_log_review: complete
    - emergency_token_expired: true
  steps:
    1_audit:
      - review_all_emergency_actions
      - identify_unauthorized_changes
      - document_incident
    2_restore:
      - revoke_emergency_tokens
      - restore_normal_authentication
      - re_enable_authorization
    3_validate:
      - verify_user_access
      - test_critical_flows
      - check_data_integrity
    4_remediate:
      - fix_root_cause
      - update_runbooks
      - schedule_postmortem
  mandatory_actions:
    - compliance_report: required
    - security_review: required
    - executive_briefing: if_duration_exceeds_2_hours
```

---

## Implementation Checklist

### Phase 1: Design
- [ ] Define security modes for your environment
- [ ] Map evidence types to threat scores
- [ ] Design transition rules and thresholds
- [ ] Create approval workflows
- [ ] Plan capacity for each mode

### Phase 2: Implementation
- [ ] Implement mode orchestrator
- [ ] Configure authentication policies per mode
- [ ] Set up authorization rules per mode
- [ ] Deploy monitoring and alerting
- [ ] Create transition automation

### Phase 3: Testing
- [ ] Test mode transitions under load
- [ ] Validate evidence collection
- [ ] Verify rollback procedures
- [ ] Test emergency mode activation
- [ ] Run security drills

### Phase 4: Operation
- [ ] Monitor mode transitions
- [ ] Track false positive rate
- [ ] Measure performance impact
- [ ] Review and adjust thresholds
- [ ] Maintain compliance documentation

---

## Conclusion

Security Mode Matrices enable adaptive defense that responds to threats while maintaining availability. By defining clear modes, transition rules, and evidence requirements, systems can automatically adjust their security posture based on real-time threat assessment.

Key principles:
1. **Evidence-driven transitions**: Never change modes without evidence
2. **Gradual escalation**: Move through modes progressively
3. **Automatic recovery**: Return to normal when threats subside
4. **Performance awareness**: Understand the cost of security
5. **Audit everything**: Maintain complete records for compliance

Remember: The goal is not maximum security at all times, but appropriate security based on current threats and business needs.

---

*"Security modes are not about paranoia or complacency, but about matching defensive posture to actual threat level with evidence-based transitions."*