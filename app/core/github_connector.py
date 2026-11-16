"""
AI-Local-Hub - GitHub Connector
===============================
Handles GitHub authentication and repository operations.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import keyring
from github import Github, GithubException, Auth
from github.Repository import Repository
from github.PaginatedList import PaginatedList

from app.utils.config import Config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GitHubRepoInfo:
    """Information about a GitHub repository."""
    name: str
    full_name: str
    url: str
    private: bool
    description: str
    stars: int
    forks: int
    size: int  # in KB
    default_branch: str


class GitHubConnector:
    """Handles GitHub API operations with token authentication."""
    
    _token: Optional[str] = None
    _github_client: Optional[Github] = None
    
    @classmethod
    def get_token(cls) -> Optional[str]:
        """Get the stored GitHub token."""
        if cls._token:
            return cls._token
        
        # Try to get from keyring
        try:
            token = keyring.get_password(
                Config.GITHUB_TOKEN_SERVICE,
                Config.GITHUB_TOKEN_KEY
            )
            if token:
                cls._token = token
                return token
        except Exception as e:
            logger.warning(f"Failed to get token from keyring: {e}")
        
        # Try to get from environment variable
        token = os.getenv("GITHUB_TOKEN")
        if token:
            cls._token = token
            return token
        
        return None
    
    @classmethod
    def set_token(cls, token: str) -> bool:
        """Store a GitHub token securely."""
        try:
            # Save to keyring
            keyring.set_password(
                Config.GITHUB_TOKEN_SERVICE,
                Config.GITHUB_TOKEN_KEY,
                token
            )
            cls._token = token
            cls._github_client = None  # Reset client
            logger.info("GitHub token stored securely")
            return True
        except Exception as e:
            logger.error(f"Failed to store token: {e}")
            return False
    
    @classmethod
    def remove_token(cls) -> bool:
        """Remove the stored GitHub token."""
        try:
            keyring.delete_password(
                Config.GITHUB_TOKEN_SERVICE,
                Config.GITHUB_TOKEN_KEY
            )
            cls._token = None
            cls._github_client = None
            logger.info("GitHub token removed")
            return True
        except Exception as e:
            logger.error(f"Failed to remove token: {e}")
            return False
    
    @classmethod
    def get_client(cls) -> Optional[Github]:
        """Get a GitHub client instance."""
        if cls._github_client:
            return cls._github_client
        
        token = cls.get_token()
        if not token:
            logger.warning("No GitHub token available")
            return None
        
        try:
            # Use token authentication
            auth = Auth.Token(token)
            cls._github_client = Github(auth=auth)
            return cls._github_client
        except Exception as e:
            logger.error(f"Failed to create GitHub client: {e}")
            return None
    
    @classmethod
    def validate_token(cls) -> bool:
        """Validate if the current token is valid."""
        client = cls.get_client()
        if not client:
            return False
        
        try:
            # Try to get the authenticated user
            user = client.get_user()
            logger.info(f"Token is valid. Authenticated as: {user.login}")
            return True
        except GithubException as e:
            logger.error(f"Invalid token: {e}")
            return False
    
    @classmethod
    def get_user_repos(cls, username: str = None) -> List[GitHubRepoInfo]:
        """Get repositories for a user."""
        client = cls.get_client()
        if not client:
            return []
        
        try:
            if username:
                user = client.get_user(username)
            else:
                user = client.get_user()
            
            repos = []
            for repo in user.get_repos():
                repos.append(GitHubRepoInfo(
                    name=repo.name,
                    full_name=repo.full_name,
                    url=repo.html_url,
                    private=repo.private,
                    description=repo.description or "",
                    stars=repo.stargazers_count,
                    forks=repo.forks_count,
                    size=repo.size,
                    default_branch=repo.default_branch
                ))
            return repos
        except GithubException as e:
            logger.error(f"Failed to get user repos: {e}")
            return []
    
    @classmethod
    def get_org_repos(cls, org_name: str) -> List[GitHubRepoInfo]:
        """Get repositories for an organization."""
        client = cls.get_client()
        if not client:
            return []
        
        try:
            org = client.get_organization(org_name)
            repos = []
            for repo in org.get_repos():
                repos.append(GitHubRepoInfo(
                    name=repo.name,
                    full_name=repo.full_name,
                    url=repo.html_url,
                    private=repo.private,
                    description=repo.description or "",
                    stars=repo.stargazers_count,
                    forks=repo.forks_count,
                    size=repo.size,
                    default_branch=repo.default_branch
                ))
            return repos
        except GithubException as e:
            logger.error(f"Failed to get org repos: {e}")
            return []
    
    @classmethod
    def search_repos(cls, query: str, limit: int = 10) -> List[GitHubRepoInfo]:
        """Search for repositories on GitHub."""
        client = cls.get_client()
        if not client:
            return []
        
        try:
            repos = client.search_repositories(query=query)
            results = []
            for repo in repos[:limit]:
                results.append(GitHubRepoInfo(
                    name=repo.name,
                    full_name=repo.full_name,
                    url=repo.html_url,
                    private=repo.private,
                    description=repo.description or "",
                    stars=repo.stargazers_count,
                    forks=repo.forks_count,
                    size=repo.size,
                    default_branch=repo.default_branch
                ))
            return results
        except GithubException as e:
            logger.error(f"Failed to search repos: {e}")
            return []
    
    @classmethod
    def get_repo_info(cls, repo_name: str) -> Optional[GitHubRepoInfo]:
        """Get information about a specific repository."""
        client = cls.get_client()
        if not client:
            return None
        
        try:
            repo = client.get_repo(repo_name)
            return GitHubRepoInfo(
                name=repo.name,
                full_name=repo.full_name,
                url=repo.html_url,
                private=repo.private,
                description=repo.description or "",
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                size=repo.size,
                default_branch=repo.default_branch
            )
        except GithubException as e:
            logger.error(f"Failed to get repo info: {e}")
            return None
    
    @classmethod
    def get_repo_contents(cls, repo_name: str, path: str = "") -> List[Dict[str, Any]]:
        """Get contents of a repository."""
        client = cls.get_client()
        if not client:
            return []
        
        try:
            repo = client.get_repo(repo_name)
            contents = repo.get_contents(path)
            
            result = []
            while contents:
                file = contents.pop(0)
                if file.type == "dir":
                    result.append({
                        "name": file.name,
                        "path": file.path,
                        "type": "dir",
                        "size": 0,
                        "url": file.html_url
                    })
                    # Recursively get contents
                    contents.extend(repo.get_contents(file.path))
                else:
                    result.append({
                        "name": file.name,
                        "path": file.path,
                        "type": "file",
                        "size": file.size,
                        "url": file.download_url or file.html_url
                    })
            return result
        except GithubException as e:
            logger.error(f"Failed to get repo contents: {e}")
            return []
    
    @classmethod
    def download_file(cls, repo_name: str, file_path: str, save_path: Path) -> bool:
        """Download a file from a repository."""
        client = cls.get_client()
        if not client:
            return False
        
        try:
            repo = client.get_repo(repo_name)
            content = repo.get_contents(file_path)
            
            if content.type != "file":
                logger.error(f"{file_path} is not a file")
                return False
            
            # Download the file
            response = requests.get(content.download_url, headers={
                "Authorization": f"token {cls.get_token()}"
            })
            
            if response.status_code == 200:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Downloaded {file_path} to {save_path}")
                return True
            else:
                logger.error(f"Failed to download file: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return False
    
    @classmethod
    def get_user_info(cls) -> Optional[Dict[str, Any]]:
        """Get information about the authenticated user."""
        client = cls.get_client()
        if not client:
            return None
        
        try:
            user = client.get_user()
            return {
                "login": user.login,
                "name": user.name,
                "email": user.email,
                "bio": user.bio,
                "public_repos": user.public_repos,
                "followers": user.followers,
                "following": user.following,
                "avatar_url": user.avatar_url
            }
        except GithubException as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    @classmethod
    def list_starred_repos(cls) -> List[GitHubRepoInfo]:
        """List repositories starred by the authenticated user."""
        client = cls.get_client()
        if not client:
            return []
        
        try:
            user = client.get_user()
            starred = user.get_starred()
            
            repos = []
            for repo in starred:
                repos.append(GitHubRepoInfo(
                    name=repo.name,
                    full_name=repo.full_name,
                    url=repo.html_url,
                    private=repo.private,
                    description=repo.description or "",
                    stars=repo.stargazers_count,
                    forks=repo.forks_count,
                    size=repo.size,
                    default_branch=repo.default_branch
                ))
            return repos
        except GithubException as e:
            logger.error(f"Failed to list starred repos: {e}")
            return []
    
    @classmethod
    def create_repo(cls, name: str, description: str = "", private: bool = False) -> bool:
        """Create a new repository."""
        client = cls.get_client()
        if not client:
            return False
        
        try:
            user = client.get_user()
            repo = user.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=True
            )
            logger.info(f"Created repository: {repo.full_name}")
            return True
        except GithubException as e:
            logger.error(f"Failed to create repo: {e}")
            return False


# Import requests for download_file
import requests
