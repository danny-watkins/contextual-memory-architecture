"""MCP (Model Context Protocol) server.

Exposes the Retriever, Recorder, and graph commands as MCP tools so any
MCP-aware agent (Claude Code, the Anthropic SDK, etc.) can call them.

The server is stdio-based by default, which is what Claude Code expects.
Run with: cma mcp serve --project /path/to/your/cma-project
"""
