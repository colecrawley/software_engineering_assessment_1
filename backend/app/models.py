from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

Base = declarative_base()

# user roles
class UserRole(enum.Enum):
    VIEWER = "viewer"
    COMMANDER = "commander"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommandLog(Base):
    __tablename__ = 'command_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    username = Column(String(50), nullable=False)
    command_type = Column(String(50), nullable=False)
    command_data = Column(String(255))
    robot_response = Column(String(255))
    success = Column(Integer, default=0)

class TelemetryLog(Base):
    __tablename__ = 'telemetry_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    position_x = Column(Integer)
    position_y = Column(Integer)
    battery_level = Column(Float)
    robot_status = Column(String(50))