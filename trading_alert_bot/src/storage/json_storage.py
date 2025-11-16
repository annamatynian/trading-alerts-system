"""
Реализация хранилища, использующая локальный JSON-файл.
Идеально для тестирования и разработки.
"""
import json
import logging
from typing import List, Dict, Any
from pathlib import Path
import uuid

from models.alert import AlertTarget
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
                json.dump({"alerts": [], "users": {}}, f, indent=4)
            logger.info(f"Created empty storage file at {self.file_path}")

    def _read_data(self) -> Dict[str, Any]:
        """Читает все данные из файла."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.error(f"Could not read or parse {self.file_path}. Recreating it.")
            self._ensure_file_exists()
            return {"alerts": [], "users": {}}

    def _write_data(self, data: Dict[str, Any]):
        """Записывает все данные в файл."""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, default=str) # default=str для datetime

    async def load_alerts(self) -> List[AlertTarget]:
        data = self._read_data()
        return [AlertTarget.parse_obj(alert_data) for alert_data in data.get("alerts", [])]

    async def save_alert(self, alert: AlertTarget) -> bool:
        data = self._read_data()
        alert.id = str(uuid.uuid4()) # Присваиваем уникальный ID
        data["alerts"].append(alert.dict())
        self._write_data(data)
        logger.info(f"Saved new alert with ID {alert.id}")
        return True
    
    async def update_alert(self, alert_to_update: AlertTarget) -> bool:
        data = self._read_data()
        alerts = data.get("alerts", [])
        for i, alert_data in enumerate(alerts):
            if alert_data.get("id") == alert_to_update.id:
                alerts[i] = alert_to_update.dict()
                self._write_data(data)
                logger.info(f"Updated alert with ID {alert_to_update.id}")
                return True
        logger.warning(f"Could not find alert with ID {alert_to_update.id} to update.")
        return False
    
    async def delete_alert(self, alert_id: str) -> bool:
        """Delete alert by ID"""
        data = self._read_data()
        alerts = data.get("alerts", [])
        for i, alert_data in enumerate(alerts):
            if alert_data.get("id") == alert_id:
                alerts.pop(i)
                self._write_data(data)
                logger.info(f"Deleted alert with ID {alert_id}")
                return True
        logger.warning(f"Could not find alert with ID {alert_id} to delete.")
        return False
        
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
