# Supabase PostgreSQL CA

`supabase-root-2021-ca.crt` is the public Supabase Root 2021 CA certificate
downloaded by the project operator from the authenticated Supabase dashboard's
Database Settings → SSL Configuration page. It is not a credential.

Certificate identity checked before inclusion:

- Subject and issuer: `Supabase Root 2021 CA` (self-signed root).
- Validity: 2021-04-28 through 2031-04-26.
- Basic constraint: critical `CA:TRUE`.
- Key usage: certificate signing and CRL signing.
- SHA-256 fingerprint over DER: `807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa`.
- SHA-256 over the complete approved PEM file: `700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7`.

The fingerprint matches the independently published fingerprint for the
dashboard-provided Supabase Root 2021 CA. Supabase documents that the project
CA is available in Database Settings and is needed for `verify-full`:
<https://supabase.com/docs/guides/platform/ssl-enforcement>.

The scheduled worker pins both digests, rejects extra certificates or trailing
data, and loads the single verified root without using the operating-system CA
bundle. The bootstrap holds an immutable anonymous descriptor of those exact
bytes through worker execution and configures `sslmode=verify-full` and
`sslrootcert`. The approved connection hostname is validated before the worker
starts, so libpq performs hostname validation against the pinned root.
