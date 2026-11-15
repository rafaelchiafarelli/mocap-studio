#import "estilo.typ": *
#show: estilo.with(titulo: "Simulação do tecido e montagem no Blender", etapa: "11",
  codigo: "tissue_sim.py, tissue_solver.py, tissue_assemble.py",
  entra: [A malha (nós $bold(x)^0_i$ na pose do quadro 1, tetraedros, nós guiados com o seu osso $b(i)$) e $T_b (f)$.],
  sai: [`pele.pc2`: a pele mostrada em coordenadas de mundo, um quadro por quadro da dança; o `.blend` com ela num Mesh Cache.])

= Transformações relativas ao quadro de construção
$ T^"rel"_b (f) = T_b (f) thin (T^0_b)^(-1) $
Sequência: 1 quadro de identidade, 15 quadros parados (o tecido assenta na gravidade), depois $T^"rel" (1), dots, T^"rel" (341)$.

= Nós guiados, a cada subpasso
160 subpassos por quadro, $h = Delta t \/ 160$; no subpasso $k$, $alpha = (k + 1) \/ 160$:
$ M_b = (1 - alpha) thin T^"rel"_b (f - 1) + alpha thin T^"rel"_b (f), quad bold(x)_i = M_(b(i)) tilde(bold(x))^0_i quad "(nós rígidos e das tampas)" $

= Passo de XPBD (nós livres)
$ bold(v) <- bold(v) + bold(g) h, quad bold(x) <- bold(x) + bold(v) h $
Para cada tetraedro (por cores), $F = D_s D_m^(-1)$ com $D_s = [bold(x)_1 - bold(x)_0, bold(x)_2 - bold(x)_0, bold(x)_3 - bold(x)_0]$:
$ C_D = norm(F)_F, quad alpha_D = 1 \/ (mu V h^2); quad
  C_H = det F - 1 - mu \/ lambda, quad alpha_H = 1 \/ (lambda V h^2) $
$ Delta lambda = -C \/ (sum_i w_i norm(nabla_i C)^2 + alpha), quad Delta bold(x)_i = w_i Delta lambda thin nabla_i C $
Depois, a cola entre as faixas (nó fino na posição baricêntrica do tetraedro grosso), o contato (v7) e a velocidade, amortecida
só no movimento próprio, relativo ao osso:
$ bold(v)_"levado" = (T^"rel"_b (f) - T^"rel"_b (f-1)) tilde(bold(x))^0 \/ Delta t, quad
  bold(v) = bold(v)_"levado" + (1 - D h) ((bold(x) - bold(x)_"ant") \/ h - bold(v)_"levado") $

= A pele mostrada e a montagem
Cada vértice da pele subdividida $s$ fica no seu tetraedro com pesos baricêntricos $beta$ (às vezes um pouco fora):
$ bold(s) = sum_(k=0)^3 beta_k thin bold(x)_("tet"(s), k) $
`pele.pc2` guarda $bold(s)$ em mundo; no Blender, o objeto fica na identidade e o Mesh Cache só lê as posições. Cabeça, mãos e
pés continuam no `HM_body`, deformados pelo rig com $W(f) A_b (f)$ (LBS do Blender), com dois anéis de faces para dentro da emenda.

#atencao[$M_b$ é uma média linear de duas matrizes, não uma rotação: no meio de um quadro em que o osso gira $theta$, o
ponto encolhe para o eixo por um fator $cos(theta \/ 2)$ (0,4% a $10 degree$ por quadro). Pequeno, mas cada quadro começa e termina
certo e passa por dentro no meio, o que dá um tremor de alta frequência aos nós rígidos. Mais importante: as emendas de cabeça,
mãos e pés vêm de duas fontes diferentes (LBS do Blender e simulação) e só se encontram se o tecido perto das tampas não se
mexer.]
