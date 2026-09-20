"""Orquestra o dia simulado: solar -> sessões -> demanda -> comandos OCPP -> medição -> tarifa.

Um tick = `cfg.PASSO_MIN` minutos. Todas as leituras são no fim do intervalo. Invariantes
(verificados em `tests/test_simulacao.py`): rede <= limite; solar_usada + rede == entregue;
entregue <= alocada <= desejada.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from chargegrid import config as cfg
from chargegrid.demanda import alocar, comandos_de_limite
from chargegrid.medidor import MedidorModbus
from chargegrid.ocpp import RegistroOcpp
from chargegrid.sessoes import Sessao, criar_sessao, gerar_chegadas_por_tick
from chargegrid.solar import gerar_fatores_nuvem, potencia_solar_kw
from chargegrid.tarifacao import custo_do_intervalo, eh_pico

FuncaoAoVivo = Callable[[dict, list[str]], None]


@dataclass
class ResultadoDia:
    seed: int
    telemetria: pd.DataFrame
    sessoes: list[Sessao]
    ocpp: RegistroOcpp
    recusadas: int


def _instante(tick: int) -> str:
    momento = cfg.DATA_SIMULADA + timedelta(minutes=tick * cfg.PASSO_MIN)
    return momento.strftime("%Y-%m-%dT%H:%M:%SZ")


def _hhmm(minuto: int) -> str:
    return f"{minuto // 60:02d}:{minuto % 60:02d}"


def simular_dia(seed: int, ao_vivo: FuncaoAoVivo | None = None) -> ResultadoDia:
    rng = random.Random(seed)
    nuvem = gerar_fatores_nuvem(rng)
    chegadas = gerar_chegadas_por_tick(rng)
    medidores = {ponto: MedidorModbus(ponto) for ponto in cfg.PONTOS}
    ocpp = RegistroOcpp()
    ativas: dict[str, Sessao] = {}
    ultimo_limite: dict[str, float | None] = {}
    todas: list[Sessao] = []
    linhas: list[dict] = []
    recusadas = 0
    horas = cfg.PASSO_MIN / 60

    for tick in range(cfg.TICKS_POR_DIA):
        minuto = tick * cfg.PASSO_MIN
        inicio = _instante(tick)
        fim = _instante(tick + 1)
        eventos: list[str] = []

        for _ in range(chegadas[tick]):
            livres = [p for p in cfg.PONTOS if p not in ativas]
            if not livres:
                recusadas += 1
                eventos.append("Chegada recusada: todos os pontos ocupados")
                continue
            ponto = rng.choice(livres)
            sessao = criar_sessao(len(todas) + 1, ponto, rng, tick)
            todas.append(sessao)
            ativas[ponto] = sessao
            ocpp.start_transaction(
                inicio, ponto, f"RFID-{sessao.id:03d}", medidores[ponto].energia_wh
            )
            eventos.append(
                f"StartTransaction {ponto} ({sessao.veiculo.nome}, SoC {sessao.soc:.0%})"
            )

        desejadas = {p: s.potencia_desejada_kw(cfg.PONTOS[p]) for p, s in ativas.items()}
        solar_kw = potencia_solar_kw(minuto, nuvem[tick])
        aloc = alocar(desejadas, solar_kw, cfg.LIMITE_OPERACIONAL_KW)
        for ponto, limite_kw in comandos_de_limite(
            ultimo_limite, desejadas, aloc.alocadas, cfg.PONTOS
        ):
            ocpp.set_charging_profile(inicio, ponto, round(limite_kw * 1000))
            eventos.append(f"SetChargingProfile {ponto} -> {limite_kw:.1f} kW")

        energias = {p: s.avancar(aloc.alocadas[p]) for p, s in ativas.items()}
        entregues = {p: e / horas for p, e in energias.items()}
        entregue_total = sum(entregues.values())
        solar_usada = min(solar_kw, entregue_total)
        rede = entregue_total - solar_usada
        fracao_solar = solar_usada / entregue_total if entregue_total > 0 else 0.0
        pico = eh_pico(minuto)

        for ponto, sessao in ativas.items():
            energia = energias[ponto]
            medidores[ponto].acumular(energia)
            regs = medidores[ponto].ler_registradores(entregues[ponto])
            ocpp.meter_values(fim, ponto, regs["potencia_ativa_W"], regs["energia_ativa_Wh"])
            em_corte = aloc.alocadas[ponto] < desejadas[ponto] - 1e-9
            sessao.registrar(
                energia, fracao_solar, custo_do_intervalo(energia, minuto), pico, em_corte
            )

        linha = {
            "tick": tick,
            "hora": _hhmm(minuto),
            "minuto": minuto,
            "solar_kw": solar_kw,
            "desejada_kw": aloc.desejada_total_kw,
            "teto_kw": aloc.teto_kw,
            "alocada_kw": aloc.alocada_total_kw,
            "entregue_kw": entregue_total,
            "solar_usada_kw": solar_usada,
            "rede_kw": rede,
            "limite_kw": cfg.LIMITE_OPERACIONAL_KW,
            "fator_corte": aloc.fator,
            "em_corte": aloc.em_corte,
            "pontos_ativos": len(ativas),
            "em_pico": pico,
        }
        for ponto in cfg.PONTOS:
            linha[f"{ponto}_desejada_kw"] = desejadas.get(ponto, 0.0)
            linha[f"{ponto}_alocada_kw"] = aloc.alocadas.get(ponto, 0.0)
            linha[f"{ponto}_entregue_kw"] = entregues.get(ponto, 0.0)
        linhas.append(linha)

        for ponto in [p for p, s in ativas.items() if s.atingiu_alvo]:
            sessao = ativas.pop(ponto)
            sessao.concluida, sessao.tick_fim = True, tick
            ultimo_limite.pop(ponto, None)
            ocpp.stop_transaction(fim, ponto, medidores[ponto].energia_wh, "EVDisconnected")
            eventos.append(
                f"StopTransaction {ponto} ({sessao.energia_kwh:.1f} kWh, SoC {sessao.soc:.0%})"
            )

        if ao_vivo is not None:
            ao_vivo(linha, eventos)

    fim_do_dia = _instante(cfg.TICKS_POR_DIA)
    for ponto, sessao in ativas.items():  # sessões ainda ativas à meia-noite
        sessao.tick_fim = cfg.TICKS_POR_DIA - 1
        ocpp.stop_transaction(fim_do_dia, ponto, medidores[ponto].energia_wh, "Other")

    return ResultadoDia(seed, pd.DataFrame(linhas), todas, ocpp, recusadas)
