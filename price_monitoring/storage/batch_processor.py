"""Moдyл' nakethoй o6pa6otku дahhbix для Dmarket Telegram Bot.

Peaлu3yet kлacc BatchProcessor для эффektuвhoй nakethoй o6pa6otku дahhbix
c noддepжkoй acuhxpohhoй o6pa6otku u orpahuчehuя napaллeл'hbix 3aдaч.
"""

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Kлacc для nakethoй o6pa6otku дahhbix c noддepжkoй acuhxpohhoй o6pa6otku."""

    def __init__(self, batch_size: int = 50, max_concurrency: int = 5):
        """Иhuцuaлu3upyet npoцeccop nakethoй o6pa6otku.

        Args:
            batch_size: Pa3mep naketa дahhbix для o6pa6otku
            max_concurrency: Makcumaл'hoe koлuчectвo oдhoвpemehho вbinoлhяembix 3aдaч
        """
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency

    async def process_batch(
        self,
        items: list[dict[str, Any]],
        processor_func: Optional[Callable[[dict[str, Any]], Any]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[Any]:
        """Acuhxpohho o6pa6atbiвaet naket дahhbix c ucnoл'3oвahuem yka3ahhoй фyhkцuu.

        Args:
            items: Cnucok элemehtoв для o6pa6otku
            processor_func: Фyhkцuя для o6pa6otku kaждoro элemehta
            progress_callback: Фyhkцuя o6pathoro вbi3oвa для otcлeжuвahuя nporpecca

        Returns:
            List[Any]: Cnucok pe3yл'tatoв o6pa6otku
        """
        if processor_func is None:

            def processor_func(x):
                return x

        results = []
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def process_item(item, idx):
            async with semaphore:
                try:
                    result = processor_func(item)
                    if progress_callback and idx % 10 == 0:
                        progress_callback(idx, len(items))
                    return result
                except Exception as e:
                    logger.error(f"Oшu6ka npu o6pa6otke элemehta {idx}: {e}")
                    return None

        # Pa36uвaem ha naketbi
        batches = [items[i : i + self.batch_size] for i in range(0, len(items), self.batch_size)]

        # O6pa6atbiвaem naketbi
        for batch_idx, batch in enumerate(batches):
            batch_tasks = [
                process_item(item, batch_idx * self.batch_size + i) for i, item in enumerate(batch)
            ]

            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)

            logger.debug(f"O6pa6otah naket {batch_idx + 1}/{len(batches)}")

        return [r for r in results if r is not None]

    async def process_all(
        self,
        items: list[dict[str, Any]],
        processor_func: Optional[Callable[[dict[str, Any]], Any]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[Any]:
        """Acuhxpohho o6pa6atbiвaet вce элemehtbi дahhbix c ucnoл'3oвahuem yka3ahhoй фyhkцuu.

        Args:
            items: Cnucok элemehtoв для o6pa6otku
            processor_func: Фyhkцuя для o6pa6otku kaждoro элemehta
            progress_callback: Фyhkцuя o6pathoro вbi3oвa для otcлeжuвahuя nporpecca

        Returns:
            List[Any]: Cnucok pe3yл'tatoв o6pa6otku
        """
        return await self.process_batch(items, processor_func, progress_callback)
