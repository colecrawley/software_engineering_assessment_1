import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.robot_client import RobotClient, HttpClientFactory
from app.audit_logger import AuditLogger
from app.auth import get_password_hash, verify_password, create_access_token

@pytest.mark.asyncio
async def test_move_robot_invalid_coordinates():
    client = RobotClient()
    with pytest.raises(ValueError) as exc_info:
        await client.move_robot(-1, 5)
    assert "Coordinates must be between 0 and 20" in str(exc_info.value)
    
    with pytest.raises(ValueError) as exc_info:
        await client.move_robot(25, 5)
    assert "Coordinates must be between 0 and 20" in str(exc_info.value)

@pytest.mark.asyncio
async def test_move_robot_non_integer():
    client = RobotClient()
    with pytest.raises(ValueError) as exc_info:
        await client.move_robot(5.5, 5)
    assert "Coordinates must be integers" in str(exc_info.value)

@pytest.mark.asyncio
async def test_move_robot_negative_y():
    client = RobotClient()
    with pytest.raises(ValueError, match="Coordinates must be between 0 and 20"):
        await client.move_robot(5, -1)

@pytest.mark.asyncio
async def test_move_robot_y_exceeds_max():
    client = RobotClient()
    with pytest.raises(ValueError, match="Coordinates must be between 0 and 20"):
        await client.move_robot(5, 21)

@pytest.mark.asyncio
async def test_move_robot_float_y():
    client = RobotClient()
    with pytest.raises(ValueError, match="Coordinates must be integers"):
        await client.move_robot(5, 3.14)

@pytest.mark.asyncio
async def test_move_robot_x_exceeds_max():
    client = RobotClient()
    with pytest.raises(ValueError, match="Coordinates must be between 0 and 20"):
        await client.move_robot(21, 5)

@pytest.mark.asyncio
async def test_move_robot_boundary_origin():
    client = RobotClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "moving", "position": {"x": 0, "y": 0}}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
        result = await client.move_robot(0, 0)
    assert result["position"]["x"] == 0
    assert result["position"]["y"] == 0

@pytest.mark.asyncio
async def test_move_robot_boundary_max():
    client = RobotClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "moving", "position": {"x": 20, "y": 20}}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "post", new=AsyncMock(return_value=mock_response)):
        result = await client.move_robot(20, 20)
    assert result["position"]["x"] == 20
    assert result["position"]["y"] == 20

@pytest.mark.asyncio
async def test_get_status_sets_connected():
    client = RobotClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"battery": 80, "status": "IDLE", "position": {"x": 0, "y": 0}}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "get", new=AsyncMock(return_value=mock_response)):
        await client.get_status()
    assert client.get_connection_status() == "connected"

@pytest.mark.asyncio
async def test_get_status_sets_error_on_connect_failure():
    client = RobotClient()
    with patch.object(client.client, "get", new=AsyncMock(side_effect=httpx.ConnectError("refused"))):
        with pytest.raises(Exception):
            await client.get_status()
    assert client.get_connection_status() == "error"

def test_robot_client_singleton():
    a = RobotClient()
    b = RobotClient()
    assert a is b

def test_audit_logger_singleton():
    a = AuditLogger()
    b = AuditLogger()
    assert a is b

def test_factory_creates_async_client():
    client = HttpClientFactory.create(timeout=5)
    assert isinstance(client, httpx.AsyncClient)

def test_factory_test_client_accepts_transport():
    transport = httpx.MockTransport(handler=lambda r: httpx.Response(200))
    client = HttpClientFactory.create_test_client(transport=transport)
    assert isinstance(client, httpx.AsyncClient)

def test_log_command_success_flag():
    logger = AuditLogger()
    mock_db = MagicMock()

    entry = logger.log_command(
        mock_db, "testuser", "MOVE", "x=5, y=3", "OK", success=True
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert entry.success == 1
    assert entry.username == "testuser"
    assert entry.command_type == "MOVE"

def test_log_command_failure_flag():
    logger = AuditLogger()
    mock_db = MagicMock()

    entry = logger.log_command(
        mock_db, "testuser", "MOVE", "x=5, y=3", "Connection refused", success=False
    )
    assert entry.success == 0

def test_log_telemetry_field_mapping():
    logger = AuditLogger()
    mock_db = MagicMock()

    entry = logger.log_telemetry(
        mock_db,
        position={"x": 3, "y": 7},
        battery=65.5,
        status="IDLE"
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert entry.position_x == 3
    assert entry.position_y == 7
    assert entry.battery_level == 65.5
    assert entry.robot_status == "IDLE"

def test_get_command_history_no_filter():
    logger = AuditLogger()
    mock_db = MagicMock()
    mock_db.query.return_value \
        .order_by.return_value \
        .limit.return_value \
        .all.return_value = []

    result = logger.get_command_history(mock_db, limit=10)
    assert result == []

def test_get_command_history_with_username_filter():
    logger = AuditLogger()
    mock_db = MagicMock()
    chain = mock_db.query.return_value.order_by.return_value
    chain.filter.return_value.limit.return_value.all.return_value = []

    result = logger.get_command_history(mock_db, limit=5, username="alice")
    assert result == []
    chain.filter.assert_called_once()

def test_password_hash_and_verify():
    hashed = get_password_hash("securepassword123")
    assert verify_password("securepassword123", hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_create_access_token_claims():
    from jose import jwt
    from app.config import Config

    token = create_access_token(data={"sub": "alice"})
    payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
    assert payload["sub"] == "alice"
    assert "exp" in payload