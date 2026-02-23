import asyncio
import asyncpg
import sys

async def test_pure_asyncpg():
    print(f"Platform: {sys.platform}")
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    import urllib.parse
    encoded_pass = urllib.parse.quote('4hrEEZZ5=M"1FXkE')
    dsn = f"postgresql://dev-playground:{encoded_pass}@127.0.0.1:5432/agentic-rag"
    
    print("Attempting to connect to proxy at 127.0.0.1:5432 via pure asyncpg...")
    try:
        conn = await asyncpg.connect(dsn)
        print("✅ SUCCESS: Pure asyncpg connection established!")
        
        # Test a simple query
        version = await conn.fetchval('SELECT version()')
        print(f"PostgreSQL Version: {version}")
        
        await conn.close()
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_pure_asyncpg())
