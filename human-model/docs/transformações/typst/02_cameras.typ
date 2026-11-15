#import "estilo.typ": *
#show: estilo.with(titulo: "As duas câmeras, achadas pelo próprio corpo", etapa: "2", codigo: "two_cameras.py: calibrate",
  entra: [Os pares $(bold(u)_(A,j)(t), bold(u)_B (t))$ em que as duas câmeras veem bem o ponto ($nu > "0,6"$ nas duas); os quadros em que
    os 8 ossos dos membros são bem vistos inteiros.],
  sai: [$P_A = K_A [I | bold(0)]$ e $P_B = K_B [R | bold(t)]$, com $norm(bold(t)) = 1$ (a escala só vem na etapa 5).])

= Câmera de furo (pinhole), sem distorção
$ K = mat(f, 0, W\/2; 0, f, H\/2; 0, 0, 1), quad
  f_0 = sqrt(W^2 + H^2) thin f_"35mm" / "43,27" $
$f_"35mm" = 26$ mm (equivalente da lente principal dos celulares); 43,27 mm é a diagonal do filme 35 mm.

= Primeira estimativa: matriz essencial
Coordenadas normalizadas $hat(bold(x)) = K^(-1) (bold(u), 1)$. Para todo par visto pelas duas:
$ hat(bold(x))_B^top thin E thin hat(bold(x))_A = 0, quad E = [bold(t)]_times R $
$E$ por RANSAC (limiar $4 \/ f_0$), decomposta em $(R, bold(t))$ escolhendo a solução com os pontos à frente das duas câmeras.

= Refinamento (mínimos quadrados robustos)
Parâmetros $bold(p) = (bold(r), theta, phi, ln f_A, ln f_B)$: $R = exp([bold(r)]_times)$ (Rodrigues) e
$bold(t) = (sin theta cos phi, sin theta sin phi, cos theta)$. Três famílias de resíduos:
$ r_"proj" = pi(P_(v), bold(X)_k) - bold(u)_(v,k) quad "(até 6000 pares, cada um triangulado de novo a cada tentativa, etapa 3)" $
$ r_"osso" = 100 (L_(q,s) / (op("med")_q L_(q,s)) - 1) quad "(8 ossos dos membros, até 150 quadros)" $
$ r_"lente" = (ln f_v - ln f_(0,v)) / "0,3" $
$ min_bold(p) sum rho(r^2), quad rho = "Huber" "com joelho em 3 px" $
O osso entra porque duas vistas só de pontos não determinam $f$: uma focal errada reprojeta igual e só estica a profundidade.
Ossos rígidos determinam.

#valores[ângulo entre as câmeras $"82,6" degree$; $f_A = 1344$ px contra $f_(0,A) = 1324$ px.]

#atencao[A escala aqui é arbitrária (distância entre câmeras = 1) e a focal é ajustada junto: um erro na focal ou na altura das
câmeras inclina o "chão" reconstruído em relação ao corpo. Foi o que deu a rampa de $"9,9" degree$ corrigida na etapa 6 por um
cisalhamento. Ou seja, a reconstrução tem um erro sistemático que depende da profundidade, e ele só foi tirado das alturas.]
