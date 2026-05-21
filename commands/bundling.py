from __future__ import annotations

import shutil
import warnings
from pathlib import Path

import yaml
from invoke.collection import Collection
from invoke.tasks import task


MANIFEST_NAME = "manifest.yml"
DEFAULT_TARGET = "v1"


def _collect_includes(datagrowth: Path, patterns: list[str]) -> set[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        paths = sorted(
            p for p in datagrowth.glob(pattern)
            if p.is_file() and p.name != "__init__.py" and "__pycache__" not in p.parts
        )  # glue __init__.py: maintain under bundle only; skip bytecode dirs
        if not paths:
            warnings.warn(f"Include pattern matched no files: {pattern!r}", stacklevel=2)
        for path in paths:
            files.add(path.resolve())
    return files


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def build_bundle(repo: Path, bundle_root: Path) -> None:
    bundle_root = bundle_root.resolve()
    manifest_path = bundle_root / MANIFEST_NAME

    # --- Load manifest ---
    with manifest_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Manifest root must be a mapping: {manifest_path}")

    # --- Includes and renames ---
    includes = data.get("includes") or []
    if not isinstance(includes, list):
        raise TypeError("includes must be a list of glob patterns")
    raw_renames = data.get("renames")
    if raw_renames is None:
        renames: dict[str, str] = {}
    elif not isinstance(raw_renames, dict):
        raise TypeError("renames must be a mapping of source -> dest paths")
    else:
        renames = {str(k).replace("\\", "/"): str(v).replace("\\", "/") for k, v in raw_renames.items()}

    # --- Source and output roots (cwd is assumed to be the repo root) ---
    datagrowth = (repo / "datagrowth").resolve()
    if not datagrowth.is_dir():
        raise FileNotFoundError(f"Missing datagrowth package directory: {datagrowth}")

    # --- Files matched by include globs (under datagrowth/) ---
    include_files = _collect_includes(datagrowth, [str(p) for p in includes])

    print(f"Bundle output: {bundle_root.relative_to(repo)}")
    print("Includes:")
    # --- Copy includes to default destinations; skip sources that are only handled by renames ---
    for path in sorted(include_files, key=lambda p: str(p)):
        rel = path.relative_to(datagrowth).as_posix()
        if rel in renames:
            continue
        dest = bundle_root.joinpath(*Path(rel).parts)
        _copy_file(path, dest)
        print(f"  datagrowth/{rel} -> {dest.relative_to(repo)}")

    # --- Copy explicit renames (__init__.py allowed here; includes still skip it implicitly) ---
    rename_pairs = sorted(renames.items(), key=lambda item: item[0])
    if rename_pairs:
        print("Renames:")
    for src_rel, dest_rel in rename_pairs:
        src = datagrowth / src_rel
        if not src.is_file():
            raise FileNotFoundError(f"Rename source missing: {src}")
        dest = bundle_root / dest_rel
        _copy_file(src, dest)
        print(f"  datagrowth/{src_rel} -> {dest.relative_to(repo)}")

    # --- Optional requirements file into the bundle ---
    req = data.get("requirements")
    if req:
        if not isinstance(req, dict):
            raise TypeError("requirements must be a mapping with copy_from and dest")
        copy_from = req.get("copy_from")
        dest_name = req.get("dest", "requirements.txt")
        if not copy_from:
            raise ValueError("requirements.copy_from is required when requirements is set")
        src_req = (repo / copy_from).resolve()
        if not src_req.is_file():
            raise FileNotFoundError(f"Requirements source missing: {src_req}")
        req_dest = bundle_root / dest_name
        _copy_file(src_req, req_dest)
        print("Requirements:")
        print(f"  {src_req.relative_to(repo)} -> {req_dest.relative_to(repo)}")


def clean_bundle(bundle_root: Path) -> None:
    if not bundle_root.is_dir():
        return
    for path in bundle_root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "__init__.py":
            continue
        if path.suffix.lower() == ".md":
            continue
        if path.name == MANIFEST_NAME:
            continue
        path.unlink()


@task(help={
    "target": (
        f"Bundle directory under repo root (default: {DEFAULT_TARGET}); "
        f"manifest is <target>/{MANIFEST_NAME}"
    ),
})
def build(ctx, target: str = DEFAULT_TARGET) -> None:
    """Copy datagrowth subset and optional requirements into the bundle per manifest.yml."""
    del ctx
    repo = Path.cwd()
    bundle_root = (repo / target).resolve()
    manifest_path = bundle_root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    build_bundle(repo, bundle_root)


@task(help={
    "target": f"Bundle directory to clean (default: {DEFAULT_TARGET})",
})
def clean(ctx, target: str = DEFAULT_TARGET) -> None:
    """Remove bundled files under the target except __init__.py, *.md, and manifest.yml."""
    del ctx
    clean_bundle((Path.cwd() / target).resolve())


bundling_collection = Collection("bundle", build, clean)
