"""
Debug phone check - Direct DB test without client connection
"""
import asyncio
import sys
sys.path.insert(0, r'e:\TG-PY\full_app')

from sqlalchemy import select
from core.database import async_session
from core.models import Account, Proxy, Log, FailedMessage

async def analyze_phone_issue():
    phone_to_check = "+923262390998"
    
    print(f"Analyzing issue for phone: {phone_to_check}")
    print("=" * 70)
    
    async with async_session() as db:
        # Get account info
        result = await db.execute(
            select(Account).where(Account.is_active == True).limit(1)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            print("❌ No active account found!")
            return
        
        print(f"✓ Account: {account.phone} (ID: {account.id})")
        print(f"  Status: {account.status}, Messages sent: {account.messages_sent}")
        
        # Get proxy info
        if account.proxy_id:
            proxy = await db.get(Proxy, account.proxy_id)
            if proxy:
                print(f"✓ Proxy: {proxy.host}:{proxy.port} ({proxy.scheme})")
                print(f"  Proxy active: {proxy.is_active}")
        else:
            print("⚠ No proxy assigned")
        
        # Check recent logs for this phone
        print("\n" + "=" * 70)
        print("Recent logs for 'message' category:")
        
        result = await db.execute(
            select(Log)
            .where(Log.category == "message")
            .order_by(Log.created_at.desc())
            .limit(20)
        )
        logs = result.scalars().all()
        
        for log in logs:
            msg = log.message or ""
            if phone_to_check in msg or "not on Telegram" in msg:
                print(f"  [{log.level}] {log.created_at}: {msg[:100]}")
        
        # Check FailedMessages table
        print("\n" + "=" * 70)
        print("Failed messages in DB:")
        
        result = await db.execute(
            select(FailedMessage)
            .where(FailedMessage.target == phone_to_check)
            .order_by(FailedMessage.created_at.desc())
            .limit(10)
        )
        failed = result.scalars().all()
        
        if failed:
            for f in failed:
                print(f"  Error: {f.error}")
                print(f"  Time: {f.created_at}")
        else:
            print("  No failed messages found for this phone")
        
        # Check what targets were recently used
        print("\n" + "=" * 70)
        print("Recent FailedMessages (all):")
        
        result = await db.execute(
            select(FailedMessage)
            .order_by(FailedMessage.created_at.desc())
            .limit(10)
        )
        all_failed = result.scalars().all()
        
        for f in all_failed:
            print(f"  Target: {f.target}")
            print(f"  Error: {f.error}")
            print(f"  Time: {f.created_at}")
            print()

if __name__ == "__main__":
    asyncio.run(analyze_phone_issue())
