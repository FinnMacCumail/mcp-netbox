# NetBox MCP - Project Context for Claude

## CRITICAL: Current Development Focus
**Phase 3: OpenAI + LangGraph Agentic Orchestration**
- Replacing Claude Code CLI with intelligent orchestration system
- Using OpenAI GPT-4o/GPT-4o-mini models
- Orchestrating with LangGraph workflow state machines
- Focus on INTELLIGENT QUERY ORCHESTRATION, not tool fixes

## Strategic Scope Separation
**Phase 3 Core Objectives** (This Phase):
- Intelligent orchestration of existing NetBox MCP read-only tools
- Natural language understanding and query routing
- Multi-step workflow coordination and result aggregation
- Enhanced user experience through conversational interface

**NetBox MCP Server Issues** (Separate Track):
- Token overflow/pagination problems in existing tools
- N+1 query performance issues (127 API calls for 63 VLANs)
- Device types and VLANs listing problems
- API call optimization within MCP server code

## Essential Features Being Implemented
1. **Natural Language Processing**: OpenAI-powered query understanding from tested patterns
2. **Intelligent Workflow Orchestration**: Multi-agent coordination via LangGraph
3. **Read-Only Tool Integration**: Existing NetBox MCP tools as-is
4. **Result Aggregation**: Combine outputs from multiple tool calls
5. **User Experience Enhancement**: Clarification, progress, context management
6. **Performance via Orchestration**: Caching, parallel execution, streaming

## Technical Approach
- **Agent Architecture**: 5 specialized agents with distinct roles
- **OpenAI Models**: GPT-4o for complex tasks, GPT-4o-mini for fast operations
- **LangGraph**: State machines for workflow orchestration
- **Tool Integration**: Dynamic MCP tool selection and execution
- **Error Recovery**: Built-in retry logic and fallback strategies

## Active Development Branches
Following Git strategy in `/docs/GIT_BRANCH_STRATEGY.md`:
- `feature/openai-agent-foundation`
- `feature/langgraph-orchestration`
- `feature/tool-integration-layer`
- `feature/conversation-management`

## Tested Query Patterns (35 Real Examples)
**Simple Queries** (10): Basic discovery and listing operations
**Intermediate Queries** (12): Detailed information retrieval  
**Complex Queries** (13): Advanced analysis and reporting

**Known Issues to Work Around** (not fix in Phase 3):
- Query #7: "Show all device types" - problem
- Query #9: "Show all VLANs" - problem  
- Query #15: Device interfaces pagination issues
- Query #26: Infrastructure audit took 3+ minutes

## Important Guidelines for Claude Sessions
1. **DO NOT** attempt to fix NetBox MCP server tool issues - work around them
2. **DO** focus on intelligent orchestration of existing tools
3. **DO** follow the branch strategy for all development
4. **DO** check `/docs/PHASE3_PROGRESS.md` for current status
5. **DO NOT** implement features marked as "Out of Scope"

## NOT in Current Scope (This Phase)
- Fixing NetBox MCP server performance issues
- Modifying existing tool implementations  
- Authentication/security layers
- Multi-user concurrent support
- State persistence across sessions
- Production deployment features

## Key Documentation
- Development Phase: `/DEVELOPMENT_PHASE.md`
- Technical Details: `/docs/PHASE3_OPENAI_ORCHESTRATION.md`
- Architecture: `/docs/architecture/AGENT_SYSTEM.md`
- Progress: `/docs/PHASE3_PROGRESS.md`
- Validation: `/docs/CLI_REPLACEMENT_CHECKLIST.md`

## Project Structure
```
netbox-mcp/
├── DEVELOPMENT_PHASE.md          # Current phase overview
├── .claude/                      # Claude-specific context
│   └── PROJECT_CONTEXT.md       # This file
├── docs/
│   ├── PHASE3_OPENAI_ORCHESTRATION.md
│   ├── PHASE3_PROGRESS.md
│   ├── CLI_REPLACEMENT_CHECKLIST.md
│   ├── TECH_STACK.md
│   └── architecture/
│       └── AGENT_SYSTEM.md
└── netbox_mcp/                  # Source code
```

## Current Objective
Build a functional CLI replacement that demonstrates OpenAI + LangGraph can successfully orchestrate NetBox operations through natural language, preparing for future production hardening in subsequent phases.