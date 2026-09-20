"""Controle de demanda: distribui a potência entre os pontos ativos.

O limite contratado vale para a IMPORTAÇÃO da rede. A geração solar atende os carregadores
primeiro, então o teto de potência para os veículos é `limite + solar`. Se a soma desejada
excede o teto, aplica-se o mesmo fator proporcional da Sprint 2 a todos os pontos.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Alocacao:
    teto_kw: float
    desejada_total_kw: float
    fator: float
    alocadas: dict[str, float]

    @property
    def em_corte(self) -> bool:
        return self.fator < 1.0

    @property
    def alocada_total_kw(self) -> float:
        return sum(self.alocadas.values())


def _truncar_mw(valor_kw: float) -> float:
    """Trunca (nunca arredonda para cima) a 3 casas, para a soma não passar do teto."""
    return math.floor(valor_kw * 1000 + 1e-9) / 1000


def alocar(desejadas: dict[str, float], solar_kw: float, limite_kw: float) -> Alocacao:
    teto = limite_kw + max(solar_kw, 0.0)
    total = sum(desejadas.values())
    if total <= teto or total <= 0:
        return Alocacao(teto, total, 1.0, dict(desejadas))
    fator = teto / total
    alocadas = {ponto: _truncar_mw(d * fator) for ponto, d in desejadas.items()}
    return Alocacao(teto, total, fator, alocadas)


def comandos_de_limite(
    ultimo_limite: dict[str, float | None],
    desejadas: dict[str, float],
    alocadas: dict[str, float],
    nominais: dict[str, float],
    tol_kw: float = 0.05,
) -> list[tuple[str, float]]:
    """Decide quais pontos recebem um novo `SetChargingProfile` neste intervalo.

    Envia o limite quando o ponto está cortado e o valor mudou mais que `tol_kw`; envia a
    liberação (limite nominal) quando o corte termina. Atualiza `ultimo_limite` (mutação).
    """
    comandos: list[tuple[str, float]] = []
    for ponto, desejada in desejadas.items():
        alocada = alocadas[ponto]
        anterior = ultimo_limite.get(ponto)
        if alocada < desejada - 1e-9:
            if anterior is None or abs(anterior - alocada) > tol_kw:
                comandos.append((ponto, alocada))
                ultimo_limite[ponto] = alocada
        elif anterior is not None:
            comandos.append((ponto, nominais[ponto]))
            ultimo_limite[ponto] = None
    return comandos
