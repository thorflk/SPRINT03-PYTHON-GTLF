"""Varredura de seeds: mostra que o comportamento vale além da seed de demonstração.

Uso: `python -m chargegrid.varredura --n 30 --saida docs/resultados/varredura_seeds.md`
"""

import argparse
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from chargegrid import config as cfg
from chargegrid.formato import br, configurar_saida_utf8
from chargegrid.simulacao import simular_dia


def varrer(seeds: Iterable[int]) -> pd.DataFrame:
    h = cfg.PASSO_MIN / 60
    linhas = []
    for seed in seeds:
        res = simular_dia(seed)
        t = res.telemetria
        total = float((t["entregue_kw"] * h).sum())
        solar = float((t["solar_usada_kw"] * h).sum())
        linhas.append(
            {
                "seed": seed,
                "sessoes": len(res.sessoes),
                "recusadas": res.recusadas,
                "energia_kwh": round(total, 1),
                "pct_solar": round(100 * solar / total, 1) if total > 0 else 0.0,
                "minutos_em_corte": int(t["em_corte"].sum() * cfg.PASSO_MIN),
                "pico_rede_kw": round(float(t["rede_kw"].max()), 2),
                "violacoes_limite": int((t["rede_kw"] > cfg.LIMITE_OPERACIONAL_KW + 1e-9).sum()),
            }
        )
    return pd.DataFrame(linhas)


def tabela_markdown(df: pd.DataFrame) -> str:
    colunas = list(df.columns)
    linhas = ["| " + " | ".join(colunas) + " |", "|" + "---|" * len(colunas)]
    for _, linha in df.iterrows():
        linhas.append("| " + " | ".join(str(linha[c]) for c in colunas) + " |")
    return "\n".join(linhas)


def resumo_markdown(df: pd.DataFrame) -> str:
    com_corte = int((df["minutos_em_corte"] > 0).sum())
    return (
        f"- Seeds simuladas: {len(df)} (de {int(df['seed'].min())} a {int(df['seed'].max())})\n"
        f"- Seeds com corte de demanda: {com_corte} de {len(df)}\n"
        f"- Média de energia entregue: {br(df['energia_kwh'].mean(), 1)} kWh/dia\n"
        f"- Média da fração solar: {br(df['pct_solar'].mean(), 1)}%\n"
        f"- Maior importação da rede: {br(df['pico_rede_kw'].max(), 2)} kW "
        f"(limite {br(cfg.LIMITE_OPERACIONAL_KW, 0)} kW)\n"
        f"- Violações do limite da rede (ticks): {int(df['violacoes_limite'].sum())}\n"
    )


def main(argv: list[str] | None = None) -> int:
    configurar_saida_utf8()
    ap = argparse.ArgumentParser(description="Varredura de seeds do ChargeGrid")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--saida", default="docs/resultados/varredura_seeds.md")
    args = ap.parse_args(argv)
    df = varrer(range(1, args.n + 1))
    destino = Path(args.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        "# Varredura de seeds\n\n" + resumo_markdown(df) + "\n" + tabela_markdown(df) + "\n",
        encoding="utf-8",
    )
    print(resumo_markdown(df))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
