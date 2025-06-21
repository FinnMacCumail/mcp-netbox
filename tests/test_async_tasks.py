"""
Tests for async task queue functionality (Issue #15)
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

# Test if RQ is available
try:
    import redis
    from rq import Queue
    RQ_AVAILABLE = True
except ImportError:
    RQ_AVAILABLE = False


class TestTaskTracker:
    """Test TaskTracker for progress and status management."""
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="Redis/RQ not available")
    def test_task_tracker_initialization(self):
        """Test TaskTracker initialization with Redis."""
        from netbox_mcp.tasks import TaskTracker
        
        with patch('netbox_mcp.tasks.Redis') as mock_redis:
            mock_redis.from_url.return_value = Mock()
            
            tracker = TaskTracker("redis://localhost:6379/0")
            
            assert tracker.task_ttl == 3600
            mock_redis.from_url.assert_called_once_with("redis://localhost:6379/0")
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="Redis/RQ not available")
    def test_update_task_status(self):
        """Test task status updates."""
        from netbox_mcp.tasks import TaskTracker
        
        with patch('netbox_mcp.tasks.Redis') as mock_redis:
            mock_redis_conn = Mock()
            mock_redis.from_url.return_value = mock_redis_conn
            
            tracker = TaskTracker()
            
            task_data = {"progress": 50, "stage": "processing"}
            tracker.update_task_status("test_task_123", "running", task_data)
            
            # Verify setex was called with proper parameters
            mock_redis_conn.setex.assert_called_once()
            call_args = mock_redis_conn.setex.call_args
            
            assert call_args[0][0] == "task:test_task_123"  # Key
            assert call_args[0][1] == 3600  # TTL
            
            # Verify JSON data structure
            stored_data = json.loads(call_args[0][2])
            assert stored_data["task_id"] == "test_task_123"
            assert stored_data["status"] == "running"
            assert stored_data["progress"] == 50
            assert stored_data["stage"] == "processing"
            assert "updated_at" in stored_data
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="Redis/RQ not available")
    def test_get_task_status_found(self):
        """Test retrieving existing task status."""
        from netbox_mcp.tasks import TaskTracker
        
        with patch('netbox_mcp.tasks.Redis') as mock_redis:
            mock_redis_conn = Mock()
            mock_redis.from_url.return_value = mock_redis_conn
            
            # Mock Redis returning task data
            task_data = {
                "task_id": "test_task_123",
                "status": "completed",
                "progress": 100
            }
            mock_redis_conn.get.return_value = json.dumps(task_data)
            
            tracker = TaskTracker()
            result = tracker.get_task_status("test_task_123")
            
            assert result == task_data
            mock_redis_conn.get.assert_called_once_with("task:test_task_123")
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="Redis/RQ not available")
    def test_get_task_status_not_found(self):
        """Test retrieving non-existent task status."""
        from netbox_mcp.tasks import TaskTracker
        
        with patch('netbox_mcp.tasks.Redis') as mock_redis:
            mock_redis_conn = Mock()
            mock_redis.from_url.return_value = mock_redis_conn
            
            # Mock Redis returning None (key not found)
            mock_redis_conn.get.return_value = None
            
            tracker = TaskTracker()
            result = tracker.get_task_status("nonexistent_task")
            
            assert result["status"] == "not_found"
            assert "error" in result


class TestAsyncTaskManager:
    """Test AsyncTaskManager for task queueing and management."""
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="Redis/RQ not available")
    def test_task_manager_initialization(self):
        """Test AsyncTaskManager initialization."""
        from netbox_mcp.tasks import AsyncTaskManager
        
        with patch('netbox_mcp.tasks.Redis') as mock_redis:
            with patch('netbox_mcp.tasks.Queue') as mock_queue:
                with patch('netbox_mcp.tasks.TaskTracker') as mock_tracker:
                    
                    manager = AsyncTaskManager("redis://localhost:6379/0", "test_queue")
                    
                    mock_redis.from_url.assert_called_once_with("redis://localhost:6379/0")
                    mock_queue.assert_called_once()
                    mock_tracker.assert_called_once()
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="Redis/RQ not available")
    def test_generate_task_id(self):
        """Test task ID generation."""
        from netbox_mcp.tasks import AsyncTaskManager
        
        with patch('netbox_mcp.tasks.Redis'), patch('netbox_mcp.tasks.Queue'), patch('netbox_mcp.tasks.TaskTracker'):
            manager = AsyncTaskManager()
            
            task_id = manager.generate_task_id("bulk_devices", "100dev")
            
            assert task_id.startswith("bulk_devices_100dev_")
            assert len(task_id.split("_")) == 4  # operation_info_timestamp_uuid
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="Redis/RQ not available")
    def test_queue_bulk_device_operation(self):
        """Test queueing bulk device operation."""
        from netbox_mcp.tasks import AsyncTaskManager
        
        with patch('netbox_mcp.tasks.Redis'), patch('netbox_mcp.tasks.TaskTracker') as mock_tracker:
            with patch('netbox_mcp.tasks.Queue') as mock_queue:
                
                mock_queue_instance = Mock()
                mock_queue.return_value = mock_queue_instance
                mock_queue_instance.enqueue.return_value = Mock(id="job_123")
                
                mock_tracker_instance = Mock()
                mock_tracker.return_value = mock_tracker_instance
                
                manager = AsyncTaskManager()
                
                devices_data = [
                    {"name": "device1", "manufacturer": "Cisco"},
                    {"name": "device2", "manufacturer": "Cisco"}
                ]
                config = {"confirm": True}
                
                task_id = manager.queue_bulk_device_operation(devices_data, config)
                
                # Verify task ID format
                assert task_id.startswith("bulk_devices_2dev_")
                
                # Verify queue enqueue was called
                mock_queue_instance.enqueue.assert_called_once()
                
                # Verify task status was initialized
                mock_tracker_instance.update_task_status.assert_called_once()


class TestAsyncMCPTools:
    """Test async MCP tools without requiring actual Redis/RQ."""
    
    def test_start_bulk_async_no_task_manager(self):
        """Test async tool when task manager not available."""
        from netbox_mcp.server import netbox_start_bulk_async
        
        with patch('netbox_mcp.tasks.get_task_manager', return_value=None):
            devices_data = [{"name": "test", "manufacturer": "Cisco", "device_type": "Switch", "site": "DC1", "role": "Access"}]
            
            result = netbox_start_bulk_async(devices_data, confirm=True)
            
            assert result["success"] is False
            assert "TaskQueueUnavailable" in result["error_type"]
            assert "netbox_bulk_ensure_devices" in result["help"]
    
    def test_start_bulk_async_validation_errors(self):
        """Test async tool input validation."""
        from netbox_mcp.server import netbox_start_bulk_async
        
        # Test empty list
        result = netbox_start_bulk_async([], confirm=True)
        assert result["success"] is False
        assert "ValidationError" in result["error_type"]
        
        # Test missing required fields
        invalid_device = {"name": "test"}  # Missing manufacturer, device_type, site, role
        result = netbox_start_bulk_async([invalid_device], confirm=True)
        assert result["success"] is False
        assert "missing required fields" in result["error"]
        
        # Test too many devices
        many_devices = [{"name": f"device{i}", "manufacturer": "Cisco", "device_type": "Switch", "site": "DC1", "role": "Access"} 
                       for i in range(1001)]
        result = netbox_start_bulk_async(many_devices, confirm=True, max_devices=1000)
        assert result["success"] is False
        assert "exceeds maximum" in result["error"]
    
    def test_start_bulk_async_requires_confirm(self):
        """Test that async tool requires confirm=True."""
        from netbox_mcp.server import netbox_start_bulk_async
        
        with patch('netbox_mcp.tasks.get_task_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager
            
            devices_data = [{"name": "test", "manufacturer": "Cisco", "device_type": "Switch", "site": "DC1", "role": "Access"}]
            
            result = netbox_start_bulk_async(devices_data, confirm=False)
            
            assert result["success"] is False
            assert "ConfirmationRequired" in result["error_type"]
            assert "confirm=True" in result["error"]
    
    def test_get_task_status_no_task_manager(self):
        """Test task status tool when task manager not available."""
        from netbox_mcp.server import netbox_get_task_status
        
        with patch('netbox_mcp.tasks.get_task_manager', return_value=None):
            result = netbox_get_task_status("test_task_123")
            
            assert result["success"] is False
            assert "TaskQueueUnavailable" in result["error_type"]
    
    def test_get_task_status_not_found(self):
        """Test task status for non-existent task."""
        from netbox_mcp.server import netbox_get_task_status
        
        with patch('netbox_mcp.tasks.get_task_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_tracker = Mock()
            mock_manager.tracker = mock_tracker
            mock_get_manager.return_value = mock_manager
            
            # Mock tracker returning not_found status
            mock_tracker.get_task_status.return_value = {"status": "not_found", "error": "Task not found"}
            
            result = netbox_get_task_status("nonexistent_task")
            
            assert result["success"] is False
            assert "TaskNotFound" in result["error_type"]
    
    def test_get_task_status_running_task(self):
        """Test task status for running task with progress."""
        from netbox_mcp.server import netbox_get_task_status
        
        with patch('netbox_mcp.tasks.get_task_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_tracker = Mock()
            mock_manager.tracker = mock_tracker
            mock_get_manager.return_value = mock_manager
            
            # Mock tracker returning running status
            task_status = {
                "task_id": "test_task_123",
                "status": "running",
                "stage": "processing",
                "progress": 45.5,
                "current_device": "switch-01"
            }
            mock_tracker.get_task_status.return_value = task_status
            
            result = netbox_get_task_status("test_task_123")
            
            assert result["success"] is True
            assert result["task_status"]["status"] == "running"
            assert result["task_status"]["progress_percentage"] == "45.5%"
            assert result["task_status"]["stage_description"] == "Processing devices using two-pass strategy"
            assert "Processing: switch-01" in result["task_status"]["current_status"]
    
    def test_get_task_status_completed_task(self):
        """Test task status for completed task with results."""
        from netbox_mcp.server import netbox_get_task_status
        
        with patch('netbox_mcp.tasks.get_task_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_tracker = Mock()
            mock_manager.tracker = mock_tracker
            mock_get_manager.return_value = mock_manager
            
            # Mock tracker returning completed status
            task_status = {
                "task_id": "test_task_123",
                "status": "completed",
                "results": {
                    "summary": {
                        "total_devices": 100,
                        "successful_devices": 95,
                        "failed_devices": 5,
                        "success_rate": 95.0
                    }
                }
            }
            mock_tracker.get_task_status.return_value = task_status
            
            result = netbox_get_task_status("test_task_123")
            
            assert result["success"] is True
            assert result["task_status"]["status"] == "completed"
            
            summary = result["task_status"]["completion_summary"]
            assert summary["total_devices"] == 100
            assert summary["successful_devices"] == 95
            assert summary["failed_devices"] == 5
            assert summary["success_rate"] == "95.0%"
    
    def test_list_active_tasks(self):
        """Test listing active tasks."""
        from netbox_mcp.server import netbox_list_active_tasks
        
        with patch('netbox_mcp.tasks.get_task_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_tracker = Mock()
            mock_manager.tracker = mock_tracker
            mock_get_manager.return_value = mock_manager
            
            # Mock active tasks
            active_tasks = [
                {"task_id": "task1", "status": "running", "progress": 50},
                {"task_id": "task2", "status": "completed", "progress": 100},
                {"task_id": "task3", "status": "queued", "progress": 0}
            ]
            mock_tracker.list_active_tasks.return_value = active_tasks
            
            # Mock queue info
            mock_manager.get_queue_info.return_value = {"job_count": 2, "worker_count": 1}
            
            result = netbox_list_active_tasks()
            
            assert result["success"] is True
            assert result["task_count"] == 3
            assert len(result["tasks"]) == 3
            
            # Check status summary
            assert result["status_summary"]["running"] == 1
            assert result["status_summary"]["completed"] == 1
            assert result["status_summary"]["queued"] == 1
    
    def test_get_queue_info(self):
        """Test getting queue information."""
        from netbox_mcp.server import netbox_get_queue_info
        
        with patch('netbox_mcp.tasks.get_task_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_tracker = Mock()
            mock_manager.tracker = mock_tracker
            mock_get_manager.return_value = mock_manager
            
            # Mock queue info
            queue_info = {
                "queue_name": "netbox_bulk",
                "job_count": 5,
                "worker_count": 2,
                "redis_info": {"connected": True, "memory_usage": "1.2MB"}
            }
            mock_manager.get_queue_info.return_value = queue_info
            
            # Mock active tasks for tracker statistics
            active_tasks = [
                {"status": "running"},
                {"status": "queued"},
                {"status": "completed"}
            ]
            mock_tracker.list_active_tasks.return_value = active_tasks
            
            result = netbox_get_queue_info()
            
            assert result["success"] is True
            assert result["queue_info"]["job_count"] == 5
            assert result["queue_info"]["worker_count"] == 2
            assert result["task_tracker"]["active_tasks"] == 3
            assert result["system_status"]["redis_available"] is True
            assert result["system_status"]["rq_available"] is True


class TestBackgroundTask:
    """Test the background task execution function."""
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="Redis/RQ not available")
    def test_execute_bulk_device_operation_structure(self):
        """Test the structure of background task execution."""
        from netbox_mcp.tasks import execute_bulk_device_operation
        
        # This test verifies the function exists and has proper signature
        # Full execution testing would require Redis infrastructure
        
        import inspect
        sig = inspect.signature(execute_bulk_device_operation)
        
        assert "task_id" in sig.parameters
        assert "devices_data" in sig.parameters
        assert "config" in sig.parameters
        
        # Function should be defined for RQ worker execution
        assert callable(execute_bulk_device_operation)