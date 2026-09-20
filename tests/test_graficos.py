from chargegrid import config as cfg
from chargegrid.graficos import gerar_graficos
from chargegrid.previsao import ajustar, gerar_historico
from chargegrid.simulacao import simular_dia

ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"


def test_gera_os_quatro_png_validos(tmp_path):
    res = simular_dia(cfg.SEED_DEMO)
    prev = ajustar(gerar_historico(4))
    caminhos = gerar_graficos(res, prev, tmp_path)
    assert [c.name for c in caminhos] == [
        "01_potencia_dia.png",
        "02_origem_energia.png",
        "03_solicitada_vs_alocada.png",
        "04_previsao_pico.png",
    ]
    for caminho in caminhos:
        conteudo = caminho.read_bytes()
        assert conteudo.startswith(ASSINATURA_PNG) and len(conteudo) > 5_000
