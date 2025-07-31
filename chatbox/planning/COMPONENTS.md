# Component Architecture - Detailed Specifications

## **Overview**

This document provides detailed specifications for all components in the NetBox MCP Chatbox Interface, including Vue.js frontend components and Node.js backend services.

---

## **Frontend Components (Vue.js/Nuxt)**

### **Layout Components**

#### **AppLayout.vue**
The main application layout wrapper.

```vue
<template>
  <div class="app-layout">
    <AppHeader />
    <div class="app-content">
      <ChatInterface class="main-chat" />
      <ContextPanel v-if="showContextPanel" class="context-sidebar" />
    </div>
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
interface Props {
  showContextPanel?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showContextPanel: true
})
</script>
```

**Responsibilities:**
- Main layout structure
- Responsive design breakpoints
- Component positioning
- Theme management

#### **AppHeader.vue**
Application header with navigation and status.

```vue
<template>
  <header class="app-header">
    <div class="header-left">
      <h1 class="app-title">NetBox MCP Chat</h1>
      <NetBoxStatusIndicator :status="mcpStatus" />
    </div>
    <div class="header-right">
      <ThemeToggle />
      <UserMenu />
      <SettingsMenu />
    </div>
  </header>
</template>

<script setup lang="ts">
import { useMCPStore } from '~/stores/mcp'

const mcpStore = useMCPStore()
const mcpStatus = computed(() => mcpStore.connectionStatus)
</script>
```

**Props:**
- `title?: string` - Application title
- `showStatus?: boolean` - Show/hide MCP status

**Events:**
- `@theme-changed` - Theme toggle event
- `@settings-opened` - Settings menu opened

---

### **Chat Components**

#### **ChatInterface.vue**
Main chat container managing the conversation flow.

```vue
<template>
  <div class="chat-interface">
    <div class="chat-header">
      <SessionInfo :session="currentSession" />
      <ChatActions />
    </div>
    
    <MessageList 
      ref="messageList"
      :messages="messages"
      :loading="isLoading"
      class="chat-messages"
    />
    
    <TypingIndicator 
      v-if="isTyping"
      :stage="processingStage"
      class="typing-indicator"
    />
    
    <MessageInput
      :disabled="isLoading"
      @send="handleSendMessage"
      @typing="handleTyping"
      class="chat-input"
    />
  </div>
</template>

<script setup lang="ts">
import { useChatStore } from '~/stores/chat'
import { useSocketStore } from '~/stores/socket'

const chatStore = useChatStore()
const socketStore = useSocketStore()

const messages = computed(() => chatStore.messages)
const isLoading = computed(() => chatStore.isLoading)
const isTyping = computed(() => socketStore.isTyping)
const processingStage = computed(() => socketStore.processingStage)

async function handleSendMessage(message: string) {
  await chatStore.sendMessage(message)
}

function handleTyping(isTyping: boolean) {
  socketStore.sendTyping(isTyping)
}
</script>
```

**State Management:**
- Message history via Pinia store
- WebSocket connection status
- Loading and typing states

#### **MessageList.vue**
Scrollable container for conversation messages.

```vue
<template>
  <div 
    ref="scrollContainer"
    class="message-list"
    @scroll="handleScroll"
  >
    <div v-if="hasMore" class="load-more">
      <button @click="loadMore" :disabled="loading">
        Load Earlier Messages
      </button>
    </div>
    
    <MessageBubble
      v-for="message in messages"
      :key="message.id"
      :message="message"
      :show-tools="showToolExecutions"
      @entity-clicked="handleEntityClick"
    />
    
    <div ref="scrollAnchor" />
  </div>
</template>

<script setup lang="ts">
interface Props {
  messages: ConversationMessage[]
  loading?: boolean
  hasMore?: boolean
}

interface Emits {
  (e: 'load-more'): void
  (e: 'entity-clicked', entity: EntityReference): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  hasMore: false
})

const emit = defineEmits<Emits>()

// Auto-scroll to bottom for new messages
const { arrivedState } = useScroll(scrollContainer)
const shouldAutoScroll = ref(true)

watch(() => props.messages.length, () => {
  if (shouldAutoScroll.value) {
    nextTick(() => scrollToBottom())
  }
})

function scrollToBottom() {
  scrollAnchor.value?.scrollIntoView({ behavior: 'smooth' })
}
</script>
```

**Features:**
- Auto-scroll to new messages
- Load more historical messages
- Entity interaction handling
- Scroll position memory

#### **MessageBubble.vue**
Individual message display component.

```vue
<template>
  <div 
    class="message-bubble" 
    :class="messageClasses"
  >
    <div class="message-header">
      <UserAvatar :sender="message.sender" />
      <span class="message-timestamp">
        {{ formatTimestamp(message.timestamp) }}
      </span>
      <MessageActions 
        :message="message"
        @copy="copyMessage"
        @reply="replyToMessage"
      />
    </div>
    
    <div class="message-content">
      <MarkdownRenderer 
        :content="message.content"
        :enable-entity-links="true"
        @entity-clicked="handleEntityClick"
      />
      
      <ToolExecutionList
        v-if="message.toolsUsed?.length"
        :tools="message.toolsUsed"
        :results="message.toolResults"
        :show-details="showToolDetails"
      />
    </div>
    
    <EntityChips
      v-if="message.extractedEntities?.length"
      :entities="message.extractedEntities"
      @entity-clicked="handleEntityClick"
    />
  </div>
</template>

<script setup lang="ts">
interface Props {
  message: ConversationMessage
  showToolDetails?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showToolDetails: false
})

const messageClasses = computed(() => ({
  'message-user': props.message.sender === 'user',
  'message-assistant': props.message.sender === 'assistant',
  'message-error': props.message.messageType === 'error',
  'has-tools': props.message.toolsUsed?.length > 0
}))

function handleEntityClick(entity: EntityReference) {
  emit('entity-clicked', entity)
}
</script>
```

**Props:**
- `message: ConversationMessage` - Message data
- `showToolDetails?: boolean` - Show tool execution details

**Events:**
- `@entity-clicked` - Entity reference clicked
- `@copy` - Copy message content
- `@reply` - Reply to specific message

#### **MessageInput.vue**
User input component with rich features.

```vue
<template>
  <div class="message-input">
    <div class="input-toolbar">
      <EntitySuggestions
        v-if="showSuggestions"
        :suggestions="entitySuggestions"
        @select="insertEntity"
      />
    </div>
    
    <div class="input-container">
      <textarea
        ref="textareaRef"
        v-model="messageText"
        :placeholder="placeholder"
        :disabled="disabled"
        class="message-textarea"
        @keydown="handleKeydown"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
      />
      
      <div class="input-actions">
        <FileAttachment @file-selected="handleFileAttachment" />
        <SendButton 
          :disabled="!canSend"
          :loading="loading"
          @click="sendMessage"
        />
      </div>
    </div>
    
    <div class="input-footer">
      <CharacterCount :current="messageText.length" :max="maxLength" />
      <ContextHint :entities="mentionedEntities" />
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  disabled?: boolean
  loading?: boolean
  placeholder?: string
  maxLength?: number
}

interface Emits {
  (e: 'send', message: string): void
  (e: 'typing', isTyping: boolean): void
  (e: 'file-attached', file: File): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  loading: false,
  placeholder: 'Ask about your NetBox infrastructure...',
  maxLength: 2000
})

const emit = defineEmits<Emits>()

const messageText = ref('')
const showSuggestions = ref(false)
const entitySuggestions = ref<EntitySuggestion[]>([])

// Auto-resize textarea
const { textarea } = useTextareaAutosize()

// Entity suggestions
const { suggestions } = useEntitySuggestions(messageText)

const canSend = computed(() => {
  return messageText.value.trim().length > 0 && !props.disabled
})

function sendMessage() {
  if (canSend.value) {
    emit('send', messageText.value.trim())
    messageText.value = ''
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

let typingTimeout: NodeJS.Timeout

function handleInput() {
  emit('typing', true)
  
  clearTimeout(typingTimeout)
  typingTimeout = setTimeout(() => {
    emit('typing', false)
  }, 1000)
}
</script>
```

**Features:**
- Auto-resizing textarea
- Entity suggestions and autocomplete
- File attachment support
- Keyboard shortcuts (Enter to send, Shift+Enter for newline)
- Character count and limits
- Typing indicators

---

### **Context Components**

#### **ContextPanel.vue**
Side panel showing conversation context and entities.

```vue
<template>
  <aside class="context-panel">
    <div class="panel-header">
      <h3>Conversation Context</h3>
      <PanelToggle @toggle="collapsed = !collapsed" />
    </div>
    
    <div v-if="!collapsed" class="panel-content">
      <TabGroup>
        <TabList>
          <Tab>Entities</Tab>
          <Tab>Tools</Tab>
          <Tab>History</Tab>
        </TabList>
        
        <TabPanels>
          <TabPanel>
            <EntityTracker 
              :entities="activeEntities"
              :loading="entitiesLoading"
              @entity-selected="handleEntitySelect"
            />
          </TabPanel>
          
          <TabPanel>
            <ToolHistory
              :executions="toolHistory"
              :limit="50"
              @tool-selected="handleToolSelect"
            />
          </TabPanel>
          
          <TabPanel>
            <ConversationSummary
              :summary="sessionSummary"
              :statistics="sessionStats"
            />
          </TabPanel>
        </TabPanels>
      </TabGroup>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useContextStore } from '~/stores/context'

const contextStore = useContextStore()

const activeEntities = computed(() => contextStore.activeEntities)
const toolHistory = computed(() => contextStore.toolHistory)
const sessionSummary = computed(() => contextStore.sessionSummary)
const sessionStats = computed(() => contextStore.sessionStatistics)

const collapsed = ref(false)
const entitiesLoading = ref(false)

function handleEntitySelect(entity: EntityReference) {
  // Add entity context to input or open details
  emit('entity-selected', entity)
}

function handleToolSelect(execution: ToolExecution) {
  // Show tool execution details
  emit('tool-selected', execution)
}
</script>
```

#### **EntityTracker.vue**
Component for displaying and managing tracked entities.

```vue
<template>
  <div class="entity-tracker">
    <div class="tracker-header">
      <h4>Active Entities</h4>
      <EntityFilters
        v-model:filters="filters"
        :types="availableTypes"
      />
    </div>
    
    <div class="entity-grid">
      <EntityCard
        v-for="entity in filteredEntities"
        :key="`${entity.type}-${entity.id}`"
        :entity="entity"
        :compact="compact"
        @click="handleEntityClick"
        @context-menu="showEntityMenu"
      />
    </div>
    
    <div v-if="hasMore" class="load-more">
      <button @click="loadMoreEntities">
        Load More Entities
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  entities: EntityReference[]
  loading?: boolean
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  compact: false
})

const filters = ref<EntityFilters>({
  types: [],
  relevance: 'all',
  recent: false
})

const filteredEntities = computed(() => {
  return props.entities.filter(entity => {
    if (filters.value.types.length && !filters.value.types.includes(entity.type)) {
      return false
    }
    
    if (filters.value.relevance === 'high' && entity.relevanceScore < 7) {
      return false
    }
    
    if (filters.value.recent) {
      const daysSince = (Date.now() - new Date(entity.lastMentioned).getTime()) / (24 * 60 * 60 * 1000)
      return daysSince <= 1
    }
    
    return true
  })
})

const availableTypes = computed(() => {
  const types = new Set(props.entities.map(e => e.type))
  return Array.from(types)
})
</script>
```

#### **EntityCard.vue**
Display card for individual NetBox entities.

```vue
<template>
  <div 
    class="entity-card"
    :class="entityClasses"
    @click="handleClick"
  >
    <div class="entity-header">
      <EntityIcon :type="entity.type" />
      <span class="entity-name">{{ entity.name }}</span>
      <RelevanceScore :score="entity.relevanceScore" />
    </div>
    
    <div class="entity-details">
      <div class="entity-meta">
        <span class="entity-type">{{ formatEntityType(entity.type) }}</span>
        <span class="entity-id">ID: {{ entity.id }}</span>
      </div>
      
      <div class="entity-stats">
        <span class="mention-count">
          {{ entity.mentionCount }} mentions
        </span>
        <time class="last-mentioned">
          {{ formatRelativeTime(entity.lastMentioned) }}
        </time>
      </div>
    </div>
    
    <div v-if="entity.relatedEntities?.length" class="entity-relations">
      <RelatedEntities
        :entities="entity.relatedEntities.slice(0, 3)"
        :compact="true"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  entity: EntityReference
  compact?: boolean
  interactive?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
  interactive: true
})

const entityClasses = computed(() => ({
  'entity-card--compact': props.compact,
  'entity-card--interactive': props.interactive,
  [`entity-card--${props.entity.type}`]: true,
  'entity-card--high-relevance': props.entity.relevanceScore >= 8
}))

function handleClick() {
  if (props.interactive) {
    emit('click', props.entity)
  }
}
</script>
```

---

### **Utility Components**

#### **MarkdownRenderer.vue**
Renders markdown content with NetBox entity linking.

```vue
<template>
  <div 
    class="markdown-content"
    v-html="renderedContent"
  />
</template>

<script setup lang="ts">
import { marked } from 'marked'
import DOMPurify from 'dompurify'

interface Props {
  content: string
  enableEntityLinks?: boolean
  enableSyntaxHighlighting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  enableEntityLinks: true,
  enableSyntaxHighlighting: true
})

const renderedContent = computed(() => {
  let processed = props.content
  
  // Add entity linking
  if (props.enableEntityLinks) {
    processed = addEntityLinks(processed)
  }
  
  // Render markdown
  const html = marked(processed, {
    highlight: props.enableSyntaxHighlighting ? highlightCode : undefined
  })
  
  // Sanitize HTML
  return DOMPurify.sanitize(html)
})

function addEntityLinks(content: string): string {
  // Device names: xxx-xxx-xx
  content = content.replace(
    /\b([a-z]+-[a-z]+-\d+)\b/gi,
    '<span class="entity-link" data-type="device" data-name="$1">$1</span>'
  )
  
  // IP addresses
  content = content.replace(
    /\b(?:\d{1,3}\.){3}\d{1,3}\b/g,
    '<span class="entity-link" data-type="ip" data-name="$&">$&</span>'
  )
  
  // Site codes: XXX-XXXX
  content = content.replace(
    /\b[A-Z]{2,4}-[A-Z]{2,4}\d{2}\b/g,
    '<span class="entity-link" data-type="site" data-name="$&">$&</span>'
  )
  
  return content
}
</script>
```

#### **TypingIndicator.vue**
Shows typing/processing status with animation.

```vue
<template>
  <div class="typing-indicator" :class="{ 'typing-indicator--visible': visible }">
    <div class="typing-avatar">
      <BridgetAvatar />
    </div>
    
    <div class="typing-content">
      <div class="typing-text">
        {{ typingText }}
      </div>
      
      <div class="typing-animation">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
      
      <div v-if="stage && stage !== 'thinking'" class="processing-stage">
        <ProcessingStage :stage="stage" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  visible?: boolean
  stage?: ProcessingStage
}

type ProcessingStage = 'thinking' | 'analyzing' | 'executing_tools' | 'generating_response'

const props = withDefaults(defineProps<Props>(), {
  visible: false
})

const typingText = computed(() => {
  switch (props.stage) {
    case 'analyzing':
      return 'Bridget is analyzing your request...'
    case 'executing_tools':
      return 'Bridget is querying NetBox...'
    case 'generating_response':
      return 'Bridget is preparing response...'
    default:
      return 'Bridget is thinking...'
  }
})
</script>

<style scoped>
@keyframes typing-dots {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-10px); }
}

.typing-dots span {
  animation: typing-dots 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }
</style>
```

---

## **Backend Services (Node.js)**

### **Core Services**

#### **ClaudeService**
Manages Claude Code SDK integration and subprocess handling.

```typescript
// services/ClaudeService.ts
import { ClaudeCode } from '@anthropic-ai/claude-code'
import { ChildProcess, spawn } from 'child_process'

export class ClaudeService {
  private claude: ClaudeCode
  private processes: Map<string, ChildProcess> = new Map()
  private config: ClaudeConfig
  
  constructor(config: ClaudeConfig) {
    this.config = config
    this.claude = new ClaudeCode({
      apiKey: config.anthropicApiKey,
      workingDirectory: config.workingDirectory,
      mcpConfig: config.mcpConfigPath
    })
  }
  
  async sendMessage(
    sessionId: string,
    message: string,
    context?: ConversationContext
  ): Promise<AsyncIterable<MessageChunk>> {
    const enrichedMessage = context 
      ? await this.enrichWithContext(message, context)
      : message
    
    return this.claude.query({
      prompt: enrichedMessage,
      stream: true,
      tools: ['mcp__netbox__*']
    })
  }
  
  async getOrCreateProcess(sessionId: string): Promise<ChildProcess> {
    if (!this.processes.has(sessionId)) {
      const process = this.createCLIProcess(sessionId)
      this.processes.set(sessionId, process)
      this.setupProcessHandlers(sessionId, process)
    }
    
    return this.processes.get(sessionId)!
  }
  
  private createCLIProcess(sessionId: string): ChildProcess {
    return spawn('claude-code', [
      '--non-interactive',
      '--working-directory', this.config.workingDirectory,
      '--mcp-config', this.config.mcpConfigPath,
      '--session-id', sessionId
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        ANTHROPIC_API_KEY: this.config.anthropicApiKey
      }
    })
  }
  
  private setupProcessHandlers(sessionId: string, process: ChildProcess) {
    process.on('error', (error) => {
      this.logger.error(`CLI process error for session ${sessionId}:`, error)
      this.handleProcessError(sessionId, error)
    })
    
    process.on('exit', (code, signal) => {
      this.logger.info(`CLI process exited for session ${sessionId}`)
      this.processes.delete(sessionId)
    })
  }
  
  async enrichWithContext(
    message: string, 
    context: ConversationContext
  ): Promise<string> {
    const parts = []
    
    // Add conversation history
    if (context.conversationHistory.length > 0) {
      const history = context.conversationHistory
        .slice(-5)
        .map(msg => `${msg.sender}: ${msg.content}`)
        .join('\n')
      
      parts.push('Recent conversation:')
      parts.push(history)
    }
    
    // Add entity context
    if (context.activeEntities.length > 0) {
      const entities = context.activeEntities
        .map(entity => `- ${entity.type}: ${entity.name}`)
        .join('\n')
      
      parts.push('\nActive NetBox entities:')
      parts.push(entities)
    }
    
    parts.push('\nCurrent message:')
    parts.push(message)
    
    return parts.join('\n')
  }
}
```

#### **SessionService**
Handles session management and persistence.

```typescript
// services/SessionService.ts
export class SessionService {
  private redis: RedisClient
  private sessions: Map<string, SessionContext> = new Map()
  
  constructor(redis: RedisClient) {
    this.redis = redis
  }
  
  async createSession(
    userId: string, 
    preferences?: UserPreferences
  ): Promise<SessionContext> {
    const session: SessionContext = {
      sessionId: this.generateSessionId(),
      userId,
      createdAt: new Date(),
      lastActivity: new Date(),
      conversationHistory: [],
      mentionedEntities: [],
      activeEntities: [],
      toolHistory: [],
      preferences: this.getDefaultPreferences(preferences),
      tokenUsage: this.initTokenUsage(),
      contextSize: 0,
      pruningHistory: []
    }
    
    await this.saveSession(session)
    return session
  }
  
  async getSession(sessionId: string): Promise<SessionContext | null> {
    // Check memory cache
    if (this.sessions.has(sessionId)) {
      const session = this.sessions.get(sessionId)!
      session.lastActivity = new Date()
      return session
    }
    
    // Load from Redis
    const sessionData = await this.redis.get(`session:${sessionId}`)
    if (!sessionData) return null
    
    const session = JSON.parse(sessionData) as SessionContext
    this.sessions.set(sessionId, session)
    
    return session
  }
  
  async updateSession(
    sessionId: string, 
    updates: Partial<SessionContext>
  ): Promise<void> {
    const session = await this.getSession(sessionId)
    if (!session) throw new Error('Session not found')
    
    Object.assign(session, updates)
    session.lastActivity = new Date()
    
    await this.saveSession(session)
  }
  
  async addMessage(
    sessionId: string, 
    message: ConversationMessage
  ): Promise<void> {
    const session = await this.getSession(sessionId)
    if (!session) throw new Error('Session not found')
    
    session.conversationHistory.push(message)
    
    // Prune history if too long
    if (session.conversationHistory.length > 100) {
      session.conversationHistory = session.conversationHistory.slice(-50)
    }
    
    await this.saveSession(session)
  }
  
  private async saveSession(session: SessionContext): Promise<void> {
    this.sessions.set(session.sessionId, session)
    
    await this.redis.setex(
      `session:${session.sessionId}`,
      86400, // 24 hours
      JSON.stringify(session)
    )
  }
  
  private generateSessionId(): string {
    return `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
}
```

#### **ContextService**
Manages conversation context and entity tracking.

```typescript
// services/ContextService.ts
export class ContextService {
  private entityExtractor: EntityExtractor
  private entityResolver: EntityResolver
  
  constructor() {
    this.entityExtractor = new EntityExtractor()
    this.entityResolver = new EntityResolver()
  }
  
  async enrichMessage(
    message: string,
    session: SessionContext
  ): Promise<string> {
    const contextParts = []
    
    // Add relevant conversation history
    const relevantHistory = await this.selectRelevantHistory(session)
    if (relevantHistory.length > 0) {
      contextParts.push(this.formatHistory(relevantHistory))
    }
    
    // Add relevant entities
    const relevantEntities = await this.selectRelevantEntities(session, message)
    if (relevantEntities.length > 0) {
      contextParts.push(await this.formatEntityContext(relevantEntities))
    }
    
    // Add current message
    contextParts.push(`Current message: ${message}`)
    
    return contextParts.join('\n\n')
  }
  
  async extractAndTrackEntities(
    message: ConversationMessage,
    session: SessionContext
  ): Promise<EntityReference[]> {
    // Extract potential entities
    const extracted = await this.entityExtractor.extract(message.content)
    
    // Resolve against conversation history and NetBox
    const resolved: EntityReference[] = []
    
    for (const potential of extracted) {
      const entity = await this.entityResolver.resolve(potential, session)
      if (entity) {
        resolved.push(entity)
      }
    }
    
    // Update session entity tracking
    this.updateSessionEntities(session, resolved)
    
    return resolved
  }
  
  private async selectRelevantHistory(
    session: SessionContext
  ): Promise<ConversationMessage[]> {
    // Keep recent messages and important messages
    const recent = session.conversationHistory.slice(-5)
    const important = session.conversationHistory
      .filter(msg => msg.toolsUsed?.length > 0)
      .slice(-3)
    
    // Combine and deduplicate
    const combined = [...recent, ...important]
    return this.deduplicateMessages(combined)
  }
  
  private async selectRelevantEntities(
    session: SessionContext,
    currentMessage: string
  ): Promise<EntityReference[]> {
    // Score entities by relevance to current message
    const scoredEntities = session.mentionedEntities.map(entity => ({
      entity,
      relevance: this.calculateRelevance(entity, currentMessage, session)
    }))
    
    // Sort by relevance and return top entities
    return scoredEntities
      .sort((a, b) => b.relevance - a.relevance)
      .slice(0, 10)
      .map(item => item.entity)
  }
  
  private calculateRelevance(
    entity: EntityReference,
    message: string,
    session: SessionContext
  ): number {
    let score = entity.relevanceScore
    
    // Boost if mentioned in current message
    if (message.toLowerCase().includes(entity.name.toLowerCase())) {
      score += 5
    }
    
    // Boost if recently mentioned
    const hoursSinceLastMention = 
      (Date.now() - new Date(entity.lastMentioned).getTime()) / (1000 * 60 * 60)
    if (hoursSinceLastMention < 1) score += 3
    else if (hoursSinceLastMention < 6) score += 1
    
    // Boost if high mention count
    score += Math.log(entity.mentionCount + 1)
    
    return score
  }
}
```

This component specification provides a comprehensive foundation for building the NetBox MCP Chatbox Interface with well-structured, reusable components and services.