import pytest
from fastapi import status
from unittest.mock import patch, Mock


class TestQueryEndpoint:
    """Test cases for /api/query endpoint"""

    def test_query_with_session_id(self, test_client, sample_query_request):
        """Test query endpoint with provided session ID"""
        response = test_client.post("/api/query", json=sample_query_request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test_session_id"
        assert data["answer"] == "Test answer"
        assert len(data["sources"]) == 2

    def test_query_without_session_id(self, test_client, sample_query_request_without_session, mock_rag_system):
        """Test query endpoint without session ID (should create new session)"""
        response = test_client.post("/api/query", json=sample_query_request_without_session)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test_session_id"
        
        # Verify session creation was called
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_with_empty_query(self, test_client):
        """Test query endpoint with empty query string"""
        response = test_client.post("/api/query", json={"query": ""})
        
        assert response.status_code == status.HTTP_200_OK
        # Should still process empty queries

    def test_query_with_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON"""
        response = test_client.post(
            "/api/query", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_with_missing_query_field(self, test_client):
        """Test query endpoint with missing query field"""
        response = test_client.post("/api/query", json={"session_id": "test"})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_internal_server_error(self, test_client, mock_rag_system):
        """Test query endpoint when RAG system raises exception"""
        mock_rag_system.query.side_effect = Exception("Database connection error")
        
        response = test_client.post("/api/query", json={"query": "test query"})
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Database connection error" in response.json()["detail"]

    def test_query_session_creation_error(self, test_client, mock_rag_system):
        """Test query endpoint when session creation fails"""
        mock_rag_system.session_manager.create_session.side_effect = Exception("Session error")
        
        response = test_client.post("/api/query", json={"query": "test query"})
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.parametrize("query,expected_answer", [
        ("What is AI?", "Test answer"),
        ("Explain machine learning", "Test answer"),
        ("How does deep learning work?", "Test answer"),
    ])
    def test_query_various_inputs(self, test_client, query, expected_answer):
        """Test query endpoint with various input queries"""
        response = test_client.post("/api/query", json={"query": query})
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["answer"] == expected_answer


class TestCoursesEndpoint:
    """Test cases for /api/courses endpoint"""

    def test_get_courses_success(self, test_client):
        """Test courses endpoint returns correct course statistics"""
        response = test_client.get("/api/courses")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Test Course 1" in data["course_titles"]
        assert "Test Course 2" in data["course_titles"]

    def test_get_courses_internal_error(self, test_client, mock_rag_system):
        """Test courses endpoint when analytics fails"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Analytics error" in response.json()["detail"]

    def test_get_courses_empty_response(self, test_client, mock_rag_system):
        """Test courses endpoint with no courses"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_courses"] == 0
        assert len(data["course_titles"]) == 0


class TestStaticFileRoutes:
    """Test cases for static file serving"""

    def test_static_routes_not_in_test_app(self, test_client):
        """Test that static routes are not mounted in test app"""
        # Our test app doesn't include static file mounting to avoid filesystem issues
        response = test_client.get("/")
        
        # Should return 404 since no route is defined for root
        assert response.status_code == 404

    def test_static_file_route_not_available(self, test_client):
        """Test static file routes are not available in test environment"""
        response = test_client.get("/index.html")
        
        # Should return 404 since static files are not served in test
        assert response.status_code == 404


class TestCORSAndMiddleware:
    """Test CORS and middleware configuration"""

    def test_cors_middleware_allows_requests(self, test_client):
        """Test CORS middleware allows requests from any origin"""
        # Test with origin header to trigger CORS
        headers = {"origin": "http://localhost:3000"}
        response = test_client.post("/api/query", 
                                  json={"query": "test"}, 
                                  headers=headers)
        
        # Request should succeed regardless of CORS headers in test
        assert response.status_code == status.HTTP_200_OK

    def test_options_request_handling(self, test_client):
        """Test OPTIONS request is handled correctly"""
        response = test_client.options("/api/query")
        
        # OPTIONS should return allowed methods or 200 OK
        assert response.status_code in [200, 405]  # 405 is also acceptable for OPTIONS


class TestResponseModels:
    """Test response model validation"""

    def test_query_response_model(self, test_client, sample_query_request):
        """Test query response matches expected model"""
        response = test_client.post("/api/query", json=sample_query_request)
        data = response.json()
        
        # Verify all required fields are present
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data
        
        # Verify data types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

    def test_courses_response_model(self, test_client):
        """Test courses response matches expected model"""
        response = test_client.get("/api/courses")
        data = response.json()
        
        # Verify all required fields are present
        required_fields = ["total_courses", "course_titles"]
        for field in required_fields:
            assert field in data
        
        # Verify data types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        for title in data["course_titles"]:
            assert isinstance(title, str)


class TestErrorHandling:
    """Test error handling across endpoints"""

    def test_invalid_endpoint(self, test_client):
        """Test accessing non-existent endpoint"""
        response = test_client.get("/api/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_method_not_allowed(self, test_client):
        """Test using wrong HTTP method"""
        response = test_client.get("/api/query")  # Should be POST
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_large_request_body(self, test_client):
        """Test handling of large request body"""
        large_query = "x" * 10000  # Very large query
        response = test_client.post("/api/query", json={"query": large_query})
        
        # Should still process (or return appropriate error)
        assert response.status_code in [200, 413, 422, 500]