# digitalpe docs/WORKING.md(「지금 하는 일」 표)에 우리 줄을 적거나 지운다 — 복제 없이 API로, 우리 가지에만.
# 주개발자 규칙(team-onboarding 4·7-2절): 작업을 시작하면 담당 파일을 적고, 끝나면 자기 줄만 지운다.
#
#   python3 -I tools/working_line.py add    <가지> <slug> "<무엇을>" "<어느 파일(폴더)>"
#   python3 -I tools/working_line.py remove <가지> <slug>
#
# 줄은 「Claude(dfz-port <slug>)」로 알아본다. remove는 그 줄만 지우고 다른 줄은 손대지 않는다 —
# 그러면 가지의 WORKING.md가 갈라진 지점과 같아져 main과 합칠 때 충돌하지 않는다.
import base64, datetime, json, subprocess, sys

REPO, PATH = "EduFit-Tech/digitalpe", "docs/WORKING.md"


def api(path, method="GET", body=None):
    cmd = ["gh", "api", "-X", method, path] + (["--input", "-"] if body else [])
    r = subprocess.run(cmd, input=json.dumps(body) if body else None, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"실패 {method} {path}: {r.stderr or r.stdout}")
    return json.loads(r.stdout)


def main():
    if len(sys.argv) < 4 or sys.argv[1] not in ("add", "remove"):
        raise SystemExit(__doc__ or "사용법은 파일 머리말")
    op, branch, slug = sys.argv[1:4]
    if not branch.startswith("claude/"):
        raise SystemExit("claude/… 가지에만 쓴다")
    tag = f"Claude(dfz-port {slug})"
    f = api(f"repos/{REPO}/contents/{PATH}?ref={branch}")
    lines = base64.b64decode(f["content"]).decode("utf-8").split("\n")
    mine = [i for i, l in enumerate(lines) if l.startswith(f"| {tag} |")]

    if op == "add":
        if mine:
            print("이미 있다:", lines[mine[0]]); return
        what, files = sys.argv[4], sys.argv[5]
        row = f"| {tag} | {what}(가지 `{branch}`) | {files} | {datetime.date.today().isoformat()} |"
        last = max(i for i, l in enumerate(lines) if l.startswith("|"))   # 표 마지막 줄 다음에
        lines.insert(last + 1, row)
        msg = f"docs: 지금 하는 일 — {what}"
    else:
        if not mine:
            print("지울 줄이 없다"); return
        for i in reversed(mine):
            del lines[i]
        msg = f"docs: 지금 하는 일 — {slug} 끝, 줄 지움"

    body = {"message": msg + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
            "content": base64.b64encode("\n".join(lines).encode("utf-8")).decode(),
            "sha": f["sha"], "branch": branch}
    r = api(f"repos/{REPO}/contents/{PATH}", "PUT", body)
    print(op, "→", r["commit"]["sha"][:7])


if __name__ == "__main__":
    main()
