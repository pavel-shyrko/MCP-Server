# MCP Server - C4 Architecture Diagrams

## Level 1: System Context Diagram

```mermaid
C4Context
    title System Context Diagram for MCP Server

    Person(user, "User", "Developer or AI system user")
    
    System(mcpServer, "MCP Server", "AI access to secure internal systems - bridges AI models with external resources")
    
    System_Ext(ollama, "Ollama", "Local LLM service running Mistral model")
    System_Ext(jsonplaceholder, "JSONPlaceholder", "External REST API for testing and prototyping")
    
    Rel(user, mcpServer, "Sends natural language queries", "HTTP/REST")
    Rel(mcpServer, ollama, "Sends prompts and receives AI responses", "HTTP/REST")
    Rel(mcpServer, jsonplaceholder, "Fetches posts and comments", "HTTP/REST")
    
    UpdateRelStyle(user, mcpServer, $textColor="blue", $lineColor="blue")
    UpdateRelStyle(mcpServer, ollama, $textColor="green", $lineColor="green")
    UpdateRelStyle(mcpServer, jsonplaceholder, $textColor="orange", $lineColor="orange")
```

## Level 2: Container Diagram

```mermaid
C4Container
    title Container Diagram for MCP Server

    Person(user, "User", "Developer or AI system user")
    
    Container_Boundary(mcpSystem, "MCP Server System") {
        Container(fastapi, "FastAPI Application", "Python, FastAPI", "Provides REST API endpoints with dependency injection and automatic documentation")
        Container(agents, "LLM Agent", "Python, httpx", "Orchestrates communication with Ollama and tool dispatching")
        Container(adapters, "Adapter Layer", "Python", "External API integration adapters following adapter pattern")
        Container(config, "Configuration Manager", "Python, Pydantic", "Environment-based configuration management")
    }
    
    Container_Boundary(docker, "Docker Environment") {
        Container(ollama, "Ollama Container", "Docker, Ollama", "LLM service running Mistral model with automated setup")
        Container(entrypoint, "Ollama Entrypoint", "Bash Script", "Automated Ollama server initialization and model download")
        ContainerDb(ollamaData, "Ollama Volume", "Docker Volume", "Persistent storage for Mistral model and configuration")
    }
    
    System_Ext(jsonplaceholder, "JSONPlaceholder API", "External REST API for testing")
    
    Rel(user, fastapi, "Sends HTTP requests", "JSON/HTTPS")
    Rel(fastapi, agents, "Delegates queries")
    Rel(fastapi, adapters, "Calls tools directly")
    Rel(fastapi, config, "Reads configuration")
    Rel(agents, ollama, "Sends prompts", "HTTP/REST")
    Rel(agents, fastapi, "Dispatches tool calls", "HTTP")
    Rel(adapters, jsonplaceholder, "Fetches data", "HTTP/REST")
    Rel(entrypoint, ollama, "Initializes and configures")
    Rel(ollama, ollamaData, "Stores model data")
    
    UpdateRelStyle(user, fastapi, $textColor="blue", $lineColor="blue")
    UpdateRelStyle(agents, ollama, $textColor="green", $lineColor="green")
    UpdateRelStyle(adapters, jsonplaceholder, $textColor="orange", $lineColor="orange")
    UpdateRelStyle(entrypoint, ollama, $textColor="purple", $lineColor="purple")
```

## Level 3: Component Diagram

```mermaid
C4Component
    title Component Diagram for MCP Server Application

    Container_Boundary(fastapi, "FastAPI Application Container") {
        Component(main, "Main Application", "FastAPI", "Application entry point with metadata configuration")
        Component(router, "API Router", "FastAPI Router", "Defines API endpoints with dependency injection")
        Component(dependencies, "Dependency Injection", "FastAPI Depends", "Provides settings and logger injection")
        
        Component(askEndpoint, "/ask Endpoint", "FastAPI Route", "Natural language query processing endpoint")
        Component(postEndpoint, "/post-call Endpoint", "FastAPI Route", "Direct post fetching tool endpoint")
        Component(commentsEndpoint, "/comments-call Endpoint", "FastAPI Route", "Direct comments fetching tool endpoint")
    }
    
    Container_Boundary(agents, "LLM Agent Container") {
        Component(llmAgent, "LLM Agent", "Python", "Orchestrates AI workflow and tool dispatching")
        Component(promptManager, "Prompt Manager", "Python", "Loads and manages system prompts from files")
    }
    
    Container_Boundary(adapters, "Adapter Layer Container") {
        Component(postAdapter, "Post Adapter", "Python, httpx", "Handles JSONPlaceholder post API integration")
        Component(commentsAdapter, "Comments Adapter", "Python, httpx", "Handles JSONPlaceholder comments API integration")
        Component(baseAdapter, "Base Adapter Pattern", "Python", "Common adapter interface and error handling")
    }
    
    Container_Boundary(config, "Configuration Container") {
        Component(settings, "Settings Manager", "Pydantic BaseSettings", "Environment-based configuration with .env file support")
        Component(envFiles, "Environment Files", ".env files", "Separate configs for local (.env.local) and Docker (.env.docker)")
        Component(logger, "Logger", "Python logging", "Centralized logging configuration")
    }
    
    Container_Boundary(external, "External Systems") {
        Component(ollama, "Ollama Service", "Ollama API", "Mistral model inference service")
        Component(jsonplaceholder, "JSONPlaceholder", "REST API", "External API for posts and comments")
    }
    
    Rel(main, router, "Includes router")
    Rel(router, dependencies, "Uses DI")
    Rel(dependencies, settings, "Injects settings")
    Rel(dependencies, logger, "Injects logger")
    
    Rel(askEndpoint, llmAgent, "Delegates query processing")
    Rel(postEndpoint, postAdapter, "Calls directly")
    Rel(commentsEndpoint, commentsAdapter, "Calls directly")
    
    Rel(llmAgent, promptManager, "Loads system prompts")
    Rel(llmAgent, ollama, "Sends AI requests")
    Rel(llmAgent, router, "Dispatches tool calls")
    
    Rel(postAdapter, jsonplaceholder, "HTTP GET /posts/{id}")
    Rel(commentsAdapter, jsonplaceholder, "HTTP GET /posts/{id}/comments")
    
    Rel(settings, envFiles, "Reads configuration")
    Rel(promptManager, envFiles, "Reads prompt files")
    
    UpdateRelStyle(askEndpoint, llmAgent, $textColor="green", $lineColor="green")
    UpdateRelStyle(llmAgent, ollama, $textColor="green", $lineColor="green")
    UpdateRelStyle(postAdapter, jsonplaceholder, $textColor="orange", $lineColor="orange")
    UpdateRelStyle(commentsAdapter, jsonplaceholder, $textColor="orange", $lineColor="orange")
```

## Architecture Patterns Used

### 1. **Dependency Injection Pattern**
- FastAPI's `Depends()` for settings and logger injection
- Improves testability and flexibility
- Allows easy mocking in tests

### 2. **Adapter Pattern**
- Separate adapters for each external API integration
- `jsonplaceholder_post.py` and `jsonplaceholder_comments.py`
- Consistent interface for external resource access

### 3. **Configuration Management Pattern**
- Environment-based configuration with Pydantic
- Separate `.env.local` and `.env.docker` files
- Type-safe configuration with validation

### 4. **Agent Pattern**
- LLM Agent orchestrates the AI workflow
- Dispatches to appropriate tools based on AI response
- Maintains conversation context

### 5. **Clean Architecture Principles**
- Separation of concerns across layers
- External dependencies isolated in adapters
- Configuration and logging centralized
- Business logic separated from infrastructure

## Data Flow

1. **User Request** → FastAPI Router
2. **Router** → Dependency Injection (Settings, Logger)
3. **Router** → LLM Agent (for `/ask` endpoint)
4. **LLM Agent** → Ollama (AI processing)
5. **LLM Agent** → Tool Dispatcher → Specific Adapter
6. **Adapter** → External API (JSONPlaceholder)
7. **Response** ← Back through the chain to User
