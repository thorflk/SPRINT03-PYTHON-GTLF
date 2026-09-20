"""ChargeGrid Intelligence — Sprint 3 (PCP) | FIAP x GoodWe | Grupo GTLF.

Simula 1 dia de um eletroposto comercial com usina solar, controle de demanda, tarifação e
previsão de pico. TODOS os dados são simulados. Exemplos:

    python main.py                 # execução completa (CSV, JSON, PNG, dashboard)
    python main.py --ao-vivo       # mostra o fim da tarde intervalo a intervalo
    python main.py --seed 7 --sem-graficos
"""

import argparse
import sys
import time
from pathlib import Path

from chargegrid import config as cfg
from chargegrid.formato import configurar_saida_utf8
from chargegrid.graficos import gerar_graficos
from chargegrid.previsao import ajustar, backtest, gerar_historico, recomendacoes
from chargegrid.relatorio import (
    formatar_dashboard,
    formatar_linha_ao_vivo,
    montar_resumo,
    salvar_saidas,
    sessoes_para_df,
)
from chargegrid.simulacao import simular_dia


def _parse_janela(texto: str) -> tuple[int, int]:
    try:
        inicio, fim = texto.split("-")
        h1, m1 = inicio.split(":")
        h2, m2 = fim.split(":")
        janela = (int(h1) * 60 + int(m1), int(h2) * 60 + int(m2))
    except ValueError as erro:
        raise ValueError(f"janela inválida: {texto!r} (use HH:MM-HH:MM)") from erro
    if not 0 <= janela[0] < janela[1] <= 24 * 60:
        raise ValueError(f"janela inválida: {texto!r} (o início deve ser menor que o fim)")
    return janela


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ChargeGrid Intelligence — Sprint 3 (PCP)")
    ap.add_argument("--seed", type=int, default=cfg.SEED_DEMO)
    ap.add_argument("--dias-historico", type=int, default=cfg.DIAS_HISTORICO)
    ap.add_argument("--saida", default="saida")
    ap.add_argument("--ao-vivo", action="store_true")
    ap.add_argument("--janela", default="17:55-21:30", help="HH:MM-HH:MM (só com --ao-vivo)")
    ap.add_argument("--velocidade", type=float, default=0.05, help="segundos entre intervalos")
    ap.add_argument("--sem-graficos", action="store_true")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configurar_saida_utf8()
    args = _argumentos(argv)
    callback = None
    if args.ao_vivo:
        try:
            inicio, fim = _parse_janela(args.janela)
        except ValueError as erro:
            print(f"Erro: {erro}", file=sys.stderr)
            return 2

        def callback(linha: dict, eventos: list[str]) -> None:
            if inicio <= linha["minuto"] < fim:
                print(formatar_linha_ao_vivo(linha, eventos), flush=True)
                time.sleep(args.velocidade)

        print(f"Modo ao vivo: janela {args.janela}, seed {args.seed} (dados simulados)\n")

    res = simular_dia(args.seed, ao_vivo=callback)
    prev = ajustar(gerar_historico(args.dias_historico))
    resumo = montar_resumo(res, prev, backtest(prev, res.telemetria))
    pasta = Path(args.saida)
    salvar_saidas(res, resumo, pasta)
    if not args.sem_graficos:
        gerar_graficos(res, prev, pasta)

    textos = recomendacoes(prev, cfg.LIMITE_OPERACIONAL_KW)
    print(formatar_dashboard(resumo, textos, sessoes_para_df(res.sessoes)))
    print(f"\nArquivos gravados em: {pasta.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
