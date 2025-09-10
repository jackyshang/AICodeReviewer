"""Tests for MCP service client."""

import pytest
from aioresponses import aioresponses
from reviewer.mcp.client import ReviewServiceClient


class TestReviewServiceClient:
    """Test the Review Service HTTP client."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with aioresponses() as mocked:
            mocked.get(
                'http://localhost:8765/health',
                payload={
                    'status': 'running',
                    'active_sessions': 2,
                    'sessions': ['session1', 'session2'],
                    'timestamp': '2025-01-01T12:00:00'
                }
            )
            
            async with ReviewServiceClient() as client:
                health = await client.check_health()
                assert health['status'] == 'running'
                assert health['active_sessions'] == 2
                assert len(health['sessions']) == 2
                
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check when service is down."""
        with aioresponses() as mocked:
            mocked.get(
                'http://localhost:8765/health',
                status=503
            )
            
            async with ReviewServiceClient() as client:
                with pytest.raises(Exception) as exc_info:
                    await client.check_health()
                assert "Service unhealthy: 503" in str(exc_info.value)
                
    @pytest.mark.asyncio
    async def test_list_sessions(self):
        """Test listing sessions."""
        with aioresponses() as mocked:
            mocked.get(
                'http://localhost:8765/sessions',
                payload={
                    'sessions': [
                        {
                            'name': 'test-session',
                            'created_at': '2025-01-01T12:00:00',
                            'last_reviewed': '2025-01-01T12:30:00',
                            'iteration': 3,
                            'messages': 10
                        }
                    ]
                }
            )
            
            async with ReviewServiceClient() as client:
                result = await client.list_sessions()
                assert 'sessions' in result
                assert len(result['sessions']) == 1
                assert result['sessions'][0]['name'] == 'test-session'
                
    @pytest.mark.asyncio
    async def test_get_session_found(self):
        """Test getting specific session details."""
        with aioresponses() as mocked:
            mocked.get(
                'http://localhost:8765/sessions/my-session',
                payload={
                    'name': 'my-session',
                    'created_at': '2025-01-01T12:00:00',
                    'last_reviewed': '2025-01-01T12:30:00',
                    'iteration': 5,
                    'messages': 20,
                    'model': 'gemini-2.5-pro'
                }
            )
            
            async with ReviewServiceClient() as client:
                session = await client.get_session('my-session')
                assert session['name'] == 'my-session'
                assert session['iteration'] == 5
                assert session['model'] == 'gemini-2.5-pro'
                
    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """Test getting non-existent session."""
        with aioresponses() as mocked:
            mocked.get(
                'http://localhost:8765/sessions/unknown',
                status=404
            )
            
            async with ReviewServiceClient() as client:
                with pytest.raises(ValueError) as exc_info:
                    await client.get_session('unknown')
                assert "Session 'unknown' not found" in str(exc_info.value)
                
    @pytest.mark.asyncio
    async def test_clear_session_success(self):
        """Test clearing a session."""
        with aioresponses() as mocked:
            mocked.delete(
                'http://localhost:8765/sessions/my-session',
                payload={'message': "Session 'my-session' cleared"}
            )
            
            async with ReviewServiceClient() as client:
                result = await client.clear_session('my-session')
                assert result['message'] == "Session 'my-session' cleared"
                
    @pytest.mark.asyncio
    async def test_custom_base_url(self):
        """Test using custom service URL."""
        custom_url = 'http://localhost:9999'
        with aioresponses() as mocked:
            mocked.get(
                f'{custom_url}/health',
                payload={'status': 'running', 'active_sessions': 0}
            )
            
            async with ReviewServiceClient(base_url=custom_url) as client:
                health = await client.check_health()
                assert health['status'] == 'running'