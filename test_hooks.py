#!/usr/bin/env python3
"""
Test hooks for GitHub Actions workflows.
This script validates the GitHub Actions setup and can be used as a pre-commit hook.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any

import yaml


class GitHubActionsValidator:
    """Validates GitHub Actions workflows and setup."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.workflows_dir = self.repo_root / ".github" / "workflows"
        self.actions_dir = self.repo_root / ".github" / "actions"

    def validate_workflow_syntax(self, workflow_file: Path) -> Dict[str, Any]:
        """Validate YAML syntax of a workflow file."""
        result = {"file": str(workflow_file), "valid": False, "errors": []}

        try:
            with open(workflow_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    result["errors"].append("File is empty")
                    return result
                workflow_data = yaml.safe_load(content)

            # Check if workflow_data is None or not a dict
            if workflow_data is None:
                result["errors"].append("YAML file is empty or invalid")
                return result

            if not isinstance(workflow_data, dict):
                result["errors"].append("YAML root must be a dictionary")
                return result

            # Basic structure validation
            # Note: YAML parser converts 'on' to True, so we check for both
            required_keys = {"name": "name", "on": [True, "on"], "jobs": "jobs"}
            for key_name, key_variants in required_keys.items():
                if isinstance(key_variants, list):
                    # Check for multiple possible keys (like 'on' -> True)
                    if not any(variant in workflow_data for variant in key_variants):
                        result["errors"].append(f"Missing required key: {key_name}")
                else:
                    # Check for single key
                    if key_variants not in workflow_data:
                        result["errors"].append(f"Missing required key: {key_name}")

            # Validate jobs structure
            if "jobs" in workflow_data:
                for job_name, job_data in workflow_data["jobs"].items():
                    if not isinstance(job_data, dict):
                        result["errors"].append(
                            f"Job '{job_name}' must be a dictionary"
                        )
                        continue

                    if "runs-on" not in job_data:
                        result["errors"].append(f"Job '{job_name}' missing 'runs-on'")

                    if "steps" not in job_data:
                        result["errors"].append(f"Job '{job_name}' missing 'steps'")

            result["valid"] = len(result["errors"]) == 0

        except yaml.YAMLError as e:
            result["errors"].append(f"YAML syntax error: {str(e)}")
        except Exception as e:
            result["errors"].append(f"Unexpected error: {str(e)}")

        return result

    def check_workflow_triggers(self, workflow_file: Path) -> Dict[str, Any]:
        """Check if workflow triggers are properly configured."""
        result = {"file": str(workflow_file), "triggers": [], "warnings": []}

        try:
            with open(workflow_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    return result
                workflow_data = yaml.safe_load(content)

            if workflow_data is None or not isinstance(workflow_data, dict):
                return result

            # Handle YAML parsing quirk where 'on' becomes True
            triggers_key = (
                True
                if True in workflow_data
                else "on" if "on" in workflow_data else None
            )
            if triggers_key is not None:
                triggers = workflow_data[triggers_key]
                if isinstance(triggers, str):
                    result["triggers"] = [triggers]
                elif isinstance(triggers, list):
                    result["triggers"] = triggers
                elif isinstance(triggers, dict):
                    result["triggers"] = list(triggers.keys())

                # Check for common trigger patterns
                if (
                    "push" in result["triggers"]
                    and "pull_request" in result["triggers"]
                ):
                    # Good practice - covers both scenarios
                    pass
                elif (
                    "push" not in result["triggers"]
                    and "pull_request" not in result["triggers"]
                ):
                    result["warnings"].append("No push or pull_request triggers found")

        except Exception as e:
            result["warnings"].append(f"Error checking triggers: {str(e)}")

        return result

    def validate_action_references(self, workflow_file: Path) -> Dict[str, Any]:
        """Validate that referenced actions exist and use proper versions."""
        result = {"file": str(workflow_file), "actions": [], "warnings": []}

        try:
            with open(workflow_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    return result
                workflow_data = yaml.safe_load(content)

            if workflow_data is None or not isinstance(workflow_data, dict):
                return result

            # Extract all action references
            if "jobs" in workflow_data:
                for job_name, job_data in workflow_data["jobs"].items():
                    if "steps" in job_data:
                        for step in job_data["steps"]:
                            if isinstance(step, dict) and "uses" in step:
                                action_ref = step["uses"]
                                result["actions"].append(action_ref)

                                # Check for version pinning
                                if "@" not in action_ref:
                                    result["warnings"].append(
                                        f"Action '{action_ref}' not version pinned"
                                    )
                                elif action_ref.endswith(
                                    "@main"
                                ) or action_ref.endswith("@master"):
                                    result["warnings"].append(
                                        f"Action '{action_ref}' uses unstable branch"
                                    )

                                # Check for local actions
                                if action_ref.startswith("./"):
                                    local_action_path = self.repo_root / action_ref[2:]
                                    if not local_action_path.exists():
                                        result["warnings"].append(
                                            f"Local action not found: {action_ref}"
                                        )

        except Exception as e:
            result["warnings"].append(f"Error validating actions: {str(e)}")

        return result

    def check_secrets_usage(self, workflow_file: Path) -> Dict[str, Any]:
        """Check for proper secrets usage."""
        result = {"file": str(workflow_file), "secrets": [], "warnings": []}

        try:
            with open(workflow_file, "r") as f:
                content = f.read()

            # Look for secrets references
            import re

            secret_pattern = r"\$\{\{\s*secrets\.([A-Z_]+)\s*\}\}"
            secrets = re.findall(secret_pattern, content)
            result["secrets"] = list(set(secrets))

            # Check for hardcoded tokens (basic check)
            if re.search(r"(ghp_|github_pat_)[a-zA-Z0-9_]+", content):
                result["warnings"].append("Potential hardcoded GitHub token found")

        except Exception as e:
            result["warnings"].append(f"Error checking secrets: {str(e)}")

        return result

    def run_workflow_validation(self) -> Dict[str, Any]:
        """Run comprehensive workflow validation."""
        results = {
            "summary": {
                "total_workflows": 0,
                "valid_workflows": 0,
                "warnings": 0,
                "errors": 0,
            },
            "workflows": [],
        }

        if not self.workflows_dir.exists():
            results["summary"]["errors"] = 1
            results["workflows"].append(
                {"error": f"Workflows directory not found: {self.workflows_dir}"}
            )
            return results

        workflow_files = list(self.workflows_dir.glob("*.yml")) + list(
            self.workflows_dir.glob("*.yaml")
        )
        results["summary"]["total_workflows"] = len(workflow_files)

        for workflow_file in workflow_files:
            workflow_result = {
                "file": str(workflow_file.relative_to(self.repo_root)),
                "syntax": self.validate_workflow_syntax(workflow_file),
                "triggers": self.check_workflow_triggers(workflow_file),
                "actions": self.validate_action_references(workflow_file),
                "secrets": self.check_secrets_usage(workflow_file),
            }

            # Count errors and warnings
            total_errors = len(workflow_result["syntax"]["errors"])
            total_warnings = (
                len(workflow_result["triggers"]["warnings"])
                + len(workflow_result["actions"]["warnings"])
                + len(workflow_result["secrets"]["warnings"])
            )

            workflow_result["summary"] = {
                "errors": total_errors,
                "warnings": total_warnings,
                "valid": total_errors == 0,
            }

            if total_errors == 0:
                results["summary"]["valid_workflows"] += 1

            results["summary"]["errors"] += total_errors
            results["summary"]["warnings"] += total_warnings
            results["workflows"].append(workflow_result)

        return results

    def check_repository_settings(self) -> Dict[str, Any]:
        """Check repository settings that affect GitHub Actions."""
        result = {"checks": [], "warnings": []}

        try:
            # Check if we're in a git repository
            git_result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )

            if git_result.returncode != 0:
                result["warnings"].append("Not in a git repository")
                return result

            # Check for .gitignore
            gitignore_path = self.repo_root / ".gitignore"
            if gitignore_path.exists():
                result["checks"].append("✓ .gitignore exists")
            else:
                result["warnings"].append(".gitignore not found")

            # Check for branch protection (requires API access, so just note it)
            result["checks"].append(
                "ℹ Branch protection settings should be verified in GitHub UI"
            )

        except Exception as e:
            result["warnings"].append(f"Error checking repository settings: {str(e)}")

        return result

    def run_python_linting(self) -> Dict[str, Any]:
        """Run Python linting and type checking."""
        results = {
            "summary": {
                "total_checks": 0,
                "passed_checks": 0,
                "errors": 0,
                "warnings": 0,
            },
            "checks": [],
        }

        # Find Python files
        python_files = list(self.repo_root.rglob("*.py"))
        if not python_files:
            results["checks"].append(
                {
                    "tool": "python",
                    "status": "skipped",
                    "message": "No Python files found",
                }
            )
            return results

        # Check if tools are available
        tools_to_check = [
            ("black", "Black code formatter"),
            ("isort", "Import sorter"),
            ("flake8", "Linting"),
            ("mypy", "Type checking"),
            ("pylint", "Advanced linting"),
        ]

        for tool_name, description in tools_to_check:
            results["summary"]["total_checks"] += 1

            if not shutil.which(tool_name):
                results["checks"].append(
                    {
                        "tool": tool_name,
                        "status": "skipped",
                        "message": f"{description} - {tool_name} not installed",
                    }
                )
                continue

            try:
                if tool_name == "black":
                    cmd = ["black", "--check", "--diff", "."]
                elif tool_name == "isort":
                    cmd = ["isort", "--check-only", "--diff", "."]
                elif tool_name == "flake8":
                    cmd = [
                        "flake8",
                        ".",
                        "--max-line-length=88",
                        "--extend-ignore=E203,W503,E501",
                    ]
                elif tool_name == "mypy":
                    cmd = ["mypy", ".", "--ignore-missing-imports"]
                elif tool_name == "pylint":
                    cmd = ["pylint", "--disable=C0114,C0115,C0116"] + [
                        str(f) for f in python_files[:5]
                    ]  # Limit files for performance

                result = subprocess.run(
                    cmd, capture_output=True, text=True, cwd=self.repo_root, timeout=60
                )

                if result.returncode == 0:
                    results["summary"]["passed_checks"] += 1
                    results["checks"].append(
                        {
                            "tool": tool_name,
                            "status": "passed",
                            "message": f"{description} - All checks passed",
                        }
                    )
                else:
                    results["summary"]["errors"] += 1
                    output = result.stdout + result.stderr
                    results["checks"].append(
                        {
                            "tool": tool_name,
                            "status": "failed",
                            "message": f"{description} - Issues found",
                            "output": (
                                output[:1000] + "..." if len(output) > 1000 else output
                            ),
                        }
                    )

            except subprocess.TimeoutExpired:
                results["summary"]["errors"] += 1
                results["checks"].append(
                    {
                        "tool": tool_name,
                        "status": "timeout",
                        "message": f"{description} - Timed out after 60 seconds",
                    }
                )
            except Exception as e:
                results["summary"]["errors"] += 1
                results["checks"].append(
                    {
                        "tool": tool_name,
                        "status": "error",
                        "message": f"{description} - Error: {str(e)}",
                    }
                )

        return results

    def run_rust_linting(self) -> Dict[str, Any]:
        """Run Rust linting and formatting checks."""
        results = {
            "summary": {
                "total_checks": 0,
                "passed_checks": 0,
                "errors": 0,
                "warnings": 0,
            },
            "checks": [],
        }

        # Check if this is a Rust project
        cargo_toml = self.repo_root / "Cargo.toml"
        if not cargo_toml.exists():
            results["checks"].append(
                {
                    "tool": "rust",
                    "status": "skipped",
                    "message": "No Cargo.toml found - not a Rust project",
                }
            )
            return results

        # Check if cargo is available
        if not shutil.which("cargo"):
            results["checks"].append(
                {"tool": "cargo", "status": "skipped", "message": "Cargo not installed"}
            )
            return results

        # Rust tools to check
        rust_checks = [
            ("cargo check", "Compilation check", ["cargo", "check"]),
            ("cargo fmt", "Code formatting", ["cargo", "fmt", "--check"]),
            (
                "cargo clippy",
                "Linting",
                ["cargo", "clippy", "--all-targets", "--", "-D", "warnings"],
            ),
            (
                "cargo test",
                "Unit tests",
                ["cargo", "test", "--no-run"],
            ),  # Just check if tests compile
        ]

        for check_name, description, cmd in rust_checks:
            results["summary"]["total_checks"] += 1

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.repo_root,
                    timeout=120,
                    env={
                        **os.environ,
                        "SKIP_WASM_BUILD": "1",
                    },  # Skip WASM build for faster checks
                )

                if result.returncode == 0:
                    results["summary"]["passed_checks"] += 1
                    results["checks"].append(
                        {
                            "tool": check_name,
                            "status": "passed",
                            "message": f"{description} - All checks passed",
                        }
                    )
                else:
                    results["summary"]["errors"] += 1
                    output = result.stdout + result.stderr
                    results["checks"].append(
                        {
                            "tool": check_name,
                            "status": "failed",
                            "message": f"{description} - Issues found",
                            "output": (
                                output[:1000] + "..." if len(output) > 1000 else output
                            ),
                        }
                    )

            except subprocess.TimeoutExpired:
                results["summary"]["errors"] += 1
                results["checks"].append(
                    {
                        "tool": check_name,
                        "status": "timeout",
                        "message": f"{description} - Timed out after 120 seconds",
                    }
                )
            except Exception as e:
                results["summary"]["errors"] += 1
                results["checks"].append(
                    {
                        "tool": check_name,
                        "status": "error",
                        "message": f"{description} - Error: {str(e)}",
                    }
                )

        return results

    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation checks including workflows, linting, and type checking."""
        results = {
            "workflows": self.run_workflow_validation(),
            "python_linting": self.run_python_linting(),
            "rust_linting": self.run_rust_linting(),
            "repository": self.check_repository_settings(),
        }

        # Calculate overall summary
        total_errors = (
            results["workflows"]["summary"]["errors"]
            + results["python_linting"]["summary"]["errors"]
            + results["rust_linting"]["summary"]["errors"]
        )

        total_warnings = results["workflows"]["summary"]["warnings"]

        results["overall_summary"] = {
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "status": "passed" if total_errors == 0 else "failed",
        }

        return results


def print_comprehensive_results(results: Dict[str, Any]) -> None:
    """Pretty print comprehensive validation results."""
    print("=" * 80)
    print("COMPREHENSIVE PROJECT VALIDATION RESULTS")
    print("=" * 80)

    overall = results["overall_summary"]
    status_icon = "✅" if overall["status"] == "passed" else "❌"
    print(f"{status_icon} Overall Status: {overall['status'].upper()}")
    print(f"Total Errors: {overall['total_errors']}")
    print(f"Total Warnings: {overall['total_warnings']}")
    print()

    # GitHub Actions Results
    print("📋 GITHUB ACTIONS WORKFLOWS")
    print("-" * 40)
    workflows = results["workflows"]
    print(
        f"Valid workflows: {workflows['summary']['valid_workflows']}/{workflows['summary']['total_workflows']}"
    )
    print(
        f"Errors: {workflows['summary']['errors']}, Warnings: {workflows['summary']['warnings']}"
    )

    for workflow in workflows["workflows"]:
        if "error" in workflow:
            print(f"❌ {workflow['error']}")
            continue

        status = "✅" if workflow["summary"]["valid"] else "❌"
        print(f"{status} {workflow['file']}")
        if workflow["summary"]["errors"] > 0:
            for error in workflow["syntax"]["errors"]:
                print(f"   ❌ {error}")
    print()

    # Python Linting Results
    print("🐍 PYTHON LINTING & TYPE CHECKING")
    print("-" * 40)
    python = results["python_linting"]
    print(
        f"Passed: {python['summary']['passed_checks']}/{python['summary']['total_checks']}"
    )
    print(f"Errors: {python['summary']['errors']}")

    for check in python["checks"]:
        if check["status"] == "passed":
            print(f"✅ {check['tool']}: {check['message']}")
        elif check["status"] == "skipped":
            print(f"⏭️  {check['tool']}: {check['message']}")
        else:
            print(f"❌ {check['tool']}: {check['message']}")
            if "output" in check and check["output"].strip():
                print(f"   Output: {check['output'][:200]}...")
    print()

    # Rust Linting Results
    print("🦀 RUST LINTING & COMPILATION")
    print("-" * 40)
    rust = results["rust_linting"]
    print(
        f"Passed: {rust['summary']['passed_checks']}/{rust['summary']['total_checks']}"
    )
    print(f"Errors: {rust['summary']['errors']}")

    for check in rust["checks"]:
        if check["status"] == "passed":
            print(f"✅ {check['tool']}: {check['message']}")
        elif check["status"] == "skipped":
            print(f"⏭️  {check['tool']}: {check['message']}")
        else:
            print(f"❌ {check['tool']}: {check['message']}")
            if "output" in check and check["output"].strip():
                print(f"   Output: {check['output'][:200]}...")
    print()

    # Repository Settings
    print("⚙️  REPOSITORY SETTINGS")
    print("-" * 40)
    repo = results["repository"]
    for check in repo["checks"]:
        print(check)
    for warning in repo["warnings"]:
        print(f"⚠️  {warning}")
    print()


def print_results(results: Dict[str, Any]) -> None:
    """Pretty print validation results."""
    print("=" * 60)
    print("GitHub Actions Validation Results")
    print("=" * 60)

    summary = results["summary"]
    print(f"Total workflows: {summary['total_workflows']}")
    print(f"Valid workflows: {summary['valid_workflows']}")
    print(f"Total errors: {summary['errors']}")
    print(f"Total warnings: {summary['warnings']}")
    print()

    for workflow in results["workflows"]:
        if "error" in workflow:
            print(f"❌ {workflow['error']}")
            continue

        file_name = workflow["file"]
        summary = workflow["summary"]

        status = "✅" if summary["valid"] else "❌"
        print(f"{status} {file_name}")

        if summary["errors"] > 0:
            print(f"   Errors: {summary['errors']}")
            for error in workflow["syntax"]["errors"]:
                print(f"     - {error}")

        if summary["warnings"] > 0:
            print(f"   Warnings: {summary['warnings']}")
            for section in ["triggers", "actions", "secrets"]:
                for warning in workflow[section]["warnings"]:
                    print(f"     - {warning}")

        print(f"   Triggers: {', '.join(workflow['triggers']['triggers'])}")
        print(f"   Actions used: {len(workflow['actions']['actions'])}")
        print(f"   Secrets referenced: {len(workflow['secrets']['secrets'])}")
        print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate GitHub Actions workflows and run linting checks"
    )
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--exit-on-error", action="store_true", help="Exit with code 1 if errors found"
    )
    parser.add_argument(
        "--workflows-only",
        action="store_true",
        help="Only validate GitHub Actions workflows",
    )
    parser.add_argument(
        "--python-only",
        action="store_true",
        help="Only run Python linting and type checking",
    )
    parser.add_argument(
        "--rust-only",
        action="store_true",
        help="Only run Rust linting and compilation checks",
    )
    parser.add_argument(
        "--comprehensive", action="store_true", help="Run all checks (default behavior)"
    )

    args = parser.parse_args()

    validator = GitHubActionsValidator(args.repo_root)

    # Determine what to run
    if args.workflows_only:
        results = validator.run_workflow_validation()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print_results(results)
        exit_code = results["summary"]["errors"]
    elif args.python_only:
        results = validator.run_python_linting()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("🐍 PYTHON LINTING & TYPE CHECKING")
            print("-" * 40)
            for check in results["checks"]:
                status_icon = (
                    "✅"
                    if check["status"] == "passed"
                    else "❌" if check["status"] == "failed" else "⏭️"
                )
                print(f"{status_icon} {check['tool']}: {check['message']}")
        exit_code = results["summary"]["errors"]
    elif args.rust_only:
        results = validator.run_rust_linting()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("🦀 RUST LINTING & COMPILATION")
            print("-" * 40)
            for check in results["checks"]:
                status_icon = (
                    "✅"
                    if check["status"] == "passed"
                    else "❌" if check["status"] == "failed" else "⏭️"
                )
                print(f"{status_icon} {check['tool']}: {check['message']}")
        exit_code = results["summary"]["errors"]
    else:
        # Run comprehensive validation (default)
        results = validator.run_comprehensive_validation()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print_comprehensive_results(results)
        exit_code = results["overall_summary"]["total_errors"]

    if args.exit_on_error and exit_code > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
