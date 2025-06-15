# Remote MCP Server Deployment Guide

This guide covers deploying the BibTeX MCP server as a remote service using Docker and Caddy.

## Overview

The deployment uses:
- **Docker**: Containerizes the FastMCP Python server
- **Caddy**: Reverse proxy for HTTPS termination and SSE support  
- **Server-Sent Events (SSE)**: Transport protocol for remote MCP communication

## Architecture

```
Client (Claude Desktop, etc.) 
    ↓ HTTPS/SSE
Caddy Reverse Proxy 
    ↓ HTTP (internal)
FastMCP Server Container
    ↓ HTTP APIs
Academic Providers (DBLP, arXiv, etc.)
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Domain name (for production) or localhost for development
- Optional: Semantic Scholar API key for increased rate limits

### 1. Environment Setup

Create a `.env` file:

```bash
# Optional API keys
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here

# Optional proxy settings
HTTP_PROXY=
PROVIDER_TIMEOUT=4
```

### 2. Development Deployment

For local testing:

```bash
# Start services
docker-compose up -d

# Test the server (check if port is listening)
curl http://localhost:8080/sse

# Test MCP endpoint (requires MCP client)
# Server URL: http://localhost:8080
```

### 3. Production Deployment

1. **Update Caddyfile**: Replace `mcp.example.com` with your domain
2. **DNS Setup**: Point your domain to your server
3. **Deploy**:

```bash
docker-compose up -d
```

Caddy will automatically obtain Let's Encrypt certificates.

## Configuration Details

### Docker Configuration

The `Dockerfile` uses:
- Multi-stage build for optimized image size
- Python 3.11 slim base image  
- UV package manager for fast dependency installation
- Non-root user for security
- Health checks for monitoring

### Caddy Configuration

Key settings for MCP/SSE support:

```caddyfile
reverse_proxy localhost:8000 {
    # CRITICAL: Disable buffering for Server-Sent Events
    flush_interval -1
}
```

### FastMCP Server

The server runs with SSE transport:

```bash
fastmcp run reference_mcp.server:mcp --transport sse --host 0.0.0.0 --port 8000
```

## MCP Client Configuration

### Claude Desktop

Add to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "bibtex-search": {
      "command": "node",
      "args": [
        "/path/to/mcp-client.js",
        "https://your-domain.com"
      ]
    }
  }
}
```

### Generic MCP Client

For SSE-based remote servers:

```typescript
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const transport = new SSEClientTransport(
  new URL("https://your-domain.com/sse")
);
```

## Authentication (Optional)

For production deployments, consider adding authentication:

### Basic Auth with Caddy

```caddyfile
mcp.example.com {
    basicauth /sse {
        username $2a$14$hashed_password
    }
    
    reverse_proxy localhost:8000 {
        flush_interval -1
    }
}
```

### API Key Authentication

Modify the MCP server to require API keys:

```python
@mcp.middleware
async def auth_middleware(request, call_next):
    api_key = request.headers.get("Authorization")
    if not api_key or not validate_api_key(api_key):
        raise HTTPException(401, "Unauthorized")
    return await call_next(request)
```

## Monitoring and Logging

### Health Checks

- Docker health check: Socket connection test to port 8000
- Container status: `docker-compose ps`
- External monitoring: Test SSE endpoint connection

### Logging

Logs are available:
- Docker logs: `docker-compose logs mcp-server`
- Caddy logs: `./logs/mcp-server.log`
- Application logs: Structured JSON output

### Metrics

Consider adding metrics collection:

```python
from prometheus_client import Counter, Histogram

search_requests = Counter('mcp_search_requests_total', 'Total search requests')
search_duration = Histogram('mcp_search_duration_seconds', 'Search duration')
```

## Scaling Considerations

### Horizontal Scaling

For multiple instances:

```yaml
services:
  mcp-server:
    deploy:
      replicas: 3
```

Update Caddy for load balancing:

```caddyfile
reverse_proxy localhost:8000 localhost:8001 localhost:8002 {
    flush_interval -1
    lb_policy round_robin
}
```

### Resource Limits

Adjust based on usage:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 1G
    reservations:
      memory: 512M
```

## Security Best Practices

1. **Use HTTPS**: Automatic with Caddy in production
2. **Network isolation**: Use Docker networks
3. **Resource limits**: Prevent resource exhaustion
4. **Regular updates**: Keep base images updated
5. **Secrets management**: Use Docker secrets or external secret stores

## Troubleshooting

### SSE Connection Issues

```bash
# Test SSE endpoint directly
curl -H "Accept: text/event-stream" https://your-domain.com/sse

# Check if buffering is disabled
curl -H "Accept: text/event-stream" -v https://your-domain.com/sse
```

### Container Issues

```bash
# Check container logs
docker-compose logs mcp-server

# Check container health
docker-compose ps

# Restart services
docker-compose restart
```

### DNS/Certificate Issues

```bash
# Check Caddy logs
docker-compose logs caddy

# Test certificate
curl -I https://your-domain.com
```

## Performance Optimization

### Provider Timeouts

Adjust timeouts in `.env`:

```bash
PROVIDER_TIMEOUT=2  # Reduce for faster responses
```

### Caching

Consider adding Redis for response caching:

```yaml
services:
  redis:
    image: redis:alpine
    
  mcp-server:
    environment:
      - REDIS_URL=redis://redis:6379
```

## Cost Optimization

### Resource Efficiency

- Use Alpine images
- Implement connection pooling
- Add response caching
- Set appropriate resource limits

### Provider API Usage

- Use API keys for higher rate limits
- Implement intelligent provider selection
- Add retry logic with exponential backoff

## Migration from Local to Remote

To migrate existing local MCP configurations:

1. **Update client configuration**: Change from stdio to SSE transport
2. **Update URLs**: Point to remote server
3. **Add authentication**: If required
4. **Test connectivity**: Verify SSE connection works
5. **Monitor performance**: Check latency vs local setup

## Next Steps

- Set up monitoring and alerting
- Implement authentication if needed
- Configure backup and disaster recovery
- Set up CI/CD for automated deployments
- Consider adding rate limiting for public deployments
