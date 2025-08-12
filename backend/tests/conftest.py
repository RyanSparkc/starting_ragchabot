import pytest
import os
import sys
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from rag_system import RAGSystem
from config import Config


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock(spec=Config)
    config.GEMINI_API_KEY = "test_key"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_SEARCH_RESULTS = 5
    config.MAX_CONVERSATION_HISTORY = 2
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.AI_MODEL = "gemini-2.5-flash"
    config.CHROMADB_PATH = ":memory:"
    return config


@pytest.fixture
def mock_rag_system(mock_config):
    """Mock RAG system for testing"""
    with patch('rag_system.RAGSystem') as MockRAGSystem:
        mock_rag = Mock(spec=RAGSystem)
        mock_rag.config = mock_config
        
        # Mock session manager
        mock_rag.session_manager = Mock()
        mock_rag.session_manager.create_session.return_value = "test_session_id"
        
        # Mock query method
        mock_rag.query.return_value = ("Test answer", ["Test source 1", "Test source 2"])
        
        # Mock analytics method
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Test Course 1", "Test Course 2"]
        }
        
        # Mock document loading
        mock_rag.add_course_folder.return_value = (2, 10)
        
        MockRAGSystem.return_value = mock_rag
        yield mock_rag


@pytest.fixture
def test_client(mock_rag_system):
    """FastAPI test client with mocked dependencies"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from app import QueryRequest, QueryResponse, CourseStats
    
    # Create a test app without static file mounting
    test_app = FastAPI(title="Course Materials RAG System", root_path="")
    
    # Add middleware
    test_app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )
    
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Add API endpoints without importing the full app
    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
    
    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
    
    yield TestClient(test_app)


@pytest.fixture
def sample_query_request():
    """Sample query request data"""
    return {
        "query": "What is machine learning?",
        "session_id": "test_session_id"
    }


@pytest.fixture
def sample_query_request_without_session():
    """Sample query request without session ID"""
    return {
        "query": "What is machine learning?"
    }


@pytest.fixture
def mock_gemini_api():
    """Mock Google Gemini API responses"""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_response = Mock()
        mock_response.text = "Test response from Gemini"
        
        mock_chat = Mock()
        mock_chat.send_message.return_value = mock_response
        
        mock_model_instance = Mock()
        mock_model_instance.start_chat.return_value = mock_chat
        mock_model.return_value = mock_model_instance
        
        yield mock_model


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client and collection"""
    with patch('chromadb.Client') as mock_client:
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "documents": [["Document 1 content", "Document 2 content"]],
            "metadatas": [[{"course": "Course 1"}, {"course": "Course 2"}]],
            "distances": [[0.1, 0.2]]
        }
        mock_collection.count.return_value = 10
        
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_client_instance.list_collections.return_value = [
            Mock(name="test_collection")
        ]
        
        mock_client.return_value = mock_client_instance
        yield mock_client_instance


@pytest.fixture
def mock_sentence_transformer():
    """Mock sentence transformer model"""
    with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_transformer.return_value = mock_model
        yield mock_model


@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return [
        {
            "content": "Machine learning is a subset of artificial intelligence.",
            "metadata": {"course": "AI Basics", "lesson": "Introduction"}
        },
        {
            "content": "Deep learning uses neural networks with multiple layers.",
            "metadata": {"course": "AI Basics", "lesson": "Advanced Topics"}
        }
    ]


@pytest.fixture(autouse=True)
def cleanup_test_environment():
    """Cleanup test environment after each test"""
    yield
    # Clean up any test artifacts
    if os.path.exists("test_chroma_db"):
        import shutil
        shutil.rmtree("test_chroma_db", ignore_errors=True)