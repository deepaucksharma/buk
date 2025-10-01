# Coherence Validation System - Complete Documentation

## Overview

This directory contains a comprehensive validation system for ensuring chapters meet the **Unified Mental Model Authoring Framework 3.0** standards. The system includes automated tools, manual checklists, scoring rubrics, and workflow guides.

---

## Quick Links

### For Authors (First Time)
1. Start here: **[VALIDATION_QUICKSTART.md](VALIDATION_QUICKSTART.md)** - 5-minute guide to getting started
2. Reference: **[CoherenceValidationChecklist.md](CoherenceValidationChecklist.md)** - Complete checklist
3. Workflow: **[VALIDATION_WORKFLOW.md](VALIDATION_WORKFLOW.md)** - Step-by-step process from draft to publication

### For Reviewers
1. **[CoherenceValidationChecklist.md](CoherenceValidationChecklist.md)** - Section 2 (Manual Review Checklist)
2. **[CoherenceValidationChecklist.md](CoherenceValidationChecklist.md)** - Section 5 (Review Rubric)
3. **[CoherenceValidationChecklist.md](CoherenceValidationChecklist.md)** - Appendix B (One-Page Reviewer Form)

### For Framework Maintainers
1. **[chapter_validator.py](chapter_validator.py)** - Automated validation script (source code)
2. **[ChapterCraftingGuide.md](ChapterCraftingGuide.md)** - Framework definition (lines 314-326)
3. **[CoherenceValidationChecklist.md](CoherenceValidationChecklist.md)** - Complete reference

---

## File Inventory

### Primary Documents

| File | Purpose | Audience | Size |
|------|---------|----------|------|
| **CoherenceValidationChecklist.md** | Complete validation system documentation | Authors, Reviewers, Maintainers | 31 KB |
| **VALIDATION_QUICKSTART.md** | Quick start guide with examples | Authors (first-time) | 16 KB |
| **VALIDATION_WORKFLOW.md** | Systematic workflow from draft to publication | Authors (ongoing) | 19 KB |
| **chapter_validator.py** | Automated validation script | Authors, CI/CD | 30 KB |
| **ChapterCraftingGuide.md** | Framework 3.0 specification | All (reference) | 24 KB |

### Supporting Documents

| File | Purpose |
|------|---------|
| VALIDATION_README.md | This file - navigation hub |
| .validation-config.yaml | (Optional) Custom validation settings |

---

## System Components

### 1. Automated Validation

**Tool:** `chapter_validator.py`

**What it checks:**
- G-vector syntax and component values
- Mode matrix completeness (4 modes)
- Evidence properties presence (5 properties)
- Sacred diagram markers (5 types)
- Transfer test presence (3 tests)
- Context capsule structure
- Composition operators usage
- Invariant catalog alignment
- Spiral narrative structure
- Cross-references validity

**Output:**
- Console report (quick feedback)
- JSON report (machine-readable for CI/CD)
- HTML report (human-readable for sharing)

**Scoring:** 0-100 points, passing threshold: 70

---

### 2. Manual Review Checklist

**Found in:** CoherenceValidationChecklist.md, Section 2

**What it checks:**
- Invariant mapping correctness (not just presence)
- Evidence lifecycle completeness (all 6 stages with costs)
- Composition soundness (vectors computed correctly)
- Transfer test quality (actually test transfer, not memorization)
- Pedagogical flow (progressive building, cognitive load)

**Scoring:** Human judgment on 0-10 scale per dimension

---

### 3. Per-Chapter Requirements

**Found in:** CoherenceValidationChecklist.md, Section 3

**Minimum requirements (MUST HAVE):**
- Primary invariant from catalog (exactly 1)
- Evidence type with full lifecycle (at least 1)
- Mode matrix with all 4 modes
- 3 transfer tests (Near, Medium, Far)
- 2 backward references (to prior chapters)
- 1 forward reference (to future chapter)
- Spiral narrative (3-pass structure)
- Irreducible sentence
- At least 2 sacred diagrams
- Context capsule at boundaries

**Nice-to-have (SHOULD HAVE):**
- Production story (real-world incident)
- Metrics to track
- Failure mode catalog
- Composition examples
- Code snippets
- Socratic prompts
- Metaphors from lexicon
- Cross-chapter resonance marking

---

### 4. Review Rubric

**Found in:** CoherenceValidationChecklist.md, Section 5

**Scoring dimensions (10 total):**

| Dimension | Max Points | Weight | Critical? |
|-----------|------------|--------|-----------|
| Invariant Clarity | 15 | 15% | Yes (≥7 required) |
| Evidence Lifecycle | 15 | 15% | Yes (≥7 required) |
| Mode Matrix | 10 | 10% | No |
| Composition | 15 | 15% | Yes (≥7 required) |
| Pedagogy | 15 | 15% | No |
| Transfer Tests | 10 | 10% | No |
| Cross-References | 5 | 5% | No |
| Diagrams | 5 | 5% | No |
| Operational Guidance | 5 | 5% | No |
| Synthesis | 5 | 5% | No |

**Grades:**
- 90-100: A (Excellent) - Ready for publication
- 80-89: B (Good) - Minor revisions suggested
- 70-79: C (Acceptable) - Conditional pass, address major items
- 60-69: D (Needs Work) - Significant revision required
- 0-59: F (Incomplete) - Not ready for review

---

### 5. Validation Workflow

**Found in:** VALIDATION_WORKFLOW.md

**Phases:**

1. **Outline Validation** (pre-writing): Validate structure before writing
2. **Incremental Writing** (ongoing): Validate after each pass
3. **Self-Review** (pre-peer-review): Manual checklist completion
4. **Peer Review** (external): Reviewer applies rubric
5. **Revision** (post-feedback): Address issues systematically
6. **Final Validation** (pre-publication): All checks pass
7. **Post-Publication Maintenance** (ongoing): Re-validate when framework changes

**Timeline examples:**
- Small chapter (2,000 words): ~10 days
- Large chapter (5,000 words): ~7 weeks

---

## Getting Started

### Authors: First Chapter

1. **Read the quick start guide:**
   ```bash
   cat VALIDATION_QUICKSTART.md
   ```

2. **Review the framework coherence section:**
   ```bash
   sed -n '314,326p' ChapterCraftingGuide.md
   ```

3. **Create your chapter outline:**
   - Use the template in VALIDATION_WORKFLOW.md (Phase 1)
   - Validate the outline to see what's needed

4. **Write incrementally and validate:**
   ```bash
   # After each pass
   python3 chapter_validator.py site/docs/chapter-XX/index.md
   ```

5. **Follow the workflow:**
   - See VALIDATION_WORKFLOW.md for detailed phase-by-phase guidance

---

### Reviewers: First Review

1. **Read the review rubric:**
   ```bash
   # Section 5 of the checklist
   sed -n '/## 5\. Review Rubric/,/## 6\./p' CoherenceValidationChecklist.md
   ```

2. **Get the validation report:**
   ```bash
   python3 chapter_validator.py --format html --output review.html site/docs/chapter-XX/index.md
   ```

3. **Review manually:**
   - Use Section 2 (Manual Review Checklist) from CoherenceValidationChecklist.md
   - Use Appendix B (One-Page Reviewer Form)

4. **Provide feedback:**
   - Complete the reviewer checklist
   - Provide line-specific comments
   - Suggest concrete fixes

---

### Maintainers: System Updates

1. **Update the validator:**
   - Edit `chapter_validator.py`
   - Add new checks in the `ChapterValidator` class
   - Update scoring in `calculate_grade()`

2. **Update the framework:**
   - Edit `ChapterCraftingGuide.md`
   - Update the coherence matrix (lines 314-326)
   - Cascade changes to CoherenceValidationChecklist.md

3. **Update documentation:**
   - Keep VALIDATION_QUICKSTART.md examples current
   - Update VALIDATION_WORKFLOW.md if process changes
   - Update this README if files are added/removed

---

## Usage Examples

### Basic Validation

```bash
# Validate one chapter
python3 chapter_validator.py site/docs/chapter-02/index.md

# Output:
# ✗ G-Vector Syntax............... 0/10
# ✓ Mode Matrix................... 10/10
# ...
# Total Score: 51/100 (51.0%)
# Grade: F
# Status: FAIL - Not ready for review
```

---

### Verbose Output (Detailed Feedback)

```bash
python3 chapter_validator.py --verbose site/docs/chapter-02/index.md

# Output includes:
# ✗ G-Vector Syntax............... 0/10
#   No G-vectors found
#   → Add at least one G-vector showing guarantee composition
```

---

### HTML Report (For Sharing)

```bash
python3 chapter_validator.py --format html --output chapter-02-report.html site/docs/chapter-02/index.md

# Open in browser:
# firefox chapter-02-report.html
```

---

### Batch Validation (All Chapters)

```bash
python3 chapter_validator.py site/docs/chapter-*/index.md --summary

# Output:
# Summary (12 chapters)
# ✓ chapter-01/index.md...... 92.0% (A)
# ✗ chapter-02/index.md...... 51.0% (F)
# ✓ chapter-03/index.md...... 88.0% (B)
# ...
# Average Score: 76.3%
```

---

### CI/CD Integration

```bash
# Generate JSON for automated systems
python3 chapter_validator.py --format json --output validation.json site/docs/chapter-*/index.md

# Exit code: 0 if all ≥70, 1 if any fail
# Use in CI pipeline to gate merges
```

---

## Understanding Validation Output

### Automated Checks (10 total, 100 points)

| Check | Max Points | What It Detects | Pass Criteria |
|-------|------------|-----------------|---------------|
| G-Vector Syntax | 10 | Typed guarantee vectors with valid components | ≥1 valid vector |
| Mode Matrix | 10 | All 4 modes defined with triggers | 4/4 modes |
| Evidence Properties | 10 | Full lifecycle (Scope, Lifetime, Binding, Transitivity, Revocation) | 4/5 properties |
| Sacred Diagrams | 5 | Framework-aligned visualizations | ≥2 diagrams |
| Transfer Tests | 10 | Near, Medium, Far knowledge transfer | 3/3 tests |
| Context Capsules | 10 | Boundary tracking with 5 core fields | ≥1 complete capsule |
| Composition Operators | 10 | Explicit composition (▷, ||, ↑, ⤓) | ≥2 operators |
| Invariant Mapping | 15 | Catalog alignment | ≥1 catalog invariant |
| Spiral Narrative | 10 | 3-pass structure (Intuition → Understanding → Mastery) | 3/3 passes |
| Cross-References | 10 | Continuity (backward and forward refs) | 2 back, 1 forward |

**Critical checks (cannot score 0):**
- Invariant Mapping (≥7 required)
- Evidence Properties (≥5 required)
- G-Vector Syntax (≥5 required)

---

### Manual Review Dimensions (5 total)

| Dimension | What Reviewer Checks | Documentation |
|-----------|---------------------|---------------|
| Invariant Mapping Correctness | Is it truly fundamental? Correct category? Complete threat model? | Section 2.1 |
| Evidence Lifecycle Completeness | All 6 stages? Costs quantified? Edge cases? | Section 2.2 |
| Composition Soundness | Boundaries explicit? Vectors computed? Capsules tracked? | Section 2.3 |
| Transfer Test Quality | Actually test transfer? Appropriate distance? Non-trivial? | Section 2.4 |
| Pedagogical Flow | Progressive building? Cognitive load managed? Smooth transitions? | Section 2.5 |

---

## Troubleshooting

### "Validation script not found"

**Cause:** Running from wrong directory or script not executable.

**Fix:**
```bash
# Make executable
chmod +x chapter_validator.py

# Run with full path
python3 /home/deepak/buk/chapter_validator.py site/docs/chapter-02/index.md
```

---

### "No G-vectors found" but they exist

**Cause:** Wrong bracket type or spacing.

**Fix:** Use exactly this syntax:
```markdown
G = ⟨Range, Lx, SI, Fresh(φ), Idem(K), Auth(π)⟩
```

Not: `G = <Range, ...>` or `G=⟨Range,...⟩`

---

### "Score doesn't improve after fixes"

**Cause:** May have introduced new issues while fixing others.

**Fix:**
```bash
# Re-run validation after EACH fix to ensure no regression
python3 chapter_validator.py site/docs/chapter-XX/index.md
```

---

### "Validation passes but chapter still feels off"

**Cause:** Automated checks are necessary but not sufficient. Manual dimensions matter.

**Fix:** Complete the manual review checklist (Section 2 of CoherenceValidationChecklist.md).

---

## Common Questions

### Q: What's the minimum passing score?
**A:** 70/100 total, with critical checks (Invariant, Evidence, G-Vectors) each ≥ threshold.

### Q: Can I skip transfer tests?
**A:** No, they're worth 10 points and are minimum requirements. However, they can start simple and be refined.

### Q: What if my chapter introduces a new invariant not in the catalog?
**A:** Justify it as a composition of existing invariants. Example: "Bounded staleness = Order + Recency constraint"

### Q: How long should each pass be?
**A:** No hard limit, but Pass 3 should be ≥300 words. Total chapter typically 2,000-5,000 words.

### Q: Can I have multiple primary invariants?
**A:** No. Focus on ONE primary invariant. Supporting invariants are OK but should be clearly secondary.

### Q: What if automated and manual scores disagree?
**A:** Manual review trumps automated. Automated catches syntax/structure; manual catches correctness/quality.

### Q: Do I need to validate every revision?
**A:** Yes, after any substantial change. Small typo fixes don't need re-validation.

### Q: Can I customize validation thresholds?
**A:** Yes, create `.validation-config.yaml` and override defaults. See VALIDATION_QUICKSTART.md.

---

## Best Practices

### For Authors

1. **Validate early and often** - Don't wait until the end
2. **Fix critical issues first** - Invariant, Evidence, Composition before polish
3. **Understand the framework** - Don't just pass checks mechanically
4. **Use manual checklist** - Automated checks don't catch everything
5. **Seek feedback before 100% done** - Early feedback saves time

### For Reviewers

1. **Run automated validation first** - Don't duplicate work the script can do
2. **Focus on manual dimensions** - That's where human judgment is needed
3. **Provide specific line numbers** - Help authors find issues quickly
4. **Suggest concrete fixes** - Not just "improve this"
5. **Distinguish must-fix from nice-to-have** - Use PASS/CONDITIONAL/FAIL clearly

### For Teams

1. **Establish baseline** - All chapters ≥70 before new work
2. **Track trends** - Monitor average score over time
3. **Share learnings** - Common issues → add to examples
4. **Evolve the framework** - Validation findings inform framework updates
5. **Automate in CI** - Gate merges on validation passing

---

## Maintenance

### Monthly Check

```bash
# Validate all chapters
python3 chapter_validator.py site/docs/chapter-*/index.md --summary > monthly-report.txt

# Compare to baseline
diff baseline-report.txt monthly-report.txt
```

### After Framework Update

```bash
# Re-validate all chapters with new framework
python3 chapter_validator.py site/docs/chapter-*/index.md --format json --output post-update.json

# Identify chapters that need updates
jq '.[] | select(.percentage < 70) | .chapter_path' post-update.json
```

---

## Contributing

### Adding a New Check

1. **Edit `chapter_validator.py`:**
   - Add method to `ChapterValidator` class
   - Follow pattern: `def check_XXX(self, content, lines) -> ValidationResult`
   - Update `validate_chapter()` to call new check

2. **Update documentation:**
   - Add to Section 1 (Automated Checks) in CoherenceValidationChecklist.md
   - Add example to VALIDATION_QUICKSTART.md
   - Add to troubleshooting if needed

3. **Test:**
   ```bash
   # Test on known-good chapter
   python3 chapter_validator.py site/docs/chapter-01/index.md

   # Test on known-bad chapter
   python3 chapter_validator.py site/docs/chapter-02/index.md
   ```

### Updating the Rubric

1. **Edit Section 5 of CoherenceValidationChecklist.md**
2. **Update weights** (must still sum to 100%)
3. **Re-run all validations** to establish new baseline

---

## Version History

- **v1.0** (2025-10-01): Initial release
  - 10 automated checks
  - 5 manual review dimensions
  - Complete workflow documentation
  - Python validation script

---

## Contact

For questions, issues, or suggestions:

- **Framework questions:** See ChapterCraftingGuide.md
- **Validation issues:** Check VALIDATION_QUICKSTART.md Troubleshooting section
- **Bug reports:** Document in validation script comments
- **Feature requests:** Propose in Contributing section above

---

## License

This validation system is part of the Unified Mental Model Authoring Framework 3.0.
See main repository for license information.

---

**Remember:** Validation is a tool to improve quality, not a barrier to creativity.
Use it to make your chapters clearer, more coherent, and more valuable to readers.

Happy writing! 📝✨
