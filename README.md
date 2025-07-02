# MCP Server

MCP Server is a backend application that enables secure and standardized communication between AI models and external resources, such as databases, APIs, and file systems. It acts as a bridge, allowing AI agents to interact with these resources in a controlled and efficient manner, expanding the capabilities of AI systems.

This application is built with Python and is designed for modularity and extensibility. It includes authentication, logging, and LLM (Large Language Model) agent integration, and is ready for deployment with Docker.

## Features
- Modular design with adapters (e.g., booking)
- Authentication support
- LLM (Large Language Model) agent integration
- Logging
- Dockerized for easy deployment

## Project Structure
```
docker-compose.yml        # Docker Compose configuration
Dockerfile                # Dockerfile for building the app image
requirements.txt          # Python dependencies
app/
    __init__.py
    auth.py               # Authentication logic
    llm_agent.py          # LLM agent integration
    logger.py             # Logging setup
    main.py               # Application entry point
    router.py             # API routing
    adapters/
        __init__.py
        booking.py        # Booking adapter
```

## Getting Started

### Prerequisites
- Docker
- Docker Compose

### Build and Run with Docker
```
docker-compose up --build
```

### Local Development
1. Install dependencies:
    ```
    pip install -r requirements.txt
    ```
2. Run the application:
    ```
    python app/main.py
    ```

## Configuration
- Environment variables and configuration can be set in the Docker Compose file or as needed in the code.

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/pavel-shyrko/MCP-Server/blob/master/LICENSE) file for details.

## Author
Pavel Shyrko