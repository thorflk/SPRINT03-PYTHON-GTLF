"""Sessões de recarga: curva de potência por SoC e geração de chegadas.

Curva (adaptada de `curve_engine.py` do Challenge): platô em min(nominal, OBC) até 80% de SoC;
depois decai linearmente até 10% da nominal em 100%. A rampa inicial de 2 min do Challenge é
desprezada porque o passo da simulação é de 5 min.
"""

import random
from dataclasses import dataclass, field
from decimal import Decimal

from chargegrid import config as cfg
from chargegrid.veiculos import Veiculo, escolher_veiculo


def potencia_desejada_kw(nominal_kw: float, veiculo: Veiculo, soc: float) -> float:
    plato = min(nominal_kw, veiculo.obc_kw)
    if soc < cfg.SOC_INICIO_TAPER:
        return plato
    fim = min(cfg.TAPER_FIM_FRACAO_NOMINAL * nominal_kw, plato)
    fracao = min(1.0, (soc - cfg.SOC_INICIO_TAPER) / (1.0 - cfg.SOC_INICIO_TAPER))
    return plato - (plato - fim) * fracao


@dataclass
class Sessao:
    id: int
    ponto: str
    veiculo: Veiculo
    soc_inicial: float
    alvo: float
    tick_inicio: int
    soc: float = field(init=False)
    tick_fim: int | None = None
    concluida: bool = False
    energia_kwh: float = 0.0
    energia_solar_kwh: float = 0.0
    energia_pico_kwh: float = 0.0
    custo: Decimal = Decimal("0")
    custo_pico: Decimal = Decimal("0")
    ticks_em_corte: int = 0

    def __post_init__(self) -> None:
        self.soc = self.soc_inicial

    @property
    def atingiu_alvo(self) -> bool:
        return self.soc >= self.alvo - 1e-9

    def potencia_desejada_kw(self, nominal_kw: float) -> float:
        return potencia_desejada_kw(nominal_kw, self.veiculo, self.soc)

    def avancar(self, potencia_alocada_kw: float) -> float:
        """Entrega energia por um intervalo e devolve os kWh entregues (limitados ao alvo)."""
        if potencia_alocada_kw < 0:
            raise ValueError("potencia_alocada_kw não pode ser negativa")
        falta_kwh = max(0.0, (self.alvo - self.soc) * self.veiculo.bateria_kwh)
        energia = min(potencia_alocada_kw * cfg.PASSO_MIN / 60, falta_kwh)
        self.soc += energia / self.veiculo.bateria_kwh
        self.energia_kwh += energia
        return energia

    def registrar(
        self,
        energia_kwh: float,
        fracao_solar: float,
        custo: Decimal,
        em_pico: bool,
        em_corte: bool,
    ) -> None:
        self.energia_solar_kwh += energia_kwh * fracao_solar
        self.custo += custo
        if em_pico:
            self.energia_pico_kwh += energia_kwh
            self.custo_pico += custo
        if em_corte:
            self.ticks_em_corte += 1


def criar_sessao(id: int, ponto: str, rng: random.Random, tick_inicio: int) -> Sessao:
    veiculo = escolher_veiculo(rng)
    soc_inicial = round(rng.uniform(cfg.SOC_INICIAL_MIN, cfg.SOC_INICIAL_MAX), 2)
    alvo = rng.choice(cfg.ALVOS_SOC)
    return Sessao(id, ponto, veiculo, soc_inicial, alvo, tick_inicio)


def gerar_chegadas_por_tick(
    rng: random.Random, faixa: tuple[int, int] = cfg.SESSOES_POR_PONTO_DIA
) -> list[int]:
    """Quantas chegadas ocorrem em cada tick, sorteadas pelo perfil horário do shopping."""
    total = sum(rng.randint(*faixa) for _ in cfg.PONTOS)
    pesos = [
        cfg.PESOS_CHEGADA_POR_HORA[(t * cfg.PASSO_MIN) // 60] for t in range(cfg.TICKS_POR_DIA)
    ]
    ticks = rng.choices(range(cfg.TICKS_POR_DIA), weights=pesos, k=total)
    contagem = [0] * cfg.TICKS_POR_DIA
    for t in ticks:
        contagem[t] += 1
    return contagem
