# NetBox Read/Write MCP Server

A Model Context Protocol (MCP) server that provides safe, intelligent read/write access to NetBox instances. Designed with safety-first principles for Large Language Model automation.

## 🎯 Project Vision

Create a robust bridge between LLMs and NetBox that enables:
- **Safe Write Operations**: All mutations require explicit confirmation
- **Idempotent Operations**: Consistent results regardless of call frequency  
- **Integration Ready**: Designed for enterprise network discovery workflows
- **Enterprise Grade**: Production-ready with comprehensive safety mechanisms

## 🚧 Development Status

**Current Version**: v0.1.0-dev (Phase 1: Foundation & Read-Only Core)

This project is under active development. See [GitHub Issues](https://github.com/Deployment-Team/netbox-mcp/issues) for current roadmap and progress.

## 📋 Roadmap

Development follows a phased approach with safety-first principles:

- **v0.1** - Foundation & Read-Only Core *(current)*
- **v0.2** - Initial Write Capabilities & Safety  
- **v0.3** - Advanced R/W Operations & Relations
- **v0.4** - Enterprise Features & Integration-readiness
- **v1.0** - Production-readiness & Full Integration

## 🔧 Development Setup

### Prerequisites

- Python 3.9+
- Access to a NetBox instance (Cloud or self-hosted)
- NetBox API token with appropriate permissions

### Installation

```bash
# Clone the repository
git clone https://github.com/Deployment-Team/netbox-mcp.git
cd netbox-mcp

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Configuration

Copy the example environment file and configure your NetBox instance:

```bash
cp .env.example .env
# Edit .env with your NetBox URL and API token
```

## 🏗️ Architecture

The server follows a modular design:

- **`netbox_mcp.client`**: NetBox API client with safety mechanisms
- **`netbox_mcp.server`**: MCP server with tool definitions
- **`netbox_mcp.config`**: Configuration management
- **Safety Layer**: Confirmation parameters and dry-run mode throughout

## 🔒 Safety Features

**CRITICAL**: This server can perform write operations on NetBox data.

### Built-in Safety Mechanisms:

- **Confirmation Required**: All write operations require `confirm=True`
- **Dry-Run Mode**: Global `NETBOX_DRY_RUN=true` prevents actual writes
- **Comprehensive Logging**: All mutations logged with detailed context
- **Idempotent Design**: Safe to retry operations
- **Error Handling**: Graceful failure with clear error messages

## 📊 Current Implementation Status

**✅ Completed:**
- Project structure and dependencies
- Exception handling framework
- Configuration foundation

**🚧 In Progress:**
- NetBox API client (read-only)
- Basic MCP server implementation

**📅 Upcoming:**
- Write operations with safety controls
- Idempotent ensure methods
- Docker containerization

## 🤝 Contributing

This project is under active development. See our [GitHub Issues](https://github.com/Deployment-Team/netbox-mcp/issues) for:

- Current development priorities
- Feature requests and roadmap
- Bug reports and discussions

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- Enterprise network automation tools - Production-ready MCP servers
- [NetBox](https://github.com/netbox-community/netbox) - The network documentation and IPAM application

---

**⚠️ Development Notice**: This is a development version with write capabilities. Always use proper safety measures and test in non-production environments.