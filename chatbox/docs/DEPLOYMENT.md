# Deployment Guide

## **Overview**

This guide covers deploying the NetBox MCP Chatbox Interface to production environments, including Docker containerization, environment configuration, and monitoring setup.

## **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│  Load Balancer (Nginx/HAProxy)                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Frontend      │  │   Frontend      │  │   Frontend      │ │
│  │  (Nuxt SSR)     │  │  (Nuxt SSR)     │  │  (Nuxt SSR)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Backend       │  │   Backend       │  │   Backend       │ │
│  │  (Node.js)      │  │  (Node.js)      │  │  (Node.js)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Redis Cluster  │  │   NetBox MCP    │  │   Monitoring    │ │
│  │   (Sessions)    │  │    Server       │  │  (Prometheus)   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## **Docker Deployment**

### **Docker Compose Configuration**

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Frontend (Nuxt.js)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - BACKEND_URL=http://backend:3001
      - REDIS_URL=redis://redis:6379
    depends_on:
      - backend
      - redis
    restart: unless-stopped
    volumes:
      - ./logs/frontend:/app/logs

  # Backend (Node.js/Express)
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=production
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_URL=redis://redis:6379
      - NETBOX_MCP_CONFIG_PATH=/app/config/.mcp.json
      - PROJECT_ROOT=/app
      - MAX_CLI_PROCESSES=20
      - PROCESS_TIMEOUT_MS=300000
    depends_on:
      - redis
      - netbox-mcp
    restart: unless-stopped
    volumes:
      - ./config/.mcp.json:/app/config/.mcp.json:ro
      - ./logs/backend:/app/logs
      - /var/run/docker.sock:/var/run/docker.sock:ro

  # Redis for session storage
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    restart: unless-stopped
    volumes:
      - redis_data:/data

  # NetBox MCP Server (Your existing server)
  netbox-mcp:
    image: controlaltautomate/netbox-mcp:latest
    ports:
      - "8080:8080"
    environment:
      - NETBOX_URL=${NETBOX_URL}
      - NETBOX_TOKEN=${NETBOX_TOKEN}
      - NETBOX_ENVIRONMENT=production
      - NETBOX_SAFETY_LEVEL=maximum
    restart: unless-stopped
    volumes:
      - ./logs/netbox-mcp:/app/logs

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

  # Monitoring (Optional)
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    restart: unless-stopped

volumes:
  redis_data:
  prometheus_data:
  grafana_data:
```

### **Frontend Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS base

# Install dependencies
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Build stage
FROM base AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM base AS runner
WORKDIR /app

# Create app user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nuxtjs

# Copy built application
COPY --from=builder --chown=nuxtjs:nodejs /app/.output .output
COPY --from=deps --chown=nuxtjs:nodejs /app/node_modules ./node_modules

USER nuxtjs

EXPOSE 3000

ENV NODE_ENV=production
ENV NUXT_HOST=0.0.0.0
ENV NUXT_PORT=3000

CMD ["node", ".output/server/index.mjs"]
```

### **Backend Dockerfile**

```dockerfile
# backend/Dockerfile
FROM node:18-alpine AS base

# Install system dependencies
RUN apk add --no-cache python3 py3-pip

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Install dependencies
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Build stage
FROM base AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM base AS runner
WORKDIR /app

# Create app user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 express

# Copy built application
COPY --from=builder --chown=express:nodejs /app/dist ./dist
COPY --from=deps --chown=express:nodejs /app/node_modules ./node_modules
COPY --chown=express:nodejs package*.json ./

# Create directories
RUN mkdir -p logs config
RUN chown express:nodejs logs config

USER express

EXPOSE 3001

ENV NODE_ENV=production

CMD ["node", "dist/server.js"]
```

## **Environment Configuration**

### **Production Environment Variables**

```bash
# .env.production
# API Keys
ANTHROPIC_API_KEY=your_production_anthropic_key

# NetBox Configuration
NETBOX_URL=https://your-netbox.example.com
NETBOX_TOKEN=your_production_netbox_token

# Application Configuration
NODE_ENV=production
FRONTEND_URL=https://chat.yourcompany.com
BACKEND_URL=https://api.chat.yourcompany.com

# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=your_redis_password

# Session Configuration
SESSION_SECRET=your_secret_session_key
SESSION_TIMEOUT=86400000  # 24 hours

# Claude Code Configuration
PROJECT_ROOT=/app
NETBOX_MCP_CONFIG_PATH=/app/config/.mcp.json
MAX_CLI_PROCESSES=20
PROCESS_TIMEOUT_MS=300000
RESTART_DELAY_MS=5000

# Performance Configuration
ENABLE_RESPONSE_CACHE=true
CACHE_TTL_MS=300000
MAX_CONTEXT_TOKENS=4000

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9100
LOG_LEVEL=info

# Security
CORS_ORIGIN=https://chat.yourcompany.com
RATE_LIMIT_WINDOW=900000  # 15 minutes
RATE_LIMIT_MAX=100        # requests per window

# SSL/TLS
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem

# Monitoring
GRAFANA_PASSWORD=your_grafana_password
```

### **MCP Configuration**

```json
// config/.mcp.json
{
  "mcpServers": {
    "netbox": {
      "command": "python",
      "args": ["-m", "netbox_mcp"],
      "env": {
        "NETBOX_URL": "https://your-netbox.example.com",
        "NETBOX_TOKEN": "your_production_netbox_token",
        "NETBOX_ENVIRONMENT": "production",
        "NETBOX_SAFETY_LEVEL": "maximum",
        "NETBOX_ENABLE_AUDIT": "true"
      }
    }
  }
}
```

## **Nginx Configuration**

### **Reverse Proxy Setup**

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:3000;
    }
    
    upstream backend {
        server backend:3001;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=ws:10m rate=5r/s;
    
    server {
        listen 80;
        server_name chat.yourcompany.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name chat.yourcompany.com;
        
        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        
        # Frontend (Nuxt.js)
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }
        
        # Backend API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # WebSocket connections
        location /socket.io/ {
            limit_req zone=ws burst=10 nodelay;
            
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket timeout
            proxy_read_timeout 86400;
        }
    }
}
```

## **Kubernetes Deployment**

### **Kubernetes Manifests**

```yaml
# kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: netbox-chatbox

---
# kubernetes/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chatbox-config
  namespace: netbox-chatbox
data:
  .mcp.json: |
    {
      "mcpServers": {
        "netbox": {
          "command": "python",
          "args": ["-m", "netbox_mcp"],
          "env": {
            "NETBOX_URL": "https://your-netbox.example.com",
            "NETBOX_TOKEN": "your_production_netbox_token",
            "NETBOX_ENVIRONMENT": "production"
          }
        }
      }
    }

---
# kubernetes/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: chatbox-secrets
  namespace: netbox-chatbox
type: Opaque
data:
  anthropic-api-key: base64_encoded_key
  netbox-token: base64_encoded_token
  session-secret: base64_encoded_secret

---
# kubernetes/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: netbox-chatbox
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
# kubernetes/backend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: netbox-chatbox
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/netbox-chatbox-backend:latest
        ports:
        - containerPort: 3001
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: chatbox-secrets
              key: anthropic-api-key
        - name: REDIS_URL
          value: "redis://redis:6379"
        volumeMounts:
        - name: config
          mountPath: /app/config
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
      volumes:
      - name: config
        configMap:
          name: chatbox-config

---
# kubernetes/frontend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: netbox-chatbox
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: your-registry/netbox-chatbox-frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: BACKEND_URL
          value: "http://backend:3001"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
# kubernetes/services.yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: netbox-chatbox
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379

---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: netbox-chatbox
spec:
  selector:
    app: backend
  ports:
  - port: 3001
    targetPort: 3001

---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: netbox-chatbox
spec:
  selector:
    app: frontend
  ports:
  - port: 3000
    targetPort: 3000

---
# kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: chatbox-ingress
  namespace: netbox-chatbox
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - chat.yourcompany.com
    secretName: chatbox-tls
  rules:
  - host: chat.yourcompany.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 3001
      - path: /socket.io
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 3001
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
```

## **Monitoring and Logging**

### **Prometheus Configuration**

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'chatbox-backend'
    static_configs:
      - targets: ['backend:9100']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'chatbox-frontend'
    static_configs:
      - targets: ['frontend:9100']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    metrics_path: /metrics
    scrape_interval: 30s
```

### **Application Metrics**

```typescript
// backend/monitoring/metrics.ts
import { register, Counter, Histogram, Gauge } from 'prom-client'

export const metrics = {
  // Request metrics
  httpRequests: new Counter({
    name: 'http_requests_total',
    help: 'Total HTTP requests',
    labelNames: ['method', 'route', 'status']
  }),
  
  httpDuration: new Histogram({
    name: 'http_request_duration_seconds',
    help: 'HTTP request duration in seconds',
    labelNames: ['method', 'route']
  }),
  
  // Claude Code metrics
  claudeRequests: new Counter({
    name: 'claude_requests_total',
    help: 'Total Claude Code requests',
    labelNames: ['status']
  }),
  
  claudeDuration: new Histogram({
    name: 'claude_request_duration_seconds',
    help: 'Claude Code request duration in seconds'
  }),
  
  // Session metrics
  activeSessions: new Gauge({
    name: 'active_sessions_total',
    help: 'Number of active chat sessions'
  }),
  
  // Context metrics
  contextSize: new Histogram({
    name: 'context_size_tokens',
    help: 'Context size in tokens',
    buckets: [100, 500, 1000, 2000, 4000, 8000]
  }),
  
  // CLI process metrics
  cliProcesses: new Gauge({
    name: 'cli_processes_active',
    help: 'Number of active CLI processes'
  })
}

// Metrics endpoint
export const metricsHandler = (req: Request, res: Response) => {
  res.set('Content-Type', register.contentType)
  res.end(register.metrics())
}
```

### **Logging Configuration**

```typescript
// backend/logging/logger.ts
import winston from 'winston'

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'netbox-chatbox' },
  transports: [
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error'
    }),
    new winston.transports.File({
      filename: 'logs/combined.log'
    })
  ]
})

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }))
}
```

## **Security Considerations**

### **Environment Security**

1. **API Key Management**: Use secrets management (Docker secrets, Kubernetes secrets)
2. **HTTPS Only**: Enforce SSL/TLS in production
3. **Rate Limiting**: Implement per-IP rate limiting
4. **CORS**: Configure appropriate CORS policies
5. **Session Security**: Use secure session configurations

### **Network Security**

```yaml
# Security policies example
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: chatbox-network-policy
  namespace: netbox-chatbox
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  egress:
  - to:
    - namespaceSelector: {}
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

This deployment guide provides a comprehensive foundation for running the NetBox MCP Chatbox Interface in production environments with proper monitoring, security, and scalability considerations.