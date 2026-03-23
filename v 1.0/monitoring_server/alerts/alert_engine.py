import logging
from datetime import datetime
from models.database import db, AlertRule

class AlertEngine:
    def __init__(self, telegram_manager):
        self.telegram_manager = telegram_manager
        # Правила будут инициализированы при первом использовании
        self.rules_initialized = False
    
    def ensure_rules_initialized(self):
        """Инициализация правил при первом использовании"""
        if not self.rules_initialized:
            self.setup_default_rules()
            self.rules_initialized = True
    
    def setup_default_rules(self):
        """Создание правил по умолчанию если их нет"""
        try:
            if AlertRule.query.count() == 0:
                default_rules = [
                    AlertRule(
                        name="High CPU Usage",
                        metric_type="cpu_percent",
                        condition="gt",
                        threshold=90.0,
                        message_template="CPU usage is {value}% (threshold: {threshold}%)",
                        cooldown_minutes=5
                    ),
                    AlertRule(
                        name="High Memory Usage", 
                        metric_type="memory_percent",
                        condition="gt",
                        threshold=85.0,
                        message_template="Memory usage is {value}% (threshold: {threshold}%)",
                        cooldown_minutes=5
                    ),
                    AlertRule(
                        name="Low Disk Space",
                        metric_type="disk_percent", 
                        condition="gt",
                        threshold=90.0,
                        message_template="Disk {drive} usage is {value}% (threshold: {threshold}%)",
                        cooldown_minutes=30
                    ),
                    AlertRule(
                        name="Service Stopped",
                        metric_type="service_status",
                        condition="eq", 
                        threshold=0,
                        message_template="Service {service_name} is stopped",
                        cooldown_minutes=1
                    )
                ]
                
                db.session.bulk_save_objects(default_rules)
                db.session.commit()
                logging.info("Default alert rules created")
        except Exception as e:
            logging.error(f"Error setting up default rules: {e}")
    
    def check_metrics(self, metrics_data):
        """Проверка метрик на нарушения правил"""
        try:
            self.ensure_rules_initialized()
            
            server_name = metrics_data['agent_name']
            
            # Проверка CPU
            self._check_cpu(server_name, metrics_data['cpu_percent'])
            
            # Проверка памяти
            memory_percent = metrics_data['memory_usage']['percent']
            self._check_memory(server_name, memory_percent)
            
            # Проверка дисков
            self._check_disks(server_name, metrics_data['disk_usage'])
            
            # Проверка служб
            self._check_services(server_name, metrics_data['services_status'])
            
        except Exception as e:
            logging.error(f"Error in alert engine: {e}")
    
    def _check_cpu(self, server_name, cpu_percent):
        rule = AlertRule.query.filter_by(metric_type="cpu_percent", is_active=True).first()
        if rule and cpu_percent > rule.threshold:
            if self.telegram_manager.should_send_alert(server_name, "cpu_percent", rule.cooldown_minutes):
                message = rule.message_template.format(value=cpu_percent, threshold=rule.threshold)
                self.telegram_manager.send_alert(server_name, "CPU", message, "warning")
                self.telegram_manager.mark_alert_sent(server_name, "cpu_percent")
    
    def _check_memory(self, server_name, memory_percent):
        rule = AlertRule.query.filter_by(metric_type="memory_percent", is_active=True).first()
        if rule and memory_percent > rule.threshold:
            if self.telegram_manager.should_send_alert(server_name, "memory_percent", rule.cooldown_minutes):
                message = rule.message_template.format(value=memory_percent, threshold=rule.threshold)
                self.telegram_manager.send_alert(server_name, "Memory", message, "warning")
                self.telegram_manager.mark_alert_sent(server_name, "memory_percent")
    
    def _check_disks(self, server_name, disk_usage):
        rule = AlertRule.query.filter_by(metric_type="disk_percent", is_active=True).first()
        if rule:
            for drive, usage in disk_usage.items():
                if 'error' not in usage and usage['percent'] > rule.threshold:
                    alert_key = f"disk_{drive}"
                    if self.telegram_manager.should_send_alert(server_name, alert_key, rule.cooldown_minutes):
                        message = rule.message_template.format(
                            drive=drive, 
                            value=usage['percent'], 
                            threshold=rule.threshold
                        )
                        self.telegram_manager.send_alert(server_name, f"Disk {drive}", message, "critical")
                        self.telegram_manager.mark_alert_sent(server_name, alert_key)
    
    def _check_services(self, server_name, services_status):
        rule = AlertRule.query.filter_by(metric_type="service_status", is_active=True).first()
        if rule:
            for service_name, status in services_status.items():
                if status.get('status') == 'stopped':
                    alert_key = f"service_{service_name}"
                    if self.telegram_manager.should_send_alert(server_name, alert_key, rule.cooldown_minutes):
                        message = rule.message_template.format(service_name=service_name)
                        self.telegram_manager.send_alert(server_name, f"Service {service_name}", message, "critical")
                        self.telegram_manager.mark_alert_sent(server_name, alert_key)