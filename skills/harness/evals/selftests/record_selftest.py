#!/usr/bin/env python3
"""record_selftest.py — 零成本自測，不呼叫 claude CLI、不產生費用。

覆蓋兩條鏈：

1. Batch 13 的紀錄鏈：judge parser 異常必須從 `.judge.json` 一路進到正式 run record 的
   `warnings` 與逐筆 `contract_anomaly`。
2. Batch 14 的 provenance 鏈：run-start／run-end manifest 的比對、`hash_schema`
   的 fail-closed、以及 raw trace manifest 的核對。這三者任一不成立，整輪必須是
   `INVALID`——不是 FAIL，因為此時已經無法斷定 observation 對應哪一個版本。
3. Batch 15 的收緊：manifest 必須**恰好**含 `REQUIRED_DOMAINS`（缺一個代表那部分沒有
   版本綁定，多一個代表產生端與本檔認知不同）、`manifest_version` 必須是支援值、
   trace manifest 的 deterministic digest 必須進紀錄，以及 `--source` 重新評分時
   digest 不符要拒絕、且不得覆寫原始 run record。

`collect()` 需要 scorer 的輸出，這裡以 stub 取代 `score.score`，避免自測依賴
真實 stream-json；scorer 本身由 `score_selftest.py` 覆蓋。
"""
import hashlib, json, os, sys, tempfile, types

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
import record  # noqa: E402

fails = []


def check(label, cond, detail=None):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        if detail is not None:
            print("         detail: %r" % (detail,))
        fails.append(label)


def _stub_scorer(rows):
    m = types.ModuleType("score")
    m.score = lambda outdir, *fx: [dict(r) for r in rows]
    sys.modules["score"] = m


H64_A = "a" * 64
H64_B = "b" * 64


def _component_domain_hash(domain, components):
    labels = (("rules", "settings", "descriptor") if domain == "execution_context"
              else ("descriptor",))
    text = "".join(("judge_descriptor" if domain == "evaluation_context" else name)
                   + "  " + components[name] + "\n" for name in labels)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


FULL_COMPONENTS = {
    "execution_context": {"rules": H64_A, "settings": H64_A, "descriptor": H64_A},
    "evaluation_context": {"descriptor": H64_A},
}
CONTRACT_COMPONENTS = {"evaluation_context": {"descriptor": H64_A}}
EXECUTION_COMBINED = _component_domain_hash(
    "execution_context", FULL_COMPONENTS["execution_context"])
EVALUATION_COMBINED = _component_domain_hash(
    "evaluation_context", FULL_COMPONENTS["evaluation_context"])


def _snap(hashes, schema="v6", files=("skills/x/fixtures.json",), components=None):
    return {"recorded_at": "2026-09-02T00:00:00+08:00", "hash_schema": schema,
            "hashes": dict(hashes), "fixture_args": ["skills/x/fixtures.json"],
            "fixture_files": list(files),
            "context_components": json.loads(json.dumps(components or FULL_COMPONENTS))}


NONCE = "0123456789abcdef0123456789abcdef"


def _man(start_hashes, end_hashes=None, version=3, schema="v6", files=None,
         kind="full", nonce=NONCE):
    """組一份 run manifest。version=None 代表刻意不寫 manifest_version。"""
    components = CONTRACT_COMPONENTS if kind == "contract" else FULL_COMPONENTS
    doc = {"start": _snap(start_hashes, schema,
                          files or ("skills/x/fixtures.json",), components),
           "end": _snap(end_hashes if end_hashes is not None else start_hashes,
                        schema, files or ("skills/x/fixtures.json",), components)}
    if version is not None:
        doc["manifest_version"] = version
    if kind is not None:
        doc["kind"] = kind
    if nonce is not None:
        doc["run_nonce"] = nonce
    return doc


def _cman(evaluator=None, evaluation_context=None, contract_fixtures=None,
          rescore_runner=None):
    """contract manifest：重新評分時量的四個 contract domain。"""
    h = {"evaluator": evaluator or ("c" * 64),
         "evaluation_context": evaluation_context or EVALUATION_COMBINED,
         "contract_fixtures": contract_fixtures or ("e" * 64),
         "rescore_runner": rescore_runner or ("f" * 64)}
    return _man(h, kind="contract")


# 恰好 REQUIRED_DOMAINS；缺一個或多一個都不合法。
BASE_HASHES = dict((d, H64_A) for d in record.REQUIRED_DOMAINS)
BASE_HASHES["execution_context"] = EXECUTION_COMBINED
BASE_HASHES["evaluation_context"] = EVALUATION_COMBINED


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _build_run(d, rows, manifest, trace_files=None, mutate_trace=False,
               write_trace_manifest=True, write_post_judge_manifest=True,
               meta_nonce=NONCE, trace_nonce=NONCE):
    """在 d 底下造一個最小 run：raw/ 內每筆一個 .jsonl／.meta.json／.judge.json。

    meta 與 trace manifest 都帶 run_nonce——`record.py` 要求 manifest／trace manifest／
    每份 meta 三方一致才認這輪是「當下」產生的（BR-F35）。
    """
    raw = os.path.join(d, "raw")
    os.makedirs(raw, exist_ok=True)
    for r in rows:
        open(os.path.join(raw, r["id"] + ".jsonl"), "w").write(
            '{"type":"result","total_cost_usd":0.01}\n')
        meta = {"id": r["id"], "exit_code": 0, "prompt": "p"}
        if meta_nonce is not None:
            meta["run_nonce"] = meta_nonce
        json.dump(meta, open(os.path.join(raw, r["id"] + ".meta.json"), "w"))
        json.dump({"overall": "PASS", "_cost_usd": 0.01},
                  open(os.path.join(raw, r["id"] + ".judge.json"), "w"))
    if manifest is not None:
        json.dump(manifest, open(os.path.join(d, "manifest.json"), "w"))
    if write_trace_manifest:
        files = dict(trace_files or {})
        if not files:
            for fn in sorted(os.listdir(raw)):
                if fn.endswith((".jsonl", ".meta.json")):
                    files[fn] = _sha(os.path.join(raw, fn))
        trace_digest = record.trace_digest(files)
        json.dump({"recorded_at": "x", "algorithm": "sha256", "digest": trace_digest,
                   "run_nonce": trace_nonce, "files": files},
                  open(os.path.join(d, "trace-manifest.json"), "w"))
        if write_post_judge_manifest:
            judge_files = {}
            for fn in sorted(os.listdir(raw)):
                if fn.endswith(".judge.json"):
                    judge_files[fn] = _sha(os.path.join(raw, fn))
            judge_digest = record.trace_digest(judge_files)
            json.dump({"manifest_version": 1, "kind": "post_judge",
                       "recorded_at": "x", "algorithm": "sha256",
                       "run_nonce": trace_nonce,
                       "trace_manifest_digest": trace_digest,
                       "digest": judge_digest, "files": judge_files},
                      open(os.path.join(d, "post-judge-manifest.json"), "w"))
    if mutate_trace:
        with open(os.path.join(raw, rows[0]["id"] + ".jsonl"), "a") as fh:
            fh.write('{"type":"assistant"}\n')
    return raw


def main():
    rows_in = [
        {"id": "s__a", "category": "positive", "routing": "PASS", "detail": "",
         "triggered": ["judgment"]},
        {"id": "s__b", "category": "positive", "routing": "PASS", "detail": "",
         "triggered": []},
        {"id": "s__c", "category": "negative", "routing": "PASS", "detail": "",
         "triggered": []},
    ]
    _stub_scorer(rows_in)
    with tempfile.TemporaryDirectory() as d:
        # a: 判定可用但有多餘 key；b: parser fail-closed；c: 正常
        json.dump({"overall": "PASS", "anomaly": {"kind": "extra_keys",
                                                  "extra_keys": ["note"]},
                   "_cost_usd": 0.01},
                  open(os.path.join(d, "s__a.judge.json"), "w"))
        json.dump({"error": "judge 判定不可用（extra_data）",
                   "anomaly": {"kind": "extra_data", "trailing_chars": 42},
                   "_cost_usd": 0.02},
                  open(os.path.join(d, "s__b.judge.json"), "w"))
        json.dump({"overall": "PASS", "_cost_usd": 0.03},
                  open(os.path.join(d, "s__c.judge.json"), "w"))
        rows, cost = record.collect(d, ())

    by = {r["id"]: r for r in rows}
    print("collect：anomaly 傳遞")
    check("可用判定的 anomaly 有帶出",
          by["s__a"]["contract_anomaly"]["kind"] == "extra_keys")
    check("多餘 key 不影響 contract 判定", by["s__a"]["contract"] == "PASS")
    check("parser 失敗記 ERROR", by["s__b"]["contract"] == "ERROR")
    check("parser 失敗的 anomaly 有帶出",
          by["s__b"]["contract_anomaly"]["kind"] == "extra_data")
    check("正常筆的 anomaly 為 None", by["s__c"]["contract_anomaly"] is None)

    print("collect：judge 成本在判定失敗時仍計入")
    check("judge_usd 不因一筆 ERROR 變 null", cost["judge_usd"] is not None)
    check("judge_usd 含 ERROR 筆的成本", abs(cost["judge_usd"] - 0.06) < 1e-9)

    print("collect_warnings")
    w = record.collect_warnings(rows)
    kinds = {x["fixture_id"]: x for x in w}
    check("兩筆異常都進 warnings", len(w) == 2)
    check("可用者標 usable=True", kinds["s__a"]["usable"] is True)
    check("不可用者標 usable=False", kinds["s__b"]["usable"] is False)
    check("來源標記為 judge_parser",
          all(x["source"] == "judge_parser" for x in w))
    check("保留完整 detail", kinds["s__b"]["detail"]["trailing_chars"] == 42)
    check("無異常筆不進 warnings", "s__c" not in kinds)

    print("result_row")
    rr = record.result_row(by["s__b"])
    check("逐筆結果含 contract_anomaly", rr["contract_anomaly"]["kind"] == "extra_data")

    # --- Batch 14：hash_schema fail-closed ---
    print("check_schema（hash_schema fail-closed）")
    check("None → 不合法", record.check_schema(None) is not None)
    check("空字串 → 不合法", record.check_schema("") is not None)
    check("缺 v 前綴 → 不合法", record.check_schema("3") is not None)
    check("非數字 → 不合法", record.check_schema("vx") is not None)
    check("v0 → 不合法", record.check_schema("v0") is not None)
    check("非字串 → 不合法", record.check_schema(3) is not None)
    check("v1 合法", record.check_schema("v1") is None)
    check("v6 合法", record.check_schema("v6") is None)

    # --- Batch 14：run-start / run-end manifest 比對 ---
    print("REQUIRED_DOMAINS（Batch 15：恰好，不多不少）")
    check("恰好八個 domain", record.REQUIRED_DOMAINS == frozenset((
        "dispatch_skill", "judgment_skill", "token_preflight_skill", "evaluator",
        "runner", "fixtures", "execution_context", "evaluation_context")))
    check("judge 端環境是獨立 domain，未併進 execution_context",
          "evaluation_context" in record.REQUIRED_DOMAINS
          and "execution_context" in record.REQUIRED_DOMAINS)
    check("manifest_version 支援值明確", record.SUPPORTED_MANIFEST_VERSIONS == (3,))

    print("check_manifest（start/end drift）")
    good = _man(BASE_HASHES)
    hashes, schema, files, probs = record.check_manifest(good)
    check("前後相同且 domain 完整 → 無問題", probs == [], probs)
    check("回傳 start 的 hashes", hashes["evaluator"] == H64_A and schema == "v6")
    check("帶出 fixture 檔案清單", files == ["skills/x/fixtures.json"])

    for domain in sorted(record.REQUIRED_DOMAINS):
        drift = dict(BASE_HASHES)
        drift[domain] = H64_B
        _, _, _, probs = record.check_manifest(_man(BASE_HASHES, drift))
        check("%s 在 run 期間變動 → 記為 drift" % domain,
              any("domain drift" in p and domain in p for p in probs))

    _, _, _, probs = record.check_manifest({"manifest_version": 3,
                                            "start": _snap(BASE_HASHES)})
    check("缺 end 快照 → 有問題", any("缺 end" in p for p in probs))
    _, _, _, probs = record.check_manifest({"manifest_version": 3,
                                            "end": _snap(BASE_HASHES)})
    check("缺 start 快照 → 有問題", any("缺 start" in p for p in probs))

    _, _, _, probs = record.check_manifest(
        {"manifest_version": 3, "start": _snap(BASE_HASHES, schema=None),
         "end": _snap(BASE_HASHES)})
    check("start 缺 hash_schema → 有問題", any("hash_schema" in p for p in probs))
    _, _, _, probs = record.check_manifest(
        {"manifest_version": 3, "start": _snap(BASE_HASHES, schema="v3"),
         "end": _snap(BASE_HASHES)})
    check("hash_schema 前後不同 → 有問題",
          any("hash_schema 在 run 期間變動" in p for p in probs))

    bad_hash = dict(BASE_HASHES, evaluator="not-a-hash")
    _, _, _, probs = record.check_manifest(_man(bad_hash))
    check("hash 格式不合法 → 有問題", any("格式不合法" in p for p in probs))

    dropped = dict((k, v) for k, v in BASE_HASHES.items() if k != "execution_context")
    _, _, _, probs = record.check_manifest(_man(BASE_HASHES, dropped))
    check("前後量測的 domain 集合不同 → 有問題",
          any("domain 集合不同" in p for p in probs))

    _, _, _, probs = record.check_manifest(
        {"manifest_version": 3,
         "start": _snap(BASE_HASHES, files=("a.json",)),
         "end": _snap(BASE_HASHES, files=("a.json", "b.json"))})
    check("fixture 檔案清單變動 → 有問題",
          any("fixture 檔案清單" in p for p in probs))

    # --- Batch 15 / BR-F22：domain 集合必須恰好，manifest_version 必須支援 ---
    print("check_manifest（domain 集合完整性與 manifest_version）")
    only_fx = {"fixtures": H64_A}
    _, _, _, probs = record.check_manifest(_man(only_fx))
    check("start/end 同時只含 fixtures → 有問題（前後一致不代表有綁定）",
          any("缺少必要 domain" in p for p in probs))
    check("缺失清單同時涵蓋 start 與 end",
          any(p.startswith("start 缺少") for p in probs)
          and any(p.startswith("end 缺少") for p in probs))

    no_exec = dict((k, v) for k, v in BASE_HASHES.items() if k != "execution_context")
    _, _, _, probs = record.check_manifest(_man(no_exec))
    check("start/end 同時缺 execution_context → 有問題",
          any("缺少必要 domain" in p and "execution_context" in p for p in probs))

    no_eval = dict((k, v) for k, v in BASE_HASHES.items() if k != "evaluation_context")
    _, _, _, probs = record.check_manifest(_man(no_eval))
    check("start/end 同時缺 evaluation_context → 有問題",
          any("缺少必要 domain" in p and "evaluation_context" in p for p in probs))

    extra = dict(BASE_HASHES, mystery_domain=H64_B)
    _, _, _, probs = record.check_manifest(_man(extra))
    check("start/end 同時多出未知 domain → 有問題",
          any("未知 domain" in p and "mystery_domain" in p for p in probs))

    _, _, _, probs = record.check_manifest(_man(BASE_HASHES, version=None))
    check("缺 manifest_version → 有問題",
          any("缺 manifest_version" in p for p in probs))
    _, _, _, probs = record.check_manifest(_man(BASE_HASHES, version=99))
    check("不支援的 manifest_version → 有問題",
          any("不支援的 manifest_version" in p for p in probs))
    _, _, _, probs = record.check_manifest(_man(BASE_HASHES, version="1"))
    check("manifest_version 型別不符 → 有問題",
          any("不支援的 manifest_version" in p for p in probs))

    _, _, _, probs = record.check_manifest(_man(BASE_HASHES))
    check("完整八個 domain + 支援的 manifest_version → 無問題", probs == [], probs)

    print("check_manifest（context component hashes）")
    missing_component = _man(BASE_HASHES)
    del missing_component["start"]["context_components"]["execution_context"]["rules"]
    _, _, _, probs = record.check_manifest(missing_component)
    check("缺 rules 分項 hash → 有問題",
          any("execution_context 缺 component" in p and "rules" in p for p in probs))
    drift_component = _man(BASE_HASHES)
    drift_component["end"]["context_components"]["evaluation_context"]["descriptor"] = H64_B
    _, _, _, probs = record.check_manifest(drift_component)
    check("context 分項 drift → 有問題",
          any("context component drift" in p for p in probs))
    absent_settings = _man(BASE_HASHES)
    for phase in ("start", "end"):
        absent_settings[phase]["context_components"]["execution_context"]["settings"] = "absent"
        absent_settings[phase]["hashes"]["execution_context"] = _component_domain_hash(
            "execution_context",
            absent_settings[phase]["context_components"]["execution_context"])
    _, _, _, probs = record.check_manifest(absent_settings)
    check("settings 明確記 absent → 合法", probs == [], probs)

    # --- Batch 16 / BR-F28：manifest kind 決定必要 domain 集合 ---
    print("check_manifest（manifest kind）")
    _, _, _, probs = record.check_manifest(_cman())
    check("contract manifest 只需兩個 contract domain → 無問題", probs == [], probs)
    _, _, _, probs = record.check_manifest(_man(BASE_HASHES, kind="contract"))
    check("contract manifest 含八個 domain → 多出未知 domain",
          any("未知 domain" in p for p in probs))
    _, _, _, probs = record.check_manifest(_man(BASE_HASHES, kind="mystery"))
    check("未知的 manifest kind → 有問題",
          any("未知的 manifest kind" in p for p in probs))
    check("CONTRACT_DOMAINS 含 contract_fixtures 與 rescore_runner（v6）",
          record.CONTRACT_DOMAINS == frozenset(
              ("evaluator", "evaluation_context", "contract_fixtures",
               "rescore_runner")))
    check("SUBJECT_DOMAINS 是 full 扣掉兩個判定端 domain，共六個",
          record.SUBJECT_DOMAINS == record.REQUIRED_DOMAINS - frozenset(
              ("evaluator", "evaluation_context"))
          and len(record.SUBJECT_DOMAINS) == 6)
    check("contract_fixtures 不屬於 full manifest",
          "contract_fixtures" not in record.REQUIRED_DOMAINS)

    # --- Batch 14：raw trace manifest 核對 ---
    print("verify_traces（raw trace 核對）")
    rows2 = [{"id": "s__a", "category": "positive", "routing": "PASS", "detail": "",
              "triggered": []}]
    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None)
        tm, _dg, probs = record.verify_traces(raw, os.path.join(d, "trace-manifest.json"))
        check("未更動 → 核對通過", probs == [] and tm is not None)

    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None, mutate_trace=True)
        _, _dg, probs = record.verify_traces(raw, os.path.join(d, "trace-manifest.json"))
        check("trace 被更動 → 記 hash 不符",
              any("trace hash 不符" in p for p in probs))

    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None, write_trace_manifest=False)
        tm, _dg, probs = record.verify_traces(raw, os.path.join(d, "trace-manifest.json"))
        check("缺 trace manifest → 有問題", tm is None and len(probs) == 1)

    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None)
        open(os.path.join(raw, "s__extra.jsonl"), "w").write("{}\n")
        _, _dg, probs = record.verify_traces(raw, os.path.join(d, "trace-manifest.json"))
        check("多出未列於 manifest 的 trace → 有問題",
              any("多出未列於 manifest" in p for p in probs))

    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None)
        os.unlink(os.path.join(raw, "s__a.jsonl"))
        _, _dg, probs = record.verify_traces(raw, os.path.join(d, "trace-manifest.json"))
        check("manifest 列到但檔案不見 → 有問題",
              any("trace 檔案遺失" in p for p in probs))

    print("verify_post_judge（contract artifact 核對）")
    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None)
        tm = json.load(open(os.path.join(d, "trace-manifest.json")))
        td = record.trace_digest(tm["files"])
        pm, _pd, probs = record.verify_post_judge(
            raw, os.path.join(d, "post-judge-manifest.json"), ["s__a"], tm, td)
        check("完整 post-judge manifest → 核對通過", probs == [] and pm is not None, probs)

    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None)
        with open(os.path.join(raw, "s__a.judge.json"), "a") as fh:
            fh.write("\n")
        tm = json.load(open(os.path.join(d, "trace-manifest.json")))
        _pm, _pd, probs = record.verify_post_judge(
            raw, os.path.join(d, "post-judge-manifest.json"), ["s__a"], tm,
            record.trace_digest(tm["files"]))
        check("judge 產物被更動 → 有問題",
              any("judge 產物 hash 不符" in p for p in probs), probs)

    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None, write_post_judge_manifest=False)
        tm = json.load(open(os.path.join(d, "trace-manifest.json")))
        pm, _pd, probs = record.verify_post_judge(
            raw, os.path.join(d, "post-judge-manifest.json"), ["s__a"], tm,
            record.trace_digest(tm["files"]))
        check("缺 post-judge manifest → 有問題", pm is None and len(probs) == 1, probs)

    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None)
        pm_path = os.path.join(d, "post-judge-manifest.json")
        pm = json.load(open(pm_path))
        pm["trace_manifest_digest"] = H64_B
        json.dump(pm, open(pm_path, "w"))
        tm = json.load(open(os.path.join(d, "trace-manifest.json")))
        _pm, _pd, probs = record.verify_post_judge(
            raw, pm_path, ["s__a"], tm, record.trace_digest(tm["files"]))
        check("post-judge 綁錯 trace → 有問題",
              any("trace digest" in p for p in probs), probs)

    # --- Batch 14：整條 provenance 進 main()，drift 必須壓過 PASS ---
    print("main（provenance 決定 run_status）")
    _stub_scorer(rows2)

    def run_main(manifest, **kw):
        with tempfile.TemporaryDirectory() as d:
            raw = _build_run(d, rows2, manifest, **kw)
            rc = record.main(raw, "selftest-run", os.path.join(d, "manifest.json"))
            doc = json.load(open(os.path.join(d, "selftest-run.json")))
        return rc, doc


    rc, doc = run_main(good)
    check("start=end 且 trace 相符 → PASS 且構成契約證據",
          doc["run_status"] == "PASS" and doc["is_contract_evidence"] is True and rc == 0)
    check("run record 的 hash 取自 manifest，不是現算",
          doc["hashes"] == BASE_HASHES and doc["hash_schema"] == "v6")
    check("provenance 標記 start/end 一致",
          doc["provenance"]["start_end_identical"] is True)
    check("run record 保存 trace manifest",
          bool(doc["provenance"]["trace_manifest"]["files"]))

    drift = dict(BASE_HASHES, fixtures=H64_B)
    rc, doc = run_main(_man(BASE_HASHES, drift))
    check("run 中途改 fixture → INVALID",
          doc["run_status"] == "INVALID" and doc["is_contract_evidence"] is False)
    check("INVALID 理由指出是 drift", "domain drift" in doc["invalid_reason"])
    check("drift 讓 record.py 回非 0", rc == 2)

    rc, doc = run_main(_man(BASE_HASHES, schema="vx"))
    check("hash_schema 不合法 → INVALID", doc["run_status"] == "INVALID")

    rc, doc = run_main(_man(BASE_HASHES, version=None))
    check("缺 manifest_version → INVALID", doc["run_status"] == "INVALID")
    rc, doc = run_main(_man({"fixtures": H64_A}))
    check("只含一個 domain 的 manifest → INVALID", doc["run_status"] == "INVALID")
    check("INVALID 理由指出缺少必要 domain",
          "缺少必要 domain" in (doc["invalid_reason"] or ""))

    rc, doc = run_main(good, mutate_trace=True)
    check("raw trace 被更動 → INVALID", doc["run_status"] == "INVALID")

    rc, doc = run_main(good, write_trace_manifest=False)
    check("缺 trace manifest → INVALID", doc["run_status"] == "INVALID")

    rc, doc = run_main(None)
    check("完全沒有 run manifest → INVALID",
          doc["run_status"] == "INVALID" and doc["hashes"] is None)

    # --- Batch 15 / BR-F24：trace digest 與 derived record ---
    print("trace digest")
    files = {"a.jsonl": H64_A, "b.jsonl": H64_B}
    check("digest 與鍵序無關",
          record.trace_digest(files)
          == record.trace_digest({"b.jsonl": H64_B, "a.jsonl": H64_A}))
    check("內容變了 digest 就變",
          record.trace_digest(files) != record.trace_digest({"a.jsonl": H64_B,
                                                             "b.jsonl": H64_B}))
    with tempfile.TemporaryDirectory() as d:
        raw = _build_run(d, rows2, None)
        tmp_path = os.path.join(d, "trace-manifest.json")
        tm = json.load(open(tmp_path))
        tm["digest"] = H64_B          # 自述值造假
        json.dump(tm, open(tmp_path, "w"))
        _, dg, probs = record.verify_traces(raw, tmp_path)
        check("不採信 manifest 自述的 digest，一律重算",
              any("自述的 digest" in p for p in probs) and dg != H64_B)

    print("derived record（--source 重新評分）")

    def build_source(d, schema="v6"):
        """造一份合法的原始 run record，並附一份 contract manifest。

        回傳 (raw, source_record_path, contract_manifest_path)。
        """
        raw = _build_run(d, rows2, _man(BASE_HASHES, schema=schema))
        record.main(raw, "src-run", os.path.join(d, "manifest.json"))
        src = os.path.join(d, "src-run.json")
        if schema != "v6":
            doc = json.load(open(src))
            doc["hash_schema"] = schema
            json.dump(doc, open(src, "w"))
        cman = os.path.join(d, "contract-manifest.json")
        json.dump(_cman(), open(cman, "w"))
        return raw, src, cman

    def audit_item(equivalent=True, evidence="兩份檔案 diff 為空",
                   method="逐檔 diff"):
        item = {}
        if equivalent is not None:
            item["equivalent"] = equivalent
        if evidence is not None:
            item["evidence"] = evidence
        if method is not None:
            item["method"] = method
        return item

    def audit_file(d, domains=None, source_schema="v3", target_schema="v6",
                   method="逐 domain 比對 allowlist 與檔案內容", item=None,
                   name="audit.json"):
        p = os.path.join(d, name)
        keys = domains if domains is not None else sorted(record.SUBJECT_DOMAINS)
        body = {"source_hash_schema": source_schema,
                "target_hash_schema": target_schema,
                "reviewed_at": "2026-09-02",
                "domains": dict((k, item if item is not None else audit_item())
                                for k in keys)}
        if method is not None:
            body["method"] = method
        json.dump(body, open(p, "w"), ensure_ascii=False)
        return p

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        srcdoc = json.load(open(src))
        check("原始 run record 保存 trace manifest digest",
              bool(srcdoc["provenance"]["trace_manifest_digest"]))
        check("原始 run record 標為 source", srcdoc["record_kind"] == "source")
        before = open(src).read()
        rc = record.main(raw, "rescore-1", cman, source_record=src)
        doc = json.load(open(os.path.join(d, "rescore-1.json")))
        check("合法原始 trace + contract manifest → 可以重評",
              rc == 0 and doc["run_status"] == "PASS")
        check("derived record 標為 derived", doc["record_kind"] == "derived")
        check("derived record 記下來源 run ID",
              doc["derived_from"]["source_run_id"] == "src-run")
        check("derived record 記下原始 trace digest",
              doc["derived_from"]["source_trace_manifest_digest"]
              == srcdoc["provenance"]["trace_manifest_digest"])
        check("rescored_with 是**現在的** evaluator，不是來源的",
              doc["derived_from"]["rescored_with"]["evaluator"] == "c" * 64
              and doc["derived_from"]["rescored_with"]["evaluation_context"]
              == EVALUATION_COMBINED)
        check("subject 那半取自來源紀錄",
              doc["hashes"]["dispatch_skill"] == H64_A
              and doc["hash_provenance"]["dispatch_skill"] == "source_run")
        check("contract 那半標為現量",
              doc["hash_provenance"]["evaluator"] == "measured_now"
              and doc["hash_provenance"]["evaluation_context"] == "measured_now")
        check("derived record 的 hashes = subject 六個 + contract 三個",
              set(doc["hashes"]) == record.SUBJECT_DOMAINS | record.CONTRACT_DOMAINS)
        check("同 schema 時不要求 migration audit",
              doc["derived_from"]["cross_schema"] is False)
        check("derived record 的 hashes 含 contract_fixtures（v5）",
              doc["hashes"]["contract_fixtures"] == "e" * 64
              and doc["hash_provenance"]["contract_fixtures"] == "measured_now")
        check("derived record 共十個 domain（六 subject + 四 contract）",
              len(doc["hashes"]) == 10)
        check("derived record 繼承來源的 trace manifest 來源宣告",
              doc["derived_from"]["source_trace_manifest_origin"] == "contemporaneous"
              and doc["evidence_class"] == "contract_evidence")
        check("derived record 不覆寫 source record", open(src).read() == before)

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        rc = record.main(raw, "rescore-full", os.path.join(d, "manifest.json"),
                         source_record=src)
        doc = json.load(open(os.path.join(d, "rescore-full.json")))
        check("重評傳 full manifest → INVALID",
              doc["run_status"] == "INVALID"
              and "contract manifest" in (doc["invalid_reason"] or ""))

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        rc = record.main(raw, "native-contract", cman)
        doc = json.load(open(os.path.join(d, "native-contract.json")))
        check("原生 run 傳 contract manifest → INVALID",
              doc["run_status"] == "INVALID"
              and "原生 run 不得使用 contract manifest" in (doc["invalid_reason"] or ""))

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        before = open(src).read()
        rc = record.main(raw, "src-run", cman, source_record=src)
        check("輸出路徑等於 source → 拒絕且不寫檔",
              rc == 3 and open(src).read() == before)

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        # 改 trace 後另建一份「自洽」的 manifest：逐檔比對會全部通過，
        # 只有跟原始紀錄比 digest 才抓得到。
        with open(os.path.join(raw, "s__a.jsonl"), "a") as fh:
            fh.write('{"type":"assistant"}\n')
        os.unlink(os.path.join(d, "trace-manifest.json"))
        files = {}
        for fn in sorted(os.listdir(raw)):
            if fn.endswith((".jsonl", ".meta.json")):
                files[fn] = _sha(os.path.join(raw, fn))
        json.dump({"recorded_at": "x", "algorithm": "sha256",
                   "digest": record.trace_digest(files), "files": files},
                  open(os.path.join(d, "trace-manifest.json"), "w"))
        rc = record.main(raw, "rescore-2", cman, source_record=src)
        doc = json.load(open(os.path.join(d, "rescore-2.json")))
        check("改 trace 後另建自洽 manifest → 逐檔比對過，digest 比對擋下",
              doc["run_status"] == "INVALID"
              and "digest 與原始紀錄不符" in (doc["invalid_reason"] or ""))

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        srcdoc = json.load(open(src))
        srcdoc["provenance"]["trace_manifest_digest"] = None
        json.dump(srcdoc, open(src, "w"))
        rc = record.main(raw, "rescore-3", cman, source_record=src)
        doc = json.load(open(os.path.join(d, "rescore-3.json")))
        check("原始紀錄沒有 digest → 拒絕沿用", doc["run_status"] == "INVALID")

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        srcdoc = json.load(open(src))
        del srcdoc["hashes"]["runner"]
        json.dump(srcdoc, open(src, "w"))
        rc = record.main(raw, "rescore-4", cman, source_record=src)
        doc = json.load(open(os.path.join(d, "rescore-4.json")))
        check("來源紀錄缺 subject domain → INVALID",
              doc["run_status"] == "INVALID"
              and "缺 subject domain" in (doc["invalid_reason"] or ""))

    # --- Batch 16 / BR-F28：跨 schema 必須另附 migration audit ---
    print("cross-schema derived record（migration audit）")
    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d, schema="v3")
        rc = record.main(raw, "x-no-audit", cman, source_record=src)
        doc = json.load(open(os.path.join(d, "x-no-audit.json")))
        check("v3 來源、無 audit → INVALID 且指出要附 audit",
              doc["run_status"] == "INVALID"
              and "migration-audit" in (doc["invalid_reason"] or ""))

        bad = audit_file(d, domains=["dispatch_skill"])
        rc = record.main(raw, "x-bad-audit", cman, source_record=src,
                         migration_audit=bad)
        doc = json.load(open(os.path.join(d, "x-bad-audit.json")))
        check("audit 未涵蓋全部 subject domain → INVALID",
              doc["run_status"] == "INVALID" and "未涵蓋" in (doc["invalid_reason"] or ""))

        wrong = audit_file(d, source_schema="v2")
        rc = record.main(raw, "x-wrong-audit", cman, source_record=src,
                         migration_audit=wrong)
        doc = json.load(open(os.path.join(d, "x-wrong-audit.json")))
        check("audit 的 source_hash_schema 對不上 → INVALID",
              doc["run_status"] == "INVALID"
              and "source_hash_schema" in (doc["invalid_reason"] or ""))

        nomethod = audit_file(d, method=None)
        rc = record.main(raw, "x-nomethod", cman, source_record=src,
                         migration_audit=nomethod)
        doc = json.load(open(os.path.join(d, "x-nomethod.json")))
        check("audit 沒說明比對方法 → INVALID",
              doc["run_status"] == "INVALID" and "method" in (doc["invalid_reason"] or ""))

        # --- Batch 17 / BR-F29：audit 必須逐條做出可歸責的主張 ---
        bad_audits = (
            ("domains 值為 null", None),
            ("equivalent 為 false", audit_item(equivalent=False)),
            ("equivalent 缺失", audit_item(equivalent=None)),
            ("evidence 為空字串", audit_item(evidence="   ")),
            ("evidence 缺失", audit_item(evidence=None)),
            ("逐 domain method 缺失", audit_item(method=None)),
            ("多出未知欄位", dict(audit_item(), confidence=0.4)),
        )
        for i, (label, item) in enumerate(bad_audits):
            if item is None:
                # domains 的值直接寫成 null——先前這樣六個都填 null 仍會 PASS
                ap = os.path.join(d, "audit-null.json")
                json.dump({"source_hash_schema": "v3", "target_hash_schema": "v6",
                           "method": "x", "reviewed_at": "y",
                           "domains": dict((k, None)
                                           for k in sorted(record.SUBJECT_DOMAINS))},
                          open(ap, "w"))
            else:
                ap = audit_file(d, item=item, name="audit-bad-%d.json" % i)
            rid = "x-bad-%d" % i
            record.main(raw, rid, cman, source_record=src, migration_audit=ap)
            doc = json.load(open(os.path.join(d, rid + ".json")))
            check("audit %s → INVALID" % label, doc["run_status"] == "INVALID",
                  doc["invalid_reason"])

        unknown = audit_file(d, domains=sorted(record.SUBJECT_DOMAINS) + ["mystery"],
                             name="audit-unknown.json")
        rc = record.main(raw, "x-unknown", cman, source_record=src,
                         migration_audit=unknown)
        doc = json.load(open(os.path.join(d, "x-unknown.json")))
        check("audit 出現未知 domain → INVALID",
              doc["run_status"] == "INVALID"
              and "未知 domain" in (doc["invalid_reason"] or ""))

        good_audit = audit_file(d)
        rc = record.main(raw, "x-ok", cman, source_record=src,
                         migration_audit=good_audit)
        doc = json.load(open(os.path.join(d, "x-ok.json")))
        check("v3 來源 + 完整 audit → 有效 derived record",
              rc == 0 and doc["run_status"] == "PASS"
              and doc["is_contract_evidence"] is True)
        check("derived record 標記 cross_schema 並保存 audit digest",
              doc["derived_from"]["cross_schema"] is True
              and bool(doc["derived_from"]["migration_audit"]["digest"]))
        check("hash_method 寫六個 domain，且 derived 說明 identity 由兩半組成",
              "六個互斥 domain" in doc["hash_method"]
              and "evaluation-context" in doc["hash_method"]
              and "hash_provenance" in doc["hash_method"])

    # --- Batch 17 / BR-F29：來源 subject hash 必須是合法 64 hex ---
    print("來源 subject hash 的格式（BR-F29）")
    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        srcdoc = json.load(open(src))
        srcdoc["hashes"] = dict((k, None) for k in record.SUBJECT_DOMAINS)
        json.dump(srcdoc, open(src, "w"))
        rc = record.main(raw, "null-hash", cman, source_record=src)
        doc = json.load(open(os.path.join(d, "null-hash.json")))
        check("六個 subject hash 全為 null → INVALID",
              doc["run_status"] == "INVALID"
              and "不是合法的 64 位 hex" in (doc["invalid_reason"] or ""))

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        srcdoc = json.load(open(src))
        srcdoc["hashes"]["runner"] = "not-a-hash"
        json.dump(srcdoc, open(src, "w"))
        rc = record.main(raw, "bad-hash", cman, source_record=src)
        doc = json.load(open(os.path.join(d, "bad-hash.json")))
        check("單一 subject hash 格式錯誤 → INVALID",
              doc["run_status"] == "INVALID"
              and "runner" in (doc["invalid_reason"] or ""))

    # --- Batch 18 / BR-F35：evidence_class 由 run nonce 鏈決定，不採信任何自述 ---
    print("evidence_class 與 run nonce 鏈（BR-F35）")
    rc, doc = run_main(_man(BASE_HASHES))
    check("完整 nonce 鏈 → contract_evidence",
          doc["evidence_class"] == "contract_evidence"
          and doc["is_contract_evidence"] is True
          and doc["provenance"]["run_nonce"] == NONCE)

    rc, doc = run_main(_man(BASE_HASHES, nonce=None))
    check("manifest 沒有 run_nonce → legacy_diagnostic",
          doc["evidence_class"] == "legacy_diagnostic"
          and doc["is_contract_evidence"] is False
          and doc["run_status"] == "PASS")
    check("legacy diagnostic 的理由寫進紀錄",
          "legacy diagnostic" in (doc["invalid_reason"] or ""))

    rc, doc = run_main(_man(BASE_HASHES), trace_nonce="f" * 32)
    check("trace manifest 的 nonce 與 manifest 不符 → legacy_diagnostic",
          doc["evidence_class"] == "legacy_diagnostic")

    rc, doc = run_main(_man(BASE_HASHES), meta_nonce=None)
    check("subject meta 沒帶 nonce → legacy_diagnostic",
          doc["evidence_class"] == "legacy_diagnostic")

    rc, doc = run_main(_man(BASE_HASHES), meta_nonce="b" * 32)
    check("subject meta 的 nonce 對不上 → legacy_diagnostic",
          doc["evidence_class"] == "legacy_diagnostic")

    # 反例本身：先前只要設一個環境變數就能升格。現在環境變數完全不參與判定。
    os.environ["HARNESS_TRACE_MANIFEST_ORIGIN"] = "contemporaneous"
    try:
        rc, doc = run_main(_man(BASE_HASHES, nonce=None))
        check("設 HARNESS_TRACE_MANIFEST_ORIGIN 不再能升格（BR-F35 反例已封）",
              doc["evidence_class"] == "legacy_diagnostic"
              and doc["is_contract_evidence"] is False)
    finally:
        os.environ.pop("HARNESS_TRACE_MANIFEST_ORIGIN", None)

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        srcdoc = json.load(open(src))
        srcdoc["provenance"]["trace_manifest_origin"] = "unknown"
        json.dump(srcdoc, open(src, "w"))
        rc = record.main(raw, "legacy-derived", cman, source_record=src)
        doc = json.load(open(os.path.join(d, "legacy-derived.json")))
        check("來源不是當下產生的 → derived record 也只能是 legacy diagnostic",
              doc["run_status"] == "PASS"
              and doc["evidence_class"] == "legacy_diagnostic"
              and doc["is_contract_evidence"] is False)
        check("derived record 記下來源的 trace manifest 來源",
              doc["derived_from"]["source_trace_manifest_origin"] == "unknown")

    # --- Batch 18 / BR-F34：--validate-only 是零成本 preflight ---
    print("validate-only preflight（BR-F34）")
    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        rc = record.main(raw, "pf-ok", cman, source_record=src, validate_only=True)
        check("合法輸入 → preflight 通過且不寫紀錄",
              rc == 0 and not os.path.exists(os.path.join(d, "pf-ok.json")))
        srcdoc = json.load(open(src))
        srcdoc["hashes"]["runner"] = None
        json.dump(srcdoc, open(src, "w"))
        rc = record.main(raw, "pf-bad", cman, source_record=src, validate_only=True)
        check("來源 hash 壞損 → preflight 回非 0 且不寫紀錄",
              rc == 3 and not os.path.exists(os.path.join(d, "pf-bad.json")))

    # --- Batch 21 / BR-F38：preflight 當下只有 start 快照，start 那半仍必須完整驗完 ---
    # 舊行為：end 缺席 → check_manifest 整段早退並回傳 hash_schema=None，
    # 於是 main() 的 cross_schema 恆為 False，跨 schema 缺 --migration-audit 這道閘
    # 在 preflight 期間完全不觸發，judge 的錢照花。
    print("start-only preflight（BR-F38）")

    def _start_only(doc):
        d = dict(doc)
        d.pop("end", None)
        return d

    hs, schema, files, probs = record.check_manifest(
        _start_only(_man(BASE_HASHES)), require_end=False)
    check("start-only + require_end=False → 無問題", probs == [], probs)
    check("start-only 仍帶出 start identity",
          hs["evaluator"] == H64_A and schema == "v6"
          and files == ["skills/x/fixtures.json"])

    hs2, schema2, _, probs = record.check_manifest(_start_only(_man(BASE_HASHES)))
    check("start-only + require_end=True → 記缺 end", any("缺 end" in p for p in probs))
    check("即使記了缺 end，start identity 仍回傳（不再整段早退）",
          hs2 == hs and schema2 == "v6")

    dropped = dict((k, v) for k, v in BASE_HASHES.items() if k != "runner")
    _, _, _, probs = record.check_manifest(_start_only(_man(dropped)), require_end=False)
    check("start-only 缺 domain → judge 前就判得出來",
          any("start 缺少必要 domain" in p and "runner" in p for p in probs))

    extra = dict(BASE_HASHES, mystery_domain=H64_B)
    _, _, _, probs = record.check_manifest(_start_only(_man(extra)), require_end=False)
    check("start-only 未知 domain → judge 前就判得出來",
          any("start 出現未知 domain" in p and "mystery_domain" in p for p in probs))

    _, _, _, probs = record.check_manifest(
        _start_only(_man(dict(BASE_HASHES, evaluator="not-a-hash"))), require_end=False)
    check("start-only 非法 hash → judge 前就判得出來",
          any("start hash 格式不合法" in p for p in probs))

    _, _, _, probs = record.check_manifest(
        _start_only(_man(BASE_HASHES, schema="bogus")), require_end=False)
    check("start-only 非法 hash_schema → judge 前就判得出來",
          any("start hash_schema 格式不合法" in p for p in probs))

    _, _, _, probs = record.check_manifest(
        _start_only(_man(BASE_HASHES, version=99)), require_end=False)
    check("start-only 不支援的 manifest_version → judge 前就判得出來",
          any("不支援的 manifest_version" in p for p in probs))

    no_files = _start_only(_man(BASE_HASHES))
    no_files["start"]["fixture_files"] = []
    _, _, _, probs = record.check_manifest(no_files, require_end=False)
    check("start-only 缺 fixture_files → 有問題",
          any("缺 fixture_files" in p for p in probs))

    _, _, _, probs = record.check_manifest(_start_only(_cman()), require_end=False)
    check("start-only contract manifest 合法 → 無問題", probs == [], probs)

    drift = dict(BASE_HASHES, runner=H64_B)
    _, _, _, probs = record.check_manifest(_man(BASE_HASHES, drift), require_end=False)
    check("require_end=False 不放行 drift：end 存在就照驗",
          any("domain drift" in p and "runner" in p for p in probs))

    _, _, _, probs = record.check_manifest(_start_only({"manifest_version": 3}),
                                           require_end=False)
    check("連 start 都沒有 → 仍然判缺 start", any("缺 start" in p for p in probs))

    # 端到端：run-rescore.sh 傳進來的 contract manifest 在 preflight 當下只有 start。
    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        json.dump(_start_only(_cman()), open(cman, "w"))
        rc = record.main(raw, "so-ok", cman, source_record=src, validate_only=True)
        check("start-only、same-schema、合法 → preflight 0 且不寫紀錄",
              rc == 0 and not os.path.exists(os.path.join(d, "so-ok.json")))

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d, schema="v3")
        json.dump(_start_only(_cman()), open(cman, "w"))
        rc = record.main(raw, "so-cross", cman, source_record=src, validate_only=True)
        check("start-only、cross-schema、缺 audit → preflight 3（不進付費 judge）",
              rc == 3 and not os.path.exists(os.path.join(d, "so-cross.json")))

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d, schema="v3")
        json.dump(_start_only(_cman()), open(cman, "w"))
        rc = record.main(raw, "so-audit", cman, source_record=src, validate_only=True,
                         migration_audit=audit_file(d))
        check("start-only、cross-schema、合法 audit → preflight 0",
              rc == 0 and not os.path.exists(os.path.join(d, "so-audit.json")))

    with tempfile.TemporaryDirectory() as d:
        raw, src, cman = build_source(d)
        broken = _start_only(_cman())
        del broken["start"]["hashes"]["rescore_runner"]
        json.dump(broken, open(cman, "w"))
        rc = record.main(raw, "so-miss", cman, source_record=src, validate_only=True)
        check("start-only contract manifest 缺 domain → preflight 3",
              rc == 3 and not os.path.exists(os.path.join(d, "so-miss.json")))

    print()
    if fails:
        print("record_selftest: FAIL %d 項" % len(fails))
        return 1
    print("record_selftest: 全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
