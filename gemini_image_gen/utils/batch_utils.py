"""Batch processing utilities for parallel image generation"""

import asyncio
import concurrent.futures
import time
from typing import List, Dict, Optional, Callable, Any, Tuple
from PIL import Image
import threading

from ..config import get_settings


class BatchGenerationResult:
    """Container for batch generation results"""

    def __init__(self):
        self.success_images: List[Image.Image] = []
        self.success_texts: List[str] = []
        self.failed_indices: List[int] = []
        self.error_messages: List[str] = []
        self.total_time: float = 0.0
        self.successful_count: int = 0
        self.failed_count: int = 0

    def add_success(self, image: Image.Image, text: str):
        """Add a successful generation result"""
        self.success_images.append(image)
        self.success_texts.append(text)
        self.successful_count += 1

    def add_failure(self, index: int, error_msg: str):
        """Add a failed generation result"""
        self.failed_indices.append(index)
        self.error_messages.append(error_msg)
        self.failed_count += 1

    def get_summary(self) -> str:
        """Get a summary of the batch results"""
        total = self.successful_count + self.failed_count
        return f"成功: {self.successful_count}/{total} 枚, 時間: {self.total_time:.1f}秒"


class BatchProcessor:
    """Handles batch processing with parallel execution"""

    def __init__(self):
        self.settings = get_settings()
        self._progress_callback: Optional[Callable] = None
        self._cancel_flag = threading.Event()

    def set_progress_callback(self, callback: Callable[[float, str], None]):
        """Set callback for progress updates"""
        self._progress_callback = callback

    def cancel(self):
        """Cancel the current batch operation"""
        self._cancel_flag.set()

    def _update_progress(self, progress: float, description: str):
        """Update progress if callback is set"""
        if self._progress_callback:
            self._progress_callback(progress, description)

    async def run_batch_async(
        self,
        batch_size: int,
        generation_func: Callable[[], Tuple[Optional[Image.Image], str]],
        max_workers: Optional[int] = None
    ) -> BatchGenerationResult:
        """
        Run batch generation asynchronously

        Args:
            batch_size: Number of images to generate
            generation_func: Function that generates a single image
            max_workers: Maximum number of concurrent workers

        Returns:
            BatchGenerationResult with all results
        """
        if max_workers is None:
            max_workers = min(
                self.settings.max_concurrent_requests,
                batch_size
            )

        result = BatchGenerationResult()
        start_time = time.time()

        # Reset cancel flag
        self._cancel_flag.clear()

        try:
            self._update_progress(0.0, f"バッチ生成開始: {batch_size}枚")

            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(max_workers)

            async def generate_single(index: int) -> Tuple[int, Optional[Image.Image], str, Optional[str]]:
                """Generate a single image with error handling"""
                async with semaphore:
                    if self._cancel_flag.is_set():
                        return index, None, "", "キャンセルされました"

                    try:
                        # Run the blocking generation function in a thread pool
                        loop = asyncio.get_event_loop()
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = loop.run_in_executor(executor, generation_func)
                            image, text = await asyncio.wait_for(
                                future,
                                timeout=self.settings.batch_timeout_seconds / batch_size
                            )

                        self._update_progress(
                            (index + 1) / batch_size * 0.9,
                            f"生成中: {index + 1}/{batch_size}"
                        )

                        return index, image, text, None

                    except asyncio.TimeoutError:
                        return index, None, "", "タイムアウト"
                    except Exception as e:
                        return index, None, "", str(e)

            # Start all generation tasks
            tasks = [generate_single(i) for i in range(batch_size)]

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for task_result in results:
                if isinstance(task_result, Exception):
                    result.add_failure(-1, str(task_result))
                else:
                    index, image, text, error = task_result
                    if error or image is None:
                        result.add_failure(index, error or "不明なエラー")
                    else:
                        result.add_success(image, text)

            result.total_time = time.time() - start_time

            self._update_progress(1.0, result.get_summary())

        except Exception as e:
            result.add_failure(-1, f"バッチ処理エラー: {str(e)}")
            result.total_time = time.time() - start_time

        return result

    def run_batch_sync(
        self,
        batch_size: int,
        generation_func: Callable[[], Tuple[Optional[Image.Image], str]]
    ) -> BatchGenerationResult:
        """
        Run batch generation synchronously (sequential)

        Args:
            batch_size: Number of images to generate
            generation_func: Function that generates a single image

        Returns:
            BatchGenerationResult with all results
        """
        result = BatchGenerationResult()
        start_time = time.time()

        # Reset cancel flag
        self._cancel_flag.clear()

        try:
            self._update_progress(0.0, f"シーケンシャル生成開始: {batch_size}枚")

            for i in range(batch_size):
                if self._cancel_flag.is_set():
                    result.add_failure(i, "キャンセルされました")
                    break

                try:
                    self._update_progress(
                        i / batch_size,
                        f"生成中: {i + 1}/{batch_size}"
                    )

                    image, text = generation_func()

                    if image is None:
                        result.add_failure(i, "画像生成に失敗")
                    else:
                        result.add_success(image, text)

                except Exception as e:
                    result.add_failure(i, str(e))

            result.total_time = time.time() - start_time
            self._update_progress(1.0, result.get_summary())

        except Exception as e:
            result.add_failure(-1, f"バッチ処理エラー: {str(e)}")
            result.total_time = time.time() - start_time

        return result

    def run_batch(
        self,
        batch_size: int,
        generation_func: Callable[[], Tuple[Optional[Image.Image], str]],
        use_parallel: Optional[bool] = None
    ) -> BatchGenerationResult:
        """
        Run batch generation with automatic parallel/sequential selection

        Args:
            batch_size: Number of images to generate
            generation_func: Function that generates a single image
            use_parallel: Force parallel (True) or sequential (False). Auto-detect if None.

        Returns:
            BatchGenerationResult with all results
        """
        # Validate batch size
        if batch_size < 1:
            raise ValueError("バッチサイズは1以上である必要があります")

        if batch_size > self.settings.max_batch_size:
            raise ValueError(f"バッチサイズは{self.settings.max_batch_size}以下である必要があります")

        # Determine processing method
        if use_parallel is None:
            use_parallel = (
                self.settings.enable_parallel_generation and
                batch_size > 1
            )

        if use_parallel:
            # Run async batch in a new event loop
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self.run_batch_async(batch_size, generation_func)
                    )
                finally:
                    loop.close()
            except Exception as e:
                # Fallback to sequential if async fails
                self._update_progress(0.0, "並列処理に失敗、シーケンシャル処理にフォールバック")
                return self.run_batch_sync(batch_size, generation_func)
        else:
            return self.run_batch_sync(batch_size, generation_func)