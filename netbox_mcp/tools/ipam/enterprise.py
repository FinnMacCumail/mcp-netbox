#!/usr/bin/env python3
"""
IPAM Enterprise Automation Tools

High-level enterprise tools for complex IPAM workflows, capacity planning,
and automated network provisioning with cross-domain integration.
"""

from typing import Dict, Optional, Any
import logging
from ...registry import mcp_tool
from ...client import NetBoxClient

logger = logging.getLogger(__name__)

@mcp_tool(category="ipam")
def netbox_get_ip_usage(
    client: NetBoxClient,
    prefix: str
) -> Dict[str, Any]:
    """
    Get IP address usage statistics for a prefix.
    
    Args:
        client: NetBoxClient instance (injected)
        prefix: Network prefix (e.g., "192.168.1.0/24")
        
    Returns:
        Usage statistics including total, used, available IPs
        
    Example:
        netbox_get_ip_usage("192.168.1.0/24")
    """
    try:
        logger.info(f"Getting IP usage for prefix: {prefix}")
        
        # Find the prefix
        prefixes = client.ipam.prefixes.filter(prefix=prefix)
        
        if not prefixes:
            return {
                "success": False,
                "error": f"Prefix '{prefix}' not found",
                "error_type": "PrefixNotFound"
            }
        
        prefix_obj = prefixes[0]
        
        # Calculate usage
        prefix_size = prefix_obj.get("_depth", 0)  # Number of host bits
        total_hosts = 2 ** (32 - int(prefix.split('/')[1])) - 2  # Exclude network and broadcast
        
        # Get used IPs in this prefix
        used_ips = client.ipam.ip_addresses.filter(parent=prefix)
        used_count = len(used_ips)
        available_count = total_hosts - used_count
        usage_percent = (used_count / total_hosts * 100) if total_hosts > 0 else 0
        
        return {
            "success": True,
            "prefix": prefix,
            "total_addresses": total_hosts,
            "used_addresses": used_count,
            "available_addresses": available_count,
            "usage_percentage": round(usage_percent, 2),
            "prefix_details": prefix_obj
        }
        
    except Exception as e:
        logger.error(f"Failed to get IP usage for {prefix}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="ipam")
def netbox_get_prefix_utilization(
    client: NetBoxClient,
    prefix: str,
    include_child_prefixes: bool = True,
    include_detailed_breakdown: bool = False,
    tenant: Optional[str] = None,
    vrf: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get comprehensive prefix utilization report for capacity planning.
    
    This enterprise-grade function provides detailed analysis of IP address usage
    within a prefix, including child prefix analysis, utilization trends, and
    capacity planning insights essential for network growth planning.
    
    Args:
        client: NetBoxClient instance (injected)
        prefix: Network prefix to analyze (e.g., "10.0.0.0/16")
        include_child_prefixes: Include utilization of child prefixes (default: True)
        include_detailed_breakdown: Include detailed IP allocation breakdown (default: False)
        tenant: Optional tenant filter for multi-tenant analysis
        vrf: Optional VRF filter for VRF-specific analysis
        
    Returns:
        Comprehensive utilization report with capacity planning insights
        
    Examples:
        # Basic utilization report
        netbox_get_prefix_utilization("10.0.0.0/16")
        
        # Detailed multi-tenant analysis
        netbox_get_prefix_utilization(
            prefix="192.168.0.0/16",
            include_child_prefixes=True,
            include_detailed_breakdown=True,
            tenant="enterprise-corp"
        )
        
        # VRF-specific capacity planning
        netbox_get_prefix_utilization(
            prefix="172.16.0.0/12",
            vrf="customer-a-vrf",
            include_detailed_breakdown=True
        )
    """
    try:
        logger.info(f"Analyzing prefix utilization for: {prefix}")
        
        # Step 1: Find and validate the target prefix
        prefix_filters = {"prefix": prefix}
        if tenant:
            prefix_filters["tenant"] = tenant
        if vrf:
            prefix_filters["vrf"] = vrf
        
        prefixes = client.ipam.prefixes.filter(**prefix_filters)
        
        if not prefixes:
            # Try alternative lookups
            if tenant or vrf:
                # Retry without restrictive filters to see if prefix exists
                alt_prefixes = client.ipam.prefixes.filter(prefix=prefix)
                if alt_prefixes:
                    return {
                        "success": False,
                        "error": f"Prefix '{prefix}' exists but not accessible with specified tenant/VRF filters",
                        "error_type": "FilterMismatchError"
                    }
            
            return {
                "success": False,
                "error": f"Prefix '{prefix}' not found",
                "error_type": "PrefixNotFoundError"
            }
        
        target_prefix = prefixes[0]
        prefix_id = target_prefix["id"]
        
        logger.debug(f"Found target prefix: {target_prefix['prefix']} (ID: {prefix_id})")
        
        # Step 2: Calculate basic utilization metrics
        import ipaddress
        try:
            network = ipaddress.ip_network(prefix, strict=False)
            total_addresses = network.num_addresses
            
            # For /31 and /32 prefixes, all addresses are usable
            if network.prefixlen >= 31:
                usable_addresses = total_addresses
            else:
                # Subtract network and broadcast addresses
                usable_addresses = total_addresses - 2
                
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid prefix format: {e}",
                "error_type": "ValidationError"
            }
        
        # Step 3: Count allocated IP addresses in this prefix
        ip_filters = {"parent": prefix}
        if tenant:
            ip_filters["tenant"] = tenant
        if vrf:
            ip_filters["vrf"] = vrf
        
        allocated_ips = client.ipam.ip_addresses.filter(**ip_filters)
        allocated_count = len(allocated_ips)
        
        # Step 4: Analyze child prefixes if requested
        child_prefix_analysis = {}
        total_child_addresses = 0
        
        if include_child_prefixes:
            logger.debug("Analyzing child prefixes...")
            
            child_filters = {"within": prefix}
            if tenant:
                child_filters["tenant"] = tenant
            if vrf:
                child_filters["vrf"] = vrf
            
            child_prefixes = client.ipam.prefixes.filter(**child_filters)
            
            # Exclude the parent prefix itself
            child_prefixes = [cp for cp in child_prefixes if cp["id"] != prefix_id]
            
            child_prefix_analysis = {
                "child_count": len(child_prefixes),
                "child_prefixes": [],
                "total_child_addresses": 0
            }
            
            for child in child_prefixes:
                try:
                    child_network = ipaddress.ip_network(child["prefix"], strict=False)
                    child_addresses = child_network.num_addresses
                    total_child_addresses += child_addresses
                    
                    # Get IP count for this child prefix
                    child_ip_filters = {"parent": child["prefix"]}
                    if tenant:
                        child_ip_filters["tenant"] = tenant
                    if vrf:
                        child_ip_filters["vrf"] = vrf
                    
                    child_ips = client.ipam.ip_addresses.filter(**child_ip_filters)
                    child_ip_count = len(child_ips)
                    
                    child_utilization = (child_ip_count / child_addresses * 100) if child_addresses > 0 else 0
                    
                    child_info = {
                        "prefix": child["prefix"],
                        "id": child["id"],
                        "status": child.get("status", {}).get("label", "Unknown"),
                        "total_addresses": child_addresses,
                        "allocated_ips": child_ip_count,
                        "utilization_percent": round(child_utilization, 2),
                        "description": child.get("description", "")
                    }
                    
                    if child.get("role"):
                        child_info["role"] = child["role"].get("name", "Unknown")
                    
                    child_prefix_analysis["child_prefixes"].append(child_info)
                    
                except ValueError:
                    logger.warning(f"Could not parse child prefix: {child['prefix']}")
                    continue
            
            child_prefix_analysis["total_child_addresses"] = total_child_addresses
        
        # Step 5: Calculate utilization metrics
        available_addresses = usable_addresses - allocated_count - total_child_addresses
        utilization_percent = (allocated_count / usable_addresses * 100) if usable_addresses > 0 else 0
        child_prefix_percent = (total_child_addresses / usable_addresses * 100) if usable_addresses > 0 else 0
        available_percent = 100 - utilization_percent - child_prefix_percent
        
        # Step 6: Generate detailed breakdown if requested
        detailed_breakdown = {}
        if include_detailed_breakdown:
            logger.debug("Generating detailed allocation breakdown...")
            
            # Analyze IP status distribution
            status_breakdown = {}
            role_breakdown = {}
            tenant_breakdown = {}
            
            for ip in allocated_ips:
                # Status breakdown
                status = ip.get("status", {}).get("label", "Unknown")
                status_breakdown[status] = status_breakdown.get(status, 0) + 1
                
                # Role breakdown (if IP has a role)
                if ip.get("role"):
                    role = ip["role"].get("name", "Unknown")
                    role_breakdown[role] = role_breakdown.get(role, 0) + 1
                
                # Tenant breakdown (if IP has a tenant)
                if ip.get("tenant"):
                    tenant_name = ip["tenant"].get("name", "Unknown")
                    tenant_breakdown[tenant_name] = tenant_breakdown.get(tenant_name, 0) + 1
            
            detailed_breakdown = {
                "ip_status_distribution": status_breakdown,
                "ip_role_distribution": role_breakdown,
                "ip_tenant_distribution": tenant_breakdown,
                "sample_allocated_ips": allocated_ips[:10]  # First 10 IPs as sample
            }
        
        # Step 7: Capacity planning insights
        capacity_insights = {
            "utilization_status": "low" if utilization_percent < 50 else "medium" if utilization_percent < 80 else "high",
            "projected_exhaustion": None,
            "recommended_action": "monitor"
        }
        
        if utilization_percent > 80:
            capacity_insights["recommended_action"] = "plan_expansion"
        elif utilization_percent > 90:
            capacity_insights["recommended_action"] = "immediate_action_required"
        
        # Estimate addresses remaining at current rate (simplified)
        if available_addresses < (usable_addresses * 0.1):  # Less than 10% available
            capacity_insights["recommended_action"] = "critical_expansion_needed"
        
        # Step 8: Build comprehensive response
        result = {
            "success": True,
            "prefix_analysis": {
                "prefix": prefix,
                "prefix_id": prefix_id,
                "network_size": f"/{network.prefixlen}",
                "total_addresses": total_addresses,
                "usable_addresses": usable_addresses,
                "allocated_ips": allocated_count,
                "available_addresses": available_addresses,
                "utilization_percent": round(utilization_percent, 2),
                "available_percent": round(available_percent, 2)
            },
            "capacity_planning": capacity_insights,
            "prefix_details": target_prefix
        }
        
        if include_child_prefixes:
            result["child_prefix_analysis"] = child_prefix_analysis
            result["child_prefix_percent"] = round(child_prefix_percent, 2)
        
        if include_detailed_breakdown:
            result["detailed_breakdown"] = detailed_breakdown
        
        if tenant:
            result["tenant_filter"] = tenant
        if vrf:
            result["vrf_filter"] = vrf
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze prefix utilization for {prefix}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp_tool(category="ipam")
def netbox_find_duplicate_ips(
    client: NetBoxClient,
    vrf: Optional[str] = None,
    tenant: Optional[str] = None,
    include_severity_analysis: bool = True,
    include_resolution_recommendations: bool = True,
    limit: int = 1000
) -> Dict[str, Any]:
    """
    Find duplicate IP addresses in NetBox for network auditing and data quality assurance.
    
    This enterprise-grade auditing tool identifies IP address conflicts across NetBox,
    providing detailed analysis including assignment context, conflict severity assessment,
    and resolution recommendations. Essential for maintaining data integrity and
    troubleshooting network configuration issues.
    
    Args:
        client: NetBoxClient instance (injected)
        vrf: Optional VRF name to scope the duplicate search
        tenant: Optional tenant name to scope the duplicate search
        include_severity_analysis: Include conflict severity assessment (default: True)
        include_resolution_recommendations: Include resolution suggestions (default: True)
        limit: Maximum number of IP addresses to analyze (default: 1000)
        
    Returns:
        Comprehensive duplicate IP analysis with resolution recommendations
        
    Examples:
        # Find all duplicate IPs
        netbox_find_duplicate_ips()
        
        # Find duplicates in specific VRF
        netbox_find_duplicate_ips(vrf="production-vrf")
        
        # Tenant-specific duplicate analysis
        netbox_find_duplicate_ips(
            tenant="customer-a",
            include_severity_analysis=True,
            include_resolution_recommendations=True
        )
        
        # Quick scan without detailed analysis
        netbox_find_duplicate_ips(
            include_severity_analysis=False,
            include_resolution_recommendations=False,
            limit=500
        )
    """
    try:
        logger.info("Starting duplicate IP address analysis...")
        
        # Step 1: Build filter parameters
        ip_filters = {}
        if vrf:
            logger.debug(f"Looking up VRF: {vrf}")
            vrfs = client.ipam.vrfs.filter(name=vrf)
            if vrfs:
                ip_filters["vrf_id"] = vrfs[0]["id"]
                logger.debug(f"Found VRF: {vrfs[0]['name']} (ID: {vrfs[0]['id']})")
            else:
                return {
                    "success": False,
                    "error": f"VRF '{vrf}' not found",
                    "error_type": "NotFoundError"
                }
        
        if tenant:
            logger.debug(f"Looking up tenant: {tenant}")
            tenants = client.tenancy.tenants.filter(name=tenant)
            if not tenants:
                tenants = client.tenancy.tenants.filter(slug=tenant)
            if tenants:
                ip_filters["tenant_id"] = tenants[0]["id"]
                logger.debug(f"Found tenant: {tenants[0]['name']} (ID: {tenants[0]['id']})")
            else:
                return {
                    "success": False,
                    "error": f"Tenant '{tenant}' not found",
                    "error_type": "NotFoundError"
                }
        
        # Step 2: Retrieve IP addresses with limit
        logger.debug(f"Retrieving IP addresses (limit: {limit})...")
        ip_addresses = list(client.ipam.ip_addresses.filter(**ip_filters)[:limit])
        
        if not ip_addresses:
            return {
                "success": True,
                "message": "No IP addresses found with the specified filters",
                "total_analyzed": 0,
                "duplicates_found": 0,
                "duplicate_groups": []
            }
        
        logger.info(f"Analyzing {len(ip_addresses)} IP addresses for duplicates...")
        
        # Step 3: Group IPs by address for duplicate detection
        ip_groups = {}
        for ip in ip_addresses:
            address = ip["address"]
            
            # Extract just the IP address (remove CIDR notation if present)
            clean_address = address.split('/')[0]
            
            if clean_address not in ip_groups:
                ip_groups[clean_address] = []
            
            ip_groups[clean_address].append(ip)
        
        # Step 4: Identify duplicate groups
        duplicate_groups = {}
        total_duplicates = 0
        
        for address, ips in ip_groups.items():
            if len(ips) > 1:
                duplicate_groups[address] = ips
                total_duplicates += len(ips)
        
        logger.info(f"Found {len(duplicate_groups)} duplicate IP groups containing {total_duplicates} IP addresses")
        
        if not duplicate_groups:
            return {
                "success": True,
                "message": "No duplicate IP addresses found",
                "total_analyzed": len(ip_addresses),
                "duplicates_found": 0,
                "duplicate_groups": [],
                "analysis_scope": {
                    "vrf": vrf,
                    "tenant": tenant,
                    "limit_applied": limit
                }
            }
        
        # Step 5: Analyze each duplicate group
        analyzed_groups = []
        
        for address, ips in duplicate_groups.items():
            group_analysis = {
                "ip_address": address,
                "duplicate_count": len(ips),
                "instances": [],
                "severity": "medium",  # Default severity
                "conflict_analysis": {},
                "resolution_recommendations": []
            }
            
            # Analyze each instance in the group
            assignment_types = set()
            devices = set()
            statuses = set()
            vrfs = set()
            tenants = set()
            
            for ip in ips:
                instance_info = {
                    "id": ip["id"],
                    "full_address": ip["address"],
                    "status": ip.get("status", {}).get("label", "Unknown"),
                    "description": ip.get("description", ""),
                    "created": ip.get("created", ""),
                    "assignment": None,
                    "vrf": None,
                    "tenant": None
                }
                
                # Capture assignment information
                if ip.get("assigned_object"):
                    assigned_obj = ip["assigned_object"]
                    assignment_type = ip.get("assigned_object_type", "Unknown")
                    assignment_types.add(assignment_type)
                    
                    instance_info["assignment"] = {
                        "type": assignment_type,
                        "object_id": ip.get("assigned_object_id"),
                        "name": assigned_obj.get("name", "Unknown") if assigned_obj else "Unknown"
                    }
                    
                    # Get device information if assigned to an interface
                    if assignment_type == "dcim.interface" and assigned_obj:
                        device_info = assigned_obj.get("device", {})
                        if device_info:
                            devices.add(device_info.get("name", "Unknown"))
                            instance_info["assignment"]["device"] = device_info.get("name", "Unknown")
                
                # Capture VRF information
                if ip.get("vrf"):
                    vrf_name = ip["vrf"].get("name", "Unknown")
                    vrfs.add(vrf_name)
                    instance_info["vrf"] = vrf_name
                
                # Capture tenant information
                if ip.get("tenant"):
                    tenant_name = ip["tenant"].get("name", "Unknown")
                    tenants.add(tenant_name)
                    instance_info["tenant"] = tenant_name
                
                # Capture status
                statuses.add(instance_info["status"])
                
                group_analysis["instances"].append(instance_info)
            
            # Step 6: Severity analysis (if requested)
            if include_severity_analysis:
                conflict_analysis = {
                    "assignment_type_conflicts": len(assignment_types) > 1,
                    "device_conflicts": len(devices) > 1,
                    "status_conflicts": len(statuses) > 1,
                    "vrf_conflicts": len(vrfs) > 1,
                    "tenant_conflicts": len(tenants) > 1,
                    "assignment_types": list(assignment_types),
                    "devices": list(devices),
                    "statuses": list(statuses),
                    "vrfs": list(vrfs),
                    "tenants": list(tenants)
                }
                
                # Determine severity based on conflicts
                severity_score = 0
                if conflict_analysis["device_conflicts"]:
                    severity_score += 3  # Device conflicts are high priority
                if conflict_analysis["vrf_conflicts"]:
                    severity_score += 2  # VRF conflicts are medium-high priority
                if conflict_analysis["tenant_conflicts"]:
                    severity_score += 2  # Tenant conflicts are medium-high priority
                if conflict_analysis["assignment_type_conflicts"]:
                    severity_score += 1  # Type conflicts are medium priority
                if conflict_analysis["status_conflicts"]:
                    severity_score += 1  # Status conflicts are lower priority
                
                if severity_score >= 5:
                    group_analysis["severity"] = "critical"
                elif severity_score >= 3:
                    group_analysis["severity"] = "high"
                elif severity_score >= 1:
                    group_analysis["severity"] = "medium"
                else:
                    group_analysis["severity"] = "low"
                
                group_analysis["conflict_analysis"] = conflict_analysis
            
            # Step 7: Resolution recommendations (if requested)
            if include_resolution_recommendations:
                recommendations = []
                
                if len(devices) > 1:
                    recommendations.append({
                        "type": "device_conflict",
                        "priority": "high",
                        "action": "Verify physical network connectivity - same IP on multiple devices indicates routing/switching misconfiguration",
                        "details": f"IP assigned to devices: {', '.join(devices)}"
                    })
                
                if len(vrfs) > 1:
                    recommendations.append({
                        "type": "vrf_conflict", 
                        "priority": "high",
                        "action": "Consolidate IP to single VRF or verify VRF isolation is working correctly",
                        "details": f"IP exists in VRFs: {', '.join(vrfs)}"
                    })
                
                if len(tenants) > 1:
                    recommendations.append({
                        "type": "tenant_conflict",
                        "priority": "medium",
                        "action": "Assign IP to correct tenant or verify tenant separation policies",
                        "details": f"IP assigned to tenants: {', '.join(tenants)}"
                    })
                
                if "active" in statuses and len(statuses) > 1:
                    recommendations.append({
                        "type": "status_conflict",
                        "priority": "medium", 
                        "action": "Standardize IP status - consider changing duplicates to 'deprecated' or 'reserved'",
                        "details": f"Mixed statuses found: {', '.join(statuses)}"
                    })
                
                if not recommendations:
                    recommendations.append({
                        "type": "general_cleanup",
                        "priority": "low",
                        "action": "Remove duplicate entries retaining the most recently created or most completely documented instance",
                        "details": "No specific conflicts detected, general cleanup recommended"
                    })
                
                group_analysis["resolution_recommendations"] = recommendations
            
            analyzed_groups.append(group_analysis)
        
        # Step 8: Sort by severity for priority handling
        if include_severity_analysis:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            analyzed_groups.sort(key=lambda x: severity_order.get(x["severity"], 4))
        
        # Step 9: Generate summary statistics
        summary_stats = {
            "total_analyzed": len(ip_addresses),
            "duplicates_found": total_duplicates,
            "duplicate_groups": len(duplicate_groups),
            "duplicate_rate_percent": round((total_duplicates / len(ip_addresses)) * 100, 2) if ip_addresses else 0
        }
        
        if include_severity_analysis:
            severity_counts = {}
            for group in analyzed_groups:
                severity = group["severity"]
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            summary_stats["severity_distribution"] = severity_counts
        
        return {
            "success": True,
            "summary": summary_stats,
            "duplicate_groups": analyzed_groups,
            "analysis_scope": {
                "vrf": vrf,
                "tenant": tenant,
                "limit_applied": limit,
                "included_severity_analysis": include_severity_analysis,
                "included_resolution_recommendations": include_resolution_recommendations
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to find duplicate IPs: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }