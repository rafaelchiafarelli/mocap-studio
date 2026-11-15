from xml.sax.saxutils import quoteattr
import sys
out = sys.argv[1]
cells, ids = [], [0]
def nid():
    ids[0] += 1
    return f"c{ids[0]}"
def vertex(x, y, w, h, value, style):
    i = nid()
    cells.append(f'<mxCell id="{i}" value={quoteattr(value)} style="{style}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    return i
def edge(a, b, style="endArrow=block;html=1;strokeWidth=1.5;", label=""):
    i = nid()
    cells.append(f'<mxCell id="{i}" value={quoteattr(label)} style="{style}" edge="1" parent="1" source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"/></mxCell>')

DATA = "shape=document;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#dae8fc;strokeColor=#6c8ebf;align=left;spacingLeft=8;fontSize=11;size=0.12;"
PROC = "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;align=left;spacingLeft=8;fontSize=11;arcSize=8;"
NOTE = "shape=note;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;align=left;spacingLeft=6;fontSize=10;size=12;"
STRONG = NOTE + "strokeWidth=3;"
PHASE = "rounded=0;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=none;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;fontSize=14;fontStyle=1;opacity=60;"

X, W, NX, NW, GAP = 60, 470, 600, 400, 26
steps = [
 ("data", "<b>Saída do MediaPipe, duas câmeras</b> · <i>a.npz, b.npz</i><br>image (T, 33, 4): x·W, y·H em pixel, z relativo, visibilidade ν · times (T) em s<br>(o 'world' de cada câmera não é usado) + som a.wav, b.wav + meta.json (ffprobe)", 78, None),
 ("proc", "<b>1. Sincronia pela palma</b> · two_cameras.py · <i>01_sincronia.typ</i><br>envelope de ataques → correlação cruzada → d = 0,126 s<br>B interpolado nos instantes de A; trecho 31,46–42,85 s", 74, "Captura"),
 ("data", "<b>u_A(t), u_B(t), ν</b> (T, 33): pixels das duas vistas no mesmo instante", 46, None),
 ("proc", "<b>2. Câmeras pelo corpo</b> · two_cameras.py · <i>02_cameras.typ</i><br>K (pinhole, 26 mm) → matriz essencial (RANSAC) → R, t<br>refino: reprojeção + ossos rígidos + focal (Huber)", 74, "n_calib"),
 ("data", "<b>P_A = K_A [I | 0], P_B = K_B [R | t]</b>, |t| = 1 · ângulo 82,6°", 46, None),
 ("proc", "<b>3. Triangulação e esquerda/direita</b> · <i>03_triangulacao.typ</i><br>DLT (SVD) por ponto; troca E/D por grupo se reprojeta 30% melhor", 60, None),
 ("data", "<b>X_j(t)</b> (T, 33, 3) · espaço da câmera A, escala arbitrária", 46, None),
 ("proc", "<b>4. Esqueleto de ossos rígidos</b> · <i>04_esqueleto_rigido.typ</i><br>por quadro: reprojeção ponderada por ν + 26 ossos + 'parado' (Huber)<br>só dos ombros para baixo; a cabeça fica triangulada", 74, "n_fit"),
 ("data", "<b>Y_j(t)</b> (T, 33, 3) · câmera A, ossos de comprimento fixo", 46, None),
 ("proc", "<b>5. Métrico</b> · <i>05_metrico.typ</i><br>para cima = mediana tornozelos→ombros; chão = P2 dos pés<br>escala pelos ombros (1,70 × 0,82); X = esquerda; P = s·M·(X − o)", 74, "n_metric"),
 ("data", "<b>two_cameras.npz</b> · <i>06_duas_cameras_esqueleto_31-43s</i><br>points_m (T, 33, 3): m, Z para cima, chão 0, olha para −Y<br>world (T, 33, 3): o mesmo em torno do meio dos quadris, eixos do MediaPipe", 70, None),
 ("proc", "<b>6. Chão nivelado e contatos</b> · foot_contacts.py · <i>06_chao_e_contatos.typ</i><br>plano z = a·x + b·y + c_k nos pontos parados → cisalhamento z −= a·x + b·y<br>altura de apoio pela marca (37,301 s, pé direito) → contato (≤ 40 mm, &lt; 0,3 m/s)", 74, "Filtros"),
 ("data", "<b>contatos.npz</b> · <i>15_chao_e_contatos</i><br>points_m nivelado, world, contact (T, 2, 3) [E, D] × [tornozelo, calcanhar, ponta]", 56, None),
 ("proc", "<b>7. Ganho por região</b> · amplify_capture.py · <i>07_ganho.typ</i><br>bases por parte → rotação local → quatérnios em 3 faixas (0,3 / 6 Hz)<br>movimento × g (quadril 3); caminho do quadril H' = base + 3·mov + ruído<br>P' = H' + pose relativa (todos os pontos, inclusive os pés)", 88, "n_gain"),
 ("data", "<b>nivelado_quadril_3.npz</b> · <i>tet_v7_movimento</i><br>world', points_m'; contact <b>copiado sem mudar</b>", 56, None),
 ("proc", "<b>8. Retarget no corpo MPFB</b> · drive_capture.py · <i>08_retarget.typ</i><br>gaussiana σ = 2 quadros; eixos (x, z, −y)<br>pelve e peito por bases; coluna por slerp; membros por swing + dobradiça<br>raiz: r_xy = k·(H − H₀), r_z = pé mais baixo no chão", 88, "Retarget"),
 ("proc", "<b>9. Pés presos</b> · drive_capture.py (2 passadas) · <i>09_pes_presos_ik.typ</i><br>âncora do ponto apoiado → descida do quadril δ (suavizada)<br>IK de dois ossos no plano do joelho; pé com a rotação capturada", 74, "n_ik"),
 ("data", "<b>movimento_quadril_3_pes_presos.blend</b><br>por quadro: quatérnio de cada osso (espaço da armadura) + rig.location", 56, None),
 ("proc", "<b>10a. Transformação por osso</b> · tissue_motion_dump.py · <i>10_ossos_para_malha.typ</i><br>T_b(f) = W(f) · A_b(f) · (A_b^rep)⁻¹", 60, "Tecido"),
 ("data", "<b>ossos_quadril_3.npz</b> · T (341, ossos, 4, 4), do repouso MPFB ao mundo", 46, None),
 ("proc", "<b>10b. Malha no quadro 1</b> · tissue_mesh.py · <i>10_ossos_para_malha.typ</i><br>pele por LBS com T⁰ = T(1); faixas 3/6/9/12 mm; partes unidas ou separadas<br>(levadas de volta ao repouso pela pele de cada parte)", 74, "n_mesh"),
 ("data", "<b>tecidos.npz</b> · <i>malha_v19</i><br>nós x⁰, tetraedros, nós guiados + osso, pele mostrada = tetraedro + pesos β", 56, None),
 ("proc", "<b>11a. Simulação</b> · tissue_sim.py · <i>11_simulacao_e_montagem.typ</i><br>T^rel = T·(T⁰)⁻¹; nós guiados M = (1−α)T^rel(f−1) + αT^rel(f), 160 subpassos<br>XPBD Neo-Hookean + cola + contato; pele s = Σ β_k x_k", 74, "n_sim"),
 ("data", "<b>pele.pc2</b> (341, 63 970, 3) · mundo", 46, None),
 ("proc", "<b>11b. Montagem</b> · tissue_assemble.py · <i>11_simulacao_e_montagem.typ</i><br>Mesh Cache (pele simulada) + HM_body só cabeça, mãos e pés (LBS do Blender)", 60, None),
 ("data", "<b>tet_v7_tecidos.blend</b> / tet_v7_cenario.blend", 40, None),
]
notes = {
 "n_calib": (NOTE, "<b>Calibração sem tabuleiro.</b> Focal e posição relativa vêm do próprio corpo. Um erro aqui inclina o chão contra o corpo: a rampa de 9,9° da etapa 6 é esse erro, tirado só das alturas."),
 "n_fit": (NOTE, "<b>Movimento abafado.</b> O termo 'parado' (4) e as gaussianas das etapas 7 e 8 somam suavização. A inclinação da pelve em torno da reta dos quadris não é observável (só 2 pontos)."),
 "n_metric": (NOTE, "<b>Escala por uma altura só</b> (P75 dos ombros, razão 0,82): o erro dela passa a todos os comprimentos e ao caminho do quadril."),
 "n_gain": (STRONG, "<b>CANDIDATO MAIS FORTE.</b> O ganho multiplica o caminho do quadril, e os pés vão junto (P' = H' + pose relativa), sem as pernas compensarem. Os contatos foram medidos antes do ganho.<br><b>Medido:</b> deslize de um ponto do pé durante um contato: mediana 24 mm antes → <b>188 mm</b> depois (p90 392, máx. 509)."),
 "n_ik": (NOTE, "<b>A IK trata o sintoma.</b> Para alcançar âncoras que o ganho deslocou, troca as direções capturadas da perna e baixa o quadril até 174 mm: joelhos dobrados que a pessoa não dobrou.<br>Também na etapa 8: translado (k·ΔH) e rotações (pernas do corpo, 1,59 m) não são forçados a concordar; r_z pelo pé mais baixo salta na troca de apoio."),
 "n_mesh": (NOTE, "<b>Repouso do tecido = quadro 1 dessa pose</b> (quadril baixado, pernas dobradas pela IK), com o afundamento do LBS nas juntas já embutido."),
 "n_sim": (NOTE, "<b>Interpolação linear de matrizes</b> entre quadros: não é rotação (encolhe cos θ/2 no meio). As emendas de cabeça, mãos e pés vêm de duas fontes (LBS do Blender e simulação)."),
}
phases = {"Captura": ("#e1f0e1", "Captura: duas câmeras → 3D métrico (two_cameras.py)"),
          "Filtros": ("#f3e6f7", "Filtros do movimento (antes do Blender)"),
          "Retarget": ("#fde9d4", "Retarget no Blender (drive_capture.py)"),
          "Tecido": ("#e6eef8", "Tecido de tetraedros")}
import re, math
def need(text, width, px_char, line_h):
    plain = re.sub(r"<(?!br)[^>]+>", "", text).replace("&lt;", "<").replace("&gt;", ">")
    lines = sum(max(1, math.ceil(len(seg) / ((width - 20) / px_char))) for seg in plain.split("<br>"))
    return lines * line_h + 16
steps = [(k, t, max(h, need(t, W, 6.3, 15)), tag) for k, t, h, tag in steps]
# layout
y = 110
placed = []
phase_start = {}
for kind, text, h, tag in steps:
    if tag in phases:
        if phase_start:
            y += 20
        phase_start[tag] = y - 40
        y += 10
    placed.append((kind, text, h, tag, y))
    y += h + GAP
end_y = y
order = list(phase_start)
# phase backgrounds first (behind)
for k, tag in enumerate(order):
    y0 = phase_start[tag]
    y1 = (phase_start[order[k + 1]] - 10) if k + 1 < len(order) else end_y
    vertex(20, y0, 1010, y1 - y0, phases[tag][1], PHASE % phases[tag][0])
vertex(20, 10, 1010, 70, "<b>Pose-capture: transformações dos dados, das duas câmeras ao tecido</b><br>"
       "<font style='font-size:11px'>Azul = dados (arquivo, forma, sistema de coordenadas) · amarelo = transformação (programa · arquivo Typst com a matemática) · "
       "vermelho = ponto de atenção para a investigação · Typst em review/2026-11-15/transformacoes/typst (PDF em pdf/)</font>",
       "text;html=1;align=left;verticalAlign=top;fontSize=16;whiteSpace=wrap;")
prev = None
for kind, text, h, tag, yy in placed:
    i = vertex(X, yy, W, h, text, DATA if kind == "data" else PROC)
    if prev:
        edge(prev, i)
    prev = i
    if tag in notes:
        st, nt = notes[tag]
        nh = max(h, need(nt, NW, 5.8, 14))
        n = vertex(NX, yy, NW, nh, nt, st)
        edge(n, i, "endArrow=none;dashed=1;html=1;strokeColor=#b85450;strokeWidth=%s;" % ("2.5" if st is STRONG else "1"))
xml = ('<mxfile host="app.diagrams.net"><diagram id="transformacoes" name="Transformações">'
       f'<mxGraphModel dx="1200" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1060" pageHeight="{end_y + 40}" math="0" shadow="0">'
       '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel></diagram></mxfile>")
open(out, "w", encoding="utf-8").write(xml)
print("cells", len(cells), "height", end_y)
