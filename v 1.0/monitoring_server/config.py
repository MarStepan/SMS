import os
from datetime import timedelta

class Config:
    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'monitoring-system-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///monitoring.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # InfluxDB настройки
    INFLUXDB_HOST = 'localhost'
    INFLUXDB_PORT = 8086
    INFLUXDB_DATABASE = 'monitoring_metrics'
    
    # Настройки Telegram
    TELEGRAM_BOT_TOKEN = '8553079574:AAGUlS2j4t1khk6VwKU0fC3okki-vktSjQI'
    TELEGRAM_CHAT_IDS = ['830737763']
    
    # Настройки сервера
    SERVER_HOST = '10.10.10.222'
    SERVER_PORT = 5000
    
    # Настройки оповещений
    ALERT_CHECK_INTERVAL = 60  # seconds
    ALERT_COOLDOWN = 300  # 5 minutes between repeated alerts
    
    # Пороги для оповещений
    ALERT_THRESHOLDS = {
        'cpu_percent': 90,
        'memory_percent': 85,
        'disk_percent': 90,
        'service_stopped': True
    }

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}