# Roteiro do apresentador — IA aplicada à Engenharia Civil

**Duração-alvo:** 30 minutos · **Slides:** 26 · **Ritmo:** ~1 a 1,5 min por slide.
Abra `index.html` no navegador (qualquer um). Funciona **offline**, sem instalar nada.

## Controles do deck
- `→` / `Espaço` / clique na metade direita → próximo slide
- `←` / clique na metade esquerda → slide anterior
- `N` → abre/fecha as **notas do apresentador**
- `F` → tela cheia
- `T` → zera o **cronômetro** (canto inferior direito; fica amarelo aos 25 min, vermelho aos 30)
- `Home` / `End` → primeiro / último slide

> As notas de cada slide também estão embutidas no próprio arquivo (`data-notes`). Pressione `N` durante a apresentação para vê-las.

---

## Cronograma sugerido (caixa de tempo)

| Tempo | Bloco | Slides | Mensagem central |
|------:|-------|:------:|------------------|
| 0–3 min | Abertura + contexto | 1–4 | O tempo migra de *produzir* para *verificar*. |
| 3–8 min | Fundamentos do Claude | 5–6 | O que é, o que não é, como acessar. |
| 8–12 min | Bom prompt + cuidados | 7–8 | Papel/Contexto/Tarefa/Formato/Restrições; 4 cuidados. |
| 12–18 min | Aplicações em projeto | 9–13 | Memoriais, especificações, documentos, quantitativos. |
| 18–22 min | Conferência | 14–16 | Revisor incansável: checklist normativo + verificação de cálculo. |
| 22–24 min | Mão na massa | 17–18 | Projects (base do escritório) + escada da automação. |
| 24–28 min | Ferramentas próprias | 19–22 | API, verificador em lote, agentes/MCP, arquitetura. |
| 28–30 min | Implementação + fecho | 23–26 | Roadmap 90 dias, governança, takeaways, CTA. |

---

## Falas de apoio (abertura forte)

**Slide 1 (capa):** *"Em 30 minutos quero que vocês saiam sabendo quatro coisas: o que é essa tecnologia, como usá-la em projeto já amanhã, como usá-la para conferir, e como construir ferramentas próprias do escritório. E uma regra que vai atravessar tudo: a IA faz o rascunho, o engenheiro confere e assina."*

**Slide 4 (antes × depois):** ancore num caso real do escritório (ex.: o último memorial descritivo que alguém penou para montar). A virada não é "a IA projeta", é "o tempo braçal vira tempo de engenharia".

**Slide 8 (cuidados):** é o slide que **protege o escritório**. Não pule. Diga em voz alta: *"Cada saída é minuta de um estagiário brilhante: velocidade ótima, revisão sempre."*

**Slide 25 (takeaways):** se o público lembrar de **uma frase**, é a do cartão 5.

---

## Se faltar tempo (versão 15 min)
Apresente apenas: **1 → 4 → 7 → 9 → 10 → 15 → 18 → 19 → 22 → 25 → 26**.

## Se sobrar tempo / público técnico
Aprofunde os slides **19–22** com o código em `exemplos/` aberto ao lado, e faça uma demo ao vivo de uma receita do `PROMPTS.md`.

---

## Materiais de apoio neste repositório
- `index.html` — o deck (este).
- `PROMPTS.md` — biblioteca de prompts/receitas prontas para colar no chat.
- `exemplos/verificador_normativo.py` — ferramenta de verificação em lote (PDF → JSON → planilha).
- `exemplos/gerar_memorial.py` — geração de memorial descritivo a partir de dados + template.
- `exemplos/extrair_sondagem.py` — extração estruturada de relatório de sondagem.
- `exemplos/orcamento_com_ferramenta.py` — agente com *tool* conectada à base de preços.
- `README.md` — visão geral e instruções.
