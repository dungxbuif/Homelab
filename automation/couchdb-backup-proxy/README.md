# CouchDB backup proxy

Private Pi5-side gateway for the VM100/VM110 native CouchDB backup pull. It accepts
only `GET`/`HEAD`, requires a separate bearer token, permits only the inventory
databases and backup paths, and forwards to CouchDB with the admin credential
kept on Pi5. It is bound to the Pi5 LAN address only and is never routed
through Traefik, Rathole, or a public domain.

Required runtime settings are supplied through secret files or the environment:
`COUCHDB_USER_FILE`, `COUCHDB_PASSWORD_FILE`, `BACKUP_PROXY_TOKEN_FILE`,
`COUCHDB_ALLOWED_DATABASES`, `ALLOWED_CLIENT_CIDRS`, and `COUCHDB_URL`.

The production allowlist must contain both backup workers as exact host CIDRs:
`10.10.0.31/32,10.10.0.32/32`. Keep the proxy LAN-only; do not publish it
through Traefik, Rathole, or a public hostname.
