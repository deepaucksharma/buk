#!/usr/bin/env python3
"""
Chapter Validation Script for Unified Mental Model Authoring Framework 3.0

This script performs automated validation checks on chapter markdown files
to ensure compliance with the framework standards.

Usage:
    python chapter_validator.py <chapter_file.md>
    python chapter_validator.py --verbose --html site/docs/chapter-*/index.md
    python chapter_validator.py --format json --output report.json chapter-02/index.md
"""

import re
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class ValidationResult:
    """Result of a single validation check"""
    check_name: str
    passed: bool
    score: int
    max_score: int
    details: str
    suggestions: List[str]
    line_numbers: List[int]


@dataclass
class ChapterValidation:
    """Overall validation result for a chapter"""
    chapter_path: str
    total_score: int
    max_score: int
    percentage: float
    grade: str
    status: str
    results: List[ValidationResult]

    def to_dict(self):
        return {
            'chapter_path': self.chapter_path,
            'total_score': self.total_score,
            'max_score': self.max_score,
            'percentage': self.percentage,
            'grade': self.grade,
            'status': self.status,
            'results': [asdict(r) for r in self.results]
        }


class ChapterValidator:
    """Main validator class"""

    # G-vector component validation
    G_VECTOR_PATTERN = r'G\s*=\s*⟨([^⟩]+)⟩'

    VALID_COMPONENTS = {
        'Scope': ['Object', 'Range', 'Transaction', 'Global'],
        'Order': ['None', 'Causal', 'Lx', 'SS'],
        'Visibility': ['Fractured', 'RA', 'SI', 'SER'],
        'Recency': ['EO', 'BS\\([^)]+\\)', 'Fresh\\([^)]+\\)'],
        'Idempotence': ['None', 'Idem\\([^)]+\\)'],
        'Auth': ['Unauth', 'Auth\\([^)]+\\)']
    }

    # Mode validation
    REQUIRED_MODES = ['Floor', 'Target', 'Degraded', 'Recovery']

    # Evidence properties
    EVIDENCE_PROPERTIES = ['Scope', 'Lifetime', 'Binding', 'Transitivity', 'Revocation']

    # Sacred diagrams
    SACRED_DIAGRAMS = [
        'Invariant Guardian',
        'Evidence Flow',
        'Composition Ladder',
        'Mode Compass',
        'Knowledge vs Data'
    ]

    # Invariant catalog
    FUNDAMENTAL_INVARIANTS = ['Conservation', 'Uniqueness', 'Authenticity', 'Integrity']
    DERIVED_INVARIANTS = ['Order', 'Exclusivity', 'Monotonicity']
    COMPOSITE_INVARIANTS = [
        'Freshness', 'Visibility', 'Coherent cut', 'Convergence',
        'Idempotence', 'Bounded staleness', 'Availability promise'
    ]

    # Composition operators
    COMPOSITION_OPERATORS = {
        '▷': 'sequential',
        '||': 'parallel',
        '↑': 'upgrade',
        '⤓': 'downgrade'
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def validate_chapter(self, filepath: Path) -> ChapterValidation:
        """Main validation entry point"""
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')

        results = []

        # Run all validation checks
        results.append(self.check_g_vectors(content, lines))
        results.append(self.check_mode_matrix(content, lines))
        results.append(self.check_evidence_properties(content, lines))
        results.append(self.check_sacred_diagrams(content, lines))
        results.append(self.check_transfer_tests(content, lines))
        results.append(self.check_context_capsules(content, lines))
        results.append(self.check_composition_operators(content, lines))
        results.append(self.check_invariant_mapping(content, lines))
        results.append(self.check_spiral_narrative(content, lines))
        results.append(self.check_cross_references(content, lines))

        # Calculate total score
        total_score = sum(r.score for r in results)
        max_score = sum(r.max_score for r in results)
        percentage = (total_score / max_score * 100) if max_score > 0 else 0

        # Determine grade and status
        grade, status = self.calculate_grade(percentage, results)

        return ChapterValidation(
            chapter_path=str(filepath),
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            grade=grade,
            status=status,
            results=results
        )

    def check_g_vectors(self, content: str, lines: List[str]) -> ValidationResult:
        """Validate G-vector syntax and components"""
        matches = list(re.finditer(self.G_VECTOR_PATTERN, content))
        suggestions = []
        line_numbers = []

        if not matches:
            return ValidationResult(
                check_name="G-Vector Syntax",
                passed=False,
                score=0,
                max_score=10,
                details="No G-vectors found",
                suggestions=["Add at least one G-vector showing guarantee composition"],
                line_numbers=[]
            )

        valid_count = 0
        for match in matches:
            vector_content = match.group(1)
            components = [c.strip() for c in vector_content.split(',')]

            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            line_numbers.append(line_num)

            # Should have 6 components
            if len(components) != 6:
                suggestions.append(
                    f"Line {line_num}: G-vector should have 6 components "
                    f"(Scope, Order, Visibility, Recency, Idempotence, Auth), found {len(components)}"
                )
                continue

            # Validate each component
            component_valid = True
            for i, (comp_name, valid_values) in enumerate(self.VALID_COMPONENTS.items()):
                if i < len(components):
                    comp_value = components[i]
                    if not any(re.match(vv, comp_value) for vv in valid_values):
                        suggestions.append(
                            f"Line {line_num}: Invalid {comp_name} value: '{comp_value}'"
                        )
                        component_valid = False

            if component_valid:
                valid_count += 1

        # Scoring: 10 points max, proportional to valid vectors
        score = min(10, (valid_count / max(len(matches), 1)) * 10)

        return ValidationResult(
            check_name="G-Vector Syntax",
            passed=valid_count > 0,
            score=int(score),
            max_score=10,
            details=f"Found {len(matches)} G-vectors, {valid_count} valid",
            suggestions=suggestions,
            line_numbers=line_numbers
        )

    def check_mode_matrix(self, content: str, lines: List[str]) -> ValidationResult:
        """Check for complete mode matrix (all 4 modes)"""
        found_modes = {}
        suggestions = []

        for mode in self.REQUIRED_MODES:
            pattern = re.compile(rf'\b{mode}\s+(Mode|mode)\b', re.IGNORECASE)
            matches = list(pattern.finditer(content))
            if matches:
                line_num = content[:matches[0].start()].count('\n') + 1
                found_modes[mode] = line_num

        missing_modes = set(self.REQUIRED_MODES) - set(found_modes.keys())

        if missing_modes:
            suggestions.append(
                f"Missing modes: {', '.join(missing_modes)}. "
                "Every chapter should define Floor, Target, Degraded, and Recovery modes."
            )

        # Check mode completeness (entry/exit triggers)
        for mode, line_num in found_modes.items():
            # Look for entry/exit triggers near the mode definition
            context_start = max(0, line_num - 5)
            context_end = min(len(lines), line_num + 20)
            context = '\n'.join(lines[context_start:context_end])

            if 'entry' not in context.lower() and 'trigger' not in context.lower():
                suggestions.append(
                    f"{mode} mode (line {line_num}): Missing entry/exit triggers"
                )

        # Scoring: 10 points max (2.5 per mode)
        score = len(found_modes) * 2.5

        return ValidationResult(
            check_name="Mode Matrix",
            passed=len(found_modes) == 4,
            score=int(score),
            max_score=10,
            details=f"Found {len(found_modes)}/4 modes: {', '.join(found_modes.keys())}",
            suggestions=suggestions,
            line_numbers=list(found_modes.values())
        )

    def check_evidence_properties(self, content: str, lines: List[str]) -> ValidationResult:
        """Check for evidence lifecycle properties"""
        found_properties = defaultdict(list)
        suggestions = []

        for prop in self.EVIDENCE_PROPERTIES:
            pattern = re.compile(rf'\b{prop}\b\s*:', re.IGNORECASE)
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                found_properties[prop].append(line_num)

        # Check if evidence sections have all properties
        evidence_sections = re.finditer(r'##.*Evidence', content, re.IGNORECASE)

        for section_match in evidence_sections:
            section_line = content[:section_match.start()].count('\n') + 1

            # Look at next 50 lines for properties
            section_end = content.find('\n##', section_match.end())
            if section_end == -1:
                section_end = len(content)

            section_content = content[section_match.start():section_end]

            missing_props = []
            for prop in self.EVIDENCE_PROPERTIES:
                if prop not in section_content:
                    missing_props.append(prop)

            if missing_props:
                suggestions.append(
                    f"Evidence section at line {section_line} missing properties: "
                    f"{', '.join(missing_props)}"
                )

        # Scoring: 10 points max
        total_props = len(self.EVIDENCE_PROPERTIES)
        found_props = len(found_properties)
        score = (found_props / total_props) * 10

        return ValidationResult(
            check_name="Evidence Properties",
            passed=found_props >= 4,  # At least 4/5 properties
            score=int(score),
            max_score=10,
            details=f"Found {found_props}/{total_props} evidence properties",
            suggestions=suggestions,
            line_numbers=[ln[0] for ln in found_properties.values() if ln]
        )

    def check_sacred_diagrams(self, content: str, lines: List[str]) -> ValidationResult:
        """Check for sacred diagrams"""
        found_diagrams = {}
        suggestions = []

        for diagram in self.SACRED_DIAGRAMS:
            pattern = re.compile(re.escape(diagram), re.IGNORECASE)
            matches = list(pattern.finditer(content))
            if matches:
                line_num = content[:matches[0].start()].count('\n') + 1
                found_diagrams[diagram] = line_num

        if len(found_diagrams) < 2:
            suggestions.append(
                f"Only {len(found_diagrams)} sacred diagrams found. "
                "Chapters should include at least 2 of the 5 sacred diagrams."
            )
            missing = set(self.SACRED_DIAGRAMS) - set(found_diagrams.keys())
            suggestions.append(f"Consider adding: {', '.join(list(missing)[:2])}")

        # Scoring: 5 points max (1 per diagram, max 5)
        score = min(5, len(found_diagrams))

        return ValidationResult(
            check_name="Sacred Diagrams",
            passed=len(found_diagrams) >= 2,
            score=score,
            max_score=5,
            details=f"Found {len(found_diagrams)}/5 sacred diagrams",
            suggestions=suggestions,
            line_numbers=list(found_diagrams.values())
        )

    def check_transfer_tests(self, content: str, lines: List[str]) -> ValidationResult:
        """Check for transfer tests (Near, Medium, Far)"""
        test_types = ['Near', 'Medium', 'Far']
        found_tests = {}
        suggestions = []

        for test_type in test_types:
            pattern = re.compile(rf'\b{test_type}\b.*Test', re.IGNORECASE)
            matches = list(pattern.finditer(content))
            if matches:
                line_num = content[:matches[0].start()].count('\n') + 1
                found_tests[test_type] = line_num

        missing_tests = set(test_types) - set(found_tests.keys())

        if missing_tests:
            suggestions.append(
                f"Missing transfer tests: {', '.join(missing_tests)}. "
                "Chapters should have 3 tests at increasing distance."
            )

        # Check if tests are substantive (>100 chars context)
        for test_type, line_num in found_tests.items():
            context_start = max(0, line_num - 1)
            context_end = min(len(lines), line_num + 10)
            test_content = '\n'.join(lines[context_start:context_end])

            if len(test_content) < 100:
                suggestions.append(
                    f"{test_type} test (line {line_num}) seems too brief. "
                    "Tests should include problem statement and expected insights."
                )

        # Scoring: 10 points max (3.33 per test)
        score = len(found_tests) * 3.33

        return ValidationResult(
            check_name="Transfer Tests",
            passed=len(found_tests) == 3,
            score=int(score),
            max_score=10,
            details=f"Found {len(found_tests)}/3 transfer tests",
            suggestions=suggestions,
            line_numbers=list(found_tests.values())
        )

    def check_context_capsules(self, content: str, lines: List[str]) -> ValidationResult:
        """Check for context capsules with required fields"""
        # Look for capsule-like structures
        capsule_pattern = re.compile(
            r'\{[^}]*?invariant:[^}]*?evidence:[^}]*?\}',
            re.IGNORECASE | re.DOTALL
        )

        capsules = list(capsule_pattern.finditer(content))
        required_fields = ['invariant', 'evidence', 'boundary', 'mode', 'fallback']
        suggestions = []
        complete_capsules = 0

        for capsule_match in capsules:
            capsule_text = capsule_match.group(0)
            line_num = content[:capsule_match.start()].count('\n') + 1

            missing_fields = []
            for field in required_fields:
                if field not in capsule_text.lower():
                    missing_fields.append(field)

            if not missing_fields:
                complete_capsules += 1
            else:
                suggestions.append(
                    f"Capsule at line {line_num} missing fields: {', '.join(missing_fields)}"
                )

        if not capsules:
            suggestions.append(
                "No context capsules found. Add capsules at chapter/service boundaries."
            )

        # Scoring: 10 points max
        if capsules:
            score = (complete_capsules / len(capsules)) * 10
        else:
            score = 0

        return ValidationResult(
            check_name="Context Capsules",
            passed=complete_capsules > 0,
            score=int(score),
            max_score=10,
            details=f"Found {len(capsules)} capsules, {complete_capsules} complete",
            suggestions=suggestions,
            line_numbers=[content[:m.start()].count('\n') + 1 for m in capsules]
        )

    def check_composition_operators(self, content: str, lines: List[str]) -> ValidationResult:
        """Check for composition operators"""
        found_operators = defaultdict(list)
        suggestions = []

        for op_symbol, op_name in self.COMPOSITION_OPERATORS.items():
            pattern = re.compile(re.escape(op_symbol))
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                found_operators[op_name].append(line_num)

        if not found_operators:
            suggestions.append(
                "No composition operators found (▷, ||, ↑, ⤓). "
                "Show how guarantees compose across boundaries."
            )

        # Check for explicit downgrades
        if 'downgrade' not in found_operators or not found_operators['downgrade']:
            suggestions.append(
                "No explicit downgrades (⤓) found. When guarantees weaken, mark with ⤓."
            )

        # Scoring: 10 points max
        score = min(10, len(found_operators) * 2.5)

        return ValidationResult(
            check_name="Composition Operators",
            passed=len(found_operators) >= 2,
            score=int(score),
            max_score=10,
            details=f"Found {len(found_operators)} operator types",
            suggestions=suggestions,
            line_numbers=[ln[0] for ln in found_operators.values() if ln]
        )

    def check_invariant_mapping(self, content: str, lines: List[str]) -> ValidationResult:
        """Check for invariant catalog mapping"""
        all_invariants = (
            self.FUNDAMENTAL_INVARIANTS +
            self.DERIVED_INVARIANTS +
            self.COMPOSITE_INVARIANTS
        )

        found_invariants = {}
        suggestions = []

        for invariant in all_invariants:
            pattern = re.compile(rf'\b{invariant}\b', re.IGNORECASE)
            matches = list(pattern.finditer(content))
            if matches:
                line_num = content[:matches[0].start()].count('\n') + 1
                found_invariants[invariant] = line_num

        if not found_invariants:
            suggestions.append(
                "No catalog invariants referenced. Map chapter to at least one "
                "primary invariant from the catalog."
            )

        # Look for "Primary invariant" or "Invariant:" declarations
        primary_pattern = re.compile(r'Primary\s+invariant:\s*(\w+)', re.IGNORECASE)
        primary_match = primary_pattern.search(content)

        if not primary_match:
            suggestions.append(
                "No explicit primary invariant declared. "
                "Add 'Primary invariant: <Name>' statement."
            )

        # Scoring: 15 points max
        score = min(15, len(found_invariants) * 3)

        return ValidationResult(
            check_name="Invariant Mapping",
            passed=len(found_invariants) >= 1,
            score=int(score),
            max_score=15,
            details=f"Found {len(found_invariants)} catalog invariants",
            suggestions=suggestions,
            line_numbers=list(found_invariants.values())
        )

    def check_spiral_narrative(self, content: str, lines: List[str]) -> ValidationResult:
        """Check for 3-pass spiral structure"""
        passes = {
            'Pass 1': r'(Part 1|Pass 1|INTUITION|Intuition)',
            'Pass 2': r'(Part 2|Pass 2|UNDERSTANDING|Understanding)',
            'Pass 3': r'(Part 3|Pass 3|MASTERY|Mastery)'
        }

        found_passes = {}
        suggestions = []

        for pass_name, pattern in passes.items():
            regex = re.compile(pattern, re.IGNORECASE)
            matches = list(regex.finditer(content))
            if matches:
                line_num = content[:matches[0].start()].count('\n') + 1
                found_passes[pass_name] = line_num

        missing_passes = set(passes.keys()) - set(found_passes.keys())

        if missing_passes:
            suggestions.append(
                f"Missing spiral passes: {', '.join(missing_passes)}. "
                "Chapters should have 3-pass structure: Intuition → Understanding → Mastery."
            )

        # Check if passes are substantive (>300 words each)
        for pass_name, line_num in found_passes.items():
            next_pass_line = len(lines)
            for other_pass, other_line in found_passes.items():
                if other_line > line_num:
                    next_pass_line = min(next_pass_line, other_line)

            pass_content = '\n'.join(lines[line_num:next_pass_line])
            word_count = len(pass_content.split())

            if word_count < 300:
                suggestions.append(
                    f"{pass_name} (line {line_num}) is too short ({word_count} words). "
                    "Each pass should be substantive (>300 words)."
                )

        # Scoring: 10 points max (3.33 per pass)
        score = len(found_passes) * 3.33

        return ValidationResult(
            check_name="Spiral Narrative",
            passed=len(found_passes) == 3,
            score=int(score),
            max_score=10,
            details=f"Found {len(found_passes)}/3 spiral passes",
            suggestions=suggestions,
            line_numbers=list(found_passes.values())
        )

    def check_cross_references(self, content: str, lines: List[str]) -> ValidationResult:
        """Check for cross-references to other chapters"""
        backward_pattern = re.compile(
            r'(Chapter [1-9]|from Chapter|as we saw in|in Chapter [1-9])',
            re.IGNORECASE
        )
        forward_pattern = re.compile(
            r"(we'll explore|will explore|in Chapter [1-9][0-9]?|future chapter)",
            re.IGNORECASE
        )

        backward_refs = list(backward_pattern.finditer(content))
        forward_refs = list(forward_pattern.finditer(content))

        suggestions = []

        if len(backward_refs) < 2:
            suggestions.append(
                f"Only {len(backward_refs)} backward references found. "
                "Include at least 2 references to prior chapters to reinforce concepts."
            )

        if len(forward_refs) < 1:
            suggestions.append(
                "No forward references found. "
                "Set up at least one future concept to create continuity."
            )

        # Scoring: 10 points max (5 for backward, 5 for forward)
        backward_score = min(5, len(backward_refs) * 2.5)
        forward_score = min(5, len(forward_refs) * 5)
        score = backward_score + forward_score

        return ValidationResult(
            check_name="Cross-References",
            passed=len(backward_refs) >= 2 and len(forward_refs) >= 1,
            score=int(score),
            max_score=10,
            details=f"{len(backward_refs)} backward, {len(forward_refs)} forward",
            suggestions=suggestions,
            line_numbers=(
                [content[:m.start()].count('\n') + 1 for m in backward_refs[:3]] +
                [content[:m.start()].count('\n') + 1 for m in forward_refs[:2]]
            )
        )

    def calculate_grade(self, percentage: float, results: List[ValidationResult]) -> Tuple[str, str]:
        """Calculate letter grade and status"""
        # Check critical dimensions
        critical_checks = {
            'Invariant Mapping': 7,
            'Evidence Properties': 7,
            'G-Vector Syntax': 5
        }

        critical_failure = False
        for check_name, min_score in critical_checks.items():
            result = next((r for r in results if r.check_name == check_name), None)
            if result and result.score < min_score:
                critical_failure = True
                break

        if percentage >= 90:
            grade = 'A'
            status = 'PASS - Ready for publication'
        elif percentage >= 80:
            grade = 'B'
            status = 'PASS - Minor revisions suggested'
        elif percentage >= 70 and not critical_failure:
            grade = 'C'
            status = 'CONDITIONAL - Address major items before publish'
        elif percentage >= 60:
            grade = 'D'
            status = 'FAIL - Significant revision required'
        else:
            grade = 'F'
            status = 'FAIL - Not ready for review'

        return grade, status


def format_console_output(validation: ChapterValidation, verbose: bool = False) -> str:
    """Format validation results for console"""
    output = []
    output.append(f"\n{'='*70}")
    output.append(f"Validating: {validation.chapter_path}")
    output.append(f"{'='*70}\n")

    for result in validation.results:
        symbol = '✓' if result.passed else '✗'
        output.append(
            f"{symbol} {result.check_name:.<30} {result.score}/{result.max_score}"
        )

        if verbose or not result.passed:
            output.append(f"  {result.details}")
            for suggestion in result.suggestions[:3]:  # Max 3 suggestions
                output.append(f"  → {suggestion}")
            if len(result.suggestions) > 3:
                output.append(f"  → ... and {len(result.suggestions) - 3} more")
            output.append("")

    output.append(f"\n{'-'*70}")
    output.append(f"Total Score: {validation.total_score}/{validation.max_score} "
                  f"({validation.percentage:.1f}%)")
    output.append(f"Grade: {validation.grade}")
    output.append(f"Status: {validation.status}")
    output.append(f"{'-'*70}\n")

    return '\n'.join(output)


def format_html_output(validation: ChapterValidation) -> str:
    """Format validation results as HTML"""
    html = ['''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Chapter Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .summary { background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .pass { color: green; }
        .fail { color: red; }
        .warn { color: orange; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .suggestions { margin-left: 20px; color: #666; }
        .grade-A { background-color: #d4edda; }
        .grade-B { background-color: #d1ecf1; }
        .grade-C { background-color: #fff3cd; }
        .grade-D { background-color: #f8d7da; }
        .grade-F { background-color: #f5c6cb; }
    </style>
</head>
<body>
''']

    html.append(f'<h1>Chapter Validation Report</h1>')
    html.append(f'<p><strong>Chapter:</strong> {validation.chapter_path}</p>')

    grade_class = f'grade-{validation.grade}'
    html.append(f'<div class="summary {grade_class}">')
    html.append(f'<h2>Summary</h2>')
    html.append(f'<p><strong>Score:</strong> {validation.total_score}/{validation.max_score} '
                f'({validation.percentage:.1f}%)</p>')
    html.append(f'<p><strong>Grade:</strong> {validation.grade}</p>')
    html.append(f'<p><strong>Status:</strong> {validation.status}</p>')
    html.append('</div>')

    html.append('<h2>Detailed Results</h2>')
    html.append('<table>')
    html.append('<tr><th>Check</th><th>Score</th><th>Status</th><th>Details</th></tr>')

    for result in validation.results:
        status_class = 'pass' if result.passed else 'fail'
        status_text = '✓ Pass' if result.passed else '✗ Fail'

        html.append(f'<tr>')
        html.append(f'<td>{result.check_name}</td>')
        html.append(f'<td>{result.score}/{result.max_score}</td>')
        html.append(f'<td class="{status_class}">{status_text}</td>')
        html.append(f'<td>{result.details}')

        if result.suggestions:
            html.append('<ul class="suggestions">')
            for suggestion in result.suggestions:
                html.append(f'<li>{suggestion}</li>')
            html.append('</ul>')

        html.append('</td>')
        html.append('</tr>')

    html.append('</table>')
    html.append('</body>')
    html.append('</html>')

    return '\n'.join(html)


def main():
    parser = argparse.ArgumentParser(
        description='Validate chapter files against framework standards'
    )
    parser.add_argument(
        'files',
        nargs='+',
        type=Path,
        help='Chapter markdown files to validate'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--format',
        choices=['console', 'json', 'html'],
        default='console',
        help='Output format'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file (for json/html formats)'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary only (for multiple files)'
    )

    args = parser.parse_args()

    validator = ChapterValidator(verbose=args.verbose)
    validations = []

    for filepath in args.files:
        if not filepath.exists():
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            continue

        validation = validator.validate_chapter(filepath)
        validations.append(validation)

        if args.format == 'console' and not args.summary:
            print(format_console_output(validation, args.verbose))

    # Summary for multiple files
    if args.summary and len(validations) > 1:
        print(f"\n{'='*70}")
        print(f"Summary ({len(validations)} chapters)")
        print(f"{'='*70}")
        for v in validations:
            status_symbol = '✓' if 'PASS' in v.status else '✗'
            print(f"{status_symbol} {Path(v.chapter_path).name:.<40} "
                  f"{v.percentage:.1f}% ({v.grade})")

        avg_score = sum(v.percentage for v in validations) / len(validations)
        print(f"\nAverage Score: {avg_score:.1f}%")

    # Output to file
    if args.output:
        if args.format == 'json':
            output_data = [v.to_dict() for v in validations]
            args.output.write_text(json.dumps(output_data, indent=2))
            print(f"\nJSON report written to: {args.output}")

        elif args.format == 'html':
            # Combine multiple chapters into one report
            html_parts = []
            for v in validations:
                html_parts.append(format_html_output(v))

            args.output.write_text('\n<hr>\n'.join(html_parts))
            print(f"\nHTML report written to: {args.output}")

    # Exit code based on results
    if validations:
        min_percentage = min(v.percentage for v in validations)
        sys.exit(0 if min_percentage >= 70 else 1)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
