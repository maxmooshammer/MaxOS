#!/usr/bin/env python3
"""
Gerador de prancha + selo no padrão visual Mooshammer Engenharia.

Saídas (a partir de UMA única geometria, então PDF e DXF ficam idênticos em layout):
  - PDF vetorial (1 página por prancha, tamanho real da folha em mm)
  - DXF (R2010, unidades em mm, escala 1:1) com o selo como BLOCO com ATRIBUTOS
    editáveis (duplo clique no AutoCAD/ZWCAD/BricsCAD -> edita os campos).

Uso:
    pip install ezdxf fonttools uharfbuzz pypdf
    python gerar_selo.py exemplo_obra.json --saida ./saida

Dependências externas:
  - Node + Playwright (Chromium) para imprimir o PDF com as fontes do template.
  - Fontes Inter / Space Grotesk / JetBrains Mono (licença OFL). Baixadas
    automaticamente do Google Fonts na primeira execução (pasta ./fonts).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

AQUI = Path(__file__).resolve().parent

# --------------------------------------------------------------------------------------
# Identidade visual (mesma paleta da Proposta Comercial)
# --------------------------------------------------------------------------------------
CORES = {
    "accent": "#E8410A",       # laranja Mooshammer
    "accent_soft": "#FCE9E2",
    "ink900": "#0F0F0F",
    "ink700": "#1C1C1E",
    "ink600": "#3A3A3C",
    "ink500": "#636366",
    "ink400": "#8E8E93",
    "div": "#8E8E93",          # divisórias principais (mais escuras que no PDF A4, para plotagem)
    "div_fina": "#C7C7CC",     # divisórias secundárias
    "logo": "#333333",
}

# chave -> (família CSS, peso, arquivo TTF)
FONTES = {
    "display": ("Space Grotesk", 700, "SpaceGrotesk-700.ttf"),
    "display_sb": ("Space Grotesk", 600, "SpaceGrotesk-600.ttf"),
    "body": ("Inter", 400, "Inter-400.ttf"),
    "body_md": ("Inter", 500, "Inter-500.ttf"),
    "mono": ("JetBrains Mono", 500, "JetBrainsMono-500.ttf"),
}
# No DXF usamos Arial (presente em qualquer Windows/CAD) para os textos editáveis.
DXF_ESTILO = {
    "display": "MOOS_NEGRITO",
    "display_sb": "MOOS_NEGRITO",
    "body": "MOOS_TEXTO",
    "body_md": "MOOS_TEXTO",
    "mono": "MOOS_ROTULO",
}
GOOGLE_FONTS_CSS = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500"
    "&family=Space+Grotesk:wght@600;700&family=JetBrains+Mono:wght@500&display=swap"
)

# Layers do DXF: nome -> (cor RGB, ACI equivalente, espessura em 1/100 mm)
LAYERS = {
    "MOOS-FOLHA": ("ink400", 8, 13),
    "MOOS-MOLDURA": ("ink900", 7, 70),
    "MOOS-SELO-CONTORNO": ("ink900", 7, 35),
    "MOOS-SELO-DIVISAO": ("div", 8, 25),
    "MOOS-SELO-DIV-FINA": ("div_fina", 9, 18),
    "MOOS-SELO-ASSINATURA": ("ink700", 7, 25),
    "MOOS-SELO-PREENCH": ("accent_soft", 31, 13),
    "MOOS-SELO-DESTAQUE": ("accent", 30, 25),
    "MOOS-SELO-ROTULO": ("ink500", 8, 18),
    "MOOS-SELO-TEXTO": ("ink900", 7, 25),
    "MOOS-SELO-ATRIB": ("ink900", 7, 25),
    "MOOS-SELO-LOGO": ("logo", 250, 13),
}

# --------------------------------------------------------------------------------------
# Geometria do selo (mm). Origem no canto INFERIOR ESQUERDO do selo, eixo Y para cima.
# --------------------------------------------------------------------------------------
SELO_L = 170.0     # largura (mesma do selo antigo -> substitui sem mexer na prancha)
PAD = 5.0          # respiro interno
MARGEM_ESQ, MARGEM = 25.0, 10.0   # NBR 16752 / 10068

# faixas verticais (y0, y1)
F_RODAPE = (0.0, 8.0)
F_ASSIN = (8.0, 40.0)
F_DADOS = (40.0, 76.0)
F_META = (76.0, 94.0)
F_OBRA = (94.0, 122.0)
F_CAB = (122.0, 138.0)
F_APROV = (138.0, 184.0)
SELO_A = F_APROV[1]


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------- fontes ----------------------------------------------
def garantir_fontes(pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    faltando = [f for _, _, f in FONTES.values() if not (pasta / f).exists()]
    if not faltando:
        return
    print("Baixando fontes do Google Fonts...", file=sys.stderr)
    req = urllib.request.Request(GOOGLE_FONTS_CSS, headers={"User-Agent": "Mozilla/4.0"})
    css = urllib.request.urlopen(req, timeout=30).read().decode()
    for fam, peso, url in re.findall(
        r"font-family: '([^']+)';.*?font-weight: (\d+);.*?url\(([^)]+)\)", css, re.S
    ):
        destino = pasta / f"{fam.replace(' ', '')}-{peso}.ttf"
        with urllib.request.urlopen(url, timeout=30) as r, open(destino, "wb") as f:
            f.write(r.read())


_CAP_CACHE: dict[str, float] = {}


def cap_ratio(pasta: Path, chave: str) -> float:
    """Altura de maiúscula / corpo da fonte (para converter corpo CSS -> altura de texto CAD)."""
    if chave not in _CAP_CACHE:
        from fontTools.ttLib import TTFont

        tt = TTFont(pasta / FONTES[chave][2])
        _CAP_CACHE[chave] = tt["OS/2"].sCapHeight / tt["head"].unitsPerEm
    return _CAP_CACHE[chave]


# ---------------------------------- logo ------------------------------------------------
class Logo:
    """Hexágonos geométricos exatos + 'M' vetorizado do PNG original."""

    def __init__(self, arq: Path):
        self.d = json.loads(arq.read_text(encoding="utf-8"))
        cx = self.d["caixa"]
        self.x0, self.y0, self.w, self.h = cx["x0"], cx["y0"], cx["largura"], cx["altura"]

    def largura(self, altura: float) -> float:
        return altura * self.w / self.h

    def _tf(self, x: float, y: float, h: float):
        s = h / self.h
        return lambda px, py: (x + (px - self.x0) * s, y + h - (py - self.y0) * s)

    @staticmethod
    def _hex(c):
        return [
            (c["cx"] + c["r"] * math.sin(math.radians(a)), c["cy"] - c["r"] * math.cos(math.radians(a)))
            for a in range(0, 360, 60)
        ]

    def contornos(self, x: float, y: float, h: float, passos: int = 8):
        """Polígonos (lista de listas de pontos) em mm, eixo Y para cima."""
        tf = self._tf(x, y, h)
        polys = [[tf(*p) for p in self._hex(self.d["hex_externo"])],
                 [tf(*p) for p in self._hex(self.d["hex_interno"])]]
        m = self.d["M"]
        pts = [tuple(m["inicio"])]
        for seg in m["segmentos"]:
            if seg[0] == "L":
                pts += [tuple(seg[1]), tuple(seg[2])]
            else:
                p0 = pts[-1]
                p1, p2, p3 = seg[1], seg[2], seg[3]
                for i in range(1, passos + 1):
                    t = i / passos
                    a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
                    pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                                a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
        limpo = [pts[0]]
        for p in pts[1:]:
            if math.dist(p, limpo[-1]) > 1e-4:
                limpo.append(p)
        if math.dist(limpo[0], limpo[-1]) < 1e-4:
            limpo.pop()
        polys.append([tf(*p) for p in limpo])
        return polys

    def svg_path(self, x: float, y: float, h: float, H: float) -> str:
        """Path SVG (com curvas) em coordenadas da folha (Y para baixo, altura H)."""
        tf = self._tf(x, y, h)

        def P(px, py):
            X, Y = tf(px, py)
            return f"{X:.3f} {H - Y:.3f}"

        d = []
        for c in (self.d["hex_externo"], self.d["hex_interno"]):
            pts = self._hex(c)
            d.append("M " + " L ".join(P(*p) for p in pts) + " Z")
        m = self.d["M"]
        s = "M " + P(*m["inicio"])
        for seg in m["segmentos"]:
            if seg[0] == "L":
                s += f" L {P(*seg[1])} L {P(*seg[2])}"
            else:
                s += f" C {P(*seg[1])} {P(*seg[2])} {P(*seg[3])}"
        d.append(s + " Z")
        return " ".join(d)


# ---------------------------------- texto em curvas (DXF) -------------------------------
def texto_em_curvas(pasta: Path, chave: str, texto: str, x: float, y: float, corpo: float,
                    track_em: float = 0.0, passos: int = 6):
    """Converte texto em contornos (mm) usando o shaping do HarfBuzz (mesmo do Chromium)."""
    import uharfbuzz as hb
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont

    arq = str(pasta / FONTES[chave][2])
    face = hb.Face(hb.Blob.from_file_path(arq))
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(texto)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})
    tt = TTFont(arq)
    gs = tt.getGlyphSet()
    ordem = tt.getGlyphOrder()
    upem = tt["head"].unitsPerEm
    esc = corpo / upem

    class Pen(BasePen):
        def __init__(self, glyphset, ox):
            super().__init__(glyphset)
            self.ox, self.contornos, self.cur = ox, [], None

        def T(self, p):
            return (x + (self.ox + p[0]) * esc, y + p[1] * esc)

        def _moveTo(self, p):
            self.cur = [self.T(p)]
            self.contornos.append(self.cur)

        def _lineTo(self, p):
            self.cur.append(self.T(p))

        def _curveToOne(self, p1, p2, p3):
            p0 = self._getCurrentPoint()
            for i in range(1, passos + 1):
                t = i / passos
                a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
                self.cur.append(self.T((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                                        a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])))

        def _qCurveToOne(self, p1, p2):
            p0 = self._getCurrentPoint()
            for i in range(1, passos + 1):
                t = i / passos
                a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t ** 2
                self.cur.append(self.T((a * p0[0] + b * p1[0] + c * p2[0],
                                        a * p0[1] + b * p1[1] + c * p2[1])))

        def _closePath(self):
            if self.cur and len(self.cur) > 1 and math.dist(self.cur[0], self.cur[-1]) < 1e-6:
                self.cur.pop()

    contornos, avanco = [], 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = Pen(gs, avanco + pos.x_offset)
        gs[ordem[info.codepoint]].draw(pen)
        contornos += [c for c in pen.contornos if len(c) >= 3]
        avanco += pos.x_advance + track_em * upem
    return contornos


# ---------------------------------- conteúdo do selo ------------------------------------
def itens_selo(cfg: dict, prancha: dict) -> list[dict]:
    """Lista de primitivas do selo (coordenadas locais em mm)."""
    esc, obra = cfg["escritorio"], cfg["obra"]
    L, it = SELO_L, []

    def fill(x0, y0, x1, y1, layer, cor):
        it.append(dict(t="fill", x0=x0, y0=y0, x1=x1, y1=y1, layer=layer, cor=cor))

    def linha(x0, y0, x1, y1, layer, cor, lw):
        it.append(dict(t="line", x0=x0, y0=y0, x1=x1, y1=y1, layer=layer, cor=cor, lw=lw))

    def texto(x, y, s, f, corpo, cor, layer, anchor="start", track=0.0, attr=None, prompt=None):
        it.append(dict(t="text", x=x, y=y, s=s, f=f, size=corpo, cor=cor, layer=layer,
                       anchor=anchor, track=track, attr=attr, prompt=prompt))

    def kicker(y_base, rotulo):
        corpo = 2.7
        meio = y_base + 0.73 * corpo / 2
        fill(PAD, meio - 0.3, PAD + 4.5, meio + 0.3, "MOOS-SELO-DESTAQUE", CORES["accent"])
        texto(PAD + 6.6, y_base, rotulo, "mono", corpo, CORES["accent"], "MOOS-SELO-DESTAQUE", track=0.18)

    # ---- preenchimentos (desenhados primeiro, ficam atrás) ----
    fill(L * 3 / 4, F_META[0], L, F_META[1], "MOOS-SELO-PREENCH", CORES["accent_soft"])

    # ---- linhas ----
    C, D, DF = ("MOOS-SELO-CONTORNO", CORES["ink900"], 0.35), ("MOOS-SELO-DIVISAO", CORES["div"], 0.25), \
        ("MOOS-SELO-DIV-FINA", CORES["div_fina"], 0.18)
    for (x0, y0, x1, y1) in [(0, 0, L, 0), (L, 0, L, SELO_A), (L, SELO_A, 0, SELO_A), (0, SELO_A, 0, 0)]:
        linha(x0, y0, x1, y1, *C)
    linha(0, F_CAB[1], L, F_CAB[1], *C)                      # aprovações | identificação
    for yy in (F_CAB[0], F_OBRA[0], F_META[0], F_DADOS[0], F_RODAPE[1]):
        linha(0, yy, L, yy, *D)
    for k in (1, 2, 3):
        linha(L * k / 4, F_META[0], L * k / 4, F_META[1], *D)
    passo = (F_DADOS[1] - F_DADOS[0]) / 4
    for k in (1, 2, 3):
        yy = F_DADOS[0] + k * passo
        linha(PAD, yy, L - PAD, yy, *DF)

    # ---- aprovações ----
    kicker(F_APROV[1] - 5.8, "APROVAÇÕES")

    # ---- cabeçalho: logo + marca + tipo de projeto ----
    meio_cab = (F_CAB[0] + F_CAB[1]) / 2
    h_logo = 10.5
    it.append(dict(t="logo", x=PAD, y=meio_cab - h_logo / 2, h=h_logo, layer="MOOS-SELO-LOGO", cor=CORES["logo"]))
    larg_logo = h_logo * 188.1 / 217.2
    it.append(dict(t="marca", x=PAD + larg_logo + 3.0, y=meio_cab - 0.70 * 5.4 / 2, s=esc["marca"],
                   f="display", size=5.4, track=-0.01, layer="MOOS-SELO-LOGO", cor=CORES["ink900"]))
    texto(L - PAD, meio_cab - 0.73 * 2.7 / 2, obra["projeto"].upper(), "mono", 2.7, CORES["ink500"],
          "MOOS-SELO-ATRIB", anchor="end", track=0.14, attr="PROJETO", prompt="Tipo de projeto")

    # ---- obra ----
    kicker(F_OBRA[1] - 5.8, "OBRA")
    texto(PAD, F_OBRA[0] + 12.4, obra["nome"], "display", 7.5, CORES["ink900"], "MOOS-SELO-ATRIB",
          track=-0.02, attr="OBRA", prompt="Nome da obra")
    texto(PAD, F_OBRA[0] + 5.4, obra["endereco"], "body", 3.6, CORES["ink600"], "MOOS-SELO-ATRIB",
          attr="ENDERECO", prompt="Endereço da obra")

    # ---- linha de metadados (4 células) ----
    celulas = [("DATA", obra["data"], "DATA"), ("ESCALA", obra["escala"], "ESCALA"),
               ("DESENHISTA", obra.get("desenhista") or "—", "DESENHISTA"),
               ("PRANCHA", prancha["numero"], "PRANCHA")]
    for k, (rot, val, tag) in enumerate(celulas):
        x = L * k / 4 + PAD
        destaque = tag == "PRANCHA"
        texto(x, F_META[1] - 5.0, rot, "mono", 2.5, CORES["accent"] if destaque else CORES["ink400"],
              "MOOS-SELO-DESTAQUE" if destaque else "MOOS-SELO-ROTULO", track=0.12)
        if tag == "PRANCHA":
            texto(x, F_META[0] + 4.4, val, "display", 6.2, CORES["accent"], "MOOS-SELO-DESTAQUE",
                  track=-0.01, attr=tag, prompt="Prancha (nº/total)")
        else:
            texto(x, F_META[0] + 4.8, val, "display_sb", 4.4, CORES["ink900"], "MOOS-SELO-ATRIB",
                  attr=tag, prompt=rot.capitalize())

    # ---- dados (tabela chave/valor) ----
    linhas_kv = [("PROPRIETÁRIO", obra["proprietario"], "PROPRIETARIO", "Proprietário"),
                 ("CPF / CNPJ", obra["cpf_cnpj"], "CPF_CNPJ", "CPF ou CNPJ do proprietário"),
                 ("CONTEÚDO", prancha["conteudo"], "CONTEUDO", "Conteúdo da prancha"),
                 ("RESP. TÉCNICO", esc["rt_linha"], "RESP_TECNICO", "Responsável técnico")]
    for k, (rot, val, tag, pr) in enumerate(linhas_kv):
        yb = F_DADOS[1] - (k + 1) * passo + 3.4
        texto(PAD, yb, rot, "mono", 2.5, CORES["ink500"], "MOOS-SELO-ROTULO", track=0.08)
        texto(PAD + 31.0, yb, val, "body_md", 3.5, CORES["ink900"], "MOOS-SELO-ATRIB", attr=tag, prompt=pr)

    # ---- assinaturas ----
    y_ass = F_ASSIN[0] + 16.5
    digitos = re.sub(r"\D", "", obra["cpf_cnpj"])
    doc_prop = ("CNPJ " if len(digitos) == 14 else "CPF ") + obra["cpf_cnpj"]
    colunas = [
        (PAD, L / 2 - PAD, esc["rt_nome"], esc["rt_doc"], "RESPONSÁVEL TÉCNICO", "ASS_RT_NOME", "ASS_RT_DOC"),
        (L / 2 + PAD, L - PAD, obra["proprietario"], doc_prop, "PROPRIETÁRIO", "ASS_PROP_NOME", "ASS_PROP_DOC"),
    ]
    for x0, x1, nome, doc, papel, tag_n, tag_d in colunas:
        linha(x0, y_ass, x1, y_ass, "MOOS-SELO-ASSINATURA", CORES["ink700"], 0.25)
        texto(x0, y_ass - 4.3, nome, "display_sb", 3.4, CORES["ink900"], "MOOS-SELO-ATRIB",
              attr=tag_n, prompt="Nome (assinatura)")
        texto(x0, y_ass - 8.2, doc, "body", 2.7, CORES["ink600"], "MOOS-SELO-ATRIB",
              attr=tag_d, prompt="Documento (assinatura)")
        texto(x0, y_ass - 12.1, papel, "mono", 2.3, CORES["ink400"], "MOOS-SELO-ROTULO", track=0.12)

    # ---- rodapé ----
    yb = (F_RODAPE[0] + F_RODAPE[1]) / 2 - 0.727 * 2.4 / 2
    texto(PAD, yb, esc["rodape"], "body", 2.4, CORES["ink400"], "MOOS-SELO-ROTULO")
    texto(L - PAD, yb, esc["contato"], "body", 2.4, CORES["ink400"], "MOOS-SELO-ROTULO", anchor="end")
    return it


# ---------------------------------- PDF (SVG -> Chromium) -------------------------------
def svg_folha(cfg: dict, prancha: dict, logo: Logo, fontes: Path) -> str:
    W, H = prancha["folha"]
    ox, oy = W - MARGEM - SELO_L, MARGEM          # canto inferior esquerdo do selo na folha
    out = []

    def Y(y):
        return H - y

    # folha e moldura
    out.append(f'<rect x="0.15" y="0.15" width="{W - 0.3}" height="{H - 0.3}" fill="none" '
               f'stroke="{CORES["ink400"]}" stroke-width="0.13"/>')
    out.append(f'<rect x="{MARGEM_ESQ}" y="{MARGEM}" width="{W - MARGEM_ESQ - MARGEM}" '
               f'height="{H - 2 * MARGEM}" fill="none" stroke="{CORES["ink900"]}" stroke-width="0.7"/>')

    for e in itens_selo(cfg, prancha):
        if e["t"] == "fill":
            out.append(f'<rect x="{ox + e["x0"]:.3f}" y="{Y(oy + e["y1"]):.3f}" width="{e["x1"] - e["x0"]:.3f}" '
                       f'height="{e["y1"] - e["y0"]:.3f}" fill="{e["cor"]}"/>')
        elif e["t"] == "line":
            out.append(f'<line x1="{ox + e["x0"]:.3f}" y1="{Y(oy + e["y0"]):.3f}" x2="{ox + e["x1"]:.3f}" '
                       f'y2="{Y(oy + e["y1"]):.3f}" stroke="{e["cor"]}" stroke-width="{e["lw"]}" '
                       f'stroke-linecap="square"/>')
        elif e["t"] == "logo":
            out.append(f'<path fill="{e["cor"]}" fill-rule="evenodd" '
                       f'd="{logo.svg_path(ox + e["x"], oy + e["y"], e["h"], H)}"/>')
        elif e["t"] in ("text", "marca"):
            fam, peso, _ = FONTES[e["f"]]
            anchor = e.get("anchor", "start")
            x = ox + e["x"]
            if anchor == "end" and e.get("track"):
                x += e["track"] * e["size"]          # compensa o espaçamento após a última letra
            out.append(
                f'<text x="{x:.3f}" y="{Y(oy + e["y"]):.3f}" font-family="{fam}" font-weight="{peso}" '
                f'font-size="{e["size"]}" fill="{e["cor"]}" text-anchor="{anchor}" '
                f'letter-spacing="{e.get("track", 0) * e["size"]:.4f}">{escape(e["s"])}</text>')

    faces = "\n".join(
        f"@font-face{{font-family:'{fam}';font-weight:{peso};src:url('{(fontes / arq).as_uri()}') format('truetype')}}"
        for fam, peso, arq in FONTES.values())
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
{faces}
@page{{size:{W}mm {H}mm;margin:0}}
html,body{{margin:0;padding:0;background:#fff}}
svg{{display:block;width:{W}mm;height:{H}mm;text-rendering:geometricPrecision;font-kerning:normal}}
</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">
{chr(10).join(out)}
</svg></body></html>"""


NODE_PDF = r"""
const { chromium } = require('playwright');
(async () => {
  const jobs = JSON.parse(process.argv[2]);
  const b = await chromium.launch();
  const p = await b.newPage();
  for (const j of jobs) {
    await p.goto('file://' + j.html);
    await p.evaluate(() => document.fonts.ready);
    await p.pdf({ path: j.pdf, width: j.w + 'mm', height: j.h + 'mm', printBackground: true,
                  margin: { top: 0, right: 0, bottom: 0, left: 0 }, preferCSSPageSize: true });
  }
  await b.close();
})();
"""


def gerar_pdf(cfg: dict, logo: Logo, fontes: Path, destino: Path) -> None:
    from pypdf import PdfWriter

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        jobs = []
        for i, pr in enumerate(cfg["pranchas"]):
            html = tmp / f"p{i}.html"
            html.write_text(svg_folha(cfg, pr, logo, fontes), encoding="utf-8")
            jobs.append({"html": str(html), "pdf": str(tmp / f"p{i}.pdf"), "w": pr["folha"][0], "h": pr["folha"][1]})
        js = tmp / "pdf.js"
        js.write_text(NODE_PDF, encoding="utf-8")
        subprocess.run(["node", str(js), json.dumps(jobs)], check=True)
        w = PdfWriter()
        for j in jobs:
            w.append(j["pdf"])
        w.add_metadata({"/Title": f'{cfg["obra"]["nome"]} — Pranchas', "/Author": cfg["escritorio"]["marca"]})
        with open(destino, "wb") as f:
            w.write(f)


# ---------------------------------- DXF -------------------------------------------------
NOME_BLOCO = "SELO_MOOSHAMMER"


def _novo_doc_dxf():
    import ezdxf

    doc = ezdxf.new("R2010", setup=False)
    doc.units = ezdxf.units.MM
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2
    doc.header["$LUPREC"] = 2
    for nome, (cor, aci, lw) in LAYERS.items():
        ly = doc.layers.add(nome, color=aci)
        ly.rgb = hex_rgb(CORES[cor])
        ly.dxf.lineweight = lw
    doc.styles.add("MOOS_TEXTO", font="arial.ttf")
    doc.styles.add("MOOS_NEGRITO", font="arialbd.ttf")
    doc.styles.add("MOOS_ROTULO", font="arial.ttf")
    return doc


def _desenhar_selo(alvo, cfg: dict, prancha: dict, logo: Logo, fontes: Path) -> None:
    """Desenha o selo (coordenadas locais) num bloco ou no model space, com ATTDEFs."""
    import ezdxf
    from ezdxf.enums import TextEntityAlignment

    for e in itens_selo(cfg, prancha):
        da = {"layer": e["layer"]}
        if e.get("cor") and e["cor"].upper() != CORES[LAYERS[e["layer"]][0]].upper():
            da["true_color"] = ezdxf.colors.rgb2int(hex_rgb(e["cor"]))
        if e["t"] == "fill":
            h = alvo.add_hatch(dxfattribs=da)
            h.set_solid_fill(color=LAYERS[e["layer"]][1], rgb=hex_rgb(e["cor"]))
            h.paths.add_polyline_path([(e["x0"], e["y0"]), (e["x1"], e["y0"]), (e["x1"], e["y1"]), (e["x0"], e["y1"])],
                                      is_closed=True)
        elif e["t"] == "line":
            alvo.add_line((e["x0"], e["y0"]), (e["x1"], e["y1"]), dxfattribs=da)
        elif e["t"] in ("logo", "marca"):
            if e["t"] == "logo":
                polys = logo.contornos(e["x"], e["y"], e["h"])
            else:   # nome da marca em curvas: fica idêntico em qualquer CAD, sem depender de fonte
                polys = texto_em_curvas(fontes, e["f"], e["s"], e["x"], e["y"], e["size"], e.get("track", 0.0))
            h = alvo.add_hatch(dxfattribs=da)
            h.set_solid_fill(color=LAYERS[e["layer"]][1], rgb=hex_rgb(e["cor"]))
            h.dxf.hatch_style = 0      # paridade par/ímpar: furos das letras e do hexágono
            for p in polys:
                h.paths.add_polyline_path(p, is_closed=True)
        elif e["t"] == "text":
            da.update(height=round(e["size"] * cap_ratio(fontes, e["f"]), 3), style=DXF_ESTILO[e["f"]])
            alinh = TextEntityAlignment.RIGHT if e["anchor"] == "end" else TextEntityAlignment.LEFT
            if e["attr"]:
                a = alvo.add_attdef(e["attr"], (e["x"], e["y"]), text=e["s"], dxfattribs=da)
                a.dxf.prompt = e["prompt"] or e["attr"]
                a.set_placement((e["x"], e["y"]), align=alinh)
            else:
                alvo.add_text(e["s"], dxfattribs=da).set_placement((e["x"], e["y"]), align=alinh)


def _salvar(doc, destino: Path) -> None:
    auditoria = doc.audit()
    if auditoria.has_errors:
        raise RuntimeError(f"DXF com erros: {auditoria.errors}")
    doc.saveas(destino)


def gerar_dxf(cfg: dict, logo: Logo, fontes: Path, destino: Path) -> None:
    """Pranchas (folha + moldura) com o selo inserido como bloco com atributos preenchidos."""
    doc = _novo_doc_dxf()
    # ponto base no canto inferior DIREITO do selo -> encaixa no canto da moldura
    blk = doc.blocks.new(name=NOME_BLOCO, base_point=(SELO_L, 0))
    _desenhar_selo(blk, cfg, cfg["pranchas"][0], logo, fontes)

    msp = doc.modelspace()
    x_off = 0.0
    for pr in cfg["pranchas"]:
        W, H = pr["folha"]
        msp.add_lwpolyline([(x_off, 0), (x_off + W, 0), (x_off + W, H), (x_off, H)], close=True,
                           dxfattribs={"layer": "MOOS-FOLHA"})
        msp.add_lwpolyline([(x_off + MARGEM_ESQ, MARGEM), (x_off + W - MARGEM, MARGEM),
                            (x_off + W - MARGEM, H - MARGEM), (x_off + MARGEM_ESQ, H - MARGEM)], close=True,
                           dxfattribs={"layer": "MOOS-MOLDURA"})
        valores = {e["attr"]: e["s"] for e in itens_selo(cfg, pr) if e["t"] == "text" and e["attr"]}
        msp.add_blockref(NOME_BLOCO, (x_off + W - MARGEM, MARGEM), dxfattribs={"layer": "0"}) \
            .add_auto_attribs(valores)
        x_off += W + 60.0
    _salvar(doc, destino)


def gerar_dxf_bloco(cfg: dict, logo: Logo, fontes: Path, destino: Path) -> None:
    """Só o selo, no model space, com ATTDEFs e INSBASE no canto inferior direito.
    No AutoCAD: INSERT > Procurar > este arquivo -> vira bloco e pede os campos."""
    doc = _novo_doc_dxf()
    doc.header["$INSBASE"] = (SELO_L, 0, 0)
    _desenhar_selo(doc.modelspace(), cfg, cfg["pranchas"][0], logo, fontes)
    _salvar(doc, destino)


# ---------------------------------- main ------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Gera prancha + selo Mooshammer (PDF + DXF).")
    ap.add_argument("config", type=Path, help="JSON com os dados da obra (ver exemplo_obra.json)")
    ap.add_argument("--saida", type=Path, default=Path("."), help="pasta de saída")
    ap.add_argument("--fontes", type=Path, default=AQUI / "fonts", help="pasta das fontes TTF")
    ap.add_argument("--logo", type=Path, default=AQUI / "logo_mooshammer.json")
    ap.add_argument("--sem-pdf", action="store_true")
    ap.add_argument("--sem-dxf", action="store_true")
    a = ap.parse_args()

    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    garantir_fontes(a.fontes)
    logo = Logo(a.logo)
    a.saida.mkdir(parents=True, exist_ok=True)
    base = cfg.get("arquivo", "Prancha_Selo_Mooshammer")
    if not a.sem_pdf:
        if not shutil.which("node"):
            sys.exit("Node.js não encontrado (necessário para o PDF). Use --sem-pdf para gerar só o DXF.")
        gerar_pdf(cfg, logo, a.fontes, a.saida / f"{base}.pdf")
        print("PDF:", a.saida / f"{base}.pdf")
    if not a.sem_dxf:
        gerar_dxf(cfg, logo, a.fontes, a.saida / f"{base}.dxf")
        gerar_dxf_bloco(cfg, logo, a.fontes, a.saida / f"{base}_SELO_bloco.dxf")
        print("DXF:", a.saida / f"{base}.dxf")
        print("DXF (só o selo, para INSERT):", a.saida / f"{base}_SELO_bloco.dxf")


if __name__ == "__main__":
    main()
