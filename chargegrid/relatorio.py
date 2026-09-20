"""Consolida o dia simulado: resumo, arquivos, dashboard de terminal e linha ao vivo."""

import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

from chargegrid import config as cfg
from chargegrid.formato import br
from chargegrid.previsao import Previsao
from chargegrid.sessoes import Sessao
from chargegrid.simulacao import ResultadoDia
from chargegrid.tarifacao import em_reais

LARGURA = 66


def _hhmm(tick: int) -> str:
    minuto = tick * cfg.PASSO_MIN
    return f"{minuto // 60:02d}:{minuto % 60:02d}"


def sessoes_para_df(sessoes: list[Sessao]) -> pd.DataFrame:
    linhas = []
    for s in sessoes:
        tick_fim = s.tick_fim if s.tick_fim is not None else cfg.TICKS_POR_DIA - 1
        linhas.append(
            {
                "id": s.id,
                "ponto": s.ponto,
                "veiculo": s.veiculo.nome,
                "inicio": _hhmm(s.tick_inicio),
                "fim": _hhmm(tick_fim + 1),
                "duracao_min": (tick_fim - s.tick_inicio + 1) * cfg.PASSO_MIN,
                "soc_inicial": round(s.soc_inicial, 3),
                "soc_final": round(s.soc, 3),
                "energia_kwh": round(s.energia_kwh, 3),
                "energia_solar_kwh": round(s.energia_solar_kwh, 3),
                "energia_pico_kwh": round(s.energia_pico_kwh, 3),
                "custo_brl": float(em_reais(s.custo)),
                "minutos_em_corte": s.ticks_em_corte * cfg.PASSO_MIN,
                "concluida": s.concluida,
            }
        )
    return pd.DataFrame(linhas)


def montar_resumo(res: ResultadoDia, prev: Previsao, bt: dict[str, float]) -> dict:
    t = res.telemetria
    h = cfg.PASSO_MIN / 60
    energia_total = float((t["entregue_kw"] * h).sum())
    energia_solar = float((t["solar_usada_kw"] * h).sum())
    energia_rede = float((t["rede_kw"] * h).sum())
    energia_pico = sum(s.energia_pico_kwh for s in res.sessoes)
    receita = sum((s.custo for s in res.sessoes), Decimal("0"))
    receita_pico = sum((s.custo_pico for s in res.sessoes), Decimal("0"))
    economia_solar = Decimal(str(energia_solar)) * cfg.CUSTO_REDE_KWH
    economia_deslocando = Decimal(str(energia_pico)) * (cfg.TARIFA_PICO - cfg.TARIFA_NORMAL)
    co2 = energia_total / cfg.CONSUMO_VEICULO_KWH_KM * cfg.EMISSAO_KG_CO2_KM
    ini, fim, media = prev.janela_pico
    return {
        "seed": res.seed,
        "sessoes": len(res.sessoes),
        "sessoes_concluidas": sum(1 for s in res.sessoes if s.concluida),
        "recusadas": res.recusadas,
        "energia_total_kwh": round(energia_total, 2),
        "energia_solar_kwh": round(energia_solar, 2),
        "energia_rede_kwh": round(energia_rede, 2),
        "pct_solar": round(100 * energia_solar / energia_total, 1) if energia_total else 0.0,
        "pico_desejado_kw": round(float(t["desejada_kw"].max()), 2),
        "pico_rede_kw": round(float(t["rede_kw"].max()), 2),
        "limite_kw": cfg.LIMITE_OPERACIONAL_KW,
        "minutos_em_corte": int(t["em_corte"].sum() * cfg.PASSO_MIN),
        "receita_brl": float(em_reais(receita)),
        "receita_pico_brl": float(em_reais(receita_pico)),
        "receita_normal_brl": float(em_reais(receita - receita_pico)),
        "energia_pico_kwh": round(energia_pico, 2),
        "economia_solar_brl": float(em_reais(economia_solar)),
        "economia_deslocando_pico_brl": float(em_reais(economia_deslocando)),
        "co2_evitado_kg": round(co2, 2),
        "previsao_janela_pico": f"{ini}h-{fim}h",
        "previsao_media_pico_kw": round(media, 2),
        "previsao_mae_kw": bt["mae_kw"],
        "previsao_mae_baseline_kw": bt["mae_baseline_kw"],
    }


def salvar_saidas(res: ResultadoDia, resumo: dict, pasta: Path | str) -> list[Path]:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    telemetria = pasta / "telemetria.csv"
    sessoes = pasta / "sessoes.csv"
    log = pasta / "ocpp_log.jsonl"
    resumo_json = pasta / "resumo.json"
    res.telemetria.to_csv(telemetria, index=False, float_format="%.3f")
    sessoes_para_df(res.sessoes).to_csv(sessoes, index=False)
    res.ocpp.salvar_jsonl(log)
    resumo_json.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return [telemetria, sessoes, log, resumo_json]


def _plural(quantidade: int, palavra: str) -> str:
    return f"{quantidade} {palavra}" + ("" if quantidade == 1 else "s")


def _titulo(texto: str) -> str:
    return f"\n{'─' * 4} {texto} {'─' * (LARGURA - 6 - len(texto))}"


def formatar_dashboard(resumo: dict, recomendacoes: list[str], sessoes_df: pd.DataFrame) -> str:
    r = resumo
    origem_limite = f"{br(cfg.CARGA_DISPONIVEL_KW, 0)} kW disponíveis x {br(cfg.MARGEM_SEGURANCA)}"
    colunas = [
        "id",
        "ponto",
        "veiculo",
        "inicio",
        "fim",
        "energia_kwh",
        "energia_solar_kwh",
        "custo_brl",
        "minutos_em_corte",
    ]
    linhas = [
        "═" * LARGURA,
        "  CHARGEGRID INTELLIGENCE — Dashboard do dia simulado",
        f"  EV Challenge 2026 | FIAP x GoodWe | Grupo GTLF | seed {r['seed']}",
        "  Todos os dados são SIMULADOS (ver README).",
        "═" * LARGURA,
        _titulo("Operação"),
        f"  Sessões: {r['sessoes']} ({_plural(r['sessoes_concluidas'], 'concluída')}, "
        f"{_plural(r['recusadas'], 'recusada')} por falta de ponto)",
        f"  Pico de demanda desejada  : {br(r['pico_desejado_kw'], 1)} kW",
        f"  Limite da rede            : {br(r['limite_kw'], 1)} kW ({origem_limite})",
        f"  Pico de importação        : {br(r['pico_rede_kw'], 1)} kW",
        f"  Tempo com corte de demanda: {r['minutos_em_corte']} min",
        _titulo("Energia e sustentabilidade"),
        f"  Energia entregue : {br(r['energia_total_kwh'], 1)} kWh",
        f"  Geração solar    : {br(r['energia_solar_kwh'], 1)} kWh ({br(r['pct_solar'], 1)}%)",
        f"  Rede elétrica    : {br(r['energia_rede_kwh'], 1)} kWh",
        f"  CO₂ evitado vs combustão: {br(r['co2_evitado_kg'], 1)} kg",
        _titulo("Financeiro"),
        f"  Receita total   : R$ {br(r['receita_brl'])} "
        f"(pico R$ {br(r['receita_pico_brl'])} | normal R$ {br(r['receita_normal_brl'])})",
        f"  Energia recarregada no pico: {br(r['energia_pico_kwh'], 1)} kWh",
        f"  Economia do operador com solar: R$ {br(r['economia_solar_brl'])} "
        f"(premissa: rede a R$ {br(float(cfg.CUSTO_REDE_KWH))}/kWh)",
        "  Economia potencial dos clientes se saíssem do pico: "
        f"R$ {br(r['economia_deslocando_pico_brl'])}",
        _titulo("IA — previsão e orientação"),
        f"  Erro médio da previsão por hora: {br(r['previsao_mae_kw'], 2)} kW "
        f"(baseline constante: {br(r['previsao_mae_baseline_kw'], 2)} kW)",
        *[f"  • {texto}" for texto in recomendacoes],
        _titulo("Sessões do dia"),
        sessoes_df[colunas].to_string(index=False),
        "═" * LARGURA,
    ]
    return "\n".join(linhas)


def tabela_resultados_markdown(resumo: dict) -> str:
    r = resumo
    limite = f"{br(r['limite_kw'], 0)} kW"
    itens = [
        (
            "Sessões (concluídas / recusadas)",
            f"{r['sessoes']} ({r['sessoes_concluidas']} / {r['recusadas']})",
        ),
        ("Energia entregue", f"{br(r['energia_total_kwh'], 1)} kWh"),
        (
            "Geração solar consumida",
            f"{br(r['energia_solar_kwh'], 1)} kWh ({br(r['pct_solar'], 1)}%)",
        ),
        ("Energia da rede", f"{br(r['energia_rede_kwh'], 1)} kWh"),
        ("Pico de demanda desejada", f"{br(r['pico_desejado_kw'], 1)} kW"),
        (f"Pico de importação da rede (limite {limite})", f"{br(r['pico_rede_kw'], 1)} kW"),
        ("Tempo com corte de demanda", f"{r['minutos_em_corte']} min"),
        ("Receita total", f"R$ {br(r['receita_brl'])}"),
        (
            "Receita no pico / fora do pico",
            f"R$ {br(r['receita_pico_brl'])} / R$ {br(r['receita_normal_brl'])}",
        ),
        ("Economia do operador com solar", f"R$ {br(r['economia_solar_brl'])}"),
        ("CO₂ evitado vs combustão", f"{br(r['co2_evitado_kg'], 1)} kg"),
        ("Janela de pico prevista", r["previsao_janela_pico"]),
        (
            "Erro da previsão (modelo / baseline)",
            f"{br(r['previsao_mae_kw'], 2)} kW / {br(r['previsao_mae_baseline_kw'], 2)} kW",
        ),
    ]
    linhas = ["| Indicador | Valor |", "|---|---|"]
    linhas += [f"| {nome} | {valor} |" for nome, valor in itens]
    return "\n".join(linhas)


def barra(valor: float, maximo: float, largura: int = 20) -> str:
    if maximo <= 0:
        cheios = 0
    else:
        cheios = round(largura * min(max(valor, 0.0), maximo) / maximo)
    return "[" + "█" * cheios + "░" * (largura - cheios) + "]"


def formatar_linha_ao_vivo(linha: dict, eventos: list[str]) -> str:
    faixa = "PICO  " if linha["em_pico"] else "normal"
    ativos = int(linha["pontos_ativos"])
    texto = (
        f"{linha['hora']}  sol {br(linha['solar_kw'], 1):>5} kW | "
        f"EVs {br(linha['entregue_kw'], 1):>5} kW | "
        f"rede {br(linha['rede_kw'], 1):>5}/{br(linha['limite_kw'], 0)} kW "
        f"{barra(linha['rede_kw'], linha['limite_kw'])} | "
        f"{ativos} {'ativo ' if ativos == 1 else 'ativos'} | {faixa}"
    )
    if linha["em_corte"]:
        texto += f" | CORTE {linha['fator_corte']:.0%}"
    for evento in eventos:
        texto += f"\n         > {evento}"
    return texto
