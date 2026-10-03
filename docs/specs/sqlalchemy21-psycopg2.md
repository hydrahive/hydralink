# AgentLink: Datenbanktreiber fest auf psycopg2

## Problem

Seit SQLAlchemy 2.1 (veröffentlicht 24.09.2026) bedeutet eine Adresse
`postgresql://…` den Treiber **psycopg (Version 3)**, nicht mehr psycopg2.
AgentLink installiert nur `psycopg2-binary`, `requirements.txt` erlaubt aber
`sqlalchemy>=2.0.36,<3`. Jede frische Installation und jeder Neubau der
Python-Umgebung bekommt deshalb SQLAlchemy 2.1.x, und das Backend bricht beim
Start mit `ModuleNotFoundError: No module named 'psycopg'` ab.

Gefunden am 03.10.2026 auf tills-master-wks: Nach dem Upgrade auf Ubuntu 26.04
hat das HydraHive-Update die venv mit `--clear` neu gebaut, danach startete
agentlink.service nicht mehr. Prod (2.0.52) und hydratest (2.0.36) laufen nur,
weil ihre venvs älter sind.

## Optionen

- **A: SQLAlchemy unter 2.1 festnageln.** Kleinste Änderung, verschiebt das
  Problem aber nur. Spätestens bei einem Python, für das 2.0 kein Wheel mehr hat,
  bricht es wieder.
- **B: psycopg (3) zusätzlich installieren.** Zwei Treiber im Paket, das
  Verhalten hängt dann von der SQLAlchemy-Version ab.
- **C: Treiber explizit `postgresql+psycopg2://`, im Code UND im Installer.**
  Unabhängig von der SQLAlchemy-Version. Der Code normalisiert auch bestehende
  env-Dateien mit `postgresql://`, die der Installer früher geschrieben hat.
  Ein Update des Codes reicht, ohne dass der Installer erneut laufen muss.

## Entscheidung: C

- `agentlink/backend/database.py`: `engine_url()` macht aus `postgresql://`
  bzw. `postgres://` die Adresse `postgresql+psycopg2://`. Explizit gesetzte
  Treiber (`postgresql+…://`) und andere Datenbanken bleiben unverändert.
- `installer/modules/20-agentlink.sh` schreibt `postgresql+psycopg2://`.
- `migrate_phase5.py` und der matrix-notifier nutzen psycopg2 direkt und sind
  nicht betroffen.

## Akzeptanz

- Ein Test mit echtem SQLAlchemy 2.1: `create_engine(engine_url("postgresql://…"))`
  gelingt und nutzt den Treiber psycopg2. Ohne Fix wird der Test rot.
- Fehler-Injektion: Ohne Normalisierung oder mit falschem Installer-Schema
  wird jeweils ein Test rot.
- Auf hydratest echt geprüft: venv mit SQLAlchemy 2.1 neu gebaut, agentlink
  startet und antwortet.
