#import "estilo.typ": *
#show: estilo.with(titulo: "Em pé, no chão, em metros (eixos do Blender)", etapa: "5", codigo: "two_cameras.py: to_metric, main",
  entra: [$bold(X)_j (t)$ no espaço da câmera A, escala arbitrária; a altura da pessoa $h = "1,70"$ m.],
  sai: [`points_m` $bold(P)_j (t)$ em metros, eixos do Blender; `world` $bold(w)_j (t)$, o mesmo em torno do meio dos quadris, eixos do MediaPipe.])

= Para cima e chão
$ hat(bold(u)) = "n"(op("med")_t hat(bold(d))(t)), quad bold(d)(t) = "mid"(11,12) - "mid"(27,28) quad "(tornozelos → ombros)" $
$ h_0 = P_2 {bold(X)_j (t) dot hat(bold(u)) : j in {29, 30, 31, 32}} quad "(calcanhares e pontas)" $

= Escala
Referência: as orelhas (razão 0,93 da altura) ou, quando B corta a cabeça, os ombros (razão 0,82):
$ s = (h dot "razão") / (P_75 {"mid"_"ref" (t) dot hat(bold(u)) - h_0}) $

= Eixos e origem
$ bold(l) = op("med")_(t < 30) (bold(X)_23 - bold(X)_24), quad hat(bold(x)) = "n"(bold(l) - (bold(l) dot hat(bold(u))) hat(bold(u))), quad
  hat(bold(y)) = hat(bold(u)) times hat(bold(x)) $
$ bold(o) = bold(q) - (bold(q) dot hat(bold(u)) - h_0) hat(bold(u)), quad bold(q) = op("med")_(t < 30) "mid"(23, 24) $
$ bold(P)_j (t) = s thin M (bold(X)_j (t) - bold(o)), quad M = mat(hat(bold(x))^top; hat(bold(y))^top; hat(bold(u))^top) $
$X$ = esquerda da pessoa (no primeiro segundo), $Z$ para cima, chão em 0, a pessoa olhando para $-Y$ como o corpo do Blender.

= O "world" para o retarget
$ bold(W)_j = bold(P)_j - "mid"(bold(P)_23, bold(P)_24), quad bold(w)_j = (W_(j,x), thin -W_(j,z), thin W_(j,y)) $
(eixos do MediaPipe: $y$ para baixo, $z$ = $Y$), para o `drive_capture.py` ler como lê uma câmera só.

#valores[referência = ombros, $h dot "0,82" = "1,394"$ m; $s = "2,09"$ (é também a distância entre as câmeras em metros);
$hat(bold(u)) = (-"0,014", -"0,999", -"0,039")$ no espaço da câmera A.]

#atencao[$hat(bold(u))$ é a mediana da direção tornozelos→ombros, ou seja, assume que a pessoa está em média de pé e reta.
Uma inclinação média do tronco vira inclinação do "para cima" de toda a cena. E a escala vem de um único percentil de uma única
altura (ombros): o erro dela passa inteiro para todos os comprimentos e para o caminho do quadril.]
