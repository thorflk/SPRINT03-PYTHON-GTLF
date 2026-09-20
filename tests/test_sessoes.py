import random
from decimal import Decimal

import pytest

from chargegrid import config as cfg
from chargegrid.sessoes import (
    Sessao,
    criar_sessao,
    gerar_chegadas_por_tick,
    potencia_desejada_kw,
)
from chargegrid.veiculos import Veiculo

CARRO = Veiculo("Teste", 11.0, 50.0)


def _sessao(soc_inicial=0.5, alvo=0.8):
    return Sessao(1, "P2", CARRO, soc_inicial, alvo, tick_inicio=0)


def test_plato_e_o_menor_entre_nominal_e_obc():
    assert potencia_desejada_kw(22.0, CARRO, 0.3) == 11.0
    assert potencia_desejada_kw(7.4, CARRO, 0.3) == 7.4


def test_taper_comeca_em_80_por_cento_sem_salto():
    assert potencia_desejada_kw(11.0, CARRO, 0.80) == pytest.approx(11.0)


def test_taper_termina_em_10_por_cento_do_nominal():
    assert potencia_desejada_kw(11.0, CARRO, 1.0) == pytest.approx(1.1)


def test_potencia_nunca_cresce_com_o_soc():
    valores = [potencia_desejada_kw(11.0, CARRO, s / 100) for s in range(10, 101)]
    assert all(a >= b - 1e-12 for a, b in zip(valores, valores[1:]))


def test_avancar_entrega_energia_igual_ao_delta_de_soc_da_bateria():
    s = _sessao(0.5, 0.8)  # 0,3 x 50 kWh = 15 kWh
    for _ in range(100):
        if s.atingiu_alvo:
            break
        s.avancar(11.0)
    assert s.atingiu_alvo
    assert s.energia_kwh == pytest.approx(15.0, abs=1e-9)
    assert s.soc == pytest.approx(0.8)


def test_avancar_nunca_passa_do_alvo_num_unico_tick():
    s = _sessao(0.79, 0.80)  # faltam 0,5 kWh; 11 kW x 5 min = 0,917 kWh
    assert s.avancar(11.0) == pytest.approx(0.5)
    assert s.atingiu_alvo


def test_avancar_com_potencia_zero_nao_entrega_energia():
    s = _sessao()
    assert s.avancar(0.0) == 0.0
    assert s.soc == 0.5


def test_avancar_rejeita_potencia_negativa():
    with pytest.raises(ValueError):
        _sessao().avancar(-1.0)


def test_registrar_acumula_solar_custo_pico_e_corte():
    s = _sessao()
    s.registrar(2.0, 0.25, Decimal("2.8000"), em_pico=True, em_corte=True)
    s.registrar(1.0, 0.0, Decimal("0.8500"), em_pico=False, em_corte=False)
    assert s.energia_solar_kwh == pytest.approx(0.5)
    assert s.energia_pico_kwh == pytest.approx(2.0)
    assert s.custo == Decimal("3.6500")
    assert s.custo_pico == Decimal("2.8000")
    assert s.ticks_em_corte == 1


def test_criar_sessao_respeita_faixas_e_e_deterministica():
    a = criar_sessao(3, "P1", random.Random(5), tick_inicio=40)
    b = criar_sessao(3, "P1", random.Random(5), tick_inicio=40)
    assert a == b
    assert cfg.SOC_INICIAL_MIN <= a.soc_inicial <= cfg.SOC_INICIAL_MAX
    assert a.alvo in cfg.ALVOS_SOC
    assert a.soc == a.soc_inicial and a.tick_inicio == 40


def test_chegadas_somam_entre_4_e_12_e_sao_deterministicas():
    a = gerar_chegadas_por_tick(random.Random(3))
    assert a == gerar_chegadas_por_tick(random.Random(3))
    assert len(a) == cfg.TICKS_POR_DIA
    assert 4 <= sum(a) <= 12


def test_chegadas_concentram_no_fim_da_tarde_e_noite():
    noite = total = 0
    for seed in range(100):
        for tick, n in enumerate(gerar_chegadas_por_tick(random.Random(seed))):
            total += n
            if 18 <= (tick * cfg.PASSO_MIN) // 60 < 22:
                noite += n
    assert noite / total > 0.5
