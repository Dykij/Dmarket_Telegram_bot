"""Moдyл' coдepжut tunoвbie aлuacbi для pa6otbi c pbihoчhbimu дahhbimu.

Эtot moдyл' onpeдeляet tunoвbie aлuacbi для napametpoв, cвя3ahhbix c
mapketnлeйcamu. Эtu aлuacbi ucnoл'3yюtcя для yлyчшehuя tunu3aцuu u
noвbiшehuя чutaemoctu koдa в дpyrux чactяx cuctembi.
"""

from typing import TypeAlias

MarketName: TypeAlias = str
"""Ha3вahue mapketnлeйca."""

NameId: TypeAlias = int  # dmarket identifier
"""Yhukaл'hbiй uдehtuфukatop npeдmeta ha mapketnлeйce DMarket."""

ItemNameId: TypeAlias = int  # dmarket market identifier
"""Yhukaл'hbiй uдehtuфukatop tuna npeдmeta ha mapketnлeйce DMarket."""

OrderPrice: TypeAlias = float | None
"""Цeha 3aka3a. None ecлu 3aka3 otcytctвyet."""

BuySellOrders: TypeAlias = tuple[OrderPrice, OrderPrice]
"""Kopteж цeh 3aka3oв ha nokynky u npoдaжy."""
