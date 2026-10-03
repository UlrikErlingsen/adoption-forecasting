# Security policy

## Supported version

Security fixes are applied to the latest release on the `main` branch.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability involving code execution, file handling, dependency compromise, or disclosure of customer data. Email [code.modular578@passmail.net](mailto:code.modular578@passmail.net) with the subject `[AdoptSignal security]`. If GitHub private vulnerability reporting is enabled for the public repository, you may instead use its [private security advisory form](https://github.com/UlrikErlingsen/adoption-forecasting/security/advisories/new). Include the affected version, reproduction steps, impact, and any suggested mitigation.

## Scope and operating advice

Run locally, Adopt Signal has no built-in limits on file size, rows or cells (Streamlit's upload cap is 10,000 MB; memory is the real limit). A public demo (`SIGNAL_PUBLIC=1`) caps uploads at 50 MB, 1,000,000 rows, 10,000,000 cells, 400 MB of expanded workbook and 400 periods of history. It does not accept serialized Python models or execute spreadsheet macros. This reduces risk but does not make an internet deployment safe by itself. Hosted operators remain responsible for authentication, TLS, patching, access logging, isolation, backups, and data retention, and may choose a lower upload limit.
