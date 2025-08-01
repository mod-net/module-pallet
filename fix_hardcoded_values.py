#!/usr/bin/env python3
"""
Automated Hard-coded Value Replacement Script

This script systematically replaces hard-coded values throughout the codebase
with configuration-based alternatives.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class HardcodedValueFixer:
    """Fixes hard-coded values in Python files."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.replacements = {
            # URLs and hosts
            r'"http://localhost:5001"': 'config.ipfs.api_url',
            r'"http://localhost:8080"': 'config.ipfs.gateway_url',
            r'"http://localhost:8000"': 'config.commune_ipfs.base_url',
            r'"http://localhost:8004"': 'config.test.test_module_registry_url',
            r'"http://127\.0\.0\.1:9933"': 'config.substrate.http_url',
            r'"ws://127\.0\.0\.1:9944"': 'config.substrate.ws_url',  # Note: config uses secure ws:// for local dev
            r'"http://127\.0\.0\.1:9944"': 'config.substrate.http_url',
            
            # Port numbers in environment variable defaults
            r"os\.getenv\(['\"]PORT['\"], ['\"]8000['\"]\)": "os.getenv('PORT', str(config.commune_ipfs.port))",
            r"os\.getenv\(['\"]IPFS_API_PORT['\"], ['\"]5001['\"]\)": "os.getenv('IPFS_API_PORT', str(config.ipfs.api_port))",
            r"os\.getenv\(['\"]IPFS_GATEWAY_PORT['\"], ['\"]8080['\"]\)": "os.getenv('IPFS_GATEWAY_PORT', str(config.ipfs.gateway_port))",
            
            # Keypair seeds (only in non-test files)
            r'"//Alice"': 'config.substrate.keypair_seed',
            r"'//Alice'": 'config.substrate.keypair_seed',
        }
        
        # Files to exclude from automatic replacement
        self.exclude_patterns = [
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'tests/.*\.py$',
            r'audit_codebase\.py$',
            r'fix_hardcoded_values\.py$',
            r'config\.py$',
            r'substrate_config\.py$',
        ]
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from replacement."""
        file_str = str(file_path)
        return any(re.search(pattern, file_str) for pattern in self.exclude_patterns)
    
    def needs_config_import(self, content: str) -> bool:
        """Check if file needs config import added."""
        return 'from config import get_config' not in content and 'import config' not in content
    
    def add_config_import(self, content: str) -> str:
        """Add config import to file content."""
        lines = content.split('\n')
        
        # Find the best place to insert the import
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
            elif line.strip() == '' and import_index > 0:
                continue
            elif import_index > 0:
                break
        
        # Insert the import
        lines.insert(import_index, 'from config import get_config')
        return '\n'.join(lines)
    
    def fix_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Fix hard-coded values in a single file."""
        if self.should_exclude_file(file_path):
            return False, []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except (UnicodeDecodeError, PermissionError):
            return False, []
        
        content = original_content
        changes = []
        needs_config = False
        
        # Apply replacements
        for pattern, replacement in self.replacements.items():
            if re.search(pattern, content):
                # Skip keypair seed replacement in test files
                if '//Alice' in replacement and 'test' in str(file_path).lower():
                    continue
                
                old_content = content
                content = re.sub(pattern, replacement, content)
                if content != old_content:
                    changes.append(f"Replaced {pattern} with {replacement}")
                    needs_config = True
        
        # Add config import if needed and changes were made
        if needs_config and self.needs_config_import(content):
            content = self.add_config_import(content)
            changes.append("Added config import")
        
        # Add config variable if replacements were made
        if needs_config and 'config = get_config()' not in content:
            # Find a good place to add config = get_config()
            lines = content.split('\n')
            
            # Look for function definitions or class methods
            for i, line in enumerate(lines):
                if (line.strip().startswith('def ') or 
                    line.strip().startswith('class ') or
                    line.strip().startswith('async def ')):
                    
                    # Check if this function/method uses config
                    function_content = '\n'.join(lines[i:i+50])  # Look ahead 50 lines
                    if 'config.' in function_content:
                        # Find the first non-docstring line in the function
                        for j in range(i + 1, min(len(lines), i + 10)):
                            if (lines[j].strip() and 
                                not lines[j].strip().startswith('"""') and
                                not lines[j].strip().startswith("'''") and
                                'config = get_config()' not in lines[j]):
                                
                                # Add config line with proper indentation
                                indent = len(lines[j]) - len(lines[j].lstrip())
                                config_line = ' ' * indent + 'config = get_config()'
                                lines.insert(j, config_line)
                                changes.append("Added config = get_config() call")
                                break
                        break
            
            content = '\n'.join(lines)
        
        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        
        return False, []
    
    def fix_all_files(self) -> Dict[str, List[str]]:
        """Fix hard-coded values in all Python files."""
        results = {}
        
        for file_path in self.root_dir.rglob('*.py'):
            if file_path.is_file():
                changed, changes = self.fix_file(file_path)
                if changed:
                    relative_path = str(file_path.relative_to(self.root_dir))
                    results[relative_path] = changes
        
        return results


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix hard-coded values in codebase')
    parser.add_argument('directory', nargs='?', default='.', 
                       help='Directory to process (default: current directory)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without making changes')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"❌ Error: Directory '{args.directory}' does not exist")
        return 1
    
    print(f"🔧 Fixing hard-coded values in: {args.directory}")
    
    fixer = HardcodedValueFixer(args.directory)
    
    if args.dry_run:
        print("🔍 DRY RUN - No changes will be made")
        # TODO: Implement dry run functionality
        return 0
    
    results = fixer.fix_all_files()
    
    if results:
        print(f"\n✅ Fixed {len(results)} files:")
        for file_path, changes in results.items():
            print(f"\n📝 {file_path}:")
            for change in changes:
                print(f"   • {change}")
    else:
        print("\n✅ No files needed fixing")
    
    return 0


if __name__ == '__main__':
    exit(main())
