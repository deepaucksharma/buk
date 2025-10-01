# Coherence Validation - Quick Start Guide

## TL;DR - For Authors

Before submitting a chapter for review:

```bash
# Validate your chapter
python3 chapter_validator.py site/docs/chapter-XX/index.md

# Get detailed feedback
python3 chapter_validator.py --verbose site/docs/chapter-XX/index.md

# Generate HTML report for review
python3 chapter_validator.py --format html --output report.html site/docs/chapter-XX/index.md
```

**Minimum passing score: 70/100**

**Critical requirements:**
- At least one G-vector with proper syntax
- All 4 modes defined (Floor, Target, Degraded, Recovery)
- Evidence properties specified (Scope, Lifetime, Binding, Transitivity, Revocation)
- Primary invariant from catalog
- 3 transfer tests (Near, Medium, Far)
- 3-pass spiral structure (Intuition → Understanding → Mastery)

---

## For Reviewers

### Quick Review Process

1. **Run automated validation:**
   ```bash
   python3 chapter_validator.py --verbose site/docs/chapter-XX/index.md
   ```

2. **Check score:**
   - 90-100: PASS - Ready to publish
   - 80-89: PASS - Minor revisions
   - 70-79: CONDITIONAL - Major items needed
   - Below 70: FAIL - Significant work required

3. **Review critical dimensions manually:**
   - Invariant mapping correctness (Section 2.1)
   - Evidence lifecycle completeness (Section 2.2)
   - Composition soundness (Section 2.3)
   - Transfer test quality (Section 2.4)
   - Pedagogical flow (Section 2.5)

4. **Use the reviewer checklist:**
   - See Appendix B in CoherenceValidationChecklist.md
   - Complete the one-page form
   - Provide specific line numbers for issues

---

## Common Validation Failures and Quick Fixes

### 1. No G-Vectors Found (0/10)

**Problem:** Chapter discusses guarantees but doesn't use typed vectors.

**Quick fix:**
```markdown
**Service A Guarantees:**
G_A = ⟨Range, Lx, SI, Fresh(φ), Idem(K), Auth(π)⟩

**Service B Guarantees:**
G_B = ⟨Global, Causal, RA, BS(200ms), None, Unauth⟩

**Composed (A ▷ B):**
G_end = meet(G_A, G_B) = ⟨Range, Causal, RA, BS(200ms), None, Unauth⟩
```

---

### 2. Missing Modes (0-7/10)

**Problem:** Only Target and Degraded modes defined.

**Quick fix:**
Add Floor and Recovery sections:

```markdown
## Mode Matrix

### Target Mode
- **Preserved invariants:** Order, Freshness
- **Evidence:** Closed timestamp (φ), leader lease
- **Operations:** Full read/write
- **Entry:** Lease acquired, quorum reachable
- **Exit:** Lease expires or partition detected

### Degraded Mode
- **Preserved invariants:** Order
- **Relaxed:** Freshness (now bounded-stale)
- **Evidence:** Stale closed timestamp
- **Operations:** Read-only (stale), no writes
- **Entry:** Lease expired but quorum still reachable
- **Exit:** Quorum lost → Floor, or lease renewed → Target

### Floor Mode
- **Preserved invariants:** Safety (never return wrong data)
- **Relaxed:** Availability (may reject requests)
- **Evidence:** None (partition)
- **Operations:** Reject all operations or return cached data with staleness warning
- **Entry:** Quorum lost (network partition)
- **Exit:** Quorum restored → Recovery

### Recovery Mode
- **Goal:** Restore evidence and return to Target
- **Actions:** Re-elect leader, sync replicas, validate timestamps
- **Evidence required:** Quorum certificate, fresh lease
- **Entry:** Partition heals
- **Exit:** Evidence restored → Target, or timeout → Floor
```

---

### 3. Evidence Without Properties (0-4/10)

**Problem:** Evidence mentioned but lifecycle not specified.

**Quick fix:**
```markdown
### Closed Timestamp Evidence

**What it proves:** All writes up to timestamp T have been replicated.

**Evidence properties:**
- **Scope:** Range (all keys in keyspace)
- **Lifetime:** 200ms (until next broadcast)
- **Binding:** Leader replica ID + epoch number
- **Transitivity:** Yes (followers can rely on it for reads)
- **Revocation:** New leader election invalidates all prior closed timestamps

**Lifecycle:**
- **Generation:** Leader tracks in-flight transactions, broadcasts max closed T every 200ms
- **Validation:** Followers check leader lease valid + epoch matches
- **Active use:** Followers serve reads at T_read ≤ T_closed
- **Expiration:** After 200ms or leader lease expires
- **Renewal:** New broadcast from leader
- **Revocation:** Leader election, followers discard old closed timestamps
```

---

### 4. No Sacred Diagrams (0-2/5)

**Problem:** Generic diagrams, not framework-aligned.

**Quick fix:**
Include at least 2 of these:

**Evidence Flow Diagram:**
```markdown
### Evidence Flow

```
Generate → Propagate → Verify → Use → Expire
  ($)         →         ✓       !       ⏰

Leader:  Issue lease (cost: quorum RTT)
Network: Propagate lease to followers
Follower: Verify signature + epoch
Follower: Use for reads (authorization)
Time:    Lease expires (TTL timeout)
```
```

**Mode Compass:**
```markdown
### Mode Transitions

```
        Target
     (fresh reads)
          ↑
   Recovery ← → Degraded
(restoring)    (stale reads)
          ↓
        Floor
    (reject reads)
```
```

---

### 5. Missing Transfer Tests (0-6/10)

**Problem:** No tests or tests all at same difficulty level.

**Quick fix:**

```markdown
## Transfer Tests

### Near Transfer Test: Message Queue Ordering

Apply Lamport clocks to a distributed message queue with 3 brokers.
How would you ensure messages are delivered in causal order?

**Expected insight:** Attach Lamport timestamp to each message. Consumers
increment their clock on receive. If message M2 has timestamp lower than
consumer's current clock, it's a causality violation (deliver out of order).

### Medium Transfer Test: Financial Transaction Ordering

A banking system needs to order transactions across 5 datacenters. Clocks
may be skewed by up to 50ms. Design a time system that guarantees causality.

**Expected insight:** Use HLC (Hybrid Logical Clocks). Physical time provides
human-readable timestamps. Logical counter breaks ties and preserves causality
despite clock skew. If transaction T2 depends on T1 (reads T1's write),
then HLC(T2) > HLC(T1) regardless of clock skew.

### Far Transfer Test: Coordinating Multi-Team Project

A company has 4 teams (Dev, QA, Security, Ops) that must approve a deploy.
Apply consensus thinking: what's the "log" being replicated? Who's the "leader"?
How do you handle a team not responding (Byzantine scenario)?

**Expected insight:** The "log" is the approval history. "Leader" is the
release manager who proposes the deploy. Teams send signed approvals
(evidence). Quorum = 3/4 teams. Byzantine handling: require cryptographic
signatures (Auth(π)) to prevent forgery. Non-responding team triggers timeout
and degraded mode (deploy with 3/4 approval, document the exception).
```

---

### 6. No Composition Operators (0-5/10)

**Problem:** Services composed but algebra not shown.

**Quick fix:**

```markdown
### Composition Example

**API Gateway:**
G_gw = ⟨Global, None, Fractured, EO, None, Auth(JWT)⟩

**Auth Service:**
G_auth = ⟨Object, Lx, SI, Fresh(φ), Idem(K), Auth(π)⟩
Returns user object after JWT validation.

**Database:**
G_db = ⟨Range, Lx, SI, BS(100ms), Idem(K), Auth(session)⟩
Serves data with bounded staleness.

**Sequential composition (GW ▷ Auth ▷ DB):**

Step 1: GW ▷ Auth
meet(G_gw, G_auth) = ⟨Object, None, Fractured, EO, None, Auth(JWT)⟩

Wait—Auth requires Lx order but GW provides None. **Upgrade needed:**
G_gw ↑ ⟨Object, Lx, SI, Fresh, Idem, Auth⟩ via: Auth service provides ordering.

Step 2: Auth ▷ DB
meet(⟨Object, Lx, SI, Fresh, Idem, Auth⟩, G_db)
= ⟨Object, Lx, SI, BS(100ms), Idem, Auth(session)⟩

**Downgrade:** Fresh ⤓ BS(100ms) because DB serves stale reads.

**Final end-to-end guarantee:**
G_end = ⟨Object, Lx, SI, BS(100ms), Idem, Auth(session)⟩

**User-facing translation:**
"Your request is authenticated, reads are linearizable per-object,
transactions see consistent snapshots, data may be up to 100ms stale."
```

---

## Scoring Cheat Sheet

| Check | Weight | What It Measures | Pass Threshold |
|-------|--------|------------------|----------------|
| **G-Vector Syntax** | 10% | Correct guarantee typing | At least 1 valid vector |
| **Mode Matrix** | 10% | All 4 modes defined | 4/4 modes |
| **Evidence Properties** | 10% | Lifecycle completeness | 4/5 properties |
| **Sacred Diagrams** | 5% | Framework visualization | 2+ diagrams |
| **Transfer Tests** | 10% | Knowledge transfer | 3 tests |
| **Context Capsules** | 10% | Boundary tracking | 1+ complete capsule |
| **Composition Operators** | 10% | Explicit composition | 2+ operators |
| **Invariant Mapping** | 15% | Catalog alignment | 1+ catalog invariant |
| **Spiral Narrative** | 10% | 3-pass structure | All 3 passes |
| **Cross-References** | 10% | Chapter continuity | 2 back, 1 forward |

**Total:** 100 points
**Passing:** 70+

---

## Example Validation Output

### Chapter with Good Score (85/100)

```
======================================================================
Validating: site/docs/chapter-03/index.md
======================================================================

✓ G-Vector Syntax............... 10/10
  Found 4 G-vectors, 4 valid

✓ Mode Matrix................... 10/10
  Found 4/4 modes: Floor, Target, Degraded, Recovery

✓ Evidence Properties........... 8/10
  Found 4/5 evidence properties
  → Evidence section at line 450 missing properties: Revocation

✓ Sacred Diagrams............... 4/5
  Found 3/5 sacred diagrams

✓ Transfer Tests................ 10/10
  Found 3/3 transfer tests

✓ Context Capsules.............. 10/10
  Found 2 capsules, 2 complete

✓ Composition Operators......... 7/10
  Found 3 operator types

✓ Invariant Mapping............. 15/15
  Found 3 catalog invariants

✓ Spiral Narrative.............. 10/10
  Found 3/3 spiral passes

✓ Cross-References.............. 10/10
  12 backward, 3 forward

----------------------------------------------------------------------
Total Score: 85/100 (85.0%)
Grade: B
Status: PASS - Minor revisions suggested
----------------------------------------------------------------------

Recommended actions:
- Add revocation semantics to evidence section at line 450
- Add 1-2 more sacred diagrams (consider Mode Compass or Evidence Flow)
```

### Chapter with Failing Score (58/100)

```
======================================================================
Validating: site/docs/chapter-05/index.md
======================================================================

✗ G-Vector Syntax............... 0/10
  No G-vectors found
  → Add at least one G-vector showing guarantee composition

✓ Mode Matrix................... 7/10
  Found 3/4 modes: Floor, Target, Degraded
  → Missing modes: Recovery. Every chapter should define Floor, Target, Degraded, and Recovery modes.

✗ Evidence Properties........... 2/10
  Found 1/5 evidence properties
  → Evidence section at line 320 missing properties: Lifetime, Binding, Transitivity, Revocation

✗ Sacred Diagrams............... 1/5
  Found 1/5 sacred diagrams
  → Only 1 sacred diagrams found. Chapters should include at least 2 of the 5 sacred diagrams.

✗ Transfer Tests................ 3/10
  Found 1/3 transfer tests
  → Missing transfer tests: Medium, Far. Chapters should have 3 tests at increasing distance.

✓ Context Capsules.............. 10/10
  Found 1 capsules, 1 complete

✗ Composition Operators......... 2/10
  Found 1 operator types
  → No explicit downgrades (⤓) found. When guarantees weaken, mark with ⤓.

✓ Invariant Mapping............. 12/15
  Found 2 catalog invariants

✓ Spiral Narrative.............. 10/10
  Found 3/3 spiral passes

✗ Cross-References.............. 3/10
  5 backward, 0 forward
  → Only 5 backward references found. Include at least 2 references to prior chapters to reinforce concepts.
  → No forward references found. Set up at least one future concept to create continuity.

----------------------------------------------------------------------
Total Score: 58/100 (58.0%)
Grade: F
Status: FAIL - Not ready for review
----------------------------------------------------------------------

Critical issues:
1. No G-vectors (0/10) - Add typed guarantee vectors
2. Missing Recovery mode - Add recovery path from Floor/Degraded to Target
3. Evidence incomplete - Specify all 5 properties for each evidence type
4. Need 2 more transfer tests (Medium and Far distance)
5. No forward references - Set up future chapters
```

---

## Advanced Usage

### Batch Validation (All Chapters)

```bash
# Validate all chapters, show summary only
python3 chapter_validator.py site/docs/chapter-*/index.md --summary

# Output:
# ======================================================================
# Summary (12 chapters)
# ======================================================================
# ✓ chapter-01/index.md............................. 92.0% (A)
# ✓ chapter-02/index.md............................. 51.0% (F)
# ✓ chapter-03/index.md............................. 88.0% (B)
# ...
#
# Average Score: 76.3%
```

### CI/CD Integration

```bash
# Generate JSON report for automated systems
python3 chapter_validator.py --format json --output validation.json site/docs/chapter-*/index.md

# Exit code: 0 if all pass (≥70), 1 if any fail
# Use in CI: fail build if score < 70
```

### Custom Configuration

Create `.validation-config.yaml`:

```yaml
strict_mode: true          # Fail on warnings
min_score: 80              # Require 80+ for pass
required_diagrams: 3       # Require 3 sacred diagrams
min_word_count: 2000       # Minimum chapter length
require_production_story: true  # Require at least 1 real incident
```

Run with config:
```bash
python3 chapter_validator.py --config .validation-config.yaml chapter-XX/index.md
```

---

## Troubleshooting

### "No G-vectors found" but I have them

**Possible causes:**
1. Using wrong brackets: `<>` instead of `⟨⟩`
2. Extra whitespace: `G = < Scope, Order >` (no space after <)
3. Missing components: Only 4 components instead of 6

**Fix:** Use exactly this format:
```
G = ⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩
```

### "Mode not detected" but it's there

**Possible causes:**
1. Typo: "Taregt" instead of "Target"
2. Not followed by "Mode": Just "Target:" instead of "Target Mode:"

**Fix:** Use standard headers:
```markdown
### Target Mode
### Floor Mode
### Degraded Mode
### Recovery Mode
```

### "Evidence properties missing" but I listed them

**Possible causes:**
1. Properties not followed by colon: "Scope Range" instead of "Scope: Range"
2. Properties in prose, not structured

**Fix:** Use clear labels:
```markdown
- **Scope:** Range (all keys)
- **Lifetime:** 200ms (until next update)
- **Binding:** Leader replica + epoch
- **Transitivity:** Yes
- **Revocation:** Leader election invalidates
```

---

## Getting Help

- **Documentation:** See `CoherenceValidationChecklist.md` for full details
- **Framework Reference:** `ChapterCraftingGuide.md`
- **Validation Script Source:** `chapter_validator.py`
- **Examples:** `validation-examples/` directory (if available)

---

## Quick Reference: Minimum Requirements

✅ **Must Have (70+ points to pass):**
- [x] 1+ G-vector (10 pts)
- [x] 4/4 modes (10 pts)
- [x] 4/5 evidence properties (8 pts)
- [x] 2+ sacred diagrams (4 pts)
- [x] 3 transfer tests (10 pts)
- [x] 1+ context capsule (10 pts)
- [x] 2+ composition operators (5 pts)
- [x] 1+ catalog invariant (10 pts)
- [x] 3-pass spiral (10 pts)
- [x] 2 back, 1 forward refs (7 pts)

**Total minimum:** 84 pts if all minimums met

✅ **Critical (cannot score 0):**
- Invariant Mapping (must score ≥7)
- Evidence Properties (must score ≥5)
- G-Vector Syntax (must score ≥5)

---

**Pro tip:** Run validation early and often. Don't wait until chapter is "done."
Fix issues incrementally as you write.
