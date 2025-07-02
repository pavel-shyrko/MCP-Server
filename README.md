# MCP Server

MCP Server is a backend Python application that enables secure and standardized communication between AI models and external resources, such as databases, APIs, and file systems. It acts as a bridge, allowing AI agents to interact with these resources in a controlled and efficient manner, expanding the capabilities of AI systems.

This application has been fully reworked for modularity, extensibility, and maintainability. It features a plugin-based adapter system, robust authentication, logging, and seamless integration with LLM (Large Language Model) agents. The project is containerized for easy deployment.

## Key Features
- Modular adapter/plugin architecture for easy extension
- Secure authentication mechanisms
- LLM agent integration for advanced AI workflows
- Centralized logging
- Docker support for deployment

## Project Structure
```
docker-compose.yml        # Docker Compose configuration
Dockerfile                # Dockerfile for building the app image
requirements.txt          # Python dependencies
app/
    __init__.py
    auth.py               # Authentication logic
    config.py             # Configuration management
    llm_agent.py          # LLM agent integration
    logger.py             # Logging setup
    main.py               # Application entry point
    router.py             # API routing
    adapters/             # Adapter plugins for external resources
        __init__.py
        jsonplaceholder_comments.py
        jsonplaceholder_post.py
```

## Getting Started

### Prerequisites
- Docker
- Docker Compose
- Python 3.10+

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
- Configuration is managed via `app/config.py` and environment variables. Adjust as needed for your deployment.

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/pavel-shyrko/MCP-Server/blob/master/LICENSE) file for details.

## Author
Pavel Shyrko