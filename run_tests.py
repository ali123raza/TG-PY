"""
Test suite for full_app - Backend and Frontend integration tests
Tests all functions to ensure they work correctly
"""
import asyncio
import sys
import os
from pathlib import Path

# Set environment FIRST before any imports
os.environ['TG_BASE_DIR'] = str(Path(__file__).parent)

# Add full_app to path
sys.path.insert(0, str(Path(__file__).parent))

# Now import
from core import service_manager, init_db, async_session
from core.models import Account, Proxy, Campaign, MessageTemplate, Log, FailedMessage

async def test_database():
    """Test 1: Database initialization"""
    print("\n[Test 1] Database Initialization...")
    try:
        await init_db()
        print("PASS: Database initialized successfully")
        return True
    except Exception as e:
        print(f"FAIL: Database init failed: {e}")
        return False

async def test_service_manager():
    """Test 2: Service Manager initialization"""
    print("\n[Test 2] Service Manager Initialization...")
    try:
        await service_manager.init()
        print("PASS: Service manager initialized")
        return True
    except Exception as e:
        print(f"FAIL: Service manager init failed: {e}")
        return False

async def test_proxy_system():
    """Test 3: Proxy CRUD operations (IMPORTANT for Pakistan)"""
    print("\n[Test 3] Proxy System (CRITICAL for Pakistan)...")
    results = []
    
    # Create proxy
    try:
        proxy_data = {
            "scheme": "socks5",
            "host": "127.0.0.1",
            "port": 1080,
            "username": "test_user",
            "password": "test_pass",
            "is_active": True
        }
        proxy = await service_manager.create_proxy(proxy_data)
        print(f"PASS: Proxy created: ID {proxy['id']}")
        results.append(True)
        
        # Get all proxies
        proxies = await service_manager.get_proxies()
        print(f"PASS: Got {len(proxies)} proxies")
        results.append(True)
        
        # Delete proxy
        await service_manager.delete_proxy(proxy['id'])
        print("PASS: Proxy deleted")
        results.append(True)
    except Exception as e:
        print(f"FAIL: Proxy test failed: {e}")
        results.append(False)
    
    return all(results)

async def test_account_system():
    """Test 4: Account management"""
    print("\n[Test 4] Account Management...")
    results = []
    
    try:
        # Get accounts (should work even if empty)
        accounts = await service_manager.get_accounts()
        print(f"PASS: Got {len(accounts)} accounts")
        results.append(True)
        
        # Get stats
        stats = await service_manager.get_stats()
        print(f"PASS: Stats retrieved: {stats.get('total_accounts', {})}")
        results.append(True)
    except Exception as e:
        print(f"FAIL: Account test failed: {e}")
        results.append(False)
    
    return all(results)

async def test_campaign_system():
    """Test 5: Campaign CRUD"""
    print("\n[Test 5] Campaign Management...")
    results = []
    
    try:
        # Create campaign
        campaign_data = {
            "name": "Test Campaign",
            "message_text": "Test message",
            "targets": "test_group",
            "delay_min": 30,
            "delay_max": 60,
            "max_per_account": 50
        }
        campaign = await service_manager.create_campaign(campaign_data)
        print(f"PASS: Campaign created: ID {campaign['id']}")
        results.append(True)
        
        # Get campaigns
        campaigns = await service_manager.get_campaigns()
        print(f"PASS: Got {len(campaigns)} campaigns")
        results.append(True)
        
        # Update campaign
        await service_manager.update_campaign(campaign['id'], {"status": "running"})
        print("PASS: Campaign updated")
        results.append(True)
        
        # Delete campaign
        await service_manager.delete_campaign(campaign['id'])
        print("PASS: Campaign deleted")
        results.append(True)
    except Exception as e:
        print(f"FAIL: Campaign test failed: {e}")
        results.append(False)
    
    return all(results)

async def test_template_system():
    """Test 6: Template CRUD"""
    print("\n[Test 6] Template Management...")
    results = []
    
    try:
        # Create template
        template_data = {
            "name": "Test Template",
            "text": "Hello {name}!",
            "media_path": "",
            "media_type": ""
        }
        template = await service_manager.create_template(template_data)
        print(f"PASS: Template created: ID {template['id']}")
        results.append(True)
        
        # Get templates
        templates = await service_manager.get_templates()
        print(f"PASS: Got {len(templates)} templates")
        results.append(True)
        
        # Delete template
        await service_manager.delete_template(template['id'])
        print("PASS: Template deleted")
        results.append(True)
    except Exception as e:
        print(f"FAIL: Template test failed: {e}")
        results.append(False)
    
    return all(results)

async def test_logs_system():
    """Test 7: Logs"""
    print("\n[Test 7] Logs System...")
    results = []
    
    try:
        # Create log
        log = await service_manager.create_log("Test log message", "test", "info")
        print(f"PASS: Log created: ID {log['id']}")
        results.append(True)
        
        # Get logs
        logs = await service_manager.get_logs(limit=10)
        print(f"PASS: Got {len(logs)} logs")
        results.append(True)
    except Exception as e:
        print(f"FAIL: Logs test failed: {e}")
        results.append(False)
    
    return all(results)

async def test_settings():
    """Test 8: Settings"""
    print("\n[Test 8] Settings...")
    results = []
    
    try:
        # Get settings
        settings = await service_manager.get_settings()
        print(f"PASS: Settings retrieved: API ID {settings.get('api_id')}")
        results.append(True)
        
        # Save settings
        await service_manager.save_settings({"default_delay_min": 45})
        print("PASS: Settings saved")
        results.append(True)
    except Exception as e:
        print(f"FAIL: Settings test failed: {e}")
        results.append(False)
    
    return all(results)

async def test_telegram_client():
    """Test 9: Telegram client manager with proxy support"""
    print("\n[Test 9] Telegram Client (Proxy Support)...")
    
    try:
        from services.telegram import client_manager
        from core.config import API_ID, API_HASH
        
        print(f"PASS: Telegram client manager loaded")
        print(f"   API ID: {API_ID}")
        print(f"   API Hash: {API_HASH[:10]}..." if API_HASH else "   API Hash: Not set")
        
        # Test proxy formatting
        proxy_dict = {
            "scheme": "socks5",
            "host": "127.0.0.1",
            "port": 1080,
            "username": "user",
            "password": "pass"
        }
        formatted = client_manager._make_proxy(proxy_dict)
        print(f"PASS: Proxy formatting works: {formatted}")
        
        return True
    except Exception as e:
        print(f"FAIL: Telegram client test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("FULL_APP COMPREHENSIVE TEST SUITE")
    print("Testing all backend functions")
    print("="*60)
    
    tests = [
        ("Database", test_database),
        ("Service Manager", test_service_manager),
        ("Proxy System", test_proxy_system),
        ("Account System", test_account_system),
        ("Campaign System", test_campaign_system),
        ("Template System", test_template_system),
        ("Logs System", test_logs_system),
        ("Settings", test_settings),
        ("Telegram Client", test_telegram_client),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
        except Exception as e:
            print(f"FAIL: {name} crashed: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{status}: {name}")
    
    print("-"*60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("ALL TESTS PASSED!")
    else:
        print("Some tests failed. Check errors above.")
    
    return passed == total

if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    if not success:
        print("\nSome tests failed")
