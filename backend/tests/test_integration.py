import pytest
from app.robot_client import RobotClient

@pytest.mark.asyncio
async def test_robot_status_integration():
    # skip if running in github ci
    import os
    if os.getenv("CI") == "true":
        pytest.skip("Integration test skipped in CI (robot simulator not available)")
    
    client = RobotClient()
    try:
        status = await client.get_status()
        assert "position" in status
        assert "battery" in status
    finally:
        await client.close()