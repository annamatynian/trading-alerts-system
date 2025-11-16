"""
Реализация хранилища, использующая локальный JSON-файл.
Идеально для тестирования и разработки.
"""
import json
import logging
from typing import List, Dict, Any
from pathlib import Path
import uuid

from models.signal import SignalTarget
from storage.base import StorageBase

logger = logging.getLogger(__name__)

class JSONStorage(StorageBase):
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Создает пустой файл-хранилище, если его нет."""
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({"signals": [], "users": {}}, f, indent=4)
            logger.info(f"Created empty storage file at {self.file_path}")

    def _read_data(self) -> Dict[str, Any]:
        """Читает все данные из файла."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.error(f"Could not read or parse {self.file_path}. Recreating it.")
            self._ensure_file_exists()
            return {"signals": [], "users": {}}

    def _write_data(self, data: Dict[str, Any]):
        """Записывает все данные в файл."""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, default=str) # default=str для datetime

    async def load_signals(self) -> List[SignalTarget]:
        data = self._read_data()
        return [SignalTarget.parse_obj(signal_data) for signal_data in data.get("signals", [])]

    async def save_signal(self, signal: SignalTarget) -> bool:
        data = self._read_data()
        signal.id = str(uuid.uuid4()) # Присваиваем уникальный ID
        data["signals"].append(signal.dict())
        self._write_data(data)
        logger.info(f"Saved new signal with ID {signal.id}")
        return True
    
    async def update_signal(self, signal_to_update: SignalTarget) -> bool:
        data = self._read_data()
        signals = data.get("signals", [])
        for i, signal_data in enumerate(signals):
            if signal_data.get("id") == signal_to_update.id:
                signals[i] = signal_to_update.dict()
                self._write_data(data)
                logger.info(f"Updated signal with ID {signal_to_update.id}")
                return True
        logger.warning(f"Could not find signal with ID {signal_to_update.id} to update.")
        return False
    
    async def delete_signal(self, signal_id: str) -> bool:
        """Delete signal by ID"""
        data = self._read_data()
        signals = data.get("signals", [])
        for i, signal_data in enumerate(signals):
            if signal_data.get("id") == signal_id:
                signals.pop(i)
                self._write_data(data)
                logger.info(f"Deleted signal with ID {signal_id}")
                return True
        logger.warning(f"Could not find signal with ID {signal_id} to delete.")
        return False
    
    async def get_signals_for_user(self, user_id: str) -> List[SignalTarget]:
        """Get all signals for a specific user"""
        data = self._read_data()
        signals = []
        for signal_data in data.get("signals", []):
            if signal_data.get("user_id") == user_id:
                signals.append(SignalTarget.parse_obj(signal_data))
        return signals
        
    # --- Методы для работы с пользователями ---
    async def get_user_data(self, user_id: str) -> Dict[str, Any]:
        data = self._read_data()
        return data.get("users", {}).get(user_id, {})

    async def save_user_data(self, user_id: str, chat_id: str, pushover_key: str = None):
        data = self._read_data()
        if "users" not in data:
            data["users"] = {}
        
        user_data = data["users"].get(user_id, {})
        user_data["chat_id"] = chat_id
        if pushover_key:
            user_data["pushover_key"] = pushover_key
        
        data["users"][user_id] = user_data
        self._write_data(data)
        logger.info(f"Saved data for user {user_id}")
