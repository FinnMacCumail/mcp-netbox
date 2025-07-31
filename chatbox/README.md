# NetBox MCP Chatbox Interface

A Vue.js/Nuxt web application that provides a conversational interface for managing NetBox infrastructure through Claude Code with the NetBox MCP Server.

## Overview

This chatbox interface acts as a stateful web wrapper around your existing Claude Code + NetBox MCP Server setup, adding context retention and multi-user capabilities while leveraging the same 142+ NetBox MCP tools you use in the CLI.

### Key Features

- **Context Retention**: Maintains conversation history and NetBox entity tracking
- **Multi-User Support**: Multiple simultaneous users with isolated sessions
- **Real-time Interface**: WebSocket-based streaming responses
- **Same MCP Integration**: Uses your existing `.mcp.json` configuration
- **Rich UI**: Web-based interface with markdown rendering and syntax highlighting

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Redis server for session storage
- Running NetBox MCP Server (your existing `server.py`)
- Claude Code CLI configured with NetBox MCP Server
- Valid Anthropic API key

### Installation

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start development server
npm run dev
```

### Configuration

Set the following environment variables:

```bash
ANTHROPIC_API_KEY=your_api_key
NETBOX_MCP_CONFIG_PATH=/path/to/your/.mcp.json
REDIS_URL=redis://localhost:6379
```

## Technology Stack

### Frontend
- **Nuxt 3** - Vue.js framework with SSR/SPA capabilities
- **TypeScript** - Type safety and development experience
- **Tailwind CSS** - Utility-first CSS framework
- **Pinia** - State management
- **Socket.io-client** - Real-time communication

### Backend
- **Node.js/Express** - API server
- **Claude Code TypeScript SDK** - CLI subprocess wrapper
- **Socket.io** - Real-time bidirectional communication
- **Redis** - Session and context storage

## Architecture

The application follows a three-layer architecture:

1. **Frontend Layer**: Vue.js/Nuxt chatbox interface
2. **Backend API Layer**: Express server with Claude Code SDK integration
3. **MCP Integration Layer**: Your existing NetBox MCP Server

### Integration Pattern

```
User Input → Web UI → Backend API → Claude Code SDK → CLI Subprocess → .mcp.json → NetBox MCP Server → NetBox API
```

The Claude Code SDK internally spawns the same CLI process you use manually, ensuring identical functionality with added web interface and context management.

## Project Structure

```
chatbox/
├── README.md                    # This file
├── DEVELOPMENT_PLAN.md          # Complete development strategy
├── ARCHITECTURE.md              # Technical architecture details
├── docs/                        # Detailed documentation
│   ├── INTEGRATION.md          # Claude Code SDK integration
│   ├── CONTEXT_SYSTEM.md       # Context retention system
│   ├── DEPLOYMENT.md           # Deployment guide
│   └── API_DESIGN.md           # Backend API specifications
├── examples/                    # Configuration and code examples
│   ├── sample-config.json      # Example configuration
│   ├── sample-session.json     # Session data structure
│   └── integration-example.js  # SDK integration example
└── planning/                    # Development planning docs
    ├── PHASES.md               # Development phases
    ├── COMPONENTS.md           # Component specifications
    └── TIMELINE.md             # Project timeline
```

## Development Phases

1. **Foundation** (Weeks 1-2): Nuxt setup, basic chat UI, backend API
2. **CLI Integration** (Weeks 3-4): Claude Code SDK, MCP server connection
3. **Context System** (Weeks 5-6): Session management, entity tracking
4. **Advanced Features** (Weeks 7-8): Real-time features, rich formatting
5. **Polish & Deployment** (Weeks 9-10): Production setup, monitoring

## Documentation

- [Development Plan](DEVELOPMENT_PLAN.md) - Complete strategy and implementation plan
- [Architecture](ARCHITECTURE.md) - Technical architecture and design patterns
- [Integration Guide](docs/INTEGRATION.md) - Claude Code SDK integration details
- [Context System](docs/CONTEXT_SYSTEM.md) - Context retention and session management
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment instructions
- [API Design](docs/API_DESIGN.md) - Backend API specifications

## Contributing

This project enhances your existing NetBox MCP Server with a web interface. Development follows the structured phases outlined in the development plan.

## License

Same as parent project - MIT License

---

**Note**: This chatbox interface is designed to work with your existing NetBox MCP Server setup. It doesn't replace any existing functionality but adds a web-based interface with context retention capabilities.