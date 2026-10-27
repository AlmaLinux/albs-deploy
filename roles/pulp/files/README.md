# TLS certificate drop-in (prod / any HTTPS environment)

`roles/pulp/tasks/tls.yml` copies the webserver cert + key from here into the
`pulp_web` container when `pulp_https: true` and `pulp_tls_cert_src` /
`pulp_tls_key_src` point at these filenames (the prod default).

Place your PEM files here — they are **gitignored** and must never be committed:

    roles/pulp/files/pulp_webserver.crt    # server cert + intermediate chain
    roles/pulp/files/pulp_webserver.key    # private key

If both are absent while HTTPS is on, the play fails fast (no self-signed
fallback in prod). For a non-production self-signed cert instead, leave these
unset and set `pulp_tls_generate_self_signed: true`.

## Database fields encryption key (existing-deployment migration)

When `pulp_db_encryption_key_src` points here (prod default), drop the
**original** Fernet key from the deployment you're migrating:

    roles/pulp/files/database_fields.symmetric.key

Also gitignored. This key decrypts already-encrypted DB fields (remote
credentials, etc.) — a new or wrong key makes them permanently unreadable, so it
must be the exact key from the source deployment. For a brand-new deployment
instead, leave `pulp_db_encryption_key_src` empty and keep
`pulp_generate_db_encryption_key: true` to have the role generate one.

## Vendored pulpcore source patches (`export.py`, `datarepair.py`)

These are locally-patched copies of whole pulpcore modules. Unlike the secrets
above they **are committed** — source we carry until the fixes land upstream.
When `pulp_source_patches_enabled: true`, `build_image.yml` stages every entry
of `pulp_source_patches` (`{src, dest}`) into the image build context and
`Containerfile.j2` `COPY`s each one over the image's copy at its `dest`.

| File            | Upstream module                    | What it changes |
|-----------------|------------------------------------|-----------------|
| `export.py`     | `pulpcore/app/tasks/export.py`     | Sets exported package file timestamps from the package metadata; allows exporting into an existing directory. (Exporting streamed `file://` content is already upstream in 3.114.1.) |
| `datarepair.py` | `pulpcore/app/tasks/datarepair.py` | `repair_7272` / `repair_7465` (`pulpcore-manager datarepair-7272` / `-7465`) load one RepositoryVersion at a time, compare `content_ids` by count first and then stream relationship ids, and in 7465 only load versions whose cache is missing — so the repair no longer OOMs on repositories with many versions or huge `content_ids` arrays. |

Each file vendors the whole module, so the set is pinned to ONE pulpcore version
(`pulp_source_patches_pulpcore_version`, currently `3.114.1`). The build asserts
that version equals `pulp_image_tag` and fails if they drift — so on any image
bump you must re-derive every file from the new upstream and update the version
var (or disable the patches).

To add another patch: drop the patched module here and append
`{src: <file>, dest: <path inside image>}` to `pulp_source_patches` in
`roles/pulp/defaults/main.yml`.

### License

pulpcore is licensed under GPL-2.0-or-later, and so are these files as works
based on it — unlike the rest of this repository, which is MIT. Keep for every
vendored module:

- the `SPDX-License-Identifier: GPL-2.0-or-later` header and the note naming
  the upstream module and pulpcore version it is based on;
- the list of our modifications with the year, updated whenever the file
  changes (GPLv2 §2a);
- `COPYING.pulpcore`, the GPLv2 text shipped with pulpcore.

### Filesystem exporter and hardlinks (cross-device gotcha)

The filesystem exporter hardlinks (`os.link`) each artifact from `MEDIA_ROOT`
into the export directory. A hard link cannot cross filesystems, so the artifact
store and the export dir **must be on the same mounted filesystem inside the
container**, or every export fails with `[Errno 18] Invalid cross-device link`.

`export.py` has a `st_dev` guard that falls back to copy when the two are on
different devices — but it is **defeated on NFS/EFS**: two separate bind mounts
of the same NFS export become two mounts (separate superblocks) inside the
container yet report the SAME `st_dev`, so the guard thinks they match and still
attempts the hardlink. The fix is at the mount layer: bind-mount the shared
parent ONCE and place `DEPLOY_ROOT` (hence `MEDIA_ROOT`) and the export dir under
it — see the shared-parent layout in `group_vars/prod.yml`
(`pulp_storage_mount` / `pulp_deploy_root_host`).

## pulp_container token-auth keypair (optional)

When `pulp_token_public_key_src` / `pulp_token_private_key_src` point here (prod
default), drop the existing ES256 keypair:

    roles/pulp/files/token_public_key.pem
    roles/pulp/files/token_private_key.pem

Gitignored (`*.pem`). Only needed if token auth is enabled, or to mirror an
existing deployment. If you don't have or need them, set both
`pulp_token_*_key_src` vars to `""`.
