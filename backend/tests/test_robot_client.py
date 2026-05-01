import pytest
from app.robot_client import RobotClient

# unit test, input validation
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