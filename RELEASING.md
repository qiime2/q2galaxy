# Releasing q2galaxy and Galaxy wrappers

q2galaxy releases independently of the QIIME 2 distribution release cycle.
The complete release path has three stages.

## 1. Publish q2galaxy

Create and publish a GitHub release whose tag is the desired q2galaxy version.
The `Publish to PyPI` workflow builds the wheel and source distribution with
`uv build --no-sources`, then publishes them with trusted publishing via
`uv publish --trusted-publishing always`.

Before the first release, configure q2galaxy as a PyPI trusted publisher. The
GitHub environment name used by the workflow is `pypi`; no long-lived PyPI
token is needed.

## 2. Build the runtime and render Galaxy tools

Run the `Render Galaxy Tools` workflow manually in the `galaxy-tools`
repository. Supply:

- `qiime2_image`: the released QIIME 2 distribution image. Prefer a digest,
  for example `quay.io/qiime2/amplicon@sha256:...`.
- `q2galaxy_version`: the version just published to PyPI.
- `runtime_image`: the destination Quay repository.
- `runtime_tag`: a readable tag for this QIIME 2/q2galaxy combination.

The workflow uses the runtime Dockerfile maintained in `galaxy-tools` to layer
only the selected q2galaxy wheel onto the coherent QIIME 2 environment. It
pushes the runtime image, obtains its immutable digest, and then runs this
command inside that image:

```text
q2galaxy template distribution \
  --container quay.io/qiime2/q2galaxy-runtime@sha256:... \
  --clean \
  distros.yaml .
```

That one command renders the builtin and plugin wrapper XML, embeds the exact
runtime image digest, creates the per-suite `.shed.yml` files, and creates the
distribution collection metadata. The existing `distros.yaml` schema remains
supported. `--clean` removes only the generated `tools/` and
`tool_collections/` trees before recreating them.

The Galaxy workflow requires `QUAY_USERNAME`, `QUAY_PASSWORD`, and the existing
`Q2D2_TOKEN` repository secrets. The runtime repository must be publicly
pullable by Galaxy workers.

## 3. Release through galaxy-tools

The render workflow opens one PR containing the tools and their collections.
After it is merged, the Galaxy workflow deploys the changed tool repositories
first and deploys the collections only after all of those uploads succeed.

The runtime image does not need to discover its own tag or digest. The workflow
passes the canonical digest explicitly to the renderer, so a mutable local tag
cannot accidentally enter a wrapper.
