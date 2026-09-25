#!/usr/bin/env python3
"""Convert the Mermaid `erDiagram` in a Markdown file into a native Visio (.vsdx) ERD.

Each entity becomes a grouped table shape (coloured header + attribute list) and each
relationship becomes a dynamic connector glued to both entities, so the diagram stays
editable in Visio (move shapes, Design > Re-Layout Page, etc.). Attribute comments
from the Mermaid source (enum values, notes) are stored as Shape Data on the entity.

Layout is computed with Graphviz `dot` (must be on PATH). Only the Python stdlib is used.

Usage:
    python3 tools/mermaid_erd_to_vsdx.py docs/veriroute-erd.md docs/veriroute-erd.vsdx
"""
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

# ---------------------------------------------------------------- configuration
TITLE = "VeriRoute Field Services – Logical ERD"
SUBTITLE = ("Reverse-engineered from the Dashboard and Orders screens (test environment). "
            "Network, Pitches and Payments are modelled assumptions. "
            "Connector label: relationship (cardinality at start → cardinality at end).")

DOMAINS = {
    "Identity & Professional": ("#1F3864", ["USER_ACCOUNT", "COMPANY", "PROFESSIONAL", "SERVICE_AREA",
                                            "CREDENTIAL", "CREDENTIAL_TYPE", "AVAILABILITY"]),
    "Network & Pitches": ("#1B6F6A", ["NETWORK_CONNECTION", "NETWORK_GROUP", "NETWORK_GROUP_MEMBER", "PITCH"]),
    "Orders & Assignment": ("#9C6B12", ["ORDER", "ORDER_SIGNER", "ASSIGNMENT_OFFER", "ASSIGNMENT",
                                        "ORDER_STATUS_HISTORY", "PERFORMANCE_REVIEW"]),
    "Fulfilment": ("#6A4C93", ["APPOINTMENT", "DOCUMENT", "SCANBACK", "SHIPMENT"]),
    "Payments": ("#2E7D32", ["FEE_LINE", "INVOICE", "PAYMENT", "PAYOUT_METHOD", "TAX_PROFILE"]),
    "Membership & Compliance": ("#A33A3A", ["MEMBERSHIP_PLAN", "PLAN_FEATURE", "SUBSCRIPTION", "AGREEMENT",
                                            "AGREEMENT_VERSION", "AGREEMENT_ACCEPTANCE"]),
    "Communication": ("#4A5A6A", ["MESSAGE_THREAD", "MESSAGE", "THREAD_PARTICIPANT", "NOTIFICATION"]),
}
DEFAULT_COLOR = "#555555"

FONT_PT = 8.0
CHAR_W = FONT_PT * 0.6 / 72          # Consolas advance width, inches
LINE_H = FONT_PT * 1.35 / 72         # line height, inches (slack for font substitution)
HEADER_H = 0.30
PAD_X, PAD_Y = 0.10, 0.06
MARGIN = 0.75
TITLE_H = 1.0

LEFT_CARD = {"||": "1", "|o": "0..1", "}o": "0..*", "}|": "1..*"}
RIGHT_CARD = {"||": "1", "o|": "0..1", "o{": "0..*", "|{": "1..*"}

NS = 'xmlns="http://schemas.microsoft.com/office/visio/2012/main" ' \
     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


# ---------------------------------------------------------------- parse Mermaid
def parse_mermaid(md_text):
    m = re.search(r"```mermaid\s*\n\s*erDiagram\s*\n(.*?)```", md_text, re.S)
    if not m:
        sys.exit("No Mermaid erDiagram block found")
    body = m.group(1)
    rel_re = re.compile(r'^\s*(\w+)\s+([|}o]{2})--([|{o]{2})\s+(\w+)\s*:\s*"([^"]*)"')
    attr_re = re.compile(r'^\s*(\w+)\s+(\w+)\s*((?:PK|FK|UK)(?:\s*,\s*(?:PK|FK|UK))*)?\s*(?:"([^"]*)")?\s*$')
    entities, rels, current = {}, [], None
    for line in body.splitlines():
        if current:
            if line.strip() == "}":
                current = None
                continue
            a = attr_re.match(line)
            if a:
                keys = (a.group(3) or "").replace(" ", "")
                entities[current].append({"type": a.group(1), "name": a.group(2),
                                          "keys": keys, "comment": a.group(4) or ""})
            continue
        b = re.match(r"^\s*(\w+)\s*\{\s*$", line)
        if b:
            current = b.group(1)
            entities[current] = []
            continue
        r = rel_re.match(line)
        if r:
            rels.append({"a": r.group(1), "b": r.group(4), "label": r.group(5),
                         "ca": LEFT_CARD[r.group(2)], "cb": RIGHT_CARD[r.group(3)]})
    for r in rels:  # entities referenced only in relationships
        entities.setdefault(r["a"], [])
        entities.setdefault(r["b"], [])
    return entities, rels


def domain_of(name):
    for dom, (color, members) in DOMAINS.items():
        if name in members:
            return dom, color
    return "Other", DEFAULT_COLOR


def attr_lines(attrs):
    name_w = max([len(a["name"]) for a in attrs] + [4])
    return [f'{a["keys"]:<5} {a["name"]:<{name_w}}  {a["type"]}' for a in attrs]


def entity_size(name, attrs):
    lines = attr_lines(attrs)
    chars = max([len(l) + 2 for l in lines] + [len(name) * 1.45 + 2])
    w = max(1.6, chars * CHAR_W + 2 * PAD_X)
    h = HEADER_H + max(1, len(lines)) * LINE_H + 2 * PAD_Y
    return round(w, 3), round(h, 3)


# ---------------------------------------------------------------- layout (Graphviz)
def layout(entities, rels, sizes):
    out = ['digraph ERD {', 'graph [rankdir=LR, splines=ortho, nodesep=0.5, ranksep=1.1, newrank=true];',
           'node [shape=box, fixedsize=true, label=""];', 'edge [arrowhead=none];']
    by_dom = {}
    for n in entities:
        by_dom.setdefault(domain_of(n)[0], []).append(n)
    for i, (dom, names) in enumerate(by_dom.items()):
        out.append(f'subgraph cluster_{i} {{ label="{dom}"; margin=18;')
        for n in names:
            w, h = sizes[n]
            out.append(f'  "{n}" [width={w}, height={h}];')
        out.append('}')
    for r in rels:
        out.append(f'"{r["a"]}" -> "{r["b"]}";')
    out.append('}')
    res = subprocess.run(["dot", "-Tjson"], input="\n".join(out), capture_output=True, text=True, check=True)
    g = json.loads(res.stdout)

    llx, lly, urx, ury = (float(v) / 72 for v in g["bb"].split(","))
    ox, oy = MARGIN - llx, MARGIN - lly
    page_w = (urx - llx) + 2 * MARGIN
    page_h = (ury - lly) + 2 * MARGIN + TITLE_H

    nodes, clusters, gvid_name = {}, [], {}
    for o in g.get("objects", []):
        if "bb" in o and o.get("name", "").startswith("cluster"):
            x1, y1, x2, y2 = (float(v) / 72 for v in o["bb"].split(","))
            clusters.append({"label": o.get("label", ""), "x1": x1 + ox, "y1": y1 + oy, "x2": x2 + ox, "y2": y2 + oy})
        elif "pos" in o:
            x, y = (float(v) / 72 for v in o["pos"].split(","))
            nodes[o["name"]] = (x + ox, y + oy)
            gvid_name[o["_gvid"]] = o["name"]

    # dot does not return edges in input order, so match them back by (tail, head)
    by_pair = {}
    for e in g.get("edges", []):
        pts = []
        for tok in e["pos"].split():
            parts = tok.split(",")
            if parts[0] in ("s", "e"):
                parts = parts[1:]
            pts.append((float(parts[0]) / 72 + ox, float(parts[1]) / 72 + oy))
        by_pair.setdefault((gvid_name[e["tail"]], gvid_name[e["head"]]), []).append(simplify(pts))
    paths = [by_pair[(r["a"], r["b"])].pop(0) for r in rels]
    return page_w, page_h, nodes, clusters, paths


def simplify(pts):
    dedup = []
    for p in pts:
        if not dedup or abs(p[0] - dedup[-1][0]) > 1e-4 or abs(p[1] - dedup[-1][1]) > 1e-4:
            dedup.append(p)
    out = []
    for p in dedup:
        if len(out) >= 2:
            (x1, y1), (x2, y2) = out[-2], out[-1]
            if abs((x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1)) < 1e-4:
                out[-1] = p
                continue
        out.append(p)
    return out


# ---------------------------------------------------------------- XML helpers
def cell(n, v, u=None, f=None):
    s = f'<Cell N="{n}" V="{v}"'
    if u:
        s += f' U="{u}"'
    if f:
        s += f' F="{escape(f, {chr(34): "&quot;"})}"'
    return s + "/>"


def rect_geometry():
    rows = [("RelMoveTo", 0, 0), ("RelLineTo", 1, 0), ("RelLineTo", 1, 1), ("RelLineTo", 0, 1), ("RelLineTo", 0, 0)]
    xml = '<Section N="Geometry" IX="0">' + cell("NoFill", 0) + cell("NoLine", 0) + cell("NoShow", 0) + cell("NoSnap", 0)
    for i, (t, x, y) in enumerate(rows, 1):
        xml += f'<Row T="{t}" IX="{i}">{cell("X", x)}{cell("Y", y)}</Row>'
    return xml + "</Section>"


def char_section(size_pt, color, bold=False, font="Calibri"):
    return ('<Section N="Character"><Row IX="0">' + cell("Font", font) + cell("Color", color) +
            cell("Style", 1 if bold else 0) + cell("Size", round(size_pt / 72, 6), "PT") + "</Row></Section>")


def para_section(align):
    return f'<Section N="Paragraph"><Row IX="0">{cell("HorzAlign", align)}{cell("SpLine", -1.2)}</Row></Section>'


def xform(pinx, piny, w, h):
    return (cell("PinX", round(pinx, 4), "IN") + cell("PinY", round(piny, 4), "IN") +
            cell("Width", round(w, 4), "IN") + cell("Height", round(h, 4), "IN") +
            cell("LocPinX", round(w / 2, 4), "IN", "Width*0.5") + cell("LocPinY", round(h / 2, 4), "IN", "Height*0.5") +
            cell("Angle", 0) + cell("FlipX", 0) + cell("FlipY", 0) + cell("ResizeMode", 0))


def text_margins(l=0.05, t=0.03):
    return (cell("LeftMargin", l, "IN") + cell("RightMargin", l, "IN") +
            cell("TopMargin", t, "IN") + cell("BottomMargin", t, "IN"))


def safe_row_name(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


# ---------------------------------------------------------------- build shapes
def build_page(entities, rels, sizes, page_w, page_h, nodes, clusters, paths):
    shapes, connects = [], []
    next_id = [1]

    def nid():
        v = next_id[0]
        next_id[0] += 1
        return v

    # Title block
    for name, text, size, color, bold, y, h in (
            ("Title", TITLE, 22, "#1F3864", True, page_h - 0.45, 0.45),
            ("Subtitle", SUBTITLE, 10, "#555555", False, page_h - 0.85, 0.3)):
        sid = nid()
        shapes.append(
            f'<Shape ID="{sid}" NameU="{name}" Name="{name}" Type="Shape" LineStyle="0" FillStyle="0" TextStyle="0">'
            + xform(MARGIN + 8, y, 16, h)
            + cell("LinePattern", 0) + cell("FillPattern", 0) + cell("VerticalAlign", 1) + text_margins(0, 0)
            + char_section(size, color, bold=bold) + para_section(0) + rect_geometry()
            + f"<Text>{escape(text)}</Text></Shape>")

    # Domain containers (drawn first so they sit behind entities)
    for c in clusters:
        dom = c["label"]
        color = DOMAINS.get(dom, (DEFAULT_COLOR,))[0]
        sid = nid()
        w, h = c["x2"] - c["x1"], c["y2"] - c["y1"]
        shapes.append(
            f'<Shape ID="{sid}" NameU="Domain.{sid}" Name="Domain: {escape(dom)}" Type="Shape" '
            f'LineStyle="0" FillStyle="0" TextStyle="0">'
            + xform(c["x1"] + w / 2, c["y1"] + h / 2, w, h)
            + cell("FillForegnd", "#F4F6F9") + cell("FillPattern", 1) + cell("LineColor", color)
            + cell("LineWeight", round(1 / 72, 6), "PT") + cell("LinePattern", 2) + cell("Rounding", 0.08, "IN")
            + cell("VerticalAlign", 0) + text_margins(0.1, 0.05)
            + char_section(11, color, bold=True) + para_section(0) + rect_geometry()
            + f"<Text>{escape(dom)}</Text></Shape>")

    # Entities as groups: header + attribute body
    ent_ids = {}
    for name, attrs in entities.items():
        dom, color = domain_of(name)
        w, h = sizes[name]
        cx, cy = nodes[name]
        gid, hid, bid = nid(), nid(), nid()
        ent_ids[name] = gid
        body_h = h - HEADER_H
        lines = attr_lines(attrs) or ["(no attributes)"]

        props = ('<Section N="Property">'
                 f'<Row N="Entity">{cell("Label", "Entity")}{cell("Value", escape(name), "STR")}{cell("Type", 0)}</Row>'
                 f'<Row N="Domain">{cell("Label", "Domain")}{cell("Value", escape(dom), "STR")}{cell("Type", 0)}</Row>')
        for a in attrs:
            if a["comment"]:
                props += (f'<Row N="{safe_row_name("a_" + a["name"])}">{cell("Label", escape(a["name"]))}'
                          f'{cell("Value", escape(a["comment"]), "STR")}{cell("Type", 0)}</Row>')
        props += "</Section>"

        header = (f'<Shape ID="{hid}" NameU="Header.{hid}" Name="{name} header" Type="Shape" '
                  f'LineStyle="0" FillStyle="0" TextStyle="0">'
                  + xform(w / 2, h - HEADER_H / 2, w, HEADER_H)
                  + cell("FillForegnd", color) + cell("FillPattern", 1) + cell("LineColor", color)
                  + cell("LineWeight", round(0.75 / 72, 6), "PT") + cell("VerticalAlign", 1) + text_margins()
                  + char_section(10, "#FFFFFF", bold=True) + para_section(1) + rect_geometry()
                  + f"<Text>{escape(name)}</Text></Shape>")
        body = (f'<Shape ID="{bid}" NameU="Body.{bid}" Name="{name} attributes" Type="Shape" '
                f'LineStyle="0" FillStyle="0" TextStyle="0">'
                + xform(w / 2, body_h / 2, w, body_h)
                + cell("FillForegnd", "#FFFFFF") + cell("FillPattern", 1) + cell("LineColor", color)
                + cell("LineWeight", round(0.75 / 72, 6), "PT") + cell("VerticalAlign", 0) + text_margins(PAD_X, PAD_Y)
                + char_section(FONT_PT, "#222222", font="Consolas") + para_section(0) + rect_geometry()
                + f"<Text>{escape(chr(10).join(lines))}</Text></Shape>")
        shapes.append(
            f'<Shape ID="{gid}" NameU="{name}" Name="{name}" Type="Group" LineStyle="0" FillStyle="0" TextStyle="0">'
            + xform(cx, cy, w, h) + cell("SelectMode", 0) + cell("DisplayMode", 2)
            + props + f"<Shapes>{header}{body}</Shapes></Shape>")

    # Relationships as glued dynamic connectors
    for r, pts in zip(rels, paths):
        cid = nid()
        (bx, by), (ex, ey) = pts[0], pts[-1]
        w, h = ex - bx, ey - by
        local = [(x - bx, y - by) for x, y in pts]
        # label on the midpoint of the longest segment
        segs = list(zip(local, local[1:]))
        (sx1, sy1), (sx2, sy2) = max(segs, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
        tx, ty = (sx1 + sx2) / 2, (sy1 + sy2) / 2
        label = f'{r["label"]}\n({r["ca"]} → {r["cb"]})'
        tw = max(len(r["label"]), 12) * 0.075 + 0.15
        geo = '<Section N="Geometry" IX="0">' + cell("NoFill", 1) + cell("NoLine", 0) + cell("NoShow", 0) + cell("NoSnap", 0)
        for i, (x, y) in enumerate(local, 1):
            geo += f'<Row T="{"MoveTo" if i == 1 else "LineTo"}" IX="{i}">{cell("X", round(x, 4), "IN")}{cell("Y", round(y, 4), "IN")}</Row>'
        geo += "</Section>"
        a_id, b_id = ent_ids[r["a"]], ent_ids[r["b"]]
        shapes.append(
            f'<Shape ID="{cid}" NameU="Dynamic connector.{cid}" Name="{r["a"]} {escape(r["label"])} {r["b"]}" '
            f'Type="Shape" LineStyle="0" FillStyle="0" TextStyle="0">'
            + cell("PinX", round(bx + w / 2, 4), "IN") + cell("PinY", round(by + h / 2, 4), "IN")
            + cell("Width", round(w, 4), "IN") + cell("Height", round(h, 4), "IN")
            + cell("LocPinX", round(w / 2, 4), "IN", "Width*0.5") + cell("LocPinY", round(h / 2, 4), "IN", "Height*0.5")
            + cell("Angle", 0) + cell("FlipX", 0) + cell("FlipY", 0) + cell("ResizeMode", 0)
            + cell("BeginX", round(bx, 4), "IN", "_WALKGLUE(BegTrigger,EndTrigger,WalkPreference)")
            + cell("BeginY", round(by, 4), "IN", "_WALKGLUE(BegTrigger,EndTrigger,WalkPreference)")
            + cell("EndX", round(ex, 4), "IN", "_WALKGLUE(EndTrigger,BegTrigger,WalkPreference)")
            + cell("EndY", round(ey, 4), "IN", "_WALKGLUE(EndTrigger,BegTrigger,WalkPreference)")
            + cell("BegTrigger", 2, None, f"_XFTRIGGER(Sheet.{a_id}!EventXFMod)")
            + cell("EndTrigger", 2, None, f"_XFTRIGGER(Sheet.{b_id}!EventXFMod)")
            + cell("ObjType", 2) + cell("ShapeRouteStyle", 1) + cell("ConLineRouteExt", 1)
            + cell("LineColor", "#5B6573") + cell("LineWeight", round(1 / 72, 6), "PT")
            + cell("EndArrow", 4) + cell("EndArrowSize", 1)
            + cell("TxtPinX", round(tx, 4), "IN") + cell("TxtPinY", round(ty, 4), "IN")
            + cell("TxtWidth", round(tw, 4), "IN") + cell("TxtHeight", 0.3, "IN")
            + cell("TxtLocPinX", round(tw / 2, 4), "IN", "TxtWidth*0.5") + cell("TxtLocPinY", 0.15, "IN", "TxtHeight*0.5")
            + cell("TxtAngle", 0) + cell("TextBkgnd", "#FFFFFF") + cell("TextBkgndTrans", 0) + text_margins(0.02, 0.01)
            + char_section(7, "#333333") + para_section(1) + geo
            + f"<Text>{escape(label)}</Text></Shape>")
        connects.append(f'<Connect FromSheet="{cid}" FromCell="BeginX" FromPart="9" ToSheet="{a_id}" ToCell="PinX" ToPart="3"/>')
        connects.append(f'<Connect FromSheet="{cid}" FromCell="EndX" FromPart="12" ToSheet="{b_id}" ToCell="PinX" ToPart="3"/>')

    return (f'<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n<PageContents {NS} xml:space="preserve">'
            f'<Shapes>{"".join(shapes)}</Shapes><Connects>{"".join(connects)}</Connects></PageContents>')


# ---------------------------------------------------------------- package parts
def stylesheet():
    cells = [cell("EnableLineProps", 1), cell("EnableFillProps", 1), cell("EnableTextProps", 1), cell("HideForApply", 0),
             cell("LineWeight", 0.01041666666666667, "PT"), cell("LineColor", 0), cell("LinePattern", 1),
             cell("Rounding", 0), cell("EndArrowSize", 2), cell("BeginArrow", 0), cell("EndArrow", 0), cell("LineCap", 0),
             cell("BeginArrowSize", 2), cell("LineColorTrans", 0), cell("CompoundType", 0),
             cell("FillForegnd", 1), cell("FillBkgnd", 0), cell("FillPattern", 1), cell("ShdwForegnd", 0),
             cell("ShdwPattern", 0), cell("FillForegndTrans", 0), cell("FillBkgndTrans", 0), cell("ShdwForegndTrans", 0),
             cell("ShapeShdwType", 0), cell("ShapeShdwOffsetX", 0), cell("ShapeShdwOffsetY", 0),
             cell("LeftMargin", 0), cell("RightMargin", 0), cell("TopMargin", 0), cell("BottomMargin", 0),
             cell("VerticalAlign", 1), cell("TextBkgnd", 0), cell("DefaultTabStop", 0.5), cell("TextDirection", 0),
             cell("TextBkgndTrans", 0), cell("LockTextEdit", 0), cell("LockVtxEdit", 0), cell("NoAlignBox", 0),
             cell("ShapePlowCode", 0), cell("ShapeRouteStyle", 0), cell("ConFixedCode", 0), cell("ConLineJumpCode", 0),
             cell("ConLineJumpStyle", 0), cell("ConLineJumpDirX", 0), cell("ConLineJumpDirY", 0),
             cell("ShapeSplittable", 0), cell("ShapeSplit", 0)]
    char = ('<Section N="Character"><Row IX="0">' + cell("Font", "Calibri") + cell("Color", 0) + cell("Style", 0)
            + cell("Case", 0) + cell("Pos", 0) + cell("FontScale", 1) + cell("Size", 0.1666666666666667, "PT")
            + cell("DblUnderline", 0) + cell("Overline", 0) + cell("Strikethru", 0) + cell("Letterspace", 0)
            + cell("ColorTrans", 0) + "</Row></Section>")
    para = ('<Section N="Paragraph"><Row IX="0">' + cell("IndFirst", 0) + cell("IndLeft", 0) + cell("IndRight", 0)
            + cell("SpLine", -1.2) + cell("SpBefore", 0) + cell("SpAfter", 0) + cell("HorzAlign", 1) + cell("Bullet", 0)
            + "</Row></Section>")
    return (f'<StyleSheet ID="0" NameU="No Style" Name="No Style">{"".join(cells)}{char}{para}</StyleSheet>')


def build_vsdx(out_path, page_xml, page_w, page_h):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    files = {
        "[Content_Types].xml":
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>'
            '<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>'
            '<Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>'
            '<Override PartName="/visio/windows.xml" ContentType="application/vnd.ms-visio.windows+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>',
        "_rels/.rels":
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>',
        "docProps/core.xml":
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(TITLE)}</dc:title><dc:creator>mermaid_erd_to_vsdx.py</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>',
        "docProps/app.xml":
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            '<Application>Microsoft Visio</Application><Template></Template></Properties>',
        "visio/_rels/document.xml.rels":
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.microsoft.com/visio/2010/relationships/windows" Target="windows.xml"/>'
            '</Relationships>',
        "visio/document.xml":
            f'<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n<VisioDocument {NS} xml:space="preserve">'
            '<DocumentSettings TopPage="0" DefaultTextStyle="0" DefaultLineStyle="0" DefaultFillStyle="0" DefaultGuideStyle="0">'
            + cell("GlueSettings", 9) + cell("SnapSettings", 295) + cell("SnapExtensions", 34) + cell("DynamicGridEnabled", 0)
            + cell("ProtectStyles", 0) + cell("ProtectShapes", 0) + cell("ProtectMasters", 0) + cell("ProtectBkgnds", 0)
            + '</DocumentSettings>'
            '<Colors><ColorEntry IX="0" RGB="#000000"/><ColorEntry IX="1" RGB="#FFFFFF"/></Colors>'
            '<FaceNames><FaceName NameU="Calibri"/><FaceName NameU="Consolas"/></FaceNames>'
            f'<StyleSheets>{stylesheet()}</StyleSheets></VisioDocument>',
        "visio/windows.xml":
            f'<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n<Windows {NS} ClientWidth="1600" ClientHeight="900">'
            '<Window ID="0" WindowType="Drawing" WindowState="1073741824" ClientWidth="1600" ClientHeight="900" '
            'Page="0" ViewScale="-1" ViewCenterX="0" ViewCenterY="0"><ShowRulers>1</ShowRulers><ShowGrid>0</ShowGrid>'
            '<ShowPageBreaks>0</ShowPageBreaks><ShowGuides>1</ShowGuides><ShowConnectionPoints>1</ShowConnectionPoints>'
            '<GlueSettings>9</GlueSettings><SnapSettings>295</SnapSettings><SnapExtensions>34</SnapExtensions>'
            '<DynamicGridEnabled>0</DynamicGridEnabled><TabSplitterPos>0.5</TabSplitterPos></Window></Windows>',
        "visio/pages/_rels/pages.xml.rels":
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page1.xml"/>'
            '</Relationships>',
        "visio/pages/pages.xml":
            f'<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n<Pages {NS} xml:space="preserve">'
            '<Page ID="0" NameU="ERD" Name="ERD" ViewScale="-1" ViewCenterX="0" ViewCenterY="0">'
            '<PageSheet LineStyle="0" FillStyle="0" TextStyle="0">'
            + cell("PageWidth", round(page_w, 3), "IN") + cell("PageHeight", round(page_h, 3), "IN")
            + cell("ShdwOffsetX", 0.125, "IN") + cell("ShdwOffsetY", -0.125, "IN")
            + cell("PageScale", 1, "IN") + cell("DrawingScale", 1, "IN") + cell("DrawingSizeType", 0)
            + cell("DrawingScaleType", 0) + cell("InhibitSnap", 0) + cell("UIVisibility", 0)
            + cell("ShdwType", 0) + cell("ShdwObliqueAngle", 0) + cell("ShdwScaleFactor", 1)
            + cell("DrawingResizeType", 1) + cell("PageShapeSplit", 1)
            + cell("RouteStyle", 1) + cell("LineJumpCode", 0) + cell("PageLineJumpDirX", 0) + cell("PageLineJumpDirY", 0)
            + cell("PrintPageOrientation", 2)
            + '</PageSheet><Rel r:id="rId1"/></Page></Pages>',
        "visio/pages/page1.xml": page_xml,
    }
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ["[Content_Types].xml"] + [n for n in files if n != "[Content_Types].xml"]:
            z.writestr(name, files[name])


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as fh:
        entities, rels = parse_mermaid(fh.read())
    sizes = {n: entity_size(n, a) for n, a in entities.items()}
    page_w, page_h, nodes, clusters, paths = layout(entities, rels, sizes)
    page_xml = build_page(entities, rels, sizes, page_w, page_h, nodes, clusters, paths)
    build_vsdx(dst, page_xml, page_w, page_h)
    print(f"Wrote {dst}: {len(entities)} entities, {len(rels)} relationships, page {page_w:.1f} x {page_h:.1f} in")


if __name__ == "__main__":
    main()
