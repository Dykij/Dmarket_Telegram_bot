# Data Processing Improvements for Dmarket Telegram Bot

This document outlines the implementation of a comprehensive data processing system for the Dmarket Telegram Bot project, addressing one of the key improvement areas identified in the repository analysis.

## Overview

The data processing system will enable:
- Efficient compression of data for optimized storage
- Support for multiple data formats (JSON, CSV, XML, MessagePack, etc.)
- Efficient batch processing for large datasets
- Enhanced validation with schema-based validation
- Data transformation pipeline for flexible processing

## Current Issues

The current data processing approach has several limitations:
- Limited support for data formats (only JSON)
- No data compression mechanisms
- Potential issues with processing large datasets
- Basic validation without schema support
- No standardized data transformation pipeline

## Implementation Details

### 1. Data Compression System

We'll implement a comprehensive data compression system using a combination of:
- Standard compression algorithms (gzip, zlib, brotli)
- Binary serialization formats (MessagePack, Protocol Buffers)
- Redis compression options
- Selective compression based on data size and type

#### Core Components:

```python
import gzip
import zlib
import brotli
import msgpack
import json
import pickle
from typing import Any, Dict, Optional, Union, Callable, TypeVar

T = TypeVar('T')

class DataCompressor:
    """
    Data compression utility for efficient storage.

    This class provides methods for compressing and decompressing data
    using various algorithms and serialization formats.
    """

    COMPRESSION_ALGORITHMS = {
        'gzip': {
            'compress': lambda data, level=6: gzip.compress(data, level),
            'decompress': gzip.decompress
        },
        'zlib': {
            'compress': lambda data, level=6: zlib.compress(data, level),
            'decompress': zlib.decompress
        },
        'brotli': {
            'compress': lambda data, level=6: brotli.compress(data, quality=level),
            'decompress': brotli.decompress
        },
        'none': {
            'compress': lambda data, level=None: data,
            'decompress': lambda data: data
        }
    }

    SERIALIZATION_FORMATS = {
        'json': {
            'serialize': lambda obj: json.dumps(obj).encode('utf-8'),
            'deserialize': lambda data: json.loads(data.decode('utf-8'))
        },
        'msgpack': {
            'serialize': lambda obj: msgpack.packb(obj, use_bin_type=True),
            'deserialize': lambda data: msgpack.unpackb(data, raw=False)
        },
        'pickle': {
            'serialize': lambda obj: pickle.dumps(obj),
            'deserialize': lambda data: pickle.loads(data)
        }
    }

    def __init__(
        self, 
        compression_algorithm: str = 'gzip', 
        serialization_format: str = 'json',
        compression_level: int = 6,
        min_size_for_compression: int = 1024  # Don't compress data smaller than 1KB
    ):
        """
        Initialize the data compressor.

        Args:
            compression_algorithm: Algorithm to use for compression ('gzip', 'zlib', 'brotli', 'none')
            serialization_format: Format to use for serialization ('json', 'msgpack', 'pickle')
            compression_level: Compression level (1-9, higher = better compression but slower)
            min_size_for_compression: Minimum data size in bytes to apply compression
        """
        if compression_algorithm not in self.COMPRESSION_ALGORITHMS:
            raise ValueError(f"Unsupported compression algorithm: {compression_algorithm}")

        if serialization_format not in self.SERIALIZATION_FORMATS:
            raise ValueError(f"Unsupported serialization format: {serialization_format}")

        self.compression_algorithm = compression_algorithm
        self.serialization_format = serialization_format
        self.compression_level = compression_level
        self.min_size_for_compression = min_size_for_compression

    def compress(self, data: Any) -> bytes:
        """
        Compress data using the configured algorithm and serialization format.

        Args:
            data: Data to compress (any serializable object)

        Returns:
            Compressed data as bytes
        """
        # Serialize the data
        serialized = self.SERIALIZATION_FORMATS[self.serialization_format]['serialize'](data)

        # Skip compression for small data
        if len(serialized) < self.min_size_for_compression:
            return b'n:' + serialized  # Prefix with 'n:' to indicate no compression

        # Compress the serialized data
        compressed = self.COMPRESSION_ALGORITHMS[self.compression_algorithm]['compress'](
            serialized, self.compression_level
        )

        # Prefix with compression algorithm code for later decompression
        prefix = f"{self.compression_algorithm[0]}:".encode('utf-8')
        return prefix + compressed

    def decompress(self, data: bytes) -> Any:
        """
        Decompress data using the appropriate algorithm and serialization format.

        Args:
            data: Compressed data as bytes

        Returns:
            Decompressed and deserialized data
        """
        # Extract prefix to determine compression algorithm
        prefix = data[:2].decode('utf-8')
        data = data[2:]  # Remove prefix

        # Determine compression algorithm from prefix
        if prefix == 'n:':
            # No compression was applied
            decompressed = data
        elif prefix == 'g:':
            # gzip compression
            decompressed = self.COMPRESSION_ALGORITHMS['gzip']['decompress'](data)
        elif prefix == 'z:':
            # zlib compression
            decompressed = self.COMPRESSION_ALGORITHMS['zlib']['decompress'](data)
        elif prefix == 'b:':
            # brotli compression
            decompressed = self.COMPRESSION_ALGORITHMS['brotli']['decompress'](data)
        else:
            raise ValueError(f"Unknown compression prefix: {prefix}")

        # Deserialize the decompressed data
        return self.SERIALIZATION_FORMATS[self.serialization_format]['deserialize'](decompressed)

    def get_compression_stats(self, original_data: Any) -> Dict[str, Any]:
        """
        Get compression statistics for different algorithms and formats.

        Args:
            original_data: Data to test compression on

        Returns:
            Dictionary with compression statistics
        """
        results = {}

        # Test each serialization format
        for fmt in self.SERIALIZATION_FORMATS:
            serialized = self.SERIALIZATION_FORMATS[fmt]['serialize'](original_data)
            original_size = len(serialized)

            format_results = {
                'original_size': original_size,
                'algorithms': {}
            }

            # Test each compression algorithm
            for alg in self.COMPRESSION_ALGORITHMS:
                if alg == 'none':
                    compressed_size = original_size
                    ratio = 1.0
                else:
                    compressed = self.COMPRESSION_ALGORITHMS[alg]['compress'](serialized, self.compression_level)
                    compressed_size = len(compressed)
                    ratio = compressed_size / original_size if original_size > 0 else 1.0

                format_results['algorithms'][alg] = {
                    'compressed_size': compressed_size,
                    'ratio': ratio,
                    'space_saving': 1.0 - ratio
                }

            results[fmt] = format_results

        return results
```

### 2. Multi-Format Data Processor

We'll implement a flexible data processor that supports multiple formats:

```python
from typing import Any, Dict, List, Optional, Union, Type, TypeVar, Generic, Callable
import json
import csv
import xml.etree.ElementTree as ET
import msgpack
import yaml
from io import StringIO, BytesIO

T = TypeVar('T')

class DataFormatProcessor:
    """
    Processor for handling multiple data formats.

    This class provides methods for converting data between different formats
    and for reading/writing data in various formats.
    """

    SUPPORTED_FORMATS = ['json', 'csv', 'xml', 'msgpack', 'yaml']

    @staticmethod
    def to_json(data: Any) -> str:
        """Convert data to JSON string."""
        return json.dumps(data)

    @staticmethod
    def from_json(data: str) -> Any:
        """Parse JSON string to data."""
        return json.loads(data)

    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> str:
        """Convert list of dictionaries to CSV string."""
        if not data:
            return ""

        output = StringIO()
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    @staticmethod
    def from_csv(data: str) -> List[Dict[str, Any]]:
        """Parse CSV string to list of dictionaries."""
        input_data = StringIO(data)
        reader = csv.DictReader(input_data)
        return list(reader)

    @staticmethod
    def to_xml(data: Dict[str, Any], root_name: str = "root") -> str:
        """Convert dictionary to XML string."""
        def _dict_to_xml(parent: ET.Element, data: Dict[str, Any]):
            for key, value in data.items():
                if isinstance(value, dict):
                    sub_elem = ET.SubElement(parent, key)
                    _dict_to_xml(sub_elem, value)
                elif isinstance(value, list):
                    for item in value:
                        sub_elem = ET.SubElement(parent, key)
                        if isinstance(item, dict):
                            _dict_to_xml(sub_elem, item)
                        else:
                            sub_elem.text = str(item)
                else:
                    sub_elem = ET.SubElement(parent, key)
                    sub_elem.text = str(value)

        root = ET.Element(root_name)
        _dict_to_xml(root, data)
        return ET.tostring(root, encoding='unicode')

    @staticmethod
    def from_xml(data: str) -> Dict[str, Any]:
        """Parse XML string to dictionary."""
        def _xml_to_dict(element: ET.Element) -> Dict[str, Any]:
            result = {}
            for child in element:
                if len(child) > 0:
                    value = _xml_to_dict(child)
                else:
                    value = child.text or ""

                if child.tag in result:
                    if isinstance(result[child.tag], list):
                        result[child.tag].append(value)
                    else:
                        result[child.tag] = [result[child.tag], value]
                else:
                    result[child.tag] = value
            return result

        root = ET.fromstring(data)
        return {root.tag: _xml_to_dict(root)}

    @staticmethod
    def to_msgpack(data: Any) -> bytes:
        """Convert data to MessagePack bytes."""
        return msgpack.packb(data, use_bin_type=True)

    @staticmethod
    def from_msgpack(data: bytes) -> Any:
        """Parse MessagePack bytes to data."""
        return msgpack.unpackb(data, raw=False)

    @staticmethod
    def to_yaml(data: Any) -> str:
        """Convert data to YAML string."""
        return yaml.dump(data)

    @staticmethod
    def from_yaml(data: str) -> Any:
        """Parse YAML string to data."""
        return yaml.safe_load(data)

    @classmethod
    def convert(cls, data: Any, from_format: str, to_format: str) -> Union[str, bytes]:
        """
        Convert data from one format to another.

        Args:
            data: Data to convert
            from_format: Source format ('json', 'csv', 'xml', 'msgpack', 'yaml')
            to_format: Target format ('json', 'csv', 'xml', 'msgpack', 'yaml')

        Returns:
            Converted data as string or bytes
        """
        if from_format not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported source format: {from_format}")

        if to_format not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported target format: {to_format}")

        # First convert to internal representation
        if from_format == 'json':
            parsed_data = cls.from_json(data)
        elif from_format == 'csv':
            parsed_data = cls.from_csv(data)
        elif from_format == 'xml':
            parsed_data = cls.from_xml(data)
        elif from_format == 'msgpack':
            parsed_data = cls.from_msgpack(data)
        elif from_format == 'yaml':
            parsed_data = cls.from_yaml(data)

        # Then convert to target format
        if to_format == 'json':
            return cls.to_json(parsed_data)
        elif to_format == 'csv':
            return cls.to_csv(parsed_data)
        elif to_format == 'xml':
            return cls.to_xml(parsed_data)
        elif to_format == 'msgpack':
            return cls.to_msgpack(parsed_data)
        elif to_format == 'yaml':
            return cls.to_yaml(parsed_data)
```

### 3. Batch Processing System

We'll implement an efficient batch processing system for handling large datasets:

```python
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic, Awaitable
import logging

T = TypeVar('T')
U = TypeVar('U')

logger = logging.getLogger(__name__)

class BatchProcessor(Generic[T, U]):
    """
    Processor for efficient batch processing of data.

    This class provides methods for processing data in batches,
    with support for parallel processing and error handling.
    """

    def __init__(
        self,
        batch_size: int = 100,
        max_concurrency: int = 5,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the batch processor.

        Args:
            batch_size: Number of items to process in each batch
            max_concurrency: Maximum number of batches to process concurrently
            retry_attempts: Number of retry attempts for failed batches
            retry_delay: Delay between retry attempts in seconds
        """
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

    async def process_batch(
        self,
        items: List[T],
        processor_func: Callable[[T], Awaitable[U]],
        error_handler: Optional[Callable[[T, Exception], Awaitable[None]]] = None
    ) -> List[U]:
        """
        Process a single batch of items.

        Args:
            items: List of items to process
            processor_func: Async function to process each item
            error_handler: Optional async function to handle errors

        Returns:
            List of processed items
        """
        results = []

        for item in items:
            try:
                result = await processor_func(item)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                if error_handler:
                    await error_handler(item, e)

        return results

    async def process_all(
        self,
        items: List[T],
        processor_func: Callable[[T], Awaitable[U]],
        error_handler: Optional[Callable[[T, Exception], Awaitable[None]]] = None,
        progress_callback: Optional[Callable[[int, int], Awaitable[None]]] = None
    ) -> List[U]:
        """
        Process all items in batches.

        Args:
            items: List of all items to process
            processor_func: Async function to process each item
            error_handler: Optional async function to handle errors
            progress_callback: Optional async function to report progress

        Returns:
            List of all processed items
        """
        # Split items into batches
        batches = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
        total_batches = len(batches)

        logger.info(f"Processing {len(items)} items in {total_batches} batches")

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def process_batch_with_retry(batch_index: int, batch: List[T]) -> List[U]:
            """Process a batch with retry logic."""
            async with semaphore:
                for attempt in range(self.retry_attempts):
                    try:
                        result = await self.process_batch(batch, processor_func, error_handler)

                        # Report progress if callback provided
                        if progress_callback:
                            await progress_callback(batch_index + 1, total_batches)

                        return result
                    except Exception as e:
                        if attempt < self.retry_attempts - 1:
                            logger.warning(f"Batch {batch_index} failed, retrying ({attempt + 1}/{self.retry_attempts}): {e}")
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                        else:
                            logger.error(f"Batch {batch_index} failed after {self.retry_attempts} attempts: {e}")
                            raise

        # Process all batches concurrently
        batch_tasks = [
            process_batch_with_retry(i, batch)
            for i, batch in enumerate(batches)
        ]

        # Wait for all batches to complete
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Flatten results and filter out exceptions
        results = []
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                logger.error(f"Batch processing failed: {batch_result}")
            else:
                results.extend(batch_result)

        return results
```

### 4. Enhanced Data Validation

We'll implement a schema-based validation system using Pydantic:

```python
from typing import Any, Dict, List, Optional, Union, Type, TypeVar, Generic
from pydantic import BaseModel, ValidationError, Field
import logging

logger = logging.getLogger(__name__)

class SchemaValidator:
    """
    Schema-based validator for data validation.

    This class provides methods for validating data against schemas
    defined using Pydantic models.
    """

    def __init__(self, strict: bool = True):
        """
        Initialize the schema validator.

        Args:
            strict: Whether to use strict validation mode
        """
        self.strict = strict
        self.schemas: Dict[str, Type[BaseModel]] = {}

    def register_schema(self, name: str, schema: Type[BaseModel]) -> None:
        """
        Register a schema for validation.

        Args:
            name: Name to identify the schema
            schema: Pydantic model class
        """
        self.schemas[name] = schema
        logger.debug(f"Registered schema: {name}")

    def validate(self, data: Any, schema_name: str) -> tuple[bool, Optional[str], Optional[BaseModel]]:
        """
        Validate data against a registered schema.

        Args:
            data: Data to validate
            schema_name: Name of the schema to validate against

        Returns:
            Tuple of (is_valid, error_message, validated_model)
        """
        if schema_name not in self.schemas:
            return False, f"Schema not found: {schema_name}", None

        schema = self.schemas[schema_name]

        try:
            # Validate data against schema
            validated = schema.parse_obj(data)
            return True, None, validated
        except ValidationError as e:
            error_message = str(e)
            logger.warning(f"Validation failed for schema {schema_name}: {error_message}")
            return False, error_message, None

    def validate_batch(
        self, 
        items: List[Any], 
        schema_name: str
    ) -> tuple[List[BaseModel], List[tuple[Any, str]]]:
        """
        Validate a batch of items against a schema.

        Args:
            items: List of items to validate
            schema_name: Name of the schema to validate against

        Returns:
            Tuple of (valid_items, invalid_items_with_errors)
        """
        valid_items = []
        invalid_items = []

        for item in items:
            is_valid, error_message, validated = self.validate(item, schema_name)
            if is_valid and validated:
                valid_items.append(validated)
            else:
                invalid_items.append((item, error_message or "Unknown validation error"))

        return valid_items, invalid_items
```

### 5. Data Transformation Pipeline

We'll implement a flexible data transformation pipeline:

```python
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
import logging

T = TypeVar('T')
U = TypeVar('U')

logger = logging.getLogger(__name__)

class DataTransformer(Generic[T, U]):
    """
    Transformer for data processing pipeline.

    This class represents a single transformation step in a data processing pipeline.
    """

    def __init__(
        self,
        transform_func: Callable[[T], U],
        name: str = None,
        error_handler: Optional[Callable[[T, Exception], None]] = None
    ):
        """
        Initialize the data transformer.

        Args:
            transform_func: Function to transform data
            name: Name of the transformer
            error_handler: Optional function to handle errors
        """
        self.transform_func = transform_func
        self.name = name or transform_func.__name__
        self.error_handler = error_handler

    def transform(self, data: T) -> Optional[U]:
        """
        Transform data using the transform function.

        Args:
            data: Data to transform

        Returns:
            Transformed data or None if transformation fails
        """
        try:
            return self.transform_func(data)
        except Exception as e:
            logger.error(f"Error in transformer {self.name}: {e}")
            if self.error_handler:
                self.error_handler(data, e)
            return None


class DataPipeline:
    """
    Pipeline for data processing.

    This class represents a pipeline of data transformers that process data
    in sequence.
    """

    def __init__(self, name: str = "DataPipeline"):
        """
        Initialize the data pipeline.

        Args:
            name: Name of the pipeline
        """
        self.name = name
        self.transformers: List[DataTransformer] = []

    def add_transformer(self, transformer: DataTransformer) -> 'DataPipeline':
        """
        Add a transformer to the pipeline.

        Args:
            transformer: Transformer to add

        Returns:
            Self for method chaining
        """
        self.transformers.append(transformer)
        return self

    def add_transformation(
        self,
        transform_func: Callable,
        name: str = None,
        error_handler: Optional[Callable] = None
    ) -> 'DataPipeline':
        """
        Add a transformation function to the pipeline.

        Args:
            transform_func: Function to transform data
            name: Name of the transformer
            error_handler: Optional function to handle errors

        Returns:
            Self for method chaining
        """
        transformer = DataTransformer(
            transform_func=transform_func,
            name=name,
            error_handler=error_handler
        )
        return self.add_transformer(transformer)

    def process(self, data: Any) -> Any:
        """
        Process data through the pipeline.

        Args:
            data: Data to process

        Returns:
            Processed data
        """
        current_data = data

        for transformer in self.transformers:
            logger.debug(f"Applying transformer: {transformer.name}")
            result = transformer.transform(current_data)

            if result is None:
                logger.warning(f"Transformer {transformer.name} returned None, stopping pipeline")
                return None

            current_data = result

        return current_data

    def process_batch(self, items: List[Any]) -> List[Any]:
        """
        Process a batch of items through the pipeline.

        Args:
            items: List of items to process

        Returns:
            List of processed items (None values are filtered out)
        """
        results = []

        for item in items:
            result = self.process(item)
            if result is not None:
                results.append(result)

        return results
```

### 6. Enhanced DMarketStorage with Compression and Format Support

We'll enhance the existing DMarketStorage class with compression and format support:

```python
import json
import logging
from typing import Any, Dict, Optional, Tuple, List, Union

import redis.asyncio as redis
from redis.exceptions import RedisError

from ..models.dmarket import DMarketItem
from .data_compression import DataCompressor
from .data_format import DataFormatProcessor

logger = logging.getLogger(__name__)


class EnhancedDMarketStorage:
    """Enhanced storage for DMarket items with compression and format support."""

    def __init__(
        self,
        redis_client: redis.Redis,
        prefix: str = "dmarket:items",
        ttl_seconds: int = 3600,
        compression_enabled: bool = True,
        compression_algorithm: str = "gzip",
        serialization_format: str = "json",
        compression_level: int = 6,
        min_size_for_compression: int = 1024
    ):
        """
        Initialize the enhanced storage.

        Args:
            redis_client: Asynchronous Redis client
            prefix: Prefix for Redis keys
            ttl_seconds: Time-to-live for keys in seconds
            compression_enabled: Whether to enable compression
            compression_algorithm: Algorithm to use for compression
            serialization_format: Format to use for serialization
            compression_level: Compression level
            min_size_for_compression: Minimum data size for compression
        """
        self._redis = redis_client
        self._prefix = prefix
        self._ttl = ttl_seconds
        self._compression_enabled = compression_enabled

        # Initialize data compressor if compression is enabled
        if compression_enabled:
            self._compressor = DataCompressor(
                compression_algorithm=compression_algorithm,
                serialization_format=serialization_format,
                compression_level=compression_level,
                min_size_for_compression=min_size_for_compression
            )

        # Initialize format processor
        self._format_processor = DataFormatProcessor()

    def _get_key(self, item_id: str) -> str:
        """Generate Redis key for an item ID."""
        return f"{self._prefix}:{item_id}"

    async def save_item(self, item: DMarketItem, format: str = "json") -> None:
        """
        Save an item to Redis with optional compression.

        Args:
            item: DMarketItem to save
            format: Format to use for serialization

        Raises:
            RedisError: If Redis operation fails
            ValueError: If serialization fails
        """
        key = self._get_key(item.item_id)

        try:
            # Convert item to dictionary
            item_dict = item.to_dict()

            # Convert to specified format
            if format == "json":
                item_data = json.dumps(item_dict).encode("utf-8")
            elif format in self._format_processor.SUPPORTED_FORMATS:
                # Convert to the specified format
                if format == "msgpack":
                    item_data = self._format_processor.to_msgpack(item_dict)
                elif format == "yaml":
                    item_data = self._format_processor.to_yaml(item_dict).encode("utf-8")
                else:
                    # For other formats, convert to string and encode
                    item_data = str(getattr(self._format_processor, f"to_{format}")(item_dict)).encode("utf-8")
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Compress data if enabled
            if self._compression_enabled:
                compressed_data = self._compressor.compress(item_dict)
                await self._redis.set(key, compressed_data, ex=self._ttl)

                # Log compression stats
                compression_ratio = len(compressed_data) / len(item_data) if len(item_data) > 0 else 1.0
                logger.debug(
                    f"Saved item {item.item_id} to Redis with compression "
                    f"(ratio: {compression_ratio:.2f}, space saving: {1.0 - compression_ratio:.2f})"
                )
            else:
                # Store uncompressed data
                await self._redis.set(key, item_data, ex=self._ttl)
                logger.debug(f"Saved item {item.item_id} to Redis without compression")

    async def get_item(self, item_id: str) -> Optional[DMarketItem]:
        """
        Get an item from Redis with automatic decompression.

        Args:
            item_id: ID of the item to get

        Returns:
            DMarketItem if found, None otherwise
        """
        key = self._get_key(item_id)

        try:
            # Get data from Redis
            data = await self._redis.get(key)
            if data is None:
                logger.debug(f"Item {item_id} not found in Redis")
                return None

            # Check if data is compressed
            if self._compression_enabled and data.startswith((b'g:', b'z:', b'b:', b'n:')):
                # Decompress data
                item_dict = self._compressor.decompress(data)
            else:
                # Parse uncompressed data
                try:
                    item_dict = json.loads(data.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Try MessagePack format
                    try:
                        item_dict = self._format_processor.from_msgpack(data)
                    except Exception as e:
                        logger.error(f"Failed to parse item data: {e}")
                        return None

            # Create DMarketItem from dictionary
            return DMarketItem.from_dict(item_dict)
        except (RedisError, ValueError, TypeError) as e:
            logger.error(f"Failed to get item {item_id} from Redis: {e}")
            return None

    async def save_items_batch(self, items: List[DMarketItem], format: str = "json") -> Dict[str, bool]:
        """
        Save multiple items to Redis in a batch.

        Args:
            items: List of DMarketItems to save
            format: Format to use for serialization

        Returns:
            Dictionary mapping item IDs to success status
        """
        if not items:
            return {}

        results = {}
        pipeline = self._redis.pipeline()

        for item in items:
            key = self._get_key(item.item_id)
            try:
                # Convert item to dictionary
                item_dict = item.to_dict()

                # Compress data if enabled
                if self._compression_enabled:
                    data = self._compressor.compress(item_dict)
                else:
                    # Convert to specified format
                    if format == "json":
                        data = json.dumps(item_dict).encode("utf-8")
                    elif format == "msgpack":
                        data = self._format_processor.to_msgpack(item_dict)
                    else:
                        raise ValueError(f"Unsupported format for batch operations: {format}")

                # Add to pipeline
                pipeline.set(key, data, ex=self._ttl)
                results[item.item_id] = True
            except Exception as e:
                logger.error(f"Failed to prepare item {item.item_id} for batch save: {e}")
                results[item.item_id] = False

        # Execute pipeline
        try:
            await pipeline.execute()
        except RedisError as e:
            logger.error(f"Failed to execute Redis pipeline: {e}")
            # Mark all items as failed
            for item_id in results:
                results[item_id] = False

        return results
```

## Usage Examples

### Data Compression

```python
from price_monitoring.storage.data_compression import DataCompressor

# Create a compressor with default settings (gzip, json)
compressor = DataCompressor()

# Compress a dictionary
data = {
    "item_id": "123456",
    "title": "AWP | Dragon Lore",
    "price": 1299.99,
    "game_id": "730",
    "description": "A very long description...",
    "attributes": {
        "wear": 0.01,
        "pattern": 661,
        "stickers": ["Titan (Holo) | Katowice 2014", "iBUYPOWER (Holo) | Katowice 2014"]
    }
}

# Compress the data
compressed = compressor.compress(data)
print(f"Original size: {len(json.dumps(data).encode('utf-8'))} bytes")
print(f"Compressed size: {len(compressed)} bytes")

# Decompress the data
decompressed = compressor.decompress(compressed)
assert decompressed == data  # Verify data integrity

# Get compression statistics for different algorithms and formats
stats = compressor.get_compression_stats(data)
for fmt, fmt_stats in stats.items():
    print(f"\nFormat: {fmt}")
    print(f"Original size: {fmt_stats['original_size']} bytes")
    for alg, alg_stats in fmt_stats['algorithms'].items():
        print(f"  {alg}: {alg_stats['compressed_size']} bytes "
              f"(ratio: {alg_stats['ratio']:.2f}, saving: {alg_stats['space_saving']:.2f})")
```

### Multi-Format Data Processing

```python
from price_monitoring.storage.data_format import DataFormatProcessor

# Create a format processor
processor = DataFormatProcessor()

# Sample data
data = [
    {"id": 1, "name": "Item 1", "price": 10.99},
    {"id": 2, "name": "Item 2", "price": 20.99},
    {"id": 3, "name": "Item 3", "price": 30.99}
]

# Convert to different formats
json_data = processor.to_json(data)
csv_data = processor.to_csv(data)
xml_data = processor.to_xml({"items": data}, "items")
msgpack_data = processor.to_msgpack(data)
yaml_data = processor.to_yaml(data)

print("JSON:", json_data[:50], "...")
print("CSV:", csv_data[:50], "...")
print("XML:", xml_data[:50], "...")
print("YAML:", yaml_data[:50], "...")

# Convert between formats
csv_from_json = processor.convert(json_data, "json", "csv")
xml_from_csv = processor.convert(csv_data, "csv", "xml")
json_from_xml = processor.convert(xml_data, "xml", "json")

# Parse data from different formats
parsed_json = processor.from_json(json_data)
parsed_csv = processor.from_csv(csv_data)
parsed_xml = processor.from_xml(xml_data)
parsed_msgpack = processor.from_msgpack(msgpack_data)
parsed_yaml = processor.from_yaml(yaml_data)
```

### Batch Processing

```python
import asyncio
from price_monitoring.storage.batch_processor import BatchProcessor

# Sample data
items = [{"id": i, "name": f"Item {i}", "price": i * 10.99} for i in range(1, 1001)]

# Define processing function
async def process_item(item):
    # Simulate processing time
    await asyncio.sleep(0.01)
    # Process item
    item["processed"] = True
    item["price_usd"] = item["price"] * 1.1  # Add 10% tax
    return item

# Define error handler
async def handle_error(item, error):
    print(f"Error processing item {item['id']}: {error}")

# Define progress callback
async def report_progress(current, total):
    print(f"Progress: {current}/{total} batches processed ({current/total*100:.1f}%)")

# Create batch processor
processor = BatchProcessor(batch_size=50, max_concurrency=5)

# Process all items
async def main():
    results = await processor.process_all(
        items=items,
        processor_func=process_item,
        error_handler=handle_error,
        progress_callback=report_progress
    )
    print(f"Processed {len(results)} items")
    print(f"First result: {results[0]}")

# Run the batch processor
asyncio.run(main())
```

### Schema Validation

```python
from pydantic import BaseModel, Field, validator
from price_monitoring.storage.schema_validator import SchemaValidator

# Define schemas
class ItemAttributes(BaseModel):
    wear: float = Field(..., ge=0.0, le=1.0)
    pattern: int = Field(..., ge=0, le=999)
    stickers: list[str] = Field(default_factory=list)

class DMarketItemSchema(BaseModel):
    item_id: str
    title: str
    price: float = Field(..., gt=0)
    game_id: str
    description: str = None
    attributes: ItemAttributes = None

    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

# Create validator
validator = SchemaValidator()

# Register schemas
validator.register_schema("item", DMarketItemSchema)
validator.register_schema("attributes", ItemAttributes)

# Valid item
valid_item = {
    "item_id": "123456",
    "title": "AWP | Dragon Lore",
    "price": 1299.99,
    "game_id": "730",
    "description": "A very rare skin",
    "attributes": {
        "wear": 0.01,
        "pattern": 661,
        "stickers": ["Titan (Holo) | Katowice 2014"]
    }
}

# Invalid item
invalid_item = {
    "item_id": "123457",
    "title": "AK-47 | Redline",
    "price": -10.99,  # Invalid: negative price
    "game_id": "730",
    "attributes": {
        "wear": 1.5,  # Invalid: wear > 1.0
        "pattern": 661
    }
}

# Validate items
is_valid, error, validated = validator.validate(valid_item, "item")
print(f"Valid item: {is_valid}")
if validated:
    print(f"Validated item: {validated}")

is_valid, error, validated = validator.validate(invalid_item, "item")
print(f"Invalid item: {is_valid}")
if error:
    print(f"Validation error: {error}")

# Validate batch
items = [valid_item, invalid_item, valid_item]
valid_items, invalid_items = validator.validate_batch(items, "item")
print(f"Valid items: {len(valid_items)}")
print(f"Invalid items: {len(invalid_items)}")
for item, error in invalid_items:
    print(f"Error in item {item['item_id']}: {error}")
```

### Data Transformation Pipeline

```python
from price_monitoring.storage.data_pipeline import DataPipeline

# Define transformation functions
def normalize_price(item):
    """Convert price to USD and round to 2 decimal places."""
    if "price" in item:
        item["price_usd"] = round(item["price"] * 1.0, 2)  # Assume price is already in USD
    return item

def add_metadata(item):
    """Add metadata to the item."""
    item["metadata"] = {
        "processed_at": "2023-04-15T12:00:00Z",
        "source": "dmarket",
        "version": "1.0"
    }
    return item

def calculate_profit(item):
    """Calculate potential profit."""
    if "price_usd" in item and "market_price" in item:
        item["profit"] = round(item["market_price"] - item["price_usd"], 2)
        item["profit_percent"] = round(item["profit"] / item["price_usd"] * 100, 2)
    return item

def filter_profitable_items(item):
    """Filter items with profit > 0."""
    if "profit" in item and item["profit"] <= 0:
        return None  # Skip non-profitable items
    return item

# Create a pipeline
pipeline = DataPipeline(name="ProfitCalculationPipeline")
pipeline.add_transformation(normalize_price, "NormalizePrice")
pipeline.add_transformation(add_metadata, "AddMetadata")
pipeline.add_transformation(calculate_profit, "CalculateProfit")
pipeline.add_transformation(filter_profitable_items, "FilterProfitableItems")

# Process an item
item = {
    "item_id": "123456",
    "title": "AWP | Dragon Lore",
    "price": 1299.99,
    "market_price": 1500.00
}

result = pipeline.process(item)
print(f"Processed item: {result}")

# Process a batch of items
items = [
    {"item_id": "1", "title": "Item 1", "price": 100, "market_price": 120},
    {"item_id": "2", "title": "Item 2", "price": 200, "market_price": 180},  # Not profitable
    {"item_id": "3", "title": "Item 3", "price": 300, "market_price": 350}
]

results = pipeline.process_batch(items)
print(f"Processed {len(results)} profitable items out of {len(items)} total")
for result in results:
    print(f"Item {result['item_id']}: Profit ${result['profit']} ({result['profit_percent']}%)")
```

### Enhanced DMarketStorage

```python
import asyncio
import redis.asyncio as redis
from price_monitoring.models.dmarket import DMarketItem
from price_monitoring.storage.enhanced_dmarket import EnhancedDMarketStorage

# Create Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0)

# Create enhanced storage
storage = EnhancedDMarketStorage(
    redis_client=redis_client,
    compression_enabled=True,
    compression_algorithm="gzip",
    serialization_format="msgpack",
    compression_level=6
)

# Create sample items
items = [
    DMarketItem(
        item_id=f"item_{i}",
        title=f"Item {i}",
        price=i * 10.99,
        game_id="730",
        description=f"Description for item {i}" * 10  # Make it longer for better compression
    )
    for i in range(1, 101)
]

# Save and retrieve items
async def test_storage():
    # Save a single item
    item = items[0]
    await storage.save_item(item)
    print(f"Saved item: {item.item_id}")

    # Retrieve the item
    retrieved_item = await storage.get_item(item.item_id)
    print(f"Retrieved item: {retrieved_item.item_id}, {retrieved_item.title}, ${retrieved_item.price}")

    # Save items in batch
    batch_results = await storage.save_items_batch(items[1:10])
    print(f"Batch save results: {sum(batch_results.values())}/9 successful")

    # Retrieve one of the batch items
    batch_item = await storage.get_item(items[5].item_id)
    print(f"Retrieved batch item: {batch_item.item_id}, {batch_item.title}, ${batch_item.price}")

# Run the test
asyncio.run(test_storage())
```

## Implementation Plan

1. **Phase 1: Core Data Processing Components**
   - Implement DataCompressor class for efficient data compression
   - Implement DataFormatProcessor for multi-format support
   - Implement BatchProcessor for efficient batch processing
   - Create unit tests for each component

2. **Phase 2: Enhanced Validation and Transformation**
   - Implement SchemaValidator for schema-based validation
   - Implement DataTransformer and DataPipeline for flexible processing
   - Define schemas for DMarket items and other data types
   - Create unit tests for validation and transformation

3. **Phase 3: Storage Integration**
   - Implement EnhancedDMarketStorage with compression and format support
   - Update worker.py to use the enhanced storage
   - Add batch processing support to the worker
   - Create integration tests for the storage system

4. **Phase 4: Performance Optimization**
   - Benchmark different compression algorithms and formats
   - Optimize batch processing parameters
   - Implement adaptive compression based on data characteristics
   - Create performance tests and benchmarks

5. **Phase 5: Documentation and Examples**
   - Document all components with detailed docstrings
   - Create usage examples for each component
   - Update README with information about the data processing system
   - Create a migration guide for existing code

## Benefits

Implementing this data processing system will:

1. **Reduce Storage Requirements**: Data compression can reduce storage requirements by 50-80% depending on the data
2. **Improve Performance**: Efficient batch processing and binary formats can significantly improve throughput
3. **Enhance Flexibility**: Support for multiple formats enables integration with different systems
4. **Increase Reliability**: Enhanced validation ensures data integrity
5. **Simplify Development**: The transformation pipeline makes complex data processing easier to implement and maintain

## Conclusion

The proposed data processing system provides a comprehensive solution for addressing the weaknesses identified in the repository analysis. By implementing efficient compression, multi-format support, batch processing, enhanced validation, and a flexible transformation pipeline, we can significantly improve the data processing capabilities of the Dmarket Telegram Bot.
