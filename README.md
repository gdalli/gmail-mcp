# Multi-Account Gmail MCP Server

Manage 10+ Gmail inboxes through a single MCP server. Forked from [google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp), stripped down to Gmail-only.

## Prerequisites

1. **Google Cloud Project** with Gmail API enabled
2. **OAuth 2.0 credentials** (Desktop app type)
3. **Python 3.10+**

## Google Cloud Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable the **Gmail API** (APIs & Services > Library > search "Gmail API")
4. Configure **OAuth consent screen** (APIs & Services > OAuth consent screen)
   - User type: External (or Internal if using Workspace)
   - Add scopes: `https://mail.google.com/`
   - Add yourself as a test user
5. Create **OAuth 2.0 Client ID** (APIs & Services > Credentials > Create Credentials)
   - Application type: **Desktop app**
   - Download the JSON file
6. Set environment variables:
   ```bash
   export GOOGLE_OAUTH_CLIENT_ID="your-client-id"
   export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"
   ```

## Installation

```bash
cd /root/gmail-mcp
pip install -e .
```

## Adding Gmail Accounts

On first use of any account, the server will prompt for OAuth authentication. Visit the provided URL, authenticate, and the token is stored in `~/.google_workspace_mcp/credentials/`.

Each tool call takes a `user_google_email` parameter to specify which inbox to operate on.

## Running

### Local (stdio)
```bash
python main.py
```

### HTTP transport
```bash
python main.py --transport streamable-http
```

### Single-user mode
```bash
python main.py --single-user
```

## Connecting from Claude Desktop

### SSH + stdio (for remote server)
```json
{
  "mcpServers": {
    "gmail": {
      "command": "ssh",
      "args": ["centauri", "cd /root/gmail-mcp && python3 main.py --single-user"]
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `search_gmail_messages` | Search inbox with Gmail query syntax |
| `get_gmail_message_content` | Read a specific email |
| `get_gmail_messages_content_batch` | Batch read multiple emails |
| `get_gmail_attachment_content` | Download attachment |
| `send_gmail_message` | Send email with optional CC/BCC/attachments |
| `draft_gmail_message` | Create/update/send/list/delete drafts |
| `get_gmail_thread_content` | Get full thread conversation |
| `get_gmail_threads_content_batch` | Batch fetch threads |
| `list_gmail_labels` | List all labels |
| `manage_gmail_label` | Create/update/delete labels |
| `list_gmail_filters` | List email filters |
| `manage_gmail_filter` | Create/delete filters |
| `modify_gmail_message_labels` | Add/remove labels on a message |
| `batch_modify_gmail_message_labels` | Bulk label operations |

## Deployment (systemd)

```ini
[Unit]
Description=Multi-Account Gmail MCP Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/gmail-mcp
ExecStart=/usr/bin/python3 main.py --single-user
Restart=on-failure
RestartSec=5
Environment=GOOGLE_OAUTH_CLIENT_ID=your-client-id
Environment=GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
StandardOutput=append:/var/log/gmail-mcp.log
StandardError=append:/var/log/gmail-mcp.log

[Install]
WantedBy=multi-user.target
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth client ID from Google Cloud |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_CLIENT_SECRET_PATH` | Path to client_secret.json (alternative to env vars) |
| `WORKSPACE_MCP_CREDENTIALS_DIR` | Custom credentials directory |
| `MCP_SINGLE_USER_MODE` | Set to `1` for single-user mode |
| `PORT` / `WORKSPACE_MCP_PORT` | HTTP port (default: 8000) |
