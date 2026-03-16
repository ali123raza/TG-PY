"""
Test phone number resolution on Telegram
"""
import asyncio
from pyrogram import Client
from core.config import API_ID, API_HASH, SESSIONS_DIR

async def test_phone(phone: str):
    """Test if a phone number exists on Telegram"""
    
    # Use existing session
    session_name = "test_resolution"
    
    client = Client(
        name=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        workdir=str(SESSIONS_DIR),
    )
    
    await client.start()
    
    print(f"\nTesting phone: {phone}")
    print("-" * 50)
    
    # Method 1: import_contacts
    print("\n1. Testing import_contacts...")
    try:
        from pyrogram.types import InputPhoneContact
        result = await client.import_contacts([
            InputPhoneContact(phone=phone, first_name="Test", last_name="")
        ])
        
        if result.users:
            print(f"   ✅ import_contacts returned {len(result.users)} user(s)")
            for u in result.users:
                print(f"      - ID: {u.id}, Name: {u.first_name}, Phone: {getattr(u, 'phone_number', 'N/A')}")
        else:
            print(f"   ❌ import_contacts returned NO users")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Method 2: get_contacts
    print("\n2. Testing get_contacts...")
    try:
        contacts = await client.get_contacts()
        print(f"   Total contacts: {len(contacts)}")
        
        # Search for phone
        digits = phone.lstrip('+')
        found = False
        for c in contacts:
            c_phone = getattr(c, 'phone_number', '')
            if c_phone and c_phone.lstrip('+') == digits:
                print(f"   ✅ Found in contacts: ID={c.id}, Name={c.first_name}")
                found = True
                break
        
        if not found:
            print(f"   ❌ Phone not found in contacts")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Method 3: Try direct send_message with phone
    print("\n3. Testing send_message with phone...")
    try:
        await client.send_message(phone, "Test message (ignore this)")
        print(f"   ✅ Message sent successfully with phone number!")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    await client.stop()
    
    # Clean up test session
    import os
    for suffix in ['.session', '.session-journal']:
        p = SESSIONS_DIR / f"{session_name}{suffix}"
        if p.exists():
            p.unlink()

if __name__ == "__main__":
    phone = "+923262390998"  # Test number
    asyncio.run(test_phone(phone))
