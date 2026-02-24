import asyncio
import sys
from langchain_google_cloud_sql_pg import PostgresEngine

# Windows workaround for asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_native_connector():
    try:
        print("Testing native afrom_instance...")
        engine = await PostgresEngine.afrom_instance(
            project_id="dev-playground-0126",
            region="us-central1",
            instance="dev-playground-db-instance",
            database="agentic-rag",
            user="dev-playground",
            password='4hrEEZZ5=M"1FXkE',
        )
        print("SUCCESS: Connected natively without cloud-sql-proxy.exe!")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_native_connector())
