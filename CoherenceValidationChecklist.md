# Coherence Validation Checklist
## Comprehensive Quality Assurance for Framework-Aligned Chapters

This document provides a complete validation system for ensuring chapters meet the Unified Mental Model Authoring Framework 3.0 standards. It includes automated checks, manual review criteria, per-chapter requirements, validation tools, and scoring rubrics.

---

## Table of Contents

1. [Automated Validation Checks](#1-automated-validation-checks)
2. [Manual Review Checklist](#2-manual-review-checklist)
3. [Per-Chapter Requirements](#3-per-chapter-requirements)
4. [Validation Script Usage](#4-validation-script-usage)
5. [Review Rubric](#5-review-rubric)
6. [Common Issues and Fixes](#6-common-issues-and-fixes)
7. [Quality Gates](#7-quality-gates)

---

## 1. Automated Validation Checks

These checks can be performed programmatically using the validation script (see Section 4).

### 1.1 G-Vector Syntax Validation

**What to check:**
- [ ] G-vectors present in guarantee discussions
- [ ] Proper syntax: `G = ⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩`
- [ ] Valid component values:
  - Scope: `{Object, Range, Transaction, Global}`
  - Order: `{None, Causal, Lx, SS}`
  - Visibility: `{Fractured, RA, SI, SER}`
  - Recency: `{EO, BS(δ), Fresh(φ)}`
  - Idempotence: `{None, Idem(K)}`
  - Auth: `{Unauth, Auth(π)}`

**Example valid:**
```
G = ⟨Range, Lx, SI, Fresh(φ), Idem(K), Auth(π)⟩
```

**Example invalid:**
```
G = ⟨Strong, Fast, Good⟩  // Wrong components
```

**Regex pattern:**
```regex
G\s*=\s*⟨[^⟩]+⟩
```

**Common errors:**
- Missing angle brackets (using `<>` instead of `⟨⟩`)
- Undefined component values
- Incomplete vector (missing components)

---

### 1.2 Mode Matrix Completeness

**What to check:**
- [ ] All four modes defined: Floor, Target, Degraded, Recovery
- [ ] Each mode has:
  - [ ] Preserved invariants listed
  - [ ] Required evidence types specified
  - [ ] Allowed operations enumerated
  - [ ] Entry/exit triggers defined
  - [ ] User-visible contract stated

**Search patterns:**
```regex
(Floor|Target|Degraded|Recovery)\s+(Mode|mode)
```

**Minimum requirements per mode:**
- Floor: At least 1 preserved invariant, 1 allowed operation
- Target: At least 2 preserved invariants, full operation set
- Degraded: Explicit statement of relaxed invariants
- Recovery: Clear transition criteria back to Target

**Common errors:**
- Missing Recovery mode (most forgotten)
- Floor mode too permissive (should be minimal)
- No entry/exit triggers specified

---

### 1.3 Evidence Property Presence

**What to check:**
- [ ] Evidence types mentioned have all five core properties:
  1. **Scope**: What it applies to
  2. **Lifetime**: How long it's valid
  3. **Binding**: What entity generated it
  4. **Transitivity**: Can it be forwarded?
  5. **Revocation**: How it's invalidated

**Search patterns:**
```regex
(Scope|Lifetime|Binding|Transitivity|Revocation):\s*
```

**Example complete evidence description:**
```markdown
**Closed Timestamp Evidence**
- Scope: Range (all keys in range)
- Lifetime: 200ms (until next update)
- Binding: Leader replica ID
- Transitivity: Yes (followers can rely on it)
- Revocation: New leader election invalidates
```

**Common errors:**
- Only mentioning "what" evidence is, not its properties
- Missing revocation semantics (critical for safety)
- Unclear lifetime bounds

---

### 1.4 Sacred Diagram Markers

**What to check:**
- [ ] Chapter contains at least 2 of the 5 sacred diagrams:
  1. Invariant Guardian
  2. Evidence Flow
  3. Composition Ladder
  4. Mode Compass
  5. Knowledge vs Data Flow

**Diagram markers to search:**
```regex
(Invariant Guardian|Evidence Flow|Composition Ladder|Mode Compass|Knowledge vs Data)
```

**Visual consistency requirements:**
- [ ] Colors follow framework: Blue (invariants), Green (evidence), Red (threats), Yellow (boundaries)
- [ ] Shapes follow framework: Hexagons (invariants), Rectangles (evidence), Circles (mechanisms)
- [ ] Lines follow framework: Solid (data), Dashed (evidence), Wavy (degradation)

**Common errors:**
- Generic diagrams without framework symbology
- Missing evidence flow visualization
- No mode transitions shown

---

### 1.5 Cross-Reference Validity

**What to check:**
- [ ] References to prior chapters exist and are accurate
- [ ] Forward references (setup for future chapters) are present
- [ ] Invariant catalog references use consistent names
- [ ] Evidence types referenced match evidence calculus

**Cross-reference patterns:**
```regex
(Chapter \d+|Section \d+\.\d+|see Chapter|from Chapter|as we saw in|we'll explore in)
```

**Requirements:**
- [ ] At least 2 backward references (reinforcing prior concepts)
- [ ] At least 1 forward reference (setting up future concepts)
- [ ] Invariant names match catalog (Conservation, Uniqueness, Authenticity, Order, etc.)

**Common errors:**
- Chapter numbers don't exist (off-by-one errors)
- Inconsistent invariant naming ("Ordering" vs "Order")
- Forward references never fulfilled

---

### 1.6 Context Capsule Structure

**What to check:**
- [ ] Capsules present at service/chapter boundaries
- [ ] All five core fields present:
  1. `invariant`: Which property is preserved
  2. `evidence`: Proof(s) validating it
  3. `boundary`: Valid scope/domain
  4. `mode`: Current mode
  5. `fallback`: Authorized downgrade

**Capsule syntax pattern:**
```regex
\{[\s\S]*?invariant:[\s\S]*?evidence:[\s\S]*?boundary:[\s\S]*?mode:[\s\S]*?fallback:[\s\S]*?\}
```

**Example valid capsule:**
```javascript
{
  invariant: Freshness,
  evidence: closed_timestamp(T=110, range=user_data),
  boundary: Replica A, epoch 42,
  mode: Target,
  fallback: BS(200ms) if evidence expires
}
```

**Common errors:**
- Missing fallback field (critical for safety)
- Generic evidence description without parameters
- No epoch/boundary scope specified

---

### 1.7 Composition Operator Usage

**What to check:**
- [ ] Composition operators used correctly:
  - `A ▷ B`: Sequential composition (meet vectors)
  - `A || B`: Parallel composition (merge semantics)
  - `↑`: Upgrade (new evidence introduced)
  - `⤓`: Downgrade (explicit and labeled)

**Operator patterns:**
```regex
(▷|\|\||↑|⤓)
```

**Requirements:**
- [ ] Upgrades show evidence source: `EO ↑ Lx via lease+fence`
- [ ] Downgrades are explicit: `SS ⤓ SI (lost leader lease)`
- [ ] Sequential composition shows meet: `meet(GA, GB)`

**Common errors:**
- Implicit downgrades (no ⤓ symbol, just stating weaker guarantee)
- Upgrades without evidence source
- No composition shown where boundaries exist

---

### 1.8 Transfer Test Presence

**What to check:**
- [ ] Exactly 3 transfer tests (Near, Medium, Far)
- [ ] Each test has:
  - [ ] Problem statement
  - [ ] Application of chapter concepts
  - [ ] Expected solution/insight

**Search patterns:**
```regex
(Transfer Test|Near:|Medium:|Far:)
```

**Distance definitions:**
- **Near**: Same pattern, nearby domain (e.g., applying time ordering to different keyspace)
- **Medium**: Related problem (e.g., applying consensus to resource allocation)
- **Far**: Novel domain (e.g., applying distributed systems concepts to human organizations)

**Common errors:**
- Only 1-2 tests provided
- All tests are "Near" (not increasing distance)
- Tests don't actually apply chapter concepts

---

### 1.9 Invariant Catalog Alignment

**What to check:**
- [ ] Primary invariant mapped to catalog entry
- [ ] Invariant hierarchy respected (Fundamental → Derived → Composite)
- [ ] Threat model specified for invariant
- [ ] Protection boundary identified

**Catalog invariants (from framework):**

**Fundamental:**
- Conservation
- Uniqueness
- Authenticity/Integrity

**Derived:**
- Order
- Exclusivity
- Monotonicity

**Composite:**
- Freshness
- Visibility/Coherent cut
- Convergence
- Idempotence
- Bounded staleness
- Availability promise

**Requirements:**
- [ ] Chapter maps to exactly ONE primary invariant
- [ ] Supporting invariants (0-2) from catalog
- [ ] Custom invariants justified as compositions

**Common errors:**
- Inventing new fundamental invariants (should compose existing)
- Not stating which catalog entry is primary
- Mixing threat models across invariants

---

### 1.10 Spiral Narrative Structure

**What to check:**
- [ ] Three-pass structure evident:
  - **Pass 1 (Intuition)**: Story, failure, felt need
  - **Pass 2 (Understanding)**: Mechanism, limits, trade-offs
  - **Pass 3 (Mastery)**: Composition, modes, operation

**Section header patterns:**
```regex
(Part 1:|Pass 1:|Intuition|INTUITION)
(Part 2:|Pass 2:|Understanding|UNDERSTANDING)
(Part 3:|Pass 3:|Mastery|MASTERY)
```

**Requirements per pass:**
- **Pass 1**: At least 1 production story, concrete example
- **Pass 2**: Mechanism explanation, evidence identification
- **Pass 3**: Mode matrix, composition examples, operator guidance

**Common errors:**
- Missing Pass 1 (diving straight into mechanism)
- Pass 3 too short (no operational guidance)
- Passes not clearly delineated

---

## 2. Manual Review Checklist

These require human judgment and cannot be fully automated.

### 2.1 Invariant Mapping Correctness

**Questions to ask:**

1. **Is the invariant truly fundamental to the chapter?**
   - Does the entire chapter revolve around protecting this invariant?
   - If removed, would the chapter lose coherence?

2. **Is the invariant correctly categorized?**
   - Fundamental invariants should be irreducible (Conservation, Uniqueness, Authenticity)
   - Derived invariants should be buildable from fundamentals
   - Composite invariants should be named combinations

3. **Is the threat model complete?**
   - Are all realistic attack vectors listed? (delay, skew, replay, partition, Byzantine)
   - Are edge cases covered? (clock skew, message reordering, partial failures)

4. **Is the protection boundary appropriate?**
   - Service level? Shard level? Region level?
   - Is the boundary enforced consistently throughout the chapter?

**Red flags:**
- Invariant changes halfway through chapter
- Multiple primary invariants (indicates lack of focus)
- Invariant is actually a mechanism (e.g., "Paxos" instead of "Agreement")

**Scoring:**
- 10/10: Single, clear primary invariant; complete threat model; consistent boundary
- 7/10: Invariant clear but threat model incomplete
- 4/10: Multiple invariants competing for primary; unclear boundary
- 0/10: No invariant identified or wrong categorization

---

### 2.2 Evidence Lifecycle Completeness

**Questions to ask:**

1. **Are all lifecycle stages addressed?**
   - Generation: How evidence is created
   - Validation: How it's checked at boundaries
   - Active use: How decisions rely on it
   - Expiration: When it becomes invalid
   - Renewal: How it's refreshed
   - Revocation: How it's invalidated early

2. **Is the evidence lifecycle realistic?**
   - Generation cost: CPU, network, coordination?
   - Validation cost: Can it be verified efficiently?
   - Expiration: Is the lifetime bound appropriate for use case?

3. **Are edge cases handled?**
   - What if evidence expires mid-operation?
   - What if evidence cannot be renewed (network partition)?
   - What if revocation signal is lost?

**Red flags:**
- Evidence described but lifecycle not specified
- No expiration semantics (infinite validity assumed)
- Revocation missing (can't invalidate compromised evidence)

**Scoring:**
- 10/10: Complete lifecycle; costs stated; edge cases handled
- 7/10: Lifecycle present but costs not quantified
- 4/10: Only generation and use covered; no expiration
- 0/10: Evidence mentioned but no lifecycle

---

### 2.3 Composition Soundness

**Questions to ask:**

1. **Are composition boundaries explicit?**
   - Where do services compose? (Service mesh, API gateway, database client)
   - Are boundaries marked in diagrams?

2. **Are guarantee vectors composed correctly?**
   - Sequential: meet(GA, GB) computed correctly?
   - Parallel: Merge semantics appropriate?
   - Upgrades: Evidence source identified?
   - Downgrades: Explicit and justified?

3. **Do capsules flow across boundaries?**
   - Are capsules shown transferring between components?
   - Are fields rebind/restrict/extend-ed correctly?

4. **Is the final end-to-end guarantee correct?**
   - Does it match the weakest component?
   - Is it translated to user-facing language?

**Red flags:**
- Composition mentioned but not shown
- Stronger end-to-end guarantee than components allow
- Capsules disappear at boundaries (implicit downgrade)

**Scoring:**
- 10/10: Explicit boundaries; vectors composed; capsules tracked; correct end-to-end
- 7/10: Composition shown but vectors not computed
- 4/10: Boundaries mentioned but no composition algebra
- 0/10: No composition discussion

---

### 2.4 Transfer Test Quality

**Questions to ask:**

1. **Do tests actually test transfer?**
   - Can concepts be applied without reading the chapter again?
   - Do tests require understanding, not memorization?

2. **Is distance appropriate?**
   - Near: Adjacent domain (easy)
   - Medium: Related field (moderate)
   - Far: Completely different domain (hard)

3. **Are solutions non-trivial?**
   - Tests shouldn't be pattern-matching exercises
   - Should require insight, not just template substitution

**Example good Far test:**
```markdown
**Far Transfer Test**: Applying Consensus to Family Decision-Making

A family of 5 needs to decide where to go for vacation.
Apply the Raft consensus protocol:
- Who is the leader? How is leadership established?
- What is the "log" being replicated?
- How do you handle network partitions (family members not responding)?
- What is the "committed" state?

Expected insight: Consensus is about **agreement despite uncertainty**,
not about "voting." Leader proposes, majority confirms, decision becomes
final only when committed. Lost messages (silent family members) require
timeouts and re-proposals.
```

**Red flags:**
- All tests are trivial pattern-matching
- Tests don't increase in difficulty
- No expected insights provided

**Scoring:**
- 10/10: 3 tests; increasing distance; non-trivial; insights clear
- 7/10: 3 tests but similar difficulty
- 4/10: Only 1-2 tests or too easy
- 0/10: No tests or tests unrelated to chapter

---

### 2.5 Pedagogical Flow

**Questions to ask:**

1. **Does the chapter build progressively?**
   - Start with felt need (story, failure)?
   - Progress to mechanism?
   - End with operation and composition?

2. **Is cognitive load managed?**
   - Maximum 3 new concepts per chapter?
   - Each concept builds on prior?
   - Sufficient examples and diagrams?

3. **Are transitions smooth?**
   - Sections connect logically?
   - Recap prior concepts before building on them?
   - Forward references prepare for next sections?

4. **Is the irreducible sentence powerful?**
   - Does it capture the essence?
   - Is it memorable?
   - Does it tie invariant + evidence + uncertainty?

**Example great irreducible sentence:**
> "In distributed systems, time is not a single truth—it is evidence of
> ordering, with bounded uncertainty. Causality is the fundamental invariant;
> timestamps are the means to preserve it."

**Red flags:**
- Too many concepts introduced simultaneously
- Sections feel disconnected
- Irreducible sentence is generic ("Distributed systems are hard")

**Scoring:**
- 10/10: Clear progression; managed load; smooth transitions; powerful sentence
- 7/10: Good flow but occasional jumps
- 4/10: Concepts introduced too quickly; rough transitions
- 0/10: Disjointed; overwhelming; weak conclusion

---

## 3. Per-Chapter Requirements

### 3.1 Minimum Requirements (MUST HAVE)

Every chapter must have:

- [ ] **Primary invariant** from catalog (exactly 1)
- [ ] **Evidence type** with full lifecycle (at least 1)
- [ ] **Mode matrix** with all 4 modes (Floor, Target, Degraded, Recovery)
- [ ] **3 transfer tests** (Near, Medium, Far)
- [ ] **2 backward references** (reinforcing prior chapters)
- [ ] **1 forward reference** (setting up future chapter)
- [ ] **Spiral narrative** (3-pass structure)
- [ ] **Irreducible sentence** (memorable essence)
- [ ] **At least 2 sacred diagrams**
- [ ] **Context capsule** (at chapter boundaries)

**Failure threshold:** Missing any 3+ items = Chapter not ready for review

---

### 3.2 Nice-to-Have Elements (SHOULD HAVE)

Chapters should include:

- [ ] **Production story** (real-world incident)
- [ ] **Metrics to track** (operational guidance)
- [ ] **Failure mode catalog** (what can go wrong)
- [ ] **Composition examples** (cross-service scenarios)
- [ ] **Code snippets** (if applicable)
- [ ] **Socratic prompts** (margin questions)
- [ ] **Metaphor** from lexicon (Passport, Budget, Immune System, Geology, Market)
- [ ] **Cross-chapter resonance** (recurring thread marked)

**Quality threshold:** 6+ items = Excellent chapter; 3-5 = Good; 0-2 = Needs enhancement

---

### 3.3 Cross-Chapter Dependencies

**Early chapters (1-5) must establish:**
- Invariant catalog with examples
- Evidence calculus with lifecycle
- G-vector component definitions
- Mode matrix template
- STA and DCEH lenses

**Middle chapters (6-11) must:**
- Reference invariants established in Ch 1-5
- Show composition across boundaries (from Ch 1)
- Apply mode matrix consistently (from Ch 1)
- Build on time concepts (from Ch 2) if applicable
- Reference consensus evidence (from Ch 3) if applicable

**Late chapters (12-16) must:**
- Synthesize multiple invariants
- Show complex composition (3+ service boundaries)
- Reference production incidents from earlier chapters
- Demonstrate full evidence lifecycle across system

**Dependency validation:**
- [ ] Forward references in earlier chapters fulfilled
- [ ] Concepts used before defined are flagged
- [ ] Invariant names consistent across chapters

---

## 4. Validation Script Usage

See `chapter_validator.py` for the automated validation tool.

### 4.1 Basic Usage

```bash
# Validate a single chapter
python chapter_validator.py site/docs/chapter-02/index.md

# Validate all chapters
python chapter_validator.py site/docs/chapter-*/index.md

# Generate detailed report
python chapter_validator.py --verbose --output=report.html site/docs/chapter-02/index.md
```

### 4.2 Output Format

The script generates:

1. **Console output**: Quick pass/fail per check
2. **JSON report**: Machine-readable results
3. **HTML report**: Human-readable with highlights and suggestions

Example output:
```
Validating: chapter-02/index.md
✓ G-vector syntax (2 found)
✓ Mode matrix (4/4 modes)
✗ Evidence properties (2/5 missing: Transitivity, Revocation)
✓ Sacred diagrams (3/5 found)
✓ Transfer tests (3/3 found)
⚠ Spiral narrative (Pass 3 too short: <500 words)

Score: 78/100 (GOOD)
Recommended actions: Add missing evidence properties, expand Pass 3
```

### 4.3 Configuration

Create `.validation-config.yaml` to customize:

```yaml
strict_mode: false  # Fail on warnings
min_score: 70       # Minimum passing score
required_diagrams: 2  # Minimum sacred diagrams
evidence_properties: [Scope, Lifetime, Binding, Transitivity, Revocation]
```

---

## 5. Review Rubric

### 5.1 Scoring Dimensions (0-10 each)

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Invariant Clarity** | 15% | Primary invariant identified, cataloged, threat model complete |
| **Evidence Lifecycle** | 15% | Full lifecycle (gen/val/use/expire/renew/revoke) with costs |
| **Mode Matrix** | 10% | All 4 modes defined with triggers and guarantees |
| **Composition** | 15% | Boundaries explicit, vectors composed, capsules tracked |
| **Pedagogy** | 15% | Spiral narrative, managed cognitive load, smooth flow |
| **Transfer Tests** | 10% | 3 tests at increasing distance, non-trivial, insightful |
| **Cross-References** | 5% | Backward (2+) and forward (1+) references accurate |
| **Diagrams** | 5% | Sacred diagrams (2+) with framework symbology |
| **Operational Guidance** | 5% | Metrics, failure modes, debugging tips |
| **Synthesis** | 5% | Irreducible sentence, connections to framework |

**Total: 100 points**

---

### 5.2 Scoring Rubric Per Dimension

#### Invariant Clarity (15 points)

| Score | Criteria |
|-------|----------|
| 13-15 | Single primary invariant; cataloged; complete threat model; clear boundary; no confusion |
| 10-12 | Invariant clear; mostly cataloged; threat model present but incomplete |
| 7-9   | Invariant identified but competing with others; boundary unclear |
| 4-6   | Multiple invariants; uncataloged; minimal threat model |
| 0-3   | No clear invariant or fundamentally wrong categorization |

#### Evidence Lifecycle (15 points)

| Score | Criteria |
|-------|----------|
| 13-15 | All 6 stages; costs quantified; edge cases handled; revocation clear |
| 10-12 | All stages present; costs mentioned; basic edge cases |
| 7-9   | 4-5 stages; costs not quantified; no edge cases |
| 4-6   | 2-3 stages; lifecycle incomplete |
| 0-3   | Evidence mentioned but no lifecycle |

#### Mode Matrix (10 points)

| Score | Criteria |
|-------|----------|
| 9-10  | All 4 modes; triggers clear; guarantees explicit; cross-service compatibility |
| 7-8   | All 4 modes; basic triggers; guarantees stated |
| 5-6   | 3 modes (often missing Recovery); triggers vague |
| 3-4   | 2 modes only; no triggers |
| 0-2   | No mode matrix or only Target mode |

#### Composition (15 points)

| Score | Criteria |
|-------|----------|
| 13-15 | Boundaries explicit; vectors composed; meet/upgrade/downgrade shown; capsules tracked; end-to-end correct |
| 10-12 | Boundaries shown; vectors mentioned; basic composition |
| 7-9   | Boundaries identified but composition not computed |
| 4-6   | Composition mentioned but not demonstrated |
| 0-3   | No composition discussion |

#### Pedagogy (15 points)

| Score | Criteria |
|-------|----------|
| 13-15 | Clear 3-pass spiral; cognitive load managed (≤3 concepts); smooth transitions; engaging |
| 10-12 | 3 passes evident; load managed; mostly smooth |
| 7-9   | Progression present but uneven; occasional overload |
| 4-6   | Structure weak; too many concepts; rough transitions |
| 0-3   | No structure; overwhelming; disconnected |

#### Transfer Tests (10 points)

| Score | Criteria |
|-------|----------|
| 9-10  | 3 tests; increasing distance (near/med/far); non-trivial; insights provided |
| 7-8   | 3 tests; some distance variation; basic insights |
| 5-6   | 2-3 tests; similar difficulty; minimal insights |
| 3-4   | 1-2 tests; trivial |
| 0-2   | No tests or completely unrelated |

#### Cross-References (5 points)

| Score | Criteria |
|-------|----------|
| 5     | 2+ backward, 1+ forward; all accurate; invariants match catalog |
| 4     | 2+ backward or 1+ forward; mostly accurate |
| 3     | 1 backward, 1 forward; some inaccuracies |
| 2     | Minimal references; several errors |
| 0-1   | No references or mostly wrong |

#### Diagrams (5 points)

| Score | Criteria |
|-------|----------|
| 5     | 3+ sacred diagrams; framework symbology; colors/shapes correct |
| 4     | 2 sacred diagrams; mostly correct symbology |
| 3     | 1-2 diagrams; generic (not sacred) |
| 2     | Diagrams present but wrong symbology |
| 0-1   | No diagrams or completely off-framework |

#### Operational Guidance (5 points)

| Score | Criteria |
|-------|----------|
| 5     | Metrics, failure modes, debugging tips, runbooks |
| 4     | Metrics and failure modes |
| 3     | Metrics or failure modes |
| 2     | Minimal operational content |
| 0-1   | No operational guidance |

#### Synthesis (5 points)

| Score | Criteria |
|-------|----------|
| 5     | Powerful irreducible sentence; clear connections; memorable |
| 4     | Good sentence; connections present |
| 3     | Adequate sentence; some connections |
| 2     | Weak sentence; minimal connections |
| 0-1   | Generic or no irreducible sentence |

---

### 5.3 Pass/Fail Criteria

| Total Score | Grade | Status |
|-------------|-------|--------|
| 90-100 | A (Excellent) | **PASS** - Ready for publication |
| 80-89  | B (Good) | **PASS** - Minor revisions suggested |
| 70-79  | C (Acceptable) | **CONDITIONAL** - Address major items before publish |
| 60-69  | D (Needs Work) | **FAIL** - Significant revision required |
| 0-59   | F (Incomplete) | **FAIL** - Not ready for review |

**Quality gates:**
- No dimension can score 0 (missing entirely)
- Invariant Clarity, Evidence Lifecycle, Composition must each score ≥7 (these are core)
- At least 80% of automated checks must pass

---

## 6. Common Issues and Fixes

### 6.1 Issue: Implicit Downgrades

**Problem:** Weaker guarantees stated without explicit downgrade notation.

**Example (wrong):**
```markdown
The leader provides linearizable reads. Followers provide eventual consistency.
```

**Why wrong:** No explicit transition, no fallback stated, no evidence expiration shown.

**Fix:**
```markdown
The leader provides linearizable reads: G = ⟨Range, Lx, SI, Fresh(φ), Idem, Auth⟩

Followers, lacking leader lease evidence, explicitly downgrade:
G ⤓ ⟨Range, Causal, SI, BS(200ms), Idem, Auth⟩ (stale by closed timestamp lag)
```

---

### 6.2 Issue: Evidence Without Lifecycle

**Problem:** Evidence mentioned but lifecycle not specified.

**Example (wrong):**
```markdown
Paxos uses quorum certificates to ensure agreement.
```

**Why wrong:** No mention of how generated, validated, when expires, how revoked.

**Fix:**
```markdown
**Quorum Certificate Evidence**

- **Generation**: Proposer collects ⌈n/2⌉+1 acceptor promises
- **Validation**: Acceptors check ballot number > previous promises
- **Active use**: Certificate authorizes value commit
- **Expiration**: New leader election (higher ballot) invalidates
- **Renewal**: N/A (single-use, not renewable)
- **Revocation**: Higher ballot explicitly supersedes
- **Cost**: 1 RTT (parallel acceptor requests), O(n) messages
```

---

### 6.3 Issue: Missing Recovery Mode

**Problem:** Only Floor, Target, Degraded defined; Recovery omitted.

**Why wrong:** No path back to normal operation specified.

**Fix:**
```markdown
**Recovery Mode**

**Goal**: Restore full evidence after partition heals

**Actions**:
- Re-establish quorum (leader election)
- Repair replicas (sync missing log entries)
- Re-validate evidence (check lease validity)

**Entry condition**: Network partition heals, nodes reachable

**Exit condition**:
- Quorum established → Target mode
- Repair fails → Degraded mode (if minority)
- Cannot establish quorum → Floor mode

**Allowed operations**: Limited writes (appending to log), no reads
```

---

### 6.4 Issue: Transfer Tests Too Easy

**Problem:** Tests are pattern-matching, not transfer.

**Example (wrong):**
```markdown
**Near Test**: Apply Lamport clocks to message ordering.
(This is just the chapter example rephrased.)
```

**Fix:**
```markdown
**Near Test**: Apply Lamport clocks to database transaction ordering.

You have a distributed database with concurrent transactions T1, T2, T3
across 3 nodes. Design a Lamport clock-based system to order commits.

Questions:
- What events increment the clock? (txn start, read, write, commit)
- How do clocks merge when transactions span nodes?
- Can you detect concurrent transactions with Lamport clocks alone? (No—need vector clocks)

Expected insight: Lamport clocks order events but cannot detect concurrency.
If T1 and T2 access different keys, their commits might have comparable
Lamport timestamps but still be concurrent (no causal dependency).
```

---

### 6.5 Issue: G-Vectors Not Composed

**Problem:** Multiple services described but no composition shown.

**Example (wrong):**
```markdown
Service A provides strong consistency. Service B provides eventual consistency.
The system as a whole provides...?
```

**Fix:**
```markdown
**Service A**: GA = ⟨Range, Lx, SI, Fresh(φ), Idem, Auth⟩
**Service B**: GB = ⟨Global, Causal, RA, EO, None, Unauth⟩

**Composition** (A ▷ B, sequential):
Gend = meet(GA, GB) = ⟨Range, Causal, RA, EO, None, Unauth⟩

Weakest components dominate:
- Scope: Range (A's scope, narrower than B's Global)
- Order: Causal (weaker than Lx)
- Visibility: RA (weaker than SI)
- Recency: EO (weakest)
- Idempotence: None (B provides none)
- Auth: Unauth (B is unauthenticated)

**End-to-end guarantee**: Causal order, read-atomic, eventually consistent,
within range scope, unauthenticated.

**User-facing**: "Reads reflect writes in causal order but may be stale;
no authentication required."
```

---

### 6.6 Issue: Weak Irreducible Sentence

**Problem:** Generic, forgettable, doesn't tie together concepts.

**Example (wrong):**
```markdown
"Consensus is important in distributed systems."
```

**Fix:**
```markdown
"Consensus converts uncertain proposals into certain decisions by
manufacturing quorum evidence—proof that a majority agreed, which
survives minority failures and enables deterministic progress."
```

**Why better:** Ties invariant (agreement), evidence (quorum certificates),
uncertainty (minority failures), and mechanism (majority voting).

---

## 7. Quality Gates

### 7.1 Pre-Review Gate (Automated)

**Before human review, chapter must pass:**

- [ ] 80%+ automated checks pass
- [ ] All 10 minimum requirements present
- [ ] Mode matrix complete (4/4 modes)
- [ ] Transfer tests present (3/3)
- [ ] No broken cross-references

**Auto-reject if:**
- Score < 50 on automated checks
- Missing 3+ minimum requirements
- No mode matrix

---

### 7.2 Review Gate (Human + Automated)

**For publication, chapter must:**

- [ ] Total score ≥ 70/100
- [ ] Invariant Clarity ≥ 7/15
- [ ] Evidence Lifecycle ≥ 7/15
- [ ] Composition ≥ 7/15
- [ ] Pedagogy ≥ 7/15
- [ ] No dimension scores 0

**Conditional pass (70-79):**
- List specific improvements needed
- Re-review after revisions

---

### 7.3 Publication Gate

**Final checks before publish:**

- [ ] All cross-references verified (chapters exist, sections exist)
- [ ] Diagrams rendered correctly (Mermaid/SVG)
- [ ] Code snippets execute (if applicable)
- [ ] Transfer test solutions provided (in appendix or solutions doc)
- [ ] Irreducible sentence added to index/summary

---

## Appendix A: Validation Script Quick Reference

```bash
# Quick validation
./validate.sh chapter-02

# Detailed report
python chapter_validator.py --verbose --html site/docs/chapter-02/index.md

# Batch validation
python chapter_validator.py site/docs/chapter-*/index.md --summary

# Config override
python chapter_validator.py --config strict.yaml chapter-02/index.md

# JSON output for CI/CD
python chapter_validator.py --format json chapter-02/index.md > result.json
```

---

## Appendix B: Reviewer Checklist (One-Page)

**Chapter:** ________________  **Reviewer:** ________________  **Date:** ________

### Automated (from script)
- [ ] G-vectors: ___/___
- [ ] Modes: ___/4
- [ ] Evidence: ___/5 properties
- [ ] Diagrams: ___/5
- [ ] Tests: ___/3

### Manual
- [ ] Invariant clear and cataloged (score: ___/15)
- [ ] Evidence lifecycle complete (score: ___/15)
- [ ] Composition sound (score: ___/15)
- [ ] Pedagogy strong (score: ___/15)
- [ ] Transfer tests quality (score: ___/10)

### Total Score: ___/100

**Decision:**
- [ ] PASS (Ready)
- [ ] CONDITIONAL (List fixes): ___________________________
- [ ] FAIL (Major revision)

**Signature:** ________________

---

**End of Coherence Validation Checklist**

For questions or improvements to this checklist, see:
- ChapterCraftingGuide.md (framework reference)
- chapter_validator.py (automation tool)
- validation-examples/ (sample validated chapters)
