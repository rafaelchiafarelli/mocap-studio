#import "estilo.typ": *
#show: estilo.with(titulo: "Ajuste de um esqueleto de ossos rígidos", etapa: "4", codigo: "two_cameras.py: bone_lengths, fit_skeleton",
  entra: [Os pontos triangulados $bold(X)_j (t)$ da etapa 3, os pixels e as visibilidades acertados.],
  sai: [$bold(Y)_j (t)$ para $j = 11, dots, 32$ (dos ombros para baixo), com ossos de comprimento fixo; a cabeça (0 a 10) fica como triangulada.])

= Comprimento de cada osso
26 ossos $(a, b)$: tronco com as diagonais (11–12, 23–24, 11–23, 12–24, 11–24, 12–23, para não cisalhar), braços, mãos, pernas e pés.
$ ell_(a b) = op("med")_(t : thin nu > "0,8" "nas duas vistas, nos dois pontos") norm(bold(X)_a (t) - bold(X)_b (t)) $

= Ajuste por quadro
Incógnitas $bold(Y) in RR^(22 times 3)$, partindo da triangulação do mesmo quadro (partindo do quadro anterior, o ajuste ficava
para trás). Resíduos:
$ bold(r)_(v,j) = sqrt(max(nu_(v,j), "0,05")) thin (pi(P_v, bold(Y)_j) - bold(u)_(v,j)) $
$ r_(a b) = 300 (norm(bold(Y)_a - bold(Y)_b) / ell_(a b) - 1) $
$ bold(r)^"parado"_j = 30 thin (bold(Y)_j - bold(Y)_j (t - 1)) / ell_"coxa" $
$ min_bold(Y) sum rho(r^2), quad rho = "Huber" "com joelho em 5 px" $
Cada ponto puxa pela sua visibilidade: a vista que só adivinha um membro escondido cede à que o vê.

#atencao[O termo "parado" puxa a pose para o quadro anterior: amortece movimentos rápidos (o próprio CLAUDE.md da investigação
registra que ele, junto com a suavização posterior, abafa o movimento do quadril). E a pelve aqui é só a reta 23–24: o seu
giro em torno dessa reta (inclinação para a frente) não é observável.]
