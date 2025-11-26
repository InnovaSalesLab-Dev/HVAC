"""
Script to clean up duplicate tools in Vapi dashboard.
Identifies tools with the same name and deletes duplicates, keeping only one.
"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.vapi import VapiClient
from src.utils.logging import logger


async def cleanup_duplicate_tools():
    """List all tools, identify duplicates, and delete them"""
    vapi = VapiClient()
    
    print("=" * 70)
    print("🧹 CLEANING UP DUPLICATE TOOLS IN VAPI DASHBOARD")
    print("=" * 70)
    print()
    
    try:
        # Get all tools
        print("📋 Fetching all tools from Vapi dashboard...")
        all_tools = await vapi.list_tools()
        print(f"✅ Found {len(all_tools)} total tools\n")
        
        if not all_tools:
            print("No tools found. Nothing to clean up.")
            return
        
        # Group tools by name
        tools_by_name = defaultdict(list)
        print("📋 All tools found:\n")
        for tool in all_tools:
            if isinstance(tool, dict):
                tool_id = tool.get("id", "")
                tool_type = tool.get("type", "unknown")
                
                # Get tool name from different possible locations
                tool_name = None
                
                # Check different tool types
                if tool_type == "apiRequest":
                    api_req = tool.get("apiRequest", {})
                    if isinstance(api_req, dict):
                        tool_name = api_req.get("name")
                elif tool_type == "function":
                    func = tool.get("function", {})
                    if isinstance(func, dict):
                        tool_name = func.get("name")
                
                # Try to get name from any location
                if not tool_name:
                    tool_name = (
                        tool.get("name") or
                        (tool.get("apiRequest", {}).get("name") if isinstance(tool.get("apiRequest"), dict) else None) or
                        (tool.get("function", {}).get("name") if isinstance(tool.get("function"), dict) else None)
                    )
                
                if tool_name:
                    print(f"   - {tool_name} (ID: {tool_id[:8]}..., Type: {tool_type})")
                    tools_by_name[tool_name].append({
                        "id": tool_id,
                        "name": tool_name,
                        "type": tool_type,
                        "full_tool": tool
                    })
                else:
                    print(f"   - [NO NAME] (ID: {tool_id[:8]}..., Type: {tool_type})")
        
        print()
        
        # Find duplicates
        duplicates = {name: tools for name, tools in tools_by_name.items() if len(tools) > 1}
        
        if not duplicates:
            print("✅ No duplicate tools found. All tools are unique.")
            return
        
        print(f"🔍 Found {len(duplicates)} tool names with duplicates:\n")
        
        total_to_delete = 0
        tools_to_delete = []
        
        for tool_name, tools in duplicates.items():
            print(f"📌 {tool_name}: {len(tools)} instances")
            # Keep the first one (usually the oldest), delete the rest
            for idx, tool in enumerate(tools):
                if idx == 0:
                    print(f"   ✅ Keeping: {tool['id']} (type: {tool['type']})")
                else:
                    print(f"   🗑️  Will delete: {tool['id']} (type: {tool['type']})")
                    tools_to_delete.append(tool)
            print()
            total_to_delete += len(tools) - 1
        
        if not tools_to_delete:
            print("No tools to delete.")
            return
        
        # Confirm deletion
        print(f"⚠️  About to delete {total_to_delete} duplicate tool(s)")
        print("   This will keep the first instance of each duplicate tool name.")
        print()
        
        # Delete duplicates
        deleted_count = 0
        failed_count = 0
        
        for tool in tools_to_delete:
            try:
                print(f"🗑️  Deleting {tool['name']} (ID: {tool['id']})...")
                await vapi.delete_tool(tool['id'])
                print(f"   ✅ Deleted successfully")
                deleted_count += 1
            except Exception as e:
                print(f"   ❌ Failed to delete: {str(e)}")
                failed_count += 1
                logger.exception(f"Error deleting tool {tool['id']}")
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 CLEANUP SUMMARY")
        print("=" * 70)
        print(f"\n✅ Deleted: {deleted_count} duplicate tool(s)")
        if failed_count > 0:
            print(f"❌ Failed: {failed_count} tool(s)")
        print(f"📋 Remaining: {len(all_tools) - deleted_count} tool(s)")
        print("\n✅ Cleanup complete!")
        print("\nNext steps:")
        print("1. Go to dashboard.vapi.ai/tools to verify")
        print("2. Each tool name should now appear only once")
        print()
        
    except Exception as e:
        logger.exception("Error during cleanup")
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(cleanup_duplicate_tools())

