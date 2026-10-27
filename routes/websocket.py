import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from helper import generate_room_code
from websocket.room_manager import RoomManager


router = APIRouter(tags=['Room API'])
manager = RoomManager()

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str
):

    await manager.connect(room_id, websocket)

    try:

        while True:

            data = await websocket.receive_text()

            print(f"Received: {data}")

            await manager.broadcast(
                room_id,
                data,
                websocket
            )

    except WebSocketDisconnect:

        print("Client disconnected")

        manager.disconnect(
            room_id,
            websocket
        )

    except Exception as e:

        print(f"WebSocket Error: {e}")

        manager.disconnect(
            room_id,
            websocket
        )  
active_rooms =set()

@router.post("/create-room")
async def create_room():
    room_code = generate_room_code()
    active_rooms.add(room_code)
    return {
        "room_id":room_code
    }    
    
@router.get("/room/{room_id}")
async def validate_room(room_id: str):
    exists = room_id in active_rooms
    return {
        "exists":exists
    }
