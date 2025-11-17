"""
GitHub package management for Agent Warden.

Handles GitHub package metadata and version information.
"""

from datetime import datetime, timezone
from typing import Dict, Optional


class GitHubPackage:
    """Represents a GitHub package with version information."""

    def __init__(self, owner: str, repo: str, ref: str = "main",
                 installed_ref: Optional[str] = None, installed_at: Optional[str] = None):
        self.owner = owner
        self.repo = repo
        self.ref = ref  # Target ref (branch/tag)
        self.installed_ref = installed_ref  # Currently installed ref
        self.installed_at = installed_at or datetime.now(timezone.utc).isoformat()
        self.name = f"{owner}/{repo}"

    @property
    def directory_name(self) -> str:
        """Get the directory name for this package."""
        return f"{self.owner}-{self.repo}"

    @property
    def github_url(self) -> str:
        """Get the GitHub URL for this package."""
        return f"https://github.com/{self.owner}/{self.repo}.git"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'owner': self.owner,
            'repo': self.repo,
            'ref': self.ref,
            'installed_ref': self.installed_ref,
            'installed_at': self.installed_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GitHubPackage':
        """Create GitHubPackage from dictionary."""
        return cls(
            owner=data['owner'],
            repo=data['repo'],
            ref=data.get('ref', 'main'),
            installed_ref=data.get('installed_ref'),
            installed_at=data.get('installed_at')
        )

    @classmethod
    def from_spec(cls, spec: str) -> 'GitHubPackage':
        """Create GitHubPackage from spec string like 'owner/repo' or 'owner/repo@ref'."""
        if '@' in spec:
            repo_part, ref = spec.split('@', 1)
        else:
            repo_part, ref = spec, 'main'

        if '/' not in repo_part:
            raise ValueError(f"Invalid package spec: {spec}. Expected format: owner/repo[@ref]")

        owner, repo = repo_part.split('/', 1)
        return cls(owner, repo, ref)

