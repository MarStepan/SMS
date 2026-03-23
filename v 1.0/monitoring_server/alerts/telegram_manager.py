import requests
import logging
from datetime import datetime, timedelta
from models.database import db, Alert, Server

class TelegramManager:
    def __init__(self, bot_token, chat_ids):
        self.bot_token = bot_token
        self.chat_ids = chat_ids
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.sent_alerts = {}  # Кэш отправленных оповещений
        logging.info(f"Telegram менеджер инициализирован для {len(chat_ids)} chat_id(s)")
        
    def send_alert(self, server_name, metric_type, message, severity='warning'):
        """Отправка оповещения в Telegram"""
        try:
            formatted_message = self._format_message(server_name, metric_type, message, severity)
            
            for chat_id in self.chat_ids:
                payload = {
                    'chat_id': chat_id.strip(),
                    'text': formatted_message,
                    'parse_mode': 'HTML',
                    'disable_notification': severity == 'info'
                }
                
                response = requests.post(
                    f"{self.base_url}/sendMessage",
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logging.info(f"Оповещение отправлено в Telegram для {server_name}")
                    self._log_alert_to_db(server_name, metric_type, message, severity)
                else:
                    error_msg = response.json().get('description', 'Unknown error')
                    logging.error(f"Ошибка отправки Telegram оповещения: {error_msg}")
                    
        except Exception as e:
            logging.error(f"Ошибка отправки Telegram оповещения: {e}")
    
    def _format_message(self, server_name, metric_type, message, severity):
        """Форматирование сообщения для Telegram"""
        severity_icons = {
            'critical': '🔴',
            'warning': '🟡', 
            'info': '🔵'
        }
        
        icon = severity_icons.get(severity, '⚪')
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""{icon} <b>Система Мониторинга - Оповещение</b>

<b>Сервер:</b> <code>{server_name}</code>
<b>Метрика:</b> {metric_type}
<b>Уровень:</b> {severity.upper()}

<b>Сообщение:</b>
{message}

<b>Время:</b> {current_time}
<b>ЦС:</b> 10.10.10.222:5000
"""
    
    def _log_alert_to_db(self, server_name, metric_type, message, severity):
        """Логирование оповещения в базу данных"""
        try:
            server = Server.query.filter_by(name=server_name).first()
            if server:
                alert = Alert(
                    server_id=server.id,
                    metric_type=metric_type,
                    message=message,
                    severity=severity
                )
                db.session.add(alert)
                db.session.commit()
                logging.debug(f"Оповещение записано в БД для сервера {server_name}")
        except Exception as e:
            logging.error(f"Ошибка записи оповещения в БД: {e}")
    
    def should_send_alert(self, server_name, metric_type, cooldown_minutes=5):
        """Проверка нужно ли отправлять оповещение (учет кулдауна)"""
        key = f"{server_name}_{metric_type}"
        last_sent = self.sent_alerts.get(key)
        
        if not last_sent:
            return True
            
        if datetime.now() - last_sent > timedelta(minutes=cooldown_minutes):
            return True
            
        return False
    
    def mark_alert_sent(self, server_name, metric_type):
        """Отметка времени отправки оповещения"""
        key = f"{server_name}_{metric_type}"
        self.sent_alerts[key] = datetime.now()
    
    def send_test_message(self, test_message="Тестовое сообщение от системы мониторинга"):
        """Отправка тестового сообщения"""
        self.send_alert(
            "Тестовый Сервер",
            "test",
            test_message,
            "info"
        )