# NetBox MCP Chatbox - Technical Architecture

## **System Overview**

The NetBox MCP Chatbox is a three-layer web application that provides a stateful interface to the existing NetBox MCP Server while maintaining full compatibility with the Claude Code CLI workflow.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Web Browser (Client)                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Chat UI       │  │  Context Panel  │  │   Tool History  │ │
│  │   Components    │  │   Components    │  │   Components    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                         WebSocket Connection
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Server (Node.js)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Socket.io     │  │   Claude Code   │  │   Context       │ │
│  │   Server        │  │   SDK Service   │  │   Management    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                           │                                     │
│                    Subprocess Spawn                             │
│                           │                                     │
│  ┌─────────────────────────────────────────┐                   │
│  │         Claude Code CLI Process         │                   │
│  │      (Same as manual `claude`)          │                   │
│  └─────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                         Reads .mcp.json
                                │
┌─────────────────────────────────────────────────────────────────┐
│                 NetBox MCP Server (Python)                     │
│                    (Your existing server.py)                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   142+ MCP      │  │   Bridget AI    │  │   NetBox API    │ │
│  │   Tools         │  │   Persona       │  │   Client        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                         REST API Calls
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      NetBox Instance                           │
│                   (Your existing NetBox)                       │
└─────────────────────────────────────────────────────────────────┘
```

## **Layer Breakdown**

### **Layer 1: Frontend (Vue.js/Nuxt)**

**Purpose**: Provides the web-based chat interface with context visualization

**Components**:
- **Chat Interface**: Message input/output with real-time streaming
- **Context Panel**: Shows current conversation entities and history
- **Status Indicators**: NetBox MCP server health and tool execution status
- **State Management**: Pinia stores for UI state and session data

**Key Technologies**:
- Nuxt 3 (Vue.js framework)
- TypeScript for type safety
- Tailwind CSS for styling
- Socket.io-client for real-time communication
- Pinia for state management

### **Layer 2: Backend API (Node.js/Express)**

**Purpose**: Manages sessions, context, and interfaces with Claude Code SDK

**Core Services**:
- **Chat Service**: WebSocket handlers for real-time messaging
- **Claude Service**: Manages Claude Code SDK subprocess spawning
- **Context Service**: Session persistence and context enrichment
- **Entity Service**: Tracks NetBox objects mentioned in conversations

**Key Technologies**:
- Node.js/Express server
- Socket.io for WebSocket management
- Claude Code TypeScript SDK
- Redis for session storage
- Process management for CLI subprocesses

### **Layer 3: MCP Integration (Existing Infrastructure)**

**Purpose**: Leverages your existing NetBox MCP Server setup

**Components**:
- **Claude Code CLI**: Same binary you use manually
- **MCP Configuration**: Your existing `.mcp.json` file
- **NetBox MCP Server**: Your running `server.py` with 142+ tools
- **NetBox Instance**: Your existing NetBox deployment

## **Data Flow Architecture**

### **Request Flow**
```
User Input → Frontend → WebSocket → Backend → Claude SDK → CLI Subprocess → MCP Server → NetBox
```

### **Response Flow**
```
NetBox → MCP Server → CLI Subprocess → SDK Stream → Backend → WebSocket → Frontend → User
```

### **Context Flow**
```
Previous Messages → Context Service → Enriched Prompt → Claude SDK → Enhanced Response
```

## **Context Management System**

### **Context Storage Layers**

```typescript
interface SessionContext {
  sessionId: string
  userId: string
  conversationHistory: Message[]
  netboxEntities: EntityReference[]
  toolExecutionHistory: ToolExecution[]
  userPreferences: UserPreferences
  createdAt: Date
  lastActivity: Date
}

interface EntityReference {
  type: 'device' | 'site' | 'rack' | 'ip' | 'vlan' | 'prefix'
  name: string
  id: number
  mentionedAt: Date
  context: string
  relatedEntities: EntityReference[]
}
```

### **Context Enrichment Pipeline**

1. **Message Analysis**: Parse user input for NetBox entity references
2. **History Retrieval**: Pull relevant conversation history
3. **Entity Resolution**: Match mentions to known NetBox objects
4. **Context Assembly**: Build enriched prompt with context
5. **Token Management**: Trim context to stay within limits

```typescript
class ContextEnrichmentPipeline {
  async enrichMessage(message: string, session: SessionContext): Promise<string> {
    // 1. Extract potential NetBox entities from message
    const entities = await this.extractEntities(message)
    
    // 2. Resolve entities against conversation history
    const resolvedEntities = await this.resolveEntities(entities, session)
    
    // 3. Select relevant conversation history
    const relevantHistory = await this.selectRelevantHistory(session, entities)
    
    // 4. Build context-enriched prompt
    return this.buildEnrichedPrompt(message, resolvedEntities, relevantHistory)
  }
}
```

## **Session Management Architecture**

### **Session Lifecycle**

```typescript
interface SessionManager {
  createSession(userId: string): Promise<SessionContext>
  getSession(sessionId: string): Promise<SessionContext>
  updateSession(sessionId: string, updates: Partial<SessionContext>): Promise<void>
  addMessage(sessionId: string, message: Message): Promise<void>
  addEntityReference(sessionId: string, entity: EntityReference): Promise<void>
  pruneSession(sessionId: string): Promise<void>  // Remove old context
  destroySession(sessionId: string): Promise<void>
}
```

### **Redis Schema**

```
sessions:{sessionId}        → Full session context (JSON)
sessions:{sessionId}:lock   → Session lock for concurrent access
user_sessions:{userId}      → Set of active session IDs
entity_index:{entityType}   → Index of entities by type
```

## **Claude Code SDK Integration**

### **Subprocess Management**

```typescript
class ClaudeCodeService {
  private processes: Map<string, ChildProcess> = new Map()
  
  async sendMessage(sessionId: string, message: string, context: SessionContext) {
    // Get or create CLI subprocess for this session
    const process = await this.getOrCreateProcess(sessionId, context)
    
    // Send enriched message to CLI
    const enrichedMessage = await this.contextService.enrichMessage(message, context)
    
    // Stream response back
    return this.streamResponse(process, enrichedMessage)
  }
  
  private async getOrCreateProcess(sessionId: string, context: SessionContext) {
    if (!this.processes.has(sessionId)) {
      const process = spawn('claude-code', [
        '--non-interactive',
        '--working-directory', context.workingDirectory,
        '--mcp-config', context.mcpConfigPath
      ], {
        stdio: ['pipe', 'pipe', 'pipe']
      })
      
      this.processes.set(sessionId, process)
    }
    
    return this.processes.get(sessionId)
  }
}
```

### **Configuration Mapping**

The backend maps your existing MCP configuration:

```typescript
interface MCPConfiguration {
  configPath: string        // Path to your .mcp.json
  workingDirectory: string  // Project root directory
  netboxServerUrl: string   // Your MCP server endpoint
  tools: string[]          // Available MCP tools
}
```

## **Real-time Communication**

### **WebSocket Event Schema**

```typescript
// Client → Server Events
interface ClientEvents {
  'chat:join': { sessionId: string }
  'chat:message': { message: string, sessionId: string }
  'chat:typing': { sessionId: string }
  'context:request': { sessionId: string }
}

// Server → Client Events
interface ServerEvents {
  'chat:message': { message: string, sender: 'user' | 'assistant', timestamp: Date }
  'chat:stream': { chunk: string, isComplete: boolean }
  'chat:typing': { isTyping: boolean }
  'context:update': { entities: EntityReference[] }
  'tool:execution': { tool: string, status: 'running' | 'completed' | 'error' }
  'error': { message: string, code: string }
}
```

### **Stream Processing**

```typescript
class StreamProcessor {
  async processClaudeStream(stream: AsyncIterable<string>, socket: Socket) {
    for await (const chunk of stream) {
      // Parse chunk for special markers
      if (chunk.includes('🔧 Using tool:')) {
        const tool = this.extractToolName(chunk)
        socket.emit('tool:execution', { tool, status: 'running' })
      }
      
      // Forward chunk to client
      socket.emit('chat:stream', { 
        chunk, 
        isComplete: false 
      })
    }
    
    socket.emit('chat:stream', { 
      chunk: '', 
      isComplete: true 
    })
  }
}
```

## **Error Handling & Resilience**

### **Failure Scenarios**

1. **CLI Process Crashes**: Automatic restart with session context recovery
2. **MCP Server Unavailable**: Graceful degradation with status indication
3. **Redis Connection Loss**: In-memory fallback with persistence recovery
4. **WebSocket Disconnection**: Automatic reconnection with state sync

### **Recovery Strategies**

```typescript
class ResilienceManager {
  async handleCLIProcessFailure(sessionId: string) {
    // 1. Log the failure
    this.logger.error(`CLI process failed for session ${sessionId}`)
    
    // 2. Clean up the failed process
    this.processes.delete(sessionId)
    
    // 3. Notify client
    this.notifyClient(sessionId, 'cli:process:restarting')
    
    // 4. Restart with session context
    await this.restartCLIProcess(sessionId)
  }
  
  async handleMCPServerDisconnection() {
    // 1. Set global status to degraded
    this.setStatus('degraded')
    
    // 2. Notify all active sessions
    this.broadcastToAll('mcp:server:disconnected')
    
    // 3. Implement retry logic
    await this.retryMCPConnection()
  }
}
```

## **Performance Considerations**

### **Optimization Strategies**

1. **Context Pruning**: Intelligent removal of old context to manage token limits
2. **Entity Caching**: Cache frequently accessed NetBox entities
3. **Connection Pooling**: Reuse CLI processes where possible
4. **Response Streaming**: Real-time chunk delivery to improve perceived performance

### **Scaling Patterns**

```typescript
interface ScalingConfiguration {
  maxConcurrentSessions: number
  maxCLIProcesses: number
  contextRetentionDays: number
  entityCacheSize: number
  sessionTimeoutMinutes: number
}
```

This architecture provides a robust, scalable foundation for the chatbox interface while maintaining full compatibility with your existing NetBox MCP Server infrastructure.