"""Preenche o relatório LaTeX e compila o PDF com Tectonic, se solicitado."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from projeto1 import INTEGRANTES, METRICAS, PASTA_RESULTADOS, construir_grafo, ranking


def escapar_latex(texto):
    especiais = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                 "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}"}
    return "".join(especiais.get(c, c) for c in str(texto))


def numero(valor, casas=6):
    return f"{valor:.{casas}f}".replace(".", ",")


def definir_cores(comunidades):
    linhas = []
    for i in range(32):
        rgb = plt.get_cmap("viridis")(i / 31)[:3]
        linhas.append(f"\\definecolor{{met{i}}}{{rgb}}{{{rgb[0]:.4f},{rgb[1]:.4f},{rgb[2]:.4f}}}")
    paleta = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("tab20b").colors)
    paleta += list(plt.get_cmap("tab20c").colors)
    nao_unitarias = comunidades.query("quantidade_nos > 1").comunidade.tolist()
    for i, comunidade in enumerate(nao_unitarias):
        rgb = paleta[i] if len(nao_unitarias) <= 60 else plt.get_cmap("hsv")(i / len(nao_unitarias))[:3]
        linhas.append(f"\\definecolor{{com{comunidade}}}{{rgb}}{{{rgb[0]:.4f},{rgb[1]:.4f},{rgb[2]:.4f}}}")
    linhas += [r"\definecolor{isolado}{HTML}{BBBBBB}", r"\definecolor{barras}{HTML}{416B8C}"]
    return "\n".join(linhas)


def coordenadas(posicoes, centro, raios):
    xs, ys = zip(*posicoes.values())
    return {no: (centro[0] + raios[0] * (2 * (p[0] - min(xs)) / (max(xs) - min(xs)) - 1),
                 centro[1] + raios[1] * (2 * (p[1] - min(ys)) / (max(ys) - min(ys)) - 1))
            for no, p in posicoes.items()}


def desenhar_rede(grafo, pontos, cores):
    linhas = []
    for u, v in grafo.edges():
        x1, y1 = pontos[u]
        x2, y2 = pontos[v]
        linhas.append(f"\\draw[gray!45,line width=0.14pt] ({x1:.4f},{y1:.4f})--({x2:.4f},{y2:.4f});")
    # Nós maiores por último para manter os usuários centrais visíveis.
    for no in sorted(grafo, key=lambda n: (grafo.degree(n), n)):
        x, y = pontos[no]
        raio = 0.035 + 0.006 * math.sqrt(grafo.degree(no))
        linhas.append(f"\\fill[{cores[no]}] ({x:.4f},{y:.4f}) circle ({raio:.4f});")
    return linhas


def mapa_metrica(grafo, metricas, posicoes, metrica, titulo):
    tabela = metricas.set_index("no")
    maior = tabela[metrica].max()
    pontos = coordenadas(posicoes, (5.1, 2.85), (1.55, 1.6))
    cores = {no: f"met{round(31 * tabela.loc[no, metrica] / maior)}" for no in grafo}
    linhas = [r"\begin{tikzpicture}[x=1cm,y=1cm,font=\fontsize{10}{12}\selectfont]",
              r"\path[use as bounding box] (0,0) rectangle (7.65,5.25);"]
    linhas += desenhar_rede(grafo, pontos, cores)
    linhas.append(f"\\node[font=\\fontsize{{10}}{{12}}\\selectfont\\bfseries] at (5.1,5) {{{titulo}}};")
    for i, (_, linha) in enumerate(ranking(metricas, metrica, 5).iterrows()):
        no = int(linha["no"])
        x, y = pontos[no]
        altura = 4.55 - i * 0.85
        linhas.append(f"\\node[anchor=west] at (0.05,{altura:.3f}) {{{no}: {numero(linha[metrica], 4)}}};")
        linhas.append(f"\\draw[gray,line width=0.35pt] (2.8,{altura:.3f})--({x:.4f},{y:.4f});")
        destaque = 0.05 + 0.006 * math.sqrt(grafo.degree(no))
        linhas.append(f"\\draw[black,line width=0.3pt] ({x:.4f},{y:.4f}) circle ({destaque:.4f});")
    for i in range(32):
        y = 1.25 + i * 3.2 / 32
        linhas.append(f"\\fill[met{i}] (6.95,{y:.4f}) rectangle (7.1,{y+3.2/32:.4f});")
    for proporcao in (0, 0.5, 1):
        y = 1.25 + proporcao * 3.2
        linhas.append(f"\\node[anchor=west] at (7.13,{y:.4f}) {{{numero(maior * proporcao, 2)}}};")
    linhas.append(r"\end{tikzpicture}")
    return "\n".join(linhas)


def mapa_comunidades(grafo, metricas, comunidades, posicoes):
    pontos = coordenadas(posicoes, (7.8, 7.05), (4.9, 2.55))
    tabela = metricas.set_index("no")
    nao_unitarias = set(comunidades.query("quantidade_nos > 1").comunidade)
    cores = {no: f"com{int(tabela.loc[no, 'comunidade'])}"
             if tabela.loc[no, "comunidade"] in nao_unitarias else "isolado" for no in grafo}
    linhas = [r"\begin{tikzpicture}[x=1cm,y=1cm,font=\fontsize{10}{12}\selectfont]",
              r"\path[use as bounding box] (0,0) rectangle (15.65,10);"]
    linhas += desenhar_rede(grafo, pontos, cores)
    entradas = [(f"com{r.comunidade}", f"C{r.comunidade}: {r.quantidade_nos} nós")
                for r in comunidades.query("quantidade_nos > 1").itertuples()]
    entradas.append(("isolado", "Isolados (unitários)"))
    linhas_por_coluna = math.ceil(len(entradas) / 4)
    for i, (cor, texto) in enumerate(entradas):
        coluna, linha = divmod(i, linhas_por_coluna)
        x, y = coluna * 3.9, 3.65 - linha * 0.42
        linhas.append(f"\\fill[{cor}] ({x+0.12:.3f},{y:.3f}) circle (0.065);")
        linhas.append(f"\\node[anchor=west] at ({x+0.3:.3f},{y:.3f}) {{{texto}}};")
    linhas.append(r"\end{tikzpicture}")
    return "\n".join(linhas)


def distribuicoes(metricas, comunidades):
    linhas = [r"\begin{tikzpicture}[x=1cm,y=1cm,font=\fontsize{10}{12}\selectfont]",
              r"\path[use as bounding box] (0,0) rectangle (15.4,3.8);"]
    frequencias = metricas.grau.value_counts().sort_index()
    conjuntos = [(0.8, frequencias, int(metricas.grau.max()) + 1, "Grau", "(a) Distribuição dos graus"),
                 (8.6, comunidades.set_index("comunidade").quantidade_nos,
                  len(comunidades), "Comunidade", "(b) Tamanhos das comunidades")]
    for inicio, valores, quantidade, eixo_x, titulo in conjuntos:
        maximo = math.ceil(valores.max() / 20) * 20
        linhas.append(f"\\draw ({inicio:.3f},0.8)--({inicio+6.5:.3f},0.8);")
        linhas.append(f"\\draw ({inicio:.3f},0.8)--({inicio:.3f},3.3);")
        linhas.append(f"\\node[rotate=90] at ({inicio-1:.3f},2.05) {{Nós}};")
        for indice, valor in valores.items():
            x = inicio + indice / quantidade * 6.5
            largura = 6.5 / quantidade * 0.8
            altura = valor / maximo * 2.5
            linhas.append(f"\\fill[barras] ({x:.4f},0.8) rectangle ({x+largura:.4f},{0.8+altura:.4f});")
        for fracao in (0, 0.5, 1):
            y = 0.8 + fracao * 2.5
            linhas.append(f"\\node[anchor=east] at ({inicio-0.08:.3f},{y:.3f}) {{{int(maximo*fracao)}}};")
        for indice in range(0, quantidade, 20):
            x = inicio + indice / quantidade * 6.5
            linhas.append(f"\\node at ({x:.3f},0.5) {{{indice}}};")
        linhas.append(f"\\node at ({inicio+3.25:.3f},0.1) {{{eixo_x}}};")
        linhas.append(f"\\node at ({inicio+3.25:.3f},3.6) {{{titulo}}};")
    linhas.append(r"\end{tikzpicture}")
    return "\n".join(linhas)


def gerar_relatorio(pasta=PASTA_RESULTADOS, destino=None, compilar=True):
    raiz = Path(__file__).resolve().parent
    pasta = Path(pasta)
    destino = Path(destino) if destino else raiz / "output/pdf/relatorio.pdf"
    resumo = json.loads((pasta / "resumo.json").read_text(encoding="utf-8"))
    metricas = pd.read_csv(pasta / "metricas.csv")
    comunidades = pd.read_csv(pasta / "comunidades.csv")
    grafo = construir_grafo(pd.read_csv(pasta / "nos.csv"), pd.read_csv(pasta / "arestas.csv"))
    posicoes = nx.spring_layout(grafo, seed=resumo["semente"], k=0.28, iterations=200)
    lideres = {m: ranking(metricas, m, 1).iloc[0] for m in METRICAS}
    grau, autovetor = lideres["centralidade_grau"], lideres["autovetor"]
    mapas = [mapa_metrica(grafo, metricas, posicoes, m, t.replace("Centralidade de ", "").capitalize())
             for m, t in METRICAS.items()]
    mapas_tex = (r"\begin{minipage}[t]{0.485\textwidth}\centering" + mapas[0] + r"\par\medskip"
                 + mapas[2] + r"\end{minipage}\hfill\begin{minipage}[t]{0.485\textwidth}\centering"
                 + mapas[1] + r"\par\medskip" + mapas[3] + r"\end{minipage}")
    dados = {
        "CORES": definir_cores(comunidades),
        "AUTORES": "\n".join(escapar_latex(n) + " (matrícula " + escapar_latex(m) + ")" + r"\\" for n, m in INTEGRANTES),
        "AUTORES_PDF": escapar_latex("; ".join(n for n, _ in INTEGRANTES if "preencher" not in n)),
        "SEMENTE": str(resumo["semente"]),
        "RESUMO": "\n".join(escapar_latex(n) + " & " + v + r"\\" for n, v in [
            ("Nós / arestas", f"{resumo['nos']} / {resumo['arestas']}"),
            ("Densidade", numero(resumo["densidade"])), ("Grau médio", numero(resumo["grau_medio"], 4)),
            ("Isolados / componentes conexas", f"{resumo['isolados']} / {resumo['componentes']}"),
            ("Maior componente", f"{resumo['maior_componente']} nós")]),
        "LIDERES": "\n".join(t.replace("Centralidade de ", "").capitalize() + " & "
                              + str(int(lideres[m]["no"])) + " & " + numero(lideres[m][m]) + r"\\"
                              for m, t in METRICAS.items()),
        "LIDER_GRAU": str(int(grau["no"])), "GRAU_LIDER": str(int(grau["grau"])),
        "COMPONENTE_GRAU": str(int(grau["tamanho_componente"])),
        "LIDER_AUTOVETOR": str(int(autovetor["no"])),
        "COMPONENTE_AUTOVETOR": str(int(autovetor["tamanho_componente"])),
        "AUTOVETORES_PEQUENOS": str(int((metricas.autovetor < 1e-6).sum())),
        "NUM_COMUNIDADES": str(resumo["comunidades"]), "NUM_COMPONENTES": str(resumo["componentes"]),
        "MODULARIDADE": numero(resumo["modularidade"]),
        "COMUNIDADES_UNITARIAS": str(resumo["comunidades_unitarias"]),
        "VERSAO_NETWORKX": resumo["networkx"], "MAPAS": mapas_tex,
        "MAPA_COMUNIDADES": mapa_comunidades(grafo, metricas, comunidades, posicoes),
        "DISTRIBUICOES": distribuicoes(metricas, comunidades),
    }
    texto = (raiz / "relatorio_base.tex").read_text(encoding="utf-8")
    for chave, valor in dados.items():
        texto = texto.replace(f"%%{chave}%%", valor)
    if re.search(r"%%[A-Z_]+%%", texto):
        raise ValueError("Há campos não preenchidos no modelo LaTeX.")
    fonte = raiz / "relatorio.tex"
    fonte.write_text(texto, encoding="utf-8")
    if not compilar:
        return fonte
    tectonic = raiz / ".tools/tectonic"
    executavel = str(tectonic) if tectonic.is_file() else shutil.which("tectonic")
    if not executavel:
        raise FileNotFoundError("Instale Tectonic ou use --somente-tex e compile relatorio.tex no Overleaf.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    ambiente = os.environ.copy()
    ambiente["XDG_CACHE_HOME"] = str(raiz / ".tools/cache")
    subprocess.run([executavel, "--untrusted", "--keep-logs", "--outdir", str(destino.parent), str(fonte)],
                   env=ambiente, check=True)
    if destino.name != "relatorio.pdf":
        shutil.move(str(destino.parent / "relatorio.pdf"), str(destino))
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--somente-tex", action="store_true", help="gera o LaTeX sem compilar o PDF")
    argumentos = parser.parse_args()
    print("Relatório salvo em:", gerar_relatorio(compilar=not argumentos.somente_tex))
