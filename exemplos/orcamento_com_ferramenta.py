"""
Agente de orçamento com ferramenta (tool use) — Engenharia Civil
================================================================

Demonstra o nível mais avançado: dar ao modelo uma FERRAMENTA (função) que ele
chama quando precisa de um dado REAL — aqui, o preço de um insumo na sua base.
Assim o orçamento usa o preço do SEU sistema, e não um valor "alucinado".

O loop é o padrão de agente: o modelo decide chamar a ferramenta, seu código a
executa e devolve o resultado, e ele continua até concluir.

Pré-requisitos:
    pip install anthropic
    export ANTHROPIC_API_KEY="sua-chave"

Uso:
    python orcamento_com_ferramenta.py
"""

from __future__ import annotations

import json

import anthropic

MODELO = "claude-opus-4-8"

# Base de preços fictícia (no mundo real: SINAPI, banco do escritório, ERP, planilha…).
BASE_PRECOS = {
    "87490": {"descricao": "Alvenaria de vedação, bloco cerâmico 14cm", "unid": "m2", "preco": 78.50},
    "92775": {"descricao": "Concreto fck=25 MPa, lançado e adensado", "unid": "m3", "preco": 612.30},
    "90586": {"descricao": "Fôrma de madeira para estrutura", "unid": "m2", "preco": 96.10},
}

TOOLS = [
    {
        "name": "consulta_preco",
        "description": (
            "Retorna descrição, unidade e preço unitário de um insumo a partir do seu "
            "código na base de preços oficial. Use SEMPRE esta ferramenta para obter "
            "preços — nunca estime."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "codigo": {"type": "string", "description": "Código do insumo na base"}
            },
            "required": ["codigo"],
            "additionalProperties": False,
        },
    }
]


def consulta_preco(codigo: str) -> str:
    """Executa a ferramenta: consulta a base e devolve o resultado como JSON (string)."""
    item = BASE_PRECOS.get(codigo)
    if not item:
        return json.dumps({"erro": f"código {codigo} não encontrado na base"})
    return json.dumps({"codigo": codigo, **item}, ensure_ascii=False)


def executar(pergunta: str) -> str:
    client = anthropic.Anthropic()
    messages: list[dict] = [{"role": "user", "content": pergunta}]

    while True:
        resp = client.messages.create(
            model=MODELO,
            max_tokens=4000,
            system=(
                "Você é orçamentista de obras. Use a ferramenta consulta_preco para "
                "todo preço. Monte a planilha com itens, quantidades, custo unitário "
                "e total, e aponte itens sem preço na base."
            ),
            tools=TOOLS,
            messages=messages,
        )

        if resp.stop_reason != "tool_use":
            # Sem mais chamadas de ferramenta: resposta final.
            return next(b.text for b in resp.content if b.type == "text")

        # O modelo pediu uma ou mais ferramentas. Execute e devolva os resultados.
        messages.append({"role": "assistant", "content": resp.content})
        resultados = []
        for bloco in resp.content:
            if bloco.type == "tool_use":
                if bloco.name == "consulta_preco":
                    saida = consulta_preco(bloco.input["codigo"])
                else:
                    saida = json.dumps({"erro": "ferramenta desconhecida"})
                resultados.append(
                    {"type": "tool_result", "tool_use_id": bloco.id, "content": saida}
                )
        messages.append({"role": "user", "content": resultados})


if __name__ == "__main__":
    pergunta = (
        "Monte o orçamento para: 120 m2 de alvenaria (cód. 87490), "
        "35 m3 de concreto fck=25 (cód. 92775) e 210 m2 de fôrma (cód. 90586). "
        "Apresente em tabela e some o total."
    )
    print(executar(pergunta))
    print(
        "\n[Lembrete] Saída gerada por IA com preços da base oficial. "
        "Revise quantidades e composições antes de qualquer uso oficial."
    )
