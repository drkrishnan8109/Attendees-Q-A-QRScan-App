"""Typed records shared by persistence and presentation layers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Room:
    """A reusable presentation room."""

    public_id: str
    title: str
    created_at: str


@dataclass(frozen=True, slots=True)
class Question:
    """A room question with viewer-relative reaction state."""

    public_id: str
    room_id: str
    body: str
    created_at: str
    like_count: int = 0
    liked_by_viewer: bool = False
