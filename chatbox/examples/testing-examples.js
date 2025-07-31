#!/usr/bin/env node

/**
 * Testing Examples for NetBox MCP Chatbox Interface
 * 
 * This file contains practical testing examples demonstrating
 * the testing approaches used throughout the development phases.
 * 
 * Examples include:
 * - Frontend component testing with Vitest
 * - Backend API testing with Jest/Supertest
 * - Integration testing with NetBox MCP
 * - End-to-end testing with Playwright
 * - Performance and load testing
 */

// =============================================================================
// FRONTEND COMPONENT TESTING EXAMPLES
// =============================================================================

/**
 * Example: Testing Vue Components with Vitest
 * Location: tests/components/Chat/MessageBubble.test.js
 */

const messageBubbleTest = `
import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import MessageBubble from '~/components/Chat/MessageBubble.vue'

describe('MessageBubble Component', () => {
  const mockMessage = {
    id: 'msg_test_123',
    content: 'Check device switch-nyc-01 status',
    sender: 'user',
    timestamp: '2024-01-15T10:30:00Z',
    extractedEntities: [
      { type: 'device', name: 'switch-nyc-01', confidence: 0.9 }
    ]
  }

  it('renders user message with correct styling', () => {
    const wrapper = mount(MessageBubble, {
      props: { message: mockMessage }
    })
    
    expect(wrapper.text()).toContain('Check device switch-nyc-01 status')
    expect(wrapper.classes()).toContain('message-user')
    expect(wrapper.find('.message-timestamp').exists()).toBe(true)
  })

  it('displays extracted entities as clickable chips', () => {
    const wrapper = mount(MessageBubble, {
      props: { message: mockMessage }
    })
    
    const entityChips = wrapper.find('[data-testid="entity-chips"]')
    expect(entityChips.exists()).toBe(true)
    
    const deviceChip = wrapper.find('[data-entity="switch-nyc-01"]')
    expect(deviceChip.exists()).toBe(true)
    expect(deviceChip.text()).toContain('switch-nyc-01')
  })

  it('emits entity-clicked event when entity is clicked', async () => {
    const wrapper = mount(MessageBubble, {
      props: { message: mockMessage }
    })
    
    const entityChip = wrapper.find('[data-entity="switch-nyc-01"]')
    await entityChip.trigger('click')
    
    expect(wrapper.emitted('entity-clicked')).toBeTruthy()
    expect(wrapper.emitted('entity-clicked')[0][0]).toEqual({
      type: 'device',
      name: 'switch-nyc-01',
      confidence: 0.9
    })
  })

  it('handles assistant messages with tool executions', () => {
    const assistantMessage = {
      ...mockMessage,
      sender: 'assistant',
      content: 'Here are the device details for switch-nyc-01',
      toolsUsed: ['netbox_get_device_info'],
      toolResults: [
        {
          tool: 'netbox_get_device_info',
          result: { name: 'switch-nyc-01', status: 'active' }
        }
      ]
    }
    
    const wrapper = mount(MessageBubble, {
      props: { message: assistantMessage, showToolDetails: true }
    })
    
    expect(wrapper.classes()).toContain('message-assistant')
    expect(wrapper.find('[data-testid="tool-execution-list"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('netbox_get_device_info')
  })
})
`

/**
 * Example: Testing Pinia Stores
 * Location: tests/stores/chat.test.js
 */

const chatStoreTest = `
import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useChatStore } from '~/stores/chat'

describe('Chat Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty state', () => {
    const store = useChatStore()
    
    expect(store.messages).toEqual([])
    expect(store.isLoading).toBe(false)
    expect(store.currentSessionId).toBe(null)
  })

  it('adds messages to conversation history', () => {
    const store = useChatStore()
    const message = {
      content: 'List all devices',
      sender: 'user',
      timestamp: new Date().toISOString()
    }
    
    store.addMessage(message)
    
    expect(store.messages).toHaveLength(1)
    expect(store.messages[0].content).toBe('List all devices')
    expect(store.messages[0].id).toBeDefined()
  })

  it('handles message sending with loading states', async () => {
    const store = useChatStore()
    const mockSendMessage = vi.fn().mockResolvedValue('Response')
    
    // Mock the socket service
    store.$patch({ socketService: { sendMessage: mockSendMessage } })
    
    const promise = store.sendMessage('Test message')
    expect(store.isLoading).toBe(true)
    
    await promise
    expect(store.isLoading).toBe(false)
    expect(mockSendMessage).toHaveBeenCalledWith('Test message')
  })

  it('tracks entity mentions across messages', () => {
    const store = useChatStore()
    
    store.addMessage({
      content: 'Check switch-nyc-01',
      sender: 'user',
      extractedEntities: [{ type: 'device', name: 'switch-nyc-01' }]
    })
    
    store.addMessage({
      content: 'Also check switch-nyc-01 and router-la-02',
      sender: 'user',
      extractedEntities: [
        { type: 'device', name: 'switch-nyc-01' },
        { type: 'device', name: 'router-la-02' }
      ]
    })
    
    const entityMentions = store.getEntityMentions
    expect(entityMentions['switch-nyc-01']).toBe(2)
    expect(entityMentions['router-la-02']).toBe(1)
  })
})
`

// =============================================================================
// BACKEND API TESTING EXAMPLES
// =============================================================================

/**
 * Example: Testing Express API with Supertest
 * Location: tests/api/chat.test.js
 */

const apiTest = `
import request from 'supertest'
import { jest } from '@jest/globals'
import { app } from '../../src/server.js'
import { SessionService } from '../../src/services/SessionService.js'

// Mock external dependencies
jest.mock('../../src/services/ClaudeService.js')
jest.mock('redis', () => ({
  createClient: jest.fn(() => ({
    connect: jest.fn(),
    get: jest.fn(),
    setEx: jest.fn(),
    quit: jest.fn()
  }))
}))

describe('Chat API Endpoints', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('POST /api/chat/session', () => {
    it('creates new chat session successfully', async () => {
      const response = await request(app)
        .post('/api/chat/session')
        .send({
          userId: 'test_user_123',
          preferences: {
            contextRetention: 24,
            enableEntityTracking: true
          }
        })
        .expect(201)

      expect(response.body).toMatchObject({
        sessionId: expect.stringMatching(/^sess_/),
        userId: 'test_user_123',
        createdAt: expect.any(String),
        preferences: {
          contextRetention: 24,
          enableEntityTracking: true
        }
      })
    })

    it('validates required fields', async () => {
      const response = await request(app)
        .post('/api/chat/session')
        .send({}) // Missing userId
        .expect(400)

      expect(response.body).toMatchObject({
        error: 'Missing required field: userId',
        code: 'VALIDATION_ERROR'
      })
    })

    it('handles session creation errors gracefully', async () => {
      // Mock SessionService to throw error
      const mockCreate = jest.spyOn(SessionService.prototype, 'createSession')
        .mockRejectedValue(new Error('Redis connection failed'))

      const response = await request(app)
        .post('/api/chat/session')
        .send({ userId: 'test_user' })
        .expect(500)

      expect(response.body.error).toContain('Session creation failed')
      mockCreate.mockRestore()
    })
  })

  describe('GET /api/chat/session/:sessionId', () => {
    it('retrieves existing session', async () => {
      // Create session first
      const createResponse = await request(app)
        .post('/api/chat/session')
        .send({ userId: 'test_user' })

      const sessionId = createResponse.body.sessionId

      const response = await request(app)
        .get(\`/api/chat/session/\${sessionId}\`)
        .expect(200)

      expect(response.body.sessionId).toBe(sessionId)
      expect(response.body.conversationHistory).toEqual([])
    })

    it('returns 404 for non-existent session', async () => {
      const response = await request(app)
        .get('/api/chat/session/non_existent_session')
        .expect(404)

      expect(response.body.error).toBe('Session not found')
    })
  })

  describe('GET /api/chat/session/:sessionId/context', () => {
    it('returns session context with entity tracking', async () => {
      // Create session with history
      const sessionId = 'test_session_with_context'
      
      // Mock session with context
      const mockSession = {
        sessionId,
        conversationHistory: [
          { content: 'Check switch-nyc-01', sender: 'user' },
          { content: 'Device is active', sender: 'assistant' }
        ],
        mentionedEntities: [
          { type: 'device', name: 'switch-nyc-01', mentionCount: 1 }
        ],
        toolHistory: [
          { tool: 'netbox_get_device_info', executedAt: new Date().toISOString() }
        ]
      }

      jest.spyOn(SessionService.prototype, 'getSession')
        .mockResolvedValue(mockSession)

      const response = await request(app)
        .get(\`/api/chat/session/\${sessionId}/context\`)
        .expect(200)

      expect(response.body).toMatchObject({
        sessionId,
        messageCount: 2,
        entitiesTracked: 1,
        toolsUsed: ['netbox_get_device_info'],
        recentEntities: [
          { type: 'device', name: 'switch-nyc-01' }
        ]
      })
    })
  })
})
`

/**
 * Example: WebSocket Testing
 * Location: tests/websocket/chat.test.js
 */

const websocketTest = `
import { io as Client } from 'socket.io-client'
import { createServer } from 'http'
import { Server } from 'socket.io'
import { jest } from '@jest/globals'
import { setupSocketHandlers } from '../../src/websocket/chatHandlers.js'

describe('Chat WebSocket Events', () => {
  let httpServer, io, clientSocket

  beforeAll((done) => {
    httpServer = createServer()
    io = new Server(httpServer)
    
    setupSocketHandlers(io)
    
    httpServer.listen(() => {
      const port = httpServer.address().port
      clientSocket = Client(\`http://localhost:\${port}\`)
      
      clientSocket.on('connect', done)
    })
  })

  afterAll(() => {
    io.close()
    clientSocket.close()
    httpServer.close()
  })

  it('handles chat message with streaming response', (done) => {
    const testMessage = {
      sessionId: 'test_session',
      message: 'List all devices in NYC datacenter'
    }

    const receivedChunks = []

    clientSocket.on('chat:stream', (data) => {
      receivedChunks.push(data)
    })

    clientSocket.on('chat:complete', (data) => {
      expect(data.sessionId).toBe(testMessage.sessionId)
      expect(receivedChunks.length).toBeGreaterThan(0)
      expect(data.toolsUsed).toBeDefined()
      done()
    })

    clientSocket.emit('chat:message', testMessage)
  })

  it('handles typing indicators', (done) => {
    clientSocket.on('user:typing', (data) => {
      expect(data.sessionId).toBe('test_session')
      expect(data.isTyping).toBe(true)
      done()
    })

    clientSocket.emit('user:typing', {
      sessionId: 'test_session',
      isTyping: true
    })
  })

  it('handles session join and provides context', (done) => {
    clientSocket.on('session:joined', (data) => {
      expect(data.sessionId).toBe('test_session')
      expect(data.context).toBeDefined()
      expect(data.context.messageCount).toBeDefined()
      done()
    })

    clientSocket.emit('session:join', { sessionId: 'test_session' })
  })

  it('handles connection errors gracefully', (done) => {
    clientSocket.on('error', (error) => {
      expect(error.message).toBeDefined()
      expect(error.code).toBeDefined()
      done()
    })

    // Emit invalid message to trigger error
    clientSocket.emit('chat:message', { invalid: 'data' })
  })
})
`

// =============================================================================
// INTEGRATION TESTING EXAMPLES
// =============================================================================

/**
 * Example: Claude SDK Integration Testing
 * Location: tests/integration/claude-sdk.test.js
 */

const claudeIntegrationTest = `
import { ClaudeService } from '../../src/services/ClaudeService.js'
import { jest } from '@jest/globals'

// Mock Claude SDK
jest.mock('@anthropic-ai/claude-code', () => ({
  ClaudeCode: jest.fn().mockImplementation(() => ({
    query: jest.fn(),
    healthCheck: jest.fn()
  }))
}))

describe('Claude SDK Integration', () => {
  let claudeService
  
  beforeEach(() => {
    claudeService = new ClaudeService({
      anthropicApiKey: 'test-key',
      workingDirectory: '/test/dir',
      mcpConfigPath: '.test.mcp.json'
    })
  })

  it('enriches message with conversation context', async () => {
    const message = 'What is the status of that device?'
    const context = {
      conversationHistory: [
        { content: 'Check switch-nyc-01', sender: 'user' },
        { content: 'Device info retrieved', sender: 'assistant' }
      ],
      activeEntities: [
        { type: 'device', name: 'switch-nyc-01', relevanceScore: 8.5 }
      ]
    }

    const enriched = await claudeService.enrichWithContext(message, context)

    expect(enriched).toContain('Recent conversation:')
    expect(enriched).toContain('switch-nyc-01')
    expect(enriched).toContain('What is the status of that device?')
  })

  it('handles streaming responses with tool detection', async () => {
    const mockStreamResponse = [
      'I\\'ll check the device status for you.',
      '🔧 Using tool: netbox_get_device_info',
      'The device switch-nyc-01 is currently active.',
      'Status: Active, Location: NYC-DC01'
    ]

    // Mock streaming iterator
    const mockStream = async function* () {
      for (const chunk of mockStreamResponse) {
        yield chunk
      }
    }

    claudeService.claude.query.mockReturnValue(mockStream())

    const responseChunks = []
    const toolsDetected = []

    for await (const chunk of claudeService.sendMessage('test_session', 'Check device')) {
      responseChunks.push(chunk)
      
      if (chunk.includes('🔧 Using tool:')) {
        const toolMatch = chunk.match(/Using tool: ([\\w_]+)/)
        if (toolMatch) toolsDetected.push(toolMatch[1])
      }
    }

    expect(responseChunks).toHaveLength(4)
    expect(toolsDetected).toContain('netbox_get_device_info')
  })

  it('handles MCP connection errors gracefully', async () => {
    claudeService.claude.query.mockRejectedValue(
      new Error('MCP server connection failed')
    )

    await expect(
      claudeService.sendMessage('test_session', 'List devices')
    ).rejects.toThrow('MCP server connection failed')
  })

  it('manages subprocess lifecycle correctly', async () => {
    const sessionId = 'test_session'
    
    // Create process
    const process1 = await claudeService.getOrCreateProcess(sessionId)
    expect(process1).toBeDefined()
    
    // Same session should return same process
    const process2 = await claudeService.getOrCreateProcess(sessionId)
    expect(process2).toBe(process1)
    
    // Different session should create new process
    const process3 = await claudeService.getOrCreateProcess('different_session')
    expect(process3).not.toBe(process1)
  })
})
`

// =============================================================================
// END-TO-END TESTING EXAMPLES
// =============================================================================

/**
 * Example: Playwright E2E Testing
 * Location: tests/e2e/chat-flow.spec.js
 */

const e2eTest = `
import { test, expect } from '@playwright/test'

test.describe('Complete Chat Experience', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    
    // Wait for app to load
    await page.waitForSelector('[data-testid="chat-interface"]')
  })

  test('user can have complete conversation with context retention', async ({ page }) => {
    // Send first message
    await page.fill('[data-testid="message-input"]', 'List all devices in NYC datacenter')
    await page.click('[data-testid="send-button"]')
    
    // Wait for assistant response
    await page.waitForSelector('[data-testid="assistant-message"]', { timeout: 10000 })
    
    // Verify tool execution indicator appeared
    await expect(page.locator('[data-testid="tool-indicator"]')).toContainText('netbox_list_all_devices')
    
    // Send follow-up message referencing previous context
    await page.fill('[data-testid="message-input"]', 'What about the status of the first switch?')
    await page.click('[data-testid="send-button"]')
    
    // Wait for second response
    await page.waitForSelector('[data-testid="assistant-message"]:nth-child(4)')
    
    // Verify context was used (should reference specific device)
    const lastMessage = page.locator('[data-testid="assistant-message"]').last()
    await expect(lastMessage).toContainText(/switch-nyc-\d+/)
    
    // Check that context panel shows tracked entities
    await expect(page.locator('[data-testid="entity-card"]')).toHaveCount.greaterThan(0)
  })

  test('entity clicking provides quick context', async ({ page }) => {
    // Send message with entities
    await page.fill('[data-testid="message-input"]', 'Show details for switch-nyc-01')
    await page.click('[data-testid="send-button"]')
    
    await page.waitForSelector('[data-testid="assistant-message"]')
    
    // Click on entity chip
    await page.click('[data-entity="switch-nyc-01"]')
    
    // Verify entity details panel opens
    await expect(page.locator('[data-testid="entity-details-panel"]')).toBeVisible()
    await expect(page.locator('[data-testid="entity-name"]')).toContainText('switch-nyc-01')
  })

  test('export conversation functionality works', async ({ page }) => {
    // Have a conversation first
    await page.fill('[data-testid="message-input"]', 'Test export functionality')
    await page.click('[data-testid="send-button"]')
    await page.waitForSelector('[data-testid="assistant-message"]')
    
    // Open export menu
    await page.click('[data-testid="chat-actions-menu"]')
    await page.click('[data-testid="export-conversation"]')
    
    // Select JSON format
    await page.click('[data-testid="export-format-json"]')
    
    // Start download
    const downloadPromise = page.waitForEvent('download')
    await page.click('[data-testid="confirm-export"]')
    
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/conversation-.*\\.json$/)
  })

  test('real-time typing indicators work correctly', async ({ page }) => {
    // Start typing
    await page.focus('[data-testid="message-input"]')
    await page.type('[data-testid="message-input"]', 'Test typing indicators')
    
    // Verify typing indicator appears
    await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible()
    
    // Clear input
    await page.fill('[data-testid="message-input"]', '')
    
    // Verify typing indicator disappears
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible()
  })

  test('error handling displays user-friendly messages', async ({ page }) => {
    // Mock network error
    await page.route('**/api/chat/**', route => {
      route.abort('failed')
    })
    
    await page.fill('[data-testid="message-input"]', 'This should fail')
    await page.click('[data-testid="send-button"]')
    
    // Verify error message appears
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible()
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Connection error')
    
    // Verify retry button is available
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible()
  })
})

test.describe('Responsive Design', () => {
  test('mobile layout works correctly', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }) // iPhone SE
    await page.goto('/')
    
    // Verify mobile layout
    await expect(page.locator('[data-testid="context-panel"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="mobile-context-toggle"]')).toBeVisible()
    
    // Toggle context panel on mobile
    await page.click('[data-testid="mobile-context-toggle"]')
    await expect(page.locator('[data-testid="context-panel"]')).toBeVisible()
  })

  test('tablet layout maintains functionality', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 }) // iPad
    await page.goto('/')
    
    // Send message to verify functionality
    await page.fill('[data-testid="message-input"]', 'Test tablet layout')
    await page.click('[data-testid="send-button"]')
    
    await page.waitForSelector('[data-testid="assistant-message"]')
    
    // Verify layout adapts correctly
    const chatInterface = page.locator('[data-testid="chat-interface"]')
    await expect(chatInterface).toHaveCSS('width', /.*px/)
  })
})
`

// =============================================================================
// PERFORMANCE TESTING EXAMPLES
// =============================================================================

/**
 * Example: Performance and Load Testing
 * Location: tests/performance/load.test.js
 */

const performanceTest = `
import { jest } from '@jest/globals'
import { performance } from 'perf_hooks'
import { ClaudeService } from '../../src/services/ClaudeService.js'
import { SessionService } from '../../src/services/SessionService.js'

describe('Performance Tests', () => {
  let claudeService, sessionService

  beforeAll(() => {
    claudeService = new ClaudeService(testConfig)
    sessionService = new SessionService(testRedisConfig)
  })

  test('handles multiple concurrent sessions efficiently', async () => {
    const sessionCount = 50
    const startTime = performance.now()
    
    // Create multiple sessions concurrently
    const sessionPromises = Array.from({ length: sessionCount }, (_, i) =>
      sessionService.createSession(\`load_test_user_\${i}\`)
    )
    
    const sessions = await Promise.all(sessionPromises)
    
    const creationTime = performance.now() - startTime
    
    expect(sessions).toHaveLength(sessionCount)
    expect(creationTime).toBeLessThan(5000) // Should complete within 5 seconds
    
    // Verify memory usage is reasonable
    const memUsage = process.memoryUsage()
    expect(memUsage.heapUsed).toBeLessThan(500 * 1024 * 1024) // Less than 500MB
  })

  test('message processing maintains performance under load', async () => {
    const session = await sessionService.createSession('perf_test_user')
    const messageCount = 20
    const messages = Array.from({ length: messageCount }, (_, i) =>
      \`Performance test message \${i + 1}\`
    )
    
    const startTime = performance.now()
    
    // Send messages concurrently
    const messagePromises = messages.map(message =>
      claudeService.sendMessage(session.sessionId, message)
    )
    
    await Promise.all(messagePromises)
    
    const totalTime = performance.now() - startTime
    const avgTimePerMessage = totalTime / messageCount
    
    expect(avgTimePerMessage).toBeLessThan(2000) // Average < 2 seconds per message
  })

  test('context enrichment performance scales with history size', async () => {
    const session = await sessionService.createSession('context_perf_test')
    
    // Add varying amounts of history
    const historySizes = [10, 50, 100, 200]
    const results = []
    
    for (const size of historySizes) {
      // Create session with history
      const messages = Array.from({ length: size }, (_, i) => ({
        content: \`Historical message \${i}\`,
        sender: i % 2 === 0 ? 'user' : 'assistant',
        timestamp: new Date().toISOString()
      }))
      
      session.conversationHistory = messages
      
      const startTime = performance.now()
      await claudeService.enrichWithContext('New message', session)
      const enrichmentTime = performance.now() - startTime
      
      results.push({ historySize: size, time: enrichmentTime })
    }
    
    // Verify performance doesn't degrade significantly
    const timeIncrease = results[3].time / results[0].time
    expect(timeIncrease).toBeLessThan(3) // No more than 3x slower with 20x more history
  })

  test('Redis operations maintain sub-100ms performance', async () => {
    const session = await sessionService.createSession('redis_perf_test')
    const operationCount = 100
    
    const operations = []
    
    for (let i = 0; i < operationCount; i++) {
      const startTime = performance.now()
      
      // Perform Redis operations
      await sessionService.updateSession(session.sessionId, {
        lastActivity: new Date().toISOString()
      })
      
      const operationTime = performance.now() - startTime
      operations.push(operationTime)
    }
    
    const avgOperationTime = operations.reduce((a, b) => a + b) / operations.length
    const maxOperationTime = Math.max(...operations)
    
    expect(avgOperationTime).toBeLessThan(50) // Average < 50ms
    expect(maxOperationTime).toBeLessThan(100) // Max < 100ms
  })

  test('memory usage remains stable during extended operation', async () => {
    const initialMemory = process.memoryUsage().heapUsed
    const session = await sessionService.createSession('memory_test')
    
    // Simulate extended usage
    for (let i = 0; i < 100; i++) {
      await claudeService.sendMessage(session.sessionId, \`Message \${i}\`)
      await sessionService.addMessage(session.sessionId, {
        content: \`Response \${i}\`,
        sender: 'assistant',
        timestamp: new Date().toISOString()
      })
      
      // Force garbage collection every 10 iterations
      if (i % 10 === 0 && global.gc) {
        global.gc()
      }
    }
    
    const finalMemory = process.memoryUsage().heapUsed
    const memoryIncrease = finalMemory - initialMemory
    
    // Memory increase should be reasonable (less than 100MB)
    expect(memoryIncrease).toBeLessThan(100 * 1024 * 1024)
  })
})
`

// =============================================================================
// SECURITY TESTING EXAMPLES
// =============================================================================

/**
 * Example: Security Testing
 * Location: tests/security/input-validation.test.js
 */

const securityTest = `
import request from 'supertest'
import { app } from '../../src/server.js'
import { jest } from '@jest/globals'

describe('Security - Input Validation', () => {
  test('prevents XSS attacks in chat messages', async () => {
    const maliciousInputs = [
      '<script>alert("xss")</script>',
      '<img src="x" onerror="alert(\\'xss\\')">',
      'javascript:alert("xss")',
      '<svg onload="alert(\\'xss\\')">',
      '<iframe src="javascript:alert(\\'xss\\')"></iframe>'
    ]
    
    for (const maliciousInput of maliciousInputs) {
      const response = await request(app)
        .post('/api/chat/message')
        .send({
          sessionId: 'test_session',
          message: maliciousInput
        })
        .expect(200)
      
      // Verify malicious scripts are sanitized
      expect(response.body.message).not.toContain('<script>')
      expect(response.body.message).not.toContain('javascript:')
      expect(response.body.message).not.toContain('onerror=')
      expect(response.body.message).not.toContain('onload=')
    }
  })

  test('prevents SQL injection in session queries', async () => {
    const maliciousSessions = [
      "'; DROP TABLE sessions; --",
      "' OR '1'='1' --",
      "'; INSERT INTO sessions VALUES ('malicious'); --",
      "' UNION SELECT * FROM users --"
    ]
    
    for (const maliciousId of maliciousSessions) {
      const response = await request(app)
        .get(\`/api/chat/session/\${encodeURIComponent(maliciousId)}\`)
        .expect(400)
      
      expect(response.body.error).toContain('Invalid session ID')
    }
  })

  test('validates message length limits', async () => {
    const veryLongMessage = 'A'.repeat(10000) // 10KB message
    
    const response = await request(app)
      .post('/api/chat/message')
      .send({
        sessionId: 'test_session',
        message: veryLongMessage
      })
      .expect(400)
    
    expect(response.body.error).toContain('Message too long')
  })

  test('rate limits chat messages per session', async () => {
    const sessionId = 'rate_limit_test'
    const rapidRequests = []
    
    // Send 20 rapid requests
    for (let i = 0; i < 20; i++) {
      rapidRequests.push(
        request(app)
          .post('/api/chat/message')
          .send({
            sessionId,
            message: \`Rapid message \${i}\`
          })
      )
    }
    
    const responses = await Promise.all(rapidRequests)
    
    // Some requests should be rate limited (429 status)
    const rateLimitedResponses = responses.filter(r => r.status === 429)
    expect(rateLimitedResponses.length).toBeGreaterThan(0)
  })

  test('validates session token authenticity', async () => {
    const invalidTokens = [
      'invalid_token_123',
      'expired_token_456',
      '',
      null,
      undefined,
      'malformed.token.here'
    ]
    
    for (const token of invalidTokens) {
      const response = await request(app)
        .post('/api/chat/message')
        .set('Authorization', token ? \`Bearer \${token}\` : '')
        .send({
          sessionId: 'test_session',
          message: 'Test message'
        })
        .expect(401)
      
      expect(response.body.error).toContain('Invalid or missing authentication')
    }
  })

  test('prevents directory traversal in file operations', async () => {
    const maliciousPaths = [
      '../../../etc/passwd',
      '..\\\\..\\\\windows\\\\system32\\\\config\\\\sam',
      '/etc/shadow',
      'C:\\\\Windows\\\\System32\\\\config\\\\SAM',
      '../../../../root/.ssh/id_rsa'
    ]
    
    for (const path of maliciousPaths) {
      const response = await request(app)
        .post('/api/chat/export')
        .send({
          sessionId: 'test_session',
          format: 'json',
          filename: path
        })
        .expect(400)
      
      expect(response.body.error).toContain('Invalid filename')
    }
  })
})
`

// Export all examples for use in documentation
module.exports = {
  messageBubbleTest,
  chatStoreTest,
  apiTest,
  websocketTest,
  claudeIntegrationTest,
  e2eTest,
  performanceTest,
  securityTest
}

console.log('✅ Testing examples compiled successfully!')
console.log('')
console.log('This file contains comprehensive testing examples for:')
console.log('• Frontend Vue component testing with Vitest')
console.log('• Backend API testing with Jest and Supertest')
console.log('• WebSocket real-time communication testing')
console.log('• Claude SDK integration testing')
console.log('• End-to-end user journey testing with Playwright')
console.log('• Performance and load testing')
console.log('• Security vulnerability testing')
console.log('')
console.log('Use these examples to implement comprehensive test coverage')
console.log('throughout all development phases of the NetBox MCP Chatbox Interface.')