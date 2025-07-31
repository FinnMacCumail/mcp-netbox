# Git Branch Strategy - NetBox MCP Chatbox Development

## **Overview**

This document defines the git branching strategy for the 10-week NetBox MCP Chatbox Interface development project. The strategy aligns with the 5-phase development plan and supports parallel feature development, comprehensive testing, and reliable deployment workflows.

---

## **Branch Architecture**

### **Main Branches**

```
main ─────────────────────────────── (Production deployments)
  │
develop ─────────────────────────── (Integration & testing)
  │
staging ─────────────────────────── (Pre-production validation)
```

- **`main`** - Production-ready code, always deployable, tagged releases
- **`develop`** - Integration branch for ongoing development, feature merging
- **`staging`** - Pre-production testing, final validation before production

### **Phase-Based Development Structure**

```
develop
├── phase/1-foundation
│   ├── feature/phase1-nuxt-setup
│   ├── feature/phase1-express-backend
│   ├── feature/phase1-chat-ui
│   └── feature/phase1-websocket
├── phase/2-cli-integration
│   ├── feature/phase2-claude-sdk
│   ├── feature/phase2-mcp-connection
│   └── feature/phase2-subprocess-mgmt
└── [phases 3-5...]
```

---

## **Branch Types & Naming Conventions**

### **Branch Type Prefixes**

| Type | Prefix | Purpose | Example |
|------|--------|---------|---------|
| Phase | `phase/` | Main phase development | `phase/1-foundation` |
| Feature | `feature/` | Specific feature development | `feature/phase1-nuxt-setup` |
| Hotfix | `hotfix/` | Critical bug fixes | `hotfix/phase2-memory-leak` |
| Test | `test/` | Testing infrastructure | `test/phase3-integration-tests` |
| Docs | `docs/` | Documentation updates | `docs/phase1-setup-guide` |
| Refactor | `refactor/` | Code restructuring | `refactor/phase4-ui-components` |

### **Naming Pattern**

**Format:** `{type}/{phase-info}-{description}`

**Rules:**
- Use lowercase with hyphens
- Include phase number when applicable
- Keep descriptions concise but descriptive
- Use present tense verbs (setup, add, fix)

**Examples:**
```bash
# Phase branches
phase/1-foundation
phase/2-cli-integration
phase/3-context-system
phase/4-advanced-features
phase/5-production

# Feature branches
feature/phase1-nuxt-typescript-setup
feature/phase1-express-socketio-backend
feature/phase2-claude-sdk-integration
feature/phase3-redis-session-storage
feature/phase4-context-panel-ui

# Hotfix branches
hotfix/phase2-subprocess-cleanup
hotfix/phase3-context-memory-optimization

# Testing branches
test/phase1-vitest-setup
test/phase4-playwright-e2e
test/phase5-performance-benchmarks
```

---

## **Phase-Specific Branch Strategy**

## **Phase 1: Foundation (Weeks 1-2)**

### **Phase Branch**
```bash
phase/1-foundation
```

### **Feature Branches**
```bash
feature/phase1-nuxt-typescript-setup      # Nuxt 3 + TypeScript configuration
feature/phase1-tailwind-pinia-setup       # Styling and state management
feature/phase1-express-socketio-backend   # Backend server setup
feature/phase1-basic-chat-ui              # Chat interface components
feature/phase1-websocket-communication    # Real-time messaging
feature/phase1-message-flow               # End-to-end message handling
feature/phase1-testing-infrastructure     # Vitest/Jest setup
```

### **Deliverables & Merge Targets**
- All features merge to `phase/1-foundation`
- Phase completion merges to `develop`
- Tag: `v0.1.0-phase1-foundation`

---

## **Phase 2: CLI Integration (Weeks 3-4)**

### **Phase Branch**
```bash
phase/2-cli-integration
```

### **Feature Branches**
```bash
feature/phase2-claude-sdk-integration     # Claude Code SDK setup
feature/phase2-mcp-server-connection      # NetBox MCP server integration
feature/phase2-subprocess-management      # CLI process lifecycle
feature/phase2-tool-execution-tracking    # MCP tool monitoring
feature/phase2-streaming-responses        # Real-time response handling
feature/phase2-error-handling             # Robust error management
feature/phase2-sdk-integration-tests      # Integration test suite
```

### **Deliverables & Merge Targets**
- All features merge to `phase/2-cli-integration`
- Phase completion merges to `develop`
- Tag: `v0.2.0-phase2-cli-integration`

---

## **Phase 3: Context System (Weeks 5-6)**

### **Phase Branch**
```bash
phase/3-context-system
```

### **Feature Branches**
```bash
feature/phase3-redis-session-storage      # Redis integration and session storage
feature/phase3-conversation-history       # Message history management
feature/phase3-entity-extraction          # NetBox entity identification
feature/phase3-entity-tracking            # Entity relevance scoring
feature/phase3-context-enrichment         # Context injection logic
feature/phase3-token-management           # Context pruning algorithms
feature/phase3-context-tests              # Context system test suite
```

### **Deliverables & Merge Targets**
- All features merge to `phase/3-context-system`
- Phase completion merges to `develop`
- Tag: `v0.3.0-phase3-context-system`

---

## **Phase 4: Advanced Features (Weeks 7-8)**

### **Phase Branch**
```bash
phase/4-advanced-features
```

### **Feature Branches**
```bash
feature/phase4-rich-message-display       # Enhanced message formatting
feature/phase4-context-panel-ui           # Entity visualization panel
feature/phase4-real-time-indicators       # Typing and processing indicators
feature/phase4-export-import-system       # Conversation data management
feature/phase4-multi-session-management   # Session handling and switching
feature/phase4-advanced-ui-components     # Polished UI components
feature/phase4-e2e-testing-suite          # End-to-end test coverage
```

### **Deliverables & Merge Targets**
- All features merge to `phase/4-advanced-features`
- Phase completion merges to `develop`
- Tag: `v0.4.0-phase4-advanced-features`

---

## **Phase 5: Production (Weeks 9-10)**

### **Phase Branch**
```bash
phase/5-production
```

### **Feature Branches**
```bash
feature/phase5-docker-containerization    # Docker setup and optimization
feature/phase5-security-hardening         # Security measures and validation
feature/phase5-performance-optimization   # Performance tuning and caching
feature/phase5-monitoring-logging         # Operational monitoring setup
feature/phase5-deployment-automation      # Production deployment pipeline
feature/phase5-production-documentation   # Deployment and maintenance docs
feature/phase5-final-testing              # Production readiness testing
```

### **Deliverables & Merge Targets**
- All features merge to `phase/5-production`
- Phase completion merges to `develop`
- Final merge to `main` for production release
- Tag: `v1.0.0` (Production release)

---

## **Git Workflow Process**

### **Starting a New Phase**

```bash
# 1. Ensure develop branch is up to date
git checkout develop
git pull origin develop

# 2. Create and push phase branch
git checkout -b phase/{number}-{name}
git push -u origin phase/{number}-{name}

# 3. Create feature branches from phase branch
git checkout -b feature/phase{number}-{feature-name}
git push -u origin feature/phase{number}-{feature-name}
```

### **Daily Development Workflow**

```bash
# 1. Work on feature branch
git checkout feature/phase1-nuxt-setup
git add .
git commit -m "✨ feat: add Nuxt 3 TypeScript configuration"

# 2. Push feature updates
git push origin feature/phase1-nuxt-setup

# 3. Merge completed features to phase branch
git checkout phase/1-foundation
git merge feature/phase1-nuxt-setup
git push origin phase/1-foundation
```

### **Phase Completion Workflow**

```bash
# 1. Merge phase to develop
git checkout develop
git merge phase/1-foundation
git tag v0.1.0-phase1-foundation
git push origin develop --tags

# 2. Deploy to staging for testing
git checkout staging
git merge develop
git push origin staging

# 3. After validation, deploy to production
git checkout main
git merge develop
git tag v1.0.0
git push origin main --tags
```

---

## **Testing Branch Strategy**

### **Testing Infrastructure Branches**

```bash
# Unit testing setup
test/phase1-vitest-configuration
test/phase1-jest-backend-setup

# Integration testing
test/phase2-claude-sdk-integration-tests
test/phase3-context-system-tests

# End-to-end testing
test/phase4-playwright-e2e-setup
test/phase4-user-journey-tests

# Performance testing
test/phase5-load-testing-setup
test/phase5-performance-benchmarks

# Security testing
test/phase5-security-validation
test/phase5-penetration-tests
```

### **Testing Workflow**
- Testing branches created alongside feature development
- Merge to phase branch when tests are complete
- Automated testing on phase branch merges
- Comprehensive testing before production deployment

---

## **Documentation Branch Strategy**

### **Documentation Branches**

```bash
# Phase-specific documentation
docs/phase1-development-setup
docs/phase2-claude-integration-guide
docs/phase3-context-system-guide
docs/phase4-advanced-features-guide
docs/phase5-deployment-guide

# General documentation updates
docs/api-documentation-updates
docs/user-guide-creation
docs/troubleshooting-guide
```

### **Documentation Workflow**
- Documentation branches created for major updates
- Merge to develop alongside feature completion
- Keep documentation synchronized with code changes

---

## **Branch Protection Rules**

### **Protected Branches**
- `main` - Requires pull request, admin merge only
- `develop` - Requires pull request review, status checks
- `staging` - Requires pull request, automated testing
- `phase/*` - Requires pull request review

### **Merge Requirements**
- **main**: Admin approval + all status checks
- **develop**: 1 reviewer + status checks + no conflicts
- **staging**: Automated testing + no conflicts
- **phase branches**: 1 reviewer + basic status checks

---

## **Tagging Strategy**

### **Tag Formats**

```bash
# Phase completion tags
v0.1.0-phase1-foundation
v0.2.0-phase2-cli-integration
v0.3.0-phase3-context-system
v0.4.0-phase4-advanced-features
v0.5.0-phase5-production

# Release candidate tags
v1.0.0-rc1
v1.0.0-rc2

# Production release
v1.0.0

# Hotfix releases
v1.0.1
v1.0.2
```

### **Tagging Workflow**
- Tag phase completions on develop branch
- Tag release candidates on staging branch
- Tag production releases on main branch
- Use semantic versioning for all releases

---

## **Git Commands Reference**

### **Phase 1 Commands**

```bash
# Start Phase 1
git checkout develop
git checkout -b phase/1-foundation
git push -u origin phase/1-foundation

# Create feature branches
git checkout -b feature/phase1-nuxt-setup
git checkout -b feature/phase1-express-backend
git checkout -b feature/phase1-chat-ui
git checkout -b feature/phase1-websocket
git checkout -b feature/phase1-testing-setup

# Push all feature branches
for branch in feature/phase1-*; do
  git checkout $branch
  git push -u origin $branch
done
```

### **Phase 2 Commands**

```bash
# Start Phase 2
git checkout develop
git checkout -b phase/2-cli-integration
git push -u origin phase/2-cli-integration

# Create feature branches
git checkout -b feature/phase2-claude-sdk
git checkout -b feature/phase2-mcp-connection
git checkout -b feature/phase2-subprocess-mgmt
git checkout -b feature/phase2-tool-execution
git checkout -b feature/phase2-streaming
```

### **Phase 3 Commands**

```bash
# Start Phase 3
git checkout develop
git checkout -b phase/3-context-system
git push -u origin phase/3-context-system

# Create feature branches
git checkout -b feature/phase3-redis-storage
git checkout -b feature/phase3-conversation-history
git checkout -b feature/phase3-entity-tracking
git checkout -b feature/phase3-context-enrichment
```

### **Phase 4 Commands**

```bash
# Start Phase 4
git checkout develop
git checkout -b phase/4-advanced-features
git push -u origin phase/4-advanced-features

# Create feature branches
git checkout -b feature/phase4-rich-ui
git checkout -b feature/phase4-context-panel
git checkout -b feature/phase4-real-time-indicators
git checkout -b feature/phase4-export-import
```

### **Phase 5 Commands**

```bash
# Start Phase 5
git checkout develop
git checkout -b phase/5-production
git push -u origin phase/5-production

# Create feature branches
git checkout -b feature/phase5-docker
git checkout -b feature/phase5-security
git checkout -b feature/phase5-performance
git checkout -b feature/phase5-monitoring
git checkout -b feature/phase5-deployment
```

---

## **Emergency Procedures**

### **Hotfix Workflow**

```bash
# Critical bug found in production
git checkout main
git checkout -b hotfix/critical-security-patch
# Fix the bug
git commit -m "🚑️ hotfix: patch critical security vulnerability"
git checkout main
git merge hotfix/critical-security-patch
git tag v1.0.1
git push origin main --tags

# Also merge to develop
git checkout develop
git merge hotfix/critical-security-patch
git push origin develop
```

### **Rollback Procedure**

```bash
# Rollback to previous release
git checkout main
git reset --hard v1.0.0  # Previous stable version
git push --force origin main

# Update develop branch
git checkout develop
git reset --hard main
git push --force origin develop
```

---

## **Best Practices**

### **Commit Message Standards**
- Use conventional commits with emojis
- Reference issue numbers when applicable
- Keep first line under 72 characters
- Use imperative mood ("add" not "added")

### **Branch Management**
- Delete feature branches after merging
- Keep phase branches until project completion
- Regular cleanup of stale branches
- Use descriptive branch names

### **Merge Strategies**
- Use merge commits for phase completions
- Squash small feature commits if appropriate
- Preserve commit history for major features
- Always test before merging to main branches

This git branch strategy provides comprehensive organization for the 10-week development project while maintaining code quality, enabling parallel development, and ensuring reliable deployment processes.