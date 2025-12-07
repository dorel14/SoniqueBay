from __future__ import annotations
import strawberry
from typing import Optional

@strawberry.input
class TrackFilterInput:
    """Input type for filtering tracks."""
    artist_id: Optional[int] = None
    album_id: Optional[int] = None
    genre: Optional[str] = None
    year: Optional[str] = None