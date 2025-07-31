# Context Retention System Design

## **Overview**

The context retention system is the core innovation that transforms the stateless Claude Code CLI into a stateful, conversational web interface. It maintains conversation history, tracks NetBox entities, and provides intelligent context injection for multi-turn interactions.

## **Context Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                     Context System Layers                      │
├─────────────────────────────────────────────────────────────────┤
│  Session Context (Redis)                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Conversation   │  │    NetBox       │  │   Tool          │ │
│  │    History      │  │   Entities      │  │  Executions     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Entity Index (Redis)                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Device        │  │     Site        │  │      IP         │ │
│  │  References     │  │  References     │  │  References     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Context Cache (Memory)                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Frequent      │  │   Recently      │  │   Computed      │ │
│  │   Entities      │  │   Accessed      │  │   Context       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## **Core Data Models**

### **Session Context**

```typescript
interface SessionContext {
  sessionId: string
  userId: string
  createdAt: Date
  lastActivity: Date
  
  // Conversation tracking
  conversationHistory: ConversationMessage[]
  currentTopic: string | null
  
  // NetBox entity tracking
  mentionedEntities: EntityReference[]
  activeEntities: EntityReference[]  // Currently relevant entities
  
  // Tool execution tracking
  toolHistory: ToolExecution[]
  lastToolResults: Record<string, any>
  
  // User preferences
  preferences: UserPreferences
  
  // Context metadata
  tokenUsage: TokenUsageStats
  contextSize: number
  pruningHistory: PruningEvent[]
}
```

### **Entity Reference**

```typescript
interface EntityReference {
  // Entity identification
  type: NetBoxEntityType
  name: string
  id: number
  slug?: string
  
  // Context tracking
  firstMentioned: Date
  lastMentioned: Date
  mentionCount: number
  
  // Relationship tracking
  relatedEntities: EntityRelation[]
  parentEntity?: EntityReference
  childEntities: EntityReference[]
  
  // Conversation context
  mentionContext: MentionContext[]
  relevanceScore: number
  
  // NetBox data cache
  cachedData?: any
  cacheExpiry?: Date
}

type NetBoxEntityType = 
  | 'device' | 'site' | 'rack' | 'manufacturer' | 'device_type' | 'device_role'
  | 'interface' | 'cable' | 'power_port' | 'power_outlet' | 'power_feed'
  | 'ip_address' | 'prefix' | 'vlan' | 'vrf'
  | 'tenant' | 'tenant_group' | 'contact'
  | 'cluster' | 'virtual_machine' | 'vm_interface'
```

### **Conversation Message**

```typescript
interface ConversationMessage {
  id: string
  sessionId: string
  
  // Message content
  content: string
  sender: 'user' | 'assistant'
  timestamp: Date
  
  // Message metadata
  messageType: 'query' | 'response' | 'tool_result' | 'error'
  
  // Entity extraction
  extractedEntities: EntityReference[]
  entityResolutions: EntityResolution[]
  
  // Tool execution
  toolsUsed: string[]
  toolResults: Record<string, any>
  
  // Context metadata
  contextUsed: ContextSnapshot
  tokenCount: number
}
```

## **Context Management Services**

### **Session Manager**

```typescript
class SessionManager {
  private redis: RedisClient
  private cache: Map<string, SessionContext> = new Map()
  
  async createSession(userId: string): Promise<SessionContext> {
    const sessionId = this.generateSessionId()
    
    const session: SessionContext = {
      sessionId,
      userId,
      createdAt: new Date(),
      lastActivity: new Date(),
      conversationHistory: [],
      currentTopic: null,
      mentionedEntities: [],
      activeEntities: [],
      toolHistory: [],
      lastToolResults: {},
      preferences: await this.loadUserPreferences(userId),
      tokenUsage: this.initTokenUsage(),
      contextSize: 0,
      pruningHistory: []
    }
    
    await this.saveSession(session)
    this.cache.set(sessionId, session)
    
    return session
  }
  
  async getSession(sessionId: string): Promise<SessionContext | null> {
    // Check cache first
    if (this.cache.has(sessionId)) {
      const session = this.cache.get(sessionId)!
      session.lastActivity = new Date()
      return session
    }
    
    // Load from Redis
    const sessionData = await this.redis.get(`session:${sessionId}`)
    if (!sessionData) return null
    
    const session = JSON.parse(sessionData) as SessionContext
    this.cache.set(sessionId, session)
    
    return session
  }
  
  async updateSession(sessionId: string, updates: Partial<SessionContext>) {
    const session = await this.getSession(sessionId)
    if (!session) throw new Error('Session not found')
    
    Object.assign(session, updates)
    session.lastActivity = new Date()
    
    await this.saveSession(session)
  }
}
```

### **Entity Tracker**

```typescript
class EntityTracker {
  private entityExtractor: EntityExtractor
  private entityResolver: EntityResolver
  
  async trackMessageEntities(
    message: ConversationMessage, 
    session: SessionContext
  ): Promise<EntityReference[]> {
    // 1. Extract potential entities from message
    const potentialEntities = await this.entityExtractor.extract(message.content)
    
    // 2. Resolve entities against conversation history and NetBox
    const resolvedEntities: EntityReference[] = []
    
    for (const potential of potentialEntities) {
      const resolved = await this.resolveEntity(potential, session)
      if (resolved) {
        resolvedEntities.push(resolved)
      }
    }
    
    // 3. Update session entity tracking
    await this.updateSessionEntities(session, resolvedEntities)
    
    return resolvedEntities
  }
  
  private async resolveEntity(
    potential: PotentialEntity, 
    session: SessionContext
  ): Promise<EntityReference | null> {
    // Try to resolve against conversation history first
    const historicalMatch = this.findHistoricalEntity(potential, session)
    if (historicalMatch) {
      return this.updateEntityReference(historicalMatch, potential)
    }
    
    // Try to resolve against NetBox via MCP tools
    const netboxMatch = await this.resolveAgainstNetBox(potential)
    if (netboxMatch) {
      return this.createEntityReference(netboxMatch, potential)
    }
    
    return null
  }
  
  private async resolveAgainstNetBox(
    potential: PotentialEntity
  ): Promise<NetBoxEntity | null> {
    try {
      // Use appropriate MCP tool based on entity type
      const tool = this.selectResolutionTool(potential.type)
      const result = await this.mcpClient.executeTool(tool, {
        name: potential.name,
        limit: 1
      })
      
      return result.length > 0 ? result[0] : null
      
    } catch (error) {
      this.logger.warn('Entity resolution failed:', error)
      return null
    }
  }
}
```

### **Context Enricher**

```typescript
class ContextEnricher {
  async enrichMessage(
    message: string, 
    session: SessionContext
  ): Promise<string> {
    // 1. Analyze message for context requirements
    const contextRequirements = await this.analyzeContextNeeds(message, session)
    
    // 2. Select relevant conversation history
    const relevantHistory = await this.selectRelevantHistory(
      session, 
      contextRequirements
    )
    
    // 3. Select relevant entities
    const relevantEntities = await this.selectRelevantEntities(
      session, 
      contextRequirements
    )
    
    // 4. Build enriched prompt
    return this.buildEnrichedPrompt(
      message, 
      relevantHistory, 
      relevantEntities, 
      session
    )
  }
  
  private async buildEnrichedPrompt(
    message: string,
    history: ConversationMessage[],
    entities: EntityReference[],
    session: SessionContext
  ): Promise<string> {
    const sections: string[] = []
    
    // Add conversation context
    if (history.length > 0) {
      sections.push(this.formatConversationHistory(history))
    }
    
    // Add entity context
    if (entities.length > 0) {
      sections.push(await this.formatEntityContext(entities))
    }
    
    // Add current topic context
    if (session.currentTopic) {
      sections.push(`Current conversation topic: ${session.currentTopic}`)
    }
    
    // Add the actual user message
    sections.push(`Current user message: ${message}`)
    
    // Add instruction for context usage
    sections.push(this.buildContextInstructions(entities))
    
    return sections.join('\n\n')
  }
  
  private async formatEntityContext(entities: EntityReference[]): Promise<string> {
    const entityDescriptions: string[] = []
    
    for (const entity of entities) {
      const description = await this.buildEntityDescription(entity)
      entityDescriptions.push(description)
    }
    
    return `NetBox entities we've been discussing:\n${entityDescriptions.join('\n')}`
  }
  
  private async buildEntityDescription(entity: EntityReference): Promise<string> {
    const parts = [
      `- ${entity.type}: ${entity.name}`,
      `  ID: ${entity.id}`,
      `  Mentioned ${entity.mentionCount} times`,
      `  Last mentioned: ${entity.lastMentioned.toISOString()}`
    ]
    
    // Add cached data summary if available
    if (entity.cachedData) {
      const summary = this.summarizeEntityData(entity)
      parts.push(`  Details: ${summary}`)
    }
    
    // Add relationships
    if (entity.relatedEntities.length > 0) {
      const relations = entity.relatedEntities
        .map(rel => `${rel.type}: ${rel.target.name}`)
        .join(', ')
      parts.push(`  Related: ${relations}`)
    }
    
    return parts.join('\n')
  }
}
```

## **Context Pruning System**

### **Token Management**

```typescript
class ContextPruner {
  private maxTokens: number = 4000  // Leave room for response
  private tokenEstimator: TokenEstimator
  
  async pruneContext(session: SessionContext): Promise<SessionContext> {
    const currentTokens = await this.estimateContextTokens(session)
    
    if (currentTokens <= this.maxTokens) {
      return session // No pruning needed
    }
    
    const prunedSession = { ...session }
    
    // 1. Prune old conversation history
    prunedSession.conversationHistory = await this.pruneConversationHistory(
      session.conversationHistory
    )
    
    // 2. Prune less relevant entities
    prunedSession.mentionedEntities = await this.pruneEntities(
      session.mentionedEntities
    )
    
    // 3. Clean up tool history
    prunedSession.toolHistory = this.pruneToolHistory(session.toolHistory)
    
    // 4. Record pruning event
    prunedSession.pruningHistory.push({
      timestamp: new Date(),
      tokensBefore: currentTokens,
      tokensAfter: await this.estimateContextTokens(prunedSession),
      strategy: 'comprehensive'
    })
    
    return prunedSession
  }
  
  private async pruneConversationHistory(
    history: ConversationMessage[]
  ): Promise<ConversationMessage[]> {
    // Keep recent messages and important messages
    const recent = history.slice(-10)  // Last 10 messages
    const important = history.filter(msg => 
      msg.toolsUsed.length > 0 || 
      msg.extractedEntities.length > 0
    ).slice(-5)  // Last 5 important messages
    
    // Combine and deduplicate
    const combined = [...recent, ...important]
    return this.deduplicateMessages(combined)
  }
  
  private async pruneEntities(
    entities: EntityReference[]
  ): Promise<EntityReference[]> {
    // Score entities by relevance
    const scoredEntities = entities.map(entity => ({
      entity,
      score: this.calculateEntityRelevance(entity)
    }))
    
    // Sort by relevance and keep top entities
    scoredEntities.sort((a, b) => b.score - a.score)
    
    return scoredEntities
      .slice(0, 20)  // Keep top 20 entities
      .map(item => item.entity)
  }
  
  private calculateEntityRelevance(entity: EntityReference): number {
    const now = Date.now()
    const daysSinceLastMention = (now - entity.lastMentioned.getTime()) / (24 * 60 * 60 * 1000)
    
    let score = 0
    
    // Recent mentions are more relevant
    score += Math.max(0, 10 - daysSinceLastMention)
    
    // More mentions increase relevance
    score += Math.log(entity.mentionCount + 1) * 2
    
    // Related entities increase relevance
    score += entity.relatedEntities.length * 0.5
    
    // Certain entity types are more important
    const typeBonus = {
      'device': 3,
      'site': 2,
      'rack': 2,
      'ip_address': 1,
      'interface': 1
    }
    score += typeBonus[entity.type] || 0
    
    return score
  }
}
```

## **Performance Optimization**

### **Caching Strategy**

```typescript
class ContextCache {
  private memoryCache: Map<string, CachedContext> = new Map()
  private redisCache: RedisClient
  
  async getCachedContext(
    sessionId: string, 
    messageHash: string
  ): Promise<CachedContext | null> {
    // Check memory cache first
    const memoryKey = `${sessionId}:${messageHash}`
    if (this.memoryCache.has(memoryKey)) {
      return this.memoryCache.get(memoryKey)!
    }
    
    // Check Redis cache
    const redisKey = `context_cache:${sessionId}:${messageHash}`
    const cached = await this.redisCache.get(redisKey)
    
    if (cached) {
      const context = JSON.parse(cached) as CachedContext
      this.memoryCache.set(memoryKey, context)
      return context
    }
    
    return null
  }
  
  async cacheContext(
    sessionId: string,
    messageHash: string,
    context: EnrichedContext
  ) {
    const cached: CachedContext = {
      context,
      timestamp: new Date(),
      expiresAt: new Date(Date.now() + 10 * 60 * 1000) // 10 minutes
    }
    
    // Cache in memory
    const memoryKey = `${sessionId}:${messageHash}`
    this.memoryCache.set(memoryKey, cached)
    
    // Cache in Redis
    const redisKey = `context_cache:${sessionId}:${messageHash}`
    await this.redisCache.setex(
      redisKey, 
      600,  // 10 minutes
      JSON.stringify(cached)
    )
  }
}
```

### **Async Processing**

```typescript
class AsyncContextProcessor {
  private processingQueue: Queue<ContextTask>
  
  async processContextAsync(
    sessionId: string, 
    message: ConversationMessage
  ) {
    // Queue entity extraction and resolution
    this.processingQueue.add({
      type: 'entity_extraction',
      sessionId,
      messageId: message.id,
      data: message
    })
    
    // Queue relationship building
    this.processingQueue.add({
      type: 'relationship_building',
      sessionId,
      messageId: message.id,
      data: message
    })
    
    // Queue context optimization
    this.processingQueue.add({
      type: 'context_optimization',
      sessionId,
      messageId: message.id,
      data: message
    })
  }
  
  private async processEntityExtraction(task: ContextTask) {
    const session = await this.sessionManager.getSession(task.sessionId)
    if (!session) return
    
    const entities = await this.entityTracker.extractEntities(task.data)
    await this.sessionManager.updateSession(task.sessionId, {
      mentionedEntities: [...session.mentionedEntities, ...entities]
    })
  }
}
```

## **Redis Schema Design**

### **Data Structure**

```
# Session data
session:{sessionId}                 → SessionContext (JSON, TTL: 24h)
session:{sessionId}:lock           → Session lock (TTL: 30s)

# User sessions
user_sessions:{userId}             → Set of active session IDs

# Entity index
entity_index:device:{name}         → EntityReference (JSON, TTL: 1h)
entity_index:site:{name}           → EntityReference (JSON, TTL: 1h)
entity_index:ip:{address}          → EntityReference (JSON, TTL: 1h)

# Context cache
context_cache:{sessionId}:{hash}   → CachedContext (JSON, TTL: 10m)

# Performance metrics
metrics:context_size:{sessionId}   → Token count (TTL: 1h)
metrics:entity_count:{sessionId}   → Entity count (TTL: 1h)
```

This context system provides the foundation for intelligent, multi-turn conversations while maintaining efficiency and performance at scale.