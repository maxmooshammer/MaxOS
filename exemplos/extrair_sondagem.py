"""
Extrator de relatório de sondagem (SPT) — Engenharia Civil
==========================================================

Lê um relatório de sondagem em PDF e devolve dados ESTRUTURADOS:
  - tabela profundidade × N_SPT × descrição da camada;
  - nível d'água;
  - resumo das camadas;
  - pontos de atenção para fundação.

Exporta a tabela como CSV para conferência e uso direto em planilha.

Pré-requisitos:
    pip install anthropic
    export ANTHROPIC_API_KEY="sua-chave"

Uso:
    python extrair_sondagem.py sondagem.pdf > sondagem.csv
"""

from __future__ import annotations

import base64
import csv
import io
import json
import sys
from pathlib import Path

import anthropic

MODELO = "claude-opus-4-8"

SCHEMA = {
    "type": "object",
    "properties": {
        "nivel_dagua_m": {"type": "string"},
        "resumo_camadas": {"type": "string"},
        "pontos_atencao": {"type": "array", "items": {"type": "string"}},
        "camadas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "profundidade_m": {"type": "string"},
                    "nspt": {"type": "string"},
                    "descricao": {"type": "string"},
                    "leitura_incerta": {"type": "boolean"},
                },
                "required": ["profundidade_m", "nspt", "descricao", "leitura_incerta"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["nivel_dagua_m", "resumo_camadas", "pontos_atencao", "camadas"],
    "additionalProperties": False,
}

SYSTEM = (
    "Você é um engeotécnico. Extrai dados de relatórios de sondagem com precisão e "
    "marca como 'leitura_incerta' qualquer valor que não consiga ler com confiança "
    "no PDF. Você nunca inventa números."
)


def extrair(pdf_path: Path) -> dict:
    pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("utf-8")
    client = anthropic.Anthropic()

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
                            "Extraia: nível d'água, resumo das camadas (até 3 linhas), "
                            "pontos de atenção para fundação e a tabela de "
                            "profundidade × N_SPT × descrição. Marque leitura_incerta=true "
                            "onde o PDF estiver ambíguo."
                        ),
                    },
                ],
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    texto = next(b.text for b in resp.content if b.type == "text")
    return json.loads(texto)


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python extrair_sondagem.py sondagem.pdf > saida.csv", file=sys.stderr)
        raise SystemExit(1)

    dados = extrair(Path(sys.argv[1]))

    # Cabeçalho informativo no stderr (não polui o CSV no stdout).
    print(f"# Nível d'água: {dados['nivel_dagua_m']}", file=sys.stderr)
    print(f"# Resumo: {dados['resumo_camadas']}", file=sys.stderr)
    for p in dados["pontos_atencao"]:
        print(f"# Atenção: {p}", file=sys.stderr)

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["profundidade_m", "nspt", "descricao", "leitura_incerta"])
    for c in dados["camadas"]:
        w.writerow([c["profundidade_m"], c["nspt"], c["descricao"], c["leitura_incerta"]])
    sys.stdout.write(out.getvalue())


if __name__ == "__main__":
    main()
