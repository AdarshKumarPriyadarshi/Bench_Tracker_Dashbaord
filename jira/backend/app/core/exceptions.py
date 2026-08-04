class JiraClientError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Jira API error ({status_code}): {message}")


class JiraAuthError(JiraClientError):
    def __init__(self):
        super().__init__(401, "Authentication failed. Check your email and API token.")
