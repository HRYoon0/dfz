// dfz-port 앱 조종용 임시 편집기 스크립트(저장소에 올리지 않음 — 다음 unity_check.sh rsync가 지운다).
// tools/unity_play.sh가 스냅샷의 Assets/DfzLocalEditor/Editor/에 넣는다.
// 화면을 클릭하지 않고(사용자 작업을 방해하지 않게) 명령 파일로 에디터 안에서 앱을 다룬다.
//
//   명령: /tmp/claude/dfz-cmd/cmd.txt 에 한 줄씩 → 결과: /tmp/claude/dfz-cmd/out.txt 에 덧붙임
//   play | stop | login | pick <폴더 일부> | start | skipintro | state | shot <경로>
//   로그인 계정·비밀번호는 맥 키체인(서비스 dfz-portal)에서 읽는다 — 파일에 두지 않는다.
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

[InitializeOnLoad]
static class DfzDriver
{
    const string Dir = "/tmp/claude/dfz-cmd";
    static double _next;

    static DfzDriver()
    {
        Directory.CreateDirectory(Dir);
        EditorApplication.update += Tick;
        if (!SessionState.GetBool("dfz-open-play", false)) EditorApplication.update += AutoPlay;
    }

    // 에디터를 처음 열면 임포트·컴파일이 끝난 뒤 한 번 Play
    static void AutoPlay()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating) return;
        EditorApplication.update -= AutoPlay;
        SessionState.SetBool("dfz-open-play", true);
        Play();
    }

    static void Play()
    {
        if (EditorApplication.isPlayingOrWillChangePlaymode) return;
        EditorSceneManager.OpenScene("Assets/DigitalFitZone/Scenes/SessionTest.unity");
        EditorApplication.EnterPlaymode();
    }

    static void Tick()
    {
        if (EditorApplication.timeSinceStartup < _next) return;
        _next = EditorApplication.timeSinceStartup + 0.05;
        string cmdFile = Path.Combine(Dir, "cmd.txt");
        if (!File.Exists(cmdFile)) return;
        string[] lines = File.ReadAllLines(cmdFile);
        File.Delete(cmdFile);
        foreach (string raw in lines)
        {
            string line = raw.Trim();
            if (line.Length == 0) continue;
            string result;
            try { result = Run(line); }
            catch (Exception e) { result = "오류 " + e.GetType().Name + ": " + e.Message; }
            File.AppendAllText(Path.Combine(Dir, "out.txt"), DateTime.Now.ToString("HH:mm:ss") + " " + line + " → " + result + "\n");
        }
    }

    static Type T(string name) => AppDomain.CurrentDomain.GetAssemblies()
        .Select(a => a.GetType(name, false)).FirstOrDefault(t => t != null);

    static object Find(string typeName)
    {
        Type t = T(typeName);
        return t == null ? null : UnityEngine.Object.FindAnyObjectByType(t);
    }

    const BindingFlags All = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;

    static object Get(object o, string member)
    {
        Type t = o as Type ?? o.GetType();
        object target = o is Type ? null : o;
        var f = t.GetField(member, All);
        if (f != null) return f.GetValue(target);
        var p = t.GetProperty(member, All);
        return p?.GetValue(target);
    }

    static string Run(string line)
    {
        string[] parts = line.Split(new[] { ' ' }, 2);
        string arg = parts.Length > 1 ? parts[1].Trim() : "";
        switch (parts[0])
        {
            case "play": Play(); return "Play 요청";
            case "stop": EditorApplication.ExitPlaymode(); return "멈춤 요청";
            // 창에 초점이 없으면 바뀐 스크립트를 읽지 않는다 — 멈춘 뒤 refresh로 다시 읽힌다
            case "refresh": AssetDatabase.Refresh(); return "다시 읽기 요청";
            case "quit": EditorApplication.Exit(0); return "끝냄";
            case "shot":
                ScreenCapture.CaptureScreenshot(arg);
                return "찍음(프레임 끝에 저장)";
            case "login": return Login();
            case "pick": return Pick(arg, prepare: false);
            // 로비 카드 → 묶음 창에서 고른 것과 같은 길(HomeScreen.PrepareChosen: 켜고 → 안내 → 홈 닫기)
            case "prepare": return Pick(arg, prepare: true);
            case "start":
            {
                var c = Find("DigitalFitZone.Game.Session.SessionController");
                return "RequestStart=" + c.GetType().GetMethod("RequestStart", Type.EmptyTypes).Invoke(c, null);
            }
            case "skipintro":
            {
                var c = Find("DigitalFitZone.Game.Session.SessionController");
                return "RequestSkipIntro=" + c.GetType().GetMethod("RequestSkipIntro").Invoke(c, null);
            }
            case "state": return State();
            case "maze": return Maze();
            case "cam": return Cam(arg);
            // dig <감독 형식 이름 끝부분> [속성.속성 …] — 장면에서 그 객체를 찾아 간단한 값들을 찍는다
            case "dig": return DigCmd(arg);
            case "kids": return Kids();
            // 창이 초점을 잃으면 앱이 판을 멈춘다(SessionHud.OnApplicationFocus) — 흉내 확인 중에는 다시 푼다
            case "resume":
            {
                var c = Find("DigitalFitZone.Game.Session.SessionController");
                var r = Get(c, "Runner");
                if (r == null || !"Paused".Equals("" + SafeGet(r, "State"))) return "멈춤 아님";
                return "RequestPauseToggle=" + c.GetType().GetMethod("RequestPauseToggle").Invoke(c, null);
            }
            // 연습 판(N 키 「연습 중」) — 기록·순위에 올리지 않는다. 확인용 판은 늘 이것으로
            case "practice":
            {
                var c = Find("DigitalFitZone.Game.Session.SessionController");
                c.GetType().GetMethod("SetPractice").Invoke(c, new object[] { arg != "off" });
                return "IsPractice=" + SafeGet(c, "IsPractice");
            }
            default: return "모르는 명령";
        }
    }

    static string Login()
    {
        var screen = Find("DigitalFitZone.UI.Setup.AppLoginScreen");
        if (screen == null) return "로그인 화면 없음(이미 들어감?)";
        string Sec(string args)
        {
            var psi = new System.Diagnostics.ProcessStartInfo("/usr/bin/security", args) { RedirectStandardOutput = true, UseShellExecute = false };
            using (var p = System.Diagnostics.Process.Start(psi)) { string o = p.StandardOutput.ReadToEnd(); p.WaitForExit(); return o; }
        }
        var acct = System.Text.RegularExpressions.Regex.Match(Sec("find-generic-password -s dfz-portal"), "\"acct\"<blob>=\"([^\"]+)\"");
        if (!acct.Success) return "키체인에 dfz-portal 항목 없음";
        string email = acct.Groups[1].Value, pw = Sec("find-generic-password -s dfz-portal -w").Trim();
        if (pw.Length == 0) return "키체인에 비밀번호 없음";
        SetText(Get(screen, "_email"), email);
        SetText(Get(screen, "_password"), pw);
        screen.GetType().GetMethod("Submit", All).Invoke(screen, null);
        return "제출함";
    }

    static void SetText(object field, string text) => field.GetType().GetProperty("text").SetValue(field, text);

    static string Pick(string part, bool prepare)
    {
        Type picker = T("DigitalFitZone.UI.Setup.GamePickerScreen");
        var list = ((System.Collections.IEnumerable)picker.GetMethod("Installed", All, null, Type.EmptyTypes, null).Invoke(null, null)).Cast<object>().ToList();
        var hits = list.Where(e => ((string)Get(e, "Token")).Contains(part)).ToList();
        if (hits.Count != 1)
            return "후보 " + hits.Count + "개: " + string.Join(" | ", (hits.Count == 0 ? list : hits).Select(e => (string)Get(e, "Token")).Take(12));
        if (prepare)
        {
            var home = Find("DigitalFitZone.UI.Home.HomeScreen");
            if (home == null) return "홈 화면 없음";
            object ok2 = home.GetType().GetMethod("PrepareChosen", All).Invoke(home, new object[] { hits[0], true });
            return "PrepareChosen=" + ok2 + " " + Get(hits[0], "Token");
        }
        var c = Find("DigitalFitZone.Game.Session.SessionController");
        object devices = Get(c, "Devices");
        var m = picker.GetMethod("TryApply", All);
        object[] args = { hits[0], devices, null };
        bool ok = (bool)m.Invoke(null, args);
        return (ok ? "고름 " : "실패 ") + Get(hits[0], "Token") + " — " + args[2];
    }

    static string State()
    {
        var sb = new System.Text.StringBuilder();
        sb.Append(EditorApplication.isPlaying ? "Play중" : "멈춤");
        var login = Find("DigitalFitZone.UI.Setup.AppLoginScreen");
        if (login != null) sb.Append(" | 로그인막음=" + Get(login.GetType(), "BlocksInput"));
        var c = Find("DigitalFitZone.Game.Session.SessionController");
        if (c != null)
        {
            var rules = Get(c, "RuleSet");
            sb.Append(" | 규칙=" + (rules == null ? "-" : Get(rules, "RuleSetId")));
            var runner = Get(c, "Runner");
            if (runner != null)
            {
                foreach (string n in new[] { "State", "CanStart" })
                {
                    var v = SafeGet(runner, n);
                    if (v != null) sb.Append(" | " + n + "=" + v);
                }
            }
            var seats = Get(c, "Seats");
            if (seats != null) sb.Append(" | 자리=" + SafeGet(seats, "Count"));
        }
        var phone = Find("DigitalFitZone.Net.Local.PhoneServerHost");
        if (phone != null) sb.Append(" | 폰주소=" + SafeGet(phone, "JoinUrl") + " 번호=" + SafeGet(phone, "CurrentCode"));
        return sb.ToString();
    }

    static object SafeGet(object o, string n) { try { return Get(o, n); } catch { return null; } }

    // 장면의 MonoBehaviour 필드를 3단계까지 훑어 그 형식의 객체를 찾는다(감독은 MonoBehaviour가 아니다)
    static object Dig(string typeName)
    {
        var seen = new System.Collections.Generic.HashSet<object>();
        var queue = new System.Collections.Generic.Queue<(object, int)>();
        foreach (var mb in UnityEngine.Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include)) queue.Enqueue((mb, 0));
        while (queue.Count > 0)
        {
            var (o, d) = queue.Dequeue();
            if (o == null || !seen.Add(o)) continue;
            if (o.GetType().FullName == typeName) return o;
            if (d >= 3) continue;
            foreach (var f in o.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (f.FieldType.IsPrimitive || f.FieldType == typeof(string) || f.FieldType.IsEnum) continue;
                object v; try { v = f.GetValue(o); } catch { continue; }
                if (v == null || v is UnityEngine.Object && !(v is MonoBehaviour)) continue;
                queue.Enqueue((v, d + 1));
            }
        }
        return null;
    }

    static string Maze()
    {
        var sb = new System.Text.StringBuilder();
        var c = Find("DigitalFitZone.Game.Session.SessionController");
        var runner = c == null ? null : Get(c, "Runner");
        if (runner != null)
        {
            sb.Append("명단:");
            foreach (var p in (System.Collections.IEnumerable)Get(Get(runner, "Roster"), "Participants"))
                sb.Append(" [" + SafeGet(p, "PlayerId") + " 자리" + SafeGet(p, "JoinOrder") + " 팀" + SafeGet(p, "TeamIndex") + (true.Equals(SafeGet(p, "IsBot")) ? " 봇" : "") + "]");
        }
        var dir = Dig("DigitalFitZone.UI.Session.TiltMazeDirector");
        if (dir == null) return sb + " | 감독 없음";
        var round = Get(dir, "Round");
        var practice = Get(dir, "Practice");
        sb.Append(" | 연습단계=" + SafeGet(practice, "Step") + " 시작요청=" + SafeGet(practice, "StartRequested"));
        sb.Append(" | 판:");
        foreach (var m in (System.Collections.IEnumerable)Get(round, "Members"))
            sb.Append(" [" + SafeGet(m, "PlayerId") + " x=" + Fmt(SafeGet(m, "TiltX")) + " y=" + Fmt(SafeGet(m, "TiltY")) + " at=" + Fmt(SafeGet(m, "TiltAt")) + "]");
        sb.Append(" | 단계=" + SafeGet(round, "Phase") + " 차례팀=" + SafeGet(round, "ActiveTeam") + " 시계=" + Fmt(SafeGet(round, "Clock"))
            + " 공=(" + Fmt(SafeGet(round, "X")) + "," + Fmt(SafeGet(round, "Y")) + ") 별=" + SafeGet(round, "Stars"));
        sb.Append(" | 기록:");
        foreach (var r in (System.Collections.IEnumerable)Get(round, "Records"))
            sb.Append(" [팀" + SafeGet(r, "Team") + " 함=" + SafeGet(r, "Played") + " 완주=" + SafeGet(r, "Success") + " 시간=" + Fmt(SafeGet(r, "Time"))
                + " 별=" + SafeGet(r, "Stars") + " 진행=" + Fmt(SafeGet(r, "Progress")) + " 점수=" + SafeGet(r, "Points") + "]");
        return sb.ToString();
    }

    // ---- 카메라 흉내: 제품 안의 시험 이음매(CameraPoseHost.StartWithForTest + FakeFrameSource + FakePoseEstimator).
    //      맥 카메라는 켜지 않는다(얼굴·영상 없음). 골격만 넣는다.
    static object _estimator;

    static string Cam(string arg)
    {
        string[] p = arg.Split(new[] { ' ' }, 2);
        string sub = p[0], rest = p.Length > 1 ? p[1] : "";
        if (sub == "start")
        {
            var host = Find("DigitalFitZone.Vision.Devices.CameraPoseHost");
            if (host == null) return "카메라 호스트 없음";
            // 이미 돌고 있으면 그대로 쓴다(다시 시작은 거절되고 새 추정기만 헛돈다 — 11-26 G021에서 겪음)
            if (_estimator != null && true.Equals(SafeGet(host, "IsRunning"))) return "이미 켜짐(그대로 씀)";
            if (true.Equals(SafeGet(host, "IsRunning"))) host.GetType().GetMethod("StopCamera").Invoke(host, null);
            var est = Activator.CreateInstance(T("DigitalFitZone.Vision.Pose.FakePoseEstimator"), 6, 256);
            object frames = Activator.CreateInstance(T("DigitalFitZone.Vision.Capture.FakeFrameSource"), "Fake Camera");
            object ok = host.GetType().GetMethod("StartWithForTest", All).Invoke(host, new[] { frames, est });
            if (true.Equals(ok)) _estimator = est;
            return "StartWithForTest=" + ok + " " + SafeGet(host, "StartError");
        }
        if (_estimator == null) return "먼저 cam start";
        if (sub == "off") { SetIdle(new object[0]); return "사람 없음"; }
        if (sub == "stop") { var h = Find("DigitalFitZone.Vision.Devices.CameraPoseHost"); h.GetType().GetMethod("StopCamera").Invoke(h, null); _estimator = null; return "끔"; }
        if (sub == "people")
        {
            // 사람마다 ';'로, 사람 안은 '키=값' 공백 구분: x 가운데, h 키(0.6), f 발 높이(0.1), wr 두 손목 높이,
            // lw/rw 손목 x,y · le/re 팔꿈치 · lk/rk 무릎 · la/ra 발목 · hips 엉덩이 높이, dy 전체 위아래
            var list = new System.Collections.Generic.List<object>();
            foreach (string spec in rest.Split(';'))
            {
                if (spec.Trim().Length == 0) continue;
                list.Add(Person(spec.Trim()));
            }
            SetIdle(list.ToArray());
            return list.Count + "명";
        }
        return "cam start | cam off | cam people <spec;spec>";
    }

    static void SetIdle(object[] people)
    {
        Type skel = T("DigitalFitZone.Vision.Pose.PoseSkeleton");
        Array arr = Array.CreateInstance(skel, people.Length);
        for (int i = 0; i < people.Length; i++) arr.SetValue(people[i], i);
        _estimator.GetType().GetProperty("Idle").SetValue(_estimator, arr);
    }

    static object Person(string spec)
    {
        var kv = new System.Collections.Generic.Dictionary<string, string>();
        foreach (string t in spec.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries))
        {
            int e = t.IndexOf('='); if (e > 0) kv[t.Substring(0, e)] = t.Substring(e + 1);
        }
        float F(string k, float d) => kv.TryGetValue(k, out var v) ? float.Parse(v, System.Globalization.CultureInfo.InvariantCulture) : d;
        Type builder = T("DigitalFitZone.Vision.Pose.PoseSkeletonBuilder");
        object s = builder.GetMethod("Standing").Invoke(null, new object[] { F("x", 0.5f), F("f", 0.1f), F("h", 0.6f), 0.9f });
        if (kv.ContainsKey("dy")) s = builder.GetMethod("MovedBy").Invoke(null, new object[] { s, F("dy", 0f) });
        if (kv.ContainsKey("wr")) s = builder.GetMethod("WithWrists").Invoke(null, new object[] { s, F("wr", 0.5f) });
        if (kv.ContainsKey("hips")) s = builder.GetMethod("WithHips").Invoke(null, new object[] { s, F("hips", 0.4f) });
        var kps = (Array)s.GetType().GetField("Keypoints").GetValue(s);
        void SetKp(string key, int index)
        {
            if (!kv.TryGetValue(key, out var v)) return;
            string[] xy = v.Split(',');
            object kp = kps.GetValue(index);
            kp.GetType().GetField("X").SetValue(kp, float.Parse(xy[0], System.Globalization.CultureInfo.InvariantCulture));
            kp.GetType().GetField("Y").SetValue(kp, float.Parse(xy[1], System.Globalization.CultureInfo.InvariantCulture));
            kps.SetValue(kp, index);
        }
        SetKp("le", 7); SetKp("re", 8); SetKp("lw", 9); SetKp("rw", 10); SetKp("lh", 11); SetKp("rh", 12);
        SetKp("lk", 13); SetKp("rk", 14); SetKp("la", 15); SetKp("ra", 16); SetKp("ls", 5); SetKp("rs", 6);
        return s;
    }

    static string DigCmd(string arg)
    {
        string[] parts = arg.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0) return "dig <형식 끝이름> [경로…]";
        object o = DigSuffix(parts[0]);
        if (o == null) return parts[0] + " 없음";
        var sb = new System.Text.StringBuilder(o.GetType().Name + ":");
        if (parts.Length == 1) { Describe(o, sb, 1); return sb.ToString(); }
        for (int i = 1; i < parts.Length; i++)
        {
            object v = o;
            foreach (string seg in parts[i].Split('.')) { v = v == null ? null : SafeGet(v, seg); }
            sb.Append(" | " + parts[i] + "=");
            if (v is string || v == null || v.GetType().IsPrimitive || v.GetType().IsEnum) sb.Append(Fmt(v));
            else Describe(v, sb, 1);
        }
        return sb.ToString();
    }

    static object DigSuffix(string suffix)
    {
        var seen = new System.Collections.Generic.HashSet<object>();
        var queue = new System.Collections.Generic.Queue<(object, int)>();
        foreach (var mb in UnityEngine.Object.FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include)) queue.Enqueue((mb, 0));
        while (queue.Count > 0)
        {
            var (o, d) = queue.Dequeue();
            if (o == null || !seen.Add(o)) continue;
            if (o.GetType().Name == suffix || o.GetType().FullName.EndsWith("." + suffix)) return o;
            if (d >= 3) continue;
            foreach (var f in o.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (f.FieldType.IsPrimitive || f.FieldType == typeof(string) || f.FieldType.IsEnum) continue;
                object v; try { v = f.GetValue(o); } catch { continue; }
                if (v == null || v is UnityEngine.Object && !(v is MonoBehaviour)) continue;
                queue.Enqueue((v, d + 1));
            }
        }
        return null;
    }

    static void Describe(object o, System.Text.StringBuilder sb, int depth)
    {
        if (o is System.Collections.IEnumerable en && !(o is string))
        {
            int n = 0; sb.Append(" [");
            foreach (var item in en)
            {
                if (n < 20) { sb.Append(" {"); if (item == null || item.GetType().IsPrimitive || item is string) sb.Append(Fmt(item)); else Describe(item, sb, 0); sb.Append("}"); }
                n++;
            }
            sb.Append(" ]#" + n); return;
        }
        foreach (var pr in o.GetType().GetProperties(BindingFlags.Instance | BindingFlags.Public))
        {
            if (pr.GetIndexParameters().Length > 0) continue;
            Type t = pr.PropertyType;
            if (!(t.IsPrimitive || t.IsEnum || t == typeof(string) || t == typeof(double) || t == typeof(float))) continue;
            object v; try { v = pr.GetValue(o); } catch { continue; }
            sb.Append(" " + pr.Name + "=" + Fmt(v));
        }
        // 읽기 전용 구조체(BandTape 등)는 필드만 있다
        foreach (var fi in o.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public))
        {
            Type t = fi.FieldType;
            if (!(t.IsPrimitive || t.IsEnum || t == typeof(string))) continue;
            sb.Append(" " + fi.Name + "=" + Fmt(fi.GetValue(o)));
        }
    }

    static string Kids()
    {
        var c = Find("DigitalFitZone.Game.Session.SessionController");
        var runner = c == null ? null : Get(c, "Runner");
        if (runner == null) return "세션 없음";
        var sb = new System.Text.StringBuilder("명단:");
        foreach (var p in (System.Collections.IEnumerable)Get(Get(runner, "Roster"), "Participants"))
            sb.Append(" [" + SafeGet(p, "PlayerId") + " 자리" + SafeGet(p, "JoinOrder") + " 팀" + SafeGet(p, "TeamIndex") + " " + SafeGet(p, "DeviceKind") + (true.Equals(SafeGet(p, "IsBot")) ? " 봇" : "") + "]");
        sb.Append(" | State=" + SafeGet(runner, "State"));
        return sb.ToString();
    }

    static string Fmt(object v) => v is double d ? d.ToString("0.00") : v is float f ? f.ToString("0.00") : "" + v;
}
