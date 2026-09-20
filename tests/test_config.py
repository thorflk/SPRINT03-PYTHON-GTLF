import pytest

from chargegrid import config as cfg


def test_limite_operacional_aplica_margem_de_seguranca():
    assert cfg.LIMITE_OPERACIONAL_KW == pytest.approx(24.0)


def test_ticks_por_dia_com_passo_de_5_minutos():
    assert cfg.PASSO_MIN == 5
    assert cfg.TICKS_POR_DIA == 288


def test_pontos_mantem_potencias_da_sprint_2():
    assert list(cfg.PONTOS) == ["P1", "P2", "P3", "P4"]
    assert list(cfg.PONTOS.values()) == [7.4, 11.0, 22.0, 7.4]


def test_tarifa_de_pico_maior_que_normal_e_janela_18_a_21():
    assert cfg.TARIFA_PICO > cfg.TARIFA_NORMAL
    assert (cfg.HORA_PICO_INICIO, cfg.HORA_PICO_FIM) == (18, 21)


def test_pesos_de_chegada_cobrem_24_horas_e_noite_domina_madrugada():
    assert len(cfg.PESOS_CHEGADA_POR_HORA) == 24
    assert cfg.PESOS_CHEGADA_POR_HORA[19] > cfg.PESOS_CHEGADA_POR_HORA[3]
    assert all(p > 0 for p in cfg.PESOS_CHEGADA_POR_HORA)
