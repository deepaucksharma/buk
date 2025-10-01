# Validation Workflow Guide
## From Draft to Publication-Ready Chapter

This guide provides a systematic workflow for authors to validate their chapters throughout the writing process, not just at the end.

---

## Workflow Overview

```
Draft → Self-Validate → Fix → Peer Review → Final Validation → Publish
  ↑                                                              |
  └──────────────── Iterate until score ≥ 70 ──────────────────┘
```

---

## Phase 1: Outline Validation (Pre-Writing)

**Before writing prose, validate your outline.**

### Outline Template

Create `chapter-XX-outline.md`:

```markdown
# Chapter XX: [Title]

## Primary Invariant
- Name: [From catalog]
- Category: Fundamental / Derived / Composite
- Threat model: [How it's attacked]

## Evidence Type
- Name: [e.g., Quorum Certificate, Closed Timestamp]
- Scope: [Object/Range/Transaction/Global]
- Lifetime: [Duration]
- Binding: [Entity]
- Transitivity: [Yes/No]
- Revocation: [How invalidated]

## Mode Matrix (sketch)
- Floor: [Minimum guarantees]
- Target: [Normal operation]
- Degraded: [Reduced guarantees]
- Recovery: [Path back to Target]

## 3-Pass Structure
### Pass 1 (Intuition)
- Story: [Production incident or concrete example]
- Invariant at risk: [What breaks]

### Pass 2 (Understanding)
- Mechanism: [How to protect invariant]
- Evidence generated: [What proves it works]
- Trade-offs: [PACELC, dualities]

### Pass 3 (Mastery)
- Composition: [Cross-service scenarios]
- Operational modes: [Full mode matrix]
- Metrics and failure handling

## Transfer Tests (planned)
- Near: [Same domain]
- Medium: [Related domain]
- Far: [Different domain]

## Cross-References
- Backward (from prior chapters): [Ch X: concept, Ch Y: concept]
- Forward (to future chapters): [Ch Z: concept]

## Sacred Diagrams (planned)
- [Diagram 1]: Invariant Guardian / Evidence Flow / etc.
- [Diagram 2]: Mode Compass / Composition Ladder / etc.
```

### Validate Outline

```bash
# This won't pass validation (it's just an outline), but it shows what's missing
python3 chapter_validator.py chapter-XX-outline.md
```

**Expected result:** Low score, but you'll see which sections need content.

**Action:** Use the suggestions to guide your writing.

---

## Phase 2: Incremental Writing with Continuous Validation

**Validate after each major section is written.**

### After Writing Pass 1 (Intuition)

**Expected score at this stage: 20-30/100**

Run validation:
```bash
python3 chapter_validator.py --verbose site/docs/chapter-XX/index.md
```

**What should pass:**
- [x] Spiral narrative (partial: Pass 1 detected)
- [x] Invariant mapping (if you've named the invariant)
- [x] 1-2 backward cross-references (referencing prior chapters in the story)

**What will fail (expected):**
- [ ] G-vectors (not introduced yet in Pass 1)
- [ ] Mode matrix (comes in Pass 3)
- [ ] Evidence properties (detailed in Pass 2)
- [ ] Transfer tests (usually at the end)

**Action:** Continue to Pass 2. Don't worry about the low score yet.

---

### After Writing Pass 2 (Understanding)

**Expected score at this stage: 50-60/100**

Run validation:
```bash
python3 chapter_validator.py --verbose site/docs/chapter-XX/index.md
```

**What should now pass:**
- [x] Spiral narrative (Pass 1 + Pass 2 detected)
- [x] Invariant mapping (catalog reference should be explicit)
- [x] Evidence properties (detailed explanation)
- [x] G-vectors (introduced when explaining guarantees)
- [x] Composition operators (when showing boundaries)

**What will still fail:**
- [ ] Mode matrix (Pass 3 content)
- [ ] Transfer tests (usually after all passes)
- [ ] Sacred diagrams (may still be incomplete)

**Action:** If score < 50, review Pass 2. Add missing G-vectors and evidence properties before proceeding.

---

### After Writing Pass 3 (Mastery)

**Expected score at this stage: 70-80/100**

Run validation:
```bash
python3 chapter_validator.py --verbose site/docs/chapter-XX/index.md
```

**What should now pass:**
- [x] All spiral passes (1, 2, 3)
- [x] Mode matrix (all 4 modes in Pass 3)
- [x] Context capsules (boundary examples)
- [x] Sacred diagrams (at least 2)

**What might still fail:**
- [ ] Transfer tests (if not written yet)
- [ ] Forward cross-references (if not seeded)
- [ ] Some composition operators (if boundaries not fully shown)

**Action:** Add transfer tests and forward references. Score should reach 70-80.

---

### Adding Transfer Tests and Polish

**Target score: 80-90/100**

**Add transfer tests:**

1. **Near test:** Apply the chapter's main concept to a slightly different scenario
   - Example: If chapter is about Lamport clocks, apply to a different messaging system

2. **Medium test:** Apply to a related but distinct problem
   - Example: Apply time ordering concepts to financial transactions

3. **Far test:** Apply to a completely different domain
   - Example: Apply distributed systems concepts to human organizations

**Add forward references:**
- "In Chapter X, we'll explore how this composes with..."
- "This pattern recurs when we discuss... in Chapter Y"

**Add missing diagrams:**
- Use the 5 sacred diagrams as templates
- Ensure at least 2 are present

**Polish:**
- Add irreducible sentence at the end
- Ensure context capsule at chapter boundary
- Check for implicit downgrades (add ⤓ symbols)

Run final validation:
```bash
python3 chapter_validator.py --verbose --html --output chapter-XX-report.html site/docs/chapter-XX/index.md
```

**If score ≥ 70:** Ready for peer review
**If score < 70:** Address critical failures first

---

## Phase 3: Self-Review Checklist

Before submitting for peer review, manually check these items:

### Content Completeness

- [ ] **Primary invariant** is clear and from catalog
- [ ] **Threat model** covers realistic attacks (delay, skew, partition, Byzantine)
- [ ] **Evidence lifecycle** is complete (all 6 stages)
- [ ] **Mode matrix** covers all transitions (not just states)
- [ ] **G-vectors** are composed correctly (meet/upgrade/downgrade shown)
- [ ] **Transfer tests** increase in difficulty (Near < Medium < Far)
- [ ] **Cross-references** are accurate (chapters and sections exist)
- [ ] **Irreducible sentence** captures essence

### Pedagogical Flow

- [ ] **Pass 1** has a compelling story (production incident or concrete example)
- [ ] **Pass 2** explains the mechanism clearly (how, not just what)
- [ ] **Pass 3** provides operational guidance (metrics, failure modes)
- [ ] **Transitions** between sections are smooth (no jarring jumps)
- [ ] **Cognitive load** is managed (max 3 new concepts)
- [ ] **Examples** are concrete (not abstract hand-waving)

### Framework Alignment

- [ ] **Invariant** matches catalog (or justified as new composite)
- [ ] **Evidence** follows lifecycle pattern (Generation → ... → Revocation)
- [ ] **Modes** use standard names (Floor, Target, Degraded, Recovery)
- [ ] **G-vectors** use standard components (Scope, Order, Visibility, Recency, Idempotence, Auth)
- [ ] **Diagrams** use framework symbology (colors, shapes, lines)
- [ ] **Composition** uses standard operators (▷, ||, ↑, ⤓)

### Operational Practicality

- [ ] **Metrics** are specified (what to measure)
- [ ] **Thresholds** are provided (when to alert)
- [ ] **Failure modes** are cataloged (what can go wrong)
- [ ] **Debugging tips** are included (how to diagnose)
- [ ] **Code snippets** are realistic (not pseudocode if claiming production use)

---

## Phase 4: Peer Review

### For Authors: Submitting for Review

1. **Run final validation:**
   ```bash
   python3 chapter_validator.py --format html --output review-report.html site/docs/chapter-XX/index.md
   ```

2. **Include validation report in review request:**
   - Attach `review-report.html`
   - Highlight any known issues and planned fixes
   - Note score and status

3. **Provide context:**
   - What's the chapter's main contribution?
   - Which prior chapters does it build on?
   - Which future chapters does it set up?

4. **Ask specific questions:**
   - "Is the invariant mapping correct?"
   - "Are the transfer tests too easy/hard?"
   - "Does the pedagogical flow work?"

### For Reviewers: Conducting Review

1. **Review the validation report first:**
   - Check automated score
   - Note any critical failures
   - Identify obvious issues

2. **Read the chapter:**
   - Focus on manual review dimensions (Section 2 of CoherenceValidationChecklist.md)
   - Use the reviewer checklist (Appendix B)

3. **Score manually:**
   - Use the rubric (Section 5 of CoherenceValidationChecklist.md)
   - Provide specific line numbers for issues
   - Suggest concrete fixes (not just "improve this")

4. **Provide decision:**
   - **PASS:** Ready for publication (score ≥ 80) or minor revisions (score 70-79)
   - **CONDITIONAL:** Major items needed (score 70-79 with critical issues)
   - **FAIL:** Significant work required (score < 70)

5. **Return feedback:**
   - Complete reviewer checklist
   - Annotated chapter (line-specific comments)
   - Validation report with manual scores

---

## Phase 5: Revision and Re-Validation

### Addressing Feedback

**Systematic approach:**

1. **Group issues by type:**
   - Critical (prevent publication): Invariant unclear, evidence incomplete, composition wrong
   - Major (reduce quality): Missing modes, weak transfer tests, poor flow
   - Minor (polish): Typos, formatting, small clarifications

2. **Fix critical issues first:**
   - Re-run validation after each fix
   - Ensure score doesn't regress

3. **Address major issues:**
   - May require restructuring sections
   - Re-validate entire chapter after major changes

4. **Polish:**
   - Fix minor issues
   - Final validation run

### Re-Validation Protocol

After revisions:

```bash
# Full validation
python3 chapter_validator.py --verbose site/docs/chapter-XX/index.md

# Compare to previous score (if you saved the old report)
diff old-report.txt new-report.txt
```

**Improvement targets:**
- Critical issues: Must reach 0
- Major issues: Should be < 3
- Score: Should improve by at least 10 points per iteration

**If score improved but still < 70:**
- Review feedback again
- Focus on highest-weight dimensions (Invariant Clarity, Evidence Lifecycle, Composition)

**If score ≥ 70:**
- Request re-review or proceed to final validation

---

## Phase 6: Final Validation (Pre-Publication)

### Final Checks

Before publishing, verify:

1. **All cross-references are valid:**
   ```bash
   # Check for broken links
   grep -r "Chapter [0-9]" site/docs/chapter-XX/index.md | grep -o "Chapter [0-9][0-9]*" | sort -u
   # Manually verify each chapter exists
   ```

2. **All diagrams render:**
   - Build the site locally: `mkdocs serve`
   - View chapter in browser
   - Check all diagrams display correctly

3. **All code snippets work (if any):**
   - Extract code snippets
   - Run them to verify syntax/output

4. **Validation score is stable:**
   ```bash
   # Run validation 3 times (should be identical)
   python3 chapter_validator.py site/docs/chapter-XX/index.md
   ```

5. **Manual review rubric is complete:**
   - All 10 dimensions scored
   - Total score ≥ 70
   - No dimension scores 0

### Publication Criteria

**Must have:**
- [x] Automated validation score ≥ 70
- [x] Manual review score ≥ 70
- [x] No critical issues (invariant/evidence/composition failures)
- [x] All cross-references valid
- [x] All diagrams render
- [x] Peer review approved

**Should have (for high quality):**
- [ ] Automated validation score ≥ 80
- [ ] Manual review score ≥ 80
- [ ] 2+ reviewers approved
- [ ] Production story included
- [ ] Transfer tests non-trivial

**Nice to have:**
- [ ] Automated validation score ≥ 90
- [ ] 3+ sacred diagrams
- [ ] Code examples tested
- [ ] Metrics dashboard template provided

---

## Phase 7: Post-Publication Maintenance

### Continuous Validation

**When to re-validate:**
- Framework updates (changes to catalog, G-vector components, etc.)
- Cross-references break (dependent chapters change)
- Reader feedback suggests issues

**Maintenance validation:**
```bash
# Monthly check of all chapters
python3 chapter_validator.py site/docs/chapter-*/index.md --summary > monthly-validation.txt

# Compare to baseline
diff baseline-validation.txt monthly-validation.txt
```

**If scores decline:**
- Identify which chapters regressed
- Review recent changes
- Update as needed

---

## Example Workflow Timeline

### Small Chapter (2,000 words)

- **Day 1:** Write outline, validate (score: 10-15)
- **Day 2-3:** Write Pass 1, validate (score: 25-30)
- **Day 4-5:** Write Pass 2, validate (score: 50-60)
- **Day 6-7:** Write Pass 3, validate (score: 70-75)
- **Day 8:** Add transfer tests, polish (score: 80-85)
- **Day 9:** Self-review, fix issues (score: 85-90)
- **Day 10:** Submit for peer review
- **Day 11-13:** Revise based on feedback
- **Day 14:** Final validation, publish

### Large Chapter (5,000 words)

- **Week 1:** Outline, Pass 1, validate (score: 30)
- **Week 2:** Pass 2, validate (score: 55)
- **Week 3:** Pass 3, initial validation (score: 65)
- **Week 4:** Add tests, diagrams, polish (score: 75)
- **Week 5:** Self-review, fix issues (score: 80)
- **Week 6:** Peer review and revisions
- **Week 7:** Final validation and publish

---

## Common Workflow Anti-Patterns

### ❌ Anti-Pattern 1: "Write Everything, Validate Once"

**Problem:** Wait until chapter is "done" to run validation.

**Result:** 50+ issues discovered at once, requires major restructuring.

**Fix:** Validate after each pass. Catch issues early.

---

### ❌ Anti-Pattern 2: "Validation is a Formality"

**Problem:** Run validator, ignore results, submit anyway.

**Result:** Peer reviewers find the same issues, multiple revision rounds.

**Fix:** Treat validation as a quality gate. Don't submit until score ≥ 70.

---

### ❌ Anti-Pattern 3: "Optimize for the Validator"

**Problem:** Add G-vectors, modes, etc. just to pass checks, without real understanding.

**Result:** Chapter has all required elements but they're wrong or don't add value.

**Fix:** Understand the *purpose* of each element. If a G-vector doesn't clarify composition, it's not helping.

---

### ❌ Anti-Pattern 4: "Copy-Paste from Other Chapters"

**Problem:** Reuse mode matrix, evidence lifecycle, etc. without adaptation.

**Result:** Generic, not tailored to chapter's invariant.

**Fix:** Use templates as starting points, but customize to chapter context.

---

### ❌ Anti-Pattern 5: "Ignore Manual Review"

**Problem:** Focus only on automated score, skip manual dimensions.

**Result:** Chapter passes automated checks but pedagogical flow is poor.

**Fix:** Automated checks are necessary but not sufficient. Manual review is critical.

---

## Tools and Templates

### Validation Script Options Summary

```bash
# Basic validation
python3 chapter_validator.py chapter.md

# Verbose (show all issues)
python3 chapter_validator.py --verbose chapter.md

# HTML report (for sharing)
python3 chapter_validator.py --format html --output report.html chapter.md

# JSON report (for CI/CD)
python3 chapter_validator.py --format json --output report.json chapter.md

# Batch validation with summary
python3 chapter_validator.py chapter-*/index.md --summary

# Custom config
python3 chapter_validator.py --config strict.yaml chapter.md
```

### Chapter Template Checklist

Create `chapter-template-checklist.md` and check off as you write:

```markdown
# Chapter XX Writing Checklist

## Pre-Writing
- [ ] Outline created
- [ ] Primary invariant identified
- [ ] Evidence type planned
- [ ] Mode matrix sketched
- [ ] Transfer tests planned

## Pass 1 (Intuition)
- [ ] Production story or concrete example
- [ ] Invariant at risk shown
- [ ] Felt need established
- [ ] 1-2 backward references

## Pass 2 (Understanding)
- [ ] Mechanism explained
- [ ] Evidence lifecycle detailed (all 6 stages)
- [ ] G-vectors introduced
- [ ] Trade-offs discussed (PACELC, dualities)
- [ ] At least 1 sacred diagram

## Pass 3 (Mastery)
- [ ] Mode matrix complete (all 4 modes)
- [ ] Composition examples (cross-service)
- [ ] Metrics specified
- [ ] Failure modes cataloged
- [ ] Debugging guidance
- [ ] At least 1 more sacred diagram

## Transfer Tests
- [ ] Near test written
- [ ] Medium test written
- [ ] Far test written
- [ ] Expected insights provided

## Polish
- [ ] Irreducible sentence written
- [ ] Context capsule at boundary
- [ ] Forward references added
- [ ] Composition operators explicit (↑, ⤓)
- [ ] All cross-references valid

## Validation
- [ ] Automated score ≥ 70
- [ ] Manual self-review complete
- [ ] Peer review requested
- [ ] Feedback addressed
- [ ] Final validation passed
```

---

## Troubleshooting Workflow Issues

### "I'm stuck at 60-65 score"

**Common causes:**
1. Missing transfer tests (easy 10 points)
2. Incomplete mode matrix (missing Recovery mode)
3. Evidence properties missing 1-2 fields

**Quick wins:**
- Add the 3 transfer tests (even simple ones)
- Add Recovery mode section
- Check each evidence type has all 5 properties

### "Score regressed after revisions"

**Possible reasons:**
1. Accidentally deleted sections (e.g., a mode definition)
2. Changed G-vector syntax (broke pattern matching)
3. Removed cross-references while restructuring

**Fix:**
- Diff against previous version
- Re-run validation on old version to confirm baseline
- Restore deleted sections, update instead of removing

### "Validator says 'No G-vectors' but I have them"

**Debug steps:**
1. Check brackets: Must be `⟨⟩` not `<>` or `[]`
2. Check spacing: `G = ⟨` not `G=⟨` or `G = <`
3. Check components: Must have exactly 6, comma-separated

**Test with minimal example:**
```markdown
G = ⟨Range, Lx, SI, Fresh(φ), Idem(K), Auth(π)⟩
```

If this doesn't validate, check encoding (file must be UTF-8).

---

## Summary: Keys to Success

1. **Validate early and often** - Don't wait until the end
2. **Use validation to guide writing** - Let failed checks tell you what's missing
3. **Understand the framework** - Don't just pass checks, internalize the model
4. **Iterate systematically** - Fix critical issues first, then major, then minor
5. **Manual review matters** - Automated checks are necessary but not sufficient
6. **Cross-references are important** - Chapters should form a coherent book, not standalone articles
7. **Transfer tests reveal understanding** - If you can't write Far tests, you might not deeply understand
8. **Seek feedback early** - Don't polish a fundamentally flawed chapter

**Final reminder:** The validation system exists to ensure quality and consistency.
Use it as a tool to improve your writing, not as a bureaucratic hurdle.

Good luck! 🚀
