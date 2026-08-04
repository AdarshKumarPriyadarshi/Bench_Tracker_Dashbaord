from app.services.jira_client import JiraClient

_jira_client: JiraClient | None = None


def get_jira_client() -> JiraClient:
    global _jira_client
    if _jira_client is None:
        _jira_client = JiraClient()
    return _jira_client
