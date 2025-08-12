# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Quick Start
```bash
chmod +x run.sh
./run.sh
```

### Manual Development
```bash
# Install dependencies
uv sync

# Start development server
cd backend && uv run uvicorn app:app --reload --port 8000

# Access application
# Web Interface: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Environment Setup
Create a `.env` file in the root directory with:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Architecture Overview

This is a full-stack RAG (Retrieval-Augmented Generation) system with the following architecture:

### Backend Structure (Python/FastAPI)
- **`app.py`**: FastAPI application entry point with CORS, static file serving, and API endpoints
- **`rag_system.py`**: Main orchestrator connecting all components
- **`vector_store.py`**: ChromaDB integration for semantic search using sentence transformers
- **`ai_generator.py`**: Anthropic Claude API integration for response generation
- **`document_processor.py`**: Text chunking and course document parsing
- **`search_tools.py`**: Tool-based search system for AI function calling
- **`session_manager.py`**: Conversation history management
- **`models.py`**: Data models for Course, Lesson, and CourseChunk
- **`config.py`**: Environment variables and configuration management

### Frontend Structure
- **`frontend/index.html`**: Web interface for user queries
- **`frontend/script.js`**: JavaScript for API communication and UI
- **`frontend/style.css`**: Styling for the web interface

### Key Components Integration
1. **Document Processing**: Text files in `/docs` are chunked and embedded using sentence transformers
2. **Vector Storage**: ChromaDB stores course metadata and content chunks with semantic embeddings
3. **AI Generation**: Claude Sonnet 4 uses function calling with search tools to query the vector store
4. **Session Management**: Conversation history maintained for context-aware responses
5. **Web Interface**: FastAPI serves both API endpoints and static frontend files

### Configuration
- Chunk size: 800 characters with 100 character overlap
- Max search results: 5 per query
- Conversation history: 2 messages per session
- Embedding model: all-MiniLM-L6-v2
- AI model: claude-sonnet-4-20250514

### API Endpoints
- `POST /api/query`: Process user queries with session management
- `GET /api/courses`: Get course statistics and analytics
- Static file serving for frontend at root path

The system automatically loads documents from the `/docs` folder on startup and supports adding new course materials at runtime.