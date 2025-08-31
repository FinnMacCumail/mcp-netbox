# NetBox MCP Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the NetBox MCP query processing system to production as a replacement for Claude Code CLI. The system provides intelligent orchestration of NetBox MCP tools with enhanced performance, natural language processing, and robust error handling.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Validation](#pre-deployment-validation)
3. [System Architecture](#system-architecture)
4. [Installation & Setup](#installation--setup)
5. [Configuration Management](#configuration-management)
6. [Monitoring & Health Checks](#monitoring--health-checks)
7. [Performance Optimization](#performance-optimization)
8. [Security Considerations](#security-considerations)
9. [Operational Procedures](#operational-procedures)
10. [Troubleshooting](#troubleshooting)
11. [Migration from Claude Code CLI](#migration-from-claude-code-cli)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ or CentOS 8+), macOS 11+, Windows 10+
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM, Recommended 8GB+
- **CPU**: Minimum 2 cores, Recommended 4+ cores
- **Disk**: Minimum 10GB available space
- **Network**: Stable internet connection for NetBox MCP API access

### Required Dependencies

- Python packages (automatically installed via requirements.txt)
- Redis (optional, for caching - highly recommended for production)
- OpenAI API access (for agent coordination)
- NetBox MCP server access

### Optional Dependencies

- Docker (for containerized deployment)
- Kubernetes (for scalable deployment)
- Prometheus/Grafana (for advanced monitoring)

## Pre-Deployment Validation

Before deploying to production, run comprehensive validation tests to ensure system readiness.

### 1. System Health Check

```bash
# Run system health monitor
python system_health_monitor.py --mode check --verbose

# Expected output: All components "healthy" status
```

### 2. Integration Testing

```bash
# Run comprehensive integration tests
python comprehensive_integration_test.py

# Expected: >90% success rate across all test categories
```

### 3. Production Validation

```bash
# Run Claude CLI replacement validation
python production_deployment_validator.py --verbose

# Expected: "Ready for Deployment: YES" with LOW risk level
```

### 4. Performance Benchmarking

```bash
# Run performance benchmark
python performance_benchmark.py

# Expected: Response times <2s for simple queries, <5s for complex
```

## System Architecture

### Core Components

1. **Query Processing Engine**
   - Natural language understanding
   - Intent recognition and classification
   - Context management

2. **Orchestration System**
   - Multi-agent coordination
   - Tool selection and execution
   - Result aggregation

3. **Caching Layer**
   - Intelligent caching with dynamic TTL
   - Performance optimization
   - Cache invalidation strategies

4. **Error Recovery System**
   - Graceful error handling
   - Automatic retry mechanisms
   - Fallback strategies

5. **Performance Monitoring**
   - Real-time metrics collection
   - Performance analytics
   - Health assessment

### Data Flow

```
User Query → Intent Recognition → Tool Selection → Parallel Execution → Result Aggregation → Response Generation
              ↓                     ↓                ↓                      ↓
          Context Mgmt        Caching Layer    Error Recovery       Performance Mon.
```

## Installation & Setup

### Method 1: Standard Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/netbox-mcp.git
   cd netbox-mcp
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -e .
   pip install -r requirements.txt
   ```

4. **Setup Configuration**
   ```bash
   cp netbox-mcp.yaml.example netbox-mcp.yaml
   # Edit configuration file with your settings
   ```

5. **Initialize System**
   ```bash
   python -m netbox_mcp.cli_phase3 --batch-test
   ```

### Method 2: Docker Deployment

1. **Build Docker Image**
   ```bash
   docker build -t netbox-mcp:latest .
   ```

2. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Verify Deployment**
   ```bash
   docker-compose logs netbox-mcp
   ```

### Method 3: Kubernetes Deployment

1. **Apply Kubernetes Manifests**
   ```bash
   kubectl apply -f k8s/
   ```

2. **Verify Pod Status**
   ```bash
   kubectl get pods -l app=netbox-mcp
   ```

3. **Check Service Health**
   ```bash
   kubectl port-forward svc/netbox-mcp 8080:80
   curl http://localhost:8080/health
   ```

## Configuration Management

### Primary Configuration File

The system uses `netbox-mcp.yaml` for configuration:

```yaml
# NetBox MCP Configuration
system:
  environment: production
  debug: false
  log_level: INFO

orchestration:
  max_concurrent_tools: 10
  tool_timeout: 30
  retry_attempts: 3
  cache_enabled: true

cache:
  redis_url: "redis://localhost:6379"
  default_ttl: 300
  max_cache_size: 1000

performance:
  monitoring_enabled: true
  metrics_retention_days: 30
  alert_thresholds:
    response_time_ms: 5000
    error_rate: 0.05
    cache_hit_rate: 0.7

agents:
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    max_tokens: 2000

netbox:
  mcp_server_url: "${NETBOX_MCP_URL}"
  api_token: "${NETBOX_API_TOKEN}"
  timeout: 30

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "/var/log/netbox-mcp/system.log"
  max_size_mb: 100
  backup_count: 5
```

### Environment Variables

Set these environment variables for production:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export NETBOX_MCP_URL="https://your-netbox-mcp-server"
export NETBOX_API_TOKEN="your-netbox-api-token"
export REDIS_URL="redis://localhost:6379"
export LOG_LEVEL="INFO"
export ENVIRONMENT="production"
```

### Configuration Validation

```bash
# Validate configuration
python -c "from netbox_mcp.config import load_config; print('Config OK')"
```

## Monitoring & Health Checks

### Health Endpoints

The system provides several health check endpoints:

1. **Basic Health Check**
   ```bash
   curl http://localhost:8080/health
   # Expected: {"status": "healthy", "timestamp": "..."}
   ```

2. **Detailed Health Status**
   ```bash
   curl http://localhost:8080/health/detailed
   # Returns comprehensive component health information
   ```

3. **Performance Metrics**
   ```bash
   curl http://localhost:8080/metrics
   # Returns performance metrics in Prometheus format
   ```

### Continuous Monitoring

1. **Start Health Monitoring**
   ```bash
   python system_health_monitor.py --mode monitor --duration 1440  # 24 hours
   ```

2. **Monitor Specific Components**
   ```bash
   # Query processor health
   curl http://localhost:8080/health/query-processor
   
   # Cache system health
   curl http://localhost:8080/health/cache
   
   # Tool coordination health
   curl http://localhost:8080/health/tools
   ```

### Alert Configuration

Set up alerts for critical metrics:

- **Response Time**: Alert if >5 seconds average
- **Error Rate**: Alert if >5% error rate
- **Cache Hit Rate**: Alert if <70% hit rate
- **System Resources**: Alert if CPU >80% or Memory >85%
- **Component Health**: Alert on any component status "critical"

### Log Monitoring

Key log patterns to monitor:

```bash
# Error patterns
grep "ERROR\|CRITICAL" /var/log/netbox-mcp/system.log

# Performance issues
grep "SLOW_QUERY\|TIMEOUT" /var/log/netbox-mcp/system.log

# Cache issues
grep "CACHE_MISS\|CACHE_ERROR" /var/log/netbox-mcp/system.log
```

## Performance Optimization

### Caching Strategy

1. **Enable Redis Caching**
   ```yaml
   cache:
     redis_url: "redis://localhost:6379"
     enabled: true
   ```

2. **Optimize TTL Settings**
   ```yaml
   cache:
     static_infrastructure_ttl: 3600  # 1 hour for sites, racks
     semi_static_config_ttl: 1800     # 30 min for device info
     dynamic_status_ttl: 300          # 5 min for health checks
   ```

3. **Monitor Cache Performance**
   ```bash
   python -c "
   from netbox_mcp.orchestration.cache import OrchestrationCache
   cache = OrchestrationCache()
   print(cache.get_cache_statistics())
   "
   ```

### Parallel Execution

Configure optimal concurrency:

```yaml
orchestration:
  max_concurrent_tools: 10      # Adjust based on system capacity
  parallel_execution: true
  dependency_resolution: true
```

### Resource Management

1. **Memory Optimization**
   - Set appropriate cache limits
   - Configure garbage collection
   - Monitor memory usage patterns

2. **CPU Optimization**
   - Tune worker processes
   - Optimize query processing
   - Balance concurrent operations

3. **Network Optimization**
   - Configure connection pooling
   - Set appropriate timeouts
   - Implement request batching

### Performance Monitoring

```bash
# Run performance benchmark
python performance_benchmark.py --iterations 100 --concurrent 10

# Monitor real-time performance
python system_health_monitor.py --mode monitor --duration 60
```

## Security Considerations

### API Security

1. **Authentication**
   - Use secure API tokens
   - Rotate keys regularly
   - Implement token validation

2. **Authorization**
   - Limit tool access based on permissions
   - Implement role-based access control
   - Audit tool usage

3. **Network Security**
   - Use HTTPS for all communications
   - Configure firewall rules
   - Implement VPN if required

### Data Protection

1. **Sensitive Data Handling**
   - Encrypt sensitive configuration
   - Mask credentials in logs
   - Implement data retention policies

2. **Input Validation**
   - Validate all user inputs
   - Sanitize query parameters
   - Prevent injection attacks

3. **Audit Logging**
   - Log all user actions
   - Track tool executions
   - Monitor for suspicious activity

### Configuration Security

```bash
# Secure configuration file permissions
chmod 600 netbox-mcp.yaml
chown netbox-mcp:netbox-mcp netbox-mcp.yaml

# Secure log directory
mkdir -p /var/log/netbox-mcp
chmod 750 /var/log/netbox-mcp
chown netbox-mcp:netbox-mcp /var/log/netbox-mcp
```

## Operational Procedures

### Deployment Process

1. **Pre-Deployment**
   ```bash
   # Validate configuration
   python -c "from netbox_mcp.config import validate_config; validate_config()"
   
   # Run integration tests
   python comprehensive_integration_test.py
   
   # Check system health
   python system_health_monitor.py --mode check
   ```

2. **Deployment**
   ```bash
   # Stop existing service
   sudo systemctl stop netbox-mcp
   
   # Deploy new version
   git pull origin main
   pip install -e .
   
   # Start service
   sudo systemctl start netbox-mcp
   
   # Verify deployment
   curl http://localhost:8080/health
   ```

3. **Post-Deployment**
   ```bash
   # Monitor for 30 minutes
   python system_health_monitor.py --mode monitor --duration 30
   
   # Run smoke tests
   python production_deployment_validator.py --quick-test
   ```

### Backup Procedures

1. **Configuration Backup**
   ```bash
   # Backup configuration
   tar -czf netbox-mcp-config-$(date +%Y%m%d).tar.gz netbox-mcp.yaml
   
   # Upload to backup location
   aws s3 cp netbox-mcp-config-*.tar.gz s3://your-backup-bucket/
   ```

2. **Cache Backup**
   ```bash
   # Backup Redis data
   redis-cli BGSAVE
   cp /var/lib/redis/dump.rdb /backup/redis-$(date +%Y%m%d).rdb
   ```

### Update Procedures

1. **Minor Updates**
   ```bash
   # Rolling update with zero downtime
   python -m netbox_mcp.update --strategy rolling --health-check
   ```

2. **Major Updates**
   ```bash
   # Scheduled maintenance window
   python -m netbox_mcp.update --strategy maintenance --backup --validate
   ```

## Troubleshooting

### Common Issues

1. **High Response Times**
   ```bash
   # Check cache performance
   python -c "from netbox_mcp.orchestration.cache import OrchestrationCache; print(OrchestrationCache().get_statistics())"
   
   # Monitor concurrent operations
   python system_health_monitor.py --mode check --verbose
   
   # Optimize configuration
   # Increase max_concurrent_tools or enable caching
   ```

2. **Tool Execution Failures**
   ```bash
   # Check tool registry
   python -c "from netbox_mcp.orchestration.tool_registry import ReadOnlyToolRegistry; registry = ReadOnlyToolRegistry(); print(f'Tools registered: {len(registry._tool_registry)}')"
   
   # Test individual tools
   python -m netbox_mcp.tools.dcim.devices mcp__netbox__netbox_list_all_devices
   
   # Check error recovery
   grep "TOOL_ERROR\|RETRY" /var/log/netbox-mcp/system.log
   ```

3. **Cache Issues**
   ```bash
   # Check Redis connectivity
   redis-cli ping
   
   # Monitor cache hit rates
   redis-cli INFO stats
   
   # Clear cache if needed
   redis-cli FLUSHALL
   ```

4. **Memory Issues**
   ```bash
   # Monitor memory usage
   python -c "import psutil; print(f'Memory usage: {psutil.virtual_memory().percent}%')"
   
   # Check for memory leaks
   python -m netbox_mcp.tools.debug memory-profile
   
   # Restart if necessary
   sudo systemctl restart netbox-mcp
   ```

### Diagnostic Commands

```bash
# System health check
python system_health_monitor.py --mode check --verbose

# Component status
python -c "
from netbox_mcp.orchestration.state_machine import QueryProcessor
from netbox_mcp.orchestration.coordination import ToolCoordinator
from netbox_mcp.orchestration.cache import OrchestrationCache

try:
    processor = QueryProcessor()
    print('✅ Query Processor: OK')
except Exception as e:
    print(f'❌ Query Processor: {e}')

try:
    coordinator = ToolCoordinator()
    print('✅ Tool Coordinator: OK')
except Exception as e:
    print(f'❌ Tool Coordinator: {e}')

try:
    cache = OrchestrationCache()
    print('✅ Cache System: OK')
except Exception as e:
    print(f'❌ Cache System: {e}')
"

# Performance metrics
curl http://localhost:8080/metrics | grep -E "(response_time|error_rate|cache_hit)"

# Recent errors
tail -f /var/log/netbox-mcp/system.log | grep ERROR
```

### Support Information

- **Log Location**: `/var/log/netbox-mcp/system.log`
- **Configuration**: `/etc/netbox-mcp/netbox-mcp.yaml`
- **Health Endpoint**: `http://localhost:8080/health`
- **Metrics Endpoint**: `http://localhost:8080/metrics`
- **Status Dashboard**: `http://localhost:8080/status`

## Migration from Claude Code CLI

### Migration Strategy

1. **Parallel Deployment**
   - Deploy NetBox MCP alongside existing Claude CLI
   - Test with subset of users
   - Gradually migrate usage

2. **Feature Comparison**
   - Validate all Claude CLI functionality works
   - Test performance improvements
   - Verify error handling enhancements

3. **User Training**
   - Provide migration documentation
   - Train users on new natural language interface
   - Document query pattern differences

### Migration Steps

1. **Preparation**
   ```bash
   # Backup existing Claude CLI configuration
   cp ~/.claude/config.json ~/.claude/config.json.backup
   
   # Document current usage patterns
   claude-cli --export-usage > claude-usage-report.json
   ```

2. **Installation**
   ```bash
   # Install NetBox MCP system
   pip install netbox-mcp
   
   # Configure for Claude CLI compatibility
   python -m netbox_mcp.migrate --from-claude-cli
   ```

3. **Testing**
   ```bash
   # Run compatibility tests
   python production_deployment_validator.py --claude-cli-mode
   
   # Compare performance
   python performance_benchmark.py --compare-claude-cli
   ```

4. **Migration**
   ```bash
   # Update Claude CLI to use NetBox MCP backend
   python -m netbox_mcp.integrate --with-claude-cli
   
   # Verify integration
   claude-cli "Check NetBox health"
   ```

### Query Translation

Common Claude CLI patterns and their NetBox MCP equivalents:

| Claude CLI Command | NetBox MCP Natural Language |
|-------------------|------------------------------|
| `netbox_health_check` | "Check NetBox server health" |
| `netbox_list_all_sites` | "Show me all sites" |
| `netbox_get_device_info device-name` | "Get information about device-name" |
| `netbox_list_all_devices --site=site1` | "List all devices in site1" |

### Performance Comparison

Expected improvements with NetBox MCP:

- **Response Time**: 2-5x faster due to caching and parallel execution
- **Success Rate**: 10-20% improvement due to better error handling
- **User Experience**: Natural language interface, context awareness
- **Reliability**: Enhanced error recovery and graceful degradation

## Production Checklist

### Pre-Deployment Checklist

- [ ] All system components pass health checks
- [ ] Integration tests achieve >90% success rate
- [ ] Performance benchmarks meet targets
- [ ] Security configuration reviewed and approved
- [ ] Monitoring and alerting configured
- [ ] Backup procedures tested
- [ ] Documentation updated
- [ ] Team training completed

### Post-Deployment Checklist

- [ ] Health monitoring active and reporting
- [ ] Performance metrics within acceptable ranges
- [ ] Error rates below threshold (<5%)
- [ ] Cache hit rates above threshold (>70%)
- [ ] All alerts configured and tested
- [ ] Backup procedures verified
- [ ] User feedback collected
- [ ] Performance optimization applied as needed

### Ongoing Operations Checklist

- [ ] Daily health check reviews
- [ ] Weekly performance analysis
- [ ] Monthly security audits
- [ ] Quarterly capacity planning
- [ ] Regular backup verification
- [ ] Continuous monitoring of error patterns
- [ ] User satisfaction surveys
- [ ] System update planning and execution

## Support and Maintenance

### Regular Maintenance Tasks

1. **Daily**
   - Review system health dashboard
   - Check error rates and performance metrics
   - Monitor cache hit rates
   - Review critical alerts

2. **Weekly**
   - Analyze performance trends
   - Review capacity utilization
   - Update security configurations
   - Test backup procedures

3. **Monthly**
   - Security audit and penetration testing
   - Performance optimization review
   - Capacity planning assessment
   - Documentation updates

4. **Quarterly**
   - System architecture review
   - Technology stack updates
   - Disaster recovery testing
   - User experience assessment

### Support Contacts

- **Technical Issues**: support@your-org.com
- **Security Issues**: security@your-org.com
- **Performance Issues**: performance@your-org.com
- **Emergency Contact**: +1-XXX-XXX-XXXX

---

## Conclusion

This production deployment guide provides comprehensive instructions for deploying and operating the NetBox MCP system as a Claude Code CLI replacement. Following these procedures ensures a reliable, performant, and secure deployment that delivers enhanced user experience and operational efficiency.

For questions or issues not covered in this guide, please contact the support team or refer to the technical documentation in the `docs/` directory.