# Citation URL display policy

This is one display-only policy for backend citation records and frontend links.
The parity corpus is `shared/citation_url_fixtures.json`; Python and TypeScript
tests consume that same file and assert the same canonical output.

- Accept public-looking HTTPS DNS names with a valid explicit port, removing
  the default port 443 and lowercasing the host. Reject non-HTTPS schemes,
  malformed authorities, credentials, trailing-dot names, single-label hosts,
  localhost/local/internal names, and all IPv4/IPv6 literals. Rejecting public
  IP literals too keeps browser and backend URL parsing in the same subset.
- DNS names are ASCII only. Unicode and punycode IDN labels are rejected;
  percent-encoded UTF-8 is allowed in a path. A raw Unicode citation must be
  percent encoded before display.
- External paths use an explicit ASCII URI character set. Reject malformed
  percent escapes, invalid UTF-8 escapes, dot segments, encoded slashes,
  backslashes, and nested percent encoding that could normalize differently.
  A valid `%20` path escape is accepted. Queries and fragments allow valid
  percent escapes, but empty `?` and `#` delimiters are rejected.
- Internal citations are limited to repository-relative Markdown files below
  `docs/` or `knowledge_base/`. Empty, `.` and `..` path segments, encoded
  separators, absolute paths, and non-Markdown files are rejected.

This policy validates where a citation may be displayed. It does not fetch or
authorize fetching a URL and does not claim SSRF protection for any future
network fetcher. A future fetcher must separately validate DNS resolution and
the actual connected address at connection time.
