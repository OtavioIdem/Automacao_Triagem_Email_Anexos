# Triagem de e-mails e anexos

Localiza mensagens de uma caixa IMAP por remetente, assunto e período; baixa
anexos permitidos e, opcionalmente, envia uma resposta padronizada via SMTP.

## Planejamento

1. Definir filtros mínimos para evitar tratar e-mails indevidos.
2. Fazer a prévia de mensagens encontradas.
3. Baixar apenas extensões permitidas e registrar a origem no log.
4. Habilitar resposta automática somente após homologação.

## Execução

```powershell
Copy-Item config.example.json config.json
python main.py --config config.json
python main.py --config config.json --apply
```

Sem `--apply`, a automação não abre conexão IMAP/SMTP.
