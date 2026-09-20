from chargegrid import config as cfg
from chargegrid.varredura import main, resumo_markdown, tabela_markdown, varrer


def test_varredura_nao_tem_violacao_do_limite_em_nenhuma_seed():
    df = varrer(range(1, 6))
    assert len(df) == 5
    assert (df["violacoes_limite"] == 0).all()
    assert (df["pico_rede_kw"] <= cfg.LIMITE_OPERACIONAL_KW + 1e-9).all()


def test_markdown_tem_cabecalho_e_linhas():
    df = varrer(range(1, 4))
    tabela = tabela_markdown(df)
    assert tabela.splitlines()[0].startswith("| seed |")
    assert len(tabela.splitlines()) == 2 + 3
    assert "violações" in resumo_markdown(df).lower()


def test_tabela_mantem_inteiros_como_inteiros():
    df = varrer(range(1, 3))
    primeira_linha = tabela_markdown(df).splitlines()[2]
    celulas = [c.strip() for c in primeira_linha.strip("|").split("|")]
    assert celulas[0] == "1"  # seed
    assert "." not in celulas[1]  # sessoes
    assert "." not in celulas[5] and "." not in celulas[7]  # minutos_em_corte, violacoes


def test_main_grava_o_arquivo(tmp_path):
    destino = tmp_path / "varredura.md"
    assert main(["--n", "3", "--saida", str(destino)]) == 0
    assert "| seed |" in destino.read_text(encoding="utf-8")
