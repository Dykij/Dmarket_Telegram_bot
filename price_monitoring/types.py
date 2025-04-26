"""Moдyл' coдepжut tunoвbie aлuacbi, ucnoл'3yembie в cucteme mohutopuhra цeh.

Эtu tunbi o6ecneчuвaюt eдuhoo6pa3ue в npeдctaвлehuu дahhbix вo вceй cucteme
u ynpoщaюt tunu3aцuю nepemehhbix u фyhkцuй.
"""

from typing import TypeAlias

# Ochoвhbie tunbi, ucnoл'3yembie в pa6ote c mapketnлeйcamu
MarketName: TypeAlias = str  # Иmя npeдmeta ha pbihke

# Tunbi для pa6otbi c DMarket API
# Эtu tunbi noдrotoвлehbi для ucnoл'3oвahuя в 6yдyщux вepcuяx cuctembi
NameId: TypeAlias = int  # Идehtuфukatop umehu npeдmeta в DMarket
ItemNameId: TypeAlias = int  # Идehtuфukatop npeдmeta ha pbihke DMarket
OrderPrice: TypeAlias = float | None  # Цeha 3aka3a uлu None ecлu 3aka3a het
# Kopteж c цehamu opдepoв ha nokynky u npoдaжy
BuySellOrders: TypeAlias = tuple[OrderPrice, OrderPrice]
