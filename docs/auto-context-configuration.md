# Bridget Auto-Context System Configuration

## Overview

The Bridget Auto-Context System provides intelligent environment detection and safety level assignment for NetBox MCP. This document covers all configuration options and environment variables.

## Environment Variables

### Core Configuration

#### `NETBOX_AUTO_CONTEXT`
- **Default:** `true`
- **Values:** `true` | `false`
- **Description:** Enable/disable automatic context initialization
- **Example:** `export NETBOX_AUTO_CONTEXT=false`

#### `NETBOX_ENVIRONMENT`
- **Default:** Auto-detected
- **Values:** `demo` | `staging` | `production` | `cloud`
- **Description:** Override automatic environment detection
- **Example:** `export NETBOX_ENVIRONMENT=staging`

#### `NETBOX_SAFETY_LEVEL`
- **Default:** Based on environment
- **Values:** `standard` | `high` | `maximum`
- **Description:** Override automatic safety level assignment
- **Example:** `export NETBOX_SAFETY_LEVEL=maximum`

#### `NETBOX_BRIDGET_PERSONA`
- **Default:** `enabled`
- **Values:** `enabled` | `disabled`
- **Description:** Control Bridget persona interactions
- **Example:** `export NETBOX_BRIDGET_PERSONA=disabled`

### NetBox Connection (Existing)

#### `NETBOX_URL`
- **Required:** Yes
- **Description:** NetBox instance URL for environment detection
- **Example:** `export NETBOX_URL=https://demo.netbox.local`

#### `NETBOX_TOKEN`
- **Required:** Yes
- **Description:** NetBox API authentication token
- **Example:** `export NETBOX_TOKEN=your_api_token_here`

## Environment Detection Logic

### Automatic Detection Patterns

The system analyzes the `NETBOX_URL` to determine environment type:

#### Demo/Development
- `demo.*`
- `*demo*`
- `localhost`
- `127.0.0.1`
- `*.local`

#### Staging/Test
- `stag*.*`
- `*staging*`
- `*test*`
- `*dev*`

#### Cloud
- `*.cloud.netboxapp.com`
- `*cloud.netbox*`

#### Production
- `*.prod*`
- `*production*`
- `netbox.*`

### Safety Level Mapping

| Environment | Default Safety Level | Description |
|-------------|---------------------|-------------|
| `demo` | `standard` | Basic safety for development |
| `staging` | `high` | Enhanced safety for testing |
| `cloud` | `high` | Cloud best practices |
| `production` | `maximum` | Maximum safety protocols |
| `unknown` | `maximum` | Safe default for undetected |

## Configuration Examples

### Development Environment
```bash
export NETBOX_URL="http://localhost:8000"
export NETBOX_TOKEN="demo_token_123"
export NETBOX_ENVIRONMENT="demo"
export NETBOX_SAFETY_LEVEL="standard"
export NETBOX_AUTO_CONTEXT="true"
```

### Staging Environment
```bash
export NETBOX_URL="https://staging.netbox.company.com"
export NETBOX_TOKEN="staging_token_456"
export NETBOX_ENVIRONMENT="staging"
export NETBOX_SAFETY_LEVEL="high"
export NETBOX_AUTO_CONTEXT="true"
```

### Production Environment
```bash
export NETBOX_URL="https://netbox.company.com"
export NETBOX_TOKEN="production_token_789"
export NETBOX_ENVIRONMENT="production"
export NETBOX_SAFETY_LEVEL="maximum"
export NETBOX_AUTO_CONTEXT="true"
```

### Disable Auto-Context
```bash
export NETBOX_AUTO_CONTEXT="false"
export NETBOX_BRIDGET_PERSONA="disabled"
```

## Docker Configuration

### Docker Compose Example
```yaml
version: '3.8'
services:
  netbox-mcp:
    image: netbox-mcp:latest
    environment:
      - NETBOX_URL=https://demo.netbox.local
      - NETBOX_TOKEN=demo_token_123
      - NETBOX_ENVIRONMENT=demo
      - NETBOX_SAFETY_LEVEL=standard
      - NETBOX_AUTO_CONTEXT=true
      - NETBOX_BRIDGET_PERSONA=enabled
```

### Kubernetes ConfigMap Example
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: netbox-mcp-config
data:
  NETBOX_URL: "https://netbox.company.com"
  NETBOX_ENVIRONMENT: "production"
  NETBOX_SAFETY_LEVEL: "maximum"
  NETBOX_AUTO_CONTEXT: "true"
  NETBOX_BRIDGET_PERSONA: "enabled"
```

## Security Considerations

### Token Security
- **Never** commit `NETBOX_TOKEN` to version control
- Use secrets management systems in production
- Rotate tokens regularly
- Use environment-specific tokens

### Override Security
- `NETBOX_SAFETY_LEVEL` overrides can reduce security
- Always validate environment variable sources
- Monitor for unauthorized safety level changes
- Use `maximum` safety for unknown environments

## Troubleshooting

### Context Not Initializing
1. Check `NETBOX_AUTO_CONTEXT=true`
2. Verify NetBox connectivity
3. Ensure valid `NETBOX_TOKEN`
4. Check logs for initialization errors

### Wrong Environment Detected
1. Set `NETBOX_ENVIRONMENT` explicitly
2. Verify URL patterns match detection logic
3. Check for typos in environment names
4. Use override variables for edge cases

### Safety Level Issues
1. Verify `NETBOX_SAFETY_LEVEL` spelling
2. Check environment-to-safety mapping
3. Use `maximum` when in doubt
4. Monitor audit logs for safety violations

## Integration Examples

### CI/CD Pipeline
```bash
#!/bin/bash
# Set environment based on branch
if [ "$BRANCH" = "main" ]; then
    export NETBOX_ENVIRONMENT="production"
    export NETBOX_SAFETY_LEVEL="maximum"
elif [ "$BRANCH" = "develop" ]; then
    export NETBOX_ENVIRONMENT="staging"
    export NETBOX_SAFETY_LEVEL="high"
else
    export NETBOX_ENVIRONMENT="demo"
    export NETBOX_SAFETY_LEVEL="standard"
fi

export NETBOX_AUTO_CONTEXT="true"
export NETBOX_BRIDGET_PERSONA="enabled"
```

### Terraform Configuration
```hcl
resource "kubernetes_deployment" "netbox_mcp" {
  metadata {
    name = "netbox-mcp"
  }
  
  spec {
    template {
      spec {
        container {
          name = "netbox-mcp"
          
          env {
            name  = "NETBOX_ENVIRONMENT"
            value = var.environment
          }
          
          env {
            name  = "NETBOX_SAFETY_LEVEL"
            value = var.environment == "production" ? "maximum" : "high"
          }
          
          env {
            name  = "NETBOX_AUTO_CONTEXT"
            value = "true"
          }
        }
      }
    }
  }
}
```

## API Access

The auto-context system is also accessible via REST API:

### Get Current Context
```bash
curl -X GET http://localhost:8000/api/v1/context/status
```

### Initialize Context Manually
```bash
curl -X POST http://localhost:8000/api/v1/context/initialize
```

### Reset Context
```bash
curl -X POST http://localhost:8000/api/v1/context/reset
```

## Monitoring and Logging

### Log Messages
- `Context initialized: environment/safety_level/instance_type`
- `Environment overridden via NETBOX_ENVIRONMENT: value`
- `Safety level overridden via NETBOX_SAFETY_LEVEL: value`
- `Auto-context disabled via NETBOX_AUTO_CONTEXT`

### Metrics
- Context initialization time
- Environment detection accuracy
- Safety level assignments
- Override usage frequency

---

*Last Updated: NetBox MCP v0.11.0+ with Bridget Auto-Context System v1.0*