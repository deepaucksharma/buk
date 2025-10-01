# Priority Fix List - Distributed Systems Book

**Generated**: October 1, 2025
**Review Coverage**: Chapters 1-8 + Overview Pages (43% complete)

---

## 🔴 CRITICAL FIXES (Block Publication)

### 1. Remove Fabricated Financial Claims
**Files**: MASTER-EXECUTION-PLAN.md, index.md, chapter-01/production-stories.md

**Issues**:
- MongoDB "$2.3M election storm" - UNVERIFIABLE
- Wall Street "$100M nanosecond" - UNVERIFIABLE
- Google "$100M time infrastructure" - UNDISCLOSED

**Action**: Either provide citations to public incident reports OR remove specific dollar amounts and use "significant financial impact" language.

---

### 2. Fix Structural Hallucination
**File**: about.md (lines 69-82)

**Issue**: Describes book structure as Parts I-VII but only Part V actually exists.

**Action**: Rewrite to reflect actual chapter-based organization (Chapters 1-21) or create the actual Part structure.

---

### 3. Replace Placeholder Contact Info
**File**: about.md (line 135)

**Issue**: `Email: contact@example.com` is a fake placeholder

**Action**: Replace with real contact email or remove the line entirely.

---

### 4. Add Missing Chapters to Reading Paths
**File**: how-to-read.md (lines 9-73)

**Issue**: ALL reading paths omit Chapters 17-21 (24% of book content)

**Action**: Add guidance for final 5 chapters:
- Chapter 17: CRDTs
- Chapter 18: End-to-End Arguments
- Chapter 19: Complexity and Emergence
- Chapter 20: The Cutting Edge
- Chapter 21: Philosophy of Distributed Systems

---

### 5. Correct GitHub 2018 Incident Description
**Files**: index.md (line 55), chapter-01/index.md (line 89)

**Issue**: Calls it "24-hour CAP recovery" but:
- CAP theorem has no "recoveries"
- Actual incident was MySQL/Orchestrator issue, not multi-master divergence

**Action**: Rephrase as "GitHub's 24-hour network partition incident (October 2018)" with accurate technical details.

---

### 6. Fix Netflix Streaming Launch Date
**File**: chapter-05/index.md (line 1148)

**Issue**: Claims streaming launched in 2009, actually launched January 2007

**Action**: Correct to "2007: Streaming launches" and adjust timeline accordingly.

---

### 7. Fix Uber Service Consolidation Claim
**File**: chapter-05/index.md (line 1201)

**Issue**: Claims consolidated to "~100 macroservices" but never went below ~1000

**Action**: Correct to "consolidated from 2200+ to approximately 1000 domain-oriented services"

---

### 8. Update Deprecated Istio Components
**File**: chapter-08/index.md (lines 360-361)

**Issue**: Shows Citadel and Galley as separate components, but both merged into Istiod in March 2020

**Action**: Update architecture diagram and text to reflect current Istio 1.5+ structure with unified Istiod.

---

## 🟠 HIGH PRIORITY (Before Marketing/Distribution)

### 9. Replace Temporal Language
**Files**: Multiple (index.md, about.md, chapter-05, etc.)

**Issues**:
- "2025" references will be obsolete in months
- "Modern" and "contemporary" age poorly
- Facebook Libra (discontinued 2022) still referenced

**Action**:
- "2025" → "as of this writing" or remove year
- "Modern/contemporary" → "current-generation" or "production"
- Update Libra references to reflect discontinuation

---

### 10. Fix Consensus Protocol Publication Dates
**Files**: chapter-03/index.md, paxos.md, raft.md

**Issues**:
- Paxos: Inconsistent between "1989" and "1998" (submitted 1989, published 1998)
- Raft: Inconsistent "2013" vs "2014" (work started 2013, published 2014)
- HotStuff: "2019" should be "2018" (PODC 2019 proceedings, published 2018)

**Action**: Standardize across files with clear submission/publication distinction.

---

### 11. Remove Non-Standard "Fractured" Visibility Term
**File**: mental-model.md (line 111)

**Issue**: "Fractured" is not a standard database isolation level

**Action**: Replace with standard terms (Read Uncommitted, Read Committed, Repeatable Read, Snapshot, Serializable)

---

### 12. Qualify HotStuff O(n) Complexity Claims
**Files**: chapter-03/index.md (line 782), byzantine.md

**Issue**: States "O(n) message complexity" but this requires threshold signatures

**Action**: Add qualifier: "O(n) message complexity (with threshold signatures)" everywhere it appears.

---

### 13. Update Outdated Software Versions
**Files**: chapter-07 (containers.md, index.md)

**Critical EOL versions**:
- Node.js 14/16 → Update to 20 or 22
- Go 1.19 → Update to 1.21+
- PHP 5.4/7.2 → Update to 8.1+

**Action**: Update ALL code examples to current LTS versions.

---

### 14. Fix CAP Theorem Mischaracterization
**File**: chapter-05/index.md (line 1275)

**Issue**: States "CAP Theorem: Cannot have consistency + availability during partitions (physics)"

**Action**: Correct to specify this is distributed systems theory, not physics. Network partitions are engineering failures, not physics constraints.

---

### 15. Correct Technical Errors
**Issues**:
- Firecracker powers Fargate (NO - only Lambda)
- "Byzantine Paxos" (not standard terminology)
- Fast Paxos "skips Phase 1" (misleading - uses larger quorums)
- CRDT "Order: None" (some CRDTs require causal ordering)

**Action**: Correct each with accurate technical descriptions.

---

## 🟡 MEDIUM PRIORITY (Quality Improvement)

### 16. Add Citations for Production Claims
**Files**: chapter-01, 04, 05, 07, 08

**Unverified claims needing sources**:
- AWS DynamoDB 2015 outage details
- Facebook Memcache 2012 incident
- Netflix 2008 "three days" duration
- Uber specific latency numbers
- LinkedIn "7+ trillion events/day"
- Capital One "70% cost reduction"

**Action**: Either cite public post-mortems or label as "hypothetical scenarios based on common patterns."

---

### 17. Add Warnings for Saga Pattern
**File**: chapter-08/index.md (lines 857-946)

**Issue**: Saga patterns described without mentioning they DON'T provide ACID guarantees

**Action**: Add explicit warning: "Sagas provide eventual consistency, not ACID. During compensation, system may be in inconsistent intermediate states."

---

### 18. Clarify "70% Rewrite Failure" Claim
**Files**: chapter-05/index.md (lines 330, 1031)

**Issue**: Specific "70%" statistic widely cited but lacks rigorous empirical backing

**Action**: Either cite specific source or soften to "most rewrites fail" with caveat about anecdotal nature.

---

### 19. Update Kafka ZooKeeper Dependency
**File**: chapter-08/index.md (lines 636-637)

**Issue**: Shows ZooKeeper as required, but KRaft mode available since Kafka 2.8 (2021)

**Action**: Update to "ZooKeeper (legacy) or KRaft (modern consensus, Kafka 3.3+)"

---

### 20. Clarify Connection Pooling Evolution
**File**: chapter-05/index.md (lines 355, 446)

**Issue**: Describes connection pooling in both client-server and three-tier without explaining evolution

**Action**: Clarify that early client-server apps often DIDN'T implement pooling (causing problems), became standard in three-tier.

---

## 🟢 LOW PRIORITY (Polish)

### 21. Improve Time Estimate Accuracy
**File**: how-to-read.md

**Issues**: Time estimates don't match per-chapter calculations

**Action**: Recalculate all path times based on component estimates or add high-variability disclaimers.

---

### 22. Standardize Terminology
**Issues**: "Wall clock" vs "Physical clock" vs "System clock" used interchangeably

**Action**: Define terms in introduction and use consistently across chapters.

---

### 23. Add Version Context
**Files**: Multiple chapters

**Issue**: Technology references lack version/date context

**Action**: Add version tags (e.g., "as of Kafka 3.5") or "Last updated: [date]" markers.

---

### 24. Update "Future Directions" Sections
**Files**: chapter-05, chapter-07

**Issue**: Treats already-deployed technologies (service mesh, GitOps, eBPF) as speculative

**Action**: Move deployed technologies to current state, update truly future items.

---

### 25. Create Comprehensive Glossary
**File**: Referenced in how-to-read.md (line 92) but doesn't exist

**Action**: Create the promised glossary or remove reference.

---

## Summary Statistics

### Issues by Severity
| Severity | Count | % of Total |
|----------|-------|-----------|
| 🔴 Critical | 8 | 32% |
| 🟠 High | 7 | 28% |
| 🟡 Medium | 5 | 20% |
| 🟢 Low | 5 | 20% |
| **Total** | **25** | **100%** |

### Issues by Category
| Category | Count |
|----------|-------|
| Factual Errors | 12 |
| Outdated Information | 6 |
| Unverified Claims | 4 |
| Structural Issues | 2 |
| Terminology/Clarity | 1 |

### Estimated Fix Time
- **Critical fixes**: 8-12 hours
- **High priority**: 12-16 hours
- **Medium priority**: 8-10 hours
- **Low priority**: 6-8 hours
- **Total**: 34-46 hours

---

## Recommended Workflow

### Phase 1: Block Publication (Critical)
1. Fix fabricated financial claims (search/replace all instances)
2. Fix about.md structure hallucination
3. Replace placeholder email
4. Add Chapters 17-21 to reading paths
5. Correct GitHub/Netflix/Uber incident descriptions
6. Update Istio architecture

**Timeline**: 2-3 days

### Phase 2: Pre-Marketing (High Priority)
1. Global search/replace temporal language
2. Fix consensus protocol dates
3. Remove "Fractured" term
4. Qualify HotStuff claims
5. Update software versions (Node, Go, PHP)
6. Fix technical errors

**Timeline**: 3-4 days

### Phase 3: Quality Polish (Medium Priority)
1. Add citations or disclaimers for unverified claims
2. Add saga pattern warnings
3. Update Kafka/ZooKeeper references
4. Clarify "70% rewrite failure"
5. Fix connection pooling explanation

**Timeline**: 2-3 days

### Phase 4: Final Polish (Low Priority)
1. Improve time estimates
2. Standardize terminology
3. Add version context
4. Update "Future" sections
5. Create glossary

**Timeline**: 2-3 days

---

**Total Estimated Timeline**: 9-13 business days for complete fixes

---

## Files Requiring Most Attention

1. **MASTER-EXECUTION-PLAN.md**: 43 issues (timeline unrealistic, fabricated claims)
2. **about.md**: Structural hallucination, fake email
3. **how-to-read.md**: Missing chapters, bad time estimates
4. **chapter-05/index.md**: 22 issues (dates, claims, outdated refs)
5. **chapter-07** (containers): 25 issues (outdated versions)
6. **chapter-08** (architectures): 17 issues (deprecated components)

---

## Next Steps

1. **Complete review** of Chapters 9-21 (remaining 57% of content)
2. **Generate automated fix scripts** for global search/replace items
3. **Create verification checklist** for each category of fix
4. **Establish CI/CD checks** to prevent regression

---

**Document Status**: Active Fix List
**Last Updated**: October 1, 2025
**Coverage**: Chapters 1-8 (43% of book)
