import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # robot api config
    ROBOT_API_URL = os.getenv('ROBOT_API_URL', 'http://robot_sim:5000')
    ROBOT_WS_URL = os.getenv('ROBOT_WS_URL', 'ws://robot_sim:5000/ws/telemetry')
    
    # db config
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@db:5432/robot_db')
    
    # security
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # rdis config
    REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    
    # app settings
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2
    CONNECTION_TIMEOUT = 10
