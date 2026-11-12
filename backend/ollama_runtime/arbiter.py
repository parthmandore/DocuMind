"""DocuMind Ollama Hardware Arbiter

Enforces single-operation mutual exclusion across all Ollama requests
(generation, embedding, model management) to protect the 16 GB host memory envelope.
Coordinates between asynchronous coroutines and worker threads within the backend process.
"""

import time
import asyncio
import threading
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Dict, Any
import psutil

class OllamaBusyError(Exception):
    """Raised when Ollama is busy and lock cannot be acquired within timeout."""
    pass

class MemoryThresholdError(Exception):
    """Raised when available system memory falls below the safety floor."""
    pass

class OllamaHardwareArbiter:
    def __init__(self, min_free_mb: int = 200):
        self._async_lock = asyncio.Lock()
        self._thread_lock = threading.Lock()
        self.min_free_mb = min_free_mb
        
        # State tracking
        self.current_operation: Optional[str] = None
        self.active_since: Optional[float] = None
        self.operations_count: int = 0
        self.failures_count: int = 0
        self.last_duration_sec: float = 0.0

    @property
    def is_busy(self) -> bool:
        return self._thread_lock.locked()

    def get_status(self) -> Dict[str, Any]:
        """Provides non-sensitive telemetry about arbiter state."""
        busy = self.is_busy
        elapsed = round(time.perf_counter() - self.active_since, 2) if (busy and self.active_since) else 0.0
        return {
            "status": "busy" if busy else "idle",
            "active_operation": self.current_operation if busy else None,
            "active_duration_sec": elapsed,
            "total_operations": self.operations_count,
            "total_failures": self.failures_count,
            "last_duration_sec": self.last_duration_sec
        }

    def _check_memory(self, operation: str = ""):
        """Checks if available system memory is above the safety floor without thrashing active models."""
        avail_mb = psutil.virtual_memory().available / (1024 * 1024)

        # Only trigger blocking GC sweep when RAM headroom is getting tight
        if avail_mb < max(self.min_free_mb + 250, 450):
            import gc
            gc.collect()
            avail_mb = psutil.virtual_memory().available / (1024 * 1024)

        if avail_mb < 350:
            # Extreme memory pressure (< 350 MB): unload inactive models, never unload the model we are about to invoke
            is_embedding_op = "embedding" in (operation or "").lower()
            try:
                from backend.ollama_runtime.client import ollama_client
                from backend.config import config
                import gc
                # Always prefer reclaiming unused local LLM weights first
                ollama_client.unload_model(config.llm_model)
                if not is_embedding_op:
                    ollama_client.unload_model(config.embedding_model)
                gc.collect()
                avail_mb = psutil.virtual_memory().available / (1024 * 1024)
            except Exception:
                pass

        if avail_mb < self.min_free_mb:
            raise MemoryThresholdError(
                f"Critical memory floor reached: only {avail_mb:.1f} MB available (min: {self.min_free_mb} MB)."
            )

    def reclaim_memory(self):
        """Proactively reclaims memory by collecting garbage and unloading idle models if memory is critically tight."""
        avail_mb = psutil.virtual_memory().available / (1024 * 1024)
        if avail_mb >= 450:
            return
        import gc
        gc.collect()
        avail_mb = psutil.virtual_memory().available / (1024 * 1024)
        if avail_mb < 350:
            try:
                from backend.ollama_runtime.client import ollama_client
                from backend.config import config
                ollama_client.unload_model(config.llm_model)
                if avail_mb < 280:
                    ollama_client.unload_model(config.embedding_model)
                gc.collect()
            except Exception:
                pass

    @asynccontextmanager
    async def acquire_async(self, operation: str = "ollama_op", timeout: float = 120.0):
        """Asynchronous context manager acquiring exclusive access to Ollama hardware."""
        self._check_memory(operation=operation)
        t0 = time.perf_counter()
        acquired_async = False
        acquired_thread = False

        try:
            # 1. Acquire async lock with timeout
            try:
                await asyncio.wait_for(self._async_lock.acquire(), timeout=timeout)
                acquired_async = True
            except asyncio.TimeoutError:
                raise OllamaBusyError(
                    f"Timed out after {timeout}s waiting for Ollama hardware (busy with '{self.current_operation}')."
                )

            # 2. Acquire thread lock (in executor if needed)
            loop = asyncio.get_running_loop()
            acquired_thread = await loop.run_in_executor(
                None, lambda: self._thread_lock.acquire(timeout=timeout)
            )
            if not acquired_thread:
                raise OllamaBusyError(f"Thread lock acquisition timed out for '{operation}'.")

            self.current_operation = operation
            self.active_since = time.perf_counter()
            self.operations_count += 1

            yield self

        except Exception:
            self.failures_count += 1
            raise
        finally:
            if acquired_thread:
                self.last_duration_sec = round(time.perf_counter() - t0, 3)
                self.current_operation = None
                self.active_since = None
                self._thread_lock.release()
            if acquired_async:
                self._async_lock.release()

    @contextmanager
    def acquire_sync(self, operation: str = "ollama_op", timeout: float = 120.0):
        """Synchronous context manager for background workers and CLI threads."""
        self._check_memory(operation=operation)
        t0 = time.perf_counter()
        acquired = self._thread_lock.acquire(timeout=timeout)
        if not acquired:
            raise OllamaBusyError(
                f"Timed out after {timeout}s waiting for Ollama lock (currently '{self.current_operation}')."
            )

        try:
            self.current_operation = operation
            self.active_since = time.perf_counter()
            self.operations_count += 1
            yield self
        except Exception:
            self.failures_count += 1
            raise
        finally:
            self.last_duration_sec = round(time.perf_counter() - t0, 3)
            self.current_operation = None
            self.active_since = None
            self._thread_lock.release()

# Global singleton arbiter instance
arbiter = OllamaHardwareArbiter()
