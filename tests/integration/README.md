# Week 9-12 Real NetBox Integration Tests

Comprehensive integration tests for the real NetBox MCP integration featuring advanced conversation management, performance monitoring, and intelligent caching.

## Overview

This test suite validates the complete Week 9-12 implementation including:

- **Real NetBox API Integration**: Transition from simulation to production NetBox MCP tools
- **Performance Monitoring**: Real-time performance tracking and optimization
- **Intelligent Caching**: Dynamic TTL strategies with performance-driven optimization
- **Entity Tracking**: Advanced NetBox entity management across conversation turns
- **Reference Resolution**: Sophisticated linguistic pattern matching for natural conversations
- **Orchestration Workflows**: LangGraph state machine integration with real tools

## Test Structure

### Core Integration Tests (`test_real_netbox_integration.py`)

- **Real API Handler Tests**: Validates NetBox MCP tool execution, error handling, and retry logic
- **Tool Registry Tests**: Validates tool classification and complexity categorization
- **Performance Monitor Tests**: Validates real-time performance tracking and metrics collection
- **Cache Strategy Tests**: Validates intelligent TTL calculation and dynamic optimization
- **Entity Tracking Tests**: Validates NetBox entity management and relationship discovery
- **Reference Resolution Tests**: Validates advanced linguistic pattern matching
- **End-to-End Workflows**: Validates complete orchestration workflows

### State Machine Integration Tests (`test_state_machine_integration.py`)

- **Parallel Tool Execution**: Tests real API integration with parallel execution
- **Sequential Tool Execution**: Tests context passing between dependent tools
- **Conversation Management**: Tests multi-turn conversation state management
- **Error Handling**: Tests resilience and retry mechanisms
- **Performance Tracking**: Tests performance monitoring integration
- **Entity Relationships**: Tests entity relationship discovery and management

## Running Tests

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install -e .
   pip install pytest pytest-asyncio pytest-cov
   ```

2. **Optional: Redis Setup** (for cache tests):
   ```bash
   # Install Redis
   sudo apt-get install redis-server
   # or
   brew install redis
   
   # Start Redis
   redis-server
   ```

### Quick Test Commands

#### Run Basic Validation
```bash
python run_integration_tests.py validate
```

#### Run Quick Tests (No slow tests)
```bash
python run_integration_tests.py quick
```

#### Run Full Test Suite
```bash
python run_integration_tests.py full
```

#### Run Performance Tests
```bash
python run_integration_tests.py performance
```

#### Run Cache Tests (Requires Redis)
```bash
python run_integration_tests.py cache
```

#### Run Specific Test
```bash
python run_integration_tests.py specific --test-path tests/integration/test_real_netbox_integration.py::TestRealNetBoxIntegration::test_real_api_handler_tool_execution
```

#### Generate Coverage Report
```bash
python run_integration_tests.py coverage
```

### Direct Pytest Commands

#### Run All Integration Tests
```bash
pytest tests/integration/ -v
```

#### Run Tests with Markers
```bash
# Performance tests only
pytest tests/integration/ -v -m performance

# Cache tests only (requires Redis)
pytest tests/integration/ -v -m redis_required

# Exclude slow tests
pytest tests/integration/ -v -m "not slow"
```

#### Run with Coverage
```bash
pytest tests/integration/ --cov=netbox_mcp.orchestration --cov-report=html
```

## Test Categories

### Test Markers

- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.performance`: Performance-focused tests
- `@pytest.mark.redis_required`: Tests requiring Redis
- `@pytest.mark.slow`: Long-running tests

### Test Groupings

1. **Component Tests**: Individual component validation
2. **Integration Tests**: Cross-component integration validation
3. **Performance Tests**: Performance and optimization validation
4. **End-to-End Tests**: Complete workflow validation
5. **Error Scenario Tests**: Error handling and resilience validation

## Key Test Scenarios

### Real API Integration
- Tool execution with mock NetBox MCP tools
- Error handling and retry logic
- Performance tracking integration
- Cache integration with dynamic TTL

### Performance Monitoring
- Real-time metrics collection
- Performance level classification
- Bottleneck identification
- Optimization recommendations

### Intelligent Caching
- Strategy classification for NetBox tools
- Dynamic TTL calculation based on performance
- Usage pattern analysis
- Cache optimization triggers

### Entity Tracking
- NetBox entity discovery and tracking
- Relationship management
- Context persistence across conversation turns
- Entity validation with real NetBox data

### Reference Resolution
- Pronoun resolution ("it", "that", "them")
- Quantified references ("all devices", "both sites")
- Demonstrative references ("the device", "that server")
- Relational references ("connected devices", "same site")
- Temporal references ("previous device", "last site")

### Conversation Management
- Multi-turn conversation state
- Context passing between tools
- Entity focus management
- Conversation history tracking

## Performance Benchmarks

### Expected Performance Metrics

- **Tool Execution Time**: < 2 seconds average
- **Cache Hit Rate**: > 70%
- **Success Rate**: > 95%
- **Parallel Speedup**: 3-5x improvement
- **Error Rate**: < 10%

### Performance Test Scenarios

1. **Parallel Execution**: Multiple tools executed concurrently
2. **Cache Optimization**: TTL adjustment based on performance
3. **Error Recovery**: Retry mechanisms and fallback strategies
4. **Memory Usage**: Entity tracking and cache memory efficiency
5. **Latency Analysis**: End-to-end workflow latency

## Error Scenarios

### Tested Error Conditions

1. **NetBox API Errors**: Connection failures, timeout errors, authentication errors
2. **Tool Import Errors**: Missing tools, malformed tool definitions
3. **Cache Errors**: Redis unavailable, cache corruption
4. **Performance Degradation**: High latency, low success rates
5. **Conversation Errors**: Entity resolution failures, context corruption

### Error Recovery Testing

- Automatic retry with exponential backoff
- Graceful degradation when services unavailable
- Error reporting and logging
- Circuit breaker patterns for failing services

## Mocking Strategy

### Mock Components

1. **NetBox MCP Tools**: Simulated with realistic response times and data
2. **NetBox API**: Mock responses for various tool operations
3. **Redis**: Optional mocking when Redis unavailable
4. **Performance Data**: Simulated performance metrics for testing

### Mock Data Quality

- Realistic NetBox object structures
- Representative performance characteristics
- Common error scenarios
- Edge cases and boundary conditions

## Continuous Integration

### CI Pipeline Integration

```yaml
# Example GitHub Actions workflow
- name: Run Integration Tests
  run: |
    # Start Redis for cache tests
    sudo systemctl start redis
    
    # Run validation
    python run_integration_tests.py validate
    
    # Run quick tests
    python run_integration_tests.py quick
    
    # Run performance tests
    python run_integration_tests.py performance
    
    # Generate coverage report
    python run_integration_tests.py coverage
```

### Test Matrix

- Python versions: 3.8, 3.9, 3.10, 3.11
- Redis versions: 6.x, 7.x
- Operating systems: Ubuntu, macOS, Windows

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**:
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Start Redis if needed
   redis-server
   ```

2. **Import Errors**:
   ```bash
   # Ensure project is installed in development mode
   pip install -e .
   ```

3. **Timeout Errors**:
   - Increase timeout values in test configuration
   - Check system resources and load

4. **Mock Failures**:
   - Verify mock data matches expected formats
   - Check mock setup in test fixtures

### Debug Mode

Run tests with verbose output and no capture:
```bash
pytest tests/integration/ -v -s --tb=long
```

### Performance Debugging

Enable performance profiling:
```bash
pytest tests/integration/ --profile --profile-svg
```

## Contributing

### Adding New Tests

1. **Follow Naming Convention**: `test_<component>_<scenario>.py`
2. **Use Appropriate Markers**: Mark tests with relevant pytest markers
3. **Mock External Dependencies**: Use provided fixtures for consistent mocking
4. **Document Test Purpose**: Clear docstrings explaining test objectives
5. **Performance Considerations**: Include performance assertions where relevant

### Test Data

- Use provided fixtures for consistent test data
- Add new fixtures in `conftest.py` for shared test data
- Ensure test data represents realistic NetBox scenarios

### Coverage Goals

- Maintain > 90% code coverage for orchestration modules
- Cover both success and error scenarios
- Include edge cases and boundary conditions
- Test performance optimization paths

## Documentation

### Test Documentation

Each test module includes:
- Purpose and scope documentation
- Test scenario descriptions
- Expected outcomes and assertions
- Performance expectations
- Error handling validation

### Integration with Main Documentation

These tests validate the functionality described in:
- `PHASE3_PROGRESS.md`: Week 9-12 implementation status
- Architecture documentation: System design and component integration
- Performance documentation: Optimization strategies and benchmarks