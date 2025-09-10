"""Tests for CLI service management functionality."""

import pytest
from unittest.mock import patch, MagicMock, mock_open, call
import subprocess
import sys

from reviewer.cli import manage_service


class TestServiceManagement:
    """Test suite for service management commands."""
    
    @patch('subprocess.run')
    @patch('reviewer.cli.check_service_available')
    @patch('reviewer.cli.requests.get')
    @patch('reviewer.cli.console')
    @patch('reviewer.cli.ReviewFormatter')
    @patch('importlib.metadata.version')
    def test_service_status_running_with_uptime(self, mock_version, mock_formatter_class, mock_console, 
                                                 mock_get, mock_check_service, mock_run):
        """Test status command when service is running with uptime from health endpoint."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        mock_version.return_value = "0.1.0"
        
        mock_run.return_value = MagicMock(stdout="com.reviewer.api")
        mock_check_service.return_value = True
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'active_sessions': 2,
                'sessions': ['auth-feature', 'bug-fix'],
                'timestamp': '2025-07-06T18:00:00',
                'uptime': 3661  # 1 hour, 1 minute, 1 second
            }
        )
        
        # Execute
        manage_service('status')
        
        # Verify subprocess calls
        mock_run.assert_called_once_with(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            check=False
        )
        mock_check_service.assert_called_once()
        
        # Verify the new builder format output
        expected_console_calls = [
            call("Installed: ✓ Yes"),
            call("Running:   ✓ Yes"), 
            call("Healthy:   ✓ Yes"),
            call("Uptime:    1 hours, 1 minutes"),
            call("Version:   0.1.0"),
            call("Sessions:  2 active")
        ]
        mock_console.print.assert_has_calls(expected_console_calls)
    
    @patch('subprocess.run')
    @patch('reviewer.cli.check_service_available')
    @patch('reviewer.cli.requests.get')
    @patch('reviewer.cli.console')
    @patch('reviewer.cli.ReviewFormatter')
    @patch('importlib.metadata.version')
    def test_service_status_running_with_ps_fallback(self, mock_version, mock_formatter_class, mock_console, 
                                                     mock_get, mock_check_service, mock_run):
        """Test status command when service is running but health endpoint lacks uptime."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        mock_version.return_value = "0.1.0"
        
        # First call for launchctl list, second call for ps command
        mock_run.side_effect = [
            MagicMock(stdout="com.reviewer.api"),  # launchctl list
            MagicMock(stdout="1234  01:23:45 /usr/bin/python3 -m reviewer.service\n5678  00:05:30 other_process")  # ps command
        ]
        mock_check_service.return_value = True
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'active_sessions': 1,
                'sessions': ['test-session'],
                'timestamp': '2025-07-06T18:00:00'
                # No uptime field - should trigger ps fallback
            }
        )
        
        # Execute
        manage_service('status')
        
        # Verify the ps command was called for fallback
        expected_ps_call = call(
            ["ps", "-eo", "pid,etime,comm"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        mock_run.assert_has_calls([call(["launchctl", "list"], capture_output=True, text=True, check=False),
                                  expected_ps_call])
        
        # Verify uptime was extracted from ps output and converted to human format
        expected_console_calls = [
            call("Installed: ✓ Yes"),
            call("Running:   ✓ Yes"),
            call("Healthy:   ✓ Yes"),
            call("Uptime:    1 hours, 23 minutes"),
            call("Version:   0.1.0"),
            call("Sessions:  1 active")
        ]
        mock_console.print.assert_has_calls(expected_console_calls)
    
    @patch('subprocess.run')
    @patch('reviewer.cli.check_service_available')
    @patch('reviewer.cli.console')
    @patch('reviewer.cli.ReviewFormatter')
    @patch('importlib.metadata.version')
    def test_service_status_not_running(self, mock_version, mock_formatter_class, mock_console, mock_check_service, mock_run):
        """Test status command when service is loaded but not responding."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        mock_version.return_value = "0.1.0"
        
        mock_run.return_value = MagicMock(stdout="com.reviewer.api")
        mock_check_service.return_value = False
        
        # Execute
        manage_service('status')
        
        # Verify
        mock_check_service.assert_called_once()
        
        # Verify the new builder format output for non-running service
        expected_console_calls = [
            call("Installed: ✓ Yes"),
            call("Running:   ✗ No"),
            call("Healthy:   ✗ No"),
            call("Uptime:    unknown"),
            call("Version:   0.1.0")
        ]
        mock_console.print.assert_has_calls(expected_console_calls)
    
    @patch('subprocess.run')
    @patch('reviewer.cli.check_service_available')
    @patch('reviewer.cli.console')
    @patch('reviewer.cli.ReviewFormatter')
    @patch('importlib.metadata.version')
    def test_service_status_not_loaded(self, mock_version, mock_formatter_class, mock_console, mock_check_service, mock_run):
        """Test status command when service is not loaded."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        mock_version.return_value = "0.1.0"
        
        mock_run.return_value = MagicMock(stdout="other services but not ours")
        mock_check_service.return_value = False
        
        # Execute
        manage_service('status')
        
        # Verify the new builder format output for non-loaded service
        expected_console_calls = [
            call("Installed: ✗ No"),
            call("Running:   ✗ No"),
            call("Healthy:   ✗ No"),
            call("Uptime:    unknown"),
            call("Version:   0.1.0"),
            call(),  # Empty line
            call("To install: ./install-service.sh")
        ]
        mock_console.print.assert_has_calls(expected_console_calls)
    
    @patch('subprocess.run')
    @patch('reviewer.cli.check_service_available')
    @patch('reviewer.cli.time.sleep')
    @patch('reviewer.cli.console')
    @patch('reviewer.cli.ReviewFormatter')
    def test_service_restart_success(self, mock_formatter_class, mock_console, mock_sleep, mock_check_service, mock_run):
        """Test restart command with successful restart."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        
        mock_check_service.side_effect = [False, True]  # Not running, then running
        
        # Execute
        manage_service('restart')
        
        # Verify
        expected_calls = [
            call(["launchctl", "stop", "com.reviewer.api"], check=False),
            call(["launchctl", "start", "com.reviewer.api"], check=False)
        ]
        mock_run.assert_has_calls(expected_calls)
        mock_formatter.print_success.assert_called_with("✅ Service restarted successfully")
    
    @patch('subprocess.run')
    @patch('reviewer.cli.check_service_available')
    @patch('reviewer.cli.time.sleep')
    @patch('reviewer.cli.ReviewFormatter')
    def test_service_restart_failure(self, mock_formatter_class, mock_sleep, mock_check_service, mock_run):
        """Test restart command when service fails to start."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        
        mock_check_service.return_value = False  # Always False
        
        # Execute
        manage_service('restart')
        
        # Verify
        mock_formatter.print_error.assert_called_with("❌ Service failed to start within 10 seconds")
        mock_formatter.print_info.assert_called_with("Check logs: tail -f /tmp/reviewer.error.log")
    
    @patch('subprocess.call')
    @patch('reviewer.cli.console')
    @patch('reviewer.cli.ReviewFormatter')
    def test_service_logs(self, mock_formatter_class, mock_console, mock_call):
        """Test logs command."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        
        # Execute
        manage_service('logs')
        
        # Verify
        mock_call.assert_called_once_with(["tail", "-f", "/tmp/reviewer.log"])
        mock_formatter.print_info.assert_called_with("📜 Reviewer Service Logs (Ctrl+C to exit):")
    
    @patch('subprocess.call', side_effect=KeyboardInterrupt)
    @patch('reviewer.cli.console')
    @patch('reviewer.cli.ReviewFormatter')
    def test_service_logs_keyboard_interrupt(self, mock_formatter_class, mock_console, mock_call):
        """Test logs command with Ctrl+C."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        
        # Execute (should not raise exception)
        manage_service('logs')
        
        # Verify clean exit
        mock_call.assert_called_once()
    
    @patch('subprocess.run')
    @patch('reviewer.cli.ReviewFormatter')
    def test_service_stop_success(self, mock_formatter_class, mock_run):
        """Test stop command."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        
        # Execute
        manage_service('stop')
        
        # Verify
        mock_run.assert_called_once_with(
            ["launchctl", "stop", "com.reviewer.api"], 
            check=True
        )
        mock_formatter.print_success.assert_called_with("✅ Service stopped")
    
    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cmd'))
    @patch('reviewer.cli.ReviewFormatter')
    def test_service_stop_failure(self, mock_formatter_class, mock_run):
        """Test stop command when it fails."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        
        # Execute
        manage_service('stop')
        
        # Verify
        mock_formatter.print_error.assert_called_with("Failed to stop service: Command 'cmd' returned non-zero exit status 1.")


class TestPlatformCompatibility:
    """Test platform-specific behavior."""
    
    @patch('sys.platform', 'linux')
    @patch('reviewer.cli.ReviewFormatter')
    def test_service_management_on_non_macos(self, mock_formatter_class):
        """Test that service management handles non-macOS platforms gracefully."""
        # Setup
        mock_formatter = MagicMock()
        mock_formatter_class.return_value = mock_formatter
        
        # Execute
        manage_service('status')
        
        # Verify
        mock_formatter.print_error.assert_called_with("Service management is only available on macOS.")
        mock_formatter.print_info.assert_called_with("For other platforms, run the service manually: python -m reviewer.service")