#!/usr/bin/env python3
"""
Quick fix script to handle missing dependencies gracefully
This will modify imports to be optional, allowing the server to start
"""

import os
import sys

def create_import_wrapper():
    """Create a wrapper for optional imports in project_graph_generator.py"""

    file_path = "src/mcp_core/services/project_graph_generator.py"

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find and replace the problematic imports
    new_lines = []
    for i, line in enumerate(lines):
        if line.strip() == "from pyvis.network import Network":
            new_lines.append("try:\n")
            new_lines.append("    from pyvis.network import Network\n")
            new_lines.append("    PYVIS_AVAILABLE = True\n")
            new_lines.append("except ImportError:\n")
            new_lines.append("    PYVIS_AVAILABLE = False\n")
            new_lines.append("    Network = None\n")
        elif line.strip() == "import networkx as nx":
            new_lines.append("try:\n")
            new_lines.append("    import networkx as nx\n")
            new_lines.append("    NETWORKX_AVAILABLE = True\n")
            new_lines.append("except ImportError:\n")
            new_lines.append("    NETWORKX_AVAILABLE = False\n")
            new_lines.append("    nx = None\n")
        else:
            new_lines.append(line)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"✅ Fixed optional imports in {file_path}")

def install_missing_dependencies():
    """Install the missing dependencies"""
    print("\n📦 Installing missing dependencies...")
    print("Run this command to install all missing dependencies:\n")
    print("pip install pyvis networkx aiohttp aiohttp-cors psutil watchdog jieba")
    print("\nOr install all requirements:")
    print("pip install -r requirements_complete.txt")

def main():
    print("="*60)
    print("MCP Missing Dependencies Fix")
    print("="*60)

    # Option 1: Make imports optional (quick fix)
    try:
        create_import_wrapper()
        print("\n✅ Optional import wrappers created")
        print("   The server should now start, but some features may be disabled")
    except Exception as e:
        print(f"❌ Failed to create wrappers: {e}")

    # Option 2: Show install command
    install_missing_dependencies()

    print("\n" + "="*60)
    print("RECOMMENDED ACTION:")
    print("1. Install missing dependencies:")
    print("   pip install -r requirements_complete.txt")
    print("\n2. Then start the server:")
    print("   python3 mcp_server_enterprise.py")
    print("="*60)

if __name__ == "__main__":
    main()