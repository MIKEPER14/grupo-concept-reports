"""Gera o PDF do report de leads do Grupo Concept a partir de data/report.json e envia-o por email.

Corre no GitHub Actions todas as segundas-feiras às 08:00 de Lisboa. Os dados em
data/report.json são atualizados antes disso (ver docs/atualizacao-semanal.md).

Variáveis de ambiente:
  GMAIL_USER, GMAIL_APP_PASSWORD  conta Gmail remetente e palavra-passe de aplicação
  EVENTO, AGENDAMENTO             evento do GitHub e cron que o disparou
  MODO                            "teste" (só para o remetente) ou "real", em execuções manuais
  SO_PDF=1                        gera só o PDF, sem enviar (para testar localmente)
"""
import datetime as dt
import io
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

RAIZ = Path(__file__).parent
NAVY = colors.HexColor("#1B2A41")
MARCAS = {  # cor principal, cabeçalho, total
    "BodyConcept": ("#C65911", "#F8CBAD", "#F4B183"),
    "DepilConcept": ("#1A9DB8", "#CDEEF4", "#9ADBE8"),
}
CINZA, CINZA_TOTAL = colors.HexColor("#EDEDED"), colors.HexColor("#D9D9D9")


def data_pt(iso):
    return dt.date.fromisoformat(iso).strftime("%d/%m/%Y")


def ler_blocos(linhas):
    """Separa a grelha da aba Report em blocos mensais: título, marcas, cabeçalho e linhas."""
    blocos, i = [], 4
    while i < len(linhas):
        cheias = [c for c in linhas[i] if str(c).strip()]
        if len(cheias) == 1 and "·" in str(linhas[i][0]):
            marcas = [c for c in linhas[i + 1] if str(c).strip()]
            cabecalho = linhas[i + 2]
            corpo, j = [], i + 3
            while j < len(linhas) and linhas[j] and str(linhas[j][0]).strip():
                corpo.append([str(c) for c in linhas[j]] + [""] * (11 - len(linhas[j])))
                j += 1
                if corpo[-1][0] == "Total":
                    break
            blocos.append({"titulo": linhas[i][0], "marcas": marcas, "cabecalho": cabecalho, "linhas": corpo})
            i = j
        else:
            i += 1
    if not blocos:
        sys.exit("data/report.json não tem nenhum bloco mensal reconhecível em report_rows.")
    return blocos


def tabela_mes(bloco, estilo_cab):
    m1, m2 = bloco["marcas"][0], bloco["marcas"][1]
    cab = [Paragraph(str(c), estilo_cab) for c in bloco["cabecalho"]]
    dados = [[bloco["titulo"]] + [""] * 10, ["", m1, "", "", "", "", m2, "", "", "", ""], cab] + bloco["linhas"]
    larguras = [38 * mm] + [24 * mm, 27 * mm, 16 * mm, 24 * mm, 24 * mm] * 2
    t = Table(dados, colWidths=larguras, rowHeights=[8 * mm, 7 * mm, 11 * mm] + [6.5 * mm] * len(bloco["linhas"]))
    ult = len(dados) - 1
    st = [
        ("SPAN", (0, 0), (-1, 0)), ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 1), 10),
        ("SPAN", (1, 1), (5, 1)), ("SPAN", (6, 1), (10, 1)), ("TEXTCOLOR", (1, 1), (-1, 1), colors.white),
        ("ALIGN", (0, 0), (-1, 2), "CENTER"), ("ALIGN", (1, 3), (-1, -1), "CENTER"), ("ALIGN", (0, 2), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("FONTSIZE", (0, 3), (-1, -1), 9),
        ("BACKGROUND", (0, 2), (0, 2), CINZA), ("BACKGROUND", (0, ult), (0, ult), CINZA_TOTAL),
        ("FONTNAME", (0, ult), (-1, ult), "Helvetica-Bold"),
        ("LINEBELOW", (0, 3), (-1, ult - 1), 0.25, colors.HexColor("#DDDDDD")),
    ]
    for marca, (c0, c1) in ((m1, (1, 5)), (m2, (6, 10))):
        principal, claro, total = MARCAS.get(marca, ("#555555", "#DDDDDD", "#BBBBBB"))
        st += [("BACKGROUND", (c0, 1), (c1, 1), colors.HexColor(principal)),
               ("BACKGROUND", (c0, 2), (c1, 2), colors.HexColor(claro)),
               ("BACKGROUND", (c0, ult), (c1, ult), colors.HexColor(total))]
    t.setStyle(TableStyle(st))
    return t


def grafico(curva):
    datas = [dt.date.fromisoformat(d) for d, _, _ in curva]
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=150)
    ax.plot(datas, [v for _, v, _ in curva], color="#33994D", linewidth=2.2, label="Válidas (acumulado)")
    ax.plot(datas, [s for _, _, s in curva], color="#CC4033", linewidth=2.2, label="Spam (acumulado)")
    for serie, cor in (([v for _, v, _ in curva], "#33994D"), ([s for _, _, s in curva], "#CC4033")):
        ax.annotate(str(serie[-1]), (datas[-1], serie[-1]), xytext=(6, 0), textcoords="offset points",
                    color=cor, fontsize=11, fontweight="bold", va="center")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=12))
    ax.set_ylabel("Leads acumuladas")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color="#E3E3E3", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def gerar_pdf(dados, destino):
    titulo = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15, textColor=NAVY, spaceAfter=2 * mm)
    sub = ParagraphStyle("s", fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#555555"), spaceAfter=5 * mm)
    cab = ParagraphStyle("c", fontName="Helvetica-Bold", fontSize=8.5, alignment=1, leading=10)
    h2 = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12, textColor=NAVY, spaceAfter=3 * mm)
    nota = ParagraphStyle("n", fontName="Helvetica", fontSize=8.5, textColor=colors.HexColor("#555555"), spaceBefore=3 * mm)
    periodo = f"{data_pt(dados['period_start'])} a {data_pt(dados['period_end'])}"
    doc = SimpleDocTemplate(str(destino), pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=10 * mm,
                            title=f"Report de leads franchising Grupo Concept · {periodo}", author="Digital Xperience")
    el = [Paragraph("Report de leads franchising Grupo Concept", titulo),
          Paragraph(f"Período: {periodo} · Fontes: Meta Ads, Google Ads, GA4 e registo de leads.", sub)]
    for n, bloco in enumerate(ler_blocos(dados["report_rows"])):
        if n and n % 2 == 0:
            el.append(PageBreak())
        el += [tabela_mes(bloco, cab), Spacer(1, 6 * mm)]
    el.append(Paragraph("Taxa de conversão = leads ÷ cliques (no orgânico, leads ÷ sessões orgânicas do GA4).", nota))
    if dados.get("curve"):
        el += [PageBreak(), Paragraph("Curva de captação de leads (acumulado)", h2),
               Image(grafico(dados["curve"]), width=265 * mm, height=265 * mm * 4.6 / 11),
               Paragraph("Válidas e spam das duas marcas em conjunto. As leads por verificar não entram em nenhuma das linhas.", nota)]
    doc.build(el)


def corpo_email(dados, assinatura):
    periodo = f"{data_pt(dados['period_start'])} a {data_pt(dados['period_end'])}"
    blocos = ler_blocos(dados["report_rows"])
    linhas = []
    for b in blocos:
        tot = b["linhas"][-1]
        mes = b["titulo"].split("·")[0].strip()
        linhas.append((mes, b["marcas"][0], tot[1], tot[3]))
        linhas.append((mes, b["marcas"][1], tot[6], tot[8]))
    texto = [f"Bom dia,", "",
             f"Segue em anexo o report semanal de leads de franchising do Grupo Concept, com dados de {periodo}.", ""]
    texto += [f"- {m} · {marca}: {inv} de investimento, {leads} leads" for m, marca, inv, leads in linhas]
    texto += ["", f"Report completo: {dados['sheet_url']}", "", "Com os melhores cumprimentos,", assinatura]
    tr = "".join(f"<tr><td>{m}</td><td>{marca}</td><td align='right'>{inv}</td><td align='right'>{leads}</td></tr>"
                 for m, marca, inv, leads in linhas)
    html = f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#222">
<p>Bom dia,</p>
<p>Segue em anexo o report semanal de leads de franchising do Grupo Concept, com dados de {periodo}.</p>
<table cellpadding="6" cellspacing="0" border="1" style="border-collapse:collapse;border-color:#ddd;font-size:13px">
<tr style="background:#1B2A41;color:#fff"><th align="left">Mês</th><th align="left">Marca</th><th>Investimento</th><th>Leads</th></tr>{tr}</table>
<p>Report completo: <a href="{dados['sheet_url']}">abrir no Google Sheets</a></p>
<p>Com os melhores cumprimentos,<br>{assinatura}</p></div>"""
    return f"Report de leads franchising Grupo Concept · {periodo}", "\n".join(texto), html


def enviar(remetente, password, destinatarios, assunto, texto, html=None, anexo=None):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = remetente, ", ".join(destinatarios), assunto
    msg.set_content(texto)
    if html:
        msg.add_alternative(html, subtype="html")
    if anexo:
        msg.add_attachment(anexo.read_bytes(), maintype="application", subtype="pdf", filename=anexo.name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(remetente, password)
        s.send_message(msg)


def main():
    cfg = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    dados = json.loads((RAIZ / "data" / "report.json").read_text(encoding="utf-8"))
    agora = dt.datetime.now(ZoneInfo(cfg["fuso"]))
    evento, modo = os.environ.get("EVENTO", ""), os.environ.get("MODO") or "teste"

    if evento == "schedule":
        # Há dois agendamentos (07:00 e 08:00 UTC); só envia o que dá 08:00 em Lisboa.
        certo = "0 8 * * 1" if agora.utcoffset() == dt.timedelta(0) else "0 7 * * 1"
        if os.environ.get("AGENDAMENTO") != certo:
            print("Agendamento da outra hora legal; nada a enviar.")
            return
        modo = "real"

    (RAIZ / "out").mkdir(exist_ok=True)
    pdf = RAIZ / "out" / f"Report Leads Franchising Grupo Concept {dados['period_start']} a {dados['period_end']}.pdf"
    gerar_pdf(dados, pdf)
    print(f"PDF gerado: {pdf.name}")
    if os.environ.get("SO_PDF"):
        return

    remetente, password = os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_APP_PASSWORD")
    if not remetente or not password:
        sys.exit("Faltam os segredos GMAIL_USER e GMAIL_APP_PASSWORD no repositório.")
    assunto, texto, html = corpo_email(dados, cfg["assinatura"])

    if modo != "real":
        enviar(remetente, password, [remetente], "[TESTE] " + assunto, texto, html, pdf)
        print("Email de teste enviado só para o remetente.")
        return

    esperado = (agora.date() - dt.timedelta(days=1)).isoformat()
    if dados["period_end"] != esperado:
        aviso = (f"O report do Grupo Concept NÃO foi enviado ao cliente.\n\n"
                 f"Os dados em data/report.json vão até {data_pt(dados['period_end'])}, "
                 f"mas deviam ir até {data_pt(esperado)}. A atualização semanal não correu ou falhou.\n"
                 f"Depois de atualizar, corre o workflow à mão em modo 'real'.")
        enviar(remetente, password, [remetente], "[ALERTA] Report Grupo Concept não enviado", aviso)
        sys.exit("Dados desatualizados: enviado alerta ao remetente, nada enviado ao cliente.")

    enviar(remetente, password, cfg["destinatarios"], assunto, texto, html, pdf)
    print(f"Report enviado para {len(cfg['destinatarios'])} destinatários.")


if __name__ == "__main__":
    main()
