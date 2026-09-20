from decimal import Decimal

import pytest

from chargegrid.tarifacao import custo_do_intervalo, eh_pico, em_reais, tarifa_no_instante


def test_fronteiras_da_faixa_de_pico():
    assert not eh_pico(17 * 60 + 55)
    assert eh_pico(18 * 60)
    assert eh_pico(20 * 60 + 55)
    assert not eh_pico(21 * 60)


def test_tarifa_por_instante():
    assert tarifa_no_instante(10 * 60) == Decimal("0.85")
    assert tarifa_no_instante(19 * 60) == Decimal("1.40")


def test_custo_do_intervalo_usa_a_tarifa_da_faixa():
    assert custo_do_intervalo(1.0, 19 * 60) == Decimal("1.4000")
    assert custo_do_intervalo(2.0, 10 * 60) == Decimal("1.7000")
    assert custo_do_intervalo(0.0, 19 * 60) == Decimal("0.0000")


def test_energia_negativa_e_rejeitada():
    with pytest.raises(ValueError):
        custo_do_intervalo(-0.1, 600)


def test_sessao_que_atravessa_o_pico_e_cobrada_por_intervalo():
    # 17:55 (normal) + 18:00 (pico), 1 kWh cada
    total = custo_do_intervalo(1.0, 17 * 60 + 55) + custo_do_intervalo(1.0, 18 * 60)
    assert total == Decimal("2.2500")


def test_em_reais_arredonda_meio_para_cima():
    assert em_reais(Decimal("1.005")) == Decimal("1.01")
    assert em_reais(Decimal("2.2500")) == Decimal("2.25")
