"""Validações pequenas: fórmulas conhecidas e integridade da amostra real."""
import ast
import json
import unittest

import networkx as nx
import pandas as pd

import projeto1 as p


class TestProjeto(unittest.TestCase):
    def test_centralidades_em_caminho_com_isolado(self):
        # Caminho 0-1-2-3 e um isolado. Resultados calculáveis à mão.
        grafo = nx.path_graph(4)
        grafo.add_node(4)
        tabela = p.calcular_metricas(grafo).set_index("no")
        self.assertAlmostEqual(tabela.loc[1, "centralidade_grau"], 2 / 4)
        self.assertAlmostEqual(tabela.loc[1, "intermediacao"], 2 / 6)
        self.assertAlmostEqual(tabela.loc[0, "proximidade"], (3 / 4) * (3 / 6))
        self.assertAlmostEqual(tabela.loc[1, "proximidade"], (3 / 4) * (3 / 4))
        self.assertAlmostEqual(tabela.loc[0, "autovetor"], 0.371748034, places=7)
        self.assertAlmostEqual(tabela.loc[1, "autovetor"], 0.601500955, places=7)
        for coluna in p.METRICAS:
            self.assertEqual(tabela.loc[4, coluna], 0)

    def test_amostra_salva_e_subgrafo_induzido(self):
        rede = p.construir_rede_completa(p.PASTA_DADOS)
        nos = pd.read_csv(p.PASTA_RESULTADOS / "nos.csv")["no"].tolist()
        arestas = pd.read_csv(p.PASTA_RESULTADOS / "arestas.csv")
        self.assertEqual((len(rede), rede.number_of_edges()), (4039, 88234))
        self.assertEqual(len(nos), 404)
        self.assertEqual(len(set(nos)), 404)
        self.assertEqual(set(nos), set(p.sortear_nos(rede, 404, p.SEMENTE)))
        esperado = {frozenset(e) for e in rede.subgraph(nos).edges()}
        salvo = {frozenset(e) for e in arestas.itertuples(index=False, name=None)}
        self.assertEqual(salvo, esperado)

    def test_comunidades_autovetor_e_exportacao(self):
        nos = pd.read_csv(p.PASTA_RESULTADOS / "nos.csv")
        arestas = pd.read_csv(p.PASTA_RESULTADOS / "arestas.csv")
        metricas = pd.read_csv(p.PASTA_RESULTADOS / "metricas.csv").set_index("no")
        grafo = p.construir_grafo(nos, arestas)
        self.assertEqual(set(metricas.index), set(grafo))
        self.assertFalse(metricas.isna().any().any())
        comunidades = [set(grupo.index) for _, grupo in metricas.groupby("comunidade")]
        self.assertEqual(set().union(*comunidades), set(grafo))
        componentes = list(nx.connected_components(grafo))
        for comunidade in comunidades:
            self.assertTrue(any(comunidade <= componente for componente in componentes))
        for no in nx.isolates(grafo):
            self.assertEqual(len(metricas[metricas.comunidade == metricas.loc[no, "comunidade"]]), 1)
        resumo = json.loads((p.PASTA_RESULTADOS / "resumo.json").read_text())
        self.assertAlmostEqual(nx.community.modularity(grafo, comunidades), resumo["modularidade"])
        # Verifica a equação Ax = lambda*x, sem depender da chamada do algoritmo.
        x = metricas["autovetor"].to_dict()
        ax = {no: sum(x[v] for v in grafo[no]) for no in grafo}
        norma2 = sum(v * v for v in x.values())
        autovalor = sum(x[no] * ax[no] for no in grafo) / norma2
        self.assertAlmostEqual(norma2, 1, places=7)
        self.assertLess(max(abs(ax[no] - autovalor * x[no]) for no in grafo), 1e-7)
        exportado = nx.read_graphml(p.PASTA_RESULTADOS / "grafo.graphml", node_type=int)
        self.assertEqual(set(exportado), set(grafo))
        self.assertEqual({frozenset(e) for e in exportado.edges}, {frozenset(e) for e in grafo.edges})
        for no in grafo:
            for coluna in p.METRICAS:
                self.assertAlmostEqual(exportado.nodes[no][coluna], metricas.loc[no, coluna])

    def test_notebook_tem_mesmas_funcoes_e_figuras(self):
        notebook = json.loads((p.PASTA_DADOS.parent / "projeto1.ipynb").read_text())
        def funcoes(codigo):
            return {n.name: ast.dump(n) for n in ast.parse(codigo).body if isinstance(n, ast.FunctionDef)}
        script = funcoes((p.PASTA_DADOS.parent / "projeto1.py").read_text())
        codigo = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
        embutidas = funcoes(codigo)
        for nome, funcao in script.items():
            if nome != "main":
                self.assertEqual(embutidas[nome], funcao, nome)
        codigo_cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertTrue(all(c["execution_count"] is not None for c in codigo_cells))
        saidas = [o for c in codigo_cells for o in c["outputs"]]
        self.assertFalse(any(o["output_type"] == "error" for o in saidas))
        self.assertEqual(sum("image/png" in o.get("data", {}) for o in saidas), 7)


if __name__ == "__main__":
    unittest.main()
