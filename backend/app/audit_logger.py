from sqlalchemy.orm import Session
from datetime import datetime
from .models import CommandLog, TelemetryLog

class AuditLogger:

    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def log_command(self, db: Session, username: str, command_type: str, 
                    command_data: str, robot_response: str = None, success: bool = True):
        # log command sent to robot
        log_entry = CommandLog(
            timestamp=datetime.utcnow(),
            username=username,
            command_type=command_type,
            command_data=command_data,
            robot_response=robot_response,
            success=1 if success else 0
        )
        db.add(log_entry)
        db.commit()
        return log_entry
    
    def log_telemetry(self, db: Session, position: dict, battery: float, status: str):
        # log telemetry data
        log_entry = TelemetryLog(
            timestamp=datetime.utcnow(),
            position_x=position.get('x', 0),
            position_y=position.get('y', 0),
            battery_level=battery,
            robot_status=status
        )
        db.add(log_entry)
        db.commit()
        return log_entry
    
    def get_command_history(self, db: Session, limit: int = 100, username: str = None):
        # cmd history
        query = db.query(CommandLog).order_by(CommandLog.timestamp.desc())
        if username:
            query = query.filter(CommandLog.username == username)
        return query.limit(limit).all()
    
    def get_telemetry_history(self, db: Session, limit: int = 100):
        # get tel data
        return db.query(TelemetryLog).order_by(TelemetryLog.timestamp.desc()).limit(limit).all()