FROM python:3.12-slim

WORKDIR /app
COPY server.py pyproject.toml README.md ./

# no third-party dependencies on purpose: stdio MCP server, stdlib only
RUN useradd -m -u 1000 mcp
USER mcp

ENTRYPOINT ["python", "server.py"]
