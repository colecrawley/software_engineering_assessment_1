import asyncio
import httpx
import websockets
import json
from typing import Optional, Dict, Any
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from .config import Config
import logging

logger = logging.getLogger(__name__)

def is_retryable_exception(exception):
    # check if exception needs retry
    if isinstance(exception, httpx.TimeoutException):
        return True
    if isinstance(exception, httpx.ConnectError):
        return True
    if hasattr(exception, 'response') and exception.response.status_code == 503:
        return True
    return False

class RobotClient:
    # robot client with retry logic
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.base_url = Config.ROBOT_API_URL
        self.ws_url = Config.ROBOT_WS_URL
        self.connection_status = "disconnected"
        self.websocket = None
        self._setup_client()
    
    def _setup_client(self):
        # setup http client
        self.client = httpx.AsyncClient(
            timeout=Config.CONNECTION_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=5)
        )
    
    @retry(
        stop=stop_after_attempt(Config.RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception(is_retryable_exception)
    )
    async def get_status(self) -> Optional[Dict[str, Any]]:
        # robot status
        try:
            response = await self.client.get(f"{self.base_url}/api/status")
            response.raise_for_status()
            self.connection_status = "connected"
            return response.json()
        except Exception as e:
            self.connection_status = "error"
            logger.error(f"Failed to get status: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(Config.RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception(is_retryable_exception)
    )
    async def move_robot(self, x: int, y: int) -> Dict[str, Any]:
        # move command
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("Coordinates must be integers")
        if x < 0 or x > 20 or y < 0 or y > 20:
            raise ValueError("Coordinates must be between 0 and 20")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/move",
                json={"x": x, "y": y}
            )
            response.raise_for_status()
            self.connection_status = "connected"
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                self.connection_status = "service_unavailable"
            logger.error(f"Move command failed: {e}")
            raise
        except Exception as e:
            self.connection_status = "error"
            logger.error(f"Move command error: {e}")
            raise
    
    async def get_map(self) -> Optional[Dict[str, Any]]:
        # env map
        try:
            response = await self.client.get(f"{self.base_url}/api/map")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get map: {e}")
            return None
    
    async def get_sensors(self) -> Optional[Dict[str, Any]]:
        # sensor
        try:
            response = await self.client.get(f"{self.base_url}/api/sensor")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get sensors: {e}")
            return None
    
    async def reset_robot(self) -> bool:
        # reset
        try:
            response = await self.client.post(f"{self.base_url}/api/reset")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to reset robot: {e}")
            return False
    
    async def connect_websocket(self):
        # websocket
        try:
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            self.connection_status = "connected"
            return True
        except Exception as e:
            self.connection_status = "error"
            logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def listen_telemetry(self):
        if not self.websocket:
            await self.connect_websocket()
        
        try:
            while True:
                message = await self.websocket.recv()
                data = json.loads(message)
                yield data
        except websockets.exceptions.ConnectionClosed:
            self.connection_status = "disconnected"
            logger.warning("WebSocket connection closed, reconnecting...")
            await asyncio.sleep(1)
            await self.connect_websocket()
        except Exception as e:
            logger.error(f"Telemetry error: {e}")
            self.connection_status = "error"
    
    async def close(self):
        if self.websocket:
            await self.websocket.close()
        await self.client.aclose()
    
    def get_connection_status(self) -> str:
        return self.connection_status