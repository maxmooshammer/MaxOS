"""
Verificador normativo em lote — Engenharia Civil
=================================================

Lê todos os PDFs de uma pasta, confere cada um contra um critério/norma e
devolve um checklist ESTRUTURADO (JSON), consolidado em uma planilha .xlsx.

É o esqueleto de uma ferramenta interna de conferência. A saída é uma MINUTA
para o engenheiro revisar e assinar — nunca uma entrega final automática.

Pré-requisitos:
    pip install anthropic openpyxl
    export ANTHROPIC_API_KEY="sua-chave"   # nunca deixe a chave no código

Uso:
    python verificador_normativo.py ./projetos ./norma_nbr9050.txt resultado.xlsx
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import anthropic
from openpyxl import Workbook

MODELO = "claude-opus-4-8"  # alta capacidade de raciocínio; janela de 1M tokens

# Saída estruturada: garante que a resposta venha como JSON válido com este formato.
SCHEMA_CHECKLIST = {
    "type": "object",
    "properties": {
        "itens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_norma": {"type": "string"},
                    "requisito": {"type": "string"},
                    "situacao_no_projeto": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["Atende", "Não atende", "Verificar"],
                    },
                    "observacao": {"type": "string"},
                },
                "required": [
                    "item_norma",
                    "requisito",
                    "situacao_no_projeto",
                    "status",
                    "observacao",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["itens"],
    "additionalProperties": False,
}

SYSTEM = (
    "Você é um engenheiro revisor de projetos, rigoroso com a ABNT. "
    "Confere documentos contra a norma fornecida e nunca inventa: quando não for "
    "possível avaliar pelo material, marca o status como 'Verificar'."
)


def verificar_pdf(client: anthropic.Anthropic, pdf_path: Path, texto_norma: str) -> list[dict]:
    """Confere um PDF contra o texto da norma e devolve a lista de itens do checklist."""
    pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("utf-8")

    resp = client.messages.create(
        model=MODELO,
        max_tokens=8000,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Confira o projeto acima contra a norma a seguir. "
                            "Para cada requisito aplicável gere um item do checklist "
                            "(item da norma, requisito, situação no projeto, status, "
                            "observação). Não invente: use 'Verificar' quando não der "
                            "para avaliar pelo material.\n\n=== NORMA ===\n" + texto_norma
                        ),
                    },
                ],
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA_CHECKLIST}},
    )

    # output_config.format garante que o primeiro bloco de texto é JSON válido.
    texto = next(b.text for b in resp.content if b.type == "text")
    return json.loads(texto)["itens"]


def main() -> None:
    if len(sys.argv) != 4:
        print("Uso: python verificador_normativo.py <pasta_pdfs> <norma.txt> <saida.xlsx>")
        raise SystemExit(1)

    pasta_pdfs, norma_txt, saida_xlsx = (Path(a) for a in sys.argv[1:4])
    texto_norma = norma_txt.read_text(encoding="utf-8")

    client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente

    wb = Workbook()
    ws = wb.active
    ws.title = "Checklist"
    ws.append(["Arquivo", "Item da norma", "Requisito", "Situação", "Status", "Observação"])

    pdfs = sorted(pasta_pdfs.glob("*.pdf"))
    if not pdfs:
        print(f"Nenhum PDF encontrado em {pasta_pdfs}")
        raise SystemExit(1)

    for pdf in pdfs:
        print(f"Conferindo {pdf.name} …")
        try:
            itens = verificar_pdf(client, pdf, texto_norma)
        except Exception as e:  # noqa: BLE001 — registra e segue para o próximo arquivo
            print(f"  ! erro em {pdf.name}: {e}")
            ws.append([pdf.name, "", "", "", "ERRO", str(e)])
            continue

        for it in itens:
            ws.append(
                [
                    pdf.name,
                    it["item_norma"],
                    it["requisito"],
                    it["situacao_no_projeto"],
                    it["status"],
                    it["observacao"],
                ]
            )
        nao_ok = sum(1 for it in itens if it["status"] != "Atende")
        print(f"  {len(itens)} itens · {nao_ok} para revisar")

    wb.save(saida_xlsx)
    print(f"\nPlanilha salva em {saida_xlsx}. Revise antes de qualquer uso oficial.")


if __name__ == "__main__":
    main()
