import json

import pytest

from chargegrid import config as cfg
from chargegrid.previsao import ajustar, backtest, gerar_historico, recomendacoes
from chargegrid.relatorio import (
    barra,
    formatar_dashboard,
    formatar_linha_ao_vivo,
    montar_resumo,
    salvar_saidas,
    sessoes_para_df,
    tabela_resultados_markdown,
)
from chargegrid.simulacao import simular_dia


@pytest.fixture(scope="module")
def contexto():
    res = simular_dia(cfg.SEED_DEMO)
    prev = ajustar(gerar_historico(6))
    bt = backtest(prev, res.telemetria)
    return res, prev, bt, montar_resumo(res, prev, bt)


def test_resumo_energias_fecham(contexto):
    res, _, _, r = contexto
    assert r["energia_solar_kwh"] + r["energia_rede_kwh"] == pytest.approx(
        r["energia_total_kwh"], abs=0.02
    )
    das_sessoes = sum(s.energia_kwh for s in res.sessoes)
    assert r["energia_total_kwh"] == pytest.approx(das_sessoes, abs=0.02)
    assert 0 <= r["pct_solar"] <= 100


def test_resumo_financeiro_fecha_e_respeita_o_limite(contexto):
    _, _, _, r = contexto
    soma = r["receita_pico_brl"] + r["receita_normal_brl"]
    assert soma == pytest.approx(r["receita_brl"], abs=0.02)
    assert r["pico_rede_kw"] <= r["limite_kw"] + 1e-9
    esperado = r["energia_pico_kwh"] * float(cfg.TARIFA_PICO - cfg.TARIFA_NORMAL)
    assert r["economia_deslocando_pico_brl"] == pytest.approx(esperado, abs=0.02)


def test_resumo_co2_segue_a_formula_do_challenge(contexto):
    _, _, _, r = contexto
    esperado = r["energia_total_kwh"] / cfg.CONSUMO_VEICULO_KWH_KM * cfg.EMISSAO_KG_CO2_KM
    assert r["co2_evitado_kg"] == pytest.approx(esperado, abs=0.02)


def test_resumo_traz_a_previsao(contexto):
    _, prev, bt, r = contexto
    ini, fim, _ = prev.janela_pico
    assert r["previsao_janela_pico"] == f"{ini}h-{fim}h"
    assert r["previsao_mae_kw"] == bt["mae_kw"]


def test_sessoes_para_df_vazio_mantem_as_colunas():
    df = sessoes_para_df([])
    assert len(df) == 0
    assert {"id", "ponto", "veiculo", "energia_kwh", "custo_brl"} <= set(df.columns)


def test_sessoes_para_df_tem_uma_linha_por_sessao(contexto):
    res, *_ = contexto
    df = sessoes_para_df(res.sessoes)
    assert len(df) == len(res.sessoes)
    assert {"veiculo", "energia_kwh", "custo_brl", "minutos_em_corte"} <= set(df.columns)
    assert (df["duracao_min"] > 0).all()


def test_salvar_saidas_grava_os_quatro_arquivos(contexto, tmp_path):
    res, _, _, r = contexto
    caminhos = salvar_saidas(res, r, tmp_path)
    assert {c.name for c in caminhos} == {
        "telemetria.csv",
        "sessoes.csv",
        "ocpp_log.jsonl",
        "resumo.json",
    }
    assert all(c.stat().st_size > 0 for c in caminhos)
    assert json.loads((tmp_path / "resumo.json").read_text(encoding="utf-8"))["seed"] == r["seed"]
    primeira = (tmp_path / "ocpp_log.jsonl").read_text(encoding="utf-8").splitlines()[0]
    assert json.loads(primeira)["mensagem"][0] == 2


def test_dashboard_lista_indicadores_e_recomendacoes(contexto):
    res, prev, _, r = contexto
    textos = recomendacoes(prev, cfg.LIMITE_OPERACIONAL_KW)
    texto = formatar_dashboard(r, textos, sessoes_para_df(res.sessoes))
    for trecho in ("CHARGEGRID", "Limite da rede", "Geração solar", "CO₂", "Pico previsto"):
        assert trecho in texto


def test_dashboard_concorda_singular_e_plural(contexto):
    res, prev, _, r = contexto
    textos = recomendacoes(prev, cfg.LIMITE_OPERACIONAL_KW)
    um = formatar_dashboard({**r, "sessoes_concluidas": 1, "recusadas": 1}, textos,
                            sessoes_para_df(res.sessoes))
    varios = formatar_dashboard({**r, "sessoes_concluidas": 2, "recusadas": 0}, textos,
                                sessoes_para_df(res.sessoes))
    assert "1 concluída, 1 recusada por falta" in um
    assert "2 concluídas, 0 recusadas por falta" in varios


def test_tabela_markdown_tem_cabecalho_e_linhas(contexto):
    md = tabela_resultados_markdown(contexto[3])
    assert md.startswith("| Indicador | Valor |")
    assert "Energia entregue" in md and "kWh" in md


def test_barra_limita_entre_zero_e_o_maximo():
    assert barra(0, 10, 10) == "[░░░░░░░░░░]"
    assert barra(5, 10, 10) == "[█████░░░░░]"
    assert barra(99, 10, 10) == "[██████████]"
    assert barra(3, 0, 10) == "[░░░░░░░░░░]"


def test_linha_ao_vivo_concorda_singular_e_plural(contexto):
    res, *_ = contexto
    base = res.telemetria.iloc[0].to_dict()
    assert "1 ativo " in formatar_linha_ao_vivo({**base, "pontos_ativos": 1}, [])
    assert "3 ativos" in formatar_linha_ao_vivo({**base, "pontos_ativos": 3}, [])


def test_linha_ao_vivo_mostra_hora_eventos_e_corte(contexto):
    res, *_ = contexto
    linha = res.telemetria[res.telemetria["em_corte"]].iloc[0].to_dict()
    texto = formatar_linha_ao_vivo(linha, ["SetChargingProfile P2 -> 5.3 kW"])
    assert linha["hora"] in texto and "CORTE" in texto
    assert "SetChargingProfile P2" in texto
