from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Server(db.Model):
    __tablename__ = 'servers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    ip_address = db.Column(db.String(45))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime)
    
    # Связи
    alerts = db.relationship('Alert', backref='server', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.ip_address,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # 'critical', 'warning', 'info'
    status = db.Column(db.String(20), default='active')  # 'active', 'resolved', 'acknowledged'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'metric_type': self.metric_type,
            'message': self.message,
            'severity': self.severity,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }

class AlertRule(db.Model):
    __tablename__ = 'alert_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)
    condition = db.Column(db.String(10), nullable=False)  # 'gt', 'lt', 'eq', 'neq'
    threshold = db.Column(db.Float, nullable=False)
    message_template = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    cooldown_minutes = db.Column(db.Integer, default=5)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'metric_type': self.metric_type,
            'condition': self.condition,
            'threshold': self.threshold,
            'message_template': self.message_template,
            'is_active': self.is_active,
            'cooldown_minutes': self.cooldown_minutes
        }