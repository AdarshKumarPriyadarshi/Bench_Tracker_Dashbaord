import httpx
from app.config import settings
from app.core.exceptions import JiraClientError, JiraAuthError


class JiraClient:
    def __init__(self):
        self.base_url = settings.jira_base_url
        self.auth = (settings.jira_user_email, settings.jira_api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            auth=self.auth,
            headers=self.headers,
            timeout=30.0,
        )

    async def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code == 401:
            raise JiraAuthError()
        if response.status_code >= 400:
            raise JiraClientError(response.status_code, response.text[:500])
        return response.json()

    async def search_issues(
        self,
        jql: str,
        fields: list[str] | None = None,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict:
        if fields is None:
            fields = ["summary", "status", "assignee", "labels", "priority", "issuetype", "created", "updated", "sprint"]

        url = f"{self.base_url}/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "fields": ",".join(fields),
            "startAt": start_at,
            "maxResults": max_results,
        }

        async with self._client() as client:
            response = await client.get(url, params=params)
            return await self._handle_response(response)

    async def get_issue(self, issue_key: str) -> dict:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        async with self._client() as client:
            response = await client.get(url)
            return await self._handle_response(response)

    async def get_projects(self) -> list[dict]:
        url = f"{self.base_url}/rest/api/3/project/search"
        async with self._client() as client:
            response = await client.get(url, params={"maxResults": 50})
            data = await self._handle_response(response)
            return data.get("values", [])

    async def get_boards(self, project_key: str | None = None) -> list[dict]:
        url = f"{self.base_url}/rest/agile/1.0/board"
        params = {"maxResults": 50}
        if project_key:
            params["projectKeyOrId"] = project_key
        async with self._client() as client:
            response = await client.get(url, params=params)
            data = await self._handle_response(response)
            return data.get("values", [])

    async def get_board_issues(
        self,
        board_id: int,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict:
        url = f"{self.base_url}/rest/agile/1.0/board/{board_id}/issue"
        params = {
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "summary,status,assignee,labels,priority,issuetype,created,updated,sprint",
        }
        async with self._client() as client:
            response = await client.get(url, params=params)
            return await self._handle_response(response)

    async def get_sprints(self, board_id: int, state: str | None = None) -> list[dict]:
        url = f"{self.base_url}/rest/agile/1.0/board/{board_id}/sprint"
        params = {"maxResults": 50}
        if state:
            params["state"] = state
        async with self._client() as client:
            response = await client.get(url, params=params)
            data = await self._handle_response(response)
            return data.get("values", [])

    async def get_sprint_issues(
        self,
        sprint_id: int,
        start_at: int = 0,
        max_results: int = 50,
    ) -> dict:
        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
        params = {
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "summary,status,assignee,labels,priority,issuetype,created,updated,sprint",
        }
        async with self._client() as client:
            response = await client.get(url, params=params)
            return await self._handle_response(response)
