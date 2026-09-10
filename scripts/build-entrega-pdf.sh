#!/usr/bin/env bash
# Gera o PDF de submissao da fase 3 FORA do repo, a partir de
# docs/entrega/fase3/entrega-fase-3.md (mesma receita das fases 1 e 2):
#   1. rewrite-md-links.py troca links relativos por URLs absolutas do GitHub
#      (por-arquivo, cada um com seu --base-dir, para os anexos preservarem os
#      proprios links);
#   2. pre-pende a CAPA ABNT (FIAP/15SOAT, integrantes + RM, cidade/ano);
#   3. remove a "## 9. Pendencias..." (checklist interno -- nao vai pro PDF);
#   4. anexa Anexo A (scans de seguranca da fase 3) e Anexo B (evidencias
#      visuais: runs do deploy automatico na AWS, SonarQube, ZAP);
#   5. o bloco Mermaid (que pandoc nao renderiza) vira PNG via mermaid-cli;
#   6. pandoc + weasyprint produzem o PDF.
# Requisitos: python3, pandoc, weasyprint, npx (mermaid-cli baixado on-demand).
# Uso: bash scripts/build-entrega-pdf.sh   (da raiz do repo; OUT=... sobrescreve o destino)
set -euo pipefail

REPO=fiap-postech-sw-architecture/postech-sw-arch-p3
BRANCH=main
SRC=docs/entrega/fase3/entrega-fase-3.md
SEGURANCA=docs/seguranca/scan-fase-3.md
EVID=docs/entrega/fase3/evidencias
OUT_DIR="${HOME}/git/fiap/postech-sw-architecture"
CIDADE="São Paulo"
ANO="2026"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
COMBINADO="${TMP}/entrega-completo.md"

for f in "$SRC" "$SEGURANCA" scripts/rewrite-md-links.py logo-pytstop.png \
  "$EVID/sonarqube-quality-gate-fase3.png" "$EVID/zap-baseline-2026-07-11.txt"; do
  [ -f "$f" ] || { echo "erro: arquivo obrigatorio ausente: $f" >&2; exit 1; }
done

OUT="${OUT:-${OUT_DIR}/documento-entrega-fase-3.pdf}"

# 1) Links absolutos por-arquivo (cada um com seu base-dir). O rodape de
#    navegacao dos .md ("> [↑ Raiz do projeto] · ...") serve ao GitHub, nao ao
#    PDF -- sai aqui, junto com o "---" que o antecede.
rewrite() {  # <src> <dst> <base-dir>
  python3 scripts/rewrite-md-links.py "$1" "$2" --repo "$REPO" --branch "$BRANCH" --base-dir "$3"
  python3 - "$2" <<'EOF'
import sys
linhas = [l for l in open(sys.argv[1], encoding="utf-8") if not l.startswith("> [↑")]
while linhas and linhas[-1].strip() in ("", "---"):
    linhas.pop()
open(sys.argv[1], "w", encoding="utf-8").writelines(linhas + ["\n"])
EOF
}
rewrite "$SRC"       "${TMP}/body.md"   docs/entrega/fase3
rewrite "$SEGURANCA" "${TMP}/anexoA.md" docs/seguranca


# 2) CAPA ABNT (quebra de pagina apos) + CSS de tabela (colunas estreitas de
#    ID/PR nao roubam espaco do texto; celulas quebram palavra a palavra).
cat > "$COMBINADO" <<CAPA
<style>
  /* display:table anula o "table { display:block }" do CSS default do pandoc,
     que faz weasyprint ignorar table-layout e as larguras de coluna. */
  table { display: table; width: 100%; border-collapse: collapse; font-size: 9pt; }
  th, td { padding: 3pt 5pt; vertical-align: top; overflow-wrap: break-word; }
  th { text-align: left; }
  img { max-width: 100%; }
  /* Paginacao no rodape (capa sem numero) e bookmarks por titulo. */
  @page { size: A4; @bottom-center { content: counter(page); font-size: 9pt; color: #555; } }
  @page :first { @bottom-center { content: none; } }
  h1 { bookmark-level: 1; }
  h2 { bookmark-level: 2; }
  h3 { bookmark-level: 3; }
  /* Sumario gerado pelo pandoc (--toc), movido para depois da capa. */
  #TOC { break-after: page; }
  #TOC ul { list-style: none; padding-left: 0; }
  #TOC ul ul { padding-left: 1.2em; }
  #TOC li { margin: 3pt 0; }
  #TOC a { text-decoration: none; color: inherit; }
  #TOC a::after { content: leader('.') target-counter(attr(href), page); }
  /* Diagramas Mermaid em pagina propria: os largos (componentes) em paisagem,
     os altos (sequencia longa, ER) em retrato inteiro. max-height impede o
     corte no rodape que uma imagem alta sofreria (weasyprint nao pagina img). */
  @page paisagem { size: A4 landscape; margin: 1.2cm; @bottom-center { content: counter(page); font-size: 9pt; color: #555; } }
  /* O CSS default do pandoc limita o body a 36em centralizado; a div sai
     desse limite (largura fixa + margem negativa) para ocupar a paisagem. */
  .paisagem { page: paisagem; break-before: page; break-after: page; width: 26cm; margin-left: -5.4cm; }
  .paisagem img { display: block; margin: 0 auto; max-width: 100%; max-height: 16.5cm; }
  .retrato { break-before: page; break-after: page; width: 17cm; margin-left: -1.3cm; }
  .retrato img { display: block; margin: 0 auto; max-width: 100%; max-height: 23cm; }
  pre { white-space: pre-wrap; overflow-wrap: anywhere; }
</style>

<div style="text-align:center; min-height:23cm; display:flex; flex-direction:column; justify-content:space-between; break-after:page;">

<div>

**FIAP — Faculdade de Informática e Administração Paulista**

15SOAT — Pós-Graduação em Arquitetura de Software

</div>

<div>

<img src="${PWD}/logo-pytstop.png" alt="Logo PytStop" style="width:4.5cm; margin: 0 auto 0.8cm auto; display:block;"/>

<p style="font-size:26pt; font-weight:bold; margin:0.4cm 0;">Tech Challenge — Fase 3</p>

<p style="font-size:15pt; font-weight:bold; margin:0.2cm 0;">PytStop — Plataforma de Gestão de Ordens de Serviço</p>

_Documento de Entrega_

</div>

<div>

João Amaral — RM373448 · Allan Aurélio — RM372116 · Carlos Silva — RM374191

Guilherme Sousa — RM373609 · Nicolas Gerbi — RM372644

</div>

<div>

${CIDADE} — ${ANO}

</div>

</div>

<div id="pos-capa"></div>

CAPA

# 3) Corpo, sem "## 9. Pendencias..." (do cabecalho ate o fim; salvaguarda p/ ## 10).
awk '
  /^## 9\. Pend/ { pular=1 }
  /^## 10\./     { pular=0 }
  !pular         { print }
' "${TMP}/body.md" >> "$COMBINADO"

# 4) Anexos (cada um em pagina nova; pula o H1 de origem pois o anexo ja titula).
#    As capturas dos runs sao opcionais: entram as que existirem no diretorio.
evidencia() {  # <arquivo> <legenda>
  if [ -f "$EVID/$1" ]; then
    printf '\n![%s](%s/%s/%s)\n' "$2" "$PWD" "$EVID" "$1"
  else
    echo "aviso: evidencia ausente, pulando: $EVID/$1" >&2
  fi
}
{
  printf '\n\n<div style="break-before:page;"></div>\n\n# Anexo A — Scans de Segurança da Fase 3\n\n'
  tail -n +2 "${TMP}/anexoA.md"

  printf '\n\n<div style="break-before:page;"></div>\n\n# Anexo B — Evidências Visuais\n\n'
  cat <<'ANEXOB'
> Capturas do deploy automático de produção na AWS (07/09/2026, ordem RDS → EKS →
> aplicação → Lambda/API Gateway) e dos scans de fechamento. Fontes versionadas em
> `docs/entrega/fase3/evidencias/`; os runs continuam navegáveis nos links da seção 2.

## B1 — Deploy automático de produção na AWS (runs verdes)
ANEXOB
  evidencia b1a-cd-rds.png "CD do repo infra-db: apply do RDS PostgreSQL 16 (state remoto S3)"
  evidencia b1b-cd-eks.png "CD do repo infra-k8s: apply do cluster EKS e das subnets privadas"
  evidencia b1c-cd-app.png "CD do repo p3: imagens no GHCR, deploy no kind do runner e deploy no EKS com smoke"
  evidencia b1d-cd-lambda.png "CD do repo p3-lambda: gate + apply de Lambda, API Gateway e VPC Link"
  cat <<'ANEXOB2'

## B2 — SonarQube: Quality Gate da fase 3

Scan manual de fechamento (não é gate de CI por decisão, ADR-011): Quality Gate
Passed, 0 bugs, 0 vulnerabilities, 0 hotspots, 0 code smells.
ANEXOB2
  evidencia sonarqube-quality-gate-fase3.png "SonarQube: Quality Gate Passed na HEAD da fase 3"
  printf '\n## B3 — OWASP ZAP baseline (sumário persistido)\n\n```text\n'
  cat "$EVID/zap-baseline-2026-07-11.txt"
  printf '\n```\n'
  cat <<'ANEXOB4'

## B4 — Dashboards e alertas do Grafana (kind, 10/09/2026)

Stack completa levantada com `make cd-local` (mesmos manifests base do EKS),
com o smoke da collection Postman executado antes das capturas.
ANEXOB4
  evidencia b2a-grafana-negocio.png "Dashboard PytStop — Negócio: OS criadas (24h e por hora), tempo médio por status, erros e fila da outbox, status NOC"
  evidencia b2b-grafana-plataforma.png "Dashboard PytStop — Plataforma: health, uptime, taxa de erro 5xx e latência p50/p90/p99 por rota"
  evidencia b2c-grafana-alertas.png "Regras de alerta provisionadas como código (RNF-028)"
  printf '\n## B5 — Smoke da collection Postman via newman (kind, 10/09/2026)\n\n```text\n'
  cat "$EVID/newman-smoke-2026-09-10.txt"
  printf '\n```\n'
} >> "$COMBINADO"

# 5) Mermaid -> PNG, um por bloco. A substituicao no markdown acontece depois
#    do render porque a orientacao da pagina depende da proporcao do PNG, e a
#    legenda deriva do comentario "<!-- fonte: RFC-003 §x -->" que precede
#    cada bloco no .md (falha alto se ele faltar).
python3 - "$COMBINADO" "$TMP" <<'EOF'
import re, sys
md, tmp = sys.argv[1:3]
src = open(md, encoding="utf-8").read()
blocos = re.findall(r"```mermaid\n(.*?)```", src, re.S)
if not blocos:
    sys.exit("erro: nenhum bloco ```mermaid``` no markdown combinado")
for n, corpo in enumerate(blocos, 1):
    open(f"{tmp}/diagrama-{n}.mmd", "w", encoding="utf-8").write(corpo)
EOF
for mmd in "$TMP"/diagrama-*.mmd; do
  npx -y @mermaid-js/mermaid-cli -i "$mmd" -o "${mmd%.mmd}.png" -w 1600 -s 2 -b white
done
python3 - "$COMBINADO" "$TMP" <<'EOF'
import re, struct, sys
md, tmp = sys.argv[1:3]
src = open(md, encoding="utf-8").read()
padrao = re.compile(r"(?:<!-- fonte: RFC-003 (§\d+)[^\n]*-->\n)?```mermaid\n.*?```", re.S)
n = 0
def trocar(m):
    global n
    n += 1
    if not m.group(1):
        sys.exit(f"erro: bloco mermaid {n} sem comentario '<!-- fonte: RFC-003 §x -->' antes dele")
    with open(f"{tmp}/diagrama-{n}.png", "rb") as fh:
        largura, altura = struct.unpack(">II", fh.read(24)[16:24])
    classe = "paisagem" if largura >= altura * 1.3 else "retrato"
    # <img> cru: a imagem markdown herdaria o DPI do PNG (escala 2 do
    # mermaid-cli) e sairia com metade da largura; max-width/max-height no CSS
    # da classe encaixam o diagrama na pagina sem corte.
    return (
        f'<div class="{classe}">\n\n<img src="{tmp}/diagrama-{n}.png" alt="Diagrama {n}"/>\n\n'
        f"<p><em>Diagrama {n} — fonte Mermaid na RFC-003 {m.group(1)} e na seção 7 do documento no repositório.</em></p>\n\n</div>"
    )
src = padrao.sub(trocar, src)
open(md, "w", encoding="utf-8").write(src)
EOF

# 6) HTML intermediario + larguras de coluna + PDF. O passo Python fixa a
#    largura das colunas de codigo curto (ID, PR, #) em TODAS as tabelas de uma
#    vez -- sem ele o layout automatico distribuia espaco igualmente e espremia
#    as colunas de texto.
TMP_HTML="${TMP}/entrega.html"
pandoc "$COMBINADO" -o "$TMP_HTML" -s -V lang=pt-BR --toc --toc-depth=3 \
  -V toc-title="Sumário" --metadata pagetitle="PytStop — Entrega Fase 3"
python3 - "$TMP_HTML" <<'EOF'
import re
import sys

LARGURAS = {
    "ID": "4.5em",
    "PR": "5.5em",
    "#": "2.5em",
    "Artefato": "5.5em",
    "Repo": "6em",
    "Repositório": "9em",
}

html = open(sys.argv[1], encoding="utf-8").read()

# Pandoc emite <colgroup> com fatias iguais nas tabelas cujo markdown tem
# linhas longas; essas larguras vencem as dos <th> e igualam todas as colunas.
html = re.sub(r"<colgroup>.*?</colgroup>", "", html, flags=re.S)

# O pandoc poe o sumario antes de todo o corpo (isto e, antes da capa);
# move o <nav id="TOC"> para logo depois do marcador que fecha a capa.
m = re.search(r"<nav id=\"TOC\".*?</nav>", html, flags=re.S)
if m:
    nav = m.group(0)
    html = html.replace(nav, "", 1)
    # O pandoc pode renderizar o marcador como <div id="pos-capa">\n</div>.
    html, n = re.subn(r'(<div id="pos-capa">\s*</div>)', lambda mm: mm.group(1) + nav, html, count=1)
    if n != 1:
        sys.exit("erro: marcador pos-capa nao encontrado no HTML; sumario nao reposicionado")

def ajustar_ths(m: re.Match[str]) -> str:
    th = m.group(0)
    texto = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    largura = LARGURAS.get(texto)
    if largura is None or "width" in th:
        return th
    return th.replace("<th", f'<th style="width:{largura}"', 1)

def ajustar_tabela(m: re.Match[str]) -> str:
    tabela = re.sub(r"<th(?=[\s>])[^>]*>(.*?)</th>", ajustar_ths, m.group(0), flags=re.S)
    if tabela == m.group(0):
        return tabela
    return tabela.replace("<table", '<table style="table-layout:fixed"', 1)

html = re.sub(r"<table.*?</table>", ajustar_tabela, html, flags=re.S)
open(sys.argv[1], "w", encoding="utf-8").write(html)
EOF
weasyprint "$TMP_HTML" "$OUT" 2> >(grep -v "WARNING" >&2 || true)

echo ">> PDF gerado em $OUT"
