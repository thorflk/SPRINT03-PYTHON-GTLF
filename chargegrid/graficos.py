"""Gráficos PNG do dia simulado (matplotlib, backend sem janela)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from chargegrid import config as cfg  # noqa: E402
from chargegrid.previsao import Previsao  # noqa: E402
from chargegrid.simulacao import ResultadoDia  # noqa: E402

COR_SOLAR = "#e0a800"
COR_EV = "#1b9e77"
COR_REDE = "#3b5b92"
COR_LIMITE = "#c0392b"
COR_PICO = "#f4b6b6"
DPI = 150


def _preparar(titulo: str, subtitulo: str):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.set_title(f"{titulo}\n{subtitulo}", fontsize=12, loc="left")
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 2))
    ax.set_xlabel("Hora do dia (dia simulado)")
    ax.grid(alpha=0.25)
    ax.axvspan(
        cfg.HORA_PICO_INICIO,
        cfg.HORA_PICO_FIM,
        color=COR_PICO,
        alpha=0.35,
        label="Tarifa de pico (18h–21h)",
    )
    return fig, ax


def _salvar(fig, ax, caminho: Path) -> None:
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
    fig.tight_layout()
    fig.savefig(caminho, dpi=DPI)
    plt.close(fig)


def grafico_potencia_dia(res: ResultadoDia, caminho: Path) -> None:
    t = res.telemetria
    x = t["minuto"] / 60
    fig, ax = _preparar("Potência ao longo do dia", f"seed {res.seed} — dados simulados")
    ax.fill_between(
        x, t["solar_kw"], step="post", color=COR_SOLAR, alpha=0.45, label="Geração solar"
    )
    # EVs mais grossa por baixo e rede mais fina por cima: à noite (sem sol) as duas coincidem
    ax.step(
        x, t["entregue_kw"], where="post", color=COR_EV, lw=4.5, label="Recarga entregue (EVs)"
    )
    ax.step(
        x, t["rede_kw"], where="post", color=COR_REDE, lw=1.6, label="Importação da rede"
    )
    ax.axhline(
        cfg.LIMITE_OPERACIONAL_KW,
        color=COR_LIMITE,
        ls="--",
        lw=1.6,
        label=f"Limite da rede ({cfg.LIMITE_OPERACIONAL_KW:.0f} kW)",
    )
    ax.set_ylabel("Potência (kW)")
    _salvar(fig, ax, caminho)


def grafico_origem_energia(res: ResultadoDia, caminho: Path) -> None:
    t = res.telemetria.assign(hora=res.telemetria["minuto"] // 60)
    h = cfg.PASSO_MIN / 60
    por_hora = (
        t.groupby("hora")[["solar_usada_kw", "rede_kw"]]
        .sum()
        .mul(h)
        .reindex(range(24), fill_value=0.0)
    )
    fig, ax = _preparar("Origem da energia entregue, por hora", "solar consumida primeiro")
    ax.bar(
        por_hora.index + 0.5,
        por_hora["solar_usada_kw"],
        width=0.8,
        color=COR_SOLAR,
        label="Solar",
    )
    ax.bar(
        por_hora.index + 0.5,
        por_hora["rede_kw"],
        width=0.8,
        color=COR_REDE,
        bottom=por_hora["solar_usada_kw"],
        label="Rede",
    )
    ax.set_ylabel("Energia (kWh por hora)")
    _salvar(fig, ax, caminho)


def grafico_solicitada_vs_alocada(res: ResultadoDia, caminho: Path) -> None:
    t = res.telemetria
    x = t["minuto"] / 60
    fig, ax = _preparar(
        "Controle de demanda: potência solicitada x alocada",
        "o corte proporcional mantém a importação dentro do limite",
    )
    ax.step(x, t["desejada_kw"], where="post", color=COR_LIMITE, lw=1.6, label="Solicitada")
    ax.step(x, t["alocada_kw"], where="post", color=COR_EV, lw=2, label="Alocada")
    ax.step(
        x, t["teto_kw"], where="post", color="#555555", lw=1, ls=":", label="Teto (limite + solar)"
    )
    ax.fill_between(
        x,
        t["alocada_kw"],
        t["desejada_kw"],
        where=t["em_corte"].to_numpy(),
        step="post",
        color=COR_LIMITE,
        alpha=0.3,
        label="Potência cortada",
    )
    ax.set_ylabel("Potência total dos EVs (kW)")
    _salvar(fig, ax, caminho)


def grafico_previsao(res: ResultadoDia, prev: Previsao, caminho: Path) -> None:
    ph = prev.por_hora
    real = (
        res.telemetria.assign(hora=res.telemetria["minuto"] // 60)
        .groupby("hora")["desejada_kw"]
        .mean()
        .reindex(range(24), fill_value=0.0)
    )
    centro = ph["hora"] + 0.5
    ini, fim, _ = prev.janela_pico
    fig, ax = _preparar(
        "Previsão de demanda por hora (média histórica) x dia simulado",
        "estatística simples, não aprendizado de máquina",
    )
    ax.fill_between(
        centro,
        (ph["media_kw"] - ph["desvio_kw"]).clip(lower=0),
        ph["media_kw"] + ph["desvio_kw"],
        color=COR_REDE,
        alpha=0.2,
        label="Previsão ± 1 desvio",
    )
    ax.plot(centro, ph["media_kw"], color=COR_REDE, lw=2, label="Previsão (média)")
    ax.plot(
        real.index + 0.5,
        real.values,
        color=COR_EV,
        lw=2,
        marker="o",
        ms=4,
        label="Dia simulado (real)",
    )
    ax.axhline(cfg.LIMITE_OPERACIONAL_KW, color=COR_LIMITE, ls="--", label="Limite da rede")
    ax.axvspan(ini, fim, color="#999999", alpha=0.15, label=f"Pico previsto {ini}h–{fim}h")
    ax.set_ylabel("Demanda desejada média (kW)")
    _salvar(fig, ax, caminho)


def gerar_graficos(res: ResultadoDia, prev: Previsao, pasta: Path | str) -> list[Path]:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = [
        pasta / "01_potencia_dia.png",
        pasta / "02_origem_energia.png",
        pasta / "03_solicitada_vs_alocada.png",
        pasta / "04_previsao_pico.png",
    ]
    grafico_potencia_dia(res, caminhos[0])
    grafico_origem_energia(res, caminhos[1])
    grafico_solicitada_vs_alocada(res, caminhos[2])
    grafico_previsao(res, prev, caminhos[3])
    return caminhos
