import pytest
from app.robot_client import RobotClient

@pytest.mark.asyncio
async def test_robot_status_integration():
    client = RobotClient()
    try:
        status = await client.get_status()
        assert "position" in status
        assert "battery" in status
    finally:
        await client.close()