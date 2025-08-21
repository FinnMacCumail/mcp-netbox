# Phase 3 CLI Testing Guide

Complete guide for testing the Phase 3 Week 1-4 OpenAI Agent Foundation using the CLI interface.

## Overview

The Phase 3 Week 1-4 implementation provides a sophisticated multi-agent orchestration system that replaces basic CLI functionality with intelligent conversational interfaces. This guide shows you how to test and validate the complete system.

## Quick Start

### 1. Install and Set Up

```bash
# Ensure dependencies are installed
uv pip install -e .

# Set your OpenAI API key
export OPENAI_API_KEY="your-openai-api-key-here"

# Verify installation
netbox-mcp-phase3 --help
```

### 2. Run Interactive CLI

```bash
# Start interactive mode (default)
netbox-mcp-phase3 --interactive

# Or simply
netbox-mcp-phase3
```

### 3. Try Sample Queries

```
🤖 NetBox AI> list all devices in the datacenter
🤖 NetBox AI> analyze network utilization across sites
🤖 NetBox AI> show me rack inventory for datacenter-1
🤖 NetBox AI> create a new device in rack-01
🤖 NetBox AI> help me understand my infrastructure
```

## Testing Options

### Option 1: Interactive CLI (Recommended)

The interactive CLI provides the most comprehensive testing experience:

```bash
netbox-mcp-phase3 --interactive
```

**Features:**
- Natural language query processing
- Real-time agent coordination display
- Multi-turn conversation support
- Session management
- Built-in help and commands

**Special Commands:**
- `stats` - Show conversation statistics
- `session` - Show session information
- `help` - Display help information
- `clear` - Clear screen
- `quit` or `exit` - Exit CLI

### Option 2: Single Query Testing

Test individual queries quickly:

```bash
netbox-mcp-phase3 --query "list all devices in the datacenter"
netbox-mcp-phase3 --query "analyze network utilization"
netbox-mcp-phase3 --query "create a new rack in site-1"
```

### Option 3: Batch Testing

Run automated test suite with predefined queries:

```bash
netbox-mcp-phase3 --batch-test
```

This runs:
- Discovery queries
- Analysis queries
- Creation queries (read-only demos)
- Unclear queries (clarification flow)
- Health checks

### Option 4: Integration Test Suite

Run comprehensive automated tests:

```bash
# Full integration test suite
uv run python test_phase3_cli_integration.py

# Direct agent testing
uv run python test_conversation_manager.py
```

## What to Test

### 1. Discovery Queries

Test the system's ability to understand and process discovery requests:

```
• "list all devices in the datacenter"
• "show me all sites"
• "find all racks in site-1" 
• "display all VLANs"
• "show cable connections"
• "get all tenants"
• "list device types"
```

**Expected Behavior:**
- Intent recognized as "discovery"
- Complexity classified as "simple"
- Tools suggested (e.g., `netbox_list_all_devices`)
- Orchestrated tool execution simulation
- Natural language response with discovery summary

### 2. Analysis Queries

Test complex analytical capabilities:

```
• "analyze network utilization across all sites"
• "generate inventory report for datacenter-1"
• "analyze rack capacity utilization"
• "check system health status"
• "audit IP address usage"
• "compare site utilization"
```

**Expected Behavior:**
- Intent recognized as "analysis"
- Complexity classified as "complex" 
- Multiple tools coordinated
- Analysis summary with metrics
- Insights and recommendations

### 3. Creation Queries (Read-Only Phase)

Test creation intent recognition with educational responses:

```
• "create a new device in rack-01"
• "add a new site called datacenter-2"
• "provision a new rack in site-1"
• "create VLAN 100 for guest network"
• "add a tenant for customer-xyz"
```

**Expected Behavior:**
- Intent recognized as "creation"
- Complexity classified as "moderate"
- Task planning agent involvement
- Read-only phase explanation
- Planning and requirements assistance

### 4. Clarification Flow

Test handling of ambiguous or unclear queries:

```
• "help me with stuff"
• "show me the devices" (ambiguous scope)
• "I need help"
• "what about those things?"
• "fix the network"
```

**Expected Behavior:**
- Intent recognized as "unclear"
- Clarification questions generated
- Helpful guidance provided
- Suggestion for more specific queries

### 5. Multi-Turn Conversations

Test conversation memory and context:

```
1. "show me all sites"
2. "what devices are in site-1?"
3. "show me only the servers"
4. "analyze their utilization"
```

**Expected Behavior:**
- Context maintained across turns
- Entity resolution (references to previous queries)
- Conversation history preserved
- Relevant follow-up suggestions

### 6. Error Handling

Test system resilience:

```
• Empty queries
• Invalid syntax
• Extremely long queries
• Non-English queries
• Technical jargon
```

**Expected Behavior:**
- Graceful error handling
- User-friendly error messages
- Recovery suggestions
- System remains stable

## Understanding the Output

### Agent Coordination Display

When you run a query, you'll see:

```
🔍 Processing: 'list all devices in the datacenter'
⏳ Orchestrating agents...

✅ Query processed successfully (0.234s)

💬 Response:
------------------------------------------------------------
I've analyzed your query: 'list all devices in the datacenter'

**Discovery Results:**
- Found 25 entities across your NetBox infrastructure
- Used 1 specialized tools for comprehensive discovery
- Data quality: high

**Tools Coordinated:** netbox_list_all_devices

The orchestration system successfully coordinated multiple NetBox MCP 
tools to provide you with comprehensive infrastructure visibility.
------------------------------------------------------------

🤖 Agents coordinated: intent_recognition, tool_coordination, response_generation
📊 Execution Strategy: sequential
🔧 Tools Selected: netbox_list_all_devices
```

### Key Metrics to Watch

1. **Processing Time** - Should be < 5 seconds for most queries
2. **Agent Coordination** - All expected agents should be involved
3. **Response Quality** - Natural language, contextually appropriate
4. **Error Recovery** - Graceful handling of edge cases
5. **Session Persistence** - Context maintained across turns

## Performance Expectations

### Week 1-4 Scope (Current)

- **Response Time:** < 5 seconds per query
- **Agent Coordination:** 2-4 agents per query
- **Success Rate:** > 95% for well-formed queries
- **Context Retention:** 100% within session
- **Tool Simulation:** Read-only orchestration patterns

### Future Enhancements

- **Week 5-8:** LangGraph workflows for complex queries
- **Week 9-12:** Real NetBox MCP tool integration
- **Week 13-16:** Advanced conversation management

## Troubleshooting

### Common Issues

1. **OpenAI API Key Not Set**
   ```
   Error: OPENAI_API_KEY environment variable is required
   Solution: export OPENAI_API_KEY="your-key-here"
   ```

2. **Dependencies Missing**
   ```
   Error: Import error: No module named 'openai'
   Solution: uv pip install -e .
   ```

3. **Slow Responses**
   ```
   Issue: Queries taking > 10 seconds
   Check: OpenAI API connectivity and rate limits
   ```

4. **Agent Registration Failures**
   ```
   Issue: "Query with registered agents failed"
   Check: Agent initialization order and dependencies
   ```

### Verbose Logging

Enable detailed logging for debugging:

```bash
netbox-mcp-phase3 --verbose --interactive
```

### Test Reports

Integration tests generate detailed reports:

```bash
uv run python test_phase3_cli_integration.py
# Creates: phase3_integration_test_report.json
```

## Validation Checklist

Use this checklist to validate Phase 3 Week 1-4 functionality:

### Core Functionality
- [ ] Interactive CLI starts successfully
- [ ] Agent system initializes without errors
- [ ] Discovery queries work correctly
- [ ] Analysis queries generate appropriate responses
- [ ] Creation queries provide read-only explanations
- [ ] Clarification flow handles unclear queries

### Agent Coordination  
- [ ] Intent Recognition Agent processes queries
- [ ] Response Generation Agent formats output
- [ ] Conversation Manager orchestrates properly
- [ ] Tool Coordination Agent simulates execution
- [ ] Task Planning Agent handles complex queries

### Session Management
- [ ] Sessions create and close properly
- [ ] Multi-turn conversations maintain context
- [ ] Session statistics are accurate
- [ ] Memory usage remains stable

### Error Handling
- [ ] Empty queries handled gracefully
- [ ] Invalid inputs don't crash system
- [ ] Network issues are managed properly
- [ ] User-friendly error messages displayed

### Performance
- [ ] Queries complete within 5 seconds
- [ ] Memory usage stays reasonable
- [ ] No resource leaks detected
- [ ] Concurrent queries handled properly

## Integration with Existing Tools

The Phase 3 CLI works alongside existing NetBox MCP functionality:

### MCP Server (Existing)
```bash
# Traditional MCP server
netbox-mcp
```

### Phase 3 CLI (New)
```bash
# Intelligent orchestration interface
netbox-mcp-phase3
```

### Direct Agent Testing
```bash
# Individual agent testing
uv run python test_conversation_manager.py
uv run python test_phase3_cli_integration.py
```

## Next Steps

After validating Phase 3 Week 1-4:

1. **Week 5-8:** Test LangGraph orchestration workflows
2. **Week 9-12:** Validate real NetBox MCP tool integration
3. **Week 13-16:** Test advanced conversation management

The Phase 3 CLI provides a foundation for natural language infrastructure management that will be enhanced in subsequent development phases.

---

## Support

For issues or questions:
- Check logs with `--verbose` flag
- Review integration test output
- Examine detailed error messages
- Validate OpenAI API connectivity

The Phase 3 Week 1-4 implementation demonstrates the core capabilities of intelligent NetBox orchestration through natural language interfaces.