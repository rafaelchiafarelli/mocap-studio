#import "estilo.typ": *
#show: estilo.with(titulo: "Dos ossos animados às transformações por osso, e a malha no quadro 1", etapa: "10",
  codigo: "tissue_motion_dump.py, tissue_mesh.py (pose=)",
  entra: [O `.blend` animado da etapa 9; a pele do MPFB em repouso com os pesos $w_(i b)$ (`corpo_repouso.npz`).],
  sai: [`ossos_*.npz`: $T_b (f) in RR^(4 times 4)$ por osso e quadro; a malha de tetraedros construída já na pose do quadro 1.])

= Transformação de cada osso a partir do repouso
Com $W(f)$ a matriz de mundo do rig (só o translado $bold(r)(f)$), $A_b (f)$ a matriz do osso posado no espaço da armadura e
$A_b^"rep"$ a do repouso (`bone.matrix_local`):
$ T_b (f) = W(f) thin A_b (f) thin (A_b^"rep")^(-1) $
Um ponto preso rigidamente ao osso $b$ em repouso, $bold(x)^"rep"$, está em $T_b (f) tilde(bold(x))^"rep"$ no quadro $f$.

= A pele levada à pose do quadro 1
$T^0 = T(1)$. A pele do MPFB (13 380 vértices), o corpo sem seios e os ossos:
$ bold(x)^0_i = sum_b hat(w)_(i b) thin T^0_b thin tilde(bold(x))^"rep"_i, quad bold(h)^0_b = T^0_b tilde(bold(h))^"rep"_b $
A pele subdividida duas vezes (a mostrada, ~64 000 vértices) usa pesos emprestados dos 4 vértices mais próximos,
ponderados por $1 \/ "distância"$.

= Regras lidas no repouso
Zonas, grupos e espessuras de gordura são por vértice no repouso. As regras do tronco (alturas, frente/trás, esquerda/direita)
são lidas trazendo cada centro de tetraedro de volta pelo osso do meio do tronco:
$ bold(c)^"rep" = (T^0_"spine.002")^(-1) tilde(bold(c)) $

= Partes e junção (malha_v19)
Cada voxel vai para a parte (tronco, braços, pernas) em cuja pele, fechada por tampas, ele está mais fundo. Um nó comum a duas
partes $p$, $q$ é levado ao repouso pela pele de cada uma ($bold(s)_p$ = vértice de pele de $p$ mais próximo):
$ bold(rho)_p = (sum_b hat(w)_(bold(s)_p b) T^0_b)^(-1) tilde(bold(x)) $
Se $max norm(bold(rho)_p - bold(rho)_q) < 2$ cm as partes ficam unidas ali (um nó); senão o nó é duplicado (separadas).
Perna e tronco: sempre unidos.

#atencao[A malha inteira é construída *no quadro 1 da etapa 9*: com o quadril baixado e as pernas dobradas pela IK. Se esse
quadro já tem a perna esquisita, a forma de repouso do tecido (sem tensão) é essa forma esquisita. E a pele chega lá por LBS,
que afunda nas juntas dobradas (o "efeito embrulho"): o volume que a simulação preserva é o volume já afundado.]
