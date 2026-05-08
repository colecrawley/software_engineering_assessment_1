# Robot Management System — CMP9134

A web-based Ground Control Station for monitoring and controlling a virtual autonomous robot.

## Quick Start

Run setup script (generates .env and starts all containers):

    .\setup.ps1

Or manually:

    docker-compose up --build

Then open http://localhost:3000 in your browser.

## Services

- Dashboard: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Robot simulator API: http://localhost:5000/docs

## Credentials

Register at http://localhost:3000. Choose Commander role to control the robot, or Viewer for read-only access.

## Project Structure

    backend/
      app/
        main.py           FastAPI routes
        robot_client.py   HTTP/WebSocket robot integration
        audit_logger.py   Command and telemetry logging
        auth.py           JWT authentication and RBAC
        models.py         SQLAlchemy database models
        config.py         Environment configuration
      tests/
        test_robot_client.py   22 unit tests
        test_integration.py    Integration test
    frontend/
      index.html          Dashboard UI
    docker-compose.yml
    setup.ps1

## Running Tests

    docker-compose exec backend pytest tests/ -v

## CI/CD

The GitHub Actions pipeline activates whenever someone pushes code to the main branch or the develop branch. The system performs complete testing after which it transfers test results to Codecov and it creates and uploads Docker images to GHCR when developers merge code into the main branch.