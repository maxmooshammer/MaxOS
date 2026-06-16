# Biblioteca de prompts — Engenharia Civil

Receitas prontas para colar no **Claude.ai** (chat). Anexe os arquivos indicados (PDF, planilha,
template, texto da norma) antes de enviar. Adapte os trechos entre `[colchetes]`.

> **Regra que vale para todas:** termine sempre pedindo para a IA **sinalizar incertezas e pendências**
> em vez de inventar. É isso que torna a saída confiável e conferível.

---

## 1. Memorial descritivo

```
Você é um engenheiro civil projetista, rigoroso com a ABNT.

CONTEXTO: [tipo de obra, nº de pavimentos, sistema construtivo, materiais].
Use o TEMPLATE do escritório (anexo) e os DADOS DO PROJETO (anexo).
Norma aplicável: [ex.: NBR 6122] (texto anexo).

TAREFA: redija o memorial descritivo de [disciplina/elemento], item a item.

FORMATO: seções numeradas; linguagem técnica ABNT; tabelas onde fizer sentido.

RESTRIÇÕES: cite a norma onde aplicável. NÃO invente valores — onde faltar dado,
escreva "[VERIFICAR: ...]" e consolide todas as pendências numa lista ao final.
```

## 2. Memorial de cálculo (organização e redação)

```
Você é um engenheiro estrutural. NÃO recalcule o dimensionamento — organize e redija.

A partir dos RESULTADOS DO SOFTWARE (anexo) e das PREMISSAS (anexo):
1. Redija o memorial de cálculo: premissas, hipóteses, cargas, critérios normativos.
2. Transcreva os resultados em texto técnico com as tabelas necessárias.
3. Confira a coerência de unidades e de ordens de grandeza.
4. Liste qualquer inconsistência entre dados de entrada e resultados.

Norma: [ex.: NBR 6118] (texto anexo). Sinalize com "?" tudo que não puder confirmar.
```

## 3. Especificações técnicas / caderno de encargos

```
Você é um especificador técnico. A partir do ESCOPO DO PROJETO (anexo) e do
PADRÃO DO ESCRITÓRIO (anexo), gere as especificações técnicas dos serviços de
[disciplina].

FORMATO: para cada serviço — descrição, materiais, execução, normas, critérios de
medição e aceitação.

RESTRIÇÕES: padronize a terminologia; não copie premissas de obras diferentes;
marque "[CONFIRMAR]" onde o escopo não especifica.
```

## 4. Conferência normativa (checklist auditável)

```
Você é revisor de projetos. Confira o PROJETO (anexo) contra a [ex.: NBR 9050]
(texto anexo).

Para cada requisito aplicável, devolva uma TABELA:
| Item da norma | Requisito | Situação no projeto | Status | Observação |

Status ∈ {Atende, Não atende, Verificar}. Cite o item exato da norma.
Se não der para avaliar pelo material fornecido, use "Verificar" — não presuma.
Ao final, liste só os "Não atende" e "Verificar" em ordem de prioridade.
```

## 5. Compatibilização entre disciplinas

```
Você é coordenador de projetos. Recebeu [arquitetura], [estrutura] e [instalações]
(anexos).

Aponte CONFLITOS e DIVERGÊNCIAS entre as disciplinas: interferências físicas,
incoerências de cotas/níveis, elementos faltantes, premissas contraditórias.

FORMATO: tabela | Disciplinas envolvidas | Descrição do conflito | Onde (local/prancha)
| Severidade (Alta/Média/Baixa) | Sugestão.

Não invente o que não estiver nos documentos; marque leituras incertas com "?".
```

## 6. Verificação independente de cálculo

```
Refaça, de forma independente, a verificação de [ex.: esforço cortante] desta
[peça] segundo a [NBR 6118] (texto anexo).

Dados na planilha anexa. Passos:
1. Confira as unidades de cada termo.
2. Recalcule passo a passo, MOSTRANDO a conta.
3. Compare com o valor da planilha.
4. Liste divergências e premissas ausentes.

Não substitua o cálculo certificado — esta é uma segunda checagem.
```

## 7. Extração de dados de sondagem (SPT)

```
Do RELATÓRIO DE SONDAGEM anexo (PDF), extraia para conferência do projetista:
1. Tabela: profundidade (m) × N_SPT × descrição da camada.
2. Nível d'água.
3. Resumo das camadas em até 3 linhas.
4. Pontos de atenção para fundação.

Marque com "?" qualquer leitura incerta do PDF. Devolva a tabela também em CSV.
```

## 8. Quantitativos / orçamento (estrutura)

```
Você é orçamentista. A partir do LEVANTAMENTO (anexo) e da BASE DE PREÇOS (anexo,
ex.: SINAPI), monte a planilha orçamentária.

FORMATO: | Item | Descrição | Unid. | Quant. | Custo unit. | Custo total |, com
subtotais por etapa e total geral.

RESTRIÇÕES: use SOMENTE preços da base anexa (não estime). Aponte itens do
levantamento sem correspondência na base. Confira somas e unidades.
```

## 9. Resumo de laudo / relatório técnico

```
Resuma o [laudo/relatório] anexo para a equipe de projeto:
- Objeto e metodologia (2 linhas)
- Resultados principais (tópicos)
- Não-conformidades e recomendações
- Impacto no projeto / próximos passos

Cite a página de cada ponto crítico. Não extrapole além do documento.
```

## 10. Revisão de texto técnico (consistência interna)

```
Revise o [memorial/relatório] anexo quanto à CONSISTÊNCIA INTERNA:
referências cruzadas, cotas e cargas repetidas em pontos diferentes, unidades,
numeração de itens e tabelas, termos divergentes para a mesma coisa.

Liste só os problemas encontrados, com localização e correção sugerida.
```

---

### Dicas que valem ouro
- **Peça o formato de saída** (tabela, CSV, seções numeradas) — facilita conferir e reaproveitar.
- **Anexe a norma** como contexto; não confie na "memória" do modelo sobre cláusulas.
- **Use "mostre a conta"** em verificações numéricas: raciocínio explícito é auditável.
- **Salve as receitas** que funcionarem no seu **Project** do escritório.
