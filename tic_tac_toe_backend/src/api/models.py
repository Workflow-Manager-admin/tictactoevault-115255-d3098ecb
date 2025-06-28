"""SQLAlchemy ORM models for Tic Tac Toe."""

from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .db import Base


class GameStatus(enum.Enum):
    ONGOING = "ONGOING"
    X_WON = "X_WON"
    O_WON = "O_WON"
    TIE = "TIE"


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_x = Column(String, nullable=False)
    player_o = Column(String, nullable=False)
    current_turn = Column(String, default="X")
    # Remove default lambda here; handle default at application logic
    board = Column(JSON, nullable=False)
    status = Column(Enum(GameStatus), default=GameStatus.ONGOING)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    moves = relationship("Move", back_populates="game", cascade="all, delete-orphan")


class Move(Base):
    __tablename__ = "moves"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    game_id = Column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    player = Column(String, nullable=False)  # 'X' or 'O'
    row = Column(Integer, nullable=False)
    col = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    game = relationship("Game", back_populates="moves")
    __table_args__ = (
        UniqueConstraint("game_id", "row", "col", name="unique_move_per_spot"),
    )
