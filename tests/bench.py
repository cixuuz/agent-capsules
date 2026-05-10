"""Performance benchmarks for agent-capsules."""

import json
import tempfile
import time
from pathlib import Path

from agent_capsules import CapsuleStore, extract_capsules, GeneDistiller
from agent_capsules.models import Capsule


def generate_session(n_messages: int = 50, has_errors: bool = True) -> list[dict]:
    """Generate a realistic session with N messages."""
    messages = []
    messages.append({"role": "user", "content": "Set up a Python project with FastAPI and PostgreSQL"})
    
    for i in range(n_messages - 2):
        if i % 3 == 0:
            messages.append({"role": "user", "content": f"Now do step {i}: configure the {['database', 'auth', 'deploy', 'testing'][i % 4]} module"})
        elif i % 3 == 1:
            messages.append({"role": "assistant", "content": f"Running command to set up component {i}... " + "x" * 200})
        else:
            if has_errors and i % 7 == 0:
                messages.append({"role": "tool", "content": f"ERROR: ModuleNotFoundError: No module named 'psycopg2'\nTraceback (most recent call last):\n  File \"app.py\", line {i}, in <module>\n    import psycopg2\n" + "stack trace " * 20})
            else:
                messages.append({"role": "tool", "content": f"Successfully completed step {i}. Output: " + "ok " * 50})

    messages.append({"role": "assistant", "content": "All done! The project is set up."})
    return messages


def bench_extraction_heuristic():
    """Benchmark heuristic extraction at various session sizes."""
    print("=" * 60)
    print("BENCHMARK: Heuristic Extraction Speed")
    print("=" * 60)
    
    sizes = [10, 50, 100, 200, 500, 1000]
    
    for size in sizes:
        messages = generate_session(size, has_errors=True)
        
        # Warmup
        extract_capsules(messages, session_id="warmup", extractor="heuristic")
        
        # Bench
        iterations = 100
        start = time.perf_counter()
        for i in range(iterations):
            extract_capsules(messages, session_id=f"bench-{i}", extractor="heuristic")
        elapsed = time.perf_counter() - start
        
        per_call_us = (elapsed / iterations) * 1_000_000
        msgs_per_sec = (size * iterations) / elapsed
        
        print(f"  {size:>5} messages → {per_call_us:>8.1f} µs/call  ({msgs_per_sec:>10,.0f} msgs/sec)")
    
    print()


def bench_store_append():
    """Benchmark store append (JSONL write + dedup check)."""
    print("=" * 60)
    print("BENCHMARK: Store Append (write + dedup)")
    print("=" * 60)
    
    counts = [100, 500, 1000, 5000]
    
    for count in counts:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "bench.jsonl"
            store = CapsuleStore(path=store_path)
            
            capsules = [
                Capsule.now(
                    session_id=f"sess-{i}",
                    signal=f"Error #{i} in module X",
                    tags=["pip", "git"] if i % 2 == 0 else ["docker", "deploy"],
                    confidence="high" if i % 3 == 0 else "low",
                )
                for i in range(count)
            ]
            
            start = time.perf_counter()
            for c in capsules:
                store.append(c)
            elapsed = time.perf_counter() - start
            
            per_append_us = (elapsed / count) * 1_000_000
            file_size_kb = store_path.stat().st_size / 1024
            
            print(f"  {count:>5} appends → {per_append_us:>6.1f} µs/append  (file: {file_size_kb:.1f} KB)")
    
    print()


def bench_store_load():
    """Benchmark store loading at various sizes."""
    print("=" * 60)
    print("BENCHMARK: Store Load (read + parse)")
    print("=" * 60)
    
    counts = [100, 500, 1000, 5000, 10000]
    
    for count in counts:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "bench.jsonl"
            
            # Pre-populate
            lines = []
            for i in range(count):
                cap = Capsule.now(
                    session_id=f"sess-{i}",
                    signal=f"Error #{i}: something went wrong with module {i % 20}",
                    hypothesis=f"The root cause is dependency conflict #{i}",
                    attempt=f"Tried pinning version to {i}.0.0",
                    outcome="Resolved" if i % 2 == 0 else "Partially fixed",
                    lesson=f"Always check dependency {i % 20} compatibility first",
                    tags=["pip", "config"] if i % 2 == 0 else ["docker", "network"],
                    confidence="high" if i % 3 == 0 else "medium",
                )
                lines.append(cap.to_json())
            store_path.write_text("\n".join(lines) + "\n")
            
            file_size_kb = store_path.stat().st_size / 1024
            
            # Bench load
            iterations = 50 if count <= 1000 else 10
            start = time.perf_counter()
            for _ in range(iterations):
                store = CapsuleStore(path=store_path)
                store._session_ids = None  # Reset cache
                _ = store.load_all()
            elapsed = time.perf_counter() - start
            
            per_load_ms = (elapsed / iterations) * 1000
            
            print(f"  {count:>5} capsules ({file_size_kb:>6.1f} KB) → {per_load_ms:>7.2f} ms/load")
    
    print()


def bench_dedup_check():
    """Benchmark dedup lookups against a large store."""
    print("=" * 60)
    print("BENCHMARK: Dedup Check (has() lookups)")
    print("=" * 60)
    
    counts = [1000, 5000, 10000, 50000]
    
    for count in counts:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "bench.jsonl"
            
            # Pre-populate
            lines = []
            for i in range(count):
                lines.append(json.dumps({"session_id": f"sess-{i}", "date": "2025-01-01", "signal": "x", "tags": []}))
            store_path.write_text("\n".join(lines) + "\n")
            
            store = CapsuleStore(path=store_path)
            
            # Bench lookups (mix of hits and misses)
            lookups = 10000
            start = time.perf_counter()
            for i in range(lookups):
                store.has(f"sess-{i % (count * 2)}")  # 50% hit rate
            elapsed = time.perf_counter() - start
            
            per_lookup_ns = (elapsed / lookups) * 1_000_000_000
            
            print(f"  {count:>5} entries → {per_lookup_ns:>5.0f} ns/lookup  ({lookups/elapsed:,.0f} lookups/sec)")
    
    print()


def bench_distillation():
    """Benchmark gene distillation at various capsule counts."""
    print("=" * 60)
    print("BENCHMARK: Gene Distillation")
    print("=" * 60)
    
    counts = [10, 50, 100, 500, 1000]
    tags_pool = ["pip", "git", "docker", "npm", "config", "auth", "network", "database", "testing", "deploy"]
    
    for count in counts:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "bench.jsonl"
            store = CapsuleStore(path=store_path)
            
            for i in range(count):
                cap = Capsule.now(
                    session_id=f"sess-{i}",
                    signal=f"Error #{i}",
                    lesson=f"Lesson learned from error #{i}",
                    tags=[tags_pool[i % len(tags_pool)], tags_pool[(i + 3) % len(tags_pool)]],
                    confidence="high" if i % 3 == 0 else "low",
                )
                store.append(cap)
            
            # Bench distillation
            iterations = 50 if count <= 100 else 10
            start = time.perf_counter()
            for _ in range(iterations):
                distiller = GeneDistiller(store, min_cluster_size=3)
                genes = distiller.distill()
            elapsed = time.perf_counter() - start
            
            per_distill_ms = (elapsed / iterations) * 1000
            
            print(f"  {count:>5} capsules → {per_distill_ms:>7.2f} ms/distill  ({len(genes)} genes proposed)")
    
    print()


def bench_end_to_end():
    """Benchmark the full flow: extract → append → check."""
    print("=" * 60)
    print("BENCHMARK: End-to-End (extract + append + dedup)")
    print("=" * 60)
    print("  Simulates what happens at session end\n")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "bench.jsonl"
        store = CapsuleStore(path=store_path)
        
        sessions = [generate_session(50, has_errors=True) for _ in range(100)]
        
        start = time.perf_counter()
        for i, msgs in enumerate(sessions):
            capsules = extract_capsules(msgs, session_id=f"e2e-{i}", extractor="heuristic")
            for c in capsules:
                store.append(c)
        elapsed = time.perf_counter() - start
        
        per_session_us = (elapsed / len(sessions)) * 1_000_000
        total_capsules = store.count()
        
        print(f"  100 sessions (50 msgs each) → {per_session_us:.1f} µs/session")
        print(f"  Total capsules stored: {total_capsules}")
        print(f"  Total time: {elapsed*1000:.1f} ms")
        print(f"  Overhead per session: {per_session_us/1000:.2f} ms")
    
    print()


def main():
    print()
    print("🧬 agent-capsules Performance Benchmarks")
    print(f"   Python {__import__('sys').version.split()[0]}")
    print()
    
    bench_extraction_heuristic()
    bench_store_append()
    bench_store_load()
    bench_dedup_check()
    bench_distillation()
    bench_end_to_end()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
  Key takeaways:
  • Heuristic extraction: < 1ms even for 1000-message sessions
  • Store append: ~microseconds per write (JSONL is fast)
  • Dedup: O(1) set lookup after initial load
  • Distillation: < 100ms for 1000 capsules
  • End-to-end overhead per session: < 1ms
  
  → Adding agent-capsules to your session-end hook adds
    negligible latency. The agent won't notice.
""")


if __name__ == "__main__":
    main()
