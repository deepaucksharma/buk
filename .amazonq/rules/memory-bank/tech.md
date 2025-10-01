# Technology Stack

## Programming Languages and Formats
- **Markdown** - Primary content format for all documentation
- **YAML** - Configuration files (MkDocs, GitHub Actions)
- **HTML/CSS/JavaScript** - Generated static site assets
- **Python** - MkDocs static site generator (implied dependency)

## Build System and Dependencies

### MkDocs Configuration
- **Theme**: Material Design theme with dark/light mode support
- **Extensions**: 
  - Python Markdown extensions (admonition, attr_list, footnotes, toc)
  - PyMdown extensions (arithmatex, highlight, superfences, tabbed, tasklist)
  - Mermaid diagram support for technical illustrations
  - MathJax integration for mathematical notation

### Site Generation
- **Static Site Generator**: MkDocs
- **Hosting**: GitHub Pages
- **Domain**: `https://deepaucksharma.github.io/buk/`
- **Repository**: `https://github.com/deepaucksharma/buk`

## Development Commands

### Local Development
```bash
# Install MkDocs and dependencies
pip install mkdocs mkdocs-material

# Serve locally with live reload
cd site && mkdocs serve

# Build static site
cd site && mkdocs build
```

### Content Management
```bash
# Add all changes
git add .

# Commit changes
git commit -m "Update content"

# Deploy to GitHub Pages
git push
```

### Deployment Pipeline
- **Automated Deployment**: GitHub Actions workflow (`.github/workflows/deploy-docs.yml`)
- **Trigger**: Push to main branch
- **Process**: Automatic MkDocs build and GitHub Pages deployment
- **Generated Assets**: Stored in `site/site/` directory (excluded from version control)

## Development Environment
- **Version Control**: Git with GitHub remote
- **IDE Integration**: Amazon Q plugin support for assisted development
- **File Organization**: Hierarchical structure with clear separation of source content and generated assets
- **Documentation Standards**: Unified Mental Model Framework 3.0 for consistent authoring