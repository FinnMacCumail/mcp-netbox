#!/usr/bin/env python3
"""
Simple CLI wrapper for the Adaptive Intelligence System
"""

import sys
import argparse
from netbox_mcp.registry import execute_tool, load_tools
from netbox_mcp.dependencies import NetBoxClientManager
from netbox_mcp.config import load_config


def main():
    parser = argparse.ArgumentParser(
        description="NetBox Adaptive Intelligence CLI",
        epilog="""
Examples:
  python adaptive_cli.py "Show all sites"
  python adaptive_cli.py "Get rack elevation for R01-A15 in site DM-Akron"
  python adaptive_cli.py "Show all virtual machines in cluster DO-AMS3"
  python adaptive_cli.py "Get IP usage statistics for prefix 10.112.128.0/17"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "query", 
        help="Natural language query about NetBox infrastructure"
    )
    
    parser.add_argument(
        "--session-id",
        help="Optional session ID for conversation context"
    )
    
    parser.add_argument(
        "--force-system",
        choices=["intelligent", "legacy"],
        help="Force a specific system (default: auto)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed processing information"
    )

    args = parser.parse_args()
    
    print("🧠 NetBox Adaptive Intelligence System")
    print("=" * 50)
    print(f"Query: {args.query}")
    print()
    
    try:
        # Load tools and initialize client
        load_tools()
        config = load_config()
        NetBoxClientManager.initialize(config)
        client = NetBoxClientManager.get_client()
        
        # Execute query using adaptive intelligence
        print("🔄 Processing with adaptive intelligence...")
        result = execute_tool(
            'process_query',
            client,
            query=args.query,
            session_id=args.session_id,
            force_system=args.force_system
        )
        
        # Display results
        success = result.get("success", False)
        system_used = result.get("orchestration_metadata", {}).get("system_used", "unknown")
        response = result.get("response", "No response")
        error = result.get("error", "")
        
        print(f"✅ Success: {success}")
        print(f"🧠 System: {system_used}")
        print()
        
        if success:
            print("📋 Response:")
            print("-" * 40)
            print(response)
        else:
            print("❌ Error:")
            print("-" * 40)
            print(error)
        
        if args.verbose and "orchestration_metadata" in result:
            print()
            print("🔍 Debug Info:")
            print("-" * 40)
            import json
            print(json.dumps(result["orchestration_metadata"], indent=2))
            
    except Exception as e:
        print(f"❌ CLI Error: {e}")
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())