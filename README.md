# Análise de redes sociais com grafos

Projeto 1 de Teoria e Aplicação de Grafos, Turma 01, UnB, 2026/2.

| Integrante | Matrícula |
|---|---|
| Igor Araújo Rodrigues | 242001517 |
| Eduardo Marques Pereira | 211021004 |
| Matheus Barbosa e Silva | 190113987 |

## Executar

Use Python 3.12 ou superior. Os dados já estão em `facebook/`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python projeto1.py
.venv/bin/python gerar_relatorio.py
.venv/bin/jupyter notebook projeto1.ipynb
```

O notebook já está executado e contém as figuras. Para conferir do zero, use
**Kernel > Restart Kernel and Run All Cells**. Ele contém todo o código de análise;
o script oferece a mesma análise pelo terminal. A instalação fica na `.venv` e
não modifica o Python do sistema. As versões diretas estão fixadas em `requirements.txt`.

No Colab, instale `networkx`, `pandas` e `matplotlib` e disponibilize `facebook/`
no diretório de execução. As células de análise não precisam importar o script.

## O que o programa faz

1. Reconstrói a rede com as dez redes-ego: lê `.edges` e acrescenta as amizades
   de cada ego com os usuários da primeira coluna de `.feat`.
2. Sorteia 404 nós sem reposição, usando a semente 1306308606, e constrói o
   subgrafo induzido. Mantém todos os nós, inclusive isolados.
3. Calcula centralidades de grau, intermediação, proximidade e autovetor.
4. Executa Louvain com resolução 1 e semente 1306308606.
5. Salva tabelas, mapas com rótulos e valores dos cinco líderes, rankings dos
   dez maiores valores, distribuições e um mapa colorido das comunidades.
6. Gera o mini-relatório de cinco páginas a partir dos resultados salvos.

As métricas usam os 404 nós. Proximidade usa a correção de Wasserman-Faust para
o grafo desconectado. Autovetor usa até 1.000 iterações, tolerância `1e-10` e
normalização euclidiana; os isolados recebem zero. O valor global pode se
concentrar em uma componente, como discutido no notebook e no relatório.

Cada comunidade não unitária tem uma cor no mapa. Os isolados ficam cinza para
simplificar a legenda, mas cada um tem uma comunidade própria no CSV.
As posições do desenho não indicam localização geográfica.

## Arquivos de saída

- `resultados/nos.csv` e `arestas.csv`: amostra efetivamente usada.
- `resultados/metricas.csv`: grau, quatro centralidades, componente e comunidade de cada nó.
- `resultados/comunidades.csv`: tamanho e arestas internas de cada comunidade.
- `resultados/resumo.json`: contagens, densidade, modularidade, semente e versões.
- `resultados/grafo.graphml`: grafo com atributos para abrir no Gephi (opcional).
- `resultados/figuras/`: quatro mapas de centralidade, comunidades, rankings e distribuições.
- `output/pdf/relatorio.pdf`: mini-relatório.

## Relatório em LaTeX

O relatório usa apresentação acadêmica baseada nas orientações ABNT: papel A4,
margens superior/esquerda de 3 cm e inferior/direita de 2 cm, fonte serifada
da família Times em 12 pt, espaçamento de 1,5 no corpo, texto justificado,
recuo de 1,25 cm, paginação superior direita, citações autor-data e referências.
As figuras e tabelas têm título acima e fonte abaixo, com espaçamento simples.

A estrutura foi adaptada ao mini-relatório de cinco páginas da disciplina:
a identificação está na primeira página, sem capa, folha de rosto ou sumário
separados de uma monografia. O [modelo de artigo da Biblioteca Central da UnB](https://bce.unb.br/wp-content/uploads/2023/11/Template-Artigo-TCC-1.pdf)
orienta a identificação e os elementos das figuras e tabelas. A
[orientação atualizada das bibliotecas da Ufes](https://sib.ufes.br/normalizacao)
identifica as normas NBR 14724:2024, NBR 10520:2023 e NBR 6023:2025.

- `relatorio_base.tex`: modelo editável com o texto e a formatação.
- `relatorio.tex`: documento completo gerado, com dados e gráficos vetoriais TikZ incorporados.
- `gerar_relatorio.py`: preenche o modelo com os CSV e compila usando Tectonic.
- `output/pdf/relatorio.pdf`: versão final para leitura e entrega.

O Tectonic foi instalado localmente em `.tools/tectonic`; o executável e seu
cache não são versionados. Em outro computador, instale o compilador pelo
[projeto oficial](https://github.com/tectonic-typesetting/tectonic/releases)
ou use o Overleaf. Não é preciso instalar LaTeX para executar a análise do grafo.

```bash
.venv/bin/python gerar_relatorio.py              # gera o .tex e o PDF com Tectonic
.venv/bin/python gerar_relatorio.py --somente-tex # gera apenas o documento LaTeX
```

O `.tex` gerado é independente e pode ser enviado sozinho ao Overleaf ou
compilado com XeLaTeX: os desenhos vetoriais estão no próprio arquivo, sem
dependência de imagens ou bibliografia externas. Para editar o texto de forma
permanente, altere `relatorio_base.tex` e gere novamente o relatório.
Os mapas completos continuam no notebook e nos PNG individuais.

Com a semente 1306308606: 404 nós, 885 arestas, 74 isolados, 109 componentes
conexas (a maior com 142 nós), 115 comunidades Louvain e modularidade aproximada
de 0,814953. O nó 1941 lidera o grau, o nó 1465 lidera intermediação e
proximidade e o nó 2464 lidera o autovetor, todos na maior componente.

O texto de `relatorio_base.tex` descreve esses líderes. `gerar_relatorio.py`
interrompe a geração se uma nova amostra deixar o texto incorreto.

## Validação

Depois de executar o script e o notebook:

```bash
.venv/bin/python validar_notebook.py
.venv/bin/python -m unittest discover -s tests -v
```

As verificações cobrem centralidades conhecidas num caminho com um isolado,
o subgrafo induzido salvo, a cobertura da partição, o resíduo do autovetor,
a exportação GraphML e a execução do notebook com as sete figuras.

## Antes de entregar

- Conferir com o grupo se a lista sorteada não é igual à de outro grupo.
  A semente torna o sorteio reproduzível, mas não garante exclusividade.
- Se mudar a semente, atualizar o script e o notebook, executar tudo e revisar
  os textos de análise. Não aproveitar um relatório de outra amostra.
- Ler o relatório e praticar a explicação dos resultados antes da demonstração.
- Consultar o prazo no Aprender3. Os entregáveis pedidos são o notebook comentado,
  os nomes e matrículas e o mini-relatório de até cinco páginas.

## Fontes

- [SNAP: ego-Facebook](https://snap.stanford.edu/data/egonets-Facebook.html).
- [NetworkX: centralidades](https://networkx.org/documentation/stable/reference/algorithms/centrality.html).
- [NetworkX: Louvain](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html).
