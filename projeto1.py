import os
import random
import json
from pathlib import Path

import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import ConnectionPatch

PASTA_DADOS = Path(__file__).resolve().parent / "facebook"
QUANTIDADE_NOS = 404
SEMENTE = 2026
PASTA_RESULTADOS = Path(__file__).resolve().parent / "resultados"
INTEGRANTES = [
    ("Igor Araújo Rodrigues", "242001517"),
    ("Eduardo Marques Pereira", "211021004"),
    ("Terceiro integrante: preencher", "preencher"),
]
METRICAS = {
    "centralidade_grau": "Centralidade de grau",
    "intermediacao": "Centralidade de intermediação",
    "proximidade": "Centralidade de proximidade",
    "autovetor": "Centralidade de autovetor",
}


# 1. Coletar dados

def listar_egos(pasta):
    return sorted(int(nome.split(".")[0]) for nome in os.listdir(pasta) if nome.endswith(".edges"))


def ler_arestas_ego(pasta, ego):
    arestas = []
    with open(os.path.join(pasta, f"{ego}.edges")) as arquivo:
        for linha in arquivo:
            u, v = linha.split()
            arestas.append((int(u), int(v)))
    # O ego é ligado a todos os amigos listados em X.feat
    with open(os.path.join(pasta, f"{ego}.feat")) as arquivo:
        for linha in arquivo:
            amigo = int(linha.split()[0])
            arestas.append((ego, amigo))
    return arestas


def construir_rede_completa(pasta):
    rede_completa = nx.Graph()
    for ego in listar_egos(pasta):
        rede_completa.add_edges_from(ler_arestas_ego(pasta, ego))
    return rede_completa


def sortear_nos(rede_completa, quantidade, semente):
    sorteador = random.Random(semente)
    return sorteador.sample(sorted(rede_completa.nodes()), quantidade)


def extrair_arestas(rede_completa, nos_sorteados):
    conjunto_sorteados = set(nos_sorteados)
    return [
        (u, v) for u, v in rede_completa.edges() if u in conjunto_sorteados and v in conjunto_sorteados
    ]


# 2. Construir grafo

def construir_grafo(tabela_nos, tabela_arestas):
    grafo = nx.Graph()
    grafo.add_nodes_from(tabela_nos["no"])
    grafo.add_edges_from(tabela_arestas.itertuples(index=False, name=None))
    return grafo


# 3. Centralidades e comunidades

def calcular_metricas(grafo):
    # As medidas são calculadas sobre os 404 nós, incluindo os isolados.
    grau = nx.degree_centrality(grafo)
    intermediacao = nx.betweenness_centrality(grafo, normalized=True)
    # A correção WF reduz o valor de nós que alcançam apenas uma pequena componente.
    proximidade = nx.closeness_centrality(grafo, wf_improved=True)
    autovetor = nx.eigenvector_centrality(grafo, max_iter=1000, tol=1e-10)
    # Para isolados, o valor teórico é zero; eliminamos resíduos numéricos.
    for no in nx.isolates(grafo):
        autovetor[no] = 0.0

    componentes = sorted(nx.connected_components(grafo), key=lambda c: (-len(c), min(c)))
    componente_por_no = {no: i for i, c in enumerate(componentes) for no in c}
    return pd.DataFrame([
        {
            "no": no, "grau": grafo.degree(no),
            "centralidade_grau": grau[no], "intermediacao": intermediacao[no],
            "proximidade": proximidade[no], "autovetor": autovetor[no],
            "componente": componente_por_no[no],
            "tamanho_componente": len(componentes[componente_por_no[no]]),
        }
        for no in sorted(grafo)
    ])


def detectar_comunidades(grafo, semente):
    comunidades = nx.community.louvain_communities(grafo, seed=semente, resolution=1)
    # A numeração por tamanho facilita a leitura e não altera a partição.
    comunidades.sort(key=lambda c: (-len(c), min(c)))
    comunidade_por_no = {no: i for i, c in enumerate(comunidades) for no in c}
    tabela = pd.DataFrame([
        {"comunidade": i, "quantidade_nos": len(c),
         "arestas_internas": grafo.subgraph(c).number_of_edges()}
        for i, c in enumerate(comunidades)
    ])
    modularidade = nx.community.modularity(grafo, comunidades)
    return comunidade_por_no, tabela, modularidade


def ranking(tabela_metricas, metrica, quantidade=10):
    # Em caso de empate, ordenamos pelo identificador do nó.
    return tabela_metricas.sort_values([metrica, "no"], ascending=[False, True]).head(quantidade)


# 4. Figuras

def salvar_figura(figura, pasta, nome):
    pasta.mkdir(parents=True, exist_ok=True)
    figura.savefig(pasta / nome, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figura)


def desenhar_base(grafo, posicoes, eixo):
    nx.draw_networkx_edges(grafo, posicoes, ax=eixo, alpha=0.22, width=0.6)
    eixo.set_axis_off()
    eixo.margins(0.15)


def plotar_metricas(grafo, tabela_metricas, posicoes, pasta, compacto=False):
    tabela = tabela_metricas.set_index("no")
    for metrica, titulo in METRICAS.items():
        figura, eixo = plt.subplots(figsize=(5.2, 4) if compacto else (11, 8))
        desenhar_base(grafo, posicoes, eixo)
        valores = [tabela.loc[no, metrica] for no in grafo]
        pontos = nx.draw_networkx_nodes(
            grafo, posicoes, ax=eixo, node_color=valores, cmap="viridis",
            node_size=[12 + 2 * grafo.degree(no) if compacto else 25 + 5 * grafo.degree(no)
                       for no in grafo], linewidths=0.3,
            edgecolors="white",
        )
        barra = figura.colorbar(pontos, ax=eixo, shrink=0.7, label="" if compacto else titulo)
        if compacto:
            barra.ax.tick_params(labelsize=12)
            barra.ax.yaxis.set_major_locator(plt.MaxNLocator(3))
            # Reservamos uma coluna à esquerda para os valores, sem cobrir os nós.
            figura.subplots_adjust(left=0.4, right=0.9, top=0.85, bottom=0.08)
            eixo.set_aspect("equal", adjustable="box")
        maiores = ranking(tabela_metricas, metrica, 5)
        # Anotações em coluna: evitam rótulos sobrepostos em nós muito próximos.
        for i, (_, linha) in enumerate(maiores.iterrows()):
            no = int(linha["no"])
            if compacto:
                figura.text(0.025, 0.82 - i * 0.145, f"{no}: {linha[metrica]:.4f}",
                            fontsize=13, va="center",
                            bbox=dict(boxstyle="round", fc="white", ec="0.7"))
                figura.add_artist(ConnectionPatch(
                    xyA=(0.31, 0.82 - i * 0.145), coordsA=figura.transFigure,
                    xyB=posicoes[no], coordsB=eixo.transData,
                    color="0.35", lw=0.8, shrinkB=3,
                ))
            else:
                eixo.annotate(
                    f"Nó {no}: {linha[metrica]:.4f}", xy=posicoes[no], xycoords="data",
                    xytext=(0.02, 0.97 - i * 0.065), textcoords="axes fraction",
                    fontsize=10,
                    bbox=dict(boxstyle="round", fc="white", ec="0.7", alpha=0.95),
                    arrowprops=dict(arrowstyle="-", color="0.35", lw=0.8),
                )
        eixo.set_title(titulo.replace("Centralidade de ", "").capitalize() if compacto
                       else titulo + " - cinco maiores valores", fontsize=14 if compacto else 13)
        if not compacto:
            figura.text(0.5, 0.02, "404 nós; tamanho aumenta com o grau; mesma posição em todos os mapas.",
                        ha="center", fontsize=9)
        salvar_figura(figura, pasta, f"{metrica}.png")


def plotar_comunidades(grafo, tabela_metricas, tabela_comunidades, posicoes, pasta, compacto=False):
    figura, eixo = plt.subplots(figsize=(7.2, 4.4) if compacto else (12, 8))
    desenhar_base(grafo, posicoes, eixo)
    nao_unitarias = tabela_comunidades.query("quantidade_nos > 1")["comunidade"].tolist()
    paleta = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("tab20b").colors)
    paleta += list(plt.get_cmap("tab20c").colors)
    # Se outra amostra exceder 60 comunidades não unitárias, usamos cores adicionais.
    if len(nao_unitarias) > len(paleta):
        paleta = [plt.get_cmap("hsv")(i / len(nao_unitarias)) for i in range(len(nao_unitarias))]
    cores = {c: paleta[i] for i, c in enumerate(nao_unitarias)}
    tabela = tabela_metricas.set_index("no")
    nx.draw_networkx_nodes(
        grafo, posicoes, ax=eixo,
        node_color=[cores.get(int(tabela.loc[no, "comunidade"]), "#bbbbbb") for no in grafo],
        node_size=[25 + 5 * grafo.degree(no) for no in grafo], edgecolors="white", linewidths=0.3,
    )
    legenda = [Line2D([0], [0], marker="o", linestyle="", color=cores[int(linha.comunidade)],
                      label=f"C{linha.comunidade}: {linha.quantidade_nos} nós")
               for linha in tabela_comunidades.query("quantidade_nos > 1").itertuples()]
    legenda.append(Line2D([0], [0], marker="o", linestyle="", color="#bbbbbb",
                         label="Isolados (unitários)" if compacto else "Isolados: cada nó é uma comunidade"))
    if compacto:
        eixo.legend(handles=legenda, loc="upper center", bbox_to_anchor=(0.5, -0.02),
                    ncol=4, fontsize=12, columnspacing=0.8, handlelength=1,
                    handletextpad=0.4, frameon=False)
    else:
        eixo.legend(handles=legenda, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=7)
    eixo.set_title("Comunidades detectadas por Louvain", fontsize=13)
    salvar_figura(figura, pasta, "comunidades.png")


def plotar_resumos(tabela_metricas, tabela_comunidades, pasta):
    figura, eixos = plt.subplots(2, 2, figsize=(12, 9))
    for eixo, (metrica, titulo) in zip(eixos.flat, METRICAS.items()):
        maiores = ranking(tabela_metricas, metrica).iloc[::-1]
        barras = eixo.barh(maiores["no"].astype(str), maiores[metrica], color="steelblue")
        eixo.bar_label(barras, fmt="%.4f", padding=3, fontsize=8)
        eixo.set_title(titulo, fontsize=11)
        eixo.set_xlabel("Valor")
        eixo.set_ylabel("Nó")
        eixo.set_xlim(0, max(maiores[metrica].max() * 1.35, 0.01))
    figura.suptitle("Dez maiores valores por centralidade")
    figura.tight_layout()
    salvar_figura(figura, pasta, "rankings.png")

    figura, eixos = plt.subplots(1, 2, figsize=(12, 4))
    frequencias = tabela_metricas["grau"].value_counts().sort_index()
    eixos[0].bar(frequencias.index, frequencias.values, color="steelblue")
    eixos[0].set(xlabel="Grau", ylabel="Quantidade de nós", title="Distribuição dos graus")
    eixos[1].bar(tabela_comunidades["comunidade"], tabela_comunidades["quantidade_nos"], color="seagreen")
    eixos[1].set(xlabel="Comunidade", ylabel="Quantidade de nós", title="Tamanhos das comunidades")
    figura.tight_layout()
    salvar_figura(figura, pasta, "distribuicoes.png")


def salvar_resultados(grafo, tabela_nos, tabela_arestas, tabela_metricas,
                      tabela_comunidades, modularidade, pasta, semente):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    tabela_nos.to_csv(pasta / "nos.csv", index=False)
    tabela_arestas.to_csv(pasta / "arestas.csv", index=False)
    tabela_metricas.to_csv(pasta / "metricas.csv", index=False)
    tabela_comunidades.to_csv(pasta / "comunidades.csv", index=False)
    resumo = {
        "semente": semente, "nos": len(grafo), "arestas": grafo.number_of_edges(),
        "densidade": nx.density(grafo), "isolados": nx.number_of_isolates(grafo),
        "componentes": nx.number_connected_components(grafo),
        "maior_componente": len(max(nx.connected_components(grafo), key=len)),
        "grau_medio": sum(dict(grafo.degree()).values()) / len(grafo),
        "comunidades": len(tabela_comunidades), "modularidade": modularidade,
        "comunidades_unitarias": int((tabela_comunidades["quantidade_nos"] == 1).sum()),
        "networkx": nx.__version__, "pandas": pd.__version__,
    }
    (pasta / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    # O GraphML permite abrir os resultados no Gephi, se o grupo quiser.
    atributos = tabela_metricas.set_index("no").to_dict(orient="index")
    nx.set_node_attributes(grafo, atributos)
    nx.write_graphml(grafo, pasta / "grafo.graphml")
    return resumo


def main():
    rede_completa = construir_rede_completa(PASTA_DADOS)
    print("Nós da rede completa:", rede_completa.number_of_nodes())
    print("Arestas da rede completa:", rede_completa.number_of_edges())

    nos_sorteados = sortear_nos(rede_completa, QUANTIDADE_NOS, SEMENTE)
    arestas_sorteadas = extrair_arestas(rede_completa, nos_sorteados)
    print("Nós sorteados:", len(nos_sorteados))
    print("Arestas extraídas:", len(arestas_sorteadas))

    tabela_nos = pd.DataFrame({"no": sorted(nos_sorteados)})
    tabela_arestas = pd.DataFrame(arestas_sorteadas, columns=["origem", "destino"])

    grafo = construir_grafo(tabela_nos, tabela_arestas)
    print("Número de nós:", grafo.number_of_nodes())
    print("Número de arestas:", grafo.number_of_edges())
    print("Densidade:", round(nx.density(grafo), 6))
    print("Nós isolados:", nx.number_of_isolates(grafo))
    print("Componentes conexas:", nx.number_connected_components(grafo))
    print("Tamanho da maior componente:", len(max(nx.connected_components(grafo), key=len)))

    tabela_graus = pd.DataFrame(grafo.degree(), columns=["no", "grau"])
    print(tabela_graus["grau"].describe())

    tabela_metricas = calcular_metricas(grafo)
    comunidade_por_no, tabela_comunidades, modularidade = detectar_comunidades(grafo, SEMENTE)
    tabela_metricas["comunidade"] = tabela_metricas["no"].map(comunidade_por_no)
    salvar_resultados(grafo, tabela_nos, tabela_arestas, tabela_metricas,
                      tabela_comunidades, modularidade, PASTA_RESULTADOS, SEMENTE)
    print("Comunidades Louvain:", len(tabela_comunidades))
    print("Modularidade:", round(modularidade, 6))
    for metrica, titulo in METRICAS.items():
        print("\n" + titulo)
        print(ranking(tabela_metricas, metrica, 5)[["no", metrica]].to_string(index=False))

    posicoes = nx.spring_layout(grafo, seed=SEMENTE, k=0.28, iterations=200)
    pasta_figuras = PASTA_RESULTADOS / "figuras"
    plotar_metricas(grafo, tabela_metricas, posicoes, pasta_figuras)
    plotar_comunidades(grafo, tabela_metricas, tabela_comunidades, posicoes, pasta_figuras)
    plotar_resumos(tabela_metricas, tabela_comunidades, pasta_figuras)
    print("\nResultados salvos em:", PASTA_RESULTADOS)


if __name__ == "__main__":
    main()
