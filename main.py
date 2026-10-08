"""Triagem IMAP com download controlado de anexos."""
from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import smtplib
from email.header import decode_header
from email.message import EmailMessage
from pathlib import Path


def decode(value: str | None) -> str:
    if not value:
        return ""
    part, charset = decode_header(value)[0]
    return part.decode(charset or "utf-8", errors="replace") if isinstance(part, bytes) else part


def reply(config: dict, recipient: str) -> None:
    smtp = config["reply"]["smtp"]
    user, password = os.getenv(smtp["username_env"]), os.getenv(smtp["password_env"])
    if not user or not password:
        raise RuntimeError("Credenciais SMTP ausentes nas variaveis de ambiente configuradas.")
    message = EmailMessage()
    message["Subject"] = "Confirmação de recebimento"
    message["From"], message["To"] = smtp["from"], recipient
    message.set_content(config["reply"]["message"])
    with smtplib.SMTP(smtp["host"], smtp["port"]) as client:
        client.starttls()
        client.login(user, password)
        client.send_message(message)


def unique_target(folder: Path, name: str) -> Path:
    candidate, counter = folder / Path(name).name, 1
    while candidate.exists():
        candidate = folder / f"{Path(name).stem}-{counter}{Path(name).suffix}"
        counter += 1
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--apply", action="store_true", help="autoriza conexao IMAP e download")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if not args.apply or config.get("dry_run", True):
        print("Simulacao: configure filtros e use --apply com dry_run=false para conectar ao IMAP.")
        return
    imap = config["imap"]
    user, password = os.getenv(imap["username_env"]), os.getenv(imap["password_env"])
    if not user or not password:
        raise RuntimeError("Credenciais de e-mail ausentes nas variaveis de ambiente configuradas.")
    with imaplib.IMAP4_SSL(imap["host"]) as client:
        client.login(user, password)
        client.select(imap["folder"])
        status, ids = client.search(None, "ALL")
        if status != "OK":
            raise RuntimeError("Falha ao pesquisar a caixa de e-mail.")
        destination = Path(config["download_dir"])
        destination.mkdir(parents=True, exist_ok=True)
        allowed = set(config["allowed_extensions"])
        for message_id in ids[0].split():
            _, payload = client.fetch(message_id, "(RFC822)")
            message = email.message_from_bytes(payload[0][1])
            sender = message.get("From", "").lower()
            subject = decode(message.get("Subject")).lower()
            if imap["from_contains"].lower() not in sender or imap["subject_contains"].lower() not in subject:
                continue
            for part in message.walk():
                filename = decode(part.get_filename())
                if filename and Path(filename).suffix.lower() in allowed:
                    target = unique_target(destination, filename)
                    target.write_bytes(part.get_payload(decode=True))
                    print(f"Anexo salvo: {target}")
            if config["reply"].get("enabled", False):
                reply(config, message.get("Reply-To") or message.get("From", ""))
                print(f"Resposta enviada para: {message.get('Reply-To') or message.get('From')}")


if __name__ == "__main__":
    main()
