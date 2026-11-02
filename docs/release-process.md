# Release process and CI

How a release is made, what each workflow does, and how to undo a bad one. Short on purpose.

## Design

One shared kit in this repository, `packaging/kit/`, holds the logic. Each component repository holds only what is specific to it: `packaging/deb.sh` (what the package contains), `scripts/ci-test.sh` (its full test suite), `scripts/ci-smoke.sh` (the smoke test of the installed package), `VERSION`, `CHANGELOG.md`, and two thin caller workflows. The same scripts run on a developer machine and in CI.

| Kit script | Does |
|---|---|
| `build-deb.sh` | builds one `.deb` from a repository: version from `VERSION`, times clamped to `SOURCE_DATE_EPOCH` (the commit time), owner root:root, sorted lists, fixed compression, Debian changelog converted from `CHANGELOG.md` |
| `check-version.sh` | tag = `VERSION` = newest changelog section (and, here, `install.sh` and `versions.lock`) |
| `release-build.sh` | builds twice in different conditions, fails if any byte differs, writes the source tarball (`git archive`) and `SHA256SUMS` |
| `release-notes.sh` | notes from the changelog section plus the standing caveats |
| `ci-lint.sh` | shellcheck on every shell script, syntax check of every Python file |
| `ci-run-clean.sh`, `ci-install-test.sh` | install in a clean `ubuntu:24.04` (Docker in CI, a chroot where there is no Docker daemon), run the smoke test, remove, purge, assert nothing is left |
| `fetch-deps.sh`, `fetch-components.sh` | get dependency packages from their releases, or build them from `main` |
| `orchestrate.sh`, `update-lock.sh` | main repository only: check component releases against `versions.lock`, build the `sdht` meta package, assemble the release |
| `actionlint.sh` | lint the workflows with a pinned, hash-checked actionlint |

Reusable workflows, in this repository: `component-ci.yml` and `component-release.yml`. Each component's `ci.yml` and `release.yml` call them, pinned to a full commit SHA of this repository (`kit_ref` is the same SHA). A change to the kit therefore reaches a component only when you update that SHA in the component's two workflow files (Dependabot proposes it too).

### ci.yml (every push to main and every pull request)

1. `test`, on ubuntu-24.04 (the target) and ubuntu-22.04 (informational: it may fail without failing the run): shellcheck on every shell script, Python syntax, the repository's full test suite.
2. `package`, after `test`: build the `.deb`, lintian (errors and warnings fail), then in a clean `ubuntu:24.04` container: install, smoke test from the installed paths, `apt remove`, `apt purge`, assert nothing is left. Dependencies of the package (Roomtone needs `linux-theater-dsp`) are built from their `main` branch.

### release.yml (a tag matching `v*`; or by hand with `dry_run`)

1. `ci`: the whole of ci.yml again.
2. `check`: tag, `VERSION` and the newest changelog section agree.
3. `build`: the packages are built **twice** and compared; source tarball; `SHA256SUMS`.
4. `attest`: build-provenance attestation for every file (keyless, GitHub OIDC). Allowed to fail; the release notes say whether it worked.
5. `publish`: the only job with `contents: write`. `gh release create --prerelease --latest=false --verify-tag`.
6. `verify`: downloads the published assets, checks them against `SHA256SUMS`, installs the `.deb` in a clean `ubuntu:24.04`, runs the smoke test; in this repository it also runs `install.sh --dry-run` against the release.

`workflow_dispatch` with `dry_run` (the default for a manual start) does 1 to 4 and 6 with the build artifact and publishes nothing. A manual start without `dry_run` is refused: a real release always starts from a tag push.

### Main repository: orchestration

`release.yml` here builds the `sdht` meta package from `versions.lock`, checks that **every** component release it names exists and that its `.deb` has the pinned SHA256 (and matches that component's own `SHA256SUMS`), then publishes `install.sh`, `versions.lock`, the meta package, copies of the component packages and one `SHA256SUMS` as a pre-release. Everything `install.sh` downloads therefore comes from one release and one checksum file.

### Hardening

`permissions:` is `contents: read` at the top of every workflow and raised only where needed (`contents: write` on `publish`; `id-token` and `attestations` on `attest`). Third-party actions are pinned to full commit SHAs with the version in a comment (the SHAs were read from the actions' own repositories with `git ls-remote`). No `pull_request_target`, no self-hosted runners, no secrets: only the `GITHUB_TOKEN`. Concurrency groups stop two releases racing (`release`, not cancelled) and cancel superseded CI runs. Every job has a timeout; matrices have `fail-fast: false`. `.github/dependabot.yml` proposes action updates weekly. Nothing in any workflow opens a network listener except the status pages that the smoke tests start, which bind 127.0.0.1 and are checked.

## Cutting the next release

Releases are made in dependency order: the five components first, then this repository.

For each component repository:

1. Bump `VERSION` (for example `0.1.1`).
2. Add a section at the top of `CHANGELOG.md`: `## [0.1.1] - YYYY-MM-DD`, then bullet points. Say honestly what is untested.
3. Run `scripts/ci-test.sh` and the kit's build locally (`../Software-Defined-Home-Theatre/packaging/kit/build-deb.sh --out /tmp/dist`).
4. Commit, push, wait for ci.yml to go green on `main`.
5. Optional but recommended: start `release` by hand with `dry_run` (Actions tab, Run workflow).
6. Tag and push: `git tag -a v0.1.1 -m "v0.1.1" && git push origin v0.1.1`.
7. Watch the run (Actions tab, or `gh run watch`). It creates a pre-release.

Then here: `packaging/kit/update-lock.sh linux-theater-dsp=v0.1.1 Roomtone=v0.1.1 seekthumbs=v0.1.1 mpv-shelf=v0.1.1 mpv-object-audio=v0.1.1` (writes `versions.lock` from the real releases), set `VERSION`, the `RELEASE=` line in `install.sh`, a new section in `RELEASES.md`, commit, wait for green, tag `v0.1.1`.

## Promoting a pre-release to a stable release (manual, by the author)

The pipeline never does this and never marks anything "latest". When you have tried it on a spare machine and want to promote it:

```bash
gh release edit v0.1.1 --repo praveenchandrahas/Software-Defined-Home-Theatre --prerelease=false --latest
```

Do it per repository, and only after you have run the packages yourself.

## Rolling back a bad release

- **Not promoted yet (still a pre-release):** delete it and its tag, fix, tag again with a new version. `gh release delete v0.1.1 --cleanup-tag --yes`. A tag that was never relied on can be reused; a version that people may have downloaded should not be reused. Prefer `0.1.2`.
- **Installed somewhere:** `sudo apt install ./older.deb` installs an older version over it (`--allow-downgrades` if apt asks), or `sdht-setup uninstall` and `sudo apt purge` as above. Nothing in a package touches your data.
- **Promoted:** `gh release edit TAG --prerelease=true`, then publish a fixed version.

## Testing the pipeline itself

`bash packaging/kit/actionlint.sh` lints all workflows. `bash scripts/ci-test.sh` runs the main-repo tests, including the kit on a synthetic repository (byte-identical builds, version checks) and `install.sh` against a fake release. Before the first tag the workflows were run on `main` and by `workflow_dispatch` with `dry_run`.

## What the author has to do

Things this pipeline cannot or must not do: create a signing key and publish it (packages are unsigned), a Flathub, PPA or PyPI account (none is used), try the `.deb` files on a spare machine before the rig, and promote a pre-release by hand (above). Turning on branch protection, GitHub Pages, or any other repository setting was deliberately left alone.

## State of the first release (2026-11-02)

- The five component repositories each have a **v0.1.0 pre-release** (not "latest"). The author pushed the tags; the session that prepared the packaging could push branches but not tags (HTTP 403 from its git proxy, also for the API). Each tag run passed: tag/VERSION/changelog check, tests, build twice with identical SHA256, build-provenance attestation, release creation, and a final job that downloads the published files and checks them in a clean Ubuntu 24.04.
- `versions.lock` pins the five released .deb files by SHA256, each checked against its release's own SHA256SUMS.
- Ubuntu 22.04 is an informational CI job only; it fails in some repositories (older ffmpeg and python3-lupa than the tests assume). The cause was not chased because 22.04 is not a supported target.
- The main repository's v0.1.0 is pushed by the author the same way as the components: `git tag v0.1.0 && git push origin v0.1.0`.
- Lessons from the first CI runs, so they are not repeated: Docker's Ubuntu image leaves out `/usr/share/doc`, so nothing a test reads may be installed there; `apt purge` fails for a package that `remove` already erased (the kit uses `dpkg --purge`); the CI runner is not root, so tests that call `sudo` need a stub.
