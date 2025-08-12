import pytest
from unittest.mock import patch, Mock
import asyncio
from fastapi.testclient import TestClient
from fastapi import status


class TestAppStartup:
    """Test application startup events and initialization"""

    @patch('os.path.exists')
    @patch('builtins.print')
    def test_startup_with_docs_folder(self, mock_print, mock_exists, mock_rag_system):
        """Test startup event when docs folder exists"""
        mock_exists.return_value = True
        mock_rag_system.add_course_folder.return_value = (3, 15)
        
        # Import and trigger startup
        with patch('fastapi.staticfiles.StaticFiles'):
            from app import app
            import app as app_module
            app_module.rag_system = mock_rag_system
            
            # Simulate startup event
            with TestClient(app) as client:
                # Startup event should have been triggered
                mock_rag_system.add_course_folder.assert_called_once_with("../docs", clear_existing=False)
                mock_print.assert_any_call("Loading initial documents...")
                mock_print.assert_any_call("Loaded 3 courses with 15 chunks")

    @patch('os.path.exists')
    @patch('builtins.print')
    def test_startup_without_docs_folder(self, mock_print, mock_exists, mock_rag_system):
        """Test startup event when docs folder doesn't exist"""
        mock_exists.return_value = False
        
        # Import and trigger startup
        with patch('fastapi.staticfiles.StaticFiles'):
            from app import app
            import app as app_module
            app_module.rag_system = mock_rag_system
            
            # Simulate startup event
            with TestClient(app):
                # Should not attempt to load documents
                mock_rag_system.add_course_folder.assert_not_called()
                mock_print.assert_not_called()

    @patch('os.path.exists')
    @patch('builtins.print')
    def test_startup_document_loading_error(self, mock_print, mock_exists, mock_rag_system):
        """Test startup event when document loading fails"""
        mock_exists.return_value = True
        mock_rag_system.add_course_folder.side_effect = Exception("Loading failed")
        
        # Import and trigger startup
        with patch('fastapi.staticfiles.StaticFiles'):
            from app import app
            import app as app_module
            app_module.rag_system = mock_rag_system
            
            # Simulate startup event
            with TestClient(app):
                mock_print.assert_any_call("Loading initial documents...")
                mock_print.assert_any_call("Error loading documents: Loading failed")


class TestAppConfiguration:
    """Test application configuration and middleware setup"""

    def test_app_title_and_settings(self):
        """Test FastAPI app configuration"""
        with patch('fastapi.staticfiles.StaticFiles'):
            from app import app
            
            assert app.title == "Course Materials RAG System"
            assert app.root_path == ""

    def test_cors_middleware_configuration(self, test_client):
        """Test CORS middleware is properly configured"""
        # Test that requests with origins are handled properly
        headers = {"origin": "http://example.com"}
        response = test_client.post("/api/query", 
                                  json={"query": "test"}, 
                                  headers=headers)
        
        # CORS should allow the request to proceed
        assert response.status_code == status.HTTP_200_OK

    def test_trusted_host_middleware(self, test_client):
        """Test trusted host middleware allows requests"""
        # Test with various host headers
        headers = {"host": "localhost:8000"}
        response = test_client.get("/api/courses", headers=headers)
        
        # Should not be blocked by trusted host middleware
        assert response.status_code != 400


class TestStaticFileHandling:
    """Test static file serving configuration"""

    def test_dev_static_files_class_exists(self):
        """Test DevStaticFiles class is defined and can be imported"""
        from app import DevStaticFiles
        from fastapi.staticfiles import StaticFiles
        
        # Verify it's a subclass of StaticFiles
        assert issubclass(DevStaticFiles, StaticFiles)

    def test_static_file_mounting_in_actual_app(self):
        """Test static file mounting is configured in the actual app"""
        # This test verifies the concept without actually mounting files
        with patch('fastapi.staticfiles.StaticFiles'):
            # We can verify the DevStaticFiles class exists and has the right methods
            from app import DevStaticFiles
            
            # Check that the get_response method exists
            assert hasattr(DevStaticFiles, 'get_response')
            
            # Verify it's meant to add no-cache headers
            import inspect
            source = inspect.getsource(DevStaticFiles.get_response)
            assert "no-cache" in source


class TestEnvironmentSetup:
    """Test environment setup and encoding configuration"""

    @patch('sys.platform', 'win32')
    @patch('os.environ', {})
    @patch('locale.setlocale')
    def test_windows_utf8_setup(self, mock_setlocale):
        """Test UTF-8 encoding setup on Windows"""
        import os
        
        # Re-import the app module to trigger environment setup
        import importlib
        import app
        importlib.reload(app)
        
        # Check that UTF-8 encoding is set
        assert os.environ.get('PYTHONIOENCODING') == 'utf-8'

    @patch('sys.platform', 'linux')
    @patch('os.environ', {})
    def test_non_windows_no_utf8_setup(self):
        """Test no UTF-8 setup on non-Windows platforms"""
        import os
        
        # Re-import the app module
        import importlib
        import app
        importlib.reload(app)
        
        # UTF-8 encoding should not be set on non-Windows
        assert 'PYTHONIOENCODING' not in os.environ or os.environ.get('PYTHONIOENCODING') != 'utf-8'


class TestWarningsFilter:
    """Test warnings filter configuration"""

    @patch('warnings.filterwarnings')
    def test_resource_tracker_warning_filtered(self, mock_filterwarnings):
        """Test resource tracker warnings are filtered"""
        # Re-import to trigger warnings filter
        import importlib
        import app
        importlib.reload(app)
        
        # Verify filterwarnings was called
        mock_filterwarnings.assert_called_with(
            "ignore", 
            message="resource_tracker: There appear to be.*"
        )


class TestRAGSystemIntegration:
    """Test RAG system integration with FastAPI app"""

    def test_rag_system_initialization(self, mock_rag_system):
        """Test RAG system is properly initialized"""
        with patch('fastapi.staticfiles.StaticFiles'):
            from app import app
            import app as app_module
            
            # RAG system should be initialized with config
            assert hasattr(app_module, 'rag_system')

    def test_rag_system_dependency_injection(self, test_client, mock_rag_system):
        """Test RAG system is properly injected into endpoints"""
        # Make a request that uses the RAG system
        response = test_client.post("/api/query", json={"query": "test"})
        
        assert response.status_code == 200
        # Verify the mock was called
        mock_rag_system.query.assert_called_once()

    def test_session_manager_integration(self, test_client, mock_rag_system):
        """Test session manager integration"""
        response = test_client.post("/api/query", json={"query": "test"})
        
        assert response.status_code == 200
        # Verify session creation was called
        mock_rag_system.session_manager.create_session.assert_called_once()