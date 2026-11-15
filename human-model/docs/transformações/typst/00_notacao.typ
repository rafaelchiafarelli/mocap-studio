#import "estilo.typ": *
#show: estilo.with(titulo: "Notação e sistemas de coordenadas", etapa: "0", codigo: "—",
  entra: [—], sai: [Os símbolos usados nos outros arquivos.])

= Índices
- $v in {A, B}$: a câmera (vídeo). A é a referência de tempo e de espaço.
- $t$: quadro do vídeo A, com o seu instante $tau_A (t)$ em segundos (os celulares gravam com taxa variável).
- $j in {0, dots, 32}$: o ponto do MediaPipe (0 nariz, 7/8 orelhas, 11/12 ombros, 13/14 cotovelos, 15/16 pulsos,
  23/24 quadris, 25/26 joelhos, 27/28 tornozelos, 29/30 calcanhares, 31/32 pontas dos pés; ímpar = esquerda da pessoa).
- $op("med")$: mediana; $P_k$: percentil $k$; $G_sigma * x$: média gaussiana no tempo, desvio $sigma$ quadros.
- $hat(bold(a)) = "n"(bold(a)) = bold(a) \/ norm(bold(a))$: vetor unitário ("n" de normalizar, para expressões longas).
- $"mid"(a, b) = (bold(X)_a + bold(X)_b) \/ 2$.

= Sistemas de coordenadas
#table(columns: (auto, 1fr), stroke: 0.4pt + gray, inset: 6pt,
  [*Nome*], [*Eixos e unidade*],
  [Pixel da câmera $v$], [$bold(u) = (x, y)$, origem no canto superior esquerdo, $y$ para baixo, em pixels.],
  [Câmera A], [Centro óptico de A na origem, $z$ para a frente. A escala é arbitrária: a distância entre as câmeras vale 1.],
  [Métrico (Blender)], [`points_m`: metros, $Z$ para cima, chão em $Z = 0$, $X$ = esquerda da pessoa, ela começa olhando para $-Y$.],
  [MediaPipe "world"], [`world`: metros, origem no meio dos quadris, $x$ = $X$, $y$ para baixo ($= -Z$), $z = Y$.],
  [Armadura (rig)], [O espaço do objeto `HM_rig`; sem rotação, só translado pela raiz $bold(r)(t)$ (= `rig.location`).],
  [Repouso MPFB], [A pose A do MPFB (`02_corpo_com_rig.blend`), rig na origem: aqui repouso = espaço da armadura.],
)

= Transformações recorrentes
Base a partir de um eixo e de um "para cima" (as colunas são os eixos):
$ "frame"(bold(x), bold(w)) = mat(hat(bold(x)), hat(bold(z)) times hat(bold(x)), hat(bold(z))), quad
  hat(bold(z)) = "n"(bold(w) - (bold(w) dot hat(bold(x))) hat(bold(x))) $ <frame>

Menor rotação que leva o unitário $bold(a)$ a $bold(b)$ ("swing"):
$ "Swing"(bold(a) -> bold(b)) = "Rot"(hat(bold(n)), theta), quad bold(n) = bold(a) times bold(b), quad
  theta = "atan2"(norm(bold(n)), bold(a) dot bold(b)) $ <swing>

Projeção de uma câmera $P in RR^(3 times 4)$, com $tilde(bold(X)) = (bold(X), 1)$:
$ pi(P, bold(X)) = ((P tilde(bold(X)))_1, (P tilde(bold(X)))_2) \/ (P tilde(bold(X)))_3 $ <proj>

Pele por ossos (linear blend skinning), pesos normalizados $hat(w)_b = w_b \/ sum_c w_c$:
$ bold(x)' = sum_b hat(w)_b thin T_b thin tilde(bold(x)) $ <lbs>
