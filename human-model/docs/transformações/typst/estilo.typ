// Estilo comum dos arquivos de transformações (pose-capture, 2026-11-15).
#let estilo(titulo: "", etapa: "", codigo: "", entra: [], sai: [], corpo) = {
  set document(title: titulo)
  set page(paper: "a4", margin: (x: 2cm, y: 2cm), numbering: "1")
  set text(lang: "pt", size: 10.5pt)
  set par(justify: true)
  set heading(numbering: "1.")
  set math.equation(numbering: "(1)")
  block(width: 100%, inset: (bottom: 6pt), stroke: (bottom: 0.6pt + gray))[
    #text(9pt, fill: gray)[Etapa #etapa · código: #raw(codigo)] \
    #text(16pt, weight: "bold")[#titulo]
  ]
  grid(columns: (1fr, 1fr), gutter: 8pt,
    block(fill: rgb("#eef4fb"), inset: 8pt, radius: 4pt, width: 100%)[*Entra.* #entra],
    block(fill: rgb("#eef8ee"), inset: 8pt, radius: 4pt, width: 100%)[*Sai.* #sai])
  v(4pt)
  corpo
}

// Ponto de atenção: algo que pode explicar o resultado ruim, para investigar.
#let atencao(corpo) = block(fill: rgb("#fdecea"), stroke: (left: 3pt + rgb("#c0392b")), inset: 8pt, width: 100%)[
  *Ponto de atenção.* #corpo]

// Valores desta tomada (06_duas_cameras_esqueleto_31-43s e o que veio depois).
#let valores(corpo) = block(fill: rgb("#f6f6f6"), inset: 8pt, radius: 4pt, width: 100%)[*Nesta tomada.* #corpo]
