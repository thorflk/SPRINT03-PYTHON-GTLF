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


def test_janela_com_inicio_depois_do_fim_devolve_erro(tmp_path, capsys):
    assert cli.main(["--saida", str(tmp_path), "--ao-vivo", "--janela", "20:00-18:00"]) == 2
    assert "janela" in capsys.readouterr().err.lower()
