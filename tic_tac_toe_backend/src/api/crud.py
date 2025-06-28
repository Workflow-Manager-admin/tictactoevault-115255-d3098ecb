"""Business logic and CRUD helpers for Tic Tac Toe."""

from sqlalchemy.orm import Session
from sqlalchemy import select, asc

from . import models, schemas


class InvalidMoveException(Exception):
    pass


# PUBLIC_INTERFACE
def create_game(db: Session, game_req: schemas.GameCreate) -> models.Game:
    """Create a new Tic Tac Toe game."""
    db_game = models.Game(
        player_x=game_req.player_x,
        player_o=game_req.player_o,
        current_turn="X",
        board=[["", "", ""], ["", "", ""], ["", "", ""]],
        status=models.GameStatus.ONGOING,
    )
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game


# PUBLIC_INTERFACE
def get_games(db: Session):
    """Return all games (most recent first)."""
    return db.execute(
        select(models.Game).order_by(models.Game.created_at.desc())
    ).scalars().all()


# PUBLIC_INTERFACE
def get_game(db: Session, game_id: int):
    """Return a game by ID, or None."""
    return db.get(models.Game, game_id)


# PUBLIC_INTERFACE
def get_moves(db: Session, game_id: int):
    """Return all moves for a game."""
    return db.execute(
        select(models.Move)
        .where(models.Move.game_id == game_id)
        .order_by(asc(models.Move.created_at))
    ).scalars().all()


# PUBLIC_INTERFACE
def make_move(db: Session, game_id: int, move: schemas.MoveCreate) -> models.Move:
    """
    Validate and make a move, updating game state, checking for win/tie.
    """
    game = db.get(models.Game, game_id)
    if not game:
        raise InvalidMoveException("Game not found.")
    if game.status != models.GameStatus.ONGOING:
        raise InvalidMoveException(
            f"Game is already over with status {game.status.value}."
        )
    if move.player not in ("X", "O"):
        raise InvalidMoveException("Player must be X or O.")
    if game.current_turn != move.player:
        raise InvalidMoveException(f"It is not {move.player}'s turn.")
    if not (0 <= move.row <= 2 and 0 <= move.col <= 2):
        raise InvalidMoveException("Invalid board coordinates.")

    board = [row[:] for row in game.board]
    if board[move.row][move.col] != "":
        raise InvalidMoveException("That cell is already occupied.")

    board[move.row][move.col] = move.player

    # Check win or tie
    status = _evaluate_board_status(board)
    game.board = board
    game.updated_at = None  # SQLAlchemy will update
    if status == "ONGOING":
        game.current_turn = "O" if move.player == "X" else "X"
    elif status == "X_WON":
        game.status = models.GameStatus.X_WON
    elif status == "O_WON":
        game.status = models.GameStatus.O_WON
    elif status == "TIE":
        game.status = models.GameStatus.TIE

    db_move = models.Move(
        game_id=game_id,
        player=move.player,
        row=move.row,
        col=move.col,
    )
    db.add(db_move)
    db.commit()
    db.refresh(db_move)
    db.refresh(game)  # To pick up status updates

    # Broadcast websocket update if needed (optional)
    try:
        from .main import broadcast_game_update
        broadcast_game_update(
            game_id,
            {
                "type": "update",
                "game_id": game_id,
                "board": board,
                "status": (
                    game.status.value
                    if hasattr(game.status, "value")
                    else str(game.status)
                ),
                "current_turn": game.current_turn,
            }
        )
    except ImportError:
        pass

    return db_move


def _evaluate_board_status(board) -> str:
    """Return 'X_WON', 'O_WON', 'TIE', or 'ONGOING'."""
    lines = (
        board
        + [[board[r][c] for r in range(3)] for c in range(3)]
        + [[board[i][i] for i in range(3)]]
        + [[board[i][2 - i] for i in range(3)]]
    )
    for line in lines:
        if line == ["X", "X", "X"]:
            return "X_WON"
        if line == ["O", "O", "O"]:
            return "O_WON"
    if all(cell in ("X", "O") for row in board for cell in row):
        return "TIE"
    return "ONGOING"
