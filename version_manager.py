#!/usr/bin/env python3
"""
Independent Semantic Versioning CLI System
==========================================

A reusable versioning system that provides:
- Semantic versioning (major.minor.patch)
- Changelog management
- Enhanced help menus
- Interactive and command-line modes
- Git integration for tagging

Usage:
    python version_manager.py [command] [options]
    python version_manager.py bump major "Breaking changes"
    python version_manager.py bump minor "New feature"
    python version_manager.py bump patch "Bug fix"
    python version_manager.py current
    python version_manager.py help
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    WHITE = "\033[1;37m"
    BOLD = "\033[1m"
    NC = "\033[0m"  # No Color


class VersionManager:
    """Manages semantic versioning for a project."""

    def __init__(self, project_root: str | None = None):
        """Initialize the version manager.
        Args:
            project_root: Root directory of the project. Defaults to current directory.
        """
        self.project_root = Path(project_root or os.getcwd())
        self.version_file = self.project_root / "VERSION"
        self.changelog_file = self.project_root / "CHANGELOG.md"
        self.pyproject_file = self.project_root / "pyproject.toml"

    def _print_colored(self, message: str, color: str = Colors.NC):
        """Print a colored message to the terminal."""
        print(f"{color}{message}{Colors.NC}")

    def _print_header(self, message: str):
        """Print a header message."""
        self._print_colored(f"\n=== {message} ===", Colors.BLUE)

    def _print_success(self, message: str):
        """Print a success message."""
        self._print_colored(f"✓ {message}", Colors.GREEN)

    def _print_error(self, message: str):
        """Print an error message."""
        self._print_colored(f"✗ {message}", Colors.RED)

    def _print_warning(self, message: str):
        """Print a warning message."""
        self._print_colored(f"⚠ {message}", Colors.YELLOW)

    def _print_info(self, message: str):
        """Print an info message."""
        self._print_colored(f"ℹ {message}", Colors.CYAN)

    def get_current_version(self) -> tuple[int, int, int]:
        """Get the current version from VERSION file.
        Returns:
            Tuple of (major, minor, patch) version numbers.
        """
        if not self.version_file.exists():
            return (0, 1, 0)  # Default initial version

        try:
            version_str = self.version_file.read_text().strip()
            match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str)
            if match:
                return tuple(map(int, match.groups()))  # type: ignore[return-value]
            else:
                self._print_warning(
                    f"Invalid version format in {self.version_file}: {version_str}"
                )
                return (0, 1, 0)
        except Exception as e:
            self._print_error(f"Error reading version file: {e}")
            return (0, 1, 0)

    def set_version(self, major: int, minor: int, patch: int):
        """Set the version in VERSION file and pyproject.toml if it exists.
        Args:
            major: Major version number
            minor: Minor version number
            patch: Patch version number
        """
        version_str = f"{major}.{minor}.{patch}"

        # Write to VERSION file
        self.version_file.write_text(version_str + "\n")
        self._print_success(f"Updated VERSION file to {version_str}")

        # Update pyproject.toml if it exists
        if self.pyproject_file.exists():
            try:
                content = self.pyproject_file.read_text()
                # Update version in pyproject.toml
                updated_content = re.sub(
                    r'version\s*=\s*"[^"]*"', f'version = "{version_str}"', content
                )
                self.pyproject_file.write_text(updated_content)
                self._print_success(f"Updated pyproject.toml to {version_str}")
            except Exception as e:
                self._print_warning(f"Could not update pyproject.toml: {e}")

    def bump_version(
        self, bump_type: str, changelog_entry: str | None = None
    ) -> tuple[int, int, int]:
        """Bump the version according to semantic versioning rules.
        Args:
            bump_type: Type of bump ('major', 'minor', 'patch')
            changelog_entry: Optional changelog entry for this version
        Returns:
            New version tuple (major, minor, patch)
        """
        major, minor, patch = self.get_current_version()

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(
                f"Invalid bump type: {bump_type}. Must be 'major', 'minor', or 'patch'"
            )

        self.set_version(major, minor, patch)

        if changelog_entry:
            self.update_changelog(major, minor, patch, changelog_entry)

        return (major, minor, patch)

    def update_changelog(self, major: int, minor: int, patch: int, entry: str):
        """Update the CHANGELOG.md file with a new entry.
        Args:
            major: Major version number
            minor: Minor version number
            patch: Patch version number
            entry: Changelog entry description
        """
        version_str = f"{major}.{minor}.{patch}"
        date_str = datetime.now().strftime("%Y-%m-%d")

        new_entry = f"""
## [{version_str}] - {date_str}

### Changed
- {entry}
"""

        if not self.changelog_file.exists():
            # Create new changelog
            changelog_content = f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
{new_entry}
"""
        else:
            # Insert new entry after "## [Unreleased]" section
            content = self.changelog_file.read_text()

            # Find the position to insert the new entry
            if "## [Unreleased]" in content:
                # Insert after the Unreleased section
                parts = content.split("## [Unreleased]", 1)
                if len(parts) == 2:
                    # Find the next ## section or end of file
                    after_unreleased = parts[1]
                    next_section_match = re.search(r"\n## \[", after_unreleased)
                    if next_section_match:
                        # Insert before the next section
                        insert_pos = next_section_match.start()
                        changelog_content = (
                            parts[0]
                            + "## [Unreleased]"
                            + after_unreleased[:insert_pos]
                            + new_entry
                            + after_unreleased[insert_pos:]
                        )
                    else:
                        # Insert at the end
                        changelog_content = (
                            parts[0] + "## [Unreleased]" + after_unreleased + new_entry
                        )
                else:
                    changelog_content = content + new_entry
            else:
                # No unreleased section, add at the beginning
                lines = content.split("\n")
                # Find a good place to insert (after the header)
                insert_line = 0
                for i, line in enumerate(lines):
                    if line.startswith("##") and "[" in line:
                        insert_line = i
                        break

                if insert_line > 0:
                    lines.insert(insert_line, new_entry.strip())
                    changelog_content = "\n".join(lines)
                else:
                    changelog_content = content + new_entry

        self.changelog_file.write_text(changelog_content)
        self._print_success(f"Updated CHANGELOG.md with entry for v{version_str}")

    def create_git_tag(
        self, major: int, minor: int, patch: int, message: str | None = None
    ):
        """Create a git tag for the current version.
        Args:
            major: Major version number
            minor: Minor version number
            patch: Patch version number
            message: Optional tag message
        """
        version_str = f"{major}.{minor}.{patch}"
        tag_name = f"v{version_str}"

        try:
            # Check if we're in a git repository
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                check=True,
                capture_output=True,
                cwd=self.project_root,
            )

            # Create the tag
            cmd = ["git", "tag", "-a", tag_name]
            if message:
                cmd.extend(["-m", message])
            else:
                cmd.extend(["-m", f"Release version {version_str}"])

            subprocess.run(cmd, check=True, cwd=self.project_root)
            self._print_success(f"Created git tag: {tag_name}")

        except subprocess.CalledProcessError:
            self._print_warning("Not in a git repository or git command failed")
        except FileNotFoundError:
            self._print_warning("Git not found in PATH")

    def show_current_version(self):
        """Display the current version information."""
        major, minor, patch = self.get_current_version()
        version_str = f"{major}.{minor}.{patch}"

        self._print_header("Current Version Information")
        self._print_colored(f"Version: {version_str}", Colors.WHITE)
        self._print_info(f"Version file: {self.version_file}")

        if self.changelog_file.exists():
            self._print_info(f"Changelog: {self.changelog_file}")
        else:
            self._print_warning("No CHANGELOG.md found")

    def show_help(self):
        """Display enhanced help menu with all available options."""
        self._print_header("Version Manager - Enhanced Help")

        print(
            f"""
{Colors.WHITE}USAGE:{Colors.NC}
    python version_manager.py [COMMAND] [OPTIONS]

{Colors.WHITE}COMMANDS:{Colors.NC}
    {Colors.GREEN}current{Colors.NC}                     Show current version information
    {Colors.GREEN}bump <type> [message]{Colors.NC}       Bump version (major/minor/patch)
    {Colors.GREEN}set <version>{Colors.NC}               Set specific version (e.g., 1.2.3)
    {Colors.GREEN}tag [message]{Colors.NC}               Create git tag for current version
    {Colors.GREEN}help{Colors.NC}                        Show this help menu

{Colors.WHITE}BUMP TYPES:{Colors.NC}
    {Colors.YELLOW}major{Colors.NC}    - Breaking changes (1.0.0 → 2.0.0)
    {Colors.YELLOW}minor{Colors.NC}    - New features, backward compatible (1.0.0 → 1.1.0)
    {Colors.YELLOW}patch{Colors.NC}    - Bug fixes, backward compatible (1.0.0 → 1.0.1)

{Colors.WHITE}EXAMPLES:{Colors.NC}
    {Colors.CYAN}python version_manager.py current{Colors.NC}
    {Colors.CYAN}python version_manager.py bump major "Breaking API changes"{Colors.NC}
    {Colors.CYAN}python version_manager.py bump minor "Added new feature"{Colors.NC}
    {Colors.CYAN}python version_manager.py bump patch "Fixed critical bug"{Colors.NC}
    {Colors.CYAN}python version_manager.py set 1.0.0{Colors.NC}
    {Colors.CYAN}python version_manager.py tag "Release with new features"{Colors.NC}

{Colors.WHITE}FILES MANAGED:{Colors.NC}
    {Colors.PURPLE}VERSION{Colors.NC}        - Main version file
    {Colors.PURPLE}CHANGELOG.md{Colors.NC}   - Changelog with version history
    {Colors.PURPLE}pyproject.toml{Colors.NC} - Python project version (if exists)

{Colors.WHITE}INTERACTIVE MODE:{Colors.NC}
    Run without arguments to enter interactive mode with guided prompts.
        """
        )

    def interactive_mode(self):
        """Run the version manager in interactive mode."""
        self._print_header("Version Manager - Interactive Mode")
        self.show_current_version()

        print(f"\n{Colors.WHITE}Available actions:{Colors.NC}")
        print(f"  {Colors.GREEN}1{Colors.NC}) Bump major version")
        print(f"  {Colors.GREEN}2{Colors.NC}) Bump minor version")
        print(f"  {Colors.GREEN}3{Colors.NC}) Bump patch version")
        print(f"  {Colors.GREEN}4{Colors.NC}) Set specific version")
        print(f"  {Colors.GREEN}5{Colors.NC}) Create git tag")
        print(f"  {Colors.GREEN}6{Colors.NC}) Show current version")
        print(f"  {Colors.GREEN}0{Colors.NC}) Exit")

        while True:
            try:
                choice = input(
                    f"\n{Colors.CYAN}Enter your choice (0-6): {Colors.NC}"
                ).strip()

                if choice == "0":
                    self._print_info("Goodbye!")
                    break
                elif choice == "1":
                    self._handle_interactive_bump("major")
                elif choice == "2":
                    self._handle_interactive_bump("minor")
                elif choice == "3":
                    self._handle_interactive_bump("patch")
                elif choice == "4":
                    self._handle_interactive_set()
                elif choice == "5":
                    self._handle_interactive_tag()
                elif choice == "6":
                    self.show_current_version()
                else:
                    self._print_error(
                        "Invalid choice. Please enter a number between 0-6."
                    )
                    self.show_help()

            except KeyboardInterrupt:
                self._print_info("\nExiting...")
                break
            except Exception as e:
                self._print_error(f"An error occurred: {e}")

    def _handle_interactive_bump(self, bump_type: str):
        """Handle interactive version bump."""
        message = input(
            f"Enter changelog message for {bump_type} bump (optional): "
        ).strip()
        try:
            new_version = self.bump_version(bump_type, message if message else None)
            self._print_success(
                f"Bumped {bump_type} version to {'.'.join(map(str, new_version))}"
            )
        except Exception as e:
            self._print_error(f"Failed to bump version: {e}")

    def _handle_interactive_set(self):
        """Handle interactive version setting."""
        version_input = input("Enter version (e.g., 1.2.3): ").strip()
        try:
            match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_input)
            if match:
                major, minor, patch = map(int, match.groups())
                self.set_version(major, minor, patch)
                self._print_success(f"Set version to {version_input}")
            else:
                self._print_error(
                    "Invalid version format. Use major.minor.patch (e.g., 1.2.3)"
                )
        except Exception as e:
            self._print_error(f"Failed to set version: {e}")

    def _handle_interactive_tag(self):
        """Handle interactive git tag creation."""
        message = input("Enter tag message (optional): ").strip()
        try:
            major, minor, patch = self.get_current_version()
            self.create_git_tag(major, minor, patch, message if message else None)
        except Exception as e:
            self._print_error(f"Failed to create git tag: {e}")


def main():
    """Main entry point for the version manager CLI."""
    parser = argparse.ArgumentParser(
        description="Independent Semantic Versioning CLI System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python version_manager.py current
  python version_manager.py bump major "Breaking changes"
  python version_manager.py bump minor "New feature"
  python version_manager.py bump patch "Bug fix"
  python version_manager.py set 1.0.0
  python version_manager.py tag "Release message"
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["current", "bump", "set", "tag", "help"],
        help="Command to execute",
    )
    parser.add_argument(
        "type_or_version",
        nargs="?",
        help="Bump type (major/minor/patch) or version number",
    )
    parser.add_argument("message", nargs="?", help="Changelog entry or tag message")
    parser.add_argument(
        "--project-root", help="Project root directory (default: current directory)"
    )

    args = parser.parse_args()

    # Initialize version manager
    vm = VersionManager(args.project_root)

    try:
        if not args.command:
            # No command provided, enter interactive mode
            vm.interactive_mode()
        elif args.command == "current":
            vm.show_current_version()
        elif args.command == "bump":
            if not args.type_or_version:
                vm._print_error("Bump type required (major/minor/patch)")
                vm.show_help()
                sys.exit(1)

            if args.type_or_version not in ["major", "minor", "patch"]:
                vm._print_error(f"Invalid bump type: {args.type_or_version}")
                vm.show_help()
                sys.exit(1)

            new_version = vm.bump_version(args.type_or_version, args.message)
            vm._print_success(
                f"Bumped {args.type_or_version} version to {'.'.join(map(str, new_version))}"
            )

        elif args.command == "set":
            if not args.type_or_version:
                vm._print_error("Version number required (e.g., 1.2.3)")
                vm.show_help()
                sys.exit(1)

            match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", args.type_or_version)
            if not match:
                vm._print_error(
                    "Invalid version format. Use major.minor.patch (e.g., 1.2.3)"
                )
                sys.exit(1)

            major, minor, patch = map(int, match.groups())
            vm.set_version(major, minor, patch)

        elif args.command == "tag":
            major, minor, patch = vm.get_current_version()
            vm.create_git_tag(major, minor, patch, args.type_or_version)

        elif args.command == "help":
            vm.show_help()

    except KeyboardInterrupt:
        vm._print_info("\nExiting...")
        sys.exit(0)
    except Exception as e:
        vm._print_error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
