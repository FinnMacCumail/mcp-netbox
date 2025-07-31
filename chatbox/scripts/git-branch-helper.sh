#!/bin/bash

# Git Branch Helper Script for NetBox MCP Chatbox Development
# Automates branch creation and management for the 5-phase development strategy

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Phase definitions
declare -A PHASES=(
    ["1"]="foundation"
    ["2"]="cli-integration"
    ["3"]="context-system"
    ["4"]="advanced-features"
    ["5"]="production"
)

# Feature branches for each phase
declare -A PHASE1_FEATURES=(
    ["nuxt-setup"]="Nuxt 3 + TypeScript configuration"
    ["tailwind-pinia"]="Styling and state management setup"
    ["express-backend"]="Express + Socket.io backend server"
    ["chat-ui"]="Basic chat interface components"
    ["websocket"]="WebSocket communication setup"
    ["message-flow"]="End-to-end message handling"
    ["testing-setup"]="Vitest/Jest testing infrastructure"
)

declare -A PHASE2_FEATURES=(
    ["claude-sdk"]="Claude Code SDK integration"
    ["mcp-connection"]="NetBox MCP server connection"
    ["subprocess-mgmt"]="CLI subprocess management"
    ["tool-execution"]="MCP tool execution tracking"
    ["streaming"]="Real-time response streaming"
    ["error-handling"]="Robust error management"
    ["integration-tests"]="SDK integration test suite"
)

declare -A PHASE3_FEATURES=(
    ["redis-storage"]="Redis session storage integration"
    ["conversation-history"]="Message history management"
    ["entity-extraction"]="NetBox entity identification"
    ["entity-tracking"]="Entity relevance scoring"
    ["context-enrichment"]="Context injection logic"
    ["token-management"]="Context pruning algorithms"
    ["context-tests"]="Context system test suite"
)

declare -A PHASE4_FEATURES=(
    ["rich-ui"]="Enhanced message formatting"
    ["context-panel"]="Entity visualization panel"
    ["real-time-indicators"]="Typing and processing indicators"
    ["export-import"]="Conversation data management"
    ["multi-session"]="Session handling and switching"
    ["ui-components"]="Polished UI components"
    ["e2e-tests"]="End-to-end test coverage"
)

declare -A PHASE5_FEATURES=(
    ["docker"]="Docker containerization"
    ["security"]="Security hardening measures"
    ["performance"]="Performance optimization"
    ["monitoring"]="Operational monitoring setup"
    ["deployment"]="Production deployment pipeline"
    ["documentation"]="Production documentation"
    ["final-testing"]="Production readiness testing"
)

# Helper functions
print_header() {
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}  Git Branch Helper - NetBox MCP${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository!"
        exit 1
    fi
}

# Check if branch exists
branch_exists() {
    git show-ref --verify --quiet refs/heads/"$1"
}

# Check if remote branch exists
remote_branch_exists() {
    git show-ref --verify --quiet refs/remotes/origin/"$1"
}

# Ensure we're on develop branch
ensure_develop_branch() {
    local current_branch=$(git branch --show-current)
    if [ "$current_branch" != "develop" ]; then
        print_info "Switching to develop branch..."
        git checkout develop
        git pull origin develop
    else
        print_info "Already on develop branch, pulling latest changes..."
        git pull origin develop
    fi
}

# Create phase branch
create_phase_branch() {
    local phase_num=$1
    local phase_name=${PHASES[$phase_num]}
    local branch_name="phase/${phase_num}-${phase_name}"
    
    print_info "Creating phase branch: $branch_name"
    
    if branch_exists "$branch_name"; then
        print_warning "Phase branch $branch_name already exists!"
        return 1
    fi
    
    ensure_develop_branch
    git checkout -b "$branch_name"
    git push -u origin "$branch_name"
    print_success "Created and pushed phase branch: $branch_name"
}

# Create feature branches for a phase
create_feature_branches() {
    local phase_num=$1
    local phase_name=${PHASES[$phase_num]}
    local phase_branch="phase/${phase_num}-${phase_name}"
    
    # Check if phase branch exists
    if ! branch_exists "$phase_branch"; then
        print_error "Phase branch $phase_branch doesn't exist! Create it first."
        return 1
    fi
    
    # Switch to phase branch
    git checkout "$phase_branch"
    git pull origin "$phase_branch"
    
    # Get feature array name
    local features_var="PHASE${phase_num}_FEATURES[@]"
    
    # Create feature branches
    print_info "Creating feature branches for Phase $phase_num..."
    
    case $phase_num in
        1)
            for feature in "${!PHASE1_FEATURES[@]}"; do
                create_single_feature_branch "$phase_num" "$feature" "${PHASE1_FEATURES[$feature]}"
            done
            ;;
        2)
            for feature in "${!PHASE2_FEATURES[@]}"; do
                create_single_feature_branch "$phase_num" "$feature" "${PHASE2_FEATURES[$feature]}"
            done
            ;;
        3)
            for feature in "${!PHASE3_FEATURES[@]}"; do
                create_single_feature_branch "$phase_num" "$feature" "${PHASE3_FEATURES[$feature]}"
            done
            ;;
        4)
            for feature in "${!PHASE4_FEATURES[@]}"; do
                create_single_feature_branch "$phase_num" "$feature" "${PHASE4_FEATURES[$feature]}"
            done
            ;;
        5)
            for feature in "${!PHASE5_FEATURES[@]}"; do
                create_single_feature_branch "$phase_num" "$feature" "${PHASE5_FEATURES[$feature]}"
            done
            ;;
    esac
}

# Create a single feature branch
create_single_feature_branch() {
    local phase_num=$1
    local feature_name=$2
    local description=$3
    local branch_name="feature/phase${phase_num}-${feature_name}"
    
    if branch_exists "$branch_name"; then
        print_warning "Feature branch $branch_name already exists, skipping..."
        return 0
    fi
    
    git checkout -b "$branch_name"
    git push -u origin "$branch_name"
    print_success "Created feature branch: $branch_name"
    print_info "  Description: $description"
    
    # Switch back to phase branch for next feature
    git checkout "phase/${phase_num}-${PHASES[$phase_num]}"
}

# List all branches for a phase
list_phase_branches() {
    local phase_num=$1
    local phase_name=${PHASES[$phase_num]}
    
    print_info "Branches for Phase $phase_num - $phase_name:"
    echo
    
    # List phase branch
    local phase_branch="phase/${phase_num}-${phase_name}"
    if branch_exists "$phase_branch"; then
        echo -e "  ${GREEN}📁 $phase_branch${NC}"
    else
        echo -e "  ${RED}📁 $phase_branch (not created)${NC}"
    fi
    
    # List feature branches
    case $phase_num in
        1)
            for feature in "${!PHASE1_FEATURES[@]}"; do
                local branch_name="feature/phase${phase_num}-${feature}"
                if branch_exists "$branch_name"; then
                    echo -e "    ${GREEN}🔧 $branch_name${NC}"
                else
                    echo -e "    ${RED}🔧 $branch_name (not created)${NC}"
                fi
            done
            ;;
        2)
            for feature in "${!PHASE2_FEATURES[@]}"; do
                local branch_name="feature/phase${phase_num}-${feature}"
                if branch_exists "$branch_name"; then
                    echo -e "    ${GREEN}🔧 $branch_name${NC}"
                else
                    echo -e "    ${RED}🔧 $branch_name (not created)${NC}"
                fi
            done
            ;;
        3)
            for feature in "${!PHASE3_FEATURES[@]}"; do
                local branch_name="feature/phase${phase_num}-${feature}"
                if branch_exists "$branch_name"; then
                    echo -e "    ${GREEN}🔧 $branch_name${NC}"
                else
                    echo -e "    ${RED}🔧 $branch_name (not created)${NC}"
                fi
            done
            ;;
        4)
            for feature in "${!PHASE4_FEATURES[@]}"; do
                local branch_name="feature/phase${phase_num}-${feature}"
                if branch_exists "$branch_name"; then
                    echo -e "    ${GREEN}🔧 $branch_name${NC}"
                else
                    echo -e "    ${RED}🔧 $branch_name (not created)${NC}"
                fi
            done
            ;;
        5)
            for feature in "${!PHASE5_FEATURES[@]}"; do
                local branch_name="feature/phase${phase_num}-${feature}"
                if branch_exists "$branch_name"; then
                    echo -e "    ${GREEN}🔧 $branch_name${NC}"
                else
                    echo -e "    ${RED}🔧 $branch_name (not created)${NC}"
                fi
            done
            ;;
    esac
    echo
}

# Merge feature to phase branch
merge_feature_to_phase() {
    local phase_num=$1
    local feature_name=$2
    local phase_name=${PHASES[$phase_num]}
    local phase_branch="phase/${phase_num}-${phase_name}"
    local feature_branch="feature/phase${phase_num}-${feature_name}"
    
    if ! branch_exists "$feature_branch"; then
        print_error "Feature branch $feature_branch doesn't exist!"
        return 1
    fi
    
    if ! branch_exists "$phase_branch"; then
        print_error "Phase branch $phase_branch doesn't exist!"
        return 1
    fi
    
    print_info "Merging $feature_branch into $phase_branch..."
    
    # Switch to phase branch and pull latest
    git checkout "$phase_branch"
    git pull origin "$phase_branch"
    
    # Merge feature branch
    git merge "$feature_branch" --no-ff -m "🔀 merge: integrate $feature_name into phase $phase_num"
    git push origin "$phase_branch"
    
    print_success "Successfully merged $feature_branch into $phase_branch"
    
    # Ask if user wants to delete feature branch
    read -p "Delete feature branch $feature_branch? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git branch -d "$feature_branch"
        git push origin --delete "$feature_branch"
        print_success "Deleted feature branch $feature_branch"
    fi
}

# Complete phase and merge to develop
complete_phase() {
    local phase_num=$1
    local phase_name=${PHASES[$phase_num]}
    local phase_branch="phase/${phase_num}-${phase_name}"
    local tag_name="v0.${phase_num}.0-phase${phase_num}-${phase_name}"
    
    if ! branch_exists "$phase_branch"; then
        print_error "Phase branch $phase_branch doesn't exist!"
        return 1
    fi
    
    print_info "Completing Phase $phase_num and merging to develop..."
    
    # Switch to develop and pull latest
    ensure_develop_branch
    
    # Merge phase branch
    git merge "$phase_branch" --no-ff -m "🎉 feat: complete Phase $phase_num - $phase_name"
    
    # Create tag
    git tag "$tag_name" -m "Phase $phase_num completion: $phase_name"
    
    # Push changes and tags
    git push origin develop
    git push origin "$tag_name"
    
    print_success "Phase $phase_num completed and merged to develop"
    print_success "Created tag: $tag_name"
    
    # Ask if user wants to delete phase branch
    read -p "Delete phase branch $phase_branch? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git branch -d "$phase_branch"
        git push origin --delete "$phase_branch"
        print_success "Deleted phase branch $phase_branch"
    fi
}

# Show usage information
show_usage() {
    echo "Usage: $0 <command> [options]"
    echo
    echo "Commands:"
    echo "  init-phase <phase_number>        Create phase branch"
    echo "  create-features <phase_number>   Create all feature branches for phase"
    echo "  setup-phase <phase_number>       Create phase + all feature branches"
    echo "  list-phase <phase_number>        List all branches for phase"
    echo "  merge-feature <phase> <feature>  Merge feature branch to phase"
    echo "  complete-phase <phase_number>    Complete phase and merge to develop"
    echo "  list-all                         List all phases and their status"
    echo "  cleanup                          Clean up merged branches"
    echo
    echo "Phase Numbers:"
    for phase_num in "${!PHASES[@]}"; do
        echo "  $phase_num: ${PHASES[$phase_num]}"
    done
    echo
    echo "Examples:"
    echo "  $0 setup-phase 1                # Set up Phase 1 completely"
    echo "  $0 merge-feature 1 nuxt-setup   # Merge nuxt-setup to phase 1"
    echo "  $0 complete-phase 1              # Complete Phase 1"
    echo "  $0 list-all                      # Show all phases status"
}

# List all phases and their status
list_all_phases() {
    print_info "NetBox MCP Chatbox Development - All Phases Status"
    echo
    
    for phase_num in {1..5}; do
        local phase_name=${PHASES[$phase_num]}
        local phase_branch="phase/${phase_num}-${phase_name}"
        
        echo -e "${BLUE}Phase $phase_num: $phase_name${NC}"
        
        if branch_exists "$phase_branch"; then
            echo -e "  ${GREEN}✅ Phase branch created${NC}"
        else
            echo -e "  ${RED}❌ Phase branch not created${NC}"
        fi
        
        # Count feature branches
        local feature_count=0
        local created_count=0
        
        case $phase_num in
            1)
                feature_count=${#PHASE1_FEATURES[@]}
                for feature in "${!PHASE1_FEATURES[@]}"; do
                    if branch_exists "feature/phase${phase_num}-${feature}"; then
                        ((created_count++))
                    fi
                done
                ;;
            2)
                feature_count=${#PHASE2_FEATURES[@]}
                for feature in "${!PHASE2_FEATURES[@]}"; do
                    if branch_exists "feature/phase${phase_num}-${feature}"; then
                        ((created_count++))
                    fi
                done
                ;;
            3)
                feature_count=${#PHASE3_FEATURES[@]}
                for feature in "${!PHASE3_FEATURES[@]}"; do
                    if branch_exists "feature/phase${phase_num}-${feature}"; then
                        ((created_count++))
                    fi
                done
                ;;
            4)
                feature_count=${#PHASE4_FEATURES[@]}
                for feature in "${!PHASE4_FEATURES[@]}"; do
                    if branch_exists "feature/phase${phase_num}-${feature}"; then
                        ((created_count++))
                    fi
                done
                ;;
            5)
                feature_count=${#PHASE5_FEATURES[@]}
                for feature in "${!PHASE5_FEATURES[@]}"; do
                    if branch_exists "feature/phase${phase_num}-${feature}"; then
                        ((created_count++))
                    fi
                done
                ;;
        esac
        
        echo -e "  📊 Feature branches: $created_count/$feature_count created"
        
        # Check if phase is completed (tagged)
        if git tag -l | grep -q "v0.${phase_num}.0-phase${phase_num}-${phase_name}"; then
            echo -e "  ${GREEN}🎉 Phase completed${NC}"
        else
            echo -e "  ${YELLOW}🚧 Phase in progress${NC}"
        fi
        
        echo
    done
}

# Cleanup merged branches
cleanup_branches() {
    print_info "Cleaning up merged branches..."
    
    # Switch to develop first
    ensure_develop_branch
    
    # Find merged branches
    local merged_branches=$(git branch --merged | grep -E "(feature/|hotfix/)" | grep -v "develop" || true)
    
    if [ -z "$merged_branches" ]; then
        print_info "No merged branches to clean up"
        return 0
    fi
    
    echo "Merged branches found:"
    echo "$merged_branches"
    echo
    
    read -p "Delete these merged branches? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$merged_branches" | xargs -n 1 git branch -d
        print_success "Cleaned up merged branches"
    else
        print_info "Cleanup cancelled"
    fi
}

# Main script logic
main() {
    print_header
    check_git_repo
    
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    case $1 in
        "init-phase")
            if [ -z "$2" ]; then
                print_error "Phase number required"
                show_usage
                exit 1
            fi
            if [ -z "${PHASES[$2]}" ]; then
                print_error "Invalid phase number: $2"
                exit 1
            fi
            create_phase_branch "$2"
            ;;
        "create-features")
            if [ -z "$2" ]; then
                print_error "Phase number required"
                show_usage
                exit 1
            fi
            if [ -z "${PHASES[$2]}" ]; then
                print_error "Invalid phase number: $2"
                exit 1
            fi
            create_feature_branches "$2"
            ;;
        "setup-phase")
            if [ -z "$2" ]; then
                print_error "Phase number required"
                show_usage
                exit 1
            fi
            if [ -z "${PHASES[$2]}" ]; then
                print_error "Invalid phase number: $2"
                exit 1
            fi
            create_phase_branch "$2"
            create_feature_branches "$2"
            ;;
        "list-phase")
            if [ -z "$2" ]; then
                print_error "Phase number required"
                show_usage
                exit 1
            fi
            if [ -z "${PHASES[$2]}" ]; then
                print_error "Invalid phase number: $2"
                exit 1
            fi
            list_phase_branches "$2"
            ;;
        "merge-feature")
            if [ -z "$2" ] || [ -z "$3" ]; then
                print_error "Phase number and feature name required"
                show_usage
                exit 1
            fi
            if [ -z "${PHASES[$2]}" ]; then
                print_error "Invalid phase number: $2"
                exit 1
            fi
            merge_feature_to_phase "$2" "$3"
            ;;
        "complete-phase")
            if [ -z "$2" ]; then
                print_error "Phase number required"
                show_usage
                exit 1
            fi
            if [ -z "${PHASES[$2]}" ]; then
                print_error "Invalid phase number: $2"
                exit 1
            fi
            complete_phase "$2"
            ;;
        "list-all")
            list_all_phases
            ;;
        "cleanup")
            cleanup_branches
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"