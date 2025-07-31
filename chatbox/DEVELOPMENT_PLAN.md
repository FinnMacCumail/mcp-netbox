# Vue.js/Nuxt NetBox MCP Chatbox Interface - Development Strategy Plan

## **Project Overview**
Develop a Vue.js/Nuxt application that provides a web-based chatbox UI interface for interacting with Claude Code configured with the NetBox MCP Server. The application acts as a stateful wrapper around the Claude Code CLI, maintaining conversation context while leveraging the same MCP integration you use manually.

## **Core Integration Pattern**

### **SDK Architecture (Subprocess-based)**
The application uses the Claude Code TypeScript SDK, which internally:
1. **Spawns Claude Code CLI** as subprocess (same CLI you use manually)
2. **Uses your .mcp.json config** (same NetBox MCP server connection)
3. **Executes same MCP tools** (142+ NetBox tools from your server.py)
4. **Streams responses back** through the SDK to the web interface

```typescript
// Backend service that wraps the CLI
class ClaudeService {
  async sendMessage(message: string, context: ConversationContext) {
    // SDK internally does: subprocess.Popen(["claude-code", "--mcp-tools", "mcp__netbox__*"])
    const response = await this.claude.query({
      prompt: this.enrichWithContext(message, context),
      workingDirectory: process.env.PROJECT_ROOT,
      mcpConfig: '.mcp.json'  // Your existing MCP configuration
    })
    return response
  }
}
```

## **Architecture & Technology Stack**

### **Frontend Stack**
- **Nuxt 3** - Vue.js framework with SSR/SPA capabilities
- **TypeScript** - Type safety and better development experience
- **Tailwind CSS** - Utility-first CSS framework for responsive design
- **Pinia** - State management for Vue 3
- **Socket.io-client** - Real-time communication with backend
- **Marked.js** - Markdown rendering for Claude responses

### **Backend Integration**
- **Node.js/Express** - Backend API server
- **Claude Code TypeScript SDK** - Subprocess wrapper around CLI
- **Socket.io** - Real-time bidirectional communication
- **Redis** - Session and context storage
- **Docker** - Containerization and deployment

## **Context Retention System (Key Innovation)**

### **Stateful Wrapper Logic**
The web app provides what the CLI lacks - persistent conversation context:

```typescript
class ChatSession {
  private conversationHistory: Message[]
  private netboxEntities: EntityTracker
  
  async sendMessage(message: string) {
    // Enrich message with previous context
    const enrichedPrompt = `
Previous conversation:
${this.formatHistory()}

NetBox entities discussed:
- Site: NYC-DC01 (mentioned 3 messages ago)
- Device: switch-nyc-01 (current focus)

Current message: ${message}
`
    
    // Same CLI subprocess call, but with context
    const response = await claudeService.sendMessage(enrichedPrompt, this.getContext())
    
    // Store for future context
    this.conversationHistory.push({ message, response })
    return response
  }
}
```

### **Multi-Layer Context Storage**
- **Session Context** (Redis) - Current conversation state per user
- **Entity Context** - NetBox objects referenced (devices, sites, IPs)
- **Tool History** - Previous MCP tool executions and results
- **User Preferences** - Settings and frequently accessed entities

## **Core Application Flow**

### **User Experience Flow**
1. **User types**: "Show me devices in NYC datacenter"
2. **Frontend sends** to backend via WebSocket
3. **Backend enriches** with conversation context
4. **SDK spawns CLI** subprocess (same as manual `claude` command)
5. **CLI reads .mcp.json** (your existing configuration)
6. **CLI connects to NetBox MCP** (your running server.py)
7. **CLI executes** `netbox_list_all_devices site_name="NYC-DC01"`
8. **CLI streams results** back through SDK
9. **Backend stores context** and forwards to frontend
10. **Frontend displays** with rich formatting

### **Context Continuity**
Follow-up: "What's the status of the first device?"
- App remembers "first device" = "switch-nyc-01" from previous response
- Enriches new query with this context
- CLI executes `netbox_get_device_info device_name="switch-nyc-01"`

## **Component Architecture**

### **Frontend Structure**
```
components/
├── Chat/
│   ├── ChatInterface.vue      # Main chat container
│   ├── MessageList.vue        # Conversation history
│   ├── MessageInput.vue       # User input with context hints
│   ├── MessageBubble.vue      # Individual messages
│   └── TypingIndicator.vue    # Shows CLI processing
├── Context/
│   ├── ContextPanel.vue       # Shows current session context
│   ├── EntityTracker.vue      # NetBox entities in conversation
│   ├── NetBoxStatus.vue       # MCP server connection status
│   └── ToolHistory.vue        # Recent MCP tool executions
└── Common/
    ├── LoadingSpinner.vue
    └── ErrorBoundary.vue
```

### **Backend Structure**
```
backend/
├── server.js              # Express + Socket.io server
├── services/
│   ├── claudeService.js   # SDK wrapper (subprocess management)
│   ├── contextService.js  # Session context persistence
│   ├── mcpService.js      # MCP server health monitoring
│   └── entityService.js   # NetBox entity tracking
├── routes/
│   ├── chat.js            # Chat WebSocket handlers
│   ├── context.js         # Context management API
│   └── health.js          # System health endpoints
└── middleware/
    ├── auth.js            # Authentication middleware
    └── rateLimiter.js     # Rate limiting per session
```

## **Key Features Implementation**

### **1. Context-Aware Messaging**
- **Entity Recognition**: Automatically track NetBox objects mentioned
- **Reference Resolution**: "the switch" → "switch-nyc-01" from context
- **Context Injection**: Seamlessly add relevant history to CLI prompts
- **Context Pruning**: Intelligent trimming to stay within token limits

### **2. Real-time CLI Integration**
- **Subprocess Management**: Maintain CLI processes per session
- **Streaming Responses**: Real-time output from CLI to web UI
- **Tool Execution Tracking**: Show which MCP tools are being called
- **Error Propagation**: Surface CLI errors in user-friendly format

### **3. Session Management**
- **Multi-user Support**: Separate contexts per web session
- **Session Persistence**: Context survives browser refresh
- **Export/Import**: Save conversations for later reference
- **Context Sharing**: Share session context between team members

## **Development Phases**

### **Phase 1: Foundation (Weeks 1-2)**
- Set up Nuxt 3 project with TypeScript
- Implement basic chat UI components
- Create backend with Express + Socket.io
- Integrate Claude Code TypeScript SDK
- Basic message flow (no context yet)
- **Testing Suite**: Unit tests for core components, API endpoints, and WebSocket communication

### **Phase 2: CLI Integration (Weeks 3-4)**
- Configure SDK to use existing .mcp.json
- Implement subprocess management
- Add NetBox MCP server health monitoring
- Create tool execution tracking
- Test with your existing NetBox MCP server
- **Testing Suite**: Integration tests for Claude SDK, MCP tool execution tests, and subprocess management tests

### **Phase 3: Context System (Weeks 5-6)**
- Implement Redis-based session storage
- Build conversation history management
- Create NetBox entity tracking
- Add context enrichment logic
- Implement context pruning algorithms
- **Testing Suite**: Context storage tests, entity extraction tests, Redis integration tests, and context enrichment validation

### **Phase 4: Advanced Features (Weeks 7-8)**
- Real-time typing indicators during CLI processing
- Rich formatting for NetBox data responses
- Context panel showing current entities
- Export/import functionality
- Multi-session management
- **Testing Suite**: End-to-end user journey tests, export/import validation, UI component tests, and real-time feature tests

### **Phase 5: Polish & Deployment (Weeks 9-10)**
- UI/UX refinements and responsive design
- Comprehensive error handling
- Docker containerization
- Documentation and testing
- Production deployment setup
- **Testing Suite**: Production readiness tests, performance tests, security tests, and comprehensive system validation

## **Technical Implementation Details**

### **SDK Integration (Subprocess Pattern)**
```typescript
// services/claudeService.ts
import { ClaudeCode } from '@anthropic-ai/claude-code'

class ClaudeService {
  private claude: ClaudeCode
  
  constructor() {
    this.claude = new ClaudeCode({
      apiKey: process.env.ANTHROPIC_API_KEY,
      workingDirectory: process.env.PROJECT_ROOT,
      mcpConfig: '.mcp.json'  // Your existing NetBox MCP configuration
    })
  }
  
  async sendMessage(message: string, context: ConversationContext) {
    // This spawns: subprocess.Popen(["claude-code", "--mcp-tools", "mcp__netbox__*"])
    const enrichedPrompt = this.enrichWithContext(message, context)
    
    return await this.claude.query({
      prompt: enrichedPrompt,
      stream: true,  // Real-time streaming to web UI
      tools: ['mcp__netbox__*']  // All your NetBox MCP tools
    })
  }
}
```

### **Context Enrichment**
```typescript
// services/contextService.ts
class ContextService {
  enrichWithContext(message: string, session: ChatSession) {
    const entityContext = this.formatEntityContext(session.entities)
    const historyContext = this.formatHistory(session.messages)
    
    return `
Previous conversation context:
${historyContext}

NetBox entities we've discussed:
${entityContext}

User's current message: ${message}

Please refer to the above context when appropriate.
`
  }
}
```

### **WebSocket Real-time Communication**
```typescript
// Real-time chat with CLI subprocess streaming
io.on('connection', (socket) => {
  socket.on('chat:message', async (data) => {
    const session = await getSession(data.sessionId)
    
    // Stream responses from CLI subprocess
    for await (const chunk of claudeService.sendMessage(data.message, session.context)) {
      socket.emit('chat:stream', chunk)
    }
    
    // Update session context with new exchange
    await session.addMessage(data.message, response)
  })
})
```

## **Deployment Strategy**
- **Docker Compose** setup including your NetBox MCP server
- **Environment configuration** pointing to your .mcp.json
- **Session persistence** with Redis
- **Load balancing** for multiple concurrent users
- **Monitoring** for CLI subprocess health

## **Key Benefits**
1. **Same MCP Integration**: Uses your existing NetBox MCP server setup
2. **Enhanced UX**: Web interface with context retention
3. **Multi-user**: Multiple people can use same NetBox MCP server
4. **Persistent Sessions**: Context survives browser refresh
5. **Rich Formatting**: Better display of NetBox data than CLI
6. **Team Collaboration**: Shareable conversation contexts

## **Success Criteria**
- Web interface provides same NetBox functionality as CLI
- Context retention enables natural follow-up conversations  
- Multiple users can work simultaneously without conflicts
- Session persistence survives application restarts
- Performance matches or exceeds direct CLI usage

This plan provides a sophisticated web wrapper around your existing Claude Code + NetBox MCP setup, adding the context retention and multi-user capabilities that make it suitable for team infrastructure management.