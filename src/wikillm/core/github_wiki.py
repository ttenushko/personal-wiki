from __future__ import annotations

import base64

from github import Github, GithubException

from wikillm.config.settings import settings
from wikillm.core.logger import logger


class GitHubWiki:
    """Manages wiki files in a GitHub repository."""

    def __init__(self) -> None:
        self.client = Github(settings.github_token)
        self.repo = self.client.get_repo(settings.github_repo)
        self.branch = settings.github_branch

    def get_file(self, path: str) -> str | None:
        """Get file content from repo."""
        try:
            content = self.repo.get_contents(path, ref=self.branch)
            if content.content:
                return base64.b64decode(content.content).decode("utf-8")
        except GithubException:
            return None
        return None

    def create_or_update_file(
        self,
        path: str,
        content: str,
        message: str,
    ) -> bool:
        """Create or update a file in the repo."""
        try:
            # Check if file exists
            existing = None
            try:
                existing = self.repo.get_contents(path, ref=self.branch)
            except GithubException:
                pass

            if existing:
                self.repo.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=existing.sha,
                    branch=self.branch,
                )
            else:
                self.repo.create_file(
                    path=path,
                    message=message,
                    content=content,
                    branch=self.branch,
                )
            return True
        except GithubException as e:
            logger.warning(f"GitHub create/update error: {e}")
            return False

    def delete_file(self, path: str, message: str) -> bool:
        """Delete a file from the repo."""
        try:
            content = self.repo.get_contents(path, ref=self.branch)
            self.repo.delete_file(
                path=path,
                message=message,
                sha=content.sha,
                branch=self.branch,
            )
            return True
        except GithubException as e:
            logger.warning(f"GitHub delete error: {e}")
            return False

    def list_files(self, path: str = "") -> list[str]:
        """List all files in a directory."""
        try:
            contents = self.repo.get_contents(path, ref=self.branch)
            if isinstance(contents, list):
                return [c.path for c in contents]
            return [contents.path]
        except GithubException:
            return []
