from flask import Flask, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging
import atexit
import os
import traceback

from config import config
from models.database import db
from models.influx_manager import InfluxDBManager
from alerts.telegram_manager import TelegramManager
from alerts.alert_engine import AlertEngine
from api.endpoints import register_endpoints

# Глобальные переменные для менеджеров
telegram_manager = None
influx_manager = None
alert_engine = None




def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    
    
    # Инициализация расширений
    db.init_app(app)
    
    # Инициализация менеджеров при запуске приложения
    with app.app_context():
        init_managers(app)
        register_endpoints(app, telegram_manager, influx_manager, alert_engine)
    
    # Веб-роуты
    @app.route('/')
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/alerts')
    def alerts_page():
        return render_template('alerts.html')
    
    @app.route('/servers')
    def servers_page():
        return render_template('servers.html')
    
    
    
    # Задачи по расписанию
    def cleanup_old_alerts():
        """Очистка старых оповещений"""
        with app.app_context():
            try:
                from models.database import Alert
                cutoff_date = datetime.utcnow() - timedelta(days=7)  # Храним 7 дней
                old_alerts = Alert.query.filter(
                    Alert.created_at < cutoff_date,
                    Alert.status == 'resolved'
                )
                count = old_alerts.count()
                old_alerts.delete()
                db.session.commit()
                logging.info(f"Очищено {count} старых оповещений")
            except Exception as e:
                logging.error(f"Ошибка очистки оповещений: {e}")
    
    def cleanup_old_metrics():
        """Очистка старых метрик (если используем SQLite)"""
        with app.app_context():
            try:
                from models.database import ServerMetric
                cutoff_date = datetime.utcnow() - timedelta(days=3)  # Храним 3 дня
                old_metrics = ServerMetric.query.filter(
                    ServerMetric.timestamp < cutoff_date
                )
                count = old_metrics.count()
                old_metrics.delete()
                db.session.commit()
                logging.info(f"Очищено {count} старых метрик")
            except Exception as e:
                logging.error(f"Ошибка очистки метрик: {e}")
    
    # Настройка планировщика
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_old_alerts, 'interval', hours=6)
    scheduler.add_job(cleanup_old_metrics, 'interval', hours=12)
    scheduler.start()
    
    # Остановка планировщика при выходе
    atexit.register(lambda: scheduler.shutdown())
    
    return app

def init_managers(app):
    """Инициализация менеджеров"""
    global telegram_manager, influx_manager, alert_engine
    
    # Инициализация Telegram менеджера
    telegram_manager = TelegramManager(
        app.config['TELEGRAM_BOT_TOKEN'],
        app.config['TELEGRAM_CHAT_IDS']
    )
    
    # Инициализация InfluxDB менеджера
    try:
        influx_manager = InfluxDBManager(
            app.config['INFLUXDB_HOST'],
            app.config['INFLUXDB_PORT'],
            app.config['INFLUXDB_DATABASE']
        )
        logging.info("InfluxDB менеджер успешно инициализирован")
    except Exception as e:
        logging.warning(f"InfluxDB недоступен: {e}. Используется режим без InfluxDB.")
        influx_manager = None
    
    # Инициализация движка оповещений
    alert_engine = AlertEngine(telegram_manager)

if __name__ == '__main__':
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('monitoring_server.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Создание приложения
    app = create_app()
    
    # Создание таблиц в базе данных
    with app.app_context():
        db.create_all()
        logging.info("Таблицы базы данных созданы/проверены")
    
    # Запуск сервера
    host = app.config['SERVER_HOST']
    port = app.config['SERVER_PORT']
    
    print("=" * 50)
    print("Запуск системы мониторинга серверов")
    print("=" * 50)
    print(f"Центральный сервер: {host}:{port}")
    print(f"Дашборд: http://{host}:{port}")
    print(f"API Health: http://{host}:{port}/api/health")
    print(f"Telegram Bot: настроен для chat_id {app.config['TELEGRAM_CHAT_IDS']}")
    print("=" * 50)
    
    app.run(host=host, port=port, debug=True)