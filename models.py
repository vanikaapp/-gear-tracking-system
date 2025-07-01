from datetime import datetime
from app import db
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

class Trailer(db.Model):
    __tablename__ = 'trailers'
    
    id = db.Column(Integer, primary_key=True)
    trailer_id = db.Column(String(50), unique=True, nullable=False)
    location = db.Column(String(100))
    status = db.Column(String(50), default='Available')
    notes = db.Column(Text)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    gear_snapshots = relationship('GearSnapshot', back_populates='trailer', cascade='all, delete-orphan')
    driver_assignments = relationship('DriverAssignment', back_populates='trailer', cascade='all, delete-orphan')
    audit_logs = relationship('AuditLog', back_populates='trailer', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Trailer {self.trailer_id}>'

class GearSnapshot(db.Model):
    __tablename__ = 'gear_snapshots'
    
    id = db.Column(Integer, primary_key=True)
    trailer_id = db.Column(Integer, ForeignKey('trailers.id'), nullable=False)
    date_recorded = db.Column(DateTime, default=datetime.utcnow)
    gear_type = db.Column(String(100), nullable=False)
    quantity = db.Column(Integer, default=1)
    condition = db.Column(String(50), default='Good')
    notes = db.Column(Text)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trailer = relationship('Trailer', back_populates='gear_snapshots')
    
    def __repr__(self):
        return f'<GearSnapshot {self.gear_type} on {self.trailer.trailer_id}>'

class DriverAssignment(db.Model):
    __tablename__ = 'driver_assignments'
    
    id = db.Column(Integer, primary_key=True)
    trailer_id = db.Column(Integer, ForeignKey('trailers.id'), nullable=False)
    driver_name = db.Column(String(100), nullable=False)
    assigned_date = db.Column(DateTime, default=datetime.utcnow)
    returned_date = db.Column(DateTime)
    notes = db.Column(Text)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trailer = relationship('Trailer', back_populates='driver_assignments')
    
    def __repr__(self):
        return f'<DriverAssignment {self.driver_name} -> {self.trailer.trailer_id}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(Integer, primary_key=True)
    trailer_id = db.Column(Integer, ForeignKey('trailers.id'), nullable=False)
    action_type = db.Column(String(50), nullable=False)  # 'ADD', 'REMOVE', 'LOSS', 'SWAP', 'UPDATE'
    gear_type = db.Column(String(100))
    quantity_change = db.Column(Integer, default=0)
    old_condition = db.Column(String(50))
    new_condition = db.Column(String(50))
    description = db.Column(Text, nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trailer = relationship('Trailer', back_populates='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action_type} on {self.trailer.trailer_id}>'
