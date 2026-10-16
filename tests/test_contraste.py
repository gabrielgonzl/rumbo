# -*- coding: utf-8 -*-
"""V5: auditoría de contraste (WCAG 2.1) de los tokens de «Carta de navegación», en ambos temas.

Texto ≥ 4,5:1 sobre todas las superficies; elementos gráficos y bordes de campos ≥ 3:1.
Ejecutado como script imprime el informe en Markdown (docs/auto/contraste.md).
"""
import os
import re
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(RAIZ, "app", "web", "tema-carta.css")

SUPERFICIES = ("plano", "sup", "sup2", "sup3")
TEXTO = ("tinta", "tinta2", "tinta3", "bien", "mal", "aviso", "mar", "laton")
GRAFICOS = tuple(f"s{i}" for i in range(1, 13))


def tokens(tema):
    css = open(CSS, encoding="utf-8").read()
    bloque = re.search(r":root\{(.*?)\}" if tema == "oscuro" else r':root\[data-tema="claro"\]\{(.*?)\}', css, re.S).group(1)
    return dict(re.findall(r"--([a-z0-9-]+):(#[0-9a-fA-F]{6})", bloque))


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contraste(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def auditoria():
    """[(tema, grupo, primer plano, fondo, ratio, mínimo)]"""
    filas = []
    for tema in ("claro", "oscuro"):
        t = tokens(tema)
        for fg in TEXTO:
            for bg in SUPERFICIES:
                filas.append((tema, "texto", fg, bg, contraste(t[fg], t[bg]), 4.5))
        for fg in GRAFICOS:
            for bg in ("plano", "sup"):
                filas.append((tema, "gráfico", fg, bg, contraste(t[fg], t[bg]), 3.0))
        for bg in ("plano", "sup"):
            filas.append((tema, "borde de campo", "campo", bg, contraste(t["campo"], t[bg]), 3.0))
        filas.append((tema, "texto sobre acento", "sobre-acento", "mar", contraste(t["sobre-acento"], t["mar"]), 4.5))
    return filas


class Contraste(unittest.TestCase):
    def test_todos_los_pares_cumplen(self):
        fallos = [f"{t} · {g}: {fg} sobre {bg} = {r:.2f} (mín. {m})" for t, g, fg, bg, r, m in auditoria() if r < m]
        self.assertEqual(fallos, [], "\n" + "\n".join(fallos))

    def test_los_filtros_apagados_no_usan_opacidad(self):
        """Regresión V5: la opacidad dejaba «Solo largo plazo» en 1,85:1."""
        css = open(CSS, encoding="utf-8").read()
        self.assertIn('.filtro[aria-pressed="false"]{opacity:1;color:var(--tinta3)}', css)

    def test_el_calculo_es_correcto(self):
        self.assertAlmostEqual(contraste("#000000", "#ffffff"), 21.0, places=1)
        self.assertAlmostEqual(contraste("#777777", "#ffffff"), 4.48, places=1)


def informe():
    filas = auditoria()
    out = ["# Auditoría de contraste (V5)", "",
           "Generada con `python tests/test_contraste.py` sobre `app/web/tema-carta.css` (WCAG 2.1: texto ≥ 4,5:1; "
           "gráficos y bordes de campo ≥ 3:1).", ""]
    fallos = [f for f in filas if f[4] < f[5]]
    out.append(f"**{len(filas) - len(fallos)} de {len(filas)} pares cumplen.**" + (f" Fallan {len(fallos)}:" if fallos else ""))
    out.append("")
    if fallos:
        out += ["| Tema | Tipo | Color | Fondo | Ratio | Mínimo |", "|---|---|---|---|---|---|"]
        out += [f"| {t} | {g} | `{fg}` | `{bg}` | {r:.2f} | {m} |" for t, g, fg, bg, r, m in fallos]
        out.append("")
    for tema in ("claro", "oscuro"):
        out += [f"## Tema {tema}", "", "| Grupo | Mínimo ratio | Peor par |", "|---|---|---|"]
        for g in ("texto", "gráfico", "borde de campo", "texto sobre acento"):
            sub = [f for f in filas if f[0] == tema and f[1] == g]
            w = min(sub, key=lambda f: f[4] / f[5])
            out.append(f"| {g} | {w[4]:.2f} (mín. {w[5]}) | `{w[2]}` sobre `{w[3]}` |")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    if "--informe" in sys.argv:
        print(informe())
    else:
        unittest.main()
