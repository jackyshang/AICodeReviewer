# Sample Configuration Files

This directory contains sample configuration files for integrating the Reviewer tool with various MCP (Model Context Protocol) clients.

## Gemini CLI MCP Configuration

The `gemini-mcp-settings.json` file shows how to configure the Gemini CLI to use the Reviewer MCP server.

### Setup Instructions

1. **Install Reviewer**: First, ensure the reviewer tool is installed:
   ```bash
   pip install -e /path/to/pr-reviewer
   ```

2. **Start the Reviewer Service**: The MCP server requires the Reviewer API service to be running:
   ```bash
   reviewer service start
   # Or manually: python -m reviewer.service
   ```

3. **Configure Gemini CLI**: Copy the configuration to your Gemini settings:
   ```bash
   cp gemini-mcp-settings.json ~/.gemini/settings.json
   ```

4. **Update the Path**: Edit the configuration file and update the `cwd` field to point to your actual pr-reviewer installation directory:
   ```json
   "cwd": "/path/to/pr-reviewer"
   ```

5. **Verify Connection**: In Gemini CLI, run:
   ```
   /mcp
   ```
   
   You should see:
   ```
   🟢 reviewer - Ready (X tools)
   ```

### Configuration Details

- **command**: Uses `python` to run the MCP server module
- **args**: Specifies the module to run (`reviewer.mcp_server`)
- **cwd**: Working directory (must be the pr-reviewer project root)
- **env**: Environment variables
  - `REVIEWER_SERVICE_URL`: URL where the Reviewer API service is running (default: `http://localhost:8765`)
- **timeout**: Connection timeout in milliseconds (10 minutes)
- **trust**: Whether to trust the MCP server (set to `false` for security)

### Troubleshooting

If the MCP server shows as "Disconnected":

1. Check that the Reviewer service is running:
   ```bash
   reviewer service status
   ```

2. Verify the service is accessible:
   ```bash
   curl http://localhost:8765/health
   ```

3. Check the Gemini CLI logs for connection errors

4. Ensure the `cwd` path in the configuration points to the correct directory

5. If using a virtual environment, you may need to specify the full path to the Python executable:
   ```json
   "command": "/path/to/pr-reviewer/venv/bin/python"
   ```