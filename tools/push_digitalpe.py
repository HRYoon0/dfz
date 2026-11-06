# 복제 없이 GitHub API로 EduFit-Tech/digitalpe의 작업 브랜치에 커밋한다.
# 사용: python3 -I tools/push_digitalpe.py <이식 폴더> <브랜치> <커밋 메시지 파일>
#   이식 폴더(port/<slug>) 안의 파일을 저장소의 같은 경로로 올린다. 브랜치가 없으면 기준 브랜치에서 새로 판다.
#   보호 브랜치(main, 옛 본줄기 feature/stage-1-4a)에는 올리지 않는다 — main으로는 PR로만 들어간다.
#   2026-11-06 저장소 본줄기가 main으로 바뀌었다(주개발자 「main에서 가지 만들고 PR 대상도 main」).
import base64, json, os, subprocess, sys

REPO = "EduFit-Tech/digitalpe"
BASE = "main"
PROTECTED = {BASE, "feature/stage-1-4a"}


def api(path, method="GET", body=None):
    cmd = ["gh", "api", "-X", method, path]
    if body is not None:
        cmd += ["--input", "-"]
    r = subprocess.run(cmd, input=json.dumps(body) if body is not None else None, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"실패 {method} {path}: {r.stderr or r.stdout}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def main():
    if len(sys.argv) != 4:
        raise SystemExit("사용: push_digitalpe.py <이식 폴더> <브랜치> <커밋 메시지 파일>")
    src, branch, msg_file = sys.argv[1], sys.argv[2], sys.argv[3]
    if branch in PROTECTED or not branch.startswith("claude/"):
        raise SystemExit(f"올릴 수 없는 브랜치: {branch} (claude/… 만)")
    msg = open(msg_file, encoding="utf-8").read()
    if "Co-Authored-By:" not in msg:
        raise SystemExit("커밋 메시지 끝에 Co-Authored-By 줄이 없다")

    try:
        head = api(f"repos/{REPO}/git/ref/heads/{branch}")["object"]["sha"]
        exists = True
    except SystemExit:
        head = api(f"repos/{REPO}/git/ref/heads/{BASE}")["object"]["sha"]
        exists = False
    base_tree = api(f"repos/{REPO}/git/commits/{head}")["tree"]["sha"]

    entries = []
    for root, _, files in os.walk(src):
        for f in sorted(files):
            if f == ".DS_Store":
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, src)
            data = open(full, "rb").read()
            blob = api(f"repos/{REPO}/git/blobs", "POST", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
            entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    if not entries:
        raise SystemExit("올릴 파일이 없다")

    tree = api(f"repos/{REPO}/git/trees", "POST", {"base_tree": base_tree, "tree": entries})
    if tree["sha"] == base_tree:
        print("바뀐 것이 없다 — 커밋하지 않음")
        return
    commit = api(f"repos/{REPO}/git/commits", "POST", {"message": msg, "tree": tree["sha"], "parents": [head]})
    if exists:
        api(f"repos/{REPO}/git/refs/heads/{branch}", "PATCH", {"sha": commit["sha"], "force": False})
    else:
        api(f"repos/{REPO}/git/refs", "POST", {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})

    cmp = api(f"repos/{REPO}/compare/{BASE}...{branch}")
    changed = [f["filename"] for f in cmp.get("files", []) if f["status"] != "added"]
    print(f"브랜치 {branch} 커밋 {commit['sha'][:9]} (기준보다 {cmp['ahead_by']}개 앞, {cmp['behind_by']}개 뒤)")
    print("고친 기존 파일:", ", ".join(changed) if changed else "없음")


if __name__ == "__main__":
    main()
