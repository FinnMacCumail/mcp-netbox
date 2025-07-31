# Claude Code SDK Integration Guide

## **Overview**

This document details how the chatbox backend integrates with the Claude Code TypeScript SDK to provide a web interface to your existing NetBox MCP Server setup.

## **Integration Pattern**

The integration follows a subprocess pattern where the Claude Code SDK spawns the same CLI process you use manually:

```
Web Request → Backend → Claude SDK → CLI Subprocess → .mcp.json → NetBox MCP Server
```

## **SDK Setup and Configuration**

### **Installation**

```bash
npm install @anthropic-ai/claude-code
```

### **Basic Service Setup**

```typescript
// services/claudeService.ts
import { ClaudeCode } from '@anthropic-ai/claude-code'
import { spawn, ChildProcess } from 'child_process'

export class ClaudeCodeService {
  private claude: ClaudeCode
  private processes: Map<string, ChildProcess> = new Map()
  
  constructor() {
    this.claude = new ClaudeCode({
      apiKey: process.env.ANTHROPIC_API_KEY,
      workingDirectory: process.env.PROJECT_ROOT,
      mcpConfig: process.env.NETBOX_MCP_CONFIG_PATH || '.mcp.json'
    })
  }
  
  async sendMessage(
    sessionId: string, 
    message: string, 
    context: ConversationContext
  ): Promise<AsyncIterable<string>> {
    const enrichedMessage = await this.enrichWithContext(message, context)
    
    // SDK internally spawns CLI subprocess
    return await this.claude.query({
      prompt: enrichedMessage,
      stream: true,
      tools: ['mcp__netbox__*']  // All NetBox MCP tools
    })
  }
}
```

## **Subprocess Management**

### **Process Lifecycle**

```typescript
class ProcessManager {
  private processes: Map<string, ChildProcess> = new Map()
  private processConfig: ProcessConfig
  
  async getOrCreateProcess(sessionId: string): Promise<ChildProcess> {
    if (!this.processes.has(sessionId)) {
      const process = await this.createCLIProcess(sessionId)
      this.processes.set(sessionId, process)
      
      // Set up process event handlers
      this.setupProcessHandlers(sessionId, process)
    }
    
    return this.processes.get(sessionId)!
  }
  
  private async createCLIProcess(sessionId: string): Promise<ChildProcess> {
    const process = spawn('claude-code', [
      '--non-interactive',
      '--working-directory', this.processConfig.workingDirectory,
      '--mcp-config', this.processConfig.mcpConfigPath,
      '--session-id', sessionId
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: this.processConfig.workingDirectory,
      env: {
        ...process.env,
        ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY
      }
    })
    
    return process
  }
  
  private setupProcessHandlers(sessionId: string, process: ChildProcess) {
    process.on('error', (error) => {
      this.logger.error(`CLI process error for session ${sessionId}:`, error)
      this.handleProcessError(sessionId, error)
    })
    
    process.on('exit', (code, signal) => {
      this.logger.info(`CLI process exited for session ${sessionId}: code=${code}, signal=${signal}`)
      this.processes.delete(sessionId)
      this.handleProcessExit(sessionId, code, signal)
    })
  }
}
```

### **Configuration Management**

```typescript
interface ProcessConfig {
  workingDirectory: string
  mcpConfigPath: string
  maxProcesses: number
  processTimeoutMs: number
  restartDelay: number
}

class ConfigurationManager {
  loadMCPConfig(): MCPConfiguration {
    const configPath = process.env.NETBOX_MCP_CONFIG_PATH || '.mcp.json'
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'))
    
    return {
      configPath,
      workingDirectory: process.env.PROJECT_ROOT || process.cwd(),
      netboxServerUrl: this.extractNetBoxServerUrl(config),
      tools: this.extractAvailableTools(config)
    }
  }
  
  private extractNetBoxServerUrl(config: any): string {
    // Extract NetBox MCP server URL from .mcp.json
    const netboxServer = config.mcpServers?.netbox
    if (!netboxServer) {
      throw new Error('NetBox MCP server not found in configuration')
    }
    
    return netboxServer.command || netboxServer.url
  }
}
```

## **Message Flow Integration**

### **Request Processing**

```typescript
class MessageProcessor {
  async processMessage(
    sessionId: string,
    message: string,
    context: ConversationContext
  ): Promise<AsyncIterable<MessageChunk>> {
    try {
      // 1. Enrich message with conversation context
      const enrichedMessage = await this.contextService.enrichMessage(message, context)
      
      // 2. Get or create CLI process for session
      const process = await this.processManager.getOrCreateProcess(sessionId)
      
      // 3. Send message to CLI process
      const response = await this.sendToCLI(process, enrichedMessage)
      
      // 4. Stream response back with processing
      return this.processResponseStream(response, sessionId)
      
    } catch (error) {
      this.logger.error('Message processing error:', error)
      throw new ProcessingError('Failed to process message', error)
    }
  }
  
  private async sendToCLI(
    process: ChildProcess, 
    message: string
  ): Promise<AsyncIterable<string>> {
    return new Promise((resolve, reject) => {
      // Write message to CLI stdin
      process.stdin?.write(`${message}\n`)
      
      // Set up response streaming
      const responseStream = this.createResponseStream(process.stdout)
      resolve(responseStream)
    })
  }
}
```

### **Response Stream Processing**

```typescript
class ResponseStreamProcessor {
  async* processResponseStream(
    cliStream: AsyncIterable<string>, 
    sessionId: string
  ): AsyncIterable<MessageChunk> {
    let buffer = ''
    
    for await (const chunk of cliStream) {
      buffer += chunk
      
      // Process complete lines
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer
      
      for (const line of lines) {
        const processedChunk = await this.processLine(line, sessionId)
        if (processedChunk) {
          yield processedChunk
        }
      }
    }
    
    // Process any remaining buffer
    if (buffer.trim()) {
      const finalChunk = await this.processLine(buffer, sessionId)
      if (finalChunk) {
        yield finalChunk
      }
    }
  }
  
  private async processLine(line: string, sessionId: string): Promise<MessageChunk | null> {
    // Detect tool execution markers
    if (line.includes('🔧 Using tool:')) {
      const toolName = this.extractToolName(line)
      await this.notifyToolExecution(sessionId, toolName)
      return null // Don't pass tool markers to client
    }
    
    // Detect Bridget persona messages
    if (line.includes('🦜 Bridget:')) {
      return {
        type: 'persona',
        content: line,
        timestamp: new Date()
      }
    }
    
    // Regular content
    return {
      type: 'content',
      content: line,
      timestamp: new Date()
    }
  }
}
```

## **Error Handling and Recovery**

### **CLI Process Failures**

```typescript
class ErrorHandler {
  async handleProcessError(sessionId: string, error: Error) {
    this.logger.error(`CLI process error for session ${sessionId}:`, error)
    
    // Notify client of error
    await this.notifyClient(sessionId, {
      type: 'error',
      message: 'CLI process encountered an error',
      recoverable: true
    })
    
    // Attempt recovery
    await this.recoverProcess(sessionId)
  }
  
  async recoverProcess(sessionId: string) {
    try {
      // Clean up failed process
      await this.processManager.cleanupProcess(sessionId)
      
      // Wait before restart
      await this.delay(this.config.restartDelay)
      
      // Create new process with session context
      const context = await this.sessionManager.getContext(sessionId)
      await this.processManager.createProcess(sessionId, context)
      
      // Notify client of recovery
      await this.notifyClient(sessionId, {
        type: 'recovery',
        message: 'Connection restored'
      })
      
    } catch (recoveryError) {
      this.logger.error('Process recovery failed:', recoveryError)
      
      await this.notifyClient(sessionId, {
        type: 'error',
        message: 'Unable to restore connection',
        recoverable: false
      })
    }
  }
}
```

### **MCP Server Connection Issues**

```typescript
class MCPHealthMonitor {
  private healthCheckInterval: NodeJS.Timeout
  
  startMonitoring() {
    this.healthCheckInterval = setInterval(
      () => this.checkMCPServerHealth(),
      30000 // Check every 30 seconds
    )
  }
  
  async checkMCPServerHealth() {
    try {
      // Test MCP server connectivity through CLI
      const healthCheck = await this.runHealthCheck()
      
      if (!healthCheck.healthy) {
        await this.handleMCPServerDown()
      } else if (this.mcpServerStatus === 'down') {
        await this.handleMCPServerRecovered()
      }
      
    } catch (error) {
      this.logger.error('MCP health check failed:', error)
      await this.handleMCPServerDown()
    }
  }
  
  private async runHealthCheck(): Promise<HealthCheckResult> {
    // Use a simple MCP tool call to test connectivity
    const testProcess = spawn('claude-code', [
      '--non-interactive',
      '--mcp-config', this.config.mcpConfigPath,
      '--query', 'netbox_health_check'
    ])
    
    return new Promise((resolve) => {
      let output = ''
      
      testProcess.stdout?.on('data', (data) => {
        output += data.toString()
      })
      
      testProcess.on('close', (code) => {
        resolve({
          healthy: code === 0,
          output: output,
          timestamp: new Date()
        })
      })
    })
  }
}
```

## **Performance Optimization**

### **Process Pooling**

```typescript
class ProcessPool {
  private available: ChildProcess[] = []
  private inUse: Map<string, ChildProcess> = new Map()
  private maxPoolSize: number = 10
  
  async getProcess(sessionId: string): Promise<ChildProcess> {
    // Try to get available process
    if (this.available.length > 0) {
      const process = this.available.pop()!
      this.inUse.set(sessionId, process)
      return process
    }
    
    // Create new process if under limit
    if (this.getTotalProcesses() < this.maxPoolSize) {
      const process = await this.createProcess()
      this.inUse.set(sessionId, process)
      return process
    }
    
    // Wait for available process
    return await this.waitForAvailableProcess(sessionId)
  }
  
  releaseProcess(sessionId: string) {
    const process = this.inUse.get(sessionId)
    if (process) {
      this.inUse.delete(sessionId)
      this.available.push(process)
    }
  }
}
```

### **Caching Strategy**

```typescript
class ResponseCache {
  private cache: Map<string, CachedResponse> = new Map()
  private ttl: number = 5 * 60 * 1000 // 5 minutes
  
  async getCachedResponse(
    message: string, 
    context: ConversationContext
  ): Promise<CachedResponse | null> {
    const key = this.generateCacheKey(message, context)
    const cached = this.cache.get(key)
    
    if (cached && this.isValid(cached)) {
      return cached
    }
    
    return null
  }
  
  cacheResponse(
    message: string, 
    context: ConversationContext, 
    response: string
  ) {
    const key = this.generateCacheKey(message, context)
    this.cache.set(key, {
      response,
      timestamp: new Date(),
      expiresAt: new Date(Date.now() + this.ttl)
    })
  }
}
```

## **Environment Configuration**

### **Required Environment Variables**

```bash
# Claude Code Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key
PROJECT_ROOT=/path/to/your/project
NETBOX_MCP_CONFIG_PATH=/path/to/.mcp.json

# Process Management
MAX_CLI_PROCESSES=10
PROCESS_TIMEOUT_MS=300000
RESTART_DELAY_MS=5000

# Performance
ENABLE_RESPONSE_CACHE=true
CACHE_TTL_MS=300000
```

### **Configuration Validation**

```typescript
class ConfigValidator {
  validateConfiguration() {
    const required = [
      'ANTHROPIC_API_KEY',
      'PROJECT_ROOT',
      'NETBOX_MCP_CONFIG_PATH'
    ]
    
    for (const key of required) {
      if (!process.env[key]) {
        throw new Error(`Required environment variable ${key} is not set`)
      }
    }
    
    // Validate MCP config file exists
    if (!fs.existsSync(process.env.NETBOX_MCP_CONFIG_PATH!)) {
      throw new Error(`MCP config file not found: ${process.env.NETBOX_MCP_CONFIG_PATH}`)
    }
    
    // Validate project root directory
    if (!fs.existsSync(process.env.PROJECT_ROOT!)) {
      throw new Error(`Project root directory not found: ${process.env.PROJECT_ROOT}`)
    }
  }
}
```

This integration guide provides the foundation for connecting the web interface to your existing Claude Code + NetBox MCP Server infrastructure while maintaining full functionality and adding session management capabilities.