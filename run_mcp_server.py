"""Entry point for the MarketCanvas MCP server.

Usage:
    conda activate marketcanvas && python run_mcp_server.py [--transport stdio]
"""
import argparse

from marketcanvas_env import MCPServer


def main():
    parser = argparse.ArgumentParser(description="MarketCanvas MCP Server")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Default target prompt for the environment",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum steps per episode (default: 20)",
    )
    args = parser.parse_args()

    server = MCPServer(
        target_prompt=args.prompt,
        max_steps=args.max_steps,
    )
    print(f"Starting MarketCanvas MCP Server (transport={args.transport})...")
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
