# Chapter Crafting Templates - Quick Start Guide

## Overview

This repository contains comprehensive implementation templates for authoring book chapters using the Unified Mental Model Authoring Framework 3.0. These templates help authors create consistent, insight-driven content that teaches transferable understanding of distributed systems.

## Files in This Repository

1. **ChapterCraftingGuide.md** - The complete framework specification
2. **ChapterCraftingTemplates.md** - Implementation templates (this is your main working document)

## What's Inside ChapterCraftingTemplates.md

A 3000+ line comprehensive toolkit containing:

### Core Templates

1. **Guarantee Vector Template** (Section 1)
   - YAML format for typing guarantees
   - Examples of composition (meet, upgrade, downgrade)
   - Validation rules

2. **Mode Matrix Generator** (Section 2)
   - YAML input specification
   - Python script to generate Markdown tables
   - Example mode definitions

3. **Evidence Card Template** (Section 3)
   - Full lifecycle specification
   - Properties: scope, lifetime, binding, transitivity, revocation
   - Cost analysis and usage examples

4. **Context Capsule Schema** (Section 4)
   - JSON Schema definition
   - Example capsules (fresh, degraded, transaction)
   - Python implementations of capsule operations

5. **Sacred Diagram ASCII Templates** (Section 5)
   - All 5 canonical diagrams with fill-in templates
   - Consistent visual grammar
   - Symbology guide

6. **Chapter Development Canvas** (Section 6)
   - Complete 17-section canvas
   - Example filled canvas (Follower Reads)
   - Validation checklist

### Supporting Tools (Section 7)

- **Mental Linter** - Python script to validate chapter drafts
- **Guarantee Vector Validator** - Composition checker
- **Capsule Operations** - Reference implementations

## Quick Start: Three Workflows

### Workflow 1: Writing a New Chapter

1. Open **ChapterCraftingTemplates.md** Section 6.1
2. Copy the "Chapter Development Canvas" template
3. Fill out sections 1-3 (Invariant, Uncertainty, Evidence) first
4. Type the guarantee path with G vectors (Section 4)
5. Define modes (Section 6)
6. Choose 1-2 diagrams from Section 5
7. Run mental linter (Section 7.1)

**Files you'll create:**
- `chapter-N-canvas.md` (your filled canvas)
- `chapter-N-modes.yaml` (if using mode matrix)
- `chapter-N-vectors.yaml` (if complex composition)

### Workflow 2: Designing a New Mechanism

1. Start with **Evidence Card Template** (Section 3.2)
2. Define the evidence lifecycle
3. Create **Guarantee Vector** specification (Section 1.1)
4. Build **Mode Matrix** (Section 2.1)
5. Draw **Invariant Guardian** diagram (Section 5.1)

**Files you'll create:**
- `mechanism-name-evidence.yaml`
- `mechanism-name-modes.yaml`
- `mechanism-name-guardian.txt` (ASCII diagram)

### Workflow 3: Analyzing Composition

1. Define **Context Capsule** for each boundary (Section 4.1)
2. Type each path segment with G vectors (Section 1)
3. Identify meet points (where guarantees weaken)
4. Draw **Composition Ladder** (Section 5.1, Diagram 3)
5. Validate with Guarantee Vector Validator (Section 7.2)

**Files you'll create:**
- `composition-analysis-capsules.json`
- `composition-ladder.txt` (ASCII diagram)

## Template Navigation Guide

### By Task

| Task | Go to Section | Template |
|------|--------------|----------|
| Type a guarantee path | 1.1 | Guarantee Vector YAML |
| Document evidence | 3.1 | Evidence Card YAML |
| Plan degradation | 2.1 | Mode Matrix YAML |
| Cross boundaries | 4.1 | Context Capsule JSON Schema |
| Visualize pattern | 5.1 | Sacred Diagrams ASCII |
| Outline chapter | 6.1 | Chapter Canvas Markdown |
| Validate draft | 7.1 | Mental Linter Python |

### By Framework Component

| Component | Template Section | Key Files |
|-----------|-----------------|-----------|
| **Invariant Hierarchy** | 6.1 (Section 1) | Canvas template |
| **Evidence Calculus** | 3.1-3.3 | Evidence Card |
| **Guarantee Vectors** | 1.1-1.4 | G Vector YAML |
| **Context Capsules** | 4.1-4.5 | Capsule JSON Schema |
| **Mode Matrix** | 2.1-2.4 | Mode YAML + Generator |
| **Sacred Diagrams** | 5.1-5.3 | 5 ASCII templates |
| **Learning Spiral** | 6.1 (Section 9) | Canvas template |
| **Transfer Tests** | 6.1 (Section 10) | Canvas template |

## Examples Included

Each template includes:
- **Blank fill-in version** - For your content
- **Complete example** - Usually "Follower Reads with Closed Timestamps"
- **Validation rules** - Checklist for completeness
- **Best practices** - Tips for effective use

### Example Files You Can Copy

1. **Follower Reads Guarantee Vector** (Section 1.1, lines 24-210)
2. **Closed Timestamp Evidence Card** (Section 3.1, lines 644-812)
3. **Replica Read Mode Matrix** (Section 2.1, lines 386-468)
4. **Follower Read Context Capsule** (Section 4.2, lines 1129-1187)
5. **Complete Filled Canvas** (Section 6.2, lines 2295-2589)

## Tools and Scripts

### Mental Linter (Section 7.1)

```bash
python mental_linter.py chapter-draft.md
```

Checks for:
- Invariant naming from catalog
- Evidence properties (scope, lifetime, binding)
- G vector presence
- Context capsule fields
- Mode matrix completeness
- Explicit downgrades
- Learning spiral structure
- Transfer tests

### Mode Matrix Generator (Section 2.2)

```bash
python mode_matrix_generator.py modes.yaml > modes.md
```

Converts YAML mode specifications to formatted Markdown tables.

### Guarantee Vector Validator (Section 7.2)

```python
from guarantee_validator import GuaranteeVector

leader = GuaranteeVector("Range", "SS", "SER", "Fresh", "Idem(K)", "Auth(π)")
follower = GuaranteeVector("Range", "Lx", "SI", "Fresh", "Idem(K)", "Auth(π)")
composed = leader.meet(follower)
```

## Visual Reference

### The Five Sacred Diagrams (Section 5.1)

1. **Invariant Guardian** - How mechanisms protect invariants
2. **Evidence Flow** - Lifecycle from generation to expiry
3. **Composition Ladder** - Guarantee strength visualization
4. **Mode Compass** - Operational mode transitions
5. **Knowledge vs Data Flow** - Evidence/data plane separation

Each diagram has:
- Blank template
- Filled example
- Symbology guide

### Consistent Symbols (Section 5.2)

- ⚡ Threat
- 🛡️ Mechanism/Protection
- 📜 Evidence
- ✓ Verification
- ✗ Rejection/Revocation
- ⏰ Time-based event
- ♻ Renewal
- ⊗ Degradation point

## Validation Workflow

Before submitting a chapter (Section 6.1, Section 15):

- [ ] Maps to exactly one primary invariant from catalog
- [ ] Uses evidence types with scope, lifetime, binding, revocation
- [ ] Path typed with G vectors; meet/upgrade/downgrade explicit
- [ ] Capsule has all five core fields
- [ ] Mode matrix shows all four modes and triggers
- [ ] Dualities stated with justified stance
- [ ] Spiral narrative present
- [ ] Contains three transfer tests
- [ ] Reinforces two prior concepts and sets up one future
- [ ] Ends with irreducible sentence
- [ ] Diagrams use consistent symbology
- [ ] Human mental model (See/Think/Do) included
- [ ] No hidden downgrades
- [ ] No evidence-free claims

## Common Patterns

### Pattern 1: Freshness via Time-Bound Evidence

**Example:** Follower reads with closed timestamps

- **Invariant:** Freshness
- **Evidence:** Closed timestamp φ
- **Guarantee:** Fresh(φ) → BS(δ) → EO (degradation path)
- **Mode transitions:** Target (φ active) → Degraded (φ stale) → Floor (φ expired)

**Templates used:**
- Section 1.1 (G vector)
- Section 3.1 (Evidence card for φ)
- Section 5.1 Diagram 2 (Evidence lifecycle)
- Section 6.2 (Complete example)

### Pattern 2: Uniqueness via Lease

**Example:** Leader election

- **Invariant:** Uniqueness (at most one leader)
- **Evidence:** Lease epoch E
- **Guarantee:** Exclusive authority within epoch
- **Mode transitions:** Target (lease active) → Recovery (lease lost)

**Templates used:**
- Section 3.1 (Evidence card for lease)
- Section 5.1 Diagram 1 (Invariant guardian)
- Section 2.1 (Mode matrix)

### Pattern 3: Order via Commit Certificate

**Example:** Consensus protocol

- **Invariant:** Order (A precedes B)
- **Evidence:** Commit certificate with position
- **Guarantee:** Lx or SS depending on scope
- **Mode transitions:** Target (quorum healthy) → Degraded (no new commits) → Floor (read-only)

**Templates used:**
- Section 1.1 (G vector with Order component)
- Section 3.1 (Evidence card for commit cert)
- Section 4.1 (Capsule carrying commit evidence)

## Tips for Success

1. **Start simple** - Fill out one template at a time
2. **Use examples** - Copy and modify the "Follower Reads" examples
3. **Validate often** - Run mental linter on drafts
4. **Reuse terminology** - Stick to invariant catalog names
5. **Label downgrades** - Never silently weaken guarantees
6. **Show evidence costs** - Generation vs verification

## Getting Help

- **Framework questions:** See ChapterCraftingGuide.md
- **Template questions:** See ChapterCraftingTemplates.md section 8 (Best Practices)
- **Examples:** See section 6.2 (Complete Filled Canvas)
- **Validation:** Run mental linter (section 7.1)

## Version Information

- **Templates Version:** 1.0
- **Last Updated:** 2025-10-01
- **Framework Version:** 3.0 (Expanded Edition)
- **Maintained By:** Book Authors

## Quick Reference Card

### Guarantee Vector Components

| Component | Weak → Strong |
|-----------|--------------|
| Scope | Object → Range → Transaction → Global |
| Order | None → Causal → Lx → SS |
| Visibility | Fractured → RA → SI → SER |
| Recency | EO → BS(δ) → Fresh(φ) |

### Evidence Properties (Always Document)

- **Scope:** What domain it covers
- **Lifetime:** When it expires
- **Binding:** Who/what it's valid for
- **Transitivity:** Can downstream use it?
- **Revocation:** How it's invalidated

### Four Modes (Always Define)

- **Floor:** Minimum viable correctness (never lie)
- **Target:** Normal operation (all guarantees)
- **Degraded:** Reduced guarantees (labeled)
- **Recovery:** Rebuilding evidence (restricted)

---

**Ready to start?** Open ChapterCraftingTemplates.md and jump to Section 6.1 (Chapter Development Canvas) to begin outlining your chapter!
