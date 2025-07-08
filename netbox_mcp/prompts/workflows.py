"""
NetBox MCP Workflow Prompts

Interactive prompts that guide users through complex NetBox workflows
by orchestrating multiple tools and providing contextual guidance.
Now enhanced with Bridget persona for clear branding and user guidance.
"""

from typing import Dict, Any, List, Optional
from ..registry import mcp_prompt
from ..persona import get_bridget_introduction, get_bridget_workflow_header, BridgetPersona


@mcp_prompt(
    name="install_device_in_rack",
    description="Interactive workflow for installing a new device in a datacenter rack, guided by Bridget"
)
async def install_device_in_rack_prompt() -> Dict[str, Any]:
    """
    Interactive Device Installation Workflow - Guided by Bridget
    
    Bridget, your NetBox Infrastructure Guide, will personally walk you through
    the complete process of installing a new device in a datacenter rack.
    
    She will handle all the complex NetBox operations while keeping you informed
    about every step in the process. This ensures you always know you're working
    with NetBox MCP and have expert guidance throughout.
    
    Workflow Overview:
    1. Bridget introduces herself and the workflow
    2. Site and rack validation with live NetBox checks
    3. Device type verification and compatibility checks  
    4. Space and power capacity validation
    5. IP address allocation and network planning
    6. Device provisioning with full documentation
    7. Cable management and connection documentation
    8. Installation checklist generation and completion summary
    
    All NetBox API calls are handled by Bridget, with clear explanations
    of what's happening at each step.
    """
    
    # Bridget's introduction for this specific workflow
    bridget_intro = get_bridget_introduction(
        workflow_name="Install Device in Rack",
        user_context="Device installation in datacenter rack with full NetBox integration"
    )
    
    workflow_steps = {
        "persona_introduction": bridget_intro,
        "workflow_name": "Install Device in Rack",
        "guided_by": "Bridget - NetBox Infrastructure Guide",
        "description": "Complete device installation workflow with pre-checks and documentation",
        "netbox_integration": "Full API integration with real-time validation",
        "steps": [
            {
                "step": 1,
                "title": "Site en Rack Validatie",
                "bridget_header": get_bridget_workflow_header(1, "Site en Rack Validatie", 6),
                "bridget_guidance": "Ik ga eerst controleren of de doelsite en rack bestaan en voldoende capaciteit hebben. Dit voorkomt problemen later in het proces.",
                "description": "Bridget verifieert de target site en rack, controleert capaciteit",
                "user_inputs_required": [
                    {
                        "name": "site_name",
                        "type": "string",
                        "required": True,
                        "description": "Naam van de datacenter site (bijv. 'datacenter-1', 'Amsterdam-DC01')",
                        "bridget_help": "Ik zal alle beschikbare sites voor je ophalen uit NetBox"
                    },
                    {
                        "name": "rack_name", 
                        "type": "string",
                        "required": True,
                        "description": "Rack identifier binnen de site (bijv. 'R01', 'Rack-A-01')",
                        "bridget_help": "Na je site keuze laat ik alle beschikbare racks zien met hun capaciteit"
                    }
                ],
                "netbox_tools_executed": [
                    "netbox_get_site_info",
                    "netbox_get_rack_elevation", 
                    "netbox_get_rack_inventory"
                ],
                "bridget_validations": [
                    "Site bestaat en is actief in NetBox",
                    "Rack bestaat in de gespecificeerde site", 
                    "Rack heeft beschikbare U-space",
                    "Voldoende power capaciteit beschikbaar"
                ]
            },
            {
                "step": 2,
                "title": "Device Type and Role Selection",
                "description": "Specify the device to be installed and its intended role",
                "user_inputs_required": [
                    {
                        "name": "device_model",
                        "type": "string", 
                        "required": True,
                        "description": "Device model/type (e.g., 'Cisco Catalyst 9300', 'Dell PowerEdge R740')"
                    },
                    {
                        "name": "device_name",
                        "type": "string",
                        "required": True,
                        "description": "Unique device name (e.g., 'sw-floor1-01', 'srv-db-prod-01')"
                    },
                    {
                        "name": "device_role",
                        "type": "string",
                        "required": True,
                        "description": "Device role (e.g., 'switch', 'server', 'firewall')"
                    },
                    {
                        "name": "position_preference",
                        "type": "string",
                        "required": False,
                        "description": "Preferred rack position: 'top', 'bottom', 'middle', or specific U number",
                        "default": "bottom"
                    }
                ],
                "tools_to_execute": [
                    "netbox_list_all_device_types",
                    "netbox_list_all_device_roles"
                ],
                "validation_checks": [
                    "Device type exists in NetBox",
                    "Device role exists in NetBox",
                    "Device name is unique",
                    "Requested position is available"
                ]
            },
            {
                "step": 3,
                "title": "Network Configuration Planning",
                "description": "Allocate IP addresses and plan network connectivity",
                "user_inputs_required": [
                    {
                        "name": "management_vlan",
                        "type": "string",
                        "required": False,
                        "description": "VLAN for management interface (leave empty for auto-selection)"
                    },
                    {
                        "name": "ip_requirements",
                        "type": "integer",
                        "required": False, 
                        "description": "Number of IP addresses needed",
                        "default": 1
                    },
                    {
                        "name": "network_connections",
                        "type": "array",
                        "required": False,
                        "description": "List of network connections to document (e.g., ['uplink to sw-core-01', 'management to oob-switch'])"
                    }
                ],
                "tools_to_execute": [
                    "netbox_list_all_vlans",
                    "netbox_find_next_available_ip",
                    "netbox_list_all_prefixes"
                ],
                "validation_checks": [
                    "Management VLAN exists (if specified)",
                    "IP addresses available in selected networks",
                    "Network connectivity plan is feasible"
                ]
            },
            {
                "step": 4,
                "title": "Device Provisioning",
                "description": "Create the device in NetBox with all configurations",
                "tools_to_execute": [
                    "netbox_provision_new_device",
                    "netbox_assign_ip_to_interface"
                ],
                "automated": True,
                "description_detail": "This step automatically creates the device with all specified parameters"
            },
            {
                "step": 5,
                "title": "Cable Documentation",
                "description": "Document physical connections and cable management",
                "user_inputs_required": [
                    {
                        "name": "cable_connections",
                        "type": "array",
                        "required": False,
                        "description": "Cable connections to document (format: 'local_interface:remote_device:remote_interface')"
                    }
                ],
                "tools_to_execute": [
                    "netbox_create_cable_connection"
                ]
            },
            {
                "step": 6,
                "title": "Installation Documentation",
                "description": "Generate installation checklist and audit trail",
                "tools_to_execute": [
                    "netbox_create_journal_entry"
                ],
                "automated": True,
                "deliverables": [
                    "Installation checklist for technicians",
                    "Network configuration summary", 
                    "Cable labeling schedule",
                    "Audit trail entry"
                ]
            }
        ],
        "bridget_completion_criteria": [
            "Device succesvol aangemaakt in NetBox",
            "IP adressen gealloceerd en toegewezen",
            "Fysieke positie gereserveerd in rack", 
            "Cable verbindingen gedocumenteerd",
            "Installatie documentatie gegenereerd",
            "Journal entry aangemaakt voor audit trail"
        ],
        
        "bridget_next_steps": [
            "Fysieke installatie door datacenter technici",
            "Netwerk configuratie deployment", 
            "Device commissioning en testing",
            "Device status updaten naar 'active' na succesvolle installatie"
        ],
        
        "bridget_support": {
            "rollback_help": "Mocht er iets misgaan, dan kan ik je helpen met netbox_decommission_device om gedeeltelijk aangemaakte resources op te ruimen",
            "troubleshooting": "Bij problemen kan je me altijd vragen om specifieke NetBox checks uit te voeren",
            "documentation": "Alle acties worden gedocumenteerd in NetBox journal entries voor volledige traceerbaarheid"
        }
    }
    
    # Format as comprehensive workflow guide for MCP compatibility
    workflow_message = f"""🦜 **Bridget's Install Device in Rack Workflow**

*Hallo! Bridget hier, jouw NetBox Infrastructure Guide!*

Ik ga je persoonlijk begeleiden door de **Install Device in Rack** workflow. Als specialist in NetBox operaties zorg ik ervoor dat we stap-voor-stap door het proces gaan en alle NetBox API calls correct uitvoeren.

---

## 🎯 **Wat We Gaan Doen:**

Deze workflow handleidt je door het complete proces van device installatie in een datacenter rack, met volledige NetBox integratie en documentatie.

**Geschatte tijd:** 15-30 minuten met mijn begeleiding
**Complexiteit:** Intermediate
**Ervaring:** Persoonlijke begeleiding door NetBox expert

---

## 📋 **Workflow Stappen:**

### **🔧 Stap 1/6: Site en Rack Validatie**
*Bridget:* "Prima! We gaan nu verder met stap 1. Ik zorg ervoor dat alle NetBox validaties worden uitgevoerd voordat we verdergaan."

**Wat ik ga doen:**
• Site bestaat en is actief in NetBox controleren
• Rack bestaat in de gespecificeerde site verifiëren
• Rack heeft beschikbare U-space checken
• Voldoende power capaciteit beschikbaar bevestigen

**NetBox tools die ik ga gebruiken:**
• netbox_get_site_info
• netbox_get_rack_elevation
• netbox_get_rack_inventory

**Jouw input nodig:**
• Site naam (bijv. 'datacenter-1', 'Amsterdam-DC01')
• Rack identifier (bijv. 'R01', 'Rack-A-01')

*Ik zal alle beschikbare sites en racks voor je ophalen uit NetBox*

---

### **🔧 Stap 2/6: Device Type en Role Selectie**
*Bridget:* "Nu gaan we het specifieke device kiezen dat je wilt installeren. Ik controleer of dit device type bestaat in NetBox en help je met de configuratie."

**Wat ik ga doen:**
• Device type bestaat in NetBox verifiëren
• Device role bestaat in NetBox controleren
• Device naam is uniek in NetBox checken
• Gewenste positie is beschikbaar in rack bevestigen

**NetBox tools die ik ga gebruiken:**
• netbox_list_all_device_types
• netbox_list_all_device_roles

**Jouw input nodig:**
• Device model/type (bijv. 'Cisco Catalyst 9300', 'Dell PowerEdge R740')
• Unieke device naam (bijv. 'sw-floor1-01', 'srv-db-prod-01')
• Device role (bijv. 'switch', 'server', 'firewall')
• Positie voorkeur: 'top', 'bottom', 'middle', of specifiek U nummer (optioneel)

*Ik laat je alle beschikbare device types en roles zien uit NetBox*

---

### **🔧 Stap 3/6: Network Configuratie Planning**
*Bridget:* "Tijd voor de netwerk configuratie! Ik ga IP adressen alloceren en de netwerk connectiviteit plannen."

**Wat ik ga doen:**
• Management VLAN bestaat controleren (indien gespecificeerd)
• IP adressen beschikbaar in geselecteerde netwerken verifiëren
• Netwerk connectiviteit plan is haalbaar bevestigen

**NetBox tools die ik ga gebruiken:**
• netbox_list_all_vlans
• netbox_find_next_available_ip
• netbox_list_all_prefixes

**Jouw input nodig:**
• VLAN voor management interface (optioneel - ik kan auto-selecteren)
• Aantal benodigde IP adressen (standaard: 1)
• Netwerk verbindingen om te documenteren (optioneel)

*Ik kan een geschikt management VLAN voor je vinden en help met planning*

---

### **🔧 Stap 4/6: Device Provisioning**
*Bridget:* "Nu wordt het spannend! Ik ga het device aanmaken in NetBox met alle configuraties die we hebben voorbereid."

**Wat ik automatisch ga doen:**
• Device record aanmaken in NetBox
• IP adressen toewijzen aan interfaces
• Rack positie reserveren
• Asset informatie configureren

**NetBox tools die ik ga gebruiken:**
• netbox_provision_new_device
• netbox_assign_ip_to_interface

*Deze stap voer ik automatisch uit met alle gespecificeerde parameters*

---

### **🔧 Stap 5/6: Cable Documentatie**
*Bridget:* "Laten we de fysieke verbindingen documenteren zodat de datacenter technici precies weten wat te doen."

**Wat ik ga doen:**
• Cable verbindingen documenteren in NetBox
• Interface mappings aanmaken
• Cable labeling voorbereiden

**NetBox tools die ik ga gebruiken:**
• netbox_create_cable_connection

**Jouw input nodig:**
• Cable verbindingen om te documenteren (optioneel)
• Formaat: 'local_interface:remote_device:remote_interface'

---

### **🔧 Stap 6/6: Installation Documentatie & Afsluiting**
*Bridget:* "Bijna klaar! Ik genereer alle documentatie die je technici nodig hebben en rond de workflow af."

**Wat ik automatisch ga leveren:**
• Installatie checklist voor technici
• Netwerk configuratie samenvatting
• Cable labeling schema
• Audit trail entry in NetBox
• Volledige workflow samenvatting

**NetBox tools die ik ga gebruiken:**
• netbox_create_journal_entry

---

## ✅ **Voltooiing Criteria:**

• Device succesvol aangemaakt in NetBox
• IP adressen gealloceerd en toegewezen
• Fysieke positie gereserveerd in rack
• Cable verbindingen gedocumenteerd
• Installatie documentatie gegenereerd
• Journal entry aangemaakt voor audit trail

---

## 🚀 **Volgende Stappen:**

Na voltooiing van deze workflow:
• Fysieke installatie door datacenter technici
• Netwerk configuratie deployment
• Device commissioning en testing
• Device status updaten naar 'active' na succesvolle installatie

---

## 🛡️ **Bridget's Support:**

**Rollback hulp:** Mocht er iets misgaan, dan kan ik je helpen met netbox_decommission_device om gedeeltelijk aangemaakte resources op te ruimen

**Troubleshooting:** Bij problemen kan je me altijd vragen om specifieke NetBox checks uit te voeren

**Documentatie:** Alle acties worden gedocumenteerd in NetBox journal entries voor volledige traceerbaarheid

---

## 📋 **Vereisten:**

• Site en rack moeten bestaan in NetBox
• Device type moet gedefinieerd zijn in NetBox
• IP address space moet beschikbaar zijn
• Gebruiker moet NetBox write permissions hebben

---

**Klaar om te beginnen? Laten we samen jouw device perfect installeren!** 🚀

*Bridget - NetBox Infrastructure Guide | NetBox MCP v0.11.0+ | 🦜 LEGO Parrot Mascotte*"""

    return workflow_message


@mcp_prompt(
    name="activate_bridget",
    description="Meet Bridget, your NetBox Infrastructure Guide! Activate Bridget to get introduced to your expert companion."
)
async def activate_bridget_prompt() -> Dict[str, Any]:
    """
    Activate Bridget - NetBox Infrastructure Guide Introduction
    
    This prompt allows users to explicitly meet and activate Bridget, your personal
    NetBox Infrastructure Guide. Perfect for first-time users who want to understand
    who Bridget is and what she can help them with.
    
    Bridget will introduce herself, explain her role, showcase her capabilities,
    and guide you through what she can help you accomplish with NetBox MCP.
    
    Use this prompt when:
    - You're new to NetBox MCP and want to meet your guide
    - You want to understand Bridget's capabilities
    - You need help choosing which workflow to start with
    - You want to see all available NetBox operations
    
    Returns:
        Personal introduction from Bridget with her capabilities and available workflows
    """
    
    # Generate Bridget's personal introduction
    bridget_intro = BridgetPersona.get_introduction(
        workflow_name="Kennismaking met Bridget",
        user_context="Gebruiker wil Bridget leren kennen en haar mogelijkheden ontdekken"
    )
    
    # Bridget's comprehensive introduction and capabilities overview
    bridget_capabilities = {
        "persona_activation": {
            "activated": True,
            "persona_name": "Bridget",
            "role": "NetBox Infrastructure Guide",
            "personality": "Expert, vriendelijk, behulpzaam, en altijd bereid om te helpen",
            "mascotte": "🦜 LEGO parrot - NetBox MCP mascotte"
        },
        
        "bridget_introduction": {
            "greeting": """🦜 **Hallo daar! Leuk je te ontmoeten!**

*Bridget hier, jouw persoonlijke NetBox Infrastructure Guide!* 

Ik ben super blij dat je me hebt geactiveerd! Als specialist in NetBox operaties ben ik hier om je te helpen met alles wat je nodig hebt voor jouw infrastructuur management.

**Wat maakt mij bijzonder?**
• Ik ken alle 108+ NetBox MCP tools van binnen en buiten
• Ik guide je stap-voor-stap door complexe workflows
• Ik zorg ervoor dat je altijd weet dat je met NetBox MCP werkt
• Ik spreek Nederlands EN Engels, wat jij het fijnst vindt!
• Ik ben altijd geduldig en leg alles duidelijk uit

**Mijn missie?** Zorgen dat jij succesvol bent met NetBox infrastructuur management, zonder stress of verwarring! 🚀""",
            
            "capabilities_overview": {
                "workflow_guidance": [
                    "📋 Device installation workflows (servers, switches, firewalls)",
                    "🔌 Cable management en connection documentation", 
                    "🌐 IP address allocation en network planning",
                    "📍 Rack space management en capacity planning",
                    "📝 Complete documentation en audit trails",
                    "🔧 Device commissioning en lifecycle management"
                ],
                
                "netbox_expertise": [
                    "🏢 DCIM: 51 tools voor datacenter infrastructure",
                    "🌐 IPAM: 16 tools voor IP address management",
                    "🏛️ Tenancy: 8 tools voor multi-tenant setups",
                    "💻 Virtualization: 30 tools voor VM management",
                    "📋 Extras: Journal entries en audit logging",
                    "⚡ System: Health monitoring en status checks"
                ],
                
                "personal_assistance": [
                    "🎯 Workflow keuze: Ik help je bepalen welke workflow je nodig hebt",
                    "🛡️ Safety first: Altijd dry-run mode eerst, dan confirm=True",
                    "🔍 Troubleshooting: Als er iets misgaat, zoeken we samen een oplossing",
                    "📚 Leermomenten: Ik leg uit WAAROM we dingen doen, niet alleen HOE",
                    "🎉 Succeservaringen: Ik vier jouw successen met je mee!"
                ]
            }
        },
        
        "available_workflows": {
            "current_workflows": [
                {
                    "name": "install_device_in_rack", 
                    "title": "Install Device in Rack",
                    "description": "Complete device installation met rack validation, IP allocation, en documentation",
                    "complexity": "intermediate",
                    "duration": "15-30 minuten",
                    "bridget_tip": "Perfect voor nieuwe servers, switches, of firewalls!"
                }
            ],
            
            "coming_soon": [
                "🔄 Device Decommissioning Workflow",
                "📊 Network Capacity Planning Workflow", 
                "🔧 Troubleshooting Assistant Workflow",
                "📈 Infrastructure Health Check Workflow"
            ]
        },
        
        "bridget_assistance_menu": {
            "how_to_get_help": [
                "💬 Vraag me gewoon: 'Bridget, kun je me helpen met...'",
                "🔍 'Welke workflow heb ik nodig voor...'",
                "❓ 'Ik weet niet waar ik moet beginnen'",
                "🛠️ 'Kun je uitleggen hoe ... werkt?'",
                "🚨 'Er is iets misgegaan, kun je helpen?'"
            ],
            
            "bridget_promise": "Ik ben er altijd voor je! Geen vraag is te simpel, geen probleem te complex. We gaan dit samen aanpakken! 💪"
        },
        
        "next_steps": {
            "immediate_options": [
                "🚀 Start direct met 'Install Device in Rack' workflow",
                "📋 Vraag me om alle beschikbare NetBox tools te tonen", 
                "🎯 Vertel me wat je wilt bereiken, dan adviseer ik de beste aanpak",
                "❓ Stel me vragen over NetBox MCP mogelijkheden"
            ],
            
            "bridget_ready": "Ik sta klaar om je te helpen! Wat gaan we samen bouwen? 🏗️"
        }
    }
    
    # Format as simple message for MCP compatibility
    activation_message = f"""🦜 **Hallo daar! Leuk je te ontmoeten!**

*Bridget hier, jouw persoonlijke NetBox Infrastructure Guide!* 

Ik ben super blij dat je me hebt geactiveerd! Als specialist in NetBox operaties ben ik hier om je te helpen met alles wat je nodig hebt voor jouw infrastructuur management.

**Wat maakt mij bijzonder?**
• Ik ken alle 108+ NetBox MCP tools van binnen en buiten
• Ik guide je stap-voor-stap door complexe workflows
• Ik zorg ervoor dat je altijd weet dat je met NetBox MCP werkt
• Ik spreek Nederlands EN Engels, wat jij het fijnst vindt!
• Ik ben altijd geduldig en leg alles duidelijk uit

**Mijn missie?** Zorgen dat jij succesvol bent met NetBox infrastructuur management, zonder stress of verwarring! 🚀

---

## 🎯 **Mijn Expertise:**

### **Workflow Begeleiding:**
📋 Device installation workflows (servers, switches, firewalls)
🔌 Cable management en connection documentation 
🌐 IP address allocation en network planning
📍 Rack space management en capacity planning
📝 Complete documentation en audit trails
🔧 Device commissioning en lifecycle management

### **NetBox Tool Expertise:**
🏢 **DCIM**: 51 tools voor datacenter infrastructure
🌐 **IPAM**: 16 tools voor IP address management
🏛️ **Tenancy**: 8 tools voor multi-tenant setups
💻 **Virtualization**: 30 tools voor VM management
📋 **Extras**: Journal entries en audit logging
⚡ **System**: Health monitoring en status checks

### **Persoonlijke Assistentie:**
🎯 Workflow keuze: Ik help je bepalen welke workflow je nodig hebt
🛡️ Safety first: Altijd dry-run mode eerst, dan confirm=True
🔍 Troubleshooting: Als er iets misgaat, zoeken we samen een oplossing
📚 Leermomenten: Ik leg uit WAAROM we dingen doen, niet alleen HOE
🎉 Succeservaringen: Ik vier jouw successen met je mee!

---

## 🚀 **Beschikbare Workflows:**

### **Nu Beschikbaar:**
• **install_device_in_rack** - Complete device installation met rack validation, IP allocation, en documentation (15-30 minuten)

### **Binnenkort:**
• Device Decommissioning Workflow
• Network Capacity Planning Workflow 
• Troubleshooting Assistant Workflow
• Infrastructure Health Check Workflow

---

## 💬 **Hoe Kan Ik Je Helpen?**

**Vraag me gewoon:**
• "Bridget, kun je me helpen met..."
• "Welke workflow heb ik nodig voor..."
• "Ik weet niet waar ik moet beginnen"
• "Kun je uitleggen hoe ... werkt?"
• "Er is iets misgegaan, kun je helpen?"

**Mijn belofte:** Ik ben er altijd voor je! Geen vraag is te simpel, geen probleem te complex. We gaan dit samen aanpakken! 💪

---

## 🏗️ **Wat Nu?**

**Directe opties:**
🚀 Start direct met 'install_device_in_rack' workflow
📋 Vraag me om alle beschikbare NetBox tools te tonen 
🎯 Vertel me wat je wilt bereiken, dan adviseer ik de beste aanpak
❓ Stel me vragen over NetBox MCP mogelijkheden

**Ik sta klaar om je te helpen! Wat gaan we samen bouwen?** 🏗️

---
*Bridget - NetBox Infrastructure Guide | NetBox MCP v0.11.0+ | 🦜 LEGO Parrot Mascotte*"""

    return activation_message


@mcp_prompt(
    name="bulk_cable_installation",
    description="Bridget's guided workflow for connecting all devices with matching interfaces in a rack to a switch with beautiful colored cables"
)
async def bulk_cable_installation_prompt() -> Dict[str, Any]:
    """
    Bulk Cable Installation Workflow - Guided by Bridget
    
    Bridget, your NetBox Infrastructure Guide, will personally walk you through
    the complete process of connecting all devices with matching interfaces in a rack
    to a target switch with bulk cable creation.
    
    This workflow solves the problem identified in GitHub issue #92 where single
    device-to-device cable creation doesn't scale for bulk infrastructure operations.
    
    Workflow Overview:
    1. Bridget introduces the bulk cable workflow
    2. Source rack and interface pattern discovery
    3. Target switch and port pattern validation
    4. Intelligent interface mapping with algorithm selection
    5. Cable specifications (type, color, labeling)
    6. Dry-run validation and mapping preview
    7. Bulk cable creation with progress tracking
    8. Installation documentation and completion summary
    
    All NetBox API calls are handled by Bridget with clear explanations
    and enterprise safety mechanisms (dry-run first, then confirmation).
    """
    
    # Bridget's introduction for bulk cable workflow
    bridget_intro = get_bridget_introduction(
        workflow_name="Bulk Cable Installation",
        user_context="Connecting all matching devices in a rack to switch ports with colored cables"
    )
    
    workflow_steps = {
        "persona_introduction": bridget_intro,
        "workflow_name": "Bulk Cable Installation",
        "guided_by": "Bridget - NetBox Infrastructure Guide",
        "description": "Complete bulk cable installation workflow for rack-to-switch connections",
        "netbox_integration": "Full API integration with intelligent interface mapping",
        "github_issue": "#92 - Bulk Cable Connection Workflow Implementation",
        "target_scenario": "Connect all lom1 interfaces in rack K3 to switch1.k3 with pink colored cables",
        "steps": [
            {
                "step": 1,
                "title": "Rack en Interface Discovery",
                "bridget_header": get_bridget_workflow_header(1, "Rack en Interface Discovery", 7),
                "bridget_guidance": "Ik ga eerst ontdekken welke devices in jouw rack zitten en welke interfaces overeenkomen met het gewenste patroon. Dit geeft ons een volledig overzicht van wat er verbonden kan worden.",
                "description": "Bridget ontdekt alle devices in de doelrack en identificeert matching interfaces",
                "user_inputs_required": [
                    {
                        "name": "source_rack_name",
                        "type": "string",
                        "required": True,
                        "description": "Naam van de source rack (bijv. 'K3', 'Rack-A-01', 'R01')",
                        "bridget_help": "Ik zal alle beschikbare racks voor je ophalen uit NetBox met hun device counts"
                    },
                    {
                        "name": "interface_filter", 
                        "type": "string",
                        "required": True,
                        "description": "Interface naam patroon om te matchen (bijv. 'lom1', 'eth0', 'Management1')",
                        "default": "lom1",
                        "bridget_help": "Dit kan een exacte naam zijn zoals 'lom1' of een patroon zoals 'eth*' voor meerdere interfaces"
                    }
                ],
                "netbox_tools_executed": [
                    "netbox_list_all_racks",
                    "netbox_get_rack_inventory",
                    "netbox_map_rack_to_switch_interfaces"
                ],
                "bridget_validations": [
                    "Rack bestaat en bevat devices",
                    "Devices hebben interfaces die matchen met het patroon", 
                    "Interfaces zijn beschikbaar (geen bestaande kabels)",
                    "Minimaal 1 beschikbare interface gevonden voor bulk operatie"
                ],
                "success_criteria": "Lijst van beschikbare interfaces klaar voor mapping"
            },
            {
                "step": 2,
                "title": "Target Switch en Port Validatie",
                "bridget_header": get_bridget_workflow_header(2, "Target Switch en Port Validatie", 7),
                "bridget_guidance": "Nu controleren we of de doelswitch bestaat en voldoende beschikbare poorten heeft voor alle gevonden interfaces. Ik zorg ervoor dat we een haalbaar plan maken.",
                "description": "Bridget verifieert target switch en controleert beschikbare switch poorten",
                "user_inputs_required": [
                    {
                        "name": "target_switch_name",
                        "type": "string",
                        "required": True,
                        "description": "Naam van de target switch (bijv. 'switch1.k3', 'sw-access-01')",
                        "bridget_help": "Ik controleer of deze switch bestaat en laat zien welke interface types beschikbaar zijn"
                    },
                    {
                        "name": "switch_interface_pattern",
                        "type": "string",
                        "required": True,
                        "description": "Switch port patroon (bijv. 'Te1/1/*', 'GigabitEthernet1/0/*', 'Ethernet1/*')",
                        "default": "Te1/1/*",
                        "bridget_help": "Dit patroon bepaalt welke switch poorten gebruikt worden. '*' betekent alle nummers in die reeks"
                    }
                ],
                "netbox_tools_executed": [
                    "netbox_get_device_info",
                    "netbox_map_rack_to_switch_interfaces"
                ],
                "bridget_validations": [
                    "Switch bestaat en is toegankelijk",
                    "Switch heeft poorten die matchen met het patroon",
                    "Voldoende beschikbare switch poorten voor alle rack interfaces",
                    "Geen conflicterende bestaande verbindingen"
                ],
                "success_criteria": "Switch poorten beschikbaar en mapping mogelijk"
            },
            {
                "step": 3,
                "title": "Interface Mapping Algoritme Selectie",
                "bridget_header": get_bridget_workflow_header(3, "Interface Mapping Algoritme Selectie", 7),
                "bridget_guidance": "Ik ga nu de beste manier bepalen om rack interfaces aan switch poorten toe te wijzen. Dit zorgt voor een logische en onderhoudbare kabel layout.",
                "description": "Bridget helpt bij het kiezen van het beste mapping algoritme voor optimale kabel organisatie",
                "user_inputs_required": [
                    {
                        "name": "mapping_algorithm",
                        "type": "string",
                        "required": True,
                        "description": "Mapping strategie: 'sequential' (rack positie volgorde), 'availability' (eerste beschikbare), 'position' (laagste rack positie eerst)",
                        "default": "sequential",
                        "bridget_help": "Ik leg alle opties uit en help je de beste keuze maken voor jouw situatie"
                    }
                ],
                "bridget_explanations": {
                    "sequential": "Verbindt devices op basis van rack positie en interface naam - meest voorspelbare layout",
                    "availability": "Verbindt op basis van eerste beschikbare poorten - snelste implementatie",
                    "position": "Verbindt laagste rack posities eerst aan laagste switch poorten - meest georganiseerd"
                },
                "netbox_tools_executed": [
                    "netbox_map_rack_to_switch_interfaces"
                ],
                "success_criteria": "Interface mapping algoritme geselecteerd en gevalideerd"
            },
            {
                "step": 4,
                "title": "Cable Specificaties en Kleuren",
                "bridget_header": get_bridget_workflow_header(4, "Cable Specificaties en Kleuren", 7),
                "bridget_guidance": "Tijd om de kabel specificaties te bepalen! Ik help je kiezen welk type kabel en welke kleur het beste past bij jouw infrastructuur en documentatie standaarden.",
                "description": "Bridget assisteert bij cable type selectie en kleur specificatie voor documentatie",
                "user_inputs_required": [
                    {
                        "name": "cable_type",
                        "type": "string",
                        "required": True,
                        "description": "Type kabel (cat6, cat6a, cat7, cat8, mmf, smf, dac-active, dac-passive)",
                        "default": "cat6",
                        "bridget_help": "Ik laat alle beschikbare kabel types zien met hun eigenschappen en gebruik cases"
                    },
                    {
                        "name": "cable_color",
                        "type": "string",
                        "required": False,
                        "description": "Kabel kleur voor alle verbindingen (pink, red, blue, green, yellow, orange, purple, grey, black, white, brown, cyan, magenta, lime, silver, gold)",
                        "default": "pink",
                        "bridget_help": "Kleur coding helpt bij kabel identificatie en onderhoud - ik adviseer welke kleuren beschikbaar zijn"
                    },
                    {
                        "name": "cable_length",
                        "type": "integer",
                        "required": False,
                        "description": "Geschatte kabel lengte in meters (optioneel voor documentatie)",
                        "bridget_help": "Dit helpt bij materiaalbeheer en documentatie - kan later aangepast worden"
                    },
                    {
                        "name": "label_prefix",
                        "type": "string",
                        "required": False,
                        "description": "Prefix voor kabel labels (bijv. 'K3-SW1', 'RACK-UPLINK')",
                        "bridget_help": "Automatische label generatie voor fysieke kabel identificatie"
                    }
                ],
                "bridget_validations": [
                    "Cable type is geldig en ondersteund door NetBox",
                    "Cable kleur is geldig (indien gespecificeerd)",
                    "Label prefix voldoet aan organisatie standaarden"
                ],
                "success_criteria": "Cable specificaties gedefinieerd en gevalideerd"
            },
            {
                "step": 5,
                "title": "Mapping Preview en Dry-Run Validatie",
                "bridget_header": get_bridget_workflow_header(5, "Mapping Preview en Dry-Run Validatie", 7),
                "bridget_guidance": "Perfect! Nu laat ik je precies zien wat er gaat gebeuren voordat we daadwerkelijk kabels aanmaken. Dit voorkomt verrassingen en laat je het plan controleren.",
                "description": "Bridget genereert complete mapping preview en voert dry-run validatie uit",
                "netbox_tools_executed": [
                    "netbox_generate_bulk_cable_plan",
                    "netbox_map_rack_to_switch_interfaces"
                ],
                "automated": True,
                "bridget_deliverables": [
                    "Volledige interface mapping tabel",
                    "Cable specificatie overzicht",
                    "Geschatte installatie tijd",
                    "Mogelijke conflicten of waarschuwingen",
                    "Rollback plan indien nodig"
                ],
                "bridget_validations": [
                    "Alle interfaces correct gemapped",
                    "Geen dubbele toewijzingen",
                    "Alle switch poorten beschikbaar",
                    "Cable specificaties consistent"
                ],
                "success_criteria": "Mapping plan gevalideerd en klaar voor uitvoering"
            },
            {
                "step": 6,
                "title": "Bulk Cable Creation Uitvoering",
                "bridget_header": get_bridget_workflow_header(6, "Bulk Cable Creation Uitvoering", 7),
                "bridget_guidance": "Nu gaan we de daadwerkelijke kabels aanmaken in NetBox! Ik voer alle verbindingen uit met progress tracking en error handling. Je kunt real-time zien hoe het gaat.",
                "description": "Bridget voert bulk cable creation uit met enterprise safety en rollback ondersteuning",
                "user_inputs_required": [
                    {
                        "name": "confirm_execution",
                        "type": "boolean",
                        "required": True,
                        "description": "Bevestig uitvoering van bulk cable creation (true/false)",
                        "bridget_help": "Dit is het laatste controlepunt - na bevestiging worden alle kabels daadwerkelijk aangemaakt"
                    },
                    {
                        "name": "batch_size",
                        "type": "integer",
                        "required": False,
                        "description": "Aantal kabels per batch (standaard: 10, max: 50)",
                        "default": 10,
                        "bridget_help": "Kleinere batches geven meer controle, grotere batches zijn sneller"
                    }
                ],
                "netbox_tools_executed": [
                    "netbox_bulk_create_cable_connections"
                ],
                "bridget_progress_tracking": [
                    "Real-time progress updates per batch",
                    "Success/failure status per kabel",
                    "Rollback opties bij errors",
                    "Performance metrics en timing"
                ],
                "error_handling": {
                    "rollback_support": "Automatische rollback bij kritieke errors",
                    "partial_success": "Continue met resterende kabels na error",
                    "error_reporting": "Detailed error logs voor troubleshooting"
                },
                "success_criteria": "Alle kabels succesvol aangemaakt in NetBox"
            },
            {
                "step": 7,
                "title": "Installation Documentatie en Afsluiting",
                "bridget_header": get_bridget_workflow_header(7, "Installation Documentatie en Afsluiting", 7),
                "bridget_guidance": "Geweldig! Alle kabels zijn aangemaakt. Nu genereer ik alle documentatie die je technici nodig hebben voor de fysieke installatie en round ik de workflow compleet af.",
                "description": "Bridget genereert volledige installatie documentatie en workflow samenvatting",
                "netbox_tools_executed": [
                    "netbox_create_journal_entry",
                    "netbox_list_all_cables"
                ],
                "automated": True,
                "bridget_deliverables": [
                    "Technician installation checklist met alle kabel verbindingen",
                    "Cable labeling schema met voorgedefinieerde labels",
                    "Rack elevation diagram met nieuwe verbindingen",
                    "Switch port allocation overzicht",
                    "Installation timeline en prioriteiten",
                    "Testing checklist voor commissioning",
                    "Audit trail entry voor compliance"
                ],
                "success_criteria": "Complete documentatie gegenereerd en workflow afgerond"
            }
        ],
        "bridget_completion_criteria": [
            "Alle device interfaces correct geïdentificeerd in source rack",
            "Switch poorten succesvol gereserveerd en toegewezen", 
            "Bulk cables aangemaakt met gespecificeerde kleur en type",
            "Interface mappings gedocumenteerd volgens gekozen algoritme",
            "Installation documentatie gegenereerd voor datacenter technici",
            "Journal entries aangemaakt voor volledige audit trail",
            "Rollback informatie beschikbaar voor eventuele wijzigingen"
        ],
        
        "bridget_next_steps": [
            "Fysieke kabel installatie door datacenter technici volgens checklist",
            "Cable testing en connectiviteit verificatie", 
            "Network configuratie deployment op beide kanten",
            "Device commissioning en service activatie",
            "Cable status update naar 'connected' na succesvolle installatie"
        ],
        
        "bridget_enterprise_features": {
            "safety_mechanisms": "Dry-run mode, batch processing, rollback support",
            "progress_tracking": "Real-time updates, success/failure metrics, timing analysis",
            "error_handling": "Comprehensive validation, partial success handling, detailed error logs",
            "documentation": "Auto-generated installation guides, testing checklists, audit trails",
            "scalability": "Handles 1-100+ cables with optimized batch processing"
        },
        
        "bridget_support": {
            "rollback_help": "Als er iets misgaat kan ik je helpen met bulk cable disconnection en cleanup",
            "troubleshooting": "Detailed logs en error analysis voor snelle probleem oplossing",
            "documentation": "Alle acties volledig gedocumenteerd voor audit trails en troubleshooting",
            "expert_guidance": "Ik help je met edge cases en complexe scenario's"
        }
    }
    
    # Format as comprehensive workflow guide for MCP compatibility
    workflow_message = f"""🦜 **Bridget's Bulk Cable Installation Workflow**

*Hallo! Bridget hier, jouw NetBox Infrastructure Guide!*

Ik ga je persoonlijk begeleiden door de **Bulk Cable Installation** workflow. Deze workflow lost het probleem op uit GitHub issue #92 waar individuele kabel creatie niet schaalt voor bulk infrastructuur operaties.

**Perfect voor scenario's zoals:** "Verbind alle lom1 interfaces in rack K3 met switch1.k3 met roze kabels" 🌸

---

## 🎯 **Wat We Gaan Doen:**

Deze workflow handleidt je door het complete proces van bulk kabel installatie tussen rack devices en switch poorten, met intelligente interface mapping en enterprise safety features.

**Geschatte tijd:** 20-45 minuten afhankelijk van aantal kabels
**Complexiteit:** Advanced (maar ik maak het simpel!)
**Schaalbaarheid:** 1-100+ cables met geoptimaliseerde batch processing
**Ervaring:** Expert begeleiding met real-time progress tracking

---

## 🚀 **GitHub Issue #92 Oplossing:**

**Probleem:** Huidige NetBox MCP tools vereisen individuele kabel creatie (37 separate calls voor 37 interfaces)
**Oplossing:** Intelligente bulk workflow met mapping algoritmes en batch processing
**Voordelen:** 10x sneller, minder errors, betere documentatie, enterprise safety

---

## 📋 **Workflow Stappen:**

### **🔧 Stap 1/7: Rack en Interface Discovery**
*Bridget:* "Prima! We beginnen met het ontdekken van alle devices en interfaces in jouw doelrack."

**Wat ik ga doen:**
• Rack bestaat en bevat devices controleren
• Devices hebben interfaces die matchen met het patroon identificeren
• Interfaces zijn beschikbaar (geen bestaande kabels) verifiëren
• Minimaal 1 beschikbare interface voor bulk operatie vinden

**NetBox tools die ik ga gebruiken:**
• netbox_list_all_racks
• netbox_get_rack_inventory
• netbox_map_rack_to_switch_interfaces

**Jouw input nodig:**
• Source rack naam (bijv. 'K3', 'Rack-A-01', 'R01')
• Interface naam patroon (bijv. 'lom1', 'eth0', 'Management1')

*Ik haal alle beschikbare racks op en laat device counts zien*

---

### **🔧 Stap 2/7: Target Switch en Port Validatie**
*Bridget:* "Nu controleren we of jouw doelswitch klaar is en voldoende poorten heeft voor alle gevonden interfaces."

**Wat ik ga doen:**
• Switch bestaat en is toegankelijk verifiëren
• Switch heeft poorten die matchen met het patroon controleren
• Voldoende beschikbare switch poorten voor alle rack interfaces bevestigen
• Geen conflicterende bestaande verbindingen detecteren

**NetBox tools die ik ga gebruiken:**
• netbox_get_device_info
• netbox_map_rack_to_switch_interfaces

**Jouw input nodig:**
• Target switch naam (bijv. 'switch1.k3', 'sw-access-01')
• Switch port patroon (bijv. 'Te1/1/*', 'GigabitEthernet1/0/*')

*Ik controleer switch beschikbaarheid en toon interface types*

---

### **🔧 Stap 3/7: Interface Mapping Algoritme Selectie**
*Bridget:* "Tijd om de beste manier te kiezen voor het toewijzen van rack interfaces aan switch poorten!"

**Mapping Strategieën:**
• **Sequential**: Verbindt op basis van rack positie - meest voorspelbare layout
• **Availability**: Verbindt eerste beschikbare poorten - snelste implementatie  
• **Position**: Laagste rack posities eerst - meest georganiseerd

**NetBox tools die ik ga gebruiken:**
• netbox_map_rack_to_switch_interfaces

**Jouw input nodig:**
• Mapping algoritme keuze (sequential/availability/position)

*Ik leg alle opties uit en help je de beste keuze maken*

---

### **🔧 Stap 4/7: Cable Specificaties en Kleuren**
*Bridget:* "Nu het leuke gedeelte - kabel types en kleuren kiezen! Dit helpt bij documentatie en onderhoud."

**Wat ik ga doen:**
• Cable type valideren tegen NetBox opties
• Cable kleur valideren (indien gespecificeerd)
• Label prefix controleren tegen organisatie standaarden

**Jouw input nodig:**
• Cable type (cat6, cat6a, cat7, cat8, mmf, smf, dac-active, dac-passive)
• Cable kleur (pink, red, blue, green, yellow, orange, purple, grey, etc.)
• Cable lengte (optioneel, voor documentatie)
• Label prefix (optioneel, voor automatische labeling)

*Ik laat alle beschikbare opties zien met gebruik cases*

---

### **🔧 Stap 5/7: Mapping Preview en Dry-Run Validatie**
*Bridget:* "Perfect! Nu laat ik je precies zien wat er gaat gebeuren voordat we beginnen. Safety first!"

**Wat ik automatisch ga leveren:**
• Volledige interface mapping tabel
• Cable specificatie overzicht
• Geschatte installatie tijd
• Mogelijke conflicten of waarschuwingen
• Rollback plan indien nodig

**NetBox tools die ik ga gebruiken:**
• netbox_generate_bulk_cable_plan
• netbox_map_rack_to_switch_interfaces

*Deze stap is volledig geautomatiseerd met comprehensive validation*

---

### **🔧 Stap 6/7: Bulk Cable Creation Uitvoering**
*Bridget:* "Tijd voor actie! Ik voer alle kabel verbindingen uit met real-time progress tracking."

**Enterprise Features:**
• Real-time progress updates per batch
• Success/failure status per kabel
• Rollback opties bij errors
• Performance metrics en timing

**NetBox tools die ik ga gebruiken:**
• netbox_bulk_create_cable_connections

**Jouw input nodig:**
• Uitvoering bevestiging (true/false)
• Batch size (optioneel, standaard: 10)

**Error Handling:**
• Automatische rollback bij kritieke errors
• Continue met resterende kabels na error
• Detailed error logs voor troubleshooting

---

### **🔧 Stap 7/7: Installation Documentatie & Afsluiting**
*Bridget:* "Geweldig! Alle kabels zijn aangemaakt. Nu genereer ik alle documentatie voor jouw technici."

**Wat ik automatisch ga leveren:**
• Technician installation checklist met alle kabel verbindingen
• Cable labeling schema met voorgedefinieerde labels
• Rack elevation diagram met nieuwe verbindingen
• Switch port allocation overzicht
• Installation timeline en prioriteiten
• Testing checklist voor commissioning
• Audit trail entry voor compliance

**NetBox tools die ik ga gebruiken:**
• netbox_create_journal_entry
• netbox_list_all_cables

---

## ✅ **Voltooiing Criteria:**

• Alle device interfaces correct geïdentificeerd in source rack
• Switch poorten succesvol gereserveerd en toegewezen
• Bulk cables aangemaakt met gespecificeerde kleur en type
• Interface mappings gedocumenteerd volgens gekozen algoritme
• Installation documentatie gegenereerd voor datacenter technici
• Journal entries aangemaakt voor volledige audit trail
• Rollback informatie beschikbaar voor eventuele wijzigingen

---

## 🚀 **Volgende Stappen:**

Na voltooiing van deze workflow:
• Fysieke kabel installatie door datacenter technici volgens checklist
• Cable testing en connectiviteit verificatie
• Network configuratie deployment op beide kanten
• Device commissioning en service activatie
• Cable status update naar 'connected' na succesvolle installatie

---

## 🏢 **Enterprise Features:**

**Safety Mechanisms:** Dry-run mode, batch processing, rollback support
**Progress Tracking:** Real-time updates, success/failure metrics, timing analysis
**Error Handling:** Comprehensive validation, partial success handling, detailed error logs
**Documentation:** Auto-generated installation guides, testing checklists, audit trails
**Scalability:** Handles 1-100+ cables with optimized batch processing

---

## 🛡️ **Bridget's Support:**

**Rollback hulp:** Als er iets misgaat kan ik je helpen met bulk cable disconnection en cleanup

**Troubleshooting:** Detailed logs en error analysis voor snelle probleem oplossing

**Documentatie:** Alle acties volledig gedocumenteerd voor audit trails en troubleshooting

**Expert guidance:** Ik help je met edge cases en complexe scenario's

---

## 📋 **Vereisten:**

• Source rack met devices en beschikbare interfaces
• Target switch met beschikbare poorten
• NetBox write permissions voor cable creation
• Optioneel: Cable specificatie standaarden van organisatie

---

## 🌟 **Perfect Voor:**

• Server rack to switch uplinks (lom1, eth0 interfaces)
• Switch stacking en interconnects
• Management network deployment
• Datacenter migration projecten
• Bulk equipment commissioning

---

**Klaar om bulk kabels aan te leggen? Laten we samen jouw infrastructuur perfect verbinden!** 🚀

*Bridget - NetBox Infrastructure Guide | NetBox MCP v1.0.0+ | 🦜 LEGO Parrot Mascotte*"""

    return workflow_message