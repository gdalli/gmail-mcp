import io
import argparse
import logging
import os
import socket
import sys
from importlib import metadata, import_module
from dotenv import load_dotenv

# Prevent stray startup output on macOS from corrupting MCP JSON-RPC on stdout.
_original_stdout = sys.stdout
if sys.platform == "darwin":
    sys.stdout = io.StringIO()

from auth.oauth_config import reload_oauth_config, is_stateless_mode  # noqa: E402
from core.log_formatter import EnhancedLogFormatter, configure_file_logging  # noqa: E402
from core.utils import check_credentials_directory_permissions  # noqa: E402
from core.server import server, set_transport_mode, configure_server_for_http  # noqa: E402

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Suppress noisy loggers
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

reload_oauth_config()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

configure_file_logging()


def safe_print(text):
    if not sys.stderr.isatty():
        logger.debug(f"[MCP Server] {text}")
        return
    try:
        print(text, file=sys.stderr)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode(), file=sys.stderr)


def _restore_stdout() -> None:
    """Restore the real stdout and replay any captured output to stderr."""
    captured_stdout = sys.stdout
    if captured_stdout is _original_stdout:
        return

    captured = ""
    try:
        if all(
            callable(getattr(captured_stdout, m, None))
            for m in ("getvalue", "write", "flush")
        ):
            captured = captured_stdout.getvalue()
    finally:
        sys.stdout = _original_stdout

    if captured:
        print(captured, end="", file=sys.stderr)


def main():
    """Main entry point for the Gmail MCP server."""
    _restore_stdout()

    parser = argparse.ArgumentParser(description="Multi-Account Gmail MCP Server")
    parser.add_argument(
        "--single-user",
        action="store_true",
        help="Run in single-user mode - bypass session mapping",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode: stdio (default) or streamable-http",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Run in read-only mode - only read-only scopes",
    )
    args = parser.parse_args()

    port = int(os.getenv("PORT", os.getenv("WORKSPACE_MCP_PORT", 8000)))
    base_uri = os.getenv("WORKSPACE_MCP_BASE_URI", "http://localhost")
    host = os.getenv("WORKSPACE_MCP_HOST", "0.0.0.0")
    external_url = os.getenv("WORKSPACE_EXTERNAL_URL")
    display_url = external_url if external_url else f"{base_uri}:{port}"

    safe_print("Multi-Account Gmail MCP Server")
    safe_print("=" * 35)
    try:
        version = metadata.version("gmail-mcp")
    except metadata.PackageNotFoundError:
        version = "dev"
    safe_print(f"   Version: {version}")
    safe_print(f"   Transport: {args.transport}")
    if args.transport == "streamable-http":
        safe_print(f"   URL: {display_url}")
    safe_print(f"   Mode: {'Single-user' if args.single_user else 'Multi-user'}")
    if args.read_only:
        safe_print("   Read-Only: Enabled")
    safe_print("")

    # Import Gmail tools
    from core.tool_registry import wrap_server_tool_method
    wrap_server_tool_method(server)

    from auth.scopes import set_enabled_tools, set_read_only
    set_enabled_tools(["gmail"])
    if args.read_only:
        set_read_only(True)

    safe_print("Loading Gmail tools...")
    try:
        import_module("gmail.gmail_tools")
        safe_print("   Gmail tools loaded")
    except ModuleNotFoundError as exc:
        logger.error("Failed to import Gmail tools: %s", exc, exc_info=True)
        safe_print(f"   Failed to load Gmail tools: {exc}")
        sys.exit(1)
    safe_print("")

    # Single-user mode
    if args.single_user:
        if os.getenv("MCP_ENABLE_OAUTH21", "false").lower() == "true":
            safe_print("Error: Single-user mode is incompatible with OAuth 2.1 mode")
            sys.exit(1)
        if is_stateless_mode():
            safe_print("Error: Single-user mode is incompatible with stateless mode")
            sys.exit(1)
        os.environ["MCP_SINGLE_USER_MODE"] = "1"
        safe_print("Single-user mode enabled")
        safe_print("")

    # Check credentials directory permissions
    if not is_stateless_mode():
        try:
            check_credentials_directory_permissions()
        except (PermissionError, OSError) as e:
            safe_print(f"Credentials directory permission check failed: {e}")
            sys.exit(1)

    try:
        set_transport_mode(args.transport)

        if args.transport == "streamable-http":
            configure_server_for_http()
            safe_print(f"Starting HTTP server on {base_uri}:{port}")

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((host, port))
            except OSError as e:
                safe_print(f"Port {port} is already in use: {e}")
                sys.exit(1)

            server.run(
                transport="streamable-http",
                host=host,
                port=port,
                stateless_http=is_stateless_mode(),
            )
        else:
            safe_print("Starting STDIO server")
            from auth.oauth_callback_server import ensure_oauth_callback_available
            success, error_msg = ensure_oauth_callback_available("stdio", port, base_uri)
            if success:
                safe_print(f"   OAuth callback: {display_url}/oauth2callback")
            else:
                safe_print(f"   Warning: OAuth callback failed: {error_msg}")

            safe_print("Ready for MCP connections")
            safe_print("")
            server.run()
    except KeyboardInterrupt:
        from auth.oauth_callback_server import cleanup_oauth_callback_server
        cleanup_oauth_callback_server()
        sys.exit(0)
    except Exception as e:
        safe_print(f"Server error: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        from auth.oauth_callback_server import cleanup_oauth_callback_server
        cleanup_oauth_callback_server()
        sys.exit(1)


if __name__ == "__main__":
    main()
