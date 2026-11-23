# Report semanal de leads · Grupo Concept

Envia todas as segundas-feiras às 08:00 (hora de Lisboa) o report de leads de franchising
(BodyConcept e DepilConcept) para o Grupo Concept: PDF em anexo e link para a folha no Google Sheets.

## Como funciona

1. **Segunda de madrugada:** o Claude atualiza a folha do report até domingo e grava os valores em
   `data/report.json` (procedimento em `docs/atualizacao-semanal.md`).
2. **Segunda às 08:00:** o GitHub Actions (`.github/workflows/weekly-report.yml`) corre
   `send_report.py`, que gera o PDF a partir de `data/report.json` e envia o email.
3. **Proteção:** se os dados não forem até domingo, o cliente não recebe nada e segue um alerta
   para o endereço remetente.

## Configuração (uma vez)

Em *Settings → Secrets and variables → Actions*, criar dois segredos:

- `GMAIL_USER`: o endereço Gmail que envia o report
- `GMAIL_APP_PASSWORD`: uma palavra-passe de aplicação dessa conta (exige validação em dois passos)

Destinatários e assinatura estão em `config.json`.

## Testar

*Actions → Report semanal Grupo Concept → Run workflow*, modo `teste`: envia o email só para o
remetente. O modo `real` envia para o cliente.

Localmente: `pip install -r requirements.txt && SO_PDF=1 python send_report.py` gera o PDF em `out/`.
