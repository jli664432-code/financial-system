"""
金额与分数互转工具函数。
"""
from decimal import Decimal, ROUND_HALF_UP


def decimal_to_fraction(amount: Decimal, min_scale: int = 2, max_scale: int = 6) -> tuple[int, int]:
    """
    将 Decimal 金额转换为 (分子, 分母)。

    默认至少保留 2 位小数，最多 6 位，避免浮点误差。
    """
    exponent = -amount.as_tuple().exponent
    scale = min(max(exponent, min_scale), max_scale)
    denominator = 10**scale
    numerator = int((amount * Decimal(denominator)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return numerator, denominator


def fraction_to_decimal(numerator: int, denominator: int | None) -> Decimal:
    """
    将 (分子, 分母) 还原为 Decimal 金额。
    """
    denominator = denominator or 1
    return Decimal(numerator) / Decimal(denominator)

