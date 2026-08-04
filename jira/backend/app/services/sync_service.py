import asyncio
import json
from datetime import datetime, timedelta

from fastapi import WebSocket

from app.config import settings
from app.services.jira_client import JiraClient
from app.services.cache_service import cache


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)


manager = ConnectionManager()


class SyncService:
    def __init__(self):
        self.client = JiraClient()
        self.last_check = datetime.now()
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            try:
                await self._poll_changes()
            except Exception as e:
                print(f"[SyncService] Error polling: {e}")
            await asyncio.sleep(settings.sync_interval_seconds)

    def stop(self):
        self.running = False

    async def _poll_changes(self):
        if not manager.active_connections:
            return

        check_since = self.last_check - timedelta(seconds=10)
        since_str = check_since.strftime("%Y-%m-%d %H:%M")
        self.last_check = datetime.now()

        try:
            data = await self.client.search_issues(
                jql=f'updated >= "{since_str}" ORDER BY updated DESC',
                fields=["summary", "status", "assignee", "updated"],
                max_results=20,
            )

            issues = data.get("issues", [])
            if issues:
                cache.clear()

                await manager.broadcast({
                    "type": "issues_updated",
                    "count": len(issues),
                    "keys": [i.get("key") for i in issues[:10]],
                    "timestamp": datetime.now().isoformat(),
                })
        except Exception:
            pass


sync_service = SyncService()
