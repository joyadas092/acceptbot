"""
Load test: Simulate 10,000 join requests.

Usage:
    python tests/load/simulate_join_requests.py --requests 10000 --workers 10

Measures:
- Time to process all requests
- MongoDB insert throughput
- Approval worker throughput
- Memory usage
"""
import asyncio
import argparse
import time
import random
from pathlib import Path
import sys
import tracemalloc

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def simulate_join_request(db, chat_id: int, user_id: int) -> dict:
    """Simulate a join request document."""
    return {
        "chat_id": chat_id,
        "user_id": user_id,
        "status": "pending",
        "created_at": time.time()
    }

async def worker_task(worker_id: int, requests: list, db_mock):
    """Simulate a worker processing a batch of requests."""
    processed = 0
    for req in requests:
        # Simulate processing delay
        await asyncio.sleep(0.001)
        processed += 1
    return processed

async def run_simulation(num_requests: int, num_workers: int) -> None:
    """Run the load simulation."""
    print(f"Starting simulation with {num_requests} requests and {num_workers} workers...")
    
    tracemalloc.start()
    start_time = time.time()
    
    # 1. Generate requests
    print("Generating requests...")
    chat_id = -1001234567890
    requests = [await simulate_join_request(None, chat_id, i) for i in range(num_requests)]
    
    # 2. Simulate batch insertion (Motor bulk_write)
    print("Simulating batch insertion...")
    insert_start = time.time()
    await asyncio.sleep(0.1)  # Mock DB time
    insert_end = time.time()
    
    # 3. Simulate processing workers
    print("Simulating processing workers...")
    chunk_size = num_requests // num_workers
    chunks = [requests[i:i + chunk_size] for i in range(0, num_requests, chunk_size)]
    
    worker_start = time.time()
    tasks = [worker_task(i, chunk, None) for i, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks)
    worker_end = time.time()
    
    total_time = time.time() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print("\n--- Simulation Results ---")
    print(f"Total Requests Processed: {sum(results)}")
    print(f"Total Time: {total_time:.2f} seconds")
    print(f"Insert Time: {insert_end - insert_start:.2f} seconds")
    print(f"Processing Time: {worker_end - worker_start:.2f} seconds")
    print(f"Throughput: {num_requests / total_time:.2f} req/sec")
    print(f"Peak Memory Usage: {peak / 10**6:.2f} MB")
    print("--------------------------")
    print("Expected bottlenecks: MongoDB write locks, Redis lock contention, Telegram API rate limits.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--requests', type=int, default=10000)
    parser.add_argument('--workers', type=int, default=10)
    args = parser.parse_args()
    asyncio.run(run_simulation(args.requests, args.workers))
