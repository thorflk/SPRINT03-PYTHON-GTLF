import random

import pytest

from chargegrid.demanda import alocar, comandos_de_limite


def test_sem_excesso_aloca_exatamente_o_desejado():
    a = alocar({"P1": 7.4, "P2": 11.0}, solar_kw=0.0, limite_kw=24.0)
    assert a.alocadas == {"P1": 7.4, "P2": 11.0}
    assert a.fator == 1.0 and not a.em_corte


def test_excesso_aplica_fator_proporcional_e_respeita_o_teto():
    d = {"P1": 7.4, "P2": 11.0, "P3": 11.0, "P4": 7.4}  # 36,8 kW > 24 kW
    a = alocar(d, solar_kw=0.0, limite_kw=24.0)
    assert a.em_corte
    assert a.fator == pytest.approx(24.0 / 36.8)
    assert a.alocada_total_kw <= 24.0 + 1e-9
    assert a.alocadas["P2"] / a.alocadas["P1"] == pytest.approx(11.0 / 7.4, abs=1e-3)


def test_solar_amplia_o_teto_e_evita_o_corte():
    d = {"P1": 7.4, "P2": 11.0, "P3": 11.0}  # 29,4 kW
    assert alocar(d, 0.0, 24.0).em_corte
    com_sol = alocar(d, 6.0, 24.0)  # teto 30 kW
    assert not com_sol.em_corte and com_sol.teto_kw == pytest.approx(30.0)


def test_solar_negativo_e_tratado_como_zero():
    assert alocar({"P1": 5.0}, -3.0, 24.0).teto_kw == pytest.approx(24.0)


def test_sem_sessoes_ativas_nao_ha_corte():
    a = alocar({}, 5.0, 24.0)
    assert a.alocadas == {} and a.fator == 1.0 and not a.em_corte


def test_propriedade_alocada_nunca_excede_desejada_nem_o_teto():
    rng = random.Random(0)
    for _ in range(300):
        d = {f"P{i}": rng.uniform(0.5, 22.0) for i in range(rng.randint(1, 4))}
        solar = rng.uniform(0, 13)
        a = alocar(d, solar, 24.0)
        assert a.alocada_total_kw <= 24.0 + solar + 1e-9
        assert all(a.alocadas[p] <= d[p] + 1e-12 for p in d)


NOMINAIS = {"P1": 7.4, "P2": 11.0}


def test_comando_e_emitido_quando_ha_corte_e_nao_repete_sem_mudanca():
    estado = {}
    cmds = comandos_de_limite(estado, {"P1": 7.4}, {"P1": 5.0}, NOMINAIS)
    assert cmds == [("P1", 5.0)]
    assert comandos_de_limite(estado, {"P1": 7.4}, {"P1": 5.01}, NOMINAIS) == []
    assert comandos_de_limite(estado, {"P1": 7.4}, {"P1": 4.5}, NOMINAIS) == [("P1", 4.5)]


def test_comando_de_liberacao_volta_ao_nominal_quando_o_corte_termina():
    estado = {"P1": 5.0}
    cmds = comandos_de_limite(estado, {"P1": 7.4}, {"P1": 7.4}, NOMINAIS)
    assert cmds == [("P1", 7.4)]
    assert estado["P1"] is None
    assert comandos_de_limite(estado, {"P1": 7.4}, {"P1": 7.4}, NOMINAIS) == []


def test_sem_corte_e_sem_estado_anterior_nao_emite_comando():
    assert comandos_de_limite({}, {"P2": 11.0}, {"P2": 11.0}, NOMINAIS) == []
