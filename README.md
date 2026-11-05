# IA aplicada à Engenharia Civil — Apresentação completa (30 min)

Apresentação executiva e prática sobre **inteligência artificial aplicada à engenharia civil para
projetos** — desde *como usar o Claude* até *como conferir projetos, elaborar memoriais e desenvolver
ferramentas próprias*. Pensada para caber em **no máximo 30 minutos**.

## Conteúdo do repositório

| Arquivo | O que é |
|---------|---------|
| **`index.html`** | O **deck** da apresentação (26 slides). Abre em qualquer navegador, **funciona offline**, sem instalar nada. |
| **`ROTEIRO.md`** | Roteiro do apresentador: cronograma por minuto, falas de apoio, versões de 15 e 30 min, controles do deck. |
| **`PROMPTS.md`** | Biblioteca de **prompts/receitas** prontas para colar no chat (memoriais, conferência, sondagem, orçamento…). |
| **`exemplos/`** | **Ferramentas em Python** usando a API do Claude (código comentado, pronto para adaptar). |
| **`ferramentas/selo_prancha/`** | Gerador de **prancha + selo** no padrão Mooshammer (PDF + DXF com bloco de atributos). |

### Ferramentas de exemplo (`exemplos/`)
- `verificador_normativo.py` — lê PDFs de uma pasta, confere contra uma norma e gera um checklist em `.xlsx`.
- `gerar_memorial.py` — monta o rascunho de um memorial descritivo a partir de dados + template do escritório.
- `extrair_sondagem.py` — extrai dados de relatório de sondagem (SPT) em CSV estruturado.
- `orcamento_com_ferramenta.py` — agente com *tool use* conectado a uma base de preços (preço real, sem "alucinação").

## Como apresentar

1. Abra **`index.html`** no navegador e pressione `F` para tela cheia.
2. Navegue com `→` / `←` (ou clique nas metades direita/esquerda da tela).
3. Pressione `N` para ver as **notas do apresentador** de cada slide.
4. O **cronômetro** (canto inferior direito) ajuda a manter os 30 min: fica **amarelo aos 25 min** e **vermelho aos 30**. `T` zera.

> Leia o `ROTEIRO.md` antes — ele traz o cronograma minuto a minuto e as falas-chave.

## Como rodar as ferramentas de exemplo

```bash
pip install anthropic openpyxl
export ANTHROPIC_API_KEY="sua-chave"      # nunca deixe a chave no código

python exemplos/gerar_memorial.py dados.md template.md norma.txt > memorial.md
python exemplos/verificador_normativo.py ./projetos ./nbr9050.txt resultado.xlsx
python exemplos/extrair_sondagem.py sondagem.pdf > sondagem.csv
python exemplos/orcamento_com_ferramenta.py
```

Modelo usado nos exemplos: **`claude-opus-4-8`** (alta capacidade de raciocínio e janela de contexto de
1M de tokens). É possível trocar por um modelo mais econômico conforme a tarefa.

## A regra que organiza tudo

> **A IA produz o rascunho; o engenheiro confere e assina.**
> Toda saída é uma minuta a ser revisada — nunca uma entrega final automática. A responsabilidade
> técnica (ART/RRT) é, e continua sendo, do profissional.
