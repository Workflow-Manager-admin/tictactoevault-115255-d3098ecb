"""Main FastAPI application entrypoint for Tic Tac Toe backend.

Implements RESTful API endpoints for:
- Creating a new game
- Making a move
- Retrieving a specific game's state
- Listing all current and past games

Provides OpenAPI (Swagger) documentation with detailed models.

Uses SQLAlchemy ORM for PostgreSQL via environment variables:
POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT

Author: Kavia Codegen
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from dotenv import load_dotenv

from tic_tac_toe_backend.src.api import schemas, crud, db

# Load env vars
load_dotenv()

app = FastAPI(
    title="Tic Tac Toe Backend API",
    description=(
        "A backend service for Tic Tac Toe game with RESTful endpoints. "
        "Supports starting games, making moves, retrieving state, and real-time updates."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "Games", "description": "Game creation, moves, and retrieval"},
        {"name": "WebSocket", "description": "Real-time game updates (websocket)"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


# PUBLIC_INTERFACE
@app.get("/", summary="Health Check", tags=["Games"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.post(
    "/games",
    response_model=schemas.GameRead,
    status_code=201,
    summary="Start a new game",
    tags=["Games"]
)
def create_game(game_req: schemas.GameCreate, db_: Session = Depends(get_db)):
    """
    Create a new Tic Tac Toe game.

    Args:
        game_req: Request body with player X and O names.

    Returns:
        The newly created game object.
    """
    game = crud.create_game(db_, game_req)
    return game


# PUBLIC_INTERFACE
@app.get(
    "/games",
    response_model=List[schemas.GameRead],
    summary="List all games",
    tags=["Games"]
)
def list_games(db_: Session = Depends(get_db)):
    """
    List all Tic Tac Toe games (ongoing and completed).
    """
    return crud.get_games(db_)


# PUBLIC_INTERFACE
@app.get(
    "/games/{game_id}",
    response_model=schemas.GameRead,
    summary="Get a game's current state",
    tags=["Games"]
)
def get_game(game_id: int, db_: Session = Depends(get_db)):
    """
    Get details (board, players, current turn, status) for a specific game.
    """
    game = crud.get_game(db_, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


# PUBLIC_INTERFACE
@app.post(
    "/games/{game_id}/moves",
    response_model=schemas.MoveRead,
    summary="Make a move",
    tags=["Games"]
)
def make_move(game_id: int, move: schemas.MoveCreate, db_: Session = Depends(get_db)):
    """
    Play a move (place X or O at row,col) in an ongoing game.

    Args:
        game_id: Game to play in
        move: Row (0-2), col (0-2), and player ('X' or 'O')

    Returns:
        Move information, with win/tie update if game has changed state.
    """
    try:
        move_made = crud.make_move(db_, game_id, move)
        return move_made
    except crud.InvalidMoveException as e:
        raise HTTPException(status_code=400, detail=str(e))


# PUBLIC_INTERFACE
@app.get(
    "/games/{game_id}/moves",
    response_model=List[schemas.MoveRead],
    summary="List moves for a game",
    tags=["Games"]
)
def list_game_moves(game_id: int, db_: Session = Depends(get_db)):
    """
    List all moves made in a specific game.
    """
    game = crud.get_game(db_, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return crud.get_moves(db_, game_id)


# === Optional Real-Time Updates (WebSocket) ===

connections: Dict[int, List[WebSocket]] = {}


# PUBLIC_INTERFACE
@app.websocket("/ws/games/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int):
    """
    WebSocket endpoint for real-time game updates.

    - Connect clients to /ws/games/{game_id}
    - On moves, broadcast game state to all subscribed clients
    """
    game_id = int(game_id)
    await websocket.accept()
    if game_id not in connections:
        connections[game_id] = []
    connections[game_id].append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Heartbeat/keepalive
    except WebSocketDisconnect:
        connections[game_id].remove(websocket)


def broadcast_game_update(game_id: int, message: Dict[str, Any]):
    """Send update to all listening websockets for that game."""
    import asyncio
    websockets = connections.get(game_id, [])
    coros = [
        ws.send_json(message)
        for ws in websockets if not ws.client_state.name == "DISCONNECTED"
    ]
    if coros:
        asyncio.create_task(asyncio.gather(*coros))


# PUBLIC_INTERFACE
@app.get(
    "/docs/websockets",
    summary="Websocket connection usage",
    tags=["WebSocket"]
)
def websocket_usage_doc():
    """
    WebSocket usage guide for real-time updates:

    - Connect to `/ws/games/{game_id}` via websocket for real-time game state changes.
    - Server broadcasts changes after moves.
    """
    return {
        "websocket_endpoint": "/ws/games/{game_id}",
        "usage": "Receive real-time game updates."
    }
