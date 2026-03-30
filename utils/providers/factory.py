from utils.providers.base import GitProvider
from utils.providers.bitbucket import BitbucketProvider
from utils.providers.github import GitHubProvider


def get_provider(provider: str) -> GitProvider:
    if provider == "github":
        return GitHubProvider()
    if provider == "bitbucket":
        return BitbucketProvider()
    raise ValueError(f"Unknown provider: '{provider}'. Supported values: 'github', 'bitbucket'.")
