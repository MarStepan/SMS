from flask import jsonify, request
from datetime import datetime
from models.database import db, Server, Alert
from models.influx_manager import InfluxDBManager
from alerts.alert_engine import AlertEngine
import logging

def register_endpoints(app, telegram_manager, influx_manager, alert_engine):
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Проверка здоровья сервера"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    
    @app.route('/api/metrics', methods=['POST'])
    def receive_metrics():
        """Прием метрик от агентов"""
        try:
            metrics_data = request.get_json()
            
            if not metrics_data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            # Валидация обязательных полей
            required_fields = ['agent_name', 'timestamp', 'cpu_percent']
            for field in required_fields:
                if field not in metrics_data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Сохранение/обновление информации о сервере
            server = Server.query.filter_by(name=metrics_data['agent_name']).first()
            if not server:
                server = Server(
                    name=metrics_data['agent_name'],
                    description=f"Auto-registered at {datetime.utcnow()}"
                )
                db.session.add(server)
            
            server.last_seen = datetime.utcnow()
            db.session.commit()
            
            # Запись метрик в InfluxDB
            success = influx_manager.write_metrics(metrics_data)
            if not success:
                logging.error("Failed to write metrics to InfluxDB")
            
            # Проверка метрик на оповещения
            alert_engine.check_metrics(metrics_data)
            
            return jsonify({
                'status': 'success',
                'message': 'Metrics received and processed',
                'server_id': server.id
            })
            
        except Exception as e:
            logging.error(f"Error processing metrics: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/servers', methods=['GET'])
    def get_servers():
        """Получение списка серверов"""
        try:
            servers = Server.query.all()
            return jsonify({
                'servers': [server.to_dict() for server in servers]
            })
        except Exception as e:
            logging.error(f"Error getting servers: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/servers/<int:server_id>', methods=['GET'])
    def get_server(server_id):
        """Получение информации о конкретном сервере"""
        try:
            server = Server.query.get_or_404(server_id)
            return jsonify(server.to_dict())
        except Exception as e:
            logging.error(f"Error getting server: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/alerts', methods=['GET'])
    def get_alerts():
        """Получение списка оповещений"""
        try:
            status = request.args.get('status', 'active')
            limit = request.args.get('limit', 50, type=int)
            
            alerts = Alert.query.filter_by(status=status).order_by(
                Alert.created_at.desc()
            ).limit(limit).all()
            
            return jsonify({
                'alerts': [alert.to_dict() for alert in alerts]
            })
        except Exception as e:
            logging.error(f"Error getting alerts: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
    def resolve_alert(alert_id):
        """Разрешение оповещения"""
        try:
            alert = Alert.query.get_or_404(alert_id)
            alert.status = 'resolved'
            alert.resolved_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'status': 'success', 'message': 'Alert resolved'})
        except Exception as e:
            logging.error(f"Error resolving alert: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/metrics/<server_name>', methods=['GET'])
    def get_server_metrics(server_name):
        """Получение метрик сервера"""
        try:
            time_range = request.args.get('range', '1h')
            measurement = request.args.get('measurement', 'cpu')
            
            metrics = influx_manager.query_metrics(measurement, server_name, time_range)
            
            return jsonify({
                'server': server_name,
                'measurement': measurement,
                'time_range': time_range,
                'metrics': metrics
            })
        except Exception as e:
            logging.error(f"Error getting metrics: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/telegram/test', methods=['POST'])
    def test_telegram():
        """Тестовая отправка сообщения в Telegram"""
        try:
            data = request.get_json()
            message = data.get('message', 'Test message from monitoring system')
            
            telegram_manager.send_alert(
                'Test Server',
                'test',
                message,
                'info'
            )
            
            return jsonify({'status': 'success', 'message': 'Test message sent'})
        except Exception as e:
            logging.error(f"Error sending test message: {e}")
            return jsonify({'error': 'Internal server error'}), 500