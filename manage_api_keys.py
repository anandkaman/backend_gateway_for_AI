#!/usr/bin/env python3
"""
API Key Management CLI
Generate, revoke, and manage API keys for external clients
"""

import asyncio
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.auth.api_keys import APIKeyManager


async def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    api_key_manager = APIKeyManager(client)
    await api_key_manager.initialize()
    
    try:
        if command == "create":
            await create_key(api_key_manager)
        elif command == "list":
            await list_keys(api_key_manager)
        elif command == "revoke":
            await revoke_key(api_key_manager)
        elif command == "delete":
            await delete_key(api_key_manager)
        elif command == "stats":
            await show_stats(api_key_manager)
        else:
            print(f"Unknown command: {command}")
            print_usage()
            sys.exit(1)
    finally:
        client.close()


def print_usage():
    """Print usage information"""
    print("""
API Key Management Tool

Usage:
  python3 manage_api_keys.py <command> [options]

Commands:
  create <email> [name] [days]  - Create new API key
  list [--all]                  - List API keys
  revoke <email>                - Revoke API key(s)
  delete <email>                - Delete API key(s)
  stats <email>                 - Show usage statistics

Examples:
  # Create API key for client
  python3 manage_api_keys.py create client@example.com "Acme Corp" 365

  # List active keys
  python3 manage_api_keys.py list

  # Revoke client's keys
  python3 manage_api_keys.py revoke client@example.com

  # Show client stats
  python3 manage_api_keys.py stats client@example.com
""")


async def create_key(manager: APIKeyManager):
    """Create a new API key"""
    if len(sys.argv) < 3:
        print("Error: Email required")
        print("Usage: python3 manage_api_keys.py create <email> [name] [days]")
        sys.exit(1)
    
    email = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else ""
    expires_days = int(sys.argv[4]) if len(sys.argv) > 4 else None
    
    print(f"\n🔑 Creating API key for: {email}")
    
    result = await manager.create_api_key(
        email=email,
        name=name,
        expires_days=expires_days
    )
    
    print("\n" + "="*60)
    print("✅ API Key Created Successfully!")
    print("="*60)
    print(f"\n⚠️  IMPORTANT: Save this key now! It won't be shown again.\n")
    print(f"API Key: {result['api_key']}")
    print(f"\nClient Details:")
    print(f"  Email: {result['email']}")
    print(f"  Name: {result['name']}")
    print(f"  Created: {result['created_at']}")
    if result['expires_at']:
        print(f"  Expires: {result['expires_at']}")
    else:
        print(f"  Expires: Never")
    print("\n" + "="*60)
    print("\nShare this with the client:")
    print(f"  API Key: {result['api_key']}")
    print(f"  Usage: -H \"X-API-Key: {result['api_key']}\"")
    print("="*60 + "\n")


async def list_keys(manager: APIKeyManager):
    """List all API keys"""
    show_all = "--all" in sys.argv
    
    print(f"\n📋 API Keys ({'All' if show_all else 'Active Only'})")
    print("="*80)
    
    keys = await manager.list_api_keys(active_only=not show_all)
    
    if not keys:
        print("No API keys found.")
        return
    
    print(f"\n{'Email':<30} {'Name':<20} {'Status':<10} {'Usage':<10} {'Created'}")
    print("-"*80)
    
    for key in keys:
        status = "✅ Active" if key['active'] else "❌ Revoked"
        created = key['created_at'].strftime("%Y-%m-%d")
        usage = key.get('usage_count', 0)
        
        print(f"{key['email']:<30} {key['name']:<20} {status:<10} {usage:<10} {created}")
    
    print(f"\nTotal: {len(keys)} keys")
    print("="*80 + "\n")


async def revoke_key(manager: APIKeyManager):
    """Revoke API key(s)"""
    if len(sys.argv) < 3:
        print("Error: Email required")
        print("Usage: python3 manage_api_keys.py revoke <email>")
        sys.exit(1)
    
    email = sys.argv[2]
    
    print(f"\n⚠️  Revoking API keys for: {email}")
    confirm = input("Are you sure? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("Cancelled.")
        return
    
    count = await manager.revoke_api_key(email)
    
    if count > 0:
        print(f"\n✅ Revoked {count} API key(s) for {email}\n")
    else:
        print(f"\n❌ No active keys found for {email}\n")


async def delete_key(manager: APIKeyManager):
    """Delete API key(s) permanently"""
    if len(sys.argv) < 3:
        print("Error: Email required")
        print("Usage: python3 manage_api_keys.py delete <email>")
        sys.exit(1)
    
    email = sys.argv[2]
    
    print(f"\n⚠️  PERMANENTLY DELETING API keys for: {email}")
    print("This action cannot be undone!")
    confirm = input("Type 'DELETE' to confirm: ")
    
    if confirm != "DELETE":
        print("Cancelled.")
        return
    
    count = await manager.delete_api_key(email)
    
    if count > 0:
        print(f"\n✅ Deleted {count} API key(s) for {email}\n")
    else:
        print(f"\n❌ No keys found for {email}\n")


async def show_stats(manager: APIKeyManager):
    """Show usage statistics"""
    if len(sys.argv) < 3:
        print("Error: Email required")
        print("Usage: python3 manage_api_keys.py stats <email>")
        sys.exit(1)
    
    email = sys.argv[2]
    
    stats = await manager.get_key_stats(email)
    
    if not stats:
        print(f"\n❌ No keys found for {email}\n")
        return
    
    print(f"\n📊 Statistics for: {email}")
    print("="*60)
    print(f"Total Keys: {stats['total_keys']}")
    print(f"Active Keys: {stats['active_keys']}")
    print(f"Total API Calls: {stats['total_usage']}")
    if stats['last_used']:
        print(f"Last Used: {stats['last_used']}")
    else:
        print(f"Last Used: Never")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
