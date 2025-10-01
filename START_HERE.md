# Chapter Crafting Templates - START HERE

## What You Have

A complete toolkit for authoring distributed systems book chapters using the **Unified Mental Model Authoring Framework 3.0**.

---

## 📁 Your Files (in /home/deepak/buk/)

### 1. 📖 **DELIVERABLES_SUMMARY.md** ← READ THIS FIRST
- Complete overview of everything created
- What each file does
- How to use the templates
- Example workflows
- **Start here to understand the full scope**

### 2. 🚀 **TEMPLATES_README.md** ← QUICK START GUIDE
- How to get started in 5 minutes
- Three common workflows
- Navigation guide
- Where to find what you need
- **Start here to begin using templates**

### 3. 🛠️ **ChapterCraftingTemplates.md** ← MAIN WORKING FILE (107 KB!)
- All 6 comprehensive templates:
  1. Guarantee Vector (YAML)
  2. Mode Matrix (YAML → Markdown)
  3. Evidence Card (YAML)
  4. Context Capsule (JSON Schema)
  5. Sacred Diagrams (ASCII, 5 types)
  6. Chapter Development Canvas (17 sections)
- Working Python scripts (3 tools)
- Complete examples throughout
- Validation checklists
- **This is your primary reference**

### 4. 🗺️ **template-structure.txt** ← STRUCTURE OVERVIEW
- File organization map
- Quick reference to sections
- Cheat sheets
- Where to find specific templates
- **Use this for quick navigation**

### 5. 📚 **ChapterCraftingGuide.md** ← FRAMEWORK SPECIFICATION
- The framework these templates implement
- Conceptual foundation
- Why these templates exist
- **Reference for understanding principles**

---

## 🎯 Quick Start Paths

### Path 1: "I need to write a chapter NOW"
```
1. Open TEMPLATES_README.md → Section "Workflow 1"
2. Open ChapterCraftingTemplates.md → Section 6.1
3. Copy the Chapter Canvas template
4. Fill sections 1-3 (Invariant, Uncertainty, Evidence)
5. Run mental linter (Section 7.1)
```

### Path 2: "I need to understand everything first"
```
1. Read DELIVERABLES_SUMMARY.md (15 min)
2. Read ChapterCraftingGuide.md (45 min)
3. Study example canvas in Section 6.2 (30 min)
4. Review each template in sequence (2 hours)
```

### Path 3: "I just need to document a mechanism"
```
1. Open ChapterCraftingTemplates.md → Section 3.2
2. Copy blank Evidence Card template
3. Fill in lifecycle and properties
4. Create Guarantee Vector (Section 1.1)
5. Define modes (Section 2.1)
```

---

## 🎁 What You Get

### Templates (6)
- ✅ Guarantee Vector (types guarantees, composition)
- ✅ Mode Matrix (defines operational modes)
- ✅ Evidence Card (documents proof lifecycle)
- ✅ Context Capsule (carries guarantees across boundaries)
- ✅ Sacred Diagrams (5 canonical visualizations)
- ✅ Chapter Canvas (complete chapter outline)

### Tools (3)
- ✅ Mental Linter (validates chapter drafts)
- ✅ Mode Matrix Generator (YAML → Markdown)
- ✅ Guarantee Vector Validator (checks composition)

### Examples (1 complete end-to-end)
- ✅ Follower Reads with Closed Timestamps
  - Full guarantee vector
  - Complete evidence card  
  - Mode matrix (4 modes)
  - Context capsules
  - All 5 diagrams
  - Filled chapter canvas

### Documentation (4 files)
- ✅ This file (START_HERE.md)
- ✅ Quick start (TEMPLATES_README.md)
- ✅ Full summary (DELIVERABLES_SUMMARY.md)
- ✅ Structure map (template-structure.txt)

---

## 🔑 Key Concepts (Quick Reference)

### Guarantee Vector
```
G = ⟨Scope, Order, Visibility, Recency, Idempotence, Auth⟩
```
Types what guarantees a system provides.

### Context Capsule
```json
{
  "invariant": "Freshness",
  "evidence": {...},
  "boundary": {...},
  "mode": "Target",
  "fallback": {...}
}
```
Carries guarantees across system boundaries.

### Four Modes
- **Floor**: Minimum viable correctness (never lie)
- **Target**: Normal operation (all guarantees)
- **Degraded**: Reduced guarantees (labeled)
- **Recovery**: Rebuilding evidence (restricted)

### Five Sacred Diagrams
1. **Invariant Guardian** - Threat → Invariant ← Mechanism → Evidence
2. **Evidence Flow** - Generation → Use → Expiry → Renewal
3. **Composition Ladder** - Strong → Bounded → Weak
4. **Mode Compass** - Target ↔ Degraded ↔ Recovery → Floor
5. **Knowledge vs Data** - Evidence plane vs Data plane

---

## 📊 File Sizes

| File | Size | Lines | Purpose |
|------|------|-------|---------|
| ChapterCraftingTemplates.md | 107 KB | 3,013 | Main templates |
| DELIVERABLES_SUMMARY.md | 18 KB | 575 | Overview |
| TEMPLATES_README.md | 10 KB | 325 | Quick start |
| template-structure.txt | 6.9 KB | 200 | Structure |
| ChapterCraftingGuide.md | 24 KB | 510 | Framework |
| **TOTAL** | **166 KB** | **4,623** | Complete toolkit |

---

## ✅ Validation Checklist (Before Submitting)

When you finish a chapter, check:

- [ ] Maps to one primary invariant from catalog?
- [ ] Evidence has scope, lifetime, binding, revocation?
- [ ] G vectors show composition (meet/upgrade/downgrade)?
- [ ] Context capsule has all 5 core fields?
- [ ] Mode matrix defines all 4 modes?
- [ ] Dualities justified?
- [ ] Learning spiral (intuition → understanding → mastery)?
- [ ] Transfer tests (near, medium, far)?
- [ ] Reinforces prior concepts, sets up future?
- [ ] Irreducible sentence captures essence?
- [ ] Diagrams use consistent symbols?
- [ ] Human model (See/Think/Do)?
- [ ] No hidden downgrades?
- [ ] No evidence-free claims?

**Run:** `python mental_linter.py chapter.md`

---

## 🎓 Example: Follower Reads

The templates use this example throughout:

**Problem:** Leader becomes read bottleneck; need to scale reads.

**Solution:** Followers serve reads with freshness proof (closed timestamp φ).

**Invariant:** Freshness - never serve stale data as fresh.

**Evidence:** Closed timestamp φ certifying all txns ≤ φ applied.

**Guarantee Vector:**
```
Input:  ⟨Range, SS,  SER, Fresh(φ), Idem(K), Auth(π)⟩ (leader)
Output: ⟨Range, Lx,  SI,  Fresh(φ), Idem(K), Auth(π)⟩ (follower)
                 ↑                    ↑
               weaker               same (φ present)
```

**Modes:**
- Target: φ age < 9s → Fresh reads
- Degraded: φ age < 30s → BS(30s) with label
- Floor: φ age > 30s → Eventual consistency

**See complete example in Section 6.2 of ChapterCraftingTemplates.md**

---

## 💡 Pro Tips

1. **Start with Canvas** - Section 6.1 forces you to think through everything
2. **Use Examples** - Copy and modify "Follower Reads" examples
3. **Validate Often** - Run mental linter after each section
4. **Reuse Terms** - Stick to invariant catalog names
5. **Label Downgrades** - Never silently weaken guarantees
6. **Show Costs** - Document evidence generation vs verification

---

## 🆘 Getting Help

| Question | File | Section |
|----------|------|---------|
| What is this? | DELIVERABLES_SUMMARY.md | Overview |
| How do I start? | TEMPLATES_README.md | Quick Start |
| Where is X template? | template-structure.txt | File Structure |
| How do I use template X? | ChapterCraftingTemplates.md | Section X |
| Why does this exist? | ChapterCraftingGuide.md | Foundation |
| What's an example look like? | ChapterCraftingTemplates.md | Section 6.2 |

---

## 🚀 Ready to Begin?

### For Writers:
1. Read **TEMPLATES_README.md** (10 minutes)
2. Open **ChapterCraftingTemplates.md** Section 6.1
3. Copy Chapter Canvas template to new file
4. Start filling sections 1-3
5. Iterate!

### For Reviewers:
1. Read **DELIVERABLES_SUMMARY.md** (15 minutes)
2. Run **mental_linter.py** on draft
3. Check Section 6.1 #15 validation checklist
4. Verify examples follow "Follower Reads" pattern

### For System Designers:
1. Read **ChapterCraftingGuide.md** (30 minutes)
2. Create **Evidence Card** (Section 3.2)
3. Define **Guarantee Vector** (Section 1.1)
4. Build **Mode Matrix** (Section 2.1)
5. Draw **Invariant Guardian** (Section 5.1)

---

## 📞 Document Info

- **Created:** 2025-10-01
- **Version:** 1.0
- **Framework:** Unified Mental Model Authoring Framework 3.0
- **Location:** /home/deepak/buk/
- **Maintained By:** Book Authors

---

**NEXT STEP:** Open **TEMPLATES_README.md** or **DELIVERABLES_SUMMARY.md** ➔
