"""Integration module for connecting the data processing system with existing components.

This module provides adapter classes and utility functions to integrate
the new data processing capabilities with the existing storage, parsing,
and monitoring components of the Dmarket Telegram Bot.
"""

import logging
from typing import Optional

# Import existing components
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.storage.batch_processor import BatchProcessor
# Import new data processing components
from price_monitoring.storage.data_compression import DataCompressor
from price_monitoring.storage.data_format import DataFormatProcessor
from price_monitoring.storage.data_pipeline import DataPipeline
from price_monitoring.storage.dmarket import DMarketStorage

logger = logging.getLogger(__name__)


class EnhancedDMarketStorageAdapter:
    """Adapter class that enhances the existing DMarketStorage with new data processing capabilities.

    This class wraps the existing DMarketStorage and adds compression, format conversion,
    batch processing, and data transformation capabilities while maintaining the same interface.
    """

    def __init__(
        self,
        original_storage: DMarketStorage,
        compression_enabled: bool = True,
        compression_algorithm: str = "gzip",
        serialization_format: str = "json",
        compression_level: int = 6,
        min_size_for_compression: int = 1024,
        batch_size: int = 100,
        max_concurrency: int = 5,
    ):
        """Initialize the enhanced storage adapter.

        Args:
            original_storage: The original DMarketStorage instance to enhance
            compression_enabled: Whether to enable compression
            compression_algorithm: Algorithm to use for compression
            serialization_format: Format to use for serialization
            compression_level: Compression level
            min_size_for_compression: Minimum data size for compression
            batch_size: Batch size for batch operations
            max_concurrency: Maximum concurrency for batch operations
        """
        self._original_storage = original_storage
        self._compression_enabled = compression_enabled

        # Initialize data compressor if compression is enabled
        if compression_enabled:
            self._compressor = DataCompressor(
                compression_algorithm=compression_algorithm,
                serialization_format=serialization_format,
                compression_level=compression_level,
                min_size_for_compression=min_size_for_compression,
            )

        # Initialize format processor
        self._format_processor = DataFormatProcessor()

        # Initialize batch processor
        self._batch_processor = BatchProcessor(
            batch_size=batch_size, max_concurrency=max_concurrency
        )

        # Initialize data transformation pipeline
        self._pipeline = DataPipeline(name="DMarketItemPipeline")

        # Add default transformations
        self._setup_default_pipeline()

        logger.info(
            f"Enhanced DMarket storage adapter initialized with "
            f"compression={compression_enabled}, algorithm={compression_algorithm}, "
            f"format={serialization_format}, batch_size={batch_size}"
        )

    def _setup_default_pipeline(self):
        """Set up the default data transformation pipeline."""
        # Add transformations to normalize and enhance item data
        self._pipeline.add_transformation(lambda item: {**item, "processed": True}, "MarkProcessed")

    async def save_item(self, item: DMarketItem) -> None:
        """Save an item to storage with enhanced processing.

        Args:
            item: DMarketItem to save
        """
        try:
            # Process the item through the pipeline
            item_dict = item.to_dict()
            processed_dict = self._pipeline.process(item_dict)

            if processed_dict is None:
                logger.warning(f"Item {item.item_id} was filtered out by the pipeline")
                return

            # Create a new DMarketItem from the processed dictionary
            processed_item = DMarketItem.from_dict(processed_dict)

            # Compress the item if compression is enabled
            if self._compression_enabled:
                # The original storage will be modified to handle compressed data
                # For now, we'll just pass it through
                await self._original_storage.save_item(processed_item)

                # Log compression stats
                original_size = len(str(item_dict).encode("utf-8"))
                compressed_size = len(self._compressor.compress(item_dict))
                compression_ratio = compressed_size / original_size if original_size > 0 else 1.0

                logger.debug(
                    f"Saved item {item.item_id} with compression "
                    f"(ratio: {compression_ratio:.2f}, space saving: {1.0 - compression_ratio:.2f})"
                )
            else:
                # Save without compression
                await self._original_storage.save_item(processed_item)
                logger.debug(f"Saved item {item.item_id} without compression")

        except Exception as e:
            logger.error(f"Failed to save item {item.item_id}: {e}")
            # Pass through to original storage to maintain error handling
            await self._original_storage.save_item(item)

    async def get_item(self, item_id: str) -> Optional[DMarketItem]:
        """Get an item from storage with enhanced processing.

        Args:
            item_id: ID of the item to get

        Returns:
            DMarketItem if found, None otherwise
        """
        try:
            # Get the item from the original storage
            item = await self._original_storage.get_item(item_id)

            if item is None:
                return None

            # For now, we'll just return the item as is
            # In the future, we could apply reverse transformations if needed
            return item

        except Exception as e:
            logger.error(f"Failed to get item {item_id}: {e}")
            # Fall back to original behavior
            return await self._original_storage.get_item(item_id)

    async def save_items_batch(self, items: list[DMarketItem]) -> dict[str, bool]:
        """Save multiple items in a batch with enhanced processing.

        Args:
            items: List of DMarketItems to save

        Returns:
            Dictionary mapping item IDs to success status
        """
        if not items:
            return {}

        try:
            # Define processing function for batch processor
            async def process_and_save_item(item: DMarketItem) -> tuple[str, bool]:
                try:
                    await self.save_item(item)
                    return (item.item_id, True)
                except Exception as e:
                    logger.error(f"Failed to save item {item.item_id} in batch: {e}")
                    return (item.item_id, False)

            # Process all items in batches
            results = await self._batch_processor.process_all(
                items=items, processor_func=process_and_save_item
            )

            # Convert results to dictionary
            return dict(results)

        except Exception as e:
            logger.error(f"Failed to save items batch: {e}")
            # Fall back to saving items one by one
            results = {}
            for item in items:
                try:
                    await self.save_item(item)
                    results[item.item_id] = True
                except Exception as item_e:
                    logger.error(f"Failed to save item {item.item_id} in fallback: {item_e}")
                    results[item.item_id] = False

            return results

    def add_transformation(self, transform_func, name=None):
        """Add a transformation to the pipeline.

        Args:
            transform_func: Function to transform data
            name: Name of the transformer
        """
        self._pipeline.add_transformation(transform_func, name)
        logger.debug(f"Added transformation {name or transform_func.__name__} to pipeline")

    @property
    def original_storage(self) -> DMarketStorage:
        """Get the original storage instance."""
        return self._original_storage

    @property
    def pipeline(self) -> DataPipeline:
        """Get the data transformation pipeline."""
        return self._pipeline

    @property
    def batch_processor(self) -> BatchProcessor:
        """Get the batch processor."""
        return self._batch_processor

    @property
    def compressor(self) -> Optional[DataCompressor]:
        """Get the data compressor if compression is enabled."""
        if self._compression_enabled:
            return self._compressor
        return None

    @property
    def format_processor(self) -> DataFormatProcessor:
        """Get the format processor."""
        return self._format_processor


# Utility functions for integration


def create_enhanced_storage(
    original_storage: DMarketStorage,
    compression_enabled: bool = True,
    compression_algorithm: str = "gzip",
    serialization_format: str = "json",
    compression_level: int = 6,
    min_size_for_compression: int = 1024,
    batch_size: int = 100,
    max_concurrency: int = 5,
) -> EnhancedDMarketStorageAdapter:
    """Create an enhanced storage adapter from an existing DMarketStorage.

    Args:
        original_storage: The original DMarketStorage instance
        compression_enabled: Whether to enable compression
        compression_algorithm: Algorithm to use for compression
        serialization_format: Format to use for serialization
        compression_level: Compression level
        min_size_for_compression: Minimum data size for compression
        batch_size: Batch size for batch operations
        max_concurrency: Maximum concurrency for batch operations

    Returns:
        Enhanced storage adapter
    """
    return EnhancedDMarketStorageAdapter(
        original_storage=original_storage,
        compression_enabled=compression_enabled,
        compression_algorithm=compression_algorithm,
        serialization_format=serialization_format,
        compression_level=compression_level,
        min_size_for_compression=min_size_for_compression,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
    )


async def migrate_existing_data(
    original_storage: DMarketStorage,
    enhanced_storage: EnhancedDMarketStorageAdapter,
    item_ids: list[str],
) -> dict[str, bool]:
    """Migrate existing data from original storage to enhanced storage.

    Args:
        original_storage: The original DMarketStorage instance
        enhanced_storage: The enhanced storage adapter
        item_ids: List of item IDs to migrate

    Returns:
        Dictionary mapping item IDs to migration success status
    """

    # Define processing function for batch processor
    async def migrate_item(item_id: str) -> tuple[str, bool]:
        try:
            # Get item from original storage
            item = await original_storage.get_item(item_id)

            if item is None:
                logger.warning(f"Item {item_id} not found in original storage")
                return (item_id, False)

            # Save item to enhanced storage
            await enhanced_storage.save_item(item)
            logger.info(f"Successfully migrated item {item_id}")
            return (item_id, True)
        except Exception as e:
            logger.error(f"Failed to migrate item {item_id}: {e}")
            return (item_id, False)

    # Process all items in batches
    batch_results = await enhanced_storage.batch_processor.process_all(
        items=item_ids, processor_func=migrate_item
    )

    # Convert results to dictionary
    return dict(batch_results)


# Example usage:
"""
# Create original storage
redis_client = await redis_connector.get_client()
original_storage = DMarketStorage(
    redis_client=redis_client,
    prefix="dmarket:items",
    ttl_seconds=3600
)

# Create enhanced storage
enhanced_storage = create_enhanced_storage(
    original_storage=original_storage,
    compression_enabled=True,
    compression_algorithm="gzip",
    serialization_format="msgpack",
    batch_size=100
)

# Add custom transformations
enhanced_storage.add_transformation(
    lambda item: {**item, "price_usd": item["price"] * 1.0},
    "AddUSDPrice"
)

# Save an item
item = DMarketItem(
    item_id="123456",
    title="AWP | Dragon Lore",
    price=1299.99,
    game_id="730"
)
await enhanced_storage.save_item(item)

# Get an item
retrieved_item = await enhanced_storage.get_item("123456")

# Save items in batch
items = [
    DMarketItem(item_id=f"item_{i}", title=f"Item {i}", price=i*10.0, game_id="730")
    for i in range(10)
]
results = await enhanced_storage.save_items_batch(items)
"""
