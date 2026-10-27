from collections import defaultdict

from fastapi import WebSocket


class RoomManager:
    
    def __init__(self):
        self.rooms = defaultdict(list)
        self.hosts ={}
        self.room_states ={}
    
    async def connect(self,room_id:str,websocket:WebSocket,is_host:bool=False):
        await websocket.accept()
        self.rooms[room_id].append(websocket)
        if is_host:
            self.hosts[room_id] =websocket
        
    def disconnect(
    self,
    room_id: str,
    websocket: WebSocket
):

        if room_id in self.rooms:

            if websocket in self.rooms[room_id]:

                self.rooms[room_id].remove(websocket)

        if len(self.rooms[room_id]) == 0:

            del self.rooms[room_id]

        if room_id in self.hosts:

            if self.hosts[room_id] == websocket:

                del self.hosts[room_id]
                
                
    async def broadcast(
        self,
        room_id: str,
        message: str,
        sender: WebSocket
    ):
        disconnected = []

        # Use list() to iterate over a copy of the current connections
        for connection in list(self.rooms[room_id]):
            if connection == sender:
                continue

            # INDENTED INSIDE THE LOOP
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Broadcast error: {e}")
                disconnected.append(connection)

        # Cleanup dead connections
        for connection in disconnected:
            self.disconnect(room_id, connection)
    
    def update_room_state(
        self,
        room_id:str,
        state: dict
    ):
        self.room_states[room_id]=state
        
    def get_room_state(self,room_id:str,):
        return self.room_states.get(room_id,None)