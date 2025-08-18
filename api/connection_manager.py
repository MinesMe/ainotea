# file: api/connection_manager.py

from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    """
    Класс для управления активными WebSocket-соединениями.
    Работает по принципу "комнат", где каждая комната - это ID заметки.
    """
    def __init__(self):
        # Словарь для хранения активных соединений.
        # Формат: { "note_id_1": [websocket1, websocket2], "note_id_2": [websocket3] }
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, note_id: str):
        """
        Принимает новое WebSocket-соединение и добавляет его в "комнату" заметки.
        """
        await websocket.accept()
        if note_id not in self.active_connections:
            # Если это первое подключение к этой заметке, создаем для нее "комнату"
            self.active_connections[note_id] = []
        self.active_connections[note_id].append(websocket)

    def disconnect(self, websocket: WebSocket, note_id: str):
        """
        Удаляет WebSocket-соединение из "комнаты" заметки.
        """
        if note_id in self.active_connections:
            self.active_connections[note_id].remove(websocket)
            # Если в комнате больше никого не осталось, можно удалить и саму комнату
            if not self.active_connections[note_id]:
                del self.active_connections[note_id]

    async def broadcast(self, message: str, note_id: str, sender: WebSocket):
        """
        Рассылает сообщение всем подключенным клиентам в "комнате" заметки,
        кроме самого отправителя.
        """
        if note_id in self.active_connections:
            for connection in self.active_connections[note_id]:
                if connection != sender:
                    await connection.send_text(message)

# Создаем один глобальный экземпляр менеджера,
# который будет использоваться во всем приложении (Singleton pattern).
manager = ConnectionManager()