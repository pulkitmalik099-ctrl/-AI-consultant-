"""Online Jira ticket fetcher via Jira REST API v2.

Works with:
  - Jira Cloud (https://company.atlassian.net)
  - Jira Server / Data Center (self-hosted IP or domain)
"""

import requests
from langchain_core.documents import Document
from src.ingestion.models import JiraOnlineConfig


def fetch_jira_issues(config: JiraOnlineConfig) -> list[Document]:
    """Fetch issues from a live Jira instance.

    Auth: Basic auth (username + API token).
    Paginates automatically up to config.limit issues.
    """
    search_url = f"{config.server_url}/rest/api/2/search"
    auth = (config.username, config.api_token)

    if config.jql:
        query = config.jql
    elif config.project_key:
        query = f"project = {config.project_key} ORDER BY created DESC"
    else:
        query = "ORDER BY created DESC"

    docs: list[Document] = []
    start_at = 0

    while len(docs) < config.limit:
        batch = min(50, config.limit - len(docs))
        resp = requests.get(
            search_url,
            auth=auth,
            params={
                "jql": query,
                "startAt": start_at,
                "maxResults": batch,
                "fields": "summary,description,status,issuetype",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        issues = data.get("issues", [])
        if not issues:
            break

        for issue in issues:
            fields = issue.get("fields", {})
            issue_key = issue["key"]
            content = (
                f"[Jira] {issue_key}: {fields.get('summary', '')}\n"
                f"Type: {fields.get('issuetype', {}).get('name', '')} | "
                f"Status: {fields.get('status', {}).get('name', '')}\n\n"
                f"{fields.get('description', '') or ''}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": f"jira://issue/{issue_key}",
                        "provider": "jira",
                        "mode": "online",
                        "issue_key": issue_key,
                        "summary": fields.get("summary", ""),
                        "status": fields.get("status", {}).get("name", ""),
                        "issue_type": fields.get("issuetype", {}).get("name", ""),
                    },
                )
            )

        start_at += len(issues)
        if start_at >= data.get("total", 0):
            break

    return docs
