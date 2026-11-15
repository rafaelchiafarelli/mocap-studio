#import "estilo.typ": *
#show: estilo.with(titulo: "Ganho de movimento por região", etapa: "7", codigo: "amplify_capture.py",
  entra: [`world` $bold(w)_j (t)$ e `points_m` $bold(P)_j (t)$ nivelados; ganhos $g_"quadril" = 3$, demais 1, ruído $g_n = 1$.],
  sai: [`world` $bold(w)'_j (t)$ e `points_m` $bold(P)'_j (t)$ com o movimento ampliado; `contact` copiado sem mudança.])

= Base de cada parte (eixos do MediaPipe, origem nos quadris)
Com a base "frame" do arquivo 00:
$ F_"pelve" = "frame"(bold(w)_23 - bold(w)_24, thin "mid"(11,12) - "mid"(23,24)), quad
  F_"peito" = "frame"(bold(w)_11 - bold(w)_12, thin "mid"(11,12) - "mid"(23,24)) $
$ F_"cabeça" = "frame"(bold(w)_7 - bold(w)_8, thin (bold(w)_0 - "mid"(7,8)) times (bold(w)_7 - bold(w)_8)) $
Membros (braço, antebraço, coxa, canela), osso $a -> b$ com pai $F_"pai"$:
$ bold(d) = "n"(F_"pai"^top (bold(w)_b - bold(w)_a)), quad bold(r) = "n"(op("med")_t bold(d)(t)), quad
  F = F_"pai" thin "Swing"(bold(r) -> bold(d)) $

= Rotação local e três faixas de frequência
$ R_"loc" = F_"pai"^top F quad (R_"loc" = F "na pelve") $
Em quatérnios $q(t)$, todos no mesmo hemisfério ($q(t) dot q(t-1) >= 0$). Gaussiana que corta pela metade a frequência $F$:
$sigma = sqrt(ln 2 \/ 2) \/ (pi F) dot "fps"$ quadros.
$ B = "n"(G_(sigma("0,3" "Hz")) * q), quad M = "n"(G_(sigma(6 "Hz")) * q) $
$ bold(m) = log(B^(-1) M) quad "(movimento, vetor de rotação)", quad bold(n) = log(M^(-1) q) quad "(ruído)" $

= Ampliação e reconstrução
$ R'_"loc" = B dot exp(g thin bold(m)) dot exp(g_n bold(n)), quad F' = F'_"pai" thin R'_"loc" $
Cada parte leva os seus pontos $c$ em torno da sua origem $bold(o)$ (meio dos quadris, meio dos ombros ou a junta), já movida pelo pai:
$ bold(w)'_c (t) = bold(o)'(t) + F'(t) thin F(t)^top (bold(w)_c (t) - bold(o)(t)) $
Recentrado: $bold(w)' <- bold(w)' - "mid"(bold(w)'_23, bold(w)'_24)$.

= Caminho do quadril
$bold(H) = "mid"(bold(P)_23, bold(P)_24)$, separado em faixas da mesma forma, em posições:
$ bold(H)' = G_("0,3") * bold(H) + g_"quadril" (G_6 * bold(H) - G_("0,3") * bold(H)) + g_n (bold(H) - G_6 * bold(H)) $
$ bold(P)'_j = bold(H)' + (w'_(j,x), thin w'_(j,z), thin -w'_(j,y)) $

#valores[caminho do quadril: 71 mm rms de movimento → 214 mm rms; rolagem da pelve ~2,7° → ~8°.]

#atencao[*Este é o candidato mais forte.* $bold(P)'$ põe *todos* os pontos, inclusive os pés, em $bold(H)'$ mais a pose relativa.
O caminho do quadril foi multiplicado por 3, mas as pernas (ganho 1) não foram dobradas para compensar: um pé que estava
parado no chão passa a andar junto com o balanço ampliado do quadril, cerca de $(g - 1) dot$ 71 mm rms ≈ 140 mm. Os
contatos foram medidos antes do ganho e copiados, então dizem "pé parado" exatamente nos quadros em que o ganho o move. Na
etapa 9 a IK segura o pé e, para alcançar, o quadril desce até 17 cm: a descida é consequência dessa inconsistência, não da
dança.

*Medido* (15/11, deslize horizontal de um ponto do pé ao longo de cada contato): antes do ganho, mediana 24 mm, p90 40, máx. 73;
depois do ganho 3, mediana *188 mm*, p90 392, máx. 509.]
