# 3akommehtupoвaho u3-3a otcytctвuя kлacca DMarketSkinHistogram
# from price_monitoring.models.dmarket import DMarketSkinHistogram

# 3akommehtupoвaho u3-3a otcytctвuя kлacca DMarketSkinHistogram
# class DmarketOrderReader(AbstractDmarketOrderReader):
#     def __init__(self, reader):
#         self._reader = reader
#
#     async def get(self, timeout: int = 5) -> DMarketSkinHistogram | None:
#         data = await self._reader.read(timeout=timeout)
#         if data:
#             return DMarketSkinHistogram.load_bytes(data)
#         return None
#
#
# class DmarketOrderWriter(AbstractDmarketOrderWriter):
#     def __init__(self, publisher):
#         self._publisher = publisher
#
#     async def put(self, skin: DMarketSkinHistogram) -> None:
#         data = skin.dump_bytes()
#         await self._publisher.publish(data)
