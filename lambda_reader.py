"""
AWS Lambda READER - Fan-Out Architecture
Читает сигналы из Google Sheets и отправляет в SQS очередь
Запускается по расписанию CloudWatch Events
"""
import os
import json
import boto3
import logging
from datetime import datetime

# AWS SQS клиент
sqs = boto3.client('sqs')

from services.sheets_reader import SheetsReader

# Инициализация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """
    Lambda Reader - Fan-Out паттерн
    
    1. Читает все сигналы из Google Sheets
    2. Отправляет каждый сигнал как отдельное сообщение в SQS
    3. Lambda Workers обработают их параллельно
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 Lambda READER - Starting signal collection")
        logger.info(f"⏰ Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        # Получаем URL очереди из переменных окружения
        queue_url = os.getenv('SQS_QUEUE_URL')
        if not queue_url:
            logger.error("❌ SQS_QUEUE_URL not configured")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'SQS_QUEUE_URL not set'})
            }
        
        # Читаем сигналы из Google Sheets
        sheets_reader = SheetsReader()
        
        if not sheets_reader.test_connection():
            logger.error("❌ Failed to connect to Google Sheets")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Google Sheets connection failed'})
            }
        
        signals_data = sheets_reader.read_signals()
        logger.info(f"📊 Read {len(signals_data)} signals from Google Sheets")
        
        if not signals_data:
            logger.info("ℹ️  No signals found")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No signals to process'})
            }
        
        # Отправляем каждый сигнал в SQS как отдельное сообщение
        sent_count = 0
        failed_count = 0
        
        for i, signal_dict in enumerate(signals_data, 1):
            try:
                # Отправляем сообщение в SQS
                response = sqs.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(signal_dict),
                    MessageAttributes={
                        'signal_index': {
                            'DataType': 'Number',
                            'StringValue': str(i)
                        }
                    }
                )
                sent_count += 1
                logger.debug(f"✅ Sent signal {i} to SQS: {response['MessageId']}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Failed to send signal {i} to SQS: {e}")
        
        logger.info("=" * 60)
        logger.info(f"✅ Lambda READER completed")
        logger.info(f"📤 Sent: {sent_count} signals")
        logger.info(f"❌ Failed: {failed_count} signals")
        logger.info("=" * 60)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Signals sent to SQS',
                'total_signals': len(signals_data),
                'sent_count': sent_count,
                'failed_count': failed_count,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in Lambda Reader: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }
