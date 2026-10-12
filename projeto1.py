import os
import random

import networkx as nx
import pandas as pd

PASTA_DADOS = "facebook"
QUANTIDADE_NOS = 404
SEMENTE = 2026


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


if __name__ == "__main__":
    main()
