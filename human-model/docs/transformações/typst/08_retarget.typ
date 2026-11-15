#import "estilo.typ": *
#show: estilo.with(titulo: "Retarget: dos pontos para os ossos do corpo MPFB", etapa: "8", codigo: "drive_capture.py",
  entra: [`world` $bold(w)'_j (t)$ e `points_m` $bold(P)'_j (t)$ (etapa 7); o rig MPFB em repouso (pose A), `02_corpo_com_rig.blend`.],
  sai: [Por quadro, a rotação de cada osso (quatérnio, espaço da armadura) e a raiz $bold(r)(t)$ = `rig.location`, em chaves no `.blend`.])

= Suavização e eixos
Lacunas interpoladas; gaussiana de $sigma = 2$ quadros em $bold(w)'$ e em $bold(P)'$ (de novo; já houve as etapas 4 e 7).
$ bold(b)_j = (w'_(j,x), thin w'_(j,z), thin -w'_(j,y)) quad "(eixos do Blender, rotação própria: nada espelhado)" $

= Tronco
Com $"frame"_B (bold(x), bold(w))$: colunas $X = hat(bold(x))$, $Z = hat(bold(w))_perp$, $Y = Z times X$ (os eixos do corpo em repouso):
$ R_p = "frame"_B (bold(b)_23 - bold(b)_24, thin "mid"(11,12) - "mid"(23,24)), quad R_c = "frame"_B (bold(b)_11 - bold(b)_12, thin "mesmo") $
Escrever uma rotação de mundo $R$ num osso $k$ (cabeça $bold(h)_k$ mantida, $R_k^"rep"$ = rotação de repouso):
$ A_k = mat(R thin R_k^"rep", bold(h)_k; bold(0)^top, 1) $
spine ← $R_p$; spine.001…004 ← $"slerp"(q_p, q_c, i\/4)$, $i = 1..4$; spine.005, .006 ← $q_c$ (sem cabeça).

= Membros (por lado)
Seja $hat(bold(y))_k$ o eixo $Y$ atual do osso (a sua direção). Coxa:
$ A_"coxa" <- "Swing"(hat(bold(y))_"coxa" -> bold(b)_"joelho" - bold(b)_"quadril") thin A_"coxa" $
Dobradiça: o joelho deve dobrar no plano capturado. Com $bold(u) = hat(bold(y))_"coxa"$, $bold(l) = "n"(bold(b)_"tornoz" - bold(b)_"joelho")$:
$ bold(n) = bold(u) times bold(l), quad beta = arcsin norm(bold(n)) thin (180 degree - beta "se" bold(u) dot bold(l) < 0), quad
  omega = "clamp"((beta - 10 degree) \/ 20 degree, 0, 1) $
$ phi = "atan2"(bold(u) dot (bold(x)_"coxa" times hat(bold(n))), thin bold(x)_"coxa" dot hat(bold(n))), quad
  A_"coxa" <- "Rot"(bold(u), omega phi) thin A_"coxa" $
($hat(bold(n))$ com o sinal da dobra do repouso). Depois: canela ← Swing para $bold(l)$; pé ← Swing do vetor da sola
(calcanhar→ponta, no repouso) para $bold(b)_"ponta" - bold(b)_"calcanhar"$. Braço, antebraço iguais com o cotovelo; mão ← Swing para
(meio de indicador e mínimo) − pulso, e giro em torno de si até indicador−mínimo coincidir.
Só rotações: cada filho começa no fim do pai, então o corpo guarda as próprias proporções.

= Raiz (translado)
$ k = h_"quadril"^"corpo" \/ op("med")_t H'_z (t), quad
  r_x (t), r_y (t) = k thin (H'_(x y)(t) - H'_(x y)(0)), quad
  r_z (t) = z_"chão"^"rep" - min_("pontos dos pés") z $
O pé mais baixo é posto no chão a cada quadro.

#atencao[Translado e rotações vêm de fontes diferentes e não são forçados a concordar: o quadril anda $k dot Delta bold(H)$
(capturado e escalado), mas onde os pés caem depende das direções das pernas aplicadas às pernas *do corpo* (1,59 m, outras
proporções). Qualquer diferença vira pé escorregando, mesmo com ganho 1. E $r_z$ pelo pé mais baixo salta quando o pé de
apoio troca, e não segura o pé de apoio no lugar: o quadril sobe e desce com o erro de altura dos pés.]
