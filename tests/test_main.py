import pytest

import main as cli


def test_execucao_completa_grava_saidas_e_imprime_dashboard(tmp_path, capsys):
    codigo = cli.main(["--saida", str(tmp_path), "--dias-historico", "3"])
    saida = capsys.readouterr().out
    assert codigo == 0
    assert "CHARGEGRID INTELLIGENCE" in saida and "SIMULADOS" in saida
    for nome in (
        "telemetria.csv",
        "sessoes.csv",
        "ocpp_log.jsonl",
        "resumo.json",
        "01_potencia_dia.png",
        "04_previsao_pico.png",
    ):
        assert (tmp_path / nome).exists(), nome


def test_sem_graficos_nao_gera_png(tmp_path):
    cli.main(["--saida", str(tmp_path), "--dias-historico", "3", "--sem-graficos"])
    assert not list(tmp_path.glob("*.png"))
    assert (tmp_path / "resumo.json").exists()


def test_ao_vivo_imprime_so_a_janela_pedida(tmp_path, capsys):
    cli.main(
        [
            "--saida",
            str(tmp_path),
            "--dias-historico",
            "2",
            "--sem-graficos",
            "--ao-vivo",
            "--janela",
            "18:00-18:30",
            "--velocidade",
            "0",
        ]
    )
    antes_do_dashboard = capsys.readouterr().out.split("Dashboard")[0]
    horas = [linha[:5] for linha in antes_do_dashboard.splitlines() if linha[2:3] == ":"]
    assert horas[0] == "18:00" and horas[-1] == "18:25"
    assert "17:55" not in horas and "18:30" not in horas


def test_janela_invalida_devolve_erro(tmp_path, capsys):
    assert cli.main(["--saida", str(tmp_path), "--ao-vivo", "--janela", "abc"]) == 2
    assert "janela" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("dias", ["0", "-3"])
def test_dias_de_historico_invalidos_devolvem_erro_claro(tmp_path, capsys, dias):
    assert cli.main(["--saida", str(tmp_path), "--dias-historico", dias]) == 2
    assert "dias-historico" in capsys.readouterr().err


def test_velocidade_negativa_devolve_erro_claro(tmp_path, capsys):
    argv = ["--saida", str(tmp_path), "--ao-vivo", "--velocidade", "-1"]
    assert cli.main(argv) == 2
    assert "velocidade" in capsys.readouterr().err


@pytest.mark.parametrize("janela", ["10:60-12:00", "24:30-24:45", "10:00-25:00", "18:00", "a:b-c:d"])
def test_janela_impossivel_ou_mal_formada_devolve_erro(tmp_path, capsys, janela):
    assert cli.main(["--saida", str(tmp_path), "--ao-vivo", "--janela", janela]) == 2
    assert "janela" in capsys.readouterr().err.lower()


def test_janela_com_inicio_depois_do_fim_devolve_erro(tmp_path, capsys):
    assert cli.main(["--saida", str(tmp_path), "--ao-vivo", "--janela", "20:00-18:00"]) == 2
    assert "janela" in capsys.readouterr().err.lower()
