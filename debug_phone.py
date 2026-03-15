"""
Debug script to verify if phone number is on Telegram using DB proxy and account
"""
import asyncio
import sys
sys.path.insert(0, r'e:\TG-PY\full_app')

from sqlalchemy import select
from core.database import async_session
from core.models import Account, Proxy
from services.telegram import client_manager

async def test_phone_check():
    phone_to_check = "+923262390998"
    
    print(f"Testing phone: {phone_to_check}")
    print("=" * 60)
    
    async with async_session() as db:
        # Get active account
        result = await db.execute(
            select(Account).where(Account.is_active == True).limit(1)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            print("❌ No active account found in DB!")
            return
        
        print(f"✓ Account found: {account.phone} (ID: {account.id})")
        print(f"  Status: {account.status}, Active: {account.is_active}")
        
        # Get proxy for this account
        proxy = None
        if account.proxy_id:
            proxy = await db.get(Proxy, account.proxy_id)
        
        if proxy:
            print(f"✓ Proxy assigned: {proxy.host}:{proxy.port} ({proxy.scheme})")
        else:
            print("⚠ No proxy assigned - using direct connection")
        
        print("\n" + "=" * 60)
        print("Testing Telegram connection...")
        
        try:
            # Get client
            client = await client_manager.get_client(account.id, account.phone, proxy)
            print(f"✓ Client connected successfully!")
            
            # Try to import contact
            print(f"\nTrying to import contact: {phone_to_check}")
            
            try:
                from pyrogram.types import InputPhoneContact
                contacts = [InputPhoneContact(phone=phone_to_check, first_name="Test", last_name="")]
                result = await client.import_contacts(contacts)
                
                print(f"✓ import_contacts returned {len(result.users)} users")
                
                if result.users:
                    for u in result.users:
                        phone = getattr(u, 'phone_number', None)
                        uid = getattr(u, 'id', None)
                        print(f"  - User: phone={phone}, id={uid}")
                        
                        # Check if phone matches
                        if phone == phone_to_check or phone == phone_to_check.lstrip('+'):
                            print(f"\n✅ PHONE FOUND ON TELEGRAM! User ID: {uid}")
                        else:
                            print(f"\n⚠ Phone returned doesn't match exactly")
                            print(f"  Expected: {phone_to_check}")
                            print(f"  Got: {phone}")
                else:
                    print(f"\n❌ NO USERS RETURNED - Phone not on Telegram or error")
                    
                    # Try alternative method - resolve username
                    try:
                        print("\nTrying to send a test message directly...")
                        await client.send_message(phone_to_check, "Test")
                        print("✅ Message sent successfully!")
                    except Exception as e:
                        print(f"❌ Send failed: {e}")
                
            except Exception as e:
                print(f"❌ import_contacts failed: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"❌ Failed to connect client: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_phone_check())
