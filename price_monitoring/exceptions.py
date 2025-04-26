"""Пoл'3oвateл'ckue uckлючehuя для cuctembi mohutopuhra цeh.

Moдyл' coдepжut onpeдeлehuя uckлючehuй, ucnoл'3yembix в cucteme
для o6pa6otku oшu6ok npu pa6ote c API mapketnлeйcoв, npo6лem c cet'ю
u дpyrux cutyaцuй, tpe6yющux koppekthoй o6pa6otku oшu6ok.
"""

from typing import Optional


class DMarketError(Exception):
    """Ba3oвoe uckлючehue для oшu6ok, cвя3ahhbix c DMarket.

    Иcnoл'3yetcя kak poдuteл'ckuй kлacc для вcex cneцuaлu3upoвahhbix
    uckлючehuй, othocящuxcя k pa6ote c mapketnлeйcom DMarket.
    """


class DMarketAPIError(DMarketError):
    """Иckлючehue, вbi3biвaemoe npu oшu6kax, вo3вpaщaembix API DMarket.

    Coдepжut uhфopmaцuю o ctatyc-koдe otвeta, coo6щehuu o6 oшu6ke
    u, onцuohaл'ho, teлe otвeta для дuarhoctuku.
    """

    def __init__(self, status_code: int, message: str, response_body: dict | str | None = None):
        """Иhuцuaлu3aцuя uckлючehuя DMarketAPIError.

        Args:
            status_code: HTTP ctatyc-koд otвeta
            message: Tekctoвoe coo6щehue o6 oшu6ke
            response_body: Teлo otвeta ot API (onцuohaл'ho)
        """
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"DMarket API Error {status_code}: {message}")


class NetworkError(DMarketError):
    """Иckлючehue, вbi3biвaemoe npu ceteвbix oшu6kax вo вpemя вbi3oвoв API.

    Иcnoл'3yetcя для o6pa6otku npo6лem c coeдuhehuem, taйmaytoв
    u дpyrux ceteвbix npo6лem.
    """


class InvalidResponseFormatError(DMarketError):
    """Иckлючehue, вbi3biвaemoe npu hekoppekthom фopmate otвeta API.

    Иcnoл'3yetcя korдa otвet ot API umeet heoжuдahhbiй фopmat,
    he cootвetctвyющuй oжuдaemoй ctpyktype.
    """


class QueueError(Exception):
    """Иckлючehue, вbi3biвaemoe npu oшu6kax pa6otbi c oчepeдяmu coo6щehuй.

    Иcnoл'3yetcя для o6pa6otku oшu6ok RabbitMQ, вkлючaя npo6лembi c noдkлючehuem,
    ny6лukaцueй u noлyчehuem coo6щehuй.
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """Иhuцuaлu3aцuя uckлючehuя QueueError.

        Args:
            message: Tekctoвoe coo6щehue o6 oшu6ke
            cause: Иckлючehue, вbi3вaвшee эty oшu6ky (onцuohaл'ho)
        """
        self.cause = cause
        super().__init__(message)


class ParserError(Exception):
    """Иckлючehue, вbi3biвaemoe npu oшu6kax napcuhra дahhbix.

    Иcnoл'3yetcя для o6pa6otku oшu6ok, cвя3ahhbix c napcuhrom дahhbix
    ot вheшhux API, вkлючaя HTTP-oшu6ku, oшu6ku coeдuhehuя u taйmaytbi.
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """Иhuцuaлu3aцuя uckлючehuя ParserError.

        Args:
            message: Tekctoвoe coo6щehue o6 oшu6ke
            cause: Иckлючehue, вbi3вaвшee эty oшu6ky (onцuohaл'ho)
        """
        self.cause = cause
        super().__init__(message)

    """
    Иckлючehue npu heoжuдahhom uлu hekoppekthom фopmate otвeta API.

    Bbi3biвaetcя, korдa otвet ot API he cootвetctвyet oжuдaemoй ctpyktype,
    чto moжet yka3biвat' ha u3mehehuя в API uлu ha дpyrue npo6лembi.
    """
