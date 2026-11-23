# Atualização semanal do report (segunda-feira, antes das 08:00)

Procedimento para o Claude seguir todas as segundas-feiras de manhã. O objetivo é deixar a folha
do report atualizada até domingo e gravar `data/report.json` neste repositório. O envio do email
é feito pelo GitHub Actions às 08:00; **não enviar nenhum email a partir daqui**.

## Ficheiros e contas

- Report (Google Sheets): `1mjn_qNvP0_-JEC_Pb516U_yH5kmVUjd43shs5TO1EII`
  - Abas: `Report`, `Curva de leads`, `Dados Meta`, `Dados Google Ads`, `Dados GA4`, `Leads`
- Registo de leads (Google Sheets, só leitura): `1lfTdEZlUaSkEypMJUEfNHT3ZqYJbZS2F1uIgshTQmnQ`
  - Abas: `Body Concept` e `Depil Concept`; datas em formato americano (`11/16/26 04:34PM`)
- Leitura e escrita das folhas: Zapier, app Google Sheets, pedidos diretos à API
  (`_zap_raw_request`), ligação "Google Sheets dx.mikeper@gmail.com #2".
- Windsor:
  - Google Ads: conector `google_ads`, conta `983-032-9669` (só BodyConcept)
  - GA4: conector `googleanalytics4`, contas `559326223` (Body Concept) e `559332522` (Depil Concept)
  - Meta: conector `facebook`, filtro `account_name = "Franchising BC e DC"`

## Passos

1. **Período.** Fim = ontem (domingo). O início (`Report!B2`) não muda.
2. **Ler o estado atual** das quatro abas de dados e ver a última data de cada uma.
3. **Dados Meta** (`date, campaign, spend, impressions, clicks, actions_lead`): acrescentar as linhas
   dos dias em falta. Marca: campanha com `BODY` → BodyConcept; com `DEPIL` → DepilConcept.
4. **Dados Google Ads** (`date, campaign, spend, impressions, clicks, conversions`): acrescentar os
   dias em falta, marca BodyConcept. Se uma campanha mudou de nome, atualizar o nome nas linhas antigas.
5. **Dados GA4** (`date, account_name, session_source_medium, sessions`, filtro `organic`):
   acrescentar só linhas de origem orgânica.
6. **Leads.** Acrescentar as leads novas do registo (ignorar linhas sem nome). Colunas:
   data e hora, marca, nome, canal, qualidade, concelho.
   - **Canal:** cruzar a hora da lead com as visitas a `/obrigado/` no GA4
     (`date_hour_minute, session_source_medium, page_path`, mesmo minuto ou o seguinte).
     `google / cpc` → Google Adwords; `fb|ig|an / paid` → Meta Business; `organic` e tráfego direto → Orgânico.
     Sem visita registada: usar o canal mais provável pelas sessões dessa hora.
   - **Qualidade:** `Spam / teste` quando o nome não bate com o email, o telefone é inválido ou
     negativo, a localidade não é portuguesa ou é uma morada, e a hora é de madrugada via Google Ads.
     `Válida` quando nome, email e telemóvel português são coerentes. `Por verificar` nos casos duvidosos.
   - Leads de formulário Meta (`actions_lead` > 0) sem linha no registo: acrescentar como
     "Lead formulário Meta (n)", canal Meta Business, qualidade Por verificar.
7. **Datas:** escrever datas como números de série (RAW) e copiar o formato da linha anterior
   (`copyPaste` com `PASTE_FORMAT`). A aba `Dados Meta` tem um filtro nas linhas 1 a 25: não usar
   essas linhas como origem do formato.
8. **Report:** atualizar `Report!B3` (fim do período), o título em `A1` e o nome do ficheiro
   ("Report Leads Franchising Grupo Concept · 20 Out a DD Mmm AAAA (simplificado)").
9. **Mês novo.** Se o fim do período entrar num mês sem bloco na aba Report, correr
   `python tools/add_month_block.py AAAA MM LINHA` (linha = início do último bloco + 10) e enviar
   os dois JSON gerados em `out/` (primeiro o de formato, depois o de valores).
10. **Verificar.** Reler `Report!A1:K` e `Curva de leads!A:E`: sem erros (`#REF!`, `#N/A`, ...),
    a soma das leads dos blocos igual ao número de linhas da aba Leads, e a última data da curva
    igual ao fim do período.
11. **Gravar `data/report.json`** e fazer commit e push para `main`:
    - `period_start`, `period_end`, `updated_at` em `AAAA-MM-DD`
    - `report_rows`: os valores de `Report!A1:K` tal como aparecem na folha
    - `curve`: uma linha por dia `["AAAA-MM-DD", válidas acumuladas, spam acumulado]`
    - Confirmar com `SO_PDF=1 python send_report.py` que o PDF é gerado sem erros.

## Se algo falhar

Se uma fonte de dados não responder ou os totais não baterem, **não alterar `data/report.json`**.
Sem dados até domingo, o GitHub não envia nada ao cliente e manda um alerta para o remetente.
