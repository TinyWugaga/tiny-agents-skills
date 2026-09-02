#!/usr/bin/env python3
"""零成本重跑 ACCEPTANCE-r2 E-3 checker 與 nonce 行為矩陣。"""
import ast
import contextlib
import hashlib
import io
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACCEPTANCE = os.path.join(HERE, "ACCEPTANCE-r2.md")
RECORD = os.path.join(HERE, "record.py")
EXPECTED_RECORD_SHA256 = "f59becd79d780873e021a3059464b3f3734f66355948c3b7bef1f4dc99dfe593"
EXPECTED_BASELINE_COMMIT = "b96f41049a3a736dab320ccc5e848ac872377c50"
EXPECTED_STATUS_LINES = 34
TARGET_NAME = "HARNESS_TRACE_MANIFEST_ORIGIN"
EXPECTED_RECORD_READS = [
    "HARNESS_CLI_FAILED",
    "HARNESS_JUDGE_MODEL",
    "HARNESS_RUN_ENDED",
    "HARNESS_RUN_STARTED",
    "HARNESS_SUBJECT_MODEL",
]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command, env=None):
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=env,
    )


def git_status():
    result = run(["git", "-C", ROOT, "status", "--short"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git status failed")
    return result.stdout.rstrip("\n")


def git_head():
    result = run(["git", "-C", ROOT, "rev-parse", "HEAD"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git rev-parse failed")
    return result.stdout.strip()


def baseline_is_ancestor():
    result = run([
        "git", "-C", ROOT, "merge-base", "--is-ancestor",
        EXPECTED_BASELINE_COMMIT, "HEAD",
    ])
    return result.returncode == 0


def tree_fingerprint(root):
    entries = []
    for directory, names, files in os.walk(root, followlinks=False):
        if directory == root and ".git" in names:
            names.remove(".git")
        names.sort()
        files.sort()
        for name in names + files:
            path = os.path.join(directory, name)
            relative = os.path.relpath(path, root)
            info = os.lstat(path)
            mode = stat.S_IMODE(info.st_mode)
            if os.path.islink(path):
                entries.append("%s|L|%o|%s" % (relative, mode, os.readlink(path)))
            elif os.path.isdir(path):
                entries.append("%s|D|%o" % (relative, mode))
            else:
                entries.append("%s|F|%o|%s" % (relative, mode, sha256_file(path)))
    digest = hashlib.sha256()
    for entry in sorted(entries):
        digest.update(entry.encode("utf-8") + b"\n")
    return digest.hexdigest(), len(entries)


def extract_checker(destination):
    with open(ACCEPTANCE, encoding="utf-8") as handle:
        document = handle.read()
    start_marker = "<!-- E3_CHECKER_START -->\n```python\n"
    end_marker = "\n```\n<!-- E3_CHECKER_END -->"
    start = document.find(start_marker)
    end = document.find(end_marker, start + len(start_marker))
    if start < 0 or end < 0:
        raise RuntimeError("E-3 checker markers missing")
    code = document[start + len(start_marker):end]
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(code + "\n")


def python_version(executable):
    result = run([executable, "-c", "import platform; print(platform.python_version())"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "cannot read Python version")
    return result.stdout.strip()


def checker_command(executable, checker, target, delete_ast_str):
    if not delete_ast_str:
        return [executable, checker, target]
    driver = (
        "import ast,runpy,sys; "
        "delattr(ast,'Str'); "
        "checker=sys.argv[1]; "
        "sys.argv=[checker,sys.argv[2]]; "
        "runpy.run_path(checker,run_name='__main__')"
    )
    return [executable, "-c", driver, checker, target]


def assert_checker_result(label, result, expected_status, expected_reads, expected_forbidden):
    lines = result.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError("%s emitted %d stdout lines" % (label, len(lines)))
    try:
        payload = json.loads(lines[0])
    except ValueError as exc:
        raise AssertionError("%s emitted invalid JSON: %s" % (label, exc))
    expected_keys = [
        "status", "target", "python", "all_env_reads", "forbidden_reads"
    ]
    if list(payload.keys()) != expected_keys:
        raise AssertionError("%s fields differ: %r" % (label, list(payload.keys())))
    expected_rc = {"clean": 0, "forbidden": 1, "error": 2}[expected_status]
    if result.returncode != expected_rc:
        raise AssertionError("%s exit %d != %d" % (label, result.returncode, expected_rc))
    if payload["status"] != expected_status:
        raise AssertionError("%s status %r != %r" % (label, payload["status"], expected_status))
    if payload["all_env_reads"] != expected_reads:
        raise AssertionError(
            "%s all_env_reads %r != %r" % (label, payload["all_env_reads"], expected_reads)
        )
    if payload["forbidden_reads"] != expected_forbidden:
        raise AssertionError(
            "%s forbidden_reads %r != %r"
            % (label, payload["forbidden_reads"], expected_forbidden)
        )
    if expected_status == "error":
        if not result.stderr.endswith("\n") or result.stderr.endswith("\\n"):
            raise AssertionError("%s stderr does not end with a real newline" % label)
    if not os.path.isabs(payload["target"]):
        raise AssertionError("%s target is not absolute" % label)
    return lines[0]


def fixture_matrix(temp_root):
    cases = [
        (
            "legal_os_environ_get",
            'import os\nVALUE = os.environ.get("%s")\n' % TARGET_NAME,
            "forbidden", [TARGET_NAME], [TARGET_NAME],
        ),
        (
            "legal_os_getenv",
            'import os\nVALUE = os.getenv("%s")\n' % TARGET_NAME,
            "forbidden", [TARGET_NAME], [TARGET_NAME],
        ),
        (
            "legal_os_environ_subscript",
            'import os\nVALUE = os.environ["%s"]\n' % TARGET_NAME,
            "forbidden", [TARGET_NAME], [TARGET_NAME],
        ),
        (
            "wrong_cache_get",
            'VALUE = cache.get("%s")\n' % TARGET_NAME,
            "clean", [], [],
        ),
        (
            "wrong_client_getenv",
            'VALUE = client.getenv("%s")\n' % TARGET_NAME,
            "clean", [], [],
        ),
        (
            "wrong_cfg_environ_subscript",
            'VALUE = cfg.environ["%s"]\n' % TARGET_NAME,
            "clean", [], [],
        ),
    ]
    variants = [
        "HARNESS_TRACE_MANIFEST_ORIGIN_BACKUP",
        "MY_TRACE_MANIFEST_ORIGIN",
        "TRACE_MANIFEST_ORIGIN_V2",
        "HARNESS_TRACE_MANIFEST_ORIGIN2",
    ]
    for index, variant in enumerate(variants, 1):
        cases.append((
            "similar_name_%d" % index,
            'import os\nVALUE = os.environ.get("%s")\n' % variant,
            "clean", [variant], [],
        ))
    cases.extend([
        (
            "comment_decoy",
            "# %s must not be read\nVALUE = 1\n" % TARGET_NAME,
            "clean", [], [],
        ),
        (
            "docstring_decoy",
            '"""%s must not be read."""\nVALUE = 1\n' % TARGET_NAME,
            "clean", [], [],
        ),
        (
            "checker_error",
            "def broken(:\n",
            "error", [], [],
        ),
    ])
    materialized = []
    fixture_dir = os.path.join(temp_root, "fixtures")
    os.makedirs(fixture_dir)
    for label, source, status, reads, forbidden in cases:
        path = os.path.join(fixture_dir, label + ".py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(source)
        materialized.append((label, path, status, reads, forbidden))
    materialized.append(("current_record", RECORD, "clean", EXPECTED_RECORD_READS, []))
    return materialized


BEHAVIOR_DRIVER = r'''
import ast
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
if os.environ.get("R2_DELETE_AST_STR") == "1":
    delattr(ast, "Str")
sys.path.insert(0, sys.argv[1])
import record

BASE = sys.argv[2]
N = "0123456789abcdef0123456789abcdef"
H = "a" * 64
IDS = ["v__a", "v__b"]


def snap():
    return {
        "recorded_at": "2026-09-03T00:00:00+08:00",
        "hash_schema": "v6",
        "hashes": dict((domain, H) for domain in record.REQUIRED_DOMAINS),
        "fixture_args": ["skills/x/fixtures.json"],
        "fixture_files": ["skills/x/fixtures.json"],
    }


def build(directory, man_nonce=N, trace_nonce=N, meta_nonces=None):
    raw = os.path.join(directory, "raw")
    os.makedirs(raw)
    nonces = meta_nonces or [N] * len(IDS)
    for index, row_id in enumerate(IDS):
        with open(os.path.join(raw, row_id + ".jsonl"), "w") as handle:
            handle.write('{"type":"system","subtype":"init","skills":["judgment"]}\n')
            handle.write('{"type":"result","subtype":"success","total_cost_usd":0.01}\n')
        meta = {"id": row_id, "exit_code": 0, "prompt": "p"}
        if nonces[index] is not None:
            meta["run_nonce"] = nonces[index]
        with open(os.path.join(raw, row_id + ".meta.json"), "w") as handle:
            json.dump(meta, handle)
        with open(os.path.join(raw, row_id + ".judge.json"), "w") as handle:
            json.dump({"overall": "PASS", "_cost_usd": 0.01}, handle)
    manifest = {"manifest_version": 2, "kind": "full", "start": snap(), "end": snap()}
    if man_nonce is not None:
        manifest["run_nonce"] = man_nonce
    with open(os.path.join(directory, "manifest.json"), "w") as handle:
        json.dump(manifest, handle)
    files = {}
    for name in sorted(os.listdir(raw)):
        if name.endswith((".jsonl", ".meta.json")):
            path = os.path.join(raw, name)
            with open(path, "rb") as handle:
                files[name] = hashlib.sha256(handle.read()).hexdigest()
    trace = {"recorded_at": "x", "algorithm": "sha256", "files": files}
    if trace_nonce is not None:
        trace["run_nonce"] = trace_nonce
    with open(os.path.join(directory, "trace-manifest.json"), "w") as handle:
        json.dump(trace, handle)
    fixtures = {"suite_name": "v", "fixtures": [
        {
            "id": row_id.split("__")[1],
            "category": "negative",
            "expected_route": {
                "judgment": False,
                "dispatch": False,
                "token-preflight": False,
            },
        }
        for row_id in IDS
    ]}
    fixtures_path = os.path.join(directory, "fixtures.json")
    with open(fixtures_path, "w") as handle:
        json.dump(fixtures, handle)
    return raw, fixtures_path


cases = [
    ("B-5.1_run_manifest_missing_nonce", {"man_nonce": None}, "legacy_diagnostic", False),
    ("B-5.2_trace_manifest_nonce_mismatch", {"trace_nonce": "f" * 32}, "legacy_diagnostic", False),
    ("B-5.3_meta_missing_nonce", {"meta_nonces": [N, None]}, "legacy_diagnostic", False),
    ("B-5.4_meta_nonce_mismatch", {"meta_nonces": [N, "b" * 32]}, "legacy_diagnostic", False),
    ("B-6_complete_nonce_chain", {}, "contract_evidence", True),
]
os.environ["HARNESS_TRACE_MANIFEST_ORIGIN"] = "contemporaneous"
results = []
for label, arguments, expected_class, expected_flag in cases:
    directory = tempfile.mkdtemp(prefix="behavior-", dir=BASE)
    try:
        raw, fixtures_path = build(directory, **arguments)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            rc = record.main(
                raw,
                "vrun",
                os.path.join(directory, "manifest.json"),
                fixtures_path,
            )
        with open(os.path.join(directory, "vrun.json")) as handle:
            document = json.load(handle)
        results.append({
            "case": label,
            "rc": rc,
            "evidence_class": document["evidence_class"],
            "is_contract_evidence": document["is_contract_evidence"],
            "trace_manifest_origin": document["provenance"].get("trace_manifest_origin"),
            "expected_class": expected_class,
            "expected_flag": expected_flag,
        })
    finally:
        shutil.rmtree(directory)
print(json.dumps(results, sort_keys=True, separators=(",", ":")))
'''


def run_behavior_profile(executable, driver_path, temp_root, delete_ast_str):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if delete_ast_str:
        env["R2_DELETE_AST_STR"] = "1"
    result = run([executable, driver_path, HERE, temp_root], env=env)
    if result.returncode != 0:
        raise AssertionError("behavior driver failed: %s" % result.stderr.strip())
    lines = result.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError("behavior driver emitted %d stdout lines" % len(lines))
    rows = json.loads(lines[0])
    for row in rows:
        if row["rc"] != 0:
            raise AssertionError("%s rc=%r" % (row["case"], row["rc"]))
        if row["evidence_class"] != row["expected_class"]:
            raise AssertionError("%s evidence class mismatch" % row["case"])
        if row["is_contract_evidence"] is not row["expected_flag"]:
            raise AssertionError("%s evidence flag mismatch" % row["case"])
    return rows


def command_path(name):
    return shutil.which(name)


def main():
    failures = []
    status_before = git_status()
    status_before_lines = 0 if not status_before else len(status_before.splitlines())
    record_before = sha256_file(RECORD)
    fingerprint_before, entries_before = tree_fingerprint(ROOT)
    head = git_head()

    print("ACCEPTANCE-r2 REGRESSION")
    print("repository=%s" % ROOT)
    print("repository_head=%s" % head)
    print("subject_baseline_commit=%s" % EXPECTED_BASELINE_COMMIT)
    print("record_sha256_before=%s" % record_before)
    print("git_status_lines_before=%d" % status_before_lines)
    print("tree_fingerprint_before=%s entries=%d" % (fingerprint_before, entries_before))

    if not baseline_is_ancestor():
        failures.append("subject baseline commit is not an ancestor of HEAD")
    if record_before != EXPECTED_RECORD_SHA256:
        failures.append("record.py hash mismatch before tests")
    if status_before_lines != EXPECTED_STATUS_LINES:
        failures.append("git status line count before tests is not 34")

    with tempfile.TemporaryDirectory(prefix="acceptance-r2-") as temp_root:
        checker = os.path.join(temp_root, "e3_checker.py")
        driver = os.path.join(temp_root, "behavior_driver.py")
        extract_checker(checker)
        with open(driver, "w", encoding="utf-8") as handle:
            handle.write(BEHAVIOR_DRIVER)
        fixtures = fixture_matrix(temp_root)

        profiles = [
            ("python3_path", command_path("python3"), "3.7.9", False),
            ("python3_system", "/usr/bin/python3", "3.9.6", False),
            ("python3_system_without_ast_Str", "/usr/bin/python3", "3.9.6", True),
        ]
        python314 = command_path("python3.14")
        if python314:
            profiles.append(("python3_14", python314, "3.14", False))

        for profile, executable, expected_version, delete_ast_str in profiles:
            if not executable or not os.path.exists(executable):
                failures.append("%s interpreter missing" % profile)
                continue
            version = python_version(executable)
            if not version.startswith(expected_version):
                failures.append("%s version %s != %s" % (profile, version, expected_version))
            print("PROFILE %s executable=%s version=%s delete_ast_Str=%s" % (
                profile, executable, version, str(delete_ast_str).lower()
            ))
            for label, target, status, reads, forbidden in fixtures:
                result = run(checker_command(
                    executable, checker, target, delete_ast_str
                ))
                try:
                    output = assert_checker_result(
                        label, result, status, reads, forbidden
                    )
                    print("CHECK %s rc=%d json=%s" % (label, result.returncode, output))
                except AssertionError as exc:
                    failures.append("%s/%s: %s" % (profile, label, exc))
                    print("CHECK %s rc=%d stdout=%r stderr=%r" % (
                        label, result.returncode, result.stdout, result.stderr
                    ))
            try:
                behavior_rows = run_behavior_profile(
                    executable, driver, temp_root, delete_ast_str
                )
                for row in behavior_rows:
                    print(
                        "BEHAVIOR %s rc=%d evidence_class=%s "
                        "is_contract_evidence=%s trace_manifest_origin=%s"
                        % (
                            row["case"],
                            row["rc"],
                            row["evidence_class"],
                            str(row["is_contract_evidence"]).lower(),
                            row["trace_manifest_origin"],
                        )
                    )
            except (AssertionError, ValueError) as exc:
                failures.append("%s behavior: %s" % (profile, exc))

        if not python314:
            managers = [
                name for name in ("pyenv", "uv", "docker", "conda", "mise", "asdf")
                if command_path(name)
            ]
            reason = "no python3.14 runtime"
            if managers:
                reason += "; available managers=%s" % ",".join(managers)
            else:
                reason += "; no pyenv/uv/docker/conda/mise/asdf"
            print("PYTHON_3_14 status=UNVERIFIABLE reason=%s" % reason)

    record_after = sha256_file(RECORD)
    status_after = git_status()
    status_after_lines = 0 if not status_after else len(status_after.splitlines())
    fingerprint_after, entries_after = tree_fingerprint(ROOT)
    print("record_sha256_after=%s" % record_after)
    print("git_status_lines_after=%d unchanged=%s" % (
        status_after_lines, str(status_after == status_before).lower()
    ))
    print("tree_fingerprint_after=%s entries=%d unchanged=%s" % (
        fingerprint_after,
        entries_after,
        str(fingerprint_after == fingerprint_before).lower(),
    ))
    print("acceptance_r2_sha256=%s" % sha256_file(ACCEPTANCE))

    if record_after != EXPECTED_RECORD_SHA256:
        failures.append("record.py hash mismatch after tests")
    if status_after != status_before:
        failures.append("git status changed during tests")
    if status_after_lines != EXPECTED_STATUS_LINES:
        failures.append("git status line count after tests is not 34")
    if fingerprint_after != fingerprint_before or entries_after != entries_before:
        failures.append("repo tree fingerprint changed during tests")

    if failures:
        for failure in failures:
            print("FAIL %s" % failure)
        print("RESULT FAIL")
        return 1
    print("RESULT PASS_WITH_UNVERIFIABLE python3.14_runtime")
    return 0


if __name__ == "__main__":
    sys.exit(main())
