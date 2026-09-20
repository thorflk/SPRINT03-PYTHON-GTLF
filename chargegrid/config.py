"""Constantes e premissas do protótipo — única fonte de verdade.

Origem de cada valor (ver README, seção "Premissas"):
  * Sprint 2 (`main.py`): potências dos pontos, tarifas, janela de pico.
  * Challenge (ChargeGrid-Manager): margem de segurança (`dimensionamento.py`), perfil de
    chegadas (`simulador/profiles.py`), fatores de CO2 (`services/sustainability.py`).
  * PREMISSA DO GRUPO (não é dado real): usina solar, custo da rede, carga disponível de
    30 kW e veículo de 22 kW.
"""

from datetime import datetime
from decimal import Decimal

# --- tempo -------------------------------------------------------------------------------
PASSO_MIN = 5
TICKS_POR_DIA = 24 * 60 // PASSO_MIN  # 288
DATA_SIMULADA = datetime(2026, 9, 22)  # terça-feira; usada só nos carimbos de tempo

# --- eletroposto -------------------------------------------------------------------------
PONTOS = {"P1": 7.4, "P2": 11.0, "P3": 22.0, "P4": 7.4}  # potência nominal (kW), Sprint 2
CARGA_DISPONIVEL_KW = 30.0  # PREMISSA DO GRUPO (seed do Challenge usa 40 kW; é configurável)
MARGEM_SEGURANCA = 0.80  # `SAFETY_MARGIN` de dimensionamento.py (Challenge)
LIMITE_OPERACIONAL_KW = CARGA_DISPONIVEL_KW * MARGEM_SEGURANCA  # 24 kW de importação da rede

# --- tarifa (Sprint 2) -------------------------------------------------------------------
TARIFA_NORMAL = Decimal("0.85")  # R$/kWh
TARIFA_PICO = Decimal("1.40")  # R$/kWh, 18h <= hora < 21h
HORA_PICO_INICIO = 18
HORA_PICO_FIM = 21
CUSTO_REDE_KWH = Decimal("0.60")  # PREMISSA DO GRUPO: custo da energia da rede p/ o operador

# --- usina solar (PREMISSA DO GRUPO) -----------------------------------------------------
SOLAR_KWP = 15.0
SOLAR_DERATE = 0.85  # perdas de sistema (temperatura, cabos, inversor)
SOLAR_NASCER_H = 6.0
SOLAR_POENTE_H = 18.0
PROB_NUVEM = 0.04  # chance por tick de começar um evento de nuvem

# --- curva de carga do veículo (curve_engine.py do Challenge) ----------------------------
SOC_INICIO_TAPER = 0.80
TAPER_FIM_FRACAO_NOMINAL = 0.10
SOC_INICIAL_MIN = 0.10
SOC_INICIAL_MAX = 0.50
ALVOS_SOC = (0.80, 0.90, 1.00)


# --- perfil de chegadas: shopping, dia útil (profiles.py do Challenge) -------------------
def _pesos_shopping() -> tuple[float, ...]:
    pesos = []
    for hora in range(24):
        if 18 <= hora < 22:
            pesos.append(6.0)
        elif 10 <= hora < 18:
            pesos.append(1.5)
        else:
            pesos.append(0.2)
    return tuple(pesos)


PESOS_CHEGADA_POR_HORA = _pesos_shopping()
SESSOES_POR_PONTO_DIA = (1, 3)

# --- sustentabilidade (sustainability.py + config.py do Challenge) -----------------------
CONSUMO_VEICULO_KWH_KM = 0.16
EMISSAO_KG_CO2_KM = 0.12

# --- previsão ----------------------------------------------------------------------------
LARGURA_JANELA_PICO_H = 3
TOP_HORAS_RECOMENDADAS = 3
SOLAR_MINIMO_RECOMENDACAO_KW = 5.0

# --- reprodutibilidade -------------------------------------------------------------------
SEED_DEMO = 42
SEED_HISTORICO_BASE = 1000
DIAS_HISTORICO = 14
