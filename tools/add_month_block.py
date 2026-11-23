"""Gera os pedidos da API do Google Sheets para acrescentar um bloco mensal à aba Report.

Uso: python tools/add_month_block.py 2026 12 25
  (ano, mês, linha onde começa o bloco; cada bloco ocupa 9 linhas e fica 10 abaixo do anterior)

Escreve out/bloco_formato.json (para spreadsheets:batchUpdate) e out/bloco_valores.json
(para values:batchUpdate). As datas do mês ficam nas células M e N da primeira linha do bloco.
"""
import json
import sys
from pathlib import Path

SHEET_ID = 104951460  # aba Report
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
CAB = ["Investimento", "Cliques (sessões no orgânico)", "Leads", "Custo por lead", "Taxa de conversão"]


def rg(r0, r1, c0, c1):
    return {"sheetId": SHEET_ID, "startRowIndex": r0, "endRowIndex": r1, "startColumnIndex": c0, "endColumnIndex": c1}


def main(ano, mes, top):
    nome, s, e, i0 = f"{MESES[mes - 1]} {ano}", f"$M${top}", f"$N${top}", top - 1
    pedidos = [{"copyPaste": {"source": rg(i0 - 10, i0 - 1, 0, 11), "destination": rg(i0, i0 + 9, 0, 11), "pasteType": "PASTE_FORMAT"}}]
    pedidos += [{"mergeCells": {"range": r, "mergeType": "MERGE_ALL"}} for r in (rg(i0, i0 + 1, 0, 11), rg(i0 + 1, i0 + 2, 1, 6), rg(i0 + 1, i0 + 2, 6, 11))]
    for a, b, px in ((i0, i0 + 2, 24), (i0 + 2, i0 + 3, 37), (i0 + 3, i0 + 9, 21)):
        pedidos.append({"updateDimensionProperties": {"range": {"sheetId": SHEET_ID, "dimension": "ROWS", "startIndex": a, "endIndex": b}, "properties": {"pixelSize": px}, "fields": "pixelSize"}})

    linhas = [[f'="{nome} · "&TEXT({s};"dd/mm/yyyy")&" a "&TEXT({e};"dd/mm/yyyy")'],
              [None, "BodyConcept", None, None, None, None, "DepilConcept"], ["Origem"] + CAB + CAB]
    for n, origem in enumerate(["Meta Business", "Google Adwords", "LinkedIn", "Orgânico", "eBook"]):
        r, linha = top + 3 + n, [origem]
        for marca, (b, c, d) in ((f"$B${top + 1}", "BCD"), (f"$G${top + 1}", "GHI")):
            def soma(aba, col, col_marca="C"):
                return f"=SUMIFS('{aba}'!${col}:${col};'{aba}'!${col_marca}:${col_marca};{marca};'{aba}'!$A:$A;\">=\"&{s};'{aba}'!$A:$A;\"<=\"&{e})"
            inv, cli = 0, 0
            if origem == "Meta Business":
                inv, cli = soma("Dados Meta", "D"), soma("Dados Meta", "F")
            elif origem == "Google Adwords":
                inv, cli = soma("Dados Google Ads", "D"), soma("Dados Google Ads", "F")
            elif origem == "Orgânico":
                cli = soma("Dados GA4", "D", "B")
            leads = f"=COUNTIFS(Leads!$B:$B;{marca};Leads!$D:$D;$A{r};Leads!$A:$A;\">=\"&{s};Leads!$A:$A;\"<\"&({e}+1))"
            linha += [inv, cli, leads, f"=IF({d}{r}=0;0;{b}{r}/{d}{r})", f"=IF({c}{r}=0;0;{d}{r}/{c}{r})"]
        linhas.append(linha)
    t, total = top + 8, ["Total"]
    for b, c, d in ("BCD", "GHI"):
        total += [f"=SUM({x}{top + 3}:{x}{top + 7})" for x in (b, c, d)] + [f"=IF({d}{t}=0;0;{b}{t}/{d}{t})", f"=IF({c}{t}=0;0;{d}{t}/{c}{t})"]
    linhas.append(total)
    valores = {"valueInputOption": "USER_ENTERED", "data": [
        {"range": f"Report!A{top}:K{top + 8}", "values": linhas},
        {"range": f"Report!M{top}:N{top}", "values": [[f"=MAX($B$2;DATE({ano};{mes};1))", f"=MIN($B$3;EOMONTH(DATE({ano};{mes};1);0))"]]}]}
    out = Path(__file__).parent.parent / "out"
    out.mkdir(exist_ok=True)
    (out / "bloco_formato.json").write_text(json.dumps({"requests": pedidos}, separators=(",", ":")), encoding="utf-8")
    (out / "bloco_valores.json").write_text(json.dumps(valores, separators=(",", ":")), encoding="utf-8")
    print(f"Bloco de {nome} na linha {top}: out/bloco_formato.json e out/bloco_valores.json")


if __name__ == "__main__":
    main(*map(int, sys.argv[1:4]))
