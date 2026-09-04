from pathlib import Path
from playwright.sync_api import sync_playwright
import pandas as pd
import os

URL_LISTA = "https://uolcorp.service-now.com/now/sow/list/params/list-id/b92df1a5530230104a06ddeeff7b12a4/__state__/b64~eyJlNGQ0NmFiYzQxMjEwMzg5MGRkZGUyMzUyMjhhOCI6eyJsaXN0X2NvbnRyb2xsZXIiOnsiXyI6eyJxdWVyeSI6ImFjdGl2ZT10cnVlXmFzc2lnbmVkX3RvRFlOQU1JQzkwZDE5MjFlNWY1MTAxMDBhOWFkMjU3MmYyYjQ3N2ZlXmNsb3NlX25vdGVzIT1BZ3VhcmRhbmRvIG91dHJhcyB0YXJlZmFzXk9SY2xvc2Vfbm90ZXNJU0VNUFRZXkVRIiwiY3VycmVudFBhZ2UiOjB9fX19"

PASTA_RAIZ = r"C:\chamados"

WORK_NOTES_PADRAO = "Equipamento formatado e homologado."
COMENTARIOS_PADRAO = "Evidências anexadas."


def gerar_tarefas_csv():

    print("\nLendo sc_task.csv...")

    df = pd.read_csv(
        "sc_task.csv",
        encoding="latin1"
    )

    tarefas = pd.DataFrame({
        "SCTASK": df["number"],
        "USERNAME": df["request_item.requested_for"],
        "RITM": df["request_item"],
        "WORK_NOTES": WORK_NOTES_PADRAO,
        "COMENTARIOS": COMENTARIOS_PADRAO
    })

    tarefas.to_csv(
        "tarefas.csv",
        index=False
    )

    print("tarefas.csv gerado.")

    return tarefas


def criar_pastas(tarefas):

    print("\nCriando pastas...\n")

    for usuario in tarefas["USERNAME"]:

        pasta = os.path.join(
            PASTA_RAIZ,
            str(usuario).strip()
        )

        os.makedirs(
            pasta,
            exist_ok=True
        )

        print(f"[OK] {pasta}")


def buscar_arquivos(pasta):

    arquivos = []

    for extensao in [
        "*.jpg",
        "*.jpeg",
        "*.png",
        "*.gif",
        "*.bmp",
        "*.pdf"
    ]:

        arquivos.extend(
            list(
                Path(pasta).glob(extensao)
            )
        )

    return [
        str(x)
        for x in arquivos
    ]


def preencher_work_notes(page, texto):

    page.evaluate(
        """
        (texto) => {

            function procurar(root) {

                const campo =
                    root.querySelector(
                        'textarea[name="work_notes"]'
                    );

                if (campo) {

                    campo.focus();

                    campo.value = texto;

                    campo.dispatchEvent(
                        new InputEvent(
                            "input",
                            {
                                bubbles: true,
                                composed: true
                            }
                        )
                    );

                    campo.dispatchEvent(
                        new Event(
                            "change",
                            {
                                bubbles: true
                            }
                        )
                    );

                    campo.blur();

                    return true;
                }

                for (const el of root.querySelectorAll('*')) {

                    if (el.shadowRoot) {

                        const ok =
                            procurar(el.shadowRoot);

                        if (ok)
                            return true;
                    }
                }

                return false;
            }

            return procurar(document);
        }
        """,
        texto
    )


def processar_task(page, linha):

    task = str(linha["SCTASK"])
    usuario = str(linha["USERNAME"])

    pasta_usuario = os.path.join(
        PASTA_RAIZ,
        usuario
    )

    arquivos = buscar_arquivos(
        pasta_usuario
    )

    print("\n================================")
    print(f"TASK: {task}")
    print(f"USUÁRIO: {usuario}")
    print("================================")

    if len(arquivos) < 2:

        print(
            f"Quantidade insuficiente de evidências: {len(arquivos)}"
        )

        return "EVIDENCIA_INSUFICIENTE"

    print(
        f"Arquivos encontrados: {len(arquivos)}"
    )

    page.goto(URL_LISTA)

    page.get_by_text(
        task,
        exact=False
    ).first.wait_for(
        timeout=60000
    )

    page.get_by_text(
        task,
        exact=False
    ).first.click()

    page.wait_for_timeout(8000)

    preencher_work_notes(
        page,
        linha["WORK_NOTES"]
    )

    page.locator(
        'textarea[name="request_item.comments"]'
    ).fill(
        linha["COMENTARIOS"]
    )

    page.wait_for_timeout(2000)

    page.locator(
        "#attachments"
    ).click()

    page.wait_for_timeout(3000)

    with page.expect_file_chooser() as fc:

        page.get_by_role(
            "button",
            name="Selecionar arquivo"
        ).click()

    file_chooser = fc.value

    file_chooser.set_files(
        arquivos
    )

    page.wait_for_timeout(3000)

    page.get_by_text(
        "Carregar tudo",
        exact=False
    ).click()

    print(
        "\nUpload iniciado..."
    )

    page.wait_for_timeout(10000)

    print(
        "\nTentando clicar em Fechar tarefa..."
    )

    page.get_by_role(
        "button",
        name="Fechar tarefa"
    ).click()

    resposta = input(
        f"""

======================================

O robô clicou em FECHAR TAREFA.

TASK:
{task}

USUÁRIO:
{usuario}

ENTER = Funcionou

X = Interromper execução

Resposta: """
    ).strip().upper()

    if resposta == "X":

        raise SystemExit(
            "\nExecução interrompida pelo usuário."
        )

    return "FECHADO"


def main():

    tarefas = gerar_tarefas_csv()

    criar_pastas(
        tarefas
    )

    input(
        """

===================================

PASTAS CRIADAS

Coloque as evidências em:

C:\\chamados\\<usuario>

Depois pressione ENTER.

===================================

"""
    )

    resultado = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            executable_path=r"C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=False
        )

        context = browser.new_context(
            storage_state="session.json"
        )

        page = context.new_page()

        for _, linha in tarefas.iterrows():

            status = processar_task(
                page,
                linha
            )

            resultado.append({
                "SCTASK": linha["SCTASK"],
                "USERNAME": linha["USERNAME"],
                "STATUS": status
            })

        browser.close()

    pd.DataFrame(
        resultado
    ).to_csv(
        "resultado.csv",
        index=False
    )

    print(
        "\nresultado.csv gerado com sucesso."
    )

    print(
        "\nProcessamento finalizado."
    )


if __name__ == "__main__":
    main()