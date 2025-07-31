# Backend API Design

## **Overview**

The backend API provides RESTful endpoints and WebSocket communication for the NetBox MCP Chatbox Interface. It serves as the bridge between the frontend and the Claude Code SDK, managing sessions, context, and real-time communication.

## **API Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                     API Layer Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│  REST API Endpoints                                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Session       │  │    Context      │  │    Health       │ │
│  │   Management    │  │   Management    │  │   Monitoring    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  WebSocket Events                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │     Chat        │  │   Real-time     │  │   System        │ │
│  │  Communication │  │   Updates       │  │   Events        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Claude Code    │  │   Context       │  │   Session       │ │
│  │    Service      │  │   Service       │  │   Service       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## **REST API Endpoints**

### **Session Management**

#### **POST /api/sessions**
Create a new chat session.

**Request:**
```typescript
interface CreateSessionRequest {
  userId?: string
  preferences?: UserPreferences
}

interface UserPreferences {
  theme: 'light' | 'dark'
  autoSave: boolean
  contextRetention: number  // hours
  defaultNetBoxSite?: string
}
```

**Response:**
```typescript
interface CreateSessionResponse {
  sessionId: string
  userId: string
  createdAt: string
  preferences: UserPreferences
  status: 'active'
}
```

**Example:**
```bash
curl -X POST /api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user123",
    "preferences": {
      "theme": "dark",
      "autoSave": true,
      "contextRetention": 24
    }
  }'
```

#### **GET /api/sessions/:sessionId**
Retrieve session information.

**Response:**
```typescript
interface GetSessionResponse {
  sessionId: string
  userId: string
  createdAt: string
  lastActivity: string
  status: 'active' | 'inactive' | 'expired'
  messageCount: number
  entityCount: number
  contextSize: number
  preferences: UserPreferences
}
```

#### **PUT /api/sessions/:sessionId**
Update session preferences.

**Request:**
```typescript
interface UpdateSessionRequest {
  preferences?: Partial<UserPreferences>
  status?: 'active' | 'inactive'
}
```

#### **DELETE /api/sessions/:sessionId**
Delete a session and all associated data.

**Response:**
```typescript
interface DeleteSessionResponse {
  success: boolean
  deletedAt: string
  message: string
}
```

### **Context Management**

#### **GET /api/sessions/:sessionId/context**
Retrieve current session context.

**Response:**
```typescript
interface GetContextResponse {
  sessionId: string
  conversationHistory: ConversationMessage[]
  activeEntities: EntityReference[]
  toolHistory: ToolExecution[]
  contextSize: number
  lastUpdated: string
}
```

#### **GET /api/sessions/:sessionId/entities**
Get entities mentioned in the conversation.

**Query Parameters:**
- `type`: Filter by entity type (device, site, rack, etc.)
- `limit`: Maximum number of entities to return
- `sortBy`: Sort by (mentionCount, lastMentioned, relevance)

**Response:**
```typescript
interface GetEntitiesResponse {
  entities: EntityReference[]
  totalCount: number
  entityTypes: Record<string, number>
}
```

#### **POST /api/sessions/:sessionId/context/prune**
Manually trigger context pruning.

**Request:**
```typescript
interface PruneContextRequest {
  strategy: 'aggressive' | 'moderate' | 'conservative'
  targetTokens?: number
}
```

**Response:**
```typescript
interface PruneContextResponse {
  tokensBefore: number
  tokensAfter: number
  pruningStrategy: string
  itemsPruned: {
    messages: number
    entities: number
    toolHistory: number
  }
}
```

### **Message History**

#### **GET /api/sessions/:sessionId/messages**
Retrieve conversation history.

**Query Parameters:**
- `limit`: Maximum number of messages (default: 50)
- `offset`: Pagination offset
- `since`: ISO timestamp to get messages after
- `type`: Filter by message type (user, assistant, tool_result)

**Response:**
```typescript
interface GetMessagesResponse {
  messages: ConversationMessage[]
  totalCount: number
  hasMore: boolean
  nextOffset?: number
}
```

#### **POST /api/sessions/:sessionId/messages/export**
Export conversation history.

**Request:**
```typescript
interface ExportMessagesRequest {
  format: 'json' | 'markdown' | 'pdf'
  includeContext: boolean
  includeToolHistory: boolean
  dateRange?: {
    start: string
    end: string
  }
}
```

**Response:**
```typescript
interface ExportMessagesResponse {
  downloadUrl: string
  expiresAt: string
  format: string
  fileSize: number
}
```

### **Health and Status**

#### **GET /api/health**
System health check.

**Response:**
```typescript
interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  services: {
    redis: ServiceHealth
    claudeCode: ServiceHealth
    netboxMcp: ServiceHealth
  }
  metrics: {
    activeSessions: number
    activeProcesses: number
    memoryUsage: number
    uptime: number
  }
}

interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  latency?: number
  lastCheck: string
  error?: string
}
```

#### **GET /api/status/mcp**
NetBox MCP Server status.

**Response:**
```typescript
interface MCPStatusResponse {
  status: 'connected' | 'disconnected' | 'error'
  serverUrl: string
  toolsAvailable: number
  lastHealthCheck: string
  version?: string
  bridgetStatus: {
    enabled: boolean
    environment: string
    safetyLevel: string
  }
}
```

#### **GET /api/metrics**
Prometheus metrics endpoint.

**Response:** Prometheus format metrics

## **WebSocket Events**

### **Connection Management**

#### **Client → Server Events**

**join_session**
```typescript
interface JoinSessionEvent {
  sessionId: string
  userId?: string
}
```

**leave_session**
```typescript
interface LeaveSessionEvent {
  sessionId: string
}
```

### **Chat Communication**

#### **Client → Server Events**

**send_message**
```typescript
interface SendMessageEvent {
  sessionId: string
  message: string
  metadata?: {
    replyTo?: string
    context?: string
  }
}
```

**typing_start**
```typescript
interface TypingStartEvent {
  sessionId: string
}
```

**typing_stop**
```typescript
interface TypingStopEvent {
  sessionId: string
}
```

#### **Server → Client Events**

**message_stream**
```typescript
interface MessageStreamEvent {
  sessionId: string
  messageId: string
  chunk: string
  isComplete: boolean
  metadata?: {
    toolsUsed?: string[]
    entities?: EntityReference[]
  }
}
```

**message_complete**
```typescript
interface MessageCompleteEvent {
  sessionId: string
  messageId: string
  message: ConversationMessage
  context: {
    entitiesExtracted: EntityReference[]
    toolsExecuted: ToolExecution[]
    contextUpdated: boolean
  }
}
```

**typing_indicator**
```typescript
interface TypingIndicatorEvent {
  sessionId: string
  isTyping: boolean
  processingStage?: 'analyzing' | 'executing_tools' | 'generating_response'
}
```

### **System Events**

#### **Server → Client Events**

**tool_execution**
```typescript
interface ToolExecutionEvent {
  sessionId: string
  messageId: string
  tool: {
    name: string
    parameters: Record<string, any>
    status: 'starting' | 'running' | 'completed' | 'error'
  }
  result?: any
  error?: string
}
```

**context_update**
```typescript
interface ContextUpdateEvent {
  sessionId: string
  update: {
    type: 'entity_added' | 'entity_updated' | 'context_pruned'
    data: any
  }
}
```

**session_status**
```typescript
interface SessionStatusEvent {
  sessionId: string
  status: 'active' | 'inactive' | 'expired'
  reason?: string
}
```

**error**
```typescript
interface ErrorEvent {
  sessionId: string
  error: {
    code: string
    message: string
    details?: any
    recoverable: boolean
  }
}
```

**system_status**
```typescript
interface SystemStatusEvent {
  type: 'mcp_connected' | 'mcp_disconnected' | 'service_degraded' | 'service_restored'
  message: string
  affectedSessions?: string[]
}
```

## **Authentication & Authorization**

### **Authentication Middleware**

```typescript
interface AuthMiddleware {
  // JWT token validation
  validateToken(token: string): Promise<UserContext>
  
  // Session ownership validation
  validateSessionAccess(sessionId: string, userId: string): Promise<boolean>
  
  // Rate limiting
  checkRateLimit(userId: string, action: string): Promise<boolean>
}

interface UserContext {
  userId: string
  email: string
  roles: string[]
  permissions: string[]
  rateLimit: RateLimitInfo
}
```

### **Authorization Policies**

```typescript
interface AuthorizationPolicies {
  // Session management
  canCreateSession(user: UserContext): boolean
  canAccessSession(user: UserContext, sessionId: string): boolean
  canDeleteSession(user: UserContext, sessionId: string): boolean
  
  // Message operations
  canSendMessage(user: UserContext, sessionId: string): boolean
  canExportMessages(user: UserContext, sessionId: string): boolean
  
  // Admin operations
  canViewSystemMetrics(user: UserContext): boolean
  canManageAllSessions(user: UserContext): boolean
}
```

## **Error Handling**

### **Standard Error Response**

```typescript
interface ErrorResponse {
  error: {
    code: string
    message: string
    details?: any
  }
  requestId: string
  timestamp: string
}
```

### **Error Codes**

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SESSION_NOT_FOUND` | 404 | Session does not exist |
| `SESSION_EXPIRED` | 410 | Session has expired |
| `INVALID_REQUEST` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `CLAUDE_SERVICE_ERROR` | 502 | Claude Code service error |
| `MCP_SERVER_ERROR` | 502 | NetBox MCP server error |
| `CONTEXT_SIZE_EXCEEDED` | 413 | Context too large |
| `INTERNAL_ERROR` | 500 | Internal server error |

## **Rate Limiting**

### **Rate Limit Configuration**

```typescript
interface RateLimitConfig {
  // Message sending
  messages: {
    window: 900000  // 15 minutes
    max: 100        // requests per window
  }
  
  // Session creation
  sessions: {
    window: 3600000 // 1 hour
    max: 10         // sessions per window
  }
  
  // API calls
  api: {
    window: 900000  // 15 minutes
    max: 1000       // requests per window
  }
  
  // WebSocket connections
  websocket: {
    window: 60000   // 1 minute
    max: 30         // connections per window
  }
}
```

### **Rate Limit Headers**

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 900
```

## **Request/Response Examples**

### **Complete Chat Flow**

1. **Create Session:**
```bash
curl -X POST /api/sessions \
  -H "Authorization: Bearer <token>" \
  -d '{"userId": "user123"}'

# Response: {"sessionId": "sess_abc123", ...}
```

2. **Connect WebSocket:**
```javascript
const socket = io('/api/ws', {
  auth: { token: '<token>' }
})

socket.emit('join_session', { sessionId: 'sess_abc123' })
```

3. **Send Message:**
```javascript
socket.emit('send_message', {
  sessionId: 'sess_abc123',
  message: 'Show me devices in NYC datacenter'
})

// Listen for streaming response
socket.on('message_stream', (data) => {
  console.log('Chunk:', data.chunk)
})

socket.on('tool_execution', (data) => {
  console.log('Tool:', data.tool.name, data.tool.status)
})
```

4. **Get Context:**
```bash
curl -H "Authorization: Bearer <token>" \
  /api/sessions/sess_abc123/context

# Response: {"conversationHistory": [...], "activeEntities": [...]}
```

This API design provides a comprehensive interface for building rich, interactive chat experiences while maintaining security, performance, and scalability requirements.