import asyncio
import json
from uuid import uuid4

from fastapi import WebSocket


class RealtimeManager:
    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, family_id: str) -> None:
        await websocket.accept()
        async with self.lock:
            self.connections.setdefault(family_id, set()).add(websocket)

    async def disconnect(self, websocket: WebSocket, family_id: str) -> None:
        async with self.lock:
            family_connections = self.connections.get(family_id)
            if family_connections:
                family_connections.discard(websocket)
                if not family_connections:
                    self.connections.pop(family_id, None)

    async def broadcast(self, event: dict[str, str], family_id: str | None = None) -> None:
        message = json.dumps({**event, "event_id": str(uuid4())})
        async with self.lock:
            groups = [self.connections.get(family_id, set())] if family_id else self.connections.values()
            connections = [connection for group in groups for connection in group]
        disconnected: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(websocket)
        for websocket in disconnected:
            async with self.lock:
                for group in self.connections.values():
                    group.discard(websocket)


realtime_manager = RealtimeManager()
