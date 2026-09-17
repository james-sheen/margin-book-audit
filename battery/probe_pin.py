#!/usr/bin/env python3
"""Exercise the FLOOR of every declared range, not just its ceiling.

A RANGE IS A CLAIM ABOUT EVERY RELEASE INSIDE IT. Ordinary CI resolves each
dependency to the newest release its range admits, so the range is only ever
tested at one end -- and the untested end is the floor, which is exactly where a
consumer with an older install lands.

WHAT THIS DOES. It reads the ranges from `pyproject.toml` rather than naming
versions here (a version written into a probe keeps passing after somebody
raises the real one), installs each release the range admits plus the highest
release BELOW it, and runs the suite against each. The one below the floor is
the control: if it passes too, the floor is higher than anything here measured
and saying so is the honest outcome.

IT FAILS ON A COULD-NOT-RUN as well as on a refutation. If the index is
unreachable the answer is not *the pins are fine*.

Needs network. Run it on a pin change; do not re-read a previous result.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def declared_ranges() -> dict:
    text = PYPROJECT.read_text(encoding="utf-8")
    out = {}
    # THE COMMA IS PART OF THE SPECIFIER. `>=0.1.8,<0.2` is one range, and a
    # pattern that stops at the comma matched nothing at all here -- the probe
    # printed an empty list and exited 0, which reads exactly like a clean
    # sweep. A derivation that finds nothing must not look like a pass.
    for name, spec in re.findall(r'"([a-z0-9][a-z0-9-]*)([<>=!~][^"]*)"', text):
        if spec.strip():
            out[name] = spec.strip()
    return out


def _versions(dist: str) -> list:
    url = f"https://pypi.org/pypi/{dist}/json"
    with urllib.request.urlopen(url, timeout=30) as handle:
        data = json.load(handle)

    def key(v):
        return tuple(int(p) for p in re.findall(r"\d+", v))

    return sorted(data["releases"], key=key)


def _admits(version: str, spec: str) -> bool:
    try:
        from packaging.specifiers import SpecifierSet
    except ImportError:
        print("packaging is required: pip install packaging", file=sys.stderr)
        raise SystemExit(2)
    return version in SpecifierSet(spec)


def sweep(dist: str, spec: str) -> int:
    every = _versions(dist)
    inside = [v for v in every if _admits(v, spec)]
    if not inside:
        print(f"{dist}{spec}: the range admits NOTHING on the index")
        return 1
    below = [v for v in every if v not in inside and
             tuple(int(p) for p in re.findall(r"\d+", v))
             < tuple(int(p) for p in re.findall(r"\d+", inside[0]))]
    control = below[-1] if below else None

    failures = 0
    for version in inside + ([control] if control else []):
        role = "control (below the floor)" if version == control else "in range"
        code = _run_suite(dist, version)
        verdict = "pass" if code == 0 else f"FAIL({code})"
        print(f"  {dist}=={version:<10} {role:<26} {verdict}")
        if version != control and code != 0:
            failures += 1
        if version == control and code == 0:
            print(f"    ^ the control PASSED. The floor is higher than this "
                  f"probe measured -- it is not evidence the floor is wrong, "
                  f"and it is not evidence the floor is needed either.")
    return failures


def _run_suite(dist: str, version: str) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        env = subprocess.run(
            [sys.executable, "-m", "venv", tmp], capture_output=True)
        if env.returncode:
            print(f"    could not create an environment: {env.stderr[-300:]!r}")
            return 90
        pip = pathlib.Path(tmp) / "bin" / "pip"
        py = pathlib.Path(tmp) / "bin" / "python"
        install = subprocess.run(
            [str(pip), "install", "-q", "-e", str(ROOT), f"{dist}=={version}",
             "pytest"], capture_output=True, text=True)
        if install.returncode:
            print(f"    install failed: {install.stderr.strip()[-300:]}")
            return 91
        return subprocess.run(
            [str(py), "-m", "pytest", str(ROOT / "tests"), "-q"],
            capture_output=True, cwd=str(ROOT)).returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sweep", action="store_true",
                        help="install and run every release each range admits")
    args = parser.parse_args(argv)

    ranges = declared_ranges()
    if not ranges:
        print("no ranges found in pyproject.toml -- the derivation is broken, "
              "and an empty sweep is not a clean sweep", file=sys.stderr)
        return 2
    if not args.sweep:
        for name, spec in sorted(ranges.items()):
            print(f"{name}{spec}")
        print("\npass --sweep to exercise them. Needs network.")
        return 0

    failures = 0
    for name, spec in sorted(ranges.items()):
        print(f"{name}{spec}")
        failures += sweep(name, spec)
    print("\n" + ("every release in every declared range passes"
                  if not failures else f"{failures} release(s) in range FAILED"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
