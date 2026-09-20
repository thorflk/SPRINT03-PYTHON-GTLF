"""Tarifação por faixa horária.

Convenção de dinheiro herdada de `services/pricing.py` do Challenge: `Decimal`, arredondamento
`ROUND_HALF_UP`, 4 casas internas. Cada intervalo de 5 min é cobrado pela tarifa vigente no
seu início, então uma sessão que atravessa as 18h paga cada parte na faixa correta.
"""

from decimal import ROUND_HALF_UP, Decimal

from chargegrid import config as cfg

_CASAS_4 = Decimal("0.0001")
_CASAS_2 = Decimal("0.01")


def eh_pico(minuto_do_dia: int) -> bool:
    hora = minuto_do_dia // 60
    return cfg.HORA_PICO_INICIO <= hora < cfg.HORA_PICO_FIM


def tarifa_no_instante(minuto_do_dia: int) -> Decimal:
    return cfg.TARIFA_PICO if eh_pico(minuto_do_dia) else cfg.TARIFA_NORMAL


def custo_do_intervalo(energia_kwh: float, minuto_do_dia: int) -> Decimal:
    if energia_kwh < 0:
        raise ValueError("energia_kwh não pode ser negativa")
    custo = Decimal(str(energia_kwh)) * tarifa_no_instante(minuto_do_dia)
    return custo.quantize(_CASAS_4, rounding=ROUND_HALF_UP)


def em_reais(valor: Decimal) -> Decimal:
    return valor.quantize(_CASAS_2, rounding=ROUND_HALF_UP)
