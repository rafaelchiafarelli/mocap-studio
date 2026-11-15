#import "estilo.typ": *
#show: estilo.with(titulo: "Triangulação e troca de esquerda/direita", etapa: "3", codigo: "two_cameras.py: triangulate, solve_frames",
  entra: [$P_A$, $P_B$ e, por quadro, $bold(u)_(A,j)$, $bold(u)_(B,j)$, $nu$.],
  sai: [$bold(X)_j (t) in RR^3$ no espaço da câmera A (escala arbitrária), com os rótulos esquerda/direita acertados.])

= Triangulação linear (DLT)
Com $P^1, P^2, P^3$ as linhas de $P$ e $bold(u) = (x, y)$, cada vista dá duas equações em $tilde(bold(X))$:
$ mat(x_A P_A^3 - P_A^1; y_A P_A^3 - P_A^2; x_B P_B^3 - P_B^1; y_B P_B^3 - P_B^2) tilde(bold(X)) = bold(0) $
Cada linha é normalizada; $tilde(bold(X))$ é o vetor singular de menor valor (SVD), e $bold(X) = tilde(bold(X))_(1:3) \/ tilde(X)_4$.
Erro de reprojeção: $bold(e)_v = pi(P_v, bold(X)) - bold(u)_v$.

= Esquerda e direita
O MediaPipe às vezes troca os lados numa das vistas. Para cada grupo $g in {"rosto", "braços", "pernas"}$, $sigma_g$ troca os pares
(1↔4, …, 11↔12, …, 31↔32). Com os pontos do grupo bem vistos ($nu > "0,3"$ nas duas):
$ e_"igual" = op("med") abs(bold(e)(bold(u)_A, bold(u)_B)), quad e_"trocado" = op("med") abs(bold(e)(bold(u)_A, sigma_g bold(u)_B)) $
Se $e_"trocado" < "0,7" thin e_"igual"$, uma das vistas trocou. Qual: a que deixa os pontos mais perto do quadro anterior,
$ norm(bold(X)(sigma_g bold(u)_A, bold(u)_B) - bold(X)(t-1)) " contra " norm(bold(X)(bold(u)_A, sigma_g bold(u)_B) - bold(X)(t-1)) $
