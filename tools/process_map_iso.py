#!/usr/bin/env python3
"""Isometric process-map illustration for the VeriRoute closing marketplace.

Vendor side (left) -> Command Center Hub (centre) <- Customer side (right), with the
"Work Assignment" and "Deliver Work & Payment Bill" flows along the bottom.

Writes a standalone SVG (fonts embedded when --fonts points at Inter woff2 files).
Render to PNG with any browser, e.g.:
    chromium --headless --screenshot=map.png --window-size=1920,1080 \
             --force-device-scale-factor=2 map.svg

Usage: python3 tools/process_map_iso.py OUT.svg [--fonts DIR]
"""
import base64
import math
import os
import sys

W, H = 1920, 1080
S = 40.0                       # pixels per world unit
CX, CY = 960.0, 590.0
C = math.cos(math.pi / 6)

NAVY, NAVY2, NAVY3 = "#12294A", "#1F3A5F", "#2C4F7C"
TEAL, TEAL_L = "#1FA5A0", "#5FE3D6"
GRAY_T, GRAY_L, GRAY_R = "#F4F6F9", "#C9D2DC", "#A9B5C3"
INK = "#1B2A3D"

out = []


def P(x, y, z=0.0):
    return (CX + (x - y) * C * S, CY + (x + y) * 0.5 * S - z * S)


def TW(t, w, z=0.0):
    """Point from along-screen (t = x - y) and depth (w = x + y) coordinates."""
    return P((w + t) / 2, (w - t) / 2, z)


def pts(ps):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in ps)


def poly(ps, fill, extra=""):
    out.append(f'<polygon points="{pts(ps)}" fill="{fill}" {extra}/>')


def box(x, y, z, w, d, h, top, left, right, edge=None, extra=""):
    poly([P(x, y + d, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x, y + d, z + h)], left, extra)
    poly([P(x + w, y, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x + w, y, z + h)], right, extra)
    poly([P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h)], top, extra)
    if edge:
        out.append(f'<polyline points="{pts([P(x, y + d, z + h), P(x + w, y + d, z + h), P(x + w, y, z + h)])}" '
                   f'fill="none" stroke="{edge}" stroke-width="2" filter="url(#glow)" opacity=".9"/>')


def panel(tl, tr, bl, vw, vh, inner):
    """Place inner content (drawn in a vw x vh box) onto the parallelogram tl/tr/bl."""
    a, b = (tr[0] - tl[0]) / vw, (tr[1] - tl[1]) / vw
    c, d = (bl[0] - tl[0]) / vh, (bl[1] - tl[1]) / vh
    out.append(f'<g transform="matrix({a:.5f} {b:.5f} {c:.5f} {d:.5f} {tl[0]:.1f} {tl[1]:.1f})">{inner}</g>')


# ---------------------------------------------------------------- screen contents
def dashboard(vw, vh, kind=0):
    g = [f'<rect width="{vw}" height="{vh}" fill="url(#scr)"/>',
         f'<rect width="{vw}" height="{vh * .09:.1f}" fill="#0E3552"/>',
         f'<circle cx="{vh * .045:.1f}" cy="{vh * .045:.1f}" r="{vh * .022:.1f}" fill="{TEAL_L}"/>',
         f'<rect x="{vh * .09:.1f}" y="{vh * .03:.1f}" width="{vw * .25:.1f}" height="{vh * .03:.1f}" rx="2" fill="#7FA6C9" opacity=".7"/>']
    if kind == 0:  # KPI tiles + bar chart
        for i in range(4):
            x = vw * (.04 + i * .24)
            g.append(f'<rect x="{x:.1f}" y="{vh * .14:.1f}" width="{vw * .2:.1f}" height="{vh * .18:.1f}" rx="3" fill="#123E5E"/>')
            g.append(f'<rect x="{x + 4:.1f}" y="{vh * .17:.1f}" width="{vw * .1:.1f}" height="{vh * .025:.1f}" fill="#6D93B5"/>')
            g.append(f'<text x="{x + 4:.1f}" y="{vh * .29:.1f}" font-size="{vh * .08:.1f}" font-weight="800" '
                     f'fill="{[TEAL_L, "#8CC8FF", "#F2C14E", TEAL_L][i]}">{[128, 42, 17, 96][i]}</text>')
        for i in range(12):
            bh = vh * (.12 + .38 * abs(math.sin(i * 1.7 + 1)))
            g.append(f'<rect x="{vw * (.05 + i * .075):.1f}" y="{vh * .92 - bh:.1f}" width="{vw * .045:.1f}" '
                     f'height="{bh:.1f}" rx="1.5" fill="{TEAL if i % 3 else "#4FA3FF"}" opacity=".9"/>')
    elif kind == 1:  # line chart + table
        line = " ".join(f"{vw * (.05 + i * .09):.1f},{vh * (.5 - .22 * math.sin(i * .8) - i * .012):.1f}" for i in range(11))
        g.append(f'<polyline points="{line}" fill="none" stroke="{TEAL_L}" stroke-width="{vh * .018:.1f}" stroke-linejoin="round"/>')
        g.append(f'<polyline points="{line} {vw * .95:.1f},{vh * .55:.1f} {vw * .05:.1f},{vh * .55:.1f}" fill="{TEAL}" opacity=".18"/>')
        for i in range(5):
            y = vh * (.62 + i * .075)
            g.append(f'<rect x="{vw * .05:.1f}" y="{y:.1f}" width="{vw * .9:.1f}" height="{vh * .05:.1f}" rx="2" fill="#123E5E"/>')
            g.append(f'<rect x="{vw * .07:.1f}" y="{y + vh * .015:.1f}" width="{vw * (.25 + .1 * (i % 3)):.1f}" height="{vh * .02:.1f}" fill="#7FA6C9"/>')
            g.append(f'<circle cx="{vw * .9:.1f}" cy="{y + vh * .025:.1f}" r="{vh * .014:.1f}" fill="{[TEAL_L, "#F2C14E", TEAL_L, "#8CC8FF", TEAL_L][i]}"/>')
    else:  # dispatch map
        g.append(f'<rect x="{vw * .04:.1f}" y="{vh * .13:.1f}" width="{vw * .92:.1f}" height="{vh * .82:.1f}" rx="3" fill="#0F3150"/>')
        for i in range(7):
            g.append(f'<line x1="{vw * .04:.1f}" y1="{vh * (.2 + i * .11):.1f}" x2="{vw * .96:.1f}" y2="{vh * (.16 + i * .12):.1f}" stroke="#1E4E74" stroke-width="1"/>')
            g.append(f'<line x1="{vw * (.1 + i * .13):.1f}" y1="{vh * .13:.1f}" x2="{vw * (.14 + i * .12):.1f}" y2="{vh * .95:.1f}" stroke="#1E4E74" stroke-width="1"/>')
        route = [(.15, .8), (.3, .55), (.48, .62), (.62, .35), (.82, .28)]
        g.append(f'<polyline points="{" ".join(f"{vw * a:.1f},{vh * b:.1f}" for a, b in route)}" fill="none" '
                 f'stroke="{TEAL_L}" stroke-width="{vh * .02:.1f}" stroke-dasharray="{vh * .05:.1f} {vh * .03:.1f}"/>')
        for a, b in route:
            g.append(f'<circle cx="{vw * a:.1f}" cy="{vh * b:.1f}" r="{vh * .03:.1f}" fill="#F2C14E" stroke="#0B1F33" stroke-width="1"/>')
    return "".join(g)


def doc_screen(vw, vh):
    g = [f'<rect width="{vw}" height="{vh}" fill="url(#scr)"/>',
         f'<rect x="{vw * .08:.1f}" y="{vh * .1:.1f}" width="{vw * .38:.1f}" height="{vh * .8:.1f}" rx="2" fill="#EAF1F7"/>']
    for i in range(6):
        g.append(f'<rect x="{vw * .12:.1f}" y="{vh * (.2 + i * .1):.1f}" width="{vw * (.3 - .04 * (i % 2)):.1f}" height="{vh * .035:.1f}" fill="#9FB3C8"/>')
    g.append(f'<circle cx="{vw * .37:.1f}" cy="{vh * .78:.1f}" r="{vh * .07:.1f}" fill="none" stroke="#C0392B" stroke-width="{vh * .02:.1f}"/>')
    for i in range(4):
        g.append(f'<rect x="{vw * .54:.1f}" y="{vh * (.14 + i * .2):.1f}" width="{vw * .38:.1f}" height="{vh * .14:.1f}" rx="2" fill="#123E5E"/>')
        g.append(f'<rect x="{vw * .57:.1f}" y="{vh * (.19 + i * .2):.1f}" width="{vw * .2:.1f}" height="{vh * .035:.1f}" fill="{TEAL_L}"/>')
    return "".join(g)


def logo_screen(vw, vh):
    return (f'<rect width="{vw}" height="{vh}" fill="url(#scrMain)"/>'
            f'<rect width="{vw}" height="{vh}" fill="url(#scan)" opacity=".35"/>'
            f'<g transform="translate({vw / 2:.1f} {vh * .36:.1f})">{logo_mark(vh * .19)}</g>'
            f'<text x="{vw / 2:.1f}" y="{vh * .68:.1f}" text-anchor="middle" font-size="{vh * .135:.1f}" font-weight="800" '
            f'fill="#FFFFFF" letter-spacing="1">Veri<tspan fill="{TEAL_L}">Route</tspan></text>'
            f'<text x="{vw / 2:.1f}" y="{vh * .8:.1f}" text-anchor="middle" font-size="{vh * .058:.1f}" font-weight="600" '
            f'fill="#BFD6EA" letter-spacing="2">— CLOSING PLATFORM —</text>'
            f'<rect x="{vw * .2:.1f}" y="{vh * .88:.1f}" width="{vw * .6:.1f}" height="{vh * .012:.1f}" rx="1" fill="{TEAL}" opacity=".7"/>')


def logo_mark(r):
    """Shield with a route line and check mark."""
    return (f'<path d="M0,{-r:.1f} L{r * .85:.1f},{-r * .62:.1f} L{r * .85:.1f},{r * .05:.1f} '
            f'Q{r * .85:.1f},{r * .7:.1f} 0,{r:.1f} Q{-r * .85:.1f},{r * .7:.1f} {-r * .85:.1f},{r * .05:.1f} '
            f'L{-r * .85:.1f},{-r * .62:.1f} Z" fill="url(#shield)" stroke="{TEAL_L}" stroke-width="{r * .07:.1f}"/>'
            f'<path d="M{-r * .45:.1f},{r * .35:.1f} C{-r * .1:.1f},{r * .35:.1f} {-r * .35:.1f},{-r * .3:.1f} {r * .05:.1f},{-r * .3:.1f}" '
            f'fill="none" stroke="#FFFFFF" stroke-width="{r * .09:.1f}" stroke-dasharray="{r * .14:.1f} {r * .09:.1f}" stroke-linecap="round"/>'
            f'<path d="M{-r * .05:.1f},{r * .05:.1f} L{r * .15:.1f},{r * .27:.1f} L{r * .5:.1f},{-r * .3:.1f}" fill="none" '
            f'stroke="{TEAL_L}" stroke-width="{r * .16:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')


def admin_screen(vw, vh):
    g = [f'<rect width="{vw}" height="{vh}" rx="4" fill="url(#holo)" stroke="{TEAL_L}" stroke-width="1.2"/>',
         f'<text x="8" y="15" font-size="10" font-weight="800" fill="#FFFFFF">SYSTEM ADMIN</text>']
    for i, lab in enumerate(["Users &amp; Roles", "Agreements", "Audit Log", "Integrations"]):
        y = 24 + i * 14
        g.append(f'<rect x="8" y="{y}" width="{vw - 16}" height="11" rx="2" fill="#0E3552" opacity=".85"/>')
        g.append(f'<text x="13" y="{y + 8.5}" font-size="7.5" fill="#CFE6F5">{lab}</text>')
        g.append(f'<rect x="{vw - 30}" y="{y + 3}" width="14" height="5" rx="2.5" fill="{TEAL_L if i != 2 else "#F2C14E"}"/>')
    return "".join(g)


# ---------------------------------------------------------------- people & props
SUITS = {"navy": ("#22324A", "#1A2638"), "charcoal": ("#3A414D", "#2A3039"), "gray": ("#6B7684", "#505966"),
         "teal": ("#2D6468", "#224E51"), "beige": ("#B9A58A", "#8F7F69"), "blue": ("#2F5D8C", "#244A70"),
         "slate": ("#48566A", "#39455A")}


def person(x, y, z, suit="navy", skin="#E6B08A", hair="#2B1D14", facing="front", female=False,
           tie="#1FA5A0", prop=None, label=None, h=94.0):
    sx, sy = P(x, y, z)
    col, dark = SUITS[suit]
    r = h * .105
    g = [f'<ellipse cx="{sx:.1f}" cy="{sy:.1f}" rx="{h * .22:.1f}" ry="{h * .075:.1f}" fill="#0B1B2E" opacity=".22" filter="url(#blur2)"/>']
    hip = sy - h * .47
    ys = sy - h * .80
    hy = ys - h * .12
    lw = h * (.085 if female else .1)
    # legs + shoes
    for dx in (-h * .065, h * .065):
        leg = "#2E3440" if female else dark
        g.append(f'<rect x="{sx + dx - lw / 2:.1f}" y="{hip:.1f}" width="{lw:.1f}" height="{h * .45:.1f}" rx="{lw * .4:.1f}" fill="{leg}"/>')
        g.append(f'<ellipse cx="{sx + dx + (1.5 if facing == "front" else -1.5):.1f}" cy="{sy - 2:.1f}" rx="{lw * .75:.1f}" ry="3.2" fill="#15181D"/>')
    if female:
        g.append(f'<path d="M{sx - h * .15:.1f},{hip - 2:.1f} L{sx + h * .15:.1f},{hip - 2:.1f} L{sx + h * .18:.1f},{sy - h * .26:.1f} '
                 f'L{sx - h * .18:.1f},{sy - h * .26:.1f} Z" fill="{dark}"/>')
    # long hair behind the head (female, front view)
    if female and facing == "front":
        g.append(f'<rect x="{sx - r * 1.12:.1f}" y="{hy - r:.1f}" width="{r * 2.24:.1f}" height="{r * 2.5:.1f}" rx="{r:.1f}" fill="{hair}"/>')
    # torso
    ws, ww, rr = h * .40, h * .30, h * .07
    torso = (f'M{sx - ws / 2 + rr:.1f},{ys:.1f} Q{sx - ws / 2:.1f},{ys:.1f} {sx - ws / 2:.1f},{ys + rr:.1f} '
             f'L{sx - ww / 2:.1f},{hip + 3:.1f} L{sx + ww / 2:.1f},{hip + 3:.1f} L{sx + ws / 2:.1f},{ys + rr:.1f} '
             f'Q{sx + ws / 2:.1f},{ys:.1f} {sx + ws / 2 - rr:.1f},{ys:.1f} Z')
    g.append(f'<path d="{torso}" fill="{col}"/><path d="{torso}" fill="url(#shadeX)"/>')
    # arms
    aw = h * .085
    for side in (-1, 1):
        ax = sx + side * (ws / 2 - aw * .25)
        g.append(f'<rect x="{ax - aw / 2:.1f}" y="{ys + 3:.1f}" width="{aw:.1f}" height="{h * .36:.1f}" rx="{aw / 2:.1f}" '
                 f'fill="{dark}" transform="rotate({side * 5} {ax:.1f} {ys:.1f})"/>')
        g.append(f'<circle cx="{ax + side * h * .03:.1f}" cy="{ys + h * .37:.1f}" r="{aw * .45:.1f}" fill="{skin}"/>')
    if facing == "front":
        g.append(f'<polygon points="{pts([(sx - h * .075, ys), (sx + h * .075, ys), (sx, ys + h * .19)])}" fill="#F7F9FB"/>')
        if not female:
            g.append(f'<polygon points="{pts([(sx - 2.4, ys + 3), (sx + 2.4, ys + 3), (sx + 3.2, ys + h * .15), (sx, ys + h * .19), (sx - 3.2, ys + h * .15)])}" fill="{tie}"/>')
        g.append(f'<path d="M{sx - h * .075:.1f},{ys:.1f} L{sx - 1:.1f},{ys + h * .22:.1f} M{sx + h * .075:.1f},{ys:.1f} L{sx + 1:.1f},{ys + h * .22:.1f}" '
                 f'stroke="{dark}" stroke-width="1.6" fill="none"/>')
    else:
        g.append(f'<line x1="{sx:.1f}" y1="{ys + 4:.1f}" x2="{sx:.1f}" y2="{hip:.1f}" stroke="{dark}" stroke-width="1.2" opacity=".6"/>')
    # neck + head
    g.append(f'<rect x="{sx - h * .045:.1f}" y="{ys - h * .06:.1f}" width="{h * .09:.1f}" height="{h * .08:.1f}" fill="{skin}"/>')
    g.append(f'<circle cx="{sx:.1f}" cy="{hy:.1f}" r="{r:.1f}" fill="{skin}"/><circle cx="{sx:.1f}" cy="{hy:.1f}" r="{r:.1f}" fill="url(#shadeHead)"/>')
    if facing == "front":
        g.append(f'<path d="M{sx - r * 1.04:.1f},{hy + r * .05:.1f} A{r * 1.04:.1f},{r * 1.08:.1f} 0 0 1 {sx + r * 1.04:.1f},{hy + r * .05:.1f} '
                 f'Q{sx + r * .45:.1f},{hy - r * .5:.1f} {sx - r * .15:.1f},{hy - r * .38:.1f} Q{sx - r * .7:.1f},{hy - r * .25:.1f} '
                 f'{sx - r * 1.04:.1f},{hy + r * .05:.1f} Z" fill="{hair}"/>')
    else:
        g.append(f'<path d="M{sx - r * 1.05:.1f},{hy + r * .35:.1f} A{r * 1.05:.1f},{r * 1.1:.1f} 0 1 1 {sx + r * 1.05:.1f},{hy + r * .35:.1f} '
                 f'Q{sx:.1f},{hy + r * (1.3 if female else .75):.1f} {sx - r * 1.05:.1f},{hy + r * .35:.1f} Z" fill="{hair}"/>')
    g.append(f'<circle cx="{sx - r * .35:.1f}" cy="{hy - r * .45:.1f}" r="{r * .35:.1f}" fill="#FFFFFF" opacity=".12"/>')
    # props (held in front of the body, front view only)
    hx, hyy = sx + h * .17, ys + h * .30
    if prop == "folder":
        g.append(f'<g transform="rotate(-8 {hx:.1f} {hyy:.1f})"><rect x="{hx - 9:.1f}" y="{hyy - 14:.1f}" width="20" height="16" rx="1.5" fill="#E3C27A"/>'
                 f'<rect x="{hx - 9:.1f}" y="{hyy - 17:.1f}" width="8" height="4" rx="1" fill="#E3C27A"/>'
                 f'<rect x="{hx - 9:.1f}" y="{hyy - 11:.1f}" width="20" height="13" rx="1.5" fill="#F0D595"/></g>')
    elif prop == "tablet":
        g.append(f'<g transform="rotate(-12 {hx:.1f} {hyy:.1f})"><rect x="{hx - 10:.1f}" y="{hyy - 15:.1f}" width="17" height="23" rx="2" fill="#1B2330"/>'
                 f'<rect x="{hx - 8.5:.1f}" y="{hyy - 13.5:.1f}" width="14" height="20" rx="1" fill="url(#scr)"/>'
                 f'<rect x="{hx - 7:.1f}" y="{hyy - 11:.1f}" width="8" height="2" fill="{TEAL_L}"/>'
                 f'<rect x="{hx - 7:.1f}" y="{hyy - 7:.1f}" width="10" height="2" fill="#7FA6C9"/></g>')
    elif prop == "briefcase":
        bx, by = sx + h * .2, sy - h * .3
        g.append(f'<rect x="{bx - 11:.1f}" y="{by - 12:.1f}" width="22" height="16" rx="2.5" fill="#4A2F22"/>'
                 f'<path d="M{bx - 5:.1f},{by - 12:.1f} v-4 h10 v4" fill="none" stroke="#2C1B13" stroke-width="2"/>'
                 f'<rect x="{bx - 11:.1f}" y="{by - 6:.1f}" width="22" height="1.5" fill="#2C1B13"/>')
    elif prop == "document":
        g.append(f'<g transform="rotate(-6 {hx:.1f} {hyy:.1f})"><rect x="{hx - 9:.1f}" y="{hyy - 16:.1f}" width="16" height="21" rx="1" fill="#FFFFFF" stroke="#C9D2DC"/>'
                 + "".join(f'<rect x="{hx - 6:.1f}" y="{hyy - 12 + i * 4:.1f}" width="{10 - (i % 2) * 3}" height="1.6" fill="#8FA3B8"/>' for i in range(4))
                 + '</g>')
    if label:
        lw2 = len(label) * 6.2 + 16
        ly = hy - r - 16
        g.append(f'<g filter="url(#shadow)"><rect x="{sx - lw2 / 2:.1f}" y="{ly - 10:.1f}" width="{lw2:.1f}" height="17" rx="8.5" fill="#FFFFFF" opacity=".95"/></g>'
                 f'<text x="{sx:.1f}" y="{ly + 2.5:.1f}" text-anchor="middle" font-size="10" font-weight="600" fill="{NAVY2}">{label}</text>')
    out.append("<g>" + "".join(g) + "</g>")


def workstation(x, y, z, facing_axis="y", screen=doc_screen):
    """Desk with a monitor. facing_axis 'y' -> screen faces lower-left, 'x' -> lower-right."""
    if facing_axis == "y":
        box(x, y, z, 1.7, .85, .72, "#E9EEF3", "#B8C4D1", "#9AA8B8")
        mz = z + .72
        box(x + .78, y + .2, mz, .14, .12, .22, "#5A6778", "#3F4A58", "#323B47")
        box(x + .25, y + .18, mz + .2, 1.2, .08, .72, "#2A3340", "#1C232D", "#151B23")
        tl, tr, bl = P(x + .3, y + .26, mz + .88), P(x + 1.4, y + .26, mz + .88), P(x + .3, y + .26, mz + .26)
    else:
        box(x, y, z, .85, 1.7, .72, "#E9EEF3", "#B8C4D1", "#9AA8B8")
        mz = z + .72
        box(x + .2, y + .78, mz, .12, .14, .22, "#5A6778", "#3F4A58", "#323B47")
        box(x + .18, y + .25, mz + .2, .08, 1.2, .72, "#2A3340", "#1C232D", "#151B23")
        tl, tr, bl = P(x + .27, y + 1.4, mz + .88), P(x + .27, y + .3, mz + .88), P(x + .27, y + 1.4, mz + .26)
    panel(tl, tr, bl, 200, 110, screen(200, 110))
    out.append(f'<polygon points="{pts([tl, tr, (tr[0] + bl[0] - tl[0], tr[1] + bl[1] - tl[1]), bl])}" fill="{TEAL_L}" opacity=".08" filter="url(#glow)"/>')


def folder_stack(x, y, z, n=3):
    cols = [("#F0D595", "#D2B26B", "#BF9E58"), ("#8DB4DA", "#5F88B1", "#4E7599"), ("#F0D595", "#D2B26B", "#BF9E58")]
    for i in range(n):
        t, l, r = cols[i % 3]
        box(x + (i % 2) * .05, y - (i % 2) * .04, z + i * .09, .75, .55, .08, t, l, r)


def stamp(x, y, z):
    box(x, y, z, .45, .35, .12, "#2C3E50", "#1E2B38", "#16202A")
    cx, cy = P(x + .225, y + .175, z + .12)
    out.append(f'<rect x="{cx - 4:.1f}" y="{cy - 14:.1f}" width="8" height="14" fill="#5B3A29"/>'
               f'<ellipse cx="{cx:.1f}" cy="{cy - 14:.1f}" rx="8" ry="5" fill="#7A4E36"/>'
               f'<ellipse cx="{cx - 2:.1f}" cy="{cy - 15.5:.1f}" rx="3" ry="1.6" fill="#FFFFFF" opacity=".3"/>')
    px, py = P(x - .45, y + .5, z)
    out.append(f'<ellipse cx="{px:.1f}" cy="{py:.1f}" rx="10" ry="5.5" fill="none" stroke="#C0392B" stroke-width="1.6" opacity=".8"/>')


def badge(cx, cy, glyph, label, stem_to=None):
    if stem_to:
        out.append(f'<line x1="{cx:.1f}" y1="{cy + 30:.1f}" x2="{stem_to[0]:.1f}" y2="{stem_to[1]:.1f}" stroke="{TEAL}" '
                   f'stroke-width="1.5" stroke-dasharray="3 4" opacity=".7"/>'
                   f'<circle cx="{stem_to[0]:.1f}" cy="{stem_to[1]:.1f}" r="3" fill="{TEAL}"/>')
    lw2 = len(label) * 6.6 + 18
    out.append(f'<g filter="url(#shadow)"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="31" fill="url(#glass)" stroke="{TEAL}" stroke-width="2"/></g>'
               f'<g transform="translate({cx:.1f} {cy:.1f})">{glyph}</g>'
               f'<rect x="{cx - lw2 / 2:.1f}" y="{cy + 36:.1f}" width="{lw2:.1f}" height="18" rx="9" fill="{NAVY2}"/>'
               f'<text x="{cx:.1f}" y="{cy + 48.5:.1f}" text-anchor="middle" font-size="10.5" font-weight="600" fill="#FFFFFF">{label}</text>')


G_STAMP = (f'<ellipse cx="0" cy="-13" rx="8" ry="4" fill="#7A4E36"/><rect x="-3.5" y="-13" width="7" height="12" fill="#5B3A29"/>'
           f'<path d="M-13,-1 h26 l3,8 h-32 Z" fill="{NAVY2}"/><rect x="-16" y="7" width="32" height="4" rx="1" fill="{NAVY}"/>'
           f'<ellipse cx="0" cy="17" rx="11" ry="3.5" fill="none" stroke="#C0392B" stroke-width="1.6"/>')
G_FOLDERS = ('<path d="M-17,-10 h11 l3,4 h20 v20 h-34 Z" fill="#5F88B1"/><path d="M-14,-6 h11 l3,4 h20 v20 h-34 Z" fill="#D2B26B"/>'
             '<rect x="-14" y="-1" width="34" height="17" rx="1.5" fill="#F0D595"/><rect x="-9" y="4" width="16" height="2" fill="#BF9E58"/>'
             '<rect x="-9" y="8" width="11" height="2" fill="#BF9E58"/>')
G_TITLE = ('<rect x="-15" y="-18" width="24" height="31" rx="2" fill="#FFFFFF" stroke="#8FA3B8" stroke-width="1.4"/>'
           f'<rect x="-11" y="-13" width="16" height="3" fill="{NAVY2}"/>'
           + "".join(f'<rect x="-11" y="{-7 + i * 4}" width="{14 - (i % 2) * 4}" height="1.8" fill="#8FA3B8"/>' for i in range(4))
           + f'<circle cx="7" cy="6" r="8" fill="#DFF7F4" fill-opacity=".6" stroke="{TEAL}" stroke-width="3"/>'
           f'<line x1="12.5" y1="11.5" x2="19" y2="18" stroke="{NAVY2}" stroke-width="4" stroke-linecap="round"/>')
G_LOAN = (f'<path d="M-19,-12 h13 l3,5 h22 v25 h-38 Z" fill="{NAVY2}"/><rect x="-19" y="-4" width="38" height="22" rx="2" fill="#2F5D8C"/>'
          f'<circle cx="0" cy="7" r="8" fill="#F2C14E"/><text x="0" y="11" text-anchor="middle" font-size="12" font-weight="800" fill="{NAVY}">$</text>'
          '<rect x="-15" y="-9" width="9" height="2" fill="#FFFFFF" opacity=".7"/>')


def iso_table(t, w, z, rad, top="#EEF2F6", side="#AEBBC9"):
    cx, cy = TW(t, w, z)
    rx, ry = rad * S * 1.2247, rad * S * .7071
    th = .12 * S
    lx, ly = TW(t, w, z - .7)
    out.append(f'<rect x="{lx - 6:.1f}" y="{cy:.1f}" width="12" height="{ly - cy:.1f}" fill="#7C8A99"/>'
               f'<ellipse cx="{lx:.1f}" cy="{ly:.1f}" rx="{rx * .35:.1f}" ry="{ry * .35:.1f}" fill="#6B7886"/>'
               f'<path d="M{cx - rx:.1f},{cy:.1f} v{th:.1f} A{rx:.1f},{ry:.1f} 0 0 0 {cx + rx:.1f},{cy + th:.1f} v{-th:.1f} Z" fill="{side}"/>'
               f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{top}"/>'
               f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" stroke="{TEAL_L}" stroke-width="1.5" opacity=".6" filter="url(#glow)"/>')


# ---------------------------------------------------------------- flow arrows
def flow_arrow(t0, t1, w0, label, fill_top, fill_side, pill):
    half, z = .75, .16
    head = 1.4 * (1 if t1 > t0 else -1)
    tb = t1 - head
    shape = [(t0, w0 - half), (tb, w0 - half), (tb, w0 - half * 1.8), (t1, w0), (tb, w0 + half * 1.8), (tb, w0 + half), (t0, w0 + half)]
    poly([TW(t, w, 0) for t, w in shape], fill_side, 'filter="url(#shadow)"')
    front = [(t0, w0 + half), (tb, w0 + half), (tb, w0 + half * 1.8), (t1, w0)]
    poly([TW(t, w, 0) for t, w in front] + [TW(t, w, z) for t, w in reversed(front)], fill_side)
    poly([TW(t, w, z) for t, w in shape], fill_top)
    step = 1.6 * (1 if t1 > t0 else -1)
    t = t0 + step
    while (t1 - t) * (1 if t1 > t0 else -1) > 2.6:
        a, b, c = TW(t - step * .25, w0 - .45, z), TW(t + step * .15, w0, z), TW(t - step * .25, w0 + .45, z)
        out.append(f'<polyline points="{pts([a, b, c])}" fill="none" stroke="{TEAL_L}" stroke-width="3" stroke-linecap="round" '
                   f'stroke-linejoin="round" opacity=".85" filter="url(#glow)"/>')
        t += step
    mx, my = TW((t0 + t1) / 2, w0 + .1, z)
    lw2 = len(label) * 9.4 + 58
    arrow_glyph = "→" if t1 > t0 else "←"
    out.append(f'<g filter="url(#shadow)"><rect x="{mx - lw2 / 2:.1f}" y="{my - 17:.1f}" width="{lw2:.1f}" height="34" rx="17" fill="{pill}"/></g>'
               f'<rect x="{mx - lw2 / 2:.1f}" y="{my - 17:.1f}" width="{lw2:.1f}" height="34" rx="17" fill="none" stroke="{TEAL_L}" stroke-width="1.2" opacity=".7"/>'
               f'<text x="{mx:.1f}" y="{my + 5.5:.1f}" text-anchor="middle" font-size="16" font-weight="700" fill="#FFFFFF">'
               f'{arrow_glyph if t1 < t0 else ""} {label} {arrow_glyph if t1 > t0 else ""}</text>')


# ---------------------------------------------------------------- scene
def defs(font_css):
    return f'''<defs>
<style>{font_css} text{{font-family:Inter,'Liberation Sans',Arial,sans-serif}}</style>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E9EEF4"/><stop offset=".55" stop-color="#DCE4ED"/><stop offset="1" stop-color="#C7D2DE"/></linearGradient>
<radialGradient id="spot" cx=".5" cy=".45" r=".6"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".85"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>
<radialGradient id="vign" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#0B1B2E" stop-opacity="0"/><stop offset="1" stop-color="#0B1B2E" stop-opacity=".28"/></radialGradient>
<radialGradient id="hubGlow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{TEAL_L}" stop-opacity=".55"/><stop offset="1" stop-color="{TEAL_L}" stop-opacity="0"/></radialGradient>
<linearGradient id="scr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0B2540"/><stop offset="1" stop-color="#07182B"/></linearGradient>
<linearGradient id="scrMain" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0E3354"/><stop offset=".6" stop-color="#0A2440"/><stop offset="1" stop-color="#061729"/></linearGradient>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#FFFFFF" opacity=".05"/></pattern>
<linearGradient id="holo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#15608A" stop-opacity=".92"/><stop offset="1" stop-color="#0A2A47" stop-opacity=".92"/></linearGradient>
<linearGradient id="shield" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2C6FA8"/><stop offset="1" stop-color="{NAVY}"/></linearGradient>
<linearGradient id="shadeX" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".22"/><stop offset=".45" stop-color="#FFFFFF" stop-opacity="0"/><stop offset="1" stop-color="#000000" stop-opacity=".3"/></linearGradient>
<radialGradient id="shadeHead" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".25"/><stop offset=".6" stop-color="#FFFFFF" stop-opacity="0"/><stop offset="1" stop-color="#000000" stop-opacity=".25"/></radialGradient>
<radialGradient id="glass" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#E3ECF3"/></radialGradient>
<linearGradient id="metal" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#DDE3EA"/><stop offset=".5" stop-color="#F7F9FB"/><stop offset="1" stop-color="#C3CCD6"/></linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="bigGlow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="18"/></filter>
<filter id="blur2"><feGaussianBlur stdDeviation="2"/></filter>
<filter id="dof"><feGaussianBlur stdDeviation="1.6"/></filter>
<filter id="shadow" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#0B1B2E" flood-opacity=".22"/></filter>
<filter id="slabShadow" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="14" stdDeviation="16" flood-color="#0B1B2E" flood-opacity=".28"/></filter>
</defs>'''


def platform(x, y, w, d, h, edge):
    out.append('<g filter="url(#slabShadow)">')
    box(x, y, 0, w, d, h, GRAY_T, GRAY_L, GRAY_R)
    out.append('</g>')
    box(x + .25, y + .25, h, w - .5, d - .5, .02, "#FFFFFF", "#E2E8EF", "#D4DCE5")
    out.append(f'<polyline points="{pts([P(x, y + d, h), P(x + w, y + d, h), P(x + w, y, h)])}" fill="none" stroke="{edge}" '
               f'stroke-width="2.5" filter="url(#glow)" opacity=".85"/>')


def zone_heading(x, y, title, sub, anchor="middle"):
    out.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="24" font-weight="800" fill="{NAVY}" letter-spacing="1.5">{title}</text>'
               f'<text x="{x}" y="{y + 24}" text-anchor="{anchor}" font-size="14" font-weight="600" fill="{TEAL}" letter-spacing=".5">{sub}</text>'
               f'<rect x="{x - 30}" y="{y + 34}" width="60" height="3" rx="1.5" fill="{TEAL}"/>')


def hub():
    # glow under the hub
    gx, gy = P(0, 0, 1.2)
    out.append(f'<ellipse cx="{gx:.1f}" cy="{gy - 60:.1f}" rx="360" ry="220" fill="url(#hubGlow)" opacity=".7"/>')
    out.append('<g filter="url(#slabShadow)">')
    box(-5, -5, 0, 10, 10, .5, "#E6EBF1", NAVY2, NAVY)
    out.append('</g>')
    box(-4.6, -4.6, .5, 9.2, 9.2, .7, "url(#metal)", NAVY3, NAVY2, edge=TEAL_L)
    # branding on the hub faces
    for (ox, oy, ex, ey, text, size) in ((-4.0, 4.6, 1, 0, "VERIROUTE  ·  COMMAND CENTER", .36),
                                          (4.6, 4.0, 0, -1, "CLOSING PLATFORM", .36)):
        o = P(ox, oy, .98)
        a, b = ex * C * S, ex * .5 * S + (-ey) * .5 * S
        a = (ex - ey) * C * S
        b = (ex + ey) * .5 * S
        out.append(f'<text transform="matrix({a:.3f} {b:.3f} 0 {S:.3f} {o[0]:.1f} {o[1]:.1f})" font-size="{size}" '
                   f'font-weight="800" fill="#FFFFFF" fill-opacity=".85" letter-spacing=".08">{text}</text>')
    # curved video wall
    r, z0, z1 = 4.25, 1.75, 5.4
    arcs = [(150, 193, lambda vw, vh: dashboard(vw, vh, 1)), (193, 257, logo_screen), (257, 300, lambda vw, vh: dashboard(vw, vh, 2))]
    for a0, a1, fn in arcs:
        p0 = (r * math.cos(math.radians(a0)), r * math.sin(math.radians(a0)))
        p1 = (r * math.cos(math.radians(a1)), r * math.sin(math.radians(a1)))
        for pp in (p0, p1):
            box(pp[0] - .07, pp[1] - .07, 1.2, .14, .14, z0 - 1.2, "#4A5A6E", "#2B3646", "#222B38")
        tl, tr = P(p0[0], p0[1], z1 + .08), P(p1[0], p1[1], z1 + .08)
        bl, br = P(p0[0], p0[1], z0 - .08), P(p1[0], p1[1], z0 - .08)
        poly([tl, tr, br, bl], "#1A2230")
        tl, tr, bl = P(p0[0], p0[1], z1), P(p1[0], p1[1], z1), P(p0[0], p0[1], z0)
        vw = 460 if fn is logo_screen else 300
        panel(tl, tr, bl, vw, 300, fn(vw, 300))
        br = (tr[0] + bl[0] - tl[0], tr[1] + bl[1] - tl[1])
        out.append(f'<polygon points="{pts([tl, tr, br, bl])}" fill="none" stroke="{TEAL_L}" stroke-width="1.5" opacity=".55" filter="url(#glow)"/>')
    # header light bar
    hp = [P(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), z1 + .3) for a in range(150, 301, 10)]
    out.append(f'<polyline points="{pts(hp)}" fill="none" stroke="{TEAL_L}" stroke-width="3" filter="url(#glow)" opacity=".8"/>')
    tx, ty = P(r * math.cos(math.radians(225)), r * math.sin(math.radians(225)), z1 + .75)
    out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="13" font-weight="800" fill="{NAVY2}" letter-spacing="3">COMMAND CENTER HUB</text>')

    # consoles + staff (staff face the video wall, so we see their backs)
    consoles = [(-1.95, -1.25), (-1.55, -1.55), (-1.25, -1.95)]
    for i, ang in enumerate((195, 225, 255)):
        cx_, cy_ = 2.55 * math.cos(math.radians(ang)), 2.55 * math.sin(math.radians(ang))
        box(cx_ - .55, cy_ - .4, 1.2, 1.1, .8, .62, "#E9EEF3", "#8C9AAB", "#738296")
        box(cx_ - .38, cy_ - .22, 1.82, .76, .1, .38, "#2A3340", "#1C232D", "#151B23")
        glow = P(cx_, cy_ - .17, 2.22)
        out.append(f'<ellipse cx="{glow[0]:.1f}" cy="{glow[1]:.1f}" rx="26" ry="9" fill="{TEAL_L}" opacity=".35" filter="url(#glow)"/>')
    staff = [((-1.55, -.8), "blue", "#C68B63", "#1C1C1C", False),
             ((-1.0, -1.0), "charcoal", "#F1C7A4", "#8B6B4A", True),
             ((-.8, -1.55), "slate", "#8D5A3B", "#1C1C1C", False)]
    for (sx_, sy_), suit, skin, hair, fem in staff:
        person(sx_, sy_, 1.2, suit, skin, hair, facing="back", female=fem, h=86)
    # labels for staff group
    lx, ly = P(-1.0, -1.0, 1.2)
    lx, ly = lx - 118, ly - 52
    out.append(f'<g filter="url(#shadow)"><rect x="{lx - 34:.1f}" y="{ly - 8:.1f}" width="68" height="17" rx="8.5" fill="#FFFFFF"/></g>'
               f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" font-size="10" font-weight="600" fill="{NAVY2}">Staff</text>'
               f'<line x1="{lx + 34:.1f}" y1="{ly:.1f}" x2="{lx + 80:.1f}" y2="{ly + 18:.1f}" stroke="{TEAL}" stroke-width="1.2" stroke-dasharray="3 3"/>')

    # System admin on a raised dais with a holographic admin interface
    box(-4.1, 1.3, 1.2, 1.5, 1.5, .35, "#F7F9FB", NAVY3, NAVY2, edge=TEAL_L)
    ax, ay = P(-3.35, 2.05, 1.55)
    panel((ax - 150, ay - 140), (ax - 40, ay - 140), (ax - 150, ay - 60), 110, 80, admin_screen(110, 80))
    out.append(f'<line x1="{ax - 40:.1f}" y1="{ay - 100:.1f}" x2="{ax - 14:.1f}" y2="{ay - 55:.1f}" stroke="{TEAL_L}" stroke-width="1.2" stroke-dasharray="3 3"/>')
    person(-3.35, 2.05, 1.55, "navy", "#E0AC84", "#2B1D14", tie="#F2C14E", prop="tablet", label="System Admin", h=92)

    # Manager overseeing the floor
    person(1.9, 2.4, 1.2, "charcoal", "#F5D3B8", "#B9A38A", tie="#2F5D8C", prop="tablet", label="Manager", h=98)
    person(3.0, 1.0, 1.2, "teal", "#8D5A3B", "#1C1C1C", female=True, prop="document", label="Staff", h=90)


def vendor_side():
    platform(-12.75, 6.25, 6.5, 6.5, .45, TEAL_L)
    z = .45
    workstation(-12.2, 7.0, z, "y", doc_screen)
    folder_stack(-11.1, 7.05, z + .74, 3)
    workstation(-9.4, 6.7, z, "y", lambda vw, vh: dashboard(vw, vh, 1))
    stamp(-8.3, 6.95, z + .74)
    person(-11.3, 8.6, z, "slate", "#C68B63", "#2B1D14", facing="back", label="Paralegal")
    person(-8.0, 8.4, z, "beige", "#F1C7A4", "#8B6B4A", female=True, prop="folder", label="Paralegal")
    person(-11.45, 12.05, z, "navy", "#E0AC84", "#1C1C1C", prop="folder", label="Notary")
    person(-7.85, 11.65, z, "blue", "#8D5A3B", "#1C1C1C", female=True, prop="document", label="Notary")


def customer_side():
    platform(6.25, -12.75, 6.5, 6.5, .45, TEAL_L)
    z = .45
    workstation(10.9, -12.2, z, "x", lambda vw, vh: dashboard(vw, vh, 0))
    person(6.75, -11.05, z, "gray", "#F5D3B8", "#4A3222", label="Title Company")
    iso_table(17.5, -2.4, z + .75, 1.25)
    folder_stack(7.15, -10.35, z + .75, 2)
    tx, ty = TW(18.3, -2.0, z + .76)
    out.append(f'<g transform="translate({tx:.1f} {ty:.1f})"><polygon points="0,0 22,-9 34,-2 12,7" fill="#FFFFFF" stroke="#C9D2DC"/>'
               f'<polygon points="4,-1 18,-7 21,-5 7,1" fill="#8FA3B8"/></g>')
    person(12.1, -11.0, z, "blue", "#E0AC84", "#2B1D14", facing="back", label="Lender")
    person(7.5, -7.0, z, "navy", "#E6B08A", "#2B1D14", prop="tablet", label="Lender")
    person(10.6, -7.4, z, "teal", "#F1C7A4", "#4A3222", female=True, prop="document", label="Title / Insurance")
    person(12.1, -9.7, z, "charcoal", "#C68B63", "#1C1C1C", tie="#A33A3A", prop="briefcase", label="Attorney")


def build(font_css):
    out.clear()
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    out.append(defs(font_css))
    out.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    out.append(f'<ellipse cx="{W / 2}" cy="{H * .5:.0f}" rx="{W * .55:.0f}" ry="{H * .55:.0f}" fill="url(#spot)"/>')
    # soft floor grid (defocused)
    grid = []
    for i in range(-22, 23, 2):
        grid.append(f'<line x1="{P(i, -22)[0]:.1f}" y1="{P(i, -22)[1]:.1f}" x2="{P(i, 22)[0]:.1f}" y2="{P(i, 22)[1]:.1f}"/>')
        grid.append(f'<line x1="{P(-22, i)[0]:.1f}" y1="{P(-22, i)[1]:.1f}" x2="{P(22, i)[0]:.1f}" y2="{P(22, i)[1]:.1f}"/>')
    out.append(f'<g stroke="#8FA3B8" stroke-width="1" opacity=".22" filter="url(#dof)">{"".join(grid)}</g>')

    # title
    out.append(f'<g transform="translate(60 70)">{logo_mark(26)}</g>'
               f'<text x="100" y="66" font-size="30" font-weight="800" fill="{NAVY}">Veri<tspan fill="{TEAL}">Route</tspan>'
               f'<tspan font-weight="400" fill="#4A5A6E"> — Closing Platform</tspan></text>'
               f'<text x="100" y="92" font-size="15" font-weight="600" fill="#5B6B7E" letter-spacing="2">MARKETPLACE PROCESS MAP</text>')

    # soft data links between the sides and the hub
    for a, b in ((P(-7.2, 7.2, 2.8), P(-3.6, 0.2, 5.6)), (P(7.2, -7.2, 2.8), P(0.2, -3.6, 5.6))):
        mx, my = (a[0] + b[0]) / 2, min(a[1], b[1]) - 80
        out.append(f'<path d="M{a[0]:.1f},{a[1]:.1f} Q{mx:.1f},{my:.1f} {b[0]:.1f},{b[1]:.1f}" fill="none" stroke="{TEAL}" '
                   f'stroke-width="2" stroke-dasharray="2 7" stroke-linecap="round" opacity=".6"/>')

    vendor_side()
    customer_side()
    hub()

    # floating icon badges
    badge(*P(-12.3, 7.4, 4.9), G_FOLDERS, "Document Folders", stem_to=P(-10.7, 7.3, 1.5))
    badge(*P(-9.5, 6.1, 5.3), G_STAMP, "Notarization", stem_to=P(-8.1, 7.1, 1.6))
    badge(*P(8.0, -12.4, 5.3), G_TITLE, "Title Search")
    badge(1800, 372, G_LOAN, "Loan Package", stem_to=TW(17.9, -2.6, 1.3))

    zone_heading(300, 190, "VENDOR / SERVICE PROVIDERS", "Notaries  ·  Paralegals")
    zone_heading(1620, 190, "CUSTOMER SIDE", "Lenders  ·  Title &amp; Insurance  ·  Attorneys")

    # bottom flows
    flow_arrow(20.0, 4.2, 11.6, "Work Assignment", "#2C4F7C", NAVY, NAVY2)
    flow_arrow(-21.5, 21.5, 15.0, "Deliver Work &amp; Payment Bill", "#1C8A86", "#136460", "#136460")

    out.append(f'<rect width="{W}" height="{H}" fill="url(#vign)" pointer-events="none"/>')
    out.append("</svg>")
    return "\n".join(out)


def font_css_from(dirpath):
    css = ""
    for weight in (400, 600, 800):
        f = os.path.join(dirpath, f"inter-{weight}.woff2")
        if os.path.exists(f):
            data = base64.b64encode(open(f, "rb").read()).decode()
            css += f"@font-face{{font-family:Inter;font-weight:{weight};src:url(data:font/woff2;base64,{data}) format('woff2')}}"
    for weight in (700,):
        f = os.path.join(dirpath, "inter-600.woff2")
        if os.path.exists(f):
            data = base64.b64encode(open(f, "rb").read()).decode()
            css += f"@font-face{{font-family:Inter;font-weight:{weight};src:url(data:font/woff2;base64,{data}) format('woff2')}}"
    return css


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    fonts = sys.argv[sys.argv.index("--fonts") + 1] if "--fonts" in sys.argv else ""
    svg = build(font_css_from(fonts) if fonts else "")
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"Wrote {sys.argv[1]} ({len(svg) // 1024} KB)")
