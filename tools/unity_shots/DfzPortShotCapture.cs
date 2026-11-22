// dfz-port 앱 화면 캡처 — 저장소에 올리지 않는 임시 PlayMode 검사(2026-11-15).
// tools/unity_shots.sh가 스냅샷의 Tests/PlayMode에 넣어 돌리고, 다음 unity_check.sh의 rsync --delete가 지운다.
// 틀은 저장소의 NativeActivityPlayTests(실제 SessionTest 씬 · 실제 입력 라우터 · 16:9 RenderTexture)를 따랐다.
//
// 환경 변수: DFZ_SHOT_GAME  StreamingAssets/games 아래 폴더(예: g015-pair-archery)
//            DFZ_SHOT_TIMES 경기 시작 뒤 찍을 초(쉼표, 기본 "1,4,8,12,16,20")
//            DFZ_SHOT_HUMANS 가짜 사람 수(기본 1 — 나머지는 규칙의 botFill이 봇으로 채운다)
//            DIGITALPE_SHOT_OUT 저장 폴더
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using DigitalFitZone.Core.Input;
using DigitalFitZone.Core.Input.Devices;
using DigitalFitZone.Game.Session;
using DigitalFitZone.UI;
using DigitalFitZone.UI.Session;
using DigitalFitZone.UI.Session.Ugui;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace DigitalFitZone.Tests.PlayMode
{
    public class DfzPortShotCapture
    {
        [UnityTearDown]
        public IEnumerator TearDown() => SessionSceneTeardown.UnloadSessionScene("dfz-port-shot");

        [UnityTest]
        public IEnumerator 앱_경기_화면을_찍는다()
        {
            string game = Environment.GetEnvironmentVariable("DFZ_SHOT_GAME");
            string output = Environment.GetEnvironmentVariable("DIGITALPE_SHOT_OUT");
            if (string.IsNullOrEmpty(game) || string.IsNullOrEmpty(output)) { Assert.Ignore("DFZ_SHOT_GAME·DIGITALPE_SHOT_OUT 없음"); yield break; }
            string timesText = Environment.GetEnvironmentVariable("DFZ_SHOT_TIMES");
            var times = new List<float>();
            foreach (string t in (string.IsNullOrEmpty(timesText) ? "1,4,8,12,16,20" : timesText).Split(','))
            {
                times.Add(float.Parse(t.Trim(), System.Globalization.CultureInfo.InvariantCulture));
            }
            int humans = int.TryParse(Environment.GetEnvironmentVariable("DFZ_SHOT_HUMANS"), out int h) ? h : 1;

#if UNITY_EDITOR
            yield return UnityEditor.SceneManagement.EditorSceneManager.LoadSceneAsyncInPlayMode(
                "Assets/DigitalFitZone/Scenes/SessionTest.unity", new LoadSceneParameters(LoadSceneMode.Single));
#endif
            for (int i = 0; i < 10; i++) yield return null;
            var controller = UnityEngine.Object.FindAnyObjectByType<SessionController>();
            var host = InputRouterHost.Instance;
            Assert.That(controller, Is.Not.Null);
            UnityEngine.Object.FindAnyObjectByType<DigitalFitZone.UI.Home.HomeScreen>()?.Close();
            // DFZ_SHOT_INTRO=1 이면 안내 단계(동작 연습)를 찍는다 — 안내를 길게 두고 시작하지 않는다
            bool introShot = Environment.GetEnvironmentVariable("DFZ_SHOT_INTRO") == "1";
            controller.Config.introSeconds = introShot ? 600 : 0;
            // DFZ_SHOT_PRACTICE=1 이면 연습 판(N 키 「연습 중」)으로 돈다
            if (Environment.GetEnvironmentVariable("DFZ_SHOT_PRACTICE") == "1") controller.SetPractice(true);

            Canvas canvas = UiCanvasBootstrap.Ensure().Canvas;
            var viewport = new GameObject("dfz-port-shot-viewport").AddComponent<Camera>();
            var target = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32);
            viewport.orthographic = true;
            viewport.clearFlags = CameraClearFlags.SolidColor;
            viewport.backgroundColor = DesignTokens.Navy;
            viewport.targetTexture = target;
            viewport.transform.position = new Vector3(0, 0, -500);
            canvas.renderMode = RenderMode.ScreenSpaceCamera;
            canvas.worldCamera = viewport;
            canvas.planeDistance = 100;
            var devices = new List<FakeInputDevice>();
            try
            {
                Canvas.ForceUpdateCanvases();
                yield return null;
                string relative = "games/" + game + "/ruleset.json";
                Assert.That(controller.SwitchRuleSet(File.ReadAllText(Path.Combine(Application.streamingAssetsPath, relative)),
                    out var error, SessionController.FolderOfStreaming(relative)), Is.True, error);
                for (int seat = 0; seat < humans; seat++)
                {
                    // 누르기 장치 — 사람 차례에 화면 가운데를 쏜다. 나머지 조준·쏘기는 봇이 한다.
                    var d = new FakeInputDevice("DFZ-SHOT-" + seat, host.Clock, FakeDeviceMode.Synthetic,
                        controller.RuleSet.Inputs.DeviceKinds[0]) { SyntheticHz = 0.5f, SyntheticAction = InputAction.Press };
                    d.ConnectAsync(CancellationToken.None);
                    host.RegisterDevice(d);
                    devices.Add(d);
                }
                // 봇(TeamBots)은 대기 화면에서 몇 프레임 뒤에 들어온다 — 최소 인원이 찰 때까지 기다린 뒤 시작한다.
                int need = Math.Max(humans, controller.RuleSet.Players.Min);
                yield return TestWait.Until(() => controller.Runner.Roster.Count >= need, 10,
                    $"참가 인원이 모자라다(필요 {need})");
                for (int i = 0; i < 30 && controller.Runner.State == SessionState.Lobby; i++)
                {
                    controller.RequestStart();
                    yield return new WaitForSeconds(0.2f);
                }
                SessionState want = introShot ? SessionState.Intro : SessionState.Play;
                yield return TestWait.Until(() => controller.Runner.State == want, 15, "그 단계에 들어가지 못했다: " + want);
                Directory.CreateDirectory(output);
                float started = Time.realtimeSinceStartup;
                foreach (float at in times)
                {
                    while (Time.realtimeSinceStartup - started < at) yield return null;
                    Canvas.ForceUpdateCanvases();
                    viewport.Render();
                    var before = RenderTexture.active;
                    RenderTexture.active = target;
                    var shot = new Texture2D(1920, 1080, TextureFormat.RGBA32, false);
                    shot.ReadPixels(new Rect(0, 0, 1920, 1080), 0, 0);
                    shot.Apply();
                    RenderTexture.active = before;
                    try { File.WriteAllBytes(Path.Combine(output, $"{game}-{at:00}s.png"), shot.EncodeToPNG()); }
                    finally { UnityEngine.Object.DestroyImmediate(shot); }
                }
                controller.RequestAbort();
            }
            finally
            {
                foreach (var d in devices) { d.DisconnectAsync(); host?.UnregisterDevice(d); }
                viewport.targetTexture = null;
                UnityEngine.Object.DestroyImmediate(viewport.gameObject);
                target.Release();
                UnityEngine.Object.DestroyImmediate(target);
            }
        }
    }
}
