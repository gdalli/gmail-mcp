#!/usr/bin/env python3
"""Quick test to verify CORS middleware is configured correctly."""

import sys

sys.path.insert(0, ".")

# Set required env vars before importing
import os

os.environ["MCP_ENABLE_OAUTH21"] = "true"
os.environ["WORKSPACE_MCP_STATELESS_MODE"] = "true"
os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "test"
os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "test"

from core.server import server

# Get the HTTP app
app = server.http_app()

# Check middleware stack
print("Middleware stack:")
for i, m in enumerate(app.user_middleware):
    if hasattr(m, "cls"):
        print(f"  {i}: {m.cls.__name__}")
    else:
        print(f"  {i}: {type(m).__name__}")

print("\nChecking for CORSMiddleware...")
has_cors = any(
    hasattr(m, "cls") and m.cls.__name__ == "CORSMiddleware"
    for m in app.user_middleware
)
print(f"CORS middleware found: {has_cors}")

if has_cors:
    print("✅ CORS middleware is configured!")
else:
    print("❌ CORS middleware is NOT configured!")
    sys.exit(1)
