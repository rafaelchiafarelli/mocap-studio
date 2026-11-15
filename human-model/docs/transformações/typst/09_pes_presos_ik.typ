#import "estilo.typ": *
#show: estilo.with(titulo: "Pés presos: âncora, descida do quadril e IK de dois ossos", etapa: "9", codigo: "drive_capture.py: pin_feet, two_bone_ik, plan_drops",
  entra: [A pose da etapa 8 no quadro $t$, a raiz $bold(r)(t)$ e `contact` (etapa 6, copiado pela 7).],
  sai: [Coxa e canela de cada pé apoiado giradas para alcançar a âncora; a raiz baixada $delta(t)$; o pé com a orientação capturada.])

= Âncora
Um pé está apoiado se o calcanhar ou a ponta tem contato. O ponto apoiado é o mais baixo dos dois, $bold(c)$ (no mundo).
No primeiro quadro da sequência: $bold(a) = (c_x, c_y)$. Se o ponto mais baixo troca (rolar do calcanhar para a ponta),
a nova âncora guarda o deslocamento atual: $bold(a)_"novo" = bold(c)_"novo, xy" + (bold(a) - bold(c)_"velho, xy")$.
Alvo do tornozelo (altura mantida):
$ bold(T) = bold(h)_"tornoz" + (a_x - c_x, thin a_y - c_y, thin 0) $

= Descida do quadril quando a perna não alcança
Com $bold(q)$ o quadril (cabeça da coxa), $L = "0,98" (l_1 + l_2)$, $rho = norm((bold(q) - bold(T))_(x y))$:
$ delta_"preciso" = max_("pés apoiados") [(q_z - T_z) - sqrt(L^2 - rho^2)], quad "limitado a" [0, thin "0,25" "m"] $
Duas passadas: a primeira só mede $delta_"preciso" (t)$; a segunda usa
$ delta(t) = max(delta_"preciso" (t), thin G_4 * (max_(abs(s - t) <= 8) delta_"preciso" (s))) $
(máximo móvel de ±8 quadros e gaussiana de 4, para não pular 71 mm num quadro). $bold(r) <- bold(r) - (0, 0, delta)$; o pé
livre também passa pela IK, para ficar onde a captura o pôs.

= IK de dois ossos (no plano em que o joelho dobra)
$l_1 = norm(bold(k) - bold(q))$, $l_2 = norm(bold(h)_"tornoz" - bold(k))$, $bold(e) = bold(T) - bold(q)$,
$r = "clamp"(norm(bold(e)), abs(l_1 - l_2), "0,9995" (l_1 + l_2))$, $hat(bold(e)) = bold(e) \/ norm(bold(e))$.
Lado da dobra: a parte de $bold(k) - bold(q)$ perpendicular a $hat(bold(e))$ (reta: o lado da dobra do repouso):
$ bold(m) = "n"((bold(k) - bold(q)) - ((bold(k) - bold(q)) dot hat(bold(e))) hat(bold(e))), quad
  cos alpha = (l_1^2 + r^2 - l_2^2) / (2 l_1 r) $
$ bold(k)' = bold(q) + l_1 (cos alpha thin hat(bold(e)) + sin alpha thin bold(m)) $
coxa ← Swing para $bold(k)' - bold(q)$; canela ← Swing para $bold(q) + r hat(bold(e)) - bold(k)'$; pé ← a rotação de mundo que tinha antes.

#valores[sem a IK, 56% dos quadros apoiados estavam fora do alcance (p95 100 mm); com ela, escorregamento 0 e descida até
174 mm (p95 163 mm), no máximo 8,7 mm por quadro.]

#atencao[A IK corrige um sintoma: ela troca as direções capturadas da coxa e da canela por outras que alcançam a âncora.
Se a âncora e o quadril vêm de dados inconsistentes (etapa 7, ganho no translado; etapa 8, escala $k$), a perna resultante não
é a capturada: joelhos dobrados que a pessoa não dobrou. Note também que o alvo guarda a *altura* capturada do tornozelo,
não a do chão.]
