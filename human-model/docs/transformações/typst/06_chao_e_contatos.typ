#import "estilo.typ": *
#show: estilo.with(titulo: "Chão nivelado e contatos dos pés", etapa: "6", codigo: "foot_contacts.py",
  entra: [`points_m` $bold(P)_j (t)$; a sua marca "pé direito no chão" (instante em A: 37,301 s); o $d$ da etapa 1.],
  sai: [$bold(P)''_j (t)$ nivelado, `world` recalculado (etapa 5) e `contact` $C_(f,p)(t)$, pé $f in {E, D}$, ponto $p in {"tornozelo", "calcanhar", "ponta"}$.])

= Velocidade de cada ponto
Lacunas preenchidas por interpolação linear no tempo. Com $G_1$ = gaussiana de 1 quadro:
$ v_j (t) = norm(d/(d t) (G_1 * bold(P)_j)(t)) dot "fps" $

= Plano do chão (uma altura por ponto do pé)
Amostras paradas, $v_j (t) < "0,3"$ m/s, dos 6 pontos dos pés $k$:
$ z = a thin x + b thin y + c_k $
por mínimos quadrados; quatro rodadas tirando as amostras com resíduo $> 3 dot "1,4826" dot "MAD"$ (pé parado no ar).

= Nivelamento por cisalhamento (não por giro)
$ bold(P)' = S thin bold(P), quad S = mat(1, 0, 0; 0, 1, 0; -a, -b, 1) quad (x' = x, thin y' = y, thin z' = z - a x - b y) $
Retas verticais continuam verticais. O giro equivalente nivelava o chão e inclinava o corpo $"9,8" degree$ (rejeitado).

= Altura de apoio pela sua marca
No quadro marcado $k$, janela $abs(i - k) <= "0,1"$ s, pé marcado $f^*$:
$ h_p = op("média")_i z'_(f^* p)(i), quad bold(P)'' = bold(P)' - (0, 0, min_p h_p), quad tilde(h)_p = h_p - min_p h_p quad "(o mesmo nos dois pés)" $

= Contato
$ C_(f,p)(t) = [z''_(f p)(t) - tilde(h)_p < "0,04" "m"] and [v_(f p)(t) < "0,3" "m/s"] $
sequências com menos de 3 quadros descartadas.

#valores[$a = -"0,0297"$, $b = -"0,172"$ (rampa de $"9,9" degree$, resíduo 14 mm); alturas de apoio: tornozelo 74 mm, calcanhar 7 mm,
ponta 0 mm; pé esquerdo no chão em 65% dos quadros, direito em 66%.]

#atencao[$S$ não é uma rotação: muda distâncias. Um osso na direção $Y$ (profundidade) com comprimento $L$ passa a ter
$L sqrt(1 + b^2) approx "1,015" L$ e ganha uma inclinação. E o cisalhamento é a correção de um erro de calibração (etapa 2)
que provavelmente também deforma as direções dos ossos, não só as alturas.]
