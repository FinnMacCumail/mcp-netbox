# Git Branch Strategy - NetBox MCP Development

## **Overview**

This document defines the git branching strategy for the NetBox MCP Server development project. The strategy supports parallel feature development, comprehensive testing, and reliable deployment workflows.

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

### **Feature-Based Development Structure**

```
develop
├── feature/api-improvements
├── feature/bulk-operations
├── feature/performance-optimization
├── feature/security-enhancements
└── feature/documentation-updates
```

---

## **Branch Types & Naming Conventions**

### **Branch Type Prefixes**

| Type | Prefix | Purpose | Example |
|------|--------|---------|---------|
| Feature | `feature/` | Specific feature development | `feature/bulk-cable-creation` |
| Hotfix | `hotfix/` | Critical bug fixes | `hotfix/api-authentication` |
| Test | `test/` | Testing infrastructure | `test/integration-tests` |
| Docs | `docs/` | Documentation updates | `docs/api-reference` |
| Refactor | `refactor/` | Code restructuring | `refactor/tool-organization` |
| Fix | `fix/` | Bug fixes (non-critical) | `fix/device-info-pagination` |

### **Naming Pattern**

**Format:** `{type}/{description}`

**Rules:**
- Use lowercase with hyphens
- Keep descriptions concise but descriptive  
- Use present tense verbs (add, fix, update)
- Include issue numbers when applicable (e.g. `fix/issue-123-device-pagination`)

**Examples:**
```bash
# Feature branches
feature/bulk-cable-creation
feature/device-management-improvements
feature/api-authentication-enhancement
feature/power-management-tools
feature/virtualization-support

# Fix branches  
fix/device-info-token-limit
fix/bulk-cable-defensive-handling
fix/api-pagination-issues

# Hotfix branches
hotfix/critical-security-patch
hotfix/memory-leak-fix

# Testing branches
test/integration-test-suite
test/performance-benchmarks
test/security-validation
```

---

## **Development Workflow Strategy**

## **Feature Development**

### **Feature Branches**
Create feature branches for all new functionality, improvements, and significant changes:

```bash
# API and MCP Tools
feature/bulk-device-provisioning          # Bulk device creation tools
feature/power-management-suite             # Power infrastructure management
feature/virtualization-tools              # VM and cluster management
feature/api-authentication                 # Enhanced API security

# Performance and Optimization  
feature/caching-improvements               # TTL-based caching system
feature/query-optimization                 # Database query performance
feature/memory-management                  # Memory usage optimization

# User Experience
feature/bridget-persona-enhancement        # AI assistant improvements
feature/error-handling-improvements        # Better error messages
feature/documentation-updates             # API and user documentation
```

### **Development Process**
1. **Branch Creation**: Create feature branch from `develop`
2. **Development**: Implement feature with tests
3. **Code Review**: Submit pull request for review
4. **Testing**: Ensure all tests pass and coverage maintained
5. **Merge**: Merge to `develop` after approval

### **Release Process**
- **Minor Releases**: Feature additions, improvements (v1.1.0, v1.2.0)
- **Major Releases**: Breaking changes, major restructuring (v2.0.0, v3.0.0)
- **Patch Releases**: Bug fixes, security patches (v1.1.1, v1.1.2)

---

## **Git Workflow Process**

### **Starting a New Feature**

```bash
# 1. Ensure develop branch is up to date
git checkout develop
git pull origin develop

# 2. Create and push feature branch
git checkout -b feature/{feature-name}
git push -u origin feature/{feature-name}
```

### **Daily Development Workflow**

```bash
# 1. Work on feature branch
git checkout feature/bulk-cable-creation
git add .
git commit -m "✨ feat: add bulk cable creation with validation"

# 2. Push feature updates
git push origin feature/bulk-cable-creation

# 3. Create pull request when ready
# Use GitHub UI or GitHub CLI to create pull request to develop branch
```

### **Release Workflow**

```bash
# 1. Prepare release on develop
git checkout develop
git tag v1.2.0
git push origin develop --tags

# 2. Deploy to staging for testing
git checkout staging
git merge develop
git push origin staging

# 3. After validation, deploy to production
git checkout main
git merge develop
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

### **Feature Development Commands**

```bash
# Start a new feature
git checkout develop
git pull origin develop
git checkout -b feature/bulk-cable-creation
git push -u origin feature/bulk-cable-creation

# Work on feature
git add .
git commit -m "✨ feat: implement bulk cable creation API"
git push origin feature/bulk-cable-creation

# Create pull request (using GitHub CLI)
gh pr create --title "Add bulk cable creation functionality" --body "Implements bulk cable creation with validation and error handling"
```

### **Bug Fix Commands**

```bash
# Start a bug fix
git checkout develop
git pull origin develop
git checkout -b fix/device-info-pagination
git push -u origin fix/device-info-pagination

# Fix and commit
git add .
git commit -m "🐛 fix: resolve device info pagination issue"
git push origin fix/device-info-pagination

# Create pull request
gh pr create --title "Fix device info pagination" --body "Resolves pagination issue in device info endpoint"
```

### **Release Commands**

```bash
# Prepare release
git checkout develop
git pull origin develop
git tag v1.2.0
git push origin develop --tags

# Deploy to staging
git checkout staging
git merge develop
git push origin staging

# Deploy to production (after testing)
git checkout main
git merge develop
git push origin main --tags
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

This git branch strategy provides comprehensive organization for NetBox MCP development while maintaining code quality, enabling parallel development, and ensuring reliable deployment processes.