import logging
import os

import matplotlib.pyplot as plt


logger = logging.getLogger(__name__)
YEAR_COLUMN = "Año"


def generate_visualizations(df, cagrs, base_year, start_year, end_year, temp_dir):
    """Genera los graficos y los guarda en el directorio temporal."""
    image_paths = []
    inflation_df = df.loc[df[YEAR_COLUMN] > start_year].copy()

    path1 = os.path.join(temp_dir, "plot1.png")
    plt.figure(figsize=(12, 7))
    plt.plot(
        df[YEAR_COLUMN],
        df["Salario_Minimo_Real"],
        marker="o",
        label="Salario minimo (valor real)",
        color="skyblue",
        linewidth=3,
        linestyle="-",
    )
    plt.plot(
        df[YEAR_COLUMN],
        df["UMA_Real"],
        marker="o",
        label="UMA valor real",
        color="green",
        linewidth=3,
        linestyle="-",
    )
    plt.plot(
        df[YEAR_COLUMN],
        df["Salario_Minimo_Diario"],
        marker="o",
        label="Salario minimo nominal",
        color="orange",
        linewidth=3,
        linestyle="--",
    )
    plt.plot(
        df[YEAR_COLUMN],
        df["UMA_diario"],
        marker="o",
        label="UMA valor nominal",
        color="red",
        linewidth=3,
        linestyle="--",
    )
    plt.title("Comparativo de la evolucion: Salario Minimo vs. UMA", fontsize=16, fontweight="bold")
    plt.xlabel("Año", fontsize=12)
    plt.ylabel("Valor Diario (MXN ajustado por inflacion)", fontsize=12)
    plt.legend(loc="upper left", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.xticks(df[YEAR_COLUMN])

    annotation_year = start_year + 3 if (start_year + 3) <= end_year else start_year
    try:
        annotation_value = df["Salario_Minimo_Real"].loc[
            df[YEAR_COLUMN] == annotation_year
        ].values[0]
        plt.annotate(
            "Incremento acelerado",
            xy=(annotation_year, annotation_value),
            xytext=(annotation_year, annotation_value + 20),
            arrowprops=dict(facecolor="black", shrink=0.05),
            fontsize=10,
            ha="center",
        )
    except IndexError:
        pass
    plt.savefig(path1, format="png", bbox_inches="tight")
    plt.close()
    image_paths.append(path1)

    path2 = os.path.join(temp_dir, "plot2.png")
    plt.figure(figsize=(12, 6))
    plt.plot(
        df[YEAR_COLUMN],
        df["Salario_Minimo_Real_Normalizado"],
        marker="o",
        label=f"Salario Real (Base {base_year} = 100)",
        color="skyblue",
        linewidth=3,
    )
    plt.plot(
        df[YEAR_COLUMN],
        df["UMA_Real_Normalizado"],
        marker="o",
        label=f"UMA Real (Base {base_year} = 100)",
        color="green",
        linewidth=3,
    )
    plt.title(f"Salario Minimo vs. UMA (Base Año {base_year})", fontsize=16)
    plt.xlabel("Año", fontsize=12)
    plt.ylabel(f"Indice ({base_year} = 100)", fontsize=12)
    plt.legend()
    plt.grid(True)
    plt.xticks(df[YEAR_COLUMN])
    plt.savefig(path2, format="png", bbox_inches="tight")
    plt.close()
    image_paths.append(path2)

    path3 = os.path.join(temp_dir, "plot3.png")
    cagr_values = [
        cagrs["nominal_salario"],
        cagrs["real_salario"],
        cagrs["nominal_uma"],
        cagrs["real_uma"],
    ]
    labels = ["Salario Nominal", "Salario Real", "UMA Nominal", "UMA Real"]
    colors = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd"]
    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, [c * 100 for c in cagr_values], color=colors)
    plt.title(f"Crecimiento Anual Compuesto (CAGR) {start_year}-{end_year}", fontsize=16, fontweight="bold")
    plt.ylabel("CAGR (%)", fontsize=12)
    plt.ylim(0, max([c * 100 for c in cagr_values]) + 5)
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    for bar in bars:
        yval = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            yval + 0.5,
            f"{yval:.2f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    plt.savefig(path3, format="png", bbox_inches="tight")
    plt.close()
    image_paths.append(path3)

    path4 = os.path.join(temp_dir, "plot4.png")
    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax1.plot(inflation_df[YEAR_COLUMN], inflation_df["inflacion"], marker="o", color="green", linewidth=3, label="Inflacion Anual (%)")
    ax1.set_xlabel("Año", fontsize=12)
    ax1.set_ylabel("Inflacion Anual (%)", color="green", fontsize=12)
    ax1.tick_params(axis="y", labelcolor="green")
    ax1.set_title("Inflacion Anual vs. Tasa de Referencia de Banxico", fontsize=16, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(
        inflation_df[YEAR_COLUMN],
        inflation_df["Tasa_Referencia_Banxico"],
        marker="s",
        color="red",
        linestyle="--",
        linewidth=3,
        label="Tasa de Referencia Banxico (%)",
    )
    ax2.set_ylabel("Tasa de Referencia Banxico (%)", color="red", fontsize=12)
    ax2.tick_params(axis="y", labelcolor="red")
    ax2.legend(loc="upper right")
    plt.savefig(path4, format="png", bbox_inches="tight")
    plt.close(fig)
    image_paths.append(path4)

    path5 = os.path.join(temp_dir, "plot5.png")
    fig, (ax1_dash, ax2_dash, ax3_dash) = plt.subplots(3, 1, figsize=(12, 15))
    fig.suptitle(f"Analisis Economico Integral ({start_year}-{end_year})", fontsize=20, fontweight="bold")

    ax1_dash.plot(df[YEAR_COLUMN], df["Salario_Minimo_Real"], marker="o", label="Poder Adquisitivo (Salario)", color="skyblue", linewidth=3)
    ax1_dash.plot(df[YEAR_COLUMN], df["UMA_Real"], marker="o", label="Poder Adquisitivo (UMA)", color="green", linewidth=3, linestyle="--")
    ax1_dash.set_title("Evolucion del Poder Adquisitivo: Salario Minimo vs. UMA", fontsize=14)
    ax1_dash.set_ylabel(f"Valor Diario (MXN a precios de {base_year})", fontsize=12)
    ax1_dash.legend(loc="upper left", fontsize=10)
    ax1_dash.grid(True, linestyle="--", alpha=0.6)
    ax1_dash.set_xticks(df[YEAR_COLUMN])

    bars = ax2_dash.bar(labels, [c * 100 for c in cagr_values], color=colors)
    ax2_dash.set_title("Crecimiento Anual Compuesto (CAGR)", fontsize=14)
    ax2_dash.set_ylabel("CAGR (%)", fontsize=12)
    ax2_dash.grid(axis="y", linestyle="--", alpha=0.7)
    ax2_dash.set_ylim(0, max([c * 100 for c in cagr_values]) + 5)
    for bar in bars:
        yval = bar.get_height()
        ax2_dash.text(
            bar.get_x() + bar.get_width() / 2.0,
            yval + 0.5,
            f"{yval:.2f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax3_dash.plot(inflation_df[YEAR_COLUMN], inflation_df["inflacion"], marker="o", color="green", linewidth=3, label="Inflacion Anual (%)")
    ax3_dash.set_ylabel("Inflacion Anual (%)", color="green", fontsize=12)
    ax3_dash.tick_params(axis="y", labelcolor="green")
    ax3_dash.set_title("Inflacion Anual vs. Tasa de Referencia de Banxico", fontsize=14)
    ax3_dash.grid(True, linestyle="--", alpha=0.6)
    ax3_dash.legend(loc="upper left")
    ax3_dash.set_xticks(inflation_df[YEAR_COLUMN])
    ax3_twin = ax3_dash.twinx()
    ax3_twin.plot(inflation_df[YEAR_COLUMN], inflation_df["Tasa_Referencia_Banxico"], marker="s", color="red", linestyle="--", linewidth=3, label="Tasa de Referencia Banxico (%)")
    ax3_twin.set_ylabel("Tasa de Referencia Banxico (%)", color="red", fontsize=12)
    ax3_twin.tick_params(axis="y", labelcolor="red")
    ax3_twin.legend(loc="upper right")
    ax3_dash.set_xlabel("Año", fontsize=12)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(path5, format="png", bbox_inches="tight")
    plt.close(fig)
    image_paths.append(path5)

    logger.info("Graficos generados y guardados en directorio temporal.")
    return image_paths
