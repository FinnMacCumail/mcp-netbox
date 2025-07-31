#!/usr/bin/env node

/**
 * NetBox MCP Chatbox Integration Example
 * 
 * This example demonstrates how to integrate the Claude Code SDK
 * with the NetBox MCP Server for building chat applications.
 * 
 * Prerequisites:
 * - Claude Code CLI installed globally
 * - NetBox MCP Server running
 * - Valid .mcp.json configuration
 * - Environment variables set
 */

const { ClaudeCode } = require('@anthropic-ai/claude-code')
const { EventEmitter } = require('events')
const Redis = require('redis')

class NetBoxChatboxIntegration extends EventEmitter {
  constructor(config) {
    super()
    
    this.config = {
      anthropicApiKey: process.env.ANTHROPIC_API_KEY,
      projectRoot: process.env.PROJECT_ROOT || process.cwd(),
      mcpConfigPath: process.env.NETBOX_MCP_CONFIG_PATH || '.mcp.json',
      redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
      maxContextTokens: 4000,
      sessionTimeout: 3600000, // 1 hour
      ...config
    }
    
    this.sessions = new Map()
    this.redis = null
    this.claude = null
    
    this.initialize()
  }
  
  async initialize() {
    try {
      // Initialize Redis for session storage
      this.redis = Redis.createClient({ url: this.config.redisUrl })
      await this.redis.connect()
      console.log('✅ Connected to Redis')
      
      // Initialize Claude Code SDK
      this.claude = new ClaudeCode({
        apiKey: this.config.anthropicApiKey,
        workingDirectory: this.config.projectRoot,
        mcpConfig: this.config.mcpConfigPath
      })
      console.log('✅ Claude Code SDK initialized')
      
      // Test NetBox MCP connection
      await this.testMCPConnection()
      
      this.emit('ready')
      
    } catch (error) {
      console.error('❌ Initialization failed:', error)
      this.emit('error', error)
    }
  }
  
  async testMCPConnection() {
    try {
      console.log('🔍 Testing NetBox MCP connection...')
      
      const response = await this.claude.query({
        prompt: 'Test NetBox connection with netbox_health_check',
        stream: false
      })
      
      if (response.includes('healthy') || response.includes('NetBox')) {
        console.log('✅ NetBox MCP Server is accessible')
      } else {
        console.warn('⚠️ NetBox MCP connection may have issues')
      }
      
    } catch (error) {
      console.error('❌ NetBox MCP connection test failed:', error.message)
      throw error
    }
  }
  
  async createSession(userId, preferences = {}) {
    const sessionId = this.generateSessionId()
    
    const session = {
      sessionId,
      userId,
      createdAt: new Date().toISOString(),
      lastActivity: new Date().toISOString(),
      conversationHistory: [],
      mentionedEntities: [],
      toolHistory: [],
      preferences: {
        contextRetention: 24,
        maxHistory: 50,
        enableEntityTracking: true,
        ...preferences
      },
      tokenUsage: {
        totalTokens: 0,
        messagesTokens: 0,
        contextTokens: 0
      }
    }
    
    // Store in memory and Redis
    this.sessions.set(sessionId, session)
    await this.redis.setEx(
      `session:${sessionId}`,
      this.config.sessionTimeout / 1000,
      JSON.stringify(session)
    )
    
    console.log(`📝 Created session ${sessionId} for user ${userId}`)
    return session
  }
  
  async getSession(sessionId) {
    // Check memory first
    if (this.sessions.has(sessionId)) {
      return this.sessions.get(sessionId)
    }
    
    // Load from Redis
    const sessionData = await this.redis.get(`session:${sessionId}`)
    if (sessionData) {
      const session = JSON.parse(sessionData)
      this.sessions.set(sessionId, session)
      return session
    }
    
    return null
  }
  
  async sendMessage(sessionId, message) {
    const session = await this.getSession(sessionId)
    if (!session) {
      throw new Error('Session not found')
    }
    
    console.log(`💬 Processing message in session ${sessionId}:`, message)
    
    try {
      // Update session activity
      session.lastActivity = new Date().toISOString()
      
      // Enrich message with context
      const enrichedMessage = await this.enrichMessageWithContext(message, session)
      
      console.log('🔄 Sending to Claude Code...')
      
      // Stream response from Claude Code
      const responseStream = await this.claude.query({
        prompt: enrichedMessage,
        stream: true,
        tools: ['mcp__netbox__*'] // All NetBox MCP tools
      })
      
      return this.processResponseStream(responseStream, session, message)
      
    } catch (error) {
      console.error('❌ Message processing error:', error)
      throw error
    }
  }
  
  async enrichMessageWithContext(message, session) {
    const contextParts = []
    
    // Add conversation history
    if (session.conversationHistory.length > 0) {
      const recentHistory = session.conversationHistory
        .slice(-5) // Last 5 exchanges
        .map(msg => `${msg.sender}: ${msg.content}`)
        .join('\n')
      
      contextParts.push('Recent conversation:')
      contextParts.push(recentHistory)
    }
    
    // Add mentioned entities
    if (session.mentionedEntities.length > 0) {
      const entities = session.mentionedEntities
        .filter(entity => entity.relevanceScore > 5)
        .slice(0, 10) // Top 10 relevant entities
        .map(entity => `- ${entity.type}: ${entity.name} (mentioned ${entity.mentionCount} times)`)
        .join('\n')
      
      contextParts.push('\nNetBox entities we\'ve discussed:')
      contextParts.push(entities)
    }
    
    // Add current message
    contextParts.push('\nCurrent user message:')
    contextParts.push(message)
    
    // Add instructions
    contextParts.push('\nPlease use the above context when responding and utilize NetBox MCP tools as needed.')
    
    return contextParts.join('\n')
  }
  
  async *processResponseStream(responseStream, session, originalMessage) {
    let fullResponse = ''
    let toolsUsed = []
    
    // Add user message to history
    const userMessage = {
      id: this.generateMessageId(),
      content: originalMessage,
      sender: 'user',
      timestamp: new Date().toISOString(),
      extractedEntities: []
    }
    session.conversationHistory.push(userMessage)
    
    console.log('📡 Streaming response...')
    
    for await (const chunk of responseStream) {
      fullResponse += chunk
      
      // Detect tool usage
      if (chunk.includes('🔧 Using tool:')) {
        const toolMatch = chunk.match(/Using tool: ([\w_]+)/)
        if (toolMatch) {
          const toolName = toolMatch[1]
          toolsUsed.push(toolName)
          console.log(`🔧 Tool executed: ${toolName}`)
          
          // Track tool usage
          session.toolHistory.push({
            tool: toolName,
            executedAt: new Date().toISOString(),
            messageId: userMessage.id
          })
        }
      }
      
      // Yield chunk to client
      yield {
        type: 'chunk',
        data: chunk,
        sessionId: session.sessionId
      }
    }
    
    // Add assistant response to history
    const assistantMessage = {
      id: this.generateMessageId(),
      content: fullResponse,
      sender: 'assistant',
      timestamp: new Date().toISOString(),
      toolsUsed,
      extractedEntities: await this.extractEntities(fullResponse)
    }
    session.conversationHistory.push(assistantMessage)
    
    // Update entity tracking
    await this.updateEntityTracking(session, assistantMessage)
    
    // Save updated session
    await this.saveSession(session)
    
    console.log('✅ Message processing complete')
    
    // Yield completion event
    yield {
      type: 'complete',
      data: {
        messageId: assistantMessage.id,
        toolsUsed,
        entitiesExtracted: assistantMessage.extractedEntities.length
      },
      sessionId: session.sessionId
    }
  }
  
  async extractEntities(text) {
    // Simple entity extraction (in production, use more sophisticated NLP)
    const entities = []
    
    // Extract device names (pattern: xxx-xxx-xx)
    const devicePattern = /\b[a-z]+-[a-z]+-\d+\b/gi
    const devices = text.match(devicePattern) || []
    devices.forEach(device => {
      entities.push({
        type: 'device',
        name: device.toLowerCase(),
        confidence: 0.8
      })
    })
    
    // Extract IP addresses
    const ipPattern = /\b(?:\d{1,3}\.){3}\d{1,3}\b/g
    const ips = text.match(ipPattern) || []
    ips.forEach(ip => {
      entities.push({
        type: 'ip_address',
        name: ip,
        confidence: 0.9
      })
    })
    
    // Extract site references
    const sitePattern = /\b[A-Z]{2,4}-[A-Z]{2,4}\d{2}\b/g
    const sites = text.match(sitePattern) || []
    sites.forEach(site => {
      entities.push({
        type: 'site',
        name: site,
        confidence: 0.85
      })
    })
    
    return entities
  }
  
  async updateEntityTracking(session, message) {
    for (const entity of message.extractedEntities) {
      const existingEntity = session.mentionedEntities.find(
        e => e.type === entity.type && e.name === entity.name
      )
      
      if (existingEntity) {
        // Update existing entity
        existingEntity.mentionCount++
        existingEntity.lastMentioned = new Date().toISOString()
        existingEntity.relevanceScore += 0.5
      } else {
        // Add new entity
        session.mentionedEntities.push({
          ...entity,
          firstMentioned: new Date().toISOString(),
          lastMentioned: new Date().toISOString(),
          mentionCount: 1,
          relevanceScore: 5.0
        })
      }
    }
  }
  
  async saveSession(session) {
    this.sessions.set(session.sessionId, session)
    await this.redis.setEx(
      `session:${session.sessionId}`,
      this.config.sessionTimeout / 1000,
      JSON.stringify(session)
    )
  }
  
  async getSessionContext(sessionId) {
    const session = await this.getSession(sessionId)
    if (!session) return null
    
    return {
      sessionId: session.sessionId,
      messageCount: session.conversationHistory.length,
      entitiesTracked: session.mentionedEntities.length,
      toolsUsed: [...new Set(session.toolHistory.map(t => t.tool))],
      lastActivity: session.lastActivity,
      recentEntities: session.mentionedEntities
        .sort((a, b) => new Date(b.lastMentioned) - new Date(a.lastMentioned))
        .slice(0, 5)
    }
  }
  
  generateSessionId() {
    return `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
  
  generateMessageId() {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`
  }
  
  // Cleanup resources
  async destroy() {
    if (this.redis) {
      await this.redis.quit()
    }
    this.sessions.clear()
    console.log('🧹 Cleanup complete')
  }
}

// Example usage
async function example() {
  console.log('🚀 Starting NetBox MCP Chatbox Integration Example\n')
  
  const chatbox = new NetBoxChatboxIntegration({
    maxContextTokens: 3000,
    sessionTimeout: 1800000 // 30 minutes
  })
  
  chatbox.on('ready', async () => {
    console.log('✅ Integration ready!\n')
    
    try {
      // Create a session
      const session = await chatbox.createSession('demo_user', {
        contextRetention: 2,
        enableEntityTracking: true
      })
      
      console.log('📝 Session created:', session.sessionId, '\n')
      
      // Send some example messages
      const messages = [
        'Show me all devices in the NYC datacenter',
        'What is the status of the first switch?',
        'List all IP addresses in the 10.1.0.0/24 network'
      ]
      
      for (const message of messages) {
        console.log(`\n👤 User: ${message}`)
        console.log('🤖 Assistant:')
        
        const responseStream = await chatbox.sendMessage(session.sessionId, message)
        
        for await (const event of responseStream) {
          if (event.type === 'chunk') {
            process.stdout.write(event.data)
          } else if (event.type === 'complete') {
            console.log(`\n\n📊 Tools used: ${event.data.toolsUsed.join(', ') || 'none'}`)
            console.log(`📊 Entities extracted: ${event.data.entitiesExtracted}`)
          }
        }
        
        // Show session context
        const context = await chatbox.getSessionContext(session.sessionId)
        console.log('\n📋 Session Context:')
        console.log(`   Messages: ${context.messageCount}`)
        console.log(`   Entities: ${context.entitiesTracked}`)
        console.log(`   Tools: ${context.toolsUsed.join(', ')}`)
        
        // Wait between messages
        await new Promise(resolve => setTimeout(resolve, 2000))
      }
      
    } catch (error) {
      console.error('❌ Example error:', error)
    } finally {
      await chatbox.destroy()
    }
  })
  
  chatbox.on('error', (error) => {
    console.error('❌ Integration error:', error)
    process.exit(1)
  })
}

// Run example if this file is executed directly
if (require.main === module) {
  example().catch(console.error)
}

module.exports = NetBoxChatboxIntegration