from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
import asyncio

from .config import Config
from .models import Base, User, UserRole
from .auth import verify_password, get_password_hash, create_access_token, get_current_user, role_required
from .robot_client import RobotClient
from .audit_logger import AuditLogger
from .database import get_db, engine
from pydantic import BaseModel

# fastapi
app = FastAPI(title="Robot Management System", version="1.0.0")

# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:80",
        "http://frontend:80",
        "http://frontend:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

Base.metadata.create_all(bind=engine)

# init components
robot_client = RobotClient()
audit_logger = AuditLogger()

# pydantic model
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole = UserRole.VIEWER

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class MoveCommand(BaseModel):
    x: int
    y: int

# auth endpoint
@app.post("/api/register", response_model=Token)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        role=user.role
    )
    db.add(db_user)
    db.commit()
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/user/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value
    }

# robot control endpoint
@app.get("/api/robot/status")
async def get_robot_status(current_user: User = Depends(get_current_user)):
    try:
        status = await robot_client.get_status()
        connection_status = robot_client.get_connection_status()
        if status:
            pass
        return {
            **(status or {}),
            "connection_status": connection_status
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Robot unreachable: {str(e)}")

@app.post("/api/robot/move")
async def move_robot(
    command: MoveCommand,
    current_user: User = Depends(role_required(UserRole.COMMANDER)),
    db: Session = Depends(get_db)
):
    try:
        response = await robot_client.move_robot(command.x, command.y)
        audit_logger.log_command(
            db,
            current_user.username,
            "MOVE",
            f"x={command.x}, y={command.y}",
            str(response),
            success=True
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        audit_logger.log_command(
            db,
            current_user.username,
            "MOVE",
            f"x={command.x}, y={command.y}",
            str(e),
            success=False
        )
        raise HTTPException(status_code=503, detail=f"Failed to move robot: {str(e)}")

@app.post("/api/robot/reset")
async def reset_robot(
    current_user: User = Depends(role_required(UserRole.COMMANDER)),
    db: Session = Depends(get_db)
):
    try:
        success = await robot_client.reset_robot()
        audit_logger.log_command(
            db,
            current_user.username,
            "RESET",
            "Reset simulation",
            "Success" if success else "Failed",
            success=success
        )
        if success:
            return {"message": "Robot reset successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reset robot")
    except Exception as e:
        audit_logger.log_command(
            db,
            current_user.username,
            "RESET",
            "Reset simulation",
            str(e),
            success=False
        )
        raise HTTPException(status_code=503, detail=f"Reset failed: {str(e)}")

@app.get("/api/robot/map")
async def get_robot_map(current_user: User = Depends(get_current_user)):
    map_data = await robot_client.get_map()
    if map_data:
        return map_data
    raise HTTPException(status_code=503, detail="Failed to retrieve map")

@app.get("/api/robot/sensors")
async def get_robot_sensors(current_user: User = Depends(get_current_user)):
    sensor_data = await robot_client.get_sensors()
    if sensor_data:
        return sensor_data
    raise HTTPException(status_code=503, detail="Failed to retrieve sensor data")

@app.get("/api/audit/commands")
async def get_command_history(
    limit: int = 100,
    current_user: User = Depends(role_required(UserRole.COMMANDER)),
    db: Session = Depends(get_db)
):
    history = audit_logger.get_command_history(db, limit)
    return [
        {
            "timestamp": cmd.timestamp.isoformat(),
            "username": cmd.username,
            "command_type": cmd.command_type,
            "command_data": cmd.command_data,
            "robot_response": cmd.robot_response,
            "success": bool(cmd.success)
        }
        for cmd in history
    ]

@app.get("/api/audit/telemetry")
async def get_telemetry_history(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history = audit_logger.get_telemetry_history(db, limit)
    return [
        {
            "timestamp": tele.timestamp.isoformat(),
            "position": {"x": tele.position_x, "y": tele.position_y},
            "battery": tele.battery_level,
            "status": tele.robot_status
        }
        for tele in history
    ]

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    db = next(get_db())
    try:
        async for telemetry_data in robot_client.listen_telemetry():
            try:
                audit_logger.log_telemetry(
                    db,
                    position=telemetry_data.get("position", {}),
                    battery=telemetry_data.get("battery", 0),
                    status=telemetry_data.get("status", "unknown")
                )
            except Exception:
                pass
            telemetry_data["connection_status"] = robot_client.get_connection_status()
            await websocket.send_json(telemetry_data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        db.close()

@app.on_event("shutdown")
async def shutdown_event():
    await robot_client.close()

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "robot_connection": robot_client.get_connection_status()
    }