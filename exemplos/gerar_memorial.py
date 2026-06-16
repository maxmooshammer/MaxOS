"""
Gerador de memorial descritivo — Engenharia Civil
==================================================

Monta o rascunho de um memorial descritivo a partir de:
  - dados do projeto (texto/markdown);
  - template do escritório (texto/markdown);
  - texto da norma aplicável (opcional).

A saída é uma MINUTA estruturada, com uma seção final de pendências
"[VERIFICAR: ...]" — para o engenheiro conferir, ajustar e assinar.

Pré-requisitos:
    pip install anthropic
    export ANTHROPIC_API_KEY="sua-chave"

Uso:
    python gerar_memorial.py dados_projeto.md template.md [norma.txt] > memorial.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import anthropic

MODELO = "claude-opus-4-8"

SYSTEM = (
    "Você é um engenheiro civil projetista, rigoroso com a ABNT. Você redige "
    "memoriais técnicos claros, em seções numeradas, na linguagem do escritório. "
    "Você NUNCA inventa valores: onde faltar dado, escreve '[VERIFICAR: ...]' e "
    "consolida todas as pendências numa lista ao final."
)


def gerar_memorial(dados: str, template: str, norma: str | None) -> str:
    partes = [
        "Redija o MEMORIAL DESCRITIVO seguindo o template do escritório e usando "
        "exclusivamente os dados do projeto fornecidos.\n",
        "=== TEMPLATE DO ESCRITÓRIO ===\n" + template,
        "\n=== DADOS DO PROJETO ===\n" + dados,
    ]
    if norma:
        partes.append("\n=== NORMA APLICÁVEL (cite os itens onde couber) ===\n" + norma)
    partes.append(
        "\nFORMATO: seções numeradas; tabelas onde fizer sentido; linguagem técnica "
        "ABNT. Ao final, liste as pendências '[VERIFICAR: ...]' em ordem de prioridade."
    )
    prompt = "\n".join(partes)

    client = anthropic.Anthropic()

    # Streaming evita timeouts em respostas longas; .get_final_message() devolve o texto completo.
    with client.messages.stream(
        model=MODELO,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        msg = stream.get_final_message()

    return "".join(b.text for b in msg.content if b.type == "text")


def main() -> None:
    if len(sys.argv) not in (3, 4):
        print("Uso: python gerar_memorial.py dados.md template.md [norma.txt]", file=sys.stderr)
        raise SystemExit(1)

    dados = Path(sys.argv[1]).read_text(encoding="utf-8")
    template = Path(sys.argv[2]).read_text(encoding="utf-8")
    norma = Path(sys.argv[3]).read_text(encoding="utf-8") if len(sys.argv) == 4 else None

    print(gerar_memorial(dados, template, norma))


if __name__ == "__main__":
    main()
