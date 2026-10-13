"""Executa o notebook inteiro usando o mesmo Python deste comando."""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager


def validar_notebook():
    raiz = Path(__file__).resolve().parent
    caminho = raiz / "projeto1.ipynb"
    notebook = nbformat.read(caminho, as_version=4)
    # Kernel temporário: não instala configurações na conta do usuário.
    with TemporaryDirectory(prefix="tag-kernel-") as temporario:
        pasta = Path(temporario) / "tag"
        pasta.mkdir()
        especificacao = {
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "Python 3 (TAG)", "language": "python",
        }
        (pasta / "kernel.json").write_text(json.dumps(especificacao))
        gerenciador = KernelManager(kernel_name="tag", kernel_spec_manager=KernelSpecManager(
            kernel_dirs=[temporario], ensure_native_kernel=False))
        cliente = NotebookClient(notebook, km=gerenciador, timeout=120, startup_timeout=30,
                                 resources={"metadata": {"path": str(raiz)}})
        cliente.execute()
    nbformat.write(notebook, caminho)
    print("Notebook executado sem erros e salvo com as saídas.")


if __name__ == "__main__":
    validar_notebook()
