"""
Google Sheets Reader for Trading Signals
Читает торговые сигналы из Google Sheets
"""
import os
import json
import logging
from typing import List, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class SheetsReader:
    """Класс для чтения торговых сигналов из Google Sheets"""
    
    def __init__(self):
        """Инициализация клиента Google Sheets"""
        self.service = None
        self.spreadsheet_id = None
        self._initialize()
    
    def _initialize(self):
        """Инициализирует подключение к Google Sheets API"""
        try:
            # Получаем JSON credentials из переменной окружения
            creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if not creds_json:
                logger.error("GOOGLE_SERVICE_ACCOUNT_JSON not found in environment variables")
                return
            
            # Парсим JSON
            creds_dict = json.loads(creds_json)
            
            # Создаём credentials
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            
            # Создаём сервис
            self.service = build('sheets', 'v4', credentials=credentials)
            
            # Получаем ID таблицы
            self.spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
            if not self.spreadsheet_id:
                logger.error("GOOGLE_SHEETS_SPREADSHEET_ID not found in environment variables")
                return
            
            logger.info(f"Successfully initialized Google Sheets API client for spreadsheet {self.spreadsheet_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets API: {e}", exc_info=True)
    
    def read_signals(self, sheet_name: str = "Sheet1") -> List[Dict[str, Any]]:
        """
        Читает торговые сигналы из Google Sheets
        
        Args:
            sheet_name: Имя листа в таблице (по умолчанию "Sheet1")
        
        Returns:
            Список сигналов в формате словарей
        """
        if not self.service or not self.spreadsheet_id:
            logger.error("Google Sheets API not initialized")
            return []
        
        try:
            # Читаем данные из таблицы
            range_name = f"{sheet_name}!A1:F100"  # Читаем первые 100 строк
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning("No data found in Google Sheets")
                return []
            
            # Первая строка - заголовки
            headers = values[0]
            logger.info(f"Found headers: {headers}")
            
            # Остальные строки - данные
            signals = []
            for i, row in enumerate(values[1:], start=2):
                if len(row) < 3:  # Минимум нужно: symbol, condition, target_price (exchange опциональный)
                    logger.warning(f"Skipping row {i}: not enough columns")
                    continue
                
                # Создаём словарь из строки
                signal = {}
                for j, header in enumerate(headers):
                    if j < len(row):
                        signal[header.lower().strip()] = row[j]
                    else:
                        signal[header.lower().strip()] = None
                
                # Проверяем что сигнал активен
                active = signal.get('active', 'TRUE').upper()
                if active not in ['TRUE', 'YES', '1', 'Y']:
                    logger.debug(f"Skipping inactive signal on row {i}")
                    continue
                
                # Валидация обязательных полей (exchange опциональный - по умолчанию binance)
                required_fields = ['symbol', 'condition', 'target_price']
                if not all(signal.get(field) for field in required_fields):
                    logger.warning(f"Skipping row {i}: missing required fields")
                    continue
                
                # Если exchange не указан или пустой - оставляем None (будет использована первая доступная биржа)
                if not signal.get('exchange') or not signal.get('exchange').strip():
                    signal['exchange'] = None  # Изменено: None вместо 'binance'
                    logger.debug(f"Row {i}: exchange not specified, will use default available exchange")
                
                # Конвертируем target_price в float
                try:
                    signal['target_price'] = float(signal['target_price'])
                except (ValueError, TypeError):
                    logger.warning(f"Skipping row {i}: invalid target_price")
                    continue
                
                signals.append(signal)
                logger.debug(f"Added signal from row {i}: {signal}")
            
            logger.info(f"Successfully read {len(signals)} active signals from Google Sheets")
            return signals
            
        except Exception as e:
            logger.error(f"Failed to read signals from Google Sheets: {e}", exc_info=True)
            return []
    
    def test_connection(self) -> bool:
        """
        Тестирует подключение к Google Sheets
        
        Returns:
            True если подключение успешно, False иначе
        """
        if not self.service or not self.spreadsheet_id:
            return False
        
        try:
            # Пытаемся прочитать метаданные таблицы
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            title = spreadsheet.get('properties', {}).get('title', 'Unknown')
            logger.info(f"Successfully connected to spreadsheet: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}", exc_info=True)
            return False


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    reader = SheetsReader()
    
    # Тест подключения
    if reader.test_connection():
        print("✅ Connection successful!")
        
        # Читаем сигналы
        signals = reader.read_signals()
        print(f"\n📊 Found {len(signals)} signals:")
        for signal in signals:
            exchange = signal.get('exchange', 'binance')  # по умолчанию binance
            print(f"  - {exchange} {signal['symbol']} {signal['condition']} {signal['target_price']}")
        
        print("\nℹ️  Подсказка: Столбец 'exchange' опциональный!")
        print("  Если не указан - используется binance по умолчанию")
        print("  + Автоматический fallback на coinbase если binance не работает!")
    else:
        print("❌ Connection failed!")
