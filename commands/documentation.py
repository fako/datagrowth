import json
import re
import shutil
from pathlib import Path

from invoke.collection import Collection
from invoke.tasks import task

from datagrowth.version import VERSION


VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


@task
def build(ctx):
    """
    Builds the project documentation using Sphinx.
    """
    with ctx.cd("docs"):
        ctx.run("make html", echo=True, pty=True)


@task(help={
    "version": "Published docs version (for example 0.20.6). Defaults to package version.",
    "built_version": "Built docs folder in docs/_build/html to use as documentation source. Defaults to version.",
    "target_root": "Directory where publishable docs site is assembled.",
    "existing_root": "Optional existing gh-pages checkout to merge known versions from.",
    "is_latest": "Whether the published version should be marked as latest. Defaults to True",
})
def publish(ctx, version=None, built_version=None, target_root="dist/site", existing_root="gh-pages-existing",
            is_latest: bool = True):
    """
    Assembles a publishable static docs site with versioned folders and latest redirect.
    """
    del ctx

    publish_version = version or VERSION
    source_version = built_version or publish_version
    docs_source = Path("docs") / "_build" / "html" / source_version
    if not docs_source.exists():
        raise FileNotFoundError(f"Docs source directory not found: {docs_source}")

    site_root = Path(target_root)
    site_root.mkdir(parents=True, exist_ok=True)
    target = site_root / publish_version
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(docs_source, target)

    if is_latest:
        latest = site_root / "latest"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(docs_source, latest)

    redirect = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url=./latest/">
    <title>Redirecting...</title>
  </head>
  <body>
    <p>Redirecting to latest docs...</p>
  </body>
</html>
"""
    (site_root / "index.html").write_text(redirect)

    versions = set()
    for root in (Path(existing_root), site_root):
        if root.exists():
            root_versions = [path.name for path in root.iterdir() if path.is_dir() and VERSION_PATTERN.match(path.name)]
            versions.update(root_versions)
    versions.add(publish_version)
    sorted_versions = sorted(versions, key=lambda value: tuple(int(part) for part in value.split(".")))
    (site_root / "versions.json").write_text(json.dumps(sorted_versions, indent=2))


docs_collection = Collection("docs", build, publish)
