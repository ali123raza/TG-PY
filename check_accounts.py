"""
Diagnostic script to check why messages are failing
Run: py check_accounts.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import async_session
from core.models import Account, Log, Proxy
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

async def check_accounts():
    print("=" * 60)
    print("MESSAGE SENDING DIAGNOSTIC")
    print("=" * 60)
    
    async with async_session() as db:
        # Check accounts
        result = await db.execute(
            select(Account).options(selectinload(Account.proxy))
        )
        accounts = result.scalars().all()
        
        print(f"\n📱 Total Accounts: {len(accounts)}")
        print("-" * 60)
        
        for acc in accounts:
            status_icon = "✅" if acc.is_active else "❌"
            proxy_status = f"🌐 {acc.proxy.host}:{acc.proxy.port}" if acc.proxy else "⚠️  NO PROXY"
            print(f"{status_icon} {acc.phone}")
            print(f"   Status: {acc.status or 'unknown'}")
            print(f"   Active: {acc.is_active}")
            print(f"   Proxy: {proxy_status}")
            print(f"   Messages Sent: {acc.messages_sent or 0}")
            print()
        
        # Check recent logs
        print("\n📋 Recent Error Logs (last 20):")
        print("-" * 60)
        
        result = await db.execute(
            select(Log)
            .where(Log.level == "error")
            .order_by(desc(Log.created_at))
            .limit(20)
        )
        logs = result.scalars().all()
        
        if logs:
            for log in logs:
                print(f"[{log.created_at}] {log.category}: {log.message}")
        else:
            print("No error logs found")
        
        # Check failed messages
        from core.models import FailedMessage
        result = await db.execute(
            select(FailedMessage).order_by(desc(FailedMessage.created_at)).limit(10)
        )
        failed = result.scalars().all()
        
        print(f"\n❌ Recent Failed Messages ({len(failed)}):")
        print("-" * 60)
        
        if failed:
            for f in failed:
                print(f"Target: {f.target}")
                print(f"Error: {f.error}")
                print(f"Time: {f.created_at}")
                print()
        else:
            print("No failed messages in database")
        
        # Check proxies
        result = await db.execute(select(Proxy))
        proxies = result.scalars().all()
        
        print(f"\n🌐 Available Proxies: {len(proxies)}")
        print("-" * 60)
        
        for p in proxies:
            print(f"  {p.host}:{p.port} ({p.scheme})")
        
        print("\n" + "=" * 60)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 60)
        print("\nCommon Issues:")
        print("1. ❌ Account not active - Check session validity")
        print("2. ⚠️  No proxy assigned - Assign a working proxy to each account")
        print("3. 🔒 Account banned/restricted - Check Telegram status")
        print("4. ⏱️  FloodWait - Wait for rate limit to expire")
        print("5. 📞 Phone not on Telegram - Target phone not registered")

if __name__ == "__main__":
    asyncio.run(check_accounts())
