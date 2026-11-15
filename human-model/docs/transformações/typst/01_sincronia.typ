#import "estilo.typ": *
#show: estilo.with(titulo: "Sincronia pela palma e reamostragem de B", etapa: "1", codigo: "two_cameras.py: audio_offset, resample",
  entra: [A saída do MediaPipe em cada câmera, `a.npz` e `b.npz`: por quadro $i$, os 33 pontos em pixel
    $bold(u)_(v,i,j) = (x_j W_v, thin y_j H_v)$, a visibilidade $nu_(v,i,j) in [0, 1]$ e o instante $tau_(v,i)$; o som de cada vídeo; os
    inícios dos fluxos de som e vídeo (`meta.json`, do ffprobe).],
  sai: [Os pontos de B nos instantes dos quadros de A: $bold(u)_B (tau_A (t) + d)$, $nu_B (tau_A (t) + d)$.])

= Envelope de ataques do som
Para o som $s[k]$ de cada vídeo (taxa $f_s$), a cada $1\/2000$ s:
$ m[n] = max_(k in "janela"(n)) abs(s[k+1] - s[k]), quad
  e[n] = max(0, thin m[n] - (m * "caixa"_(50 "ms"))[n]), quad e <- e \/ max e $
O que sobra são os ataques: a palma é um pico isolado.

= Atraso entre os dois sons
Correlação cruzada (pela FFT), só atrasos até 30 s:
$ c[ell] = sum_n e_B [n + ell] thin e_A [n], quad ell^* = op("arg max", limits: #true)_ell c[ell] $
Refinada por uma parábola nos três vizinhos:
$ delta = 1/2 (c[ell^* - 1] - c[ell^* + 1]) / (c[ell^* - 1] - 2 c[ell^*] + c[ell^* + 1]), quad
  Delta_"som" = (ell^* + delta) / 2000 $
Confiança: $c[ell^*]$ dividido pelo maior pico fora de $plus.minus 20$ ms (abaixo de 1,5 o programa avisa).

= Do atraso do som ao atraso do vídeo
O som e o vídeo de um celular não começam juntos ($a_v$ = início do som, $s_v$ = início do vídeo):
$ d = Delta_"som" + (a_B - s_B) - (a_A - s_A) $
Um instante $tau$ no vídeo A é o instante $tau + d$ no vídeo B.

= Trecho e reamostragem
Ficam só os quadros de A com $tau_A in ["from", "to"]$ (aqui 31,46 a 42,85 s). Cada coordenada de B ($x$, $y$, $nu$) é
interpolada linearmente nos instantes $tau_A (t) + d$:
$ bold(u)_B (tau) = bold(u)_(B,i) + (tau - tau_(B,i)) / (tau_(B,i+1) - tau_(B,i)) (bold(u)_(B,i+1) - bold(u)_(B,i)), quad tau_(B,i) <= tau < tau_(B,i+1) $

#valores[$d = "0,126"$ s. A profundidade relativa $z$ do MediaPipe e os seus pontos "world" de cada câmera não são usados daqui em diante: só o pixel e a visibilidade.]

#atencao[A interpolação de B mistura dois quadros vizinhos do MediaPipe; num movimento rápido (mão, pé), o ponto interpolado
fica entre duas poses e não corresponde exatamente ao instante de A. Com 30 quadros/s isso é até meio quadro (17 ms).]
