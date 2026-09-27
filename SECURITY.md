# Security and scope

This is a single-user, local research application. Bind the API and observability UIs to loopback. Do not expose them publicly: application authentication, tenant isolation, and production credential management are not implemented.

The bundled datasets are synthetic. Do not submit sensitive production data to this version. Provider keys are read from environment variables and are not sent to the browser, SQL subprocess, reports, or traces. Model inputs go to the configured provider in live HTTP mode.

Generated SQL is restricted to allowed SELECT statements over synthetic tables. External DuckDB I/O is disabled. Process deadlines, result limits, and Compose limits reduce risk but are not a security proof or a hardened hostile-code execution service.

No source mutation, automatic GitHub publishing, or production repair is performed by the application. Candidate patches require external human review.

Report vulnerabilities privately through GitHub's security reporting feature if enabled, rather than posting secrets in issues.

