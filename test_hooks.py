#!/usr/bin/env python3
"""
Test hooks for GitHub Actions workflows.
This script validates the GitHub Actions setup and can be used as a pre-commit hook.
"""

import os
import sys
import yaml
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Any


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
            with open(workflow_file, 'r', encoding='utf-8') as f:
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
            required_keys = {'name': 'name', 'on': [True, 'on'], 'jobs': 'jobs'}
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
            if 'jobs' in workflow_data:
                for job_name, job_data in workflow_data['jobs'].items():
                    if not isinstance(job_data, dict):
                        result["errors"].append(f"Job '{job_name}' must be a dictionary")
                        continue
                    
                    if 'runs-on' not in job_data:
                        result["errors"].append(f"Job '{job_name}' missing 'runs-on'")
                    
                    if 'steps' not in job_data:
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
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    return result
                workflow_data = yaml.safe_load(content)
            
            if workflow_data is None or not isinstance(workflow_data, dict):
                return result
            
            # Handle YAML parsing quirk where 'on' becomes True
            triggers_key = True if True in workflow_data else 'on' if 'on' in workflow_data else None
            if triggers_key is not None:
                triggers = workflow_data[triggers_key]
                if isinstance(triggers, str):
                    result["triggers"] = [triggers]
                elif isinstance(triggers, list):
                    result["triggers"] = triggers
                elif isinstance(triggers, dict):
                    result["triggers"] = list(triggers.keys())
                
                # Check for common trigger patterns
                if 'push' in result["triggers"] and 'pull_request' in result["triggers"]:
                    # Good practice - covers both scenarios
                    pass
                elif 'push' not in result["triggers"] and 'pull_request' not in result["triggers"]:
                    result["warnings"].append("No push or pull_request triggers found")
                
        except Exception as e:
            result["warnings"].append(f"Error checking triggers: {str(e)}")
            
        return result
    
    def validate_action_references(self, workflow_file: Path) -> Dict[str, Any]:
        """Validate that referenced actions exist and use proper versions."""
        result = {"file": str(workflow_file), "actions": [], "warnings": []}
        
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    return result
                workflow_data = yaml.safe_load(content)
            
            if workflow_data is None or not isinstance(workflow_data, dict):
                return result
            
            # Extract all action references
            if 'jobs' in workflow_data:
                for job_name, job_data in workflow_data['jobs'].items():
                    if 'steps' in job_data:
                        for step in job_data['steps']:
                            if isinstance(step, dict) and 'uses' in step:
                                action_ref = step['uses']
                                result["actions"].append(action_ref)
                                
                                # Check for version pinning
                                if '@' not in action_ref:
                                    result["warnings"].append(f"Action '{action_ref}' not version pinned")
                                elif action_ref.endswith('@main') or action_ref.endswith('@master'):
                                    result["warnings"].append(f"Action '{action_ref}' uses unstable branch")
                                
                                # Check for local actions
                                if action_ref.startswith('./'):
                                    local_action_path = self.repo_root / action_ref[2:]
                                    if not local_action_path.exists():
                                        result["warnings"].append(f"Local action not found: {action_ref}")
                                
        except Exception as e:
            result["warnings"].append(f"Error validating actions: {str(e)}")
            
        return result
    
    def check_secrets_usage(self, workflow_file: Path) -> Dict[str, Any]:
        """Check for proper secrets usage."""
        result = {"file": str(workflow_file), "secrets": [], "warnings": []}
        
        try:
            with open(workflow_file, 'r') as f:
                content = f.read()
            
            # Look for secrets references
            import re
            secret_pattern = r'\$\{\{\s*secrets\.([A-Z_]+)\s*\}\}'
            secrets = re.findall(secret_pattern, content)
            result["secrets"] = list(set(secrets))
            
            # Check for hardcoded tokens (basic check)
            if re.search(r'(ghp_|github_pat_)[a-zA-Z0-9_]+', content):
                result["warnings"].append("Potential hardcoded GitHub token found")
            
        except Exception as e:
            result["warnings"].append(f"Error checking secrets: {str(e)}")
            
        return result
    
    def run_workflow_validation(self) -> Dict[str, Any]:
        """Run comprehensive workflow validation."""
        results = {
            "summary": {"total_workflows": 0, "valid_workflows": 0, "warnings": 0, "errors": 0},
            "workflows": []
        }
        
        if not self.workflows_dir.exists():
            results["summary"]["errors"] = 1
            results["workflows"].append({
                "error": f"Workflows directory not found: {self.workflows_dir}"
            })
            return results
        
        workflow_files = list(self.workflows_dir.glob("*.yml")) + list(self.workflows_dir.glob("*.yaml"))
        results["summary"]["total_workflows"] = len(workflow_files)
        
        for workflow_file in workflow_files:
            workflow_result = {
                "file": str(workflow_file.relative_to(self.repo_root)),
                "syntax": self.validate_workflow_syntax(workflow_file),
                "triggers": self.check_workflow_triggers(workflow_file),
                "actions": self.validate_action_references(workflow_file),
                "secrets": self.check_secrets_usage(workflow_file)
            }
            
            # Count errors and warnings
            total_errors = len(workflow_result["syntax"]["errors"])
            total_warnings = (
                len(workflow_result["triggers"]["warnings"]) +
                len(workflow_result["actions"]["warnings"]) +
                len(workflow_result["secrets"]["warnings"])
            )
            
            workflow_result["summary"] = {
                "errors": total_errors,
                "warnings": total_warnings,
                "valid": total_errors == 0
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
                cwd=self.repo_root
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
            result["checks"].append("ℹ Branch protection settings should be verified in GitHub UI")
            
        except Exception as e:
            result["warnings"].append(f"Error checking repository settings: {str(e)}")
        
        return result


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
    
    parser = argparse.ArgumentParser(description="Validate GitHub Actions workflows")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--exit-on-error", action="store_true", help="Exit with code 1 if errors found")
    
    args = parser.parse_args()
    
    validator = GitHubActionsValidator(args.repo_root)
    results = validator.run_workflow_validation()
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)
        
        # Also show repository settings
        print("=" * 60)
        print("Repository Settings")
        print("=" * 60)
        repo_settings = validator.check_repository_settings()
        for check in repo_settings["checks"]:
            print(check)
        for warning in repo_settings["warnings"]:
            print(f"⚠️  {warning}")
    
    if args.exit_on_error and results["summary"]["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
