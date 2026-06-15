"""In-memory combat session store.

Drop-in Redis replacement: swap this module in Phase 3 without changing
any caller code — all methods are async with identical signatures.

Usage:
    from backend.state.store import session_store
    await session_store.create(session)
    session = await session_store.get(combat_id)
    await session_store.update(session)
    await session_store.delete(combat_id)
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from backend.schemas.combat_session import CombatSession, SessionStatus

logger = logging.getLogger(__name__)


class InMemorySessionStore:
    def __init__(self) -> None:
        self._store: dict[str, CombatSession] = {}
        self._lock = asyncio.Lock()

    async def create(self, session: CombatSession) -> CombatSession:
        """Persist a new session. Raises ValueError if combat_id already exists."""
        async with self._lock:
            if session.combat_id in self._store:
                raise ValueError(f"Session '{session.combat_id}' already exists.")
            self._store[session.combat_id] = session
            logger.info("Session created: %s", session.combat_id)
            return session

    async def get(self, combat_id: str) -> Optional[CombatSession]:
        return self._store.get(combat_id)

    async def get_or_raise(self, combat_id: str) -> CombatSession:
        session = self._store.get(combat_id)
        if session is None:
            raise KeyError(f"Session '{combat_id}' not found")
        return session

    async def update(self, session: CombatSession) -> CombatSession:
        async with self._lock:
            if session.combat_id not in self._store:
                raise KeyError(f"Session '{session.combat_id}' not found.")
            session.updated_at = datetime.now(timezone.utc)
            self._store[session.combat_id] = session
            return session

    async def delete(self, combat_id: str) -> bool:
        async with self._lock:
            existed = combat_id in self._store
            self._store.pop(combat_id, None)
            if existed:
                logger.info("Session deleted: %s", combat_id)
            return existed

    async def list_active(self) -> list[CombatSession]:
        return [s for s in self._store.values() if s.status == SessionStatus.active]

    @property
    def count(self) -> int:
        return len(self._store)


# Module-level singleton
session_store = InMemorySessionStore()
