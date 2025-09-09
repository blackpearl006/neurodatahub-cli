"""Performance optimizations and monitoring for NeuroDataHub CLI."""

import asyncio
import concurrent.futures
import functools
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue

from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

from .config import get_config
from .logging_config import get_logger, PerformanceTimer

console = Console()
logger = get_logger(__name__)


class MemoryCache:
    """Simple in-memory cache for frequently accessed data."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """Initialize cache.
        
        Args:
            max_size: Maximum number of items to cache
            ttl: Time to live in seconds
        """
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.ttl = ttl
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self._lock:
            if key not in self.cache:
                return None
            
            # Check if expired
            if time.time() - self.timestamps[key] > self.ttl:
                del self.cache[key]
                del self.timestamps[key]
                return None
            
            return self.cache[key]
    
    def set(self, key: str, value: Any):
        """Set item in cache."""
        with self._lock:
            # Clean expired items first
            self._clean_expired()
            
            # If at capacity, remove oldest item
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def _clean_expired(self):
        """Remove expired items."""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
            del self.timestamps[key]
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self.cache)


def cached(ttl: int = 3600):
    """Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
    """
    cache = MemoryCache(ttl=ttl)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Call function and cache result
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        wrapper._cache = cache  # Allow access to cache for testing
        return wrapper
    
    return decorator


def rate_limit(calls_per_second: float):
    """Decorator to rate limit function calls.
    
    Args:
        calls_per_second: Maximum calls per second allowed
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    lock = threading.Lock()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                elapsed = time.time() - last_called[0]
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                last_called[0] = time.time()
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class ParallelDownloadManager:
    """Manage parallel downloads with optimal concurrency."""
    
    def __init__(self, max_workers: Optional[int] = None):
        """Initialize parallel download manager.
        
        Args:
            max_workers: Maximum concurrent downloads
        """
        config = get_config()
        if max_workers is None:
            max_workers = config.get('general.concurrent_downloads', 4)
        
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_downloads = {}
        self._lock = threading.Lock()
    
    def submit_download(self, download_func: Callable, *args, **kwargs) -> concurrent.futures.Future:
        """Submit a download function for parallel execution.
        
        Args:
            download_func: Function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            Future object for the download
        """
        future = self.executor.submit(download_func, *args, **kwargs)
        
        with self._lock:
            self.active_downloads[future] = {
                'start_time': time.time(),
                'function': download_func.__name__ if hasattr(download_func, '__name__') else str(download_func)
            }
        
        return future
    
    def wait_for_downloads(self, futures: List[concurrent.futures.Future], 
                          timeout: Optional[float] = None) -> Dict[concurrent.futures.Future, Any]:
        """Wait for multiple downloads to complete.
        
        Args:
            futures: List of Future objects
            timeout: Maximum time to wait
            
        Returns:
            Dictionary mapping futures to their results
        """
        results = {}
        
        try:
            for future in as_completed(futures, timeout=timeout):
                try:
                    result = future.result()
                    results[future] = result
                    
                    # Clean up tracking
                    with self._lock:
                        if future in self.active_downloads:
                            download_info = self.active_downloads[future]
                            duration = time.time() - download_info['start_time']
                            logger.info(f"Download completed: {download_info['function']} in {duration:.1f}s")
                            del self.active_downloads[future]
                
                except Exception as e:
                    logger.error(f"Download failed: {e}")
                    results[future] = e
        
        except concurrent.futures.TimeoutError:
            logger.warning("Some downloads timed out")
        
        return results
    
    def shutdown(self, wait: bool = True):
        """Shutdown the executor."""
        self.executor.shutdown(wait=wait)


class ProgressiveDownloader:
    """Download with progressive enhancement and fallback."""
    
    def __init__(self):
        """Initialize progressive downloader."""
        self.strategies = [
            self._try_aria2c,
            self._try_aws_cli,
            self._try_requests
        ]
    
    def download(self, url: str, target_path: Path, **kwargs) -> bool:
        """Download using the best available method.
        
        Args:
            url: URL to download
            target_path: Target file path
            **kwargs: Additional parameters
            
        Returns:
            True if successful
        """
        for strategy in self.strategies:
            try:
                logger.info(f"Trying download strategy: {strategy.__name__}")
                if strategy(url, target_path, **kwargs):
                    return True
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue
        
        logger.error("All download strategies failed")
        return False
    
    def _try_aria2c(self, url: str, target_path: Path, **kwargs) -> bool:
        """Try downloading with aria2c."""
        from .utils import check_dependency, run_command
        
        if not check_dependency('aria2c'):
            raise Exception("aria2c not available")
        
        cmd = f'aria2c -x 16 -s 16 -j 16 "{url}" -o "{target_path.name}" -d "{target_path.parent}"'
        returncode, stdout, stderr = run_command(cmd, timeout=kwargs.get('timeout', 3600))
        
        return returncode == 0
    
    def _try_aws_cli(self, url: str, target_path: Path, **kwargs) -> bool:
        """Try downloading with AWS CLI."""
        from .utils import check_dependency, run_command
        
        if not check_dependency('aws') or not url.startswith('s3://'):
            raise Exception("AWS CLI not available or not S3 URL")
        
        cmd = f'aws s3 cp "{url}" "{target_path}" --no-sign-request'
        returncode, stdout, stderr = run_command(cmd, timeout=kwargs.get('timeout', 3600))
        
        return returncode == 0
    
    def _try_requests(self, url: str, target_path: Path, **kwargs) -> bool:
        """Try downloading with requests."""
        import requests
        from tqdm import tqdm
        
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(target_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=target_path.name) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        return True


class ResourceMonitor:
    """Monitor system resources during operations."""
    
    def __init__(self):
        """Initialize resource monitor."""
        self.monitoring = False
        self.monitor_thread = None
        self.stats = {
            'peak_memory': 0,
            'peak_cpu': 0,
            'disk_io': 0,
            'network_io': 0
        }
    
    def start_monitoring(self):
        """Start resource monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.debug("Resource monitoring started")
    
    def stop_monitoring(self) -> Dict:
        """Stop monitoring and return stats."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        
        logger.debug(f"Resource monitoring stopped. Peak memory: {self.stats['peak_memory']:.1f} MB")
        return self.stats.copy()
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            import psutil
            process = psutil.Process()
            
            while self.monitoring:
                # Memory usage
                memory_mb = process.memory_info().rss / (1024 * 1024)
                self.stats['peak_memory'] = max(self.stats['peak_memory'], memory_mb)
                
                # CPU usage
                cpu_percent = process.cpu_percent(interval=None)
                self.stats['peak_cpu'] = max(self.stats['peak_cpu'], cpu_percent)
                
                time.sleep(1.0)
                
        except ImportError:
            logger.debug("psutil not available for resource monitoring")
        except Exception as e:
            logger.warning(f"Resource monitoring error: {e}")


def optimize_dataset_loading():
    """Optimize dataset configuration loading."""
    # This could implement lazy loading, caching, or other optimizations
    pass


def batch_operation(operation_func: Callable, items: List[Any], 
                   batch_size: int = 10, max_workers: int = 4) -> List[Any]:
    """Execute operations in optimized batches.
    
    Args:
        operation_func: Function to apply to each item
        items: List of items to process
        batch_size: Size of each batch
        max_workers: Maximum concurrent workers
        
    Returns:
        List of results
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit batches
        futures = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            future = executor.submit(_process_batch, operation_func, batch)
            futures.append(future)
        
        # Collect results
        for future in as_completed(futures):
            try:
                batch_results = future.result()
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch operation failed: {e}")
    
    return results


def _process_batch(operation_func: Callable, items: List[Any]) -> List[Any]:
    """Process a single batch of items."""
    results = []
    for item in items:
        try:
            result = operation_func(item)
            results.append(result)
        except Exception as e:
            logger.error(f"Item processing failed: {e}")
            results.append(None)
    return results


class AsyncDownloadManager:
    """Asynchronous download manager for improved performance."""
    
    def __init__(self, max_concurrent: int = 10):
        """Initialize async download manager."""
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def download_multiple(self, urls_and_paths: List[Tuple[str, Path]]) -> List[bool]:
        """Download multiple files asynchronously."""
        tasks = []
        for url, path in urls_and_paths:
            task = self._download_with_semaphore(url, path)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to False
        return [result if isinstance(result, bool) else False for result in results]
    
    async def _download_with_semaphore(self, url: str, path: Path) -> bool:
        """Download with semaphore to limit concurrency."""
        async with self.semaphore:
            return await self._async_download(url, path)
    
    async def _async_download(self, url: str, path: Path) -> bool:
        """Async download implementation."""
        import aiohttp
        import aiofiles
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    
                    async with aiofiles.open(path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
            
            return True
            
        except Exception as e:
            logger.error(f"Async download failed for {url}: {e}")
            return False


# Global instances
_cache = MemoryCache()
_download_manager = None
_resource_monitor = ResourceMonitor()


def get_cache() -> MemoryCache:
    """Get global cache instance."""
    return _cache


def get_download_manager() -> ParallelDownloadManager:
    """Get global download manager instance."""
    global _download_manager
    if _download_manager is None:
        _download_manager = ParallelDownloadManager()
    return _download_manager


def get_resource_monitor() -> ResourceMonitor:
    """Get global resource monitor instance."""
    return _resource_monitor