# Selo de prancha — padrão Mooshammer Engenharia

Gera a **prancha + selo** no mesmo padrão visual da Proposta Comercial (laranja `#E8410A`,
logo hexagonal "M", Space Grotesk / Inter / JetBrains Mono), a partir de **uma única geometria**:

| Saída | O que é |
|-------|---------|
| `<arquivo>.pdf` | 1 página por prancha, vetorial, no tamanho real da folha (mm). |
| `<arquivo>.dxf` | Folhas + moldura + selo como **bloco `SELO_MOOSHAMMER` com atributos** já preenchidos (R2010, mm, 1:1). |
| `<arquivo>_SELO_bloco.dxf` | Só o selo, para `INSERT` em qualquer desenho (ponto base = canto inferior direito do selo). |

## Geometria
- Folha com 594 mm de largura (rolo A1) e comprimento livre por prancha (`"folha": [594, 581]`).
- Margens NBR: 25 mm à esquerda, 10 mm nas demais. Selo 170 × 196 mm no canto inferior direito.
- Faixas do selo (de cima para baixo): Aprovações · Cabeçalho (logo em destaque + tipo de projeto) · Obra/endereço ·
  Data/Escala/Desenhista/Prancha · Proprietário/CPF-CNPJ/Conteúdo/Resp. técnico · Assinaturas · Rodapé.

## Uso
```bash
pip install ezdxf fonttools uharfbuzz pypdf      # + Node com Playwright/Chromium para o PDF
cp exemplo_obra.json minha_obra.local.json        # *.local.json não vai para o git (dados de cliente)
python gerar_selo.py minha_obra.local.json --saida ./saida
python gerar_selo.py minha_obra.local.json --sem-pdf   # só DXF (não precisa de Node)
```
As fontes (licença OFL) são baixadas do Google Fonts na primeira execução para `./fonts`.

## No CAD
- Textos editáveis em **Arial / Arial Bold** (estilos `MOOS_TEXTO`, `MOOS_NEGRITO`, `MOOS_ROTULO`);
  logo e nome da marca vão em **curvas (hatch)**, então ficam idênticos em qualquer máquina.
- Campos editáveis com duplo clique (`EATTEDIT`): `OBRA`, `ENDERECO`, `PROJETO`, `DATA`, `ESCALA`,
  `DESENHISTA`, `PRANCHA`, `PROPRIETARIO`, `CPF_CNPJ`, `CONTEUDO`, `RESP_TECNICO`, `ASS_*`.
- Layers `MOOS-*` com cor real e espessura definidas (moldura 0,70 · contorno do selo 0,35 · divisões 0,25/0,18).

> **Atenção (repositório público):** não versione arquivos com nome/CPF de clientes — use `*.local.json`.
