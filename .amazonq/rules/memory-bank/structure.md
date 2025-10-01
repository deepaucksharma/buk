# Project Structure

## Directory Organization

### Core Content Structure
- **`site/docs/`** - Main documentation source files organized by chapters
  - `chapter-01/` through `chapter-21/` - Individual chapter content
  - `about.md`, `how-to-read.md`, `mental-model.md` - Book introduction and framework
- **`toc/`** - Table of contents and structural planning documents
  - Part-based organization (7 parts covering foundations through future)
  - Cross-cutting concerns (observability, data governance)
- **`expanded-toc-chapters/`** - Detailed chapter expansions and planning documents

### Build and Deployment
- **`site/mkdocs.yml`** - MkDocs configuration for static site generation
- **`site/site/`** - Generated static website (excluded from git)
- **`.github/workflows/deploy-docs.yml`** - GitHub Actions for automated deployment

### Planning and Development
- **`ChapterCraftingGuide.md`** - Comprehensive authoring framework and methodology
- **`Chapter-05-Evolution-Framework.md`** - Specific chapter development example
- **`site/MASTER-EXECUTION-PLAN.md`** - Project execution strategy

## Architectural Patterns

### Content Architecture
The book follows a **7-part hierarchical structure**:
1. **Foundations** (Chapters 1-4) - Core impossibility results, time, consensus, replication
2. **Evolution** (Chapters 5-7) - Historical progression from mainframes to cloud-native
3. **Modern Systems** (Chapters 8-10) - Current architecture patterns and coordination
4. **Planet Scale** (Chapters 11-13) - Large-scale systems, economics, security
5. **Practice** (Chapters 14-16) - Building, operating, and debugging systems
6. **Advanced Topics** (Chapters 17-19) - CRDTs, end-to-end arguments, systems theory
7. **Future** (Chapters 20-21) - Emerging technologies and philosophical implications

### Documentation Framework
- **Three-Layer Mental Model**: Physics (eternal truths) → Strategies (design patterns) → Tactics (implementations)
- **Canonical Lenses**: STA (State, Time, Agreement) and DCEH (Data, Control, Evidence, Human) planes
- **Evidence Lifecycle**: Generate → Validate → Active → Expiring → Expired → Renewed/Revoked
- **Composition Algebra**: Typed guarantee vectors with explicit upgrade/downgrade semantics

## Core Components and Relationships

### Content Generation Pipeline
1. **Planning Phase**: TOC development and chapter blueprints
2. **Authoring Phase**: Using unified mental model framework
3. **Review Phase**: Multi-pass validation (invariant consistency, evidence completeness, composition soundness)
4. **Publication Phase**: MkDocs static site generation and GitHub Pages deployment

### Cross-Chapter Integration
- **Resonance Threads**: Consistent concepts that recur across chapters
- **Invariant Catalog**: Standardized taxonomy of system invariants
- **Evidence Types**: Consistent classification of proofs and certificates
- **Mode Matrix**: Standardized degradation semantics across all systems