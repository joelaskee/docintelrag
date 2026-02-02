
import sys
import os
# Add app to path
sys.path.append(os.getcwd())

from app.services.bi import bi_service

def test():
    query = "Somma del totale delle fatture"
    print(f"--- Testing query: {query} ---")

    # Test SQL Gen
    print("Generating SQL...")
    sql = bi_service._generate_sql(query)
    print(f"Generated SQL: {sql}")

    if not sql:
        print("SQL Gen failed")
        return

    # Test Execution
    print("Executing query...")
    try:
        data = bi_service._execute_query(sql)
        print(f"Data rows: {len(data)}")
        if data:
            print(f"Sample: {data[0]}")
    except Exception as e:
        print(f"Execution failed: {e}")
        return

    # Test Synthesis
    print("Synthesizing answer...")
    ans = bi_service._synthesize_answer(query, sql, data)
    print(f"Answer: {ans}")

if __name__ == "__main__":
    test()
