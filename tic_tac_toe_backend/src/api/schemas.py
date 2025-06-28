"""Pydantic request/response schemas for Tic Tac Toe API."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from .models import GameStatus


# --- Game ---

# PUBLIC_INTERFACE
class GameCreate(BaseModel):
    """Request to create a new game."""
    player_x: str = Field(..., description="Name for player X")
    player_o: str = Field(..., description="Name for player O")


# PUBLIC_INTERFACE
class GameRead(BaseModel):
    """Read-only game information."""
    id: int
    player_x: str
    player_o: str
    current_turn: str
    board: List[List[Optional[str]]]  # 3x3 grid
    status: GameStatus
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        orm_mode = True


# --- Move ---

# PUBLIC_INTERFACE
class MoveCreate(BaseModel):
    """Request to make a move in a game."""
    player: Literal["X", "O"] = Field(
        ..., description="Which player is making this move, X or O"
    )
    row: int = Field(..., ge=0, le=2, description="Board row index 0-2")
    col: int = Field(..., ge=0, le=2, description="Board column index 0-2")


# PUBLIC_INTERFACE
class MoveRead(BaseModel):
    """Information about a move."""
    id: int
    player: str
    row: int
    col: int
    created_at: Optional[str]

    class Config:
        orm_mode = True
