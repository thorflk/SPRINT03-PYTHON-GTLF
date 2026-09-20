import pytest

from chargegrid import config as cfg
from chargegrid.simulacao import simular_dia

H = cfg.PASSO_MIN / 60


@pytest.fixture(scope="module")
def demo():
    return simular_dia(cfg.SEED_DEMO)


def test_uma_linha_de_telemetria_por_tick(demo):
    assert len(demo.telemetria) == cfg.TICKS_POR_DIA
    assert list(demo.telemetria["tick"]) == list(range(cfg.TICKS_POR_DIA))


def test_mesma_seed_produz_resultado_identico():
    a, b = simular_dia(7), simular_dia(7)
    assert a.telemetria.equals(b.telemetria)
    assert [m.como_dict() for m in a.ocpp.mensagens] == [m.como_dict() for m in b.ocpp.mensagens]


@pytest.mark.parametrize("seed", range(1, 26))
def test_invariantes_fisicos_em_todos_os_ticks(seed):
    t = simular_dia(seed).telemetria
    assert (t["rede_kw"] <= cfg.LIMITE_OPERACIONAL_KW + 1e-9).all()
    assert ((t["solar_usada_kw"] + t["rede_kw"]) - t["entregue_kw"]).abs().max() < 1e-9
    assert (t["entregue_kw"] <= t["alocada_kw"] + 1e-9).all()
    assert (t["alocada_kw"] <= t["desejada_kw"] + 1e-9).all()
    assert (t["solar_usada_kw"] <= t["solar_kw"] + 1e-9).all()
    noite = (t["minuto"] < 6 * 60) | (t["minuto"] >= 18 * 60)
    assert (t.loc[noite, "solar_kw"] == 0).all()


def test_energia_das_sessoes_bate_com_a_telemetria(demo):
    da_telemetria = (demo.telemetria["entregue_kw"] * H).sum()
    das_sessoes = sum(s.energia_kwh for s in demo.sessoes)
    assert das_sessoes == pytest.approx(da_telemetria, abs=1e-6)


def test_solar_atribuido_as_sessoes_bate_com_a_telemetria(demo):
    da_telemetria = (demo.telemetria["solar_usada_kw"] * H).sum()
    das_sessoes = sum(s.energia_solar_kwh for s in demo.sessoes)
    assert das_sessoes == pytest.approx(da_telemetria, abs=1e-6)


def test_custo_de_cada_sessao_fica_entre_tarifa_normal_e_de_pico(demo):
    for s in demo.sessoes:
        if s.energia_kwh > 0:
            custo = float(s.custo)
            assert custo >= s.energia_kwh * float(cfg.TARIFA_NORMAL) - 1e-3
            assert custo <= s.energia_kwh * float(cfg.TARIFA_PICO) + 1e-3


def test_log_ocpp_e_coerente_com_as_sessoes(demo):
    contagem = demo.ocpp.contar_por_acao()
    assert contagem["StartTransaction"] == len(demo.sessoes)
    assert contagem["StopTransaction"] == len(demo.sessoes)
    assert contagem.get("MeterValues", 0) > 0


def test_cenario_de_demonstracao_exibe_corte_pico_solar_e_varias_sessoes(demo):
    t = demo.telemetria
    assert t["em_corte"].sum() * cfg.PASSO_MIN >= 60, "sem corte de demanda suficiente"
    assert demo.ocpp.contar_por_acao().get("SetChargingProfile", 0) > 0
    assert sum(s.energia_pico_kwh for s in demo.sessoes) > 0, "nenhuma recarga no pico"
    assert t["solar_usada_kw"].sum() > 0, "nenhum kWh solar consumido"
    assert len(demo.sessoes) >= 6
    assert demo.recusadas <= 1


def test_ao_vivo_e_chamado_uma_vez_por_tick_com_eventos():
    chamadas = []
    simular_dia(cfg.SEED_DEMO, ao_vivo=lambda linha, eventos: chamadas.append((linha, eventos)))
    assert len(chamadas) == cfg.TICKS_POR_DIA
    assert any(eventos for _, eventos in chamadas)
    assert {"hora", "solar_kw", "rede_kw", "em_corte"} <= set(chamadas[0][0])
