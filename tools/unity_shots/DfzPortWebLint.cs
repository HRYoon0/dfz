// dfz-port HTML 판 검사 — 저장소에 올리지 않는 임시 EditMode 검사(2026-11-15).
// tools/web_lint.sh가 스냅샷에 넣어 돌리고 뺀다. 앱이 붙여넣은·AI가 짠 웹 게임에 거는 것과 같은 검사기를 부른다:
//   WebGameLint.Check            — dfz 통로·화면 틀(ui.frame)·점수(dfz.score)·조정값·공통 요소 등 규약
//   WebGameLint.FindClassroomHazards — 글 칸·페이지 이동·동적 코드·WebAssembly
//   WebGameImport.MakeSelfContained  — 바깥 주소(아무것도 받아 주지 않으면 모두 거절 목록에 남는다)
// 환경 변수 DFZ_WEB_HTML = 검사할 HTML 파일 절대 경로.
using System;
using System.IO;
using System.Linq;
using DigitalFitZone.WebHost;
using NUnit.Framework;

namespace DigitalFitZone.Tests.EditMode
{
    public class DfzPortWebLint
    {
        [Test]
        public void HTML_판이_앱_웹_게임_규약을_지킨다()
        {
            string path = Environment.GetEnvironmentVariable("DFZ_WEB_HTML");
            if (string.IsNullOrEmpty(path)) { Assert.Ignore("DFZ_WEB_HTML 없음"); }
            string html = File.ReadAllText(path);

            var lint = WebGameLint.Check(html);
            var hazards = WebGameLint.FindClassroomHazards(html);
            var import = WebGameImport.MakeSelfContained(html, (string r, out byte[] b, out string m) => { b = null; m = null; return false; });

            string report = string.Join("\n", new[]
            {
                lint.Ok ? null : "규약: " + lint.Report(),
                hazards.Count == 0 ? null : "교실 위험: " + string.Join(", ", hazards),
                import.Ok ? null : "바깥 주소: " + string.Join(", ", import.Rejected),
            }.Where(s => s != null));
            UnityEngine.Debug.Log("[dfz-port 웹 검사] " + (report.Length == 0 ? "문제 없음" : report));
            Assert.That(report, Is.Empty, report);
        }
    }
}
