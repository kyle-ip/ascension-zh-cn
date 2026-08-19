using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text.RegularExpressions;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime.Injection;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace AscensionZhCn;

[BepInPlugin("ascension.zh.cn", "Ascension Chinese overlay", "1.5.1")]
public class Plugin : BasePlugin
{
    internal static Plugin Instance;
    static TMP_FontAsset _cjk;
    static bool _installed;
    static bool _attempted;
    static bool _locPatched;
    static bool _inRulebook;
    static bool _rulebookNeedsSweep;
    static int _rulebookSweepIdle;
    static int _rulebookIndex;
    static Component _rulebookRoot;
    static TMP_Text[] _rulebookTmps;
    static bool _cacheDirty = true;
    static int _boostFrames;
    static int _idleFrames;
    static TMP_Text[] _activeTmps;
    static int _activeSlice;
    static TMP_Text[] _allTmps;
    static int _allSlice;
    static string _prewarmChars;
    static int _prewarmAt;
    static bool _ready;
    internal static int LastActiveTmpCount;
    internal static bool IsReady
    {
        get { return _ready; }
    }
    static string LogPath = "";
    static string DumpPath = "";
    static ConfigEntry<bool> DumpUntranslated;
    static ConfigEntry<bool> PrefixSetText;
    static readonly HashSet<string> Dumped = new HashSet<string>();
    const int DumpMax = 2500;
    static Harmony _harmony;
    static MethodInfo _convertEmbedded;
    static int _locDepth;

    internal static readonly Dictionary<string, string> Keys = new Dictionary<string, string>();
    internal static readonly Dictionary<string, string> Exact = new Dictionary<string, string>();

    static readonly Regex DropCap = new Regex(
        @"<size=\s*[^>]*>\s*(.)\s*</size>(?:<space=[^>]*>)?(.*)",
        RegexOptions.IgnoreCase | RegexOptions.Singleline);
    static readonly Regex Tags = new Regex(
        @"</?(?:size|space|color|b|i|u|s|font|mark|allcaps|uppercase|lowercase|smallcaps|sprite)[^>]*>",
        RegexOptions.IgnoreCase);
    static Font _uiCjk;

    public override void Load()
    {
        Instance = this;
        try
        {
            LogPath = Path.Combine(Paths.GameRootPath, "AscensionGame_Data", "StreamingAssets", "zh-cn", "plugin.log");
            DumpPath = Path.Combine(Paths.GameRootPath, "AscensionGame_Data", "StreamingAssets", "zh-cn", "untranslated.tsv");
            Directory.CreateDirectory(Path.GetDirectoryName(LogPath));
            File.WriteAllText(LogPath, DateTime.Now + " plugin Load() 1.5.1 (gallery loc prefix + card exact)\n");
        }
        catch
        {
            LogPath = Path.Combine(Paths.PluginPath, "ascension-zh-cn.log");
            File.WriteAllText(LogPath, DateTime.Now + " plugin Load()\n");
            DumpPath = Path.Combine(Paths.PluginPath, "untranslated.tsv");
        }

        try
        {
            DumpUntranslated = Config.Bind(
                "Debug",
                "DumpUntranslated",
                false,
                "Write unseen English TMP strings to StreamingAssets/zh-cn/untranslated.tsv (can freeze Shop; keep off unless collecting strings)");
            PrefixSetText = Config.Bind(
                "Display",
                "PrefixSetText",
                true,
                "Rewrite short English at TMP text assignment (not SetText). Disable if tutorial crashes.");
            if (DumpUntranslated.Value && !string.IsNullOrEmpty(DumpPath) && !File.Exists(DumpPath))
                File.WriteAllText(DumpPath, "# kind\tsrc\tsample\n# play menus/gallery once, then: python tools/ingest_untranslated.py\n");
        }
        catch (Exception ex)
        {
            Trace("config bind failed: " + ex.Message);
        }

        LoadOverlay();
        PatchLocalization();

        try
        {
            ClassInjector.RegisterTypeInIl2Cpp<CjkFontBehaviour>();
            AddComponent<CjkFontBehaviour>();
            Trace("injected delayed CjkFontBehaviour");
        }
        catch (Exception ex)
        {
            Trace("component inject failed: " + ex);
        }
        Trace("plugin loaded keys=" + Keys.Count + " exact=" + Exact.Count);
        Log.LogInfo("Chinese overlay plugin loaded");
    }

    internal static void Trace(string message)
    {
        try
        {
            if (Instance != null)
                Instance.Log.LogInfo(message);
        }
        catch
        {
        }
        try
        {
            if (!string.IsNullOrEmpty(LogPath))
                File.AppendAllText(LogPath, DateTime.Now.ToString("HH:mm:ss.fff") + " " + message + "\n");
        }
        catch
        {
        }
    }

    static void LoadOverlay()
    {
        var candidates = new[]
        {
            Path.Combine(Paths.GameRootPath, "AscensionGame_Data", "StreamingAssets", "zh-cn", "overlay.tsv"),
            Path.Combine(Paths.PluginPath, "overlay.tsv"),
            Path.Combine(Paths.GameRootPath, "BepInEx", "plugins", "overlay.tsv"),
        };
        string path = null;
        foreach (var cand in candidates)
        {
            if (File.Exists(cand))
            {
                path = cand;
                break;
            }
        }
        if (path == null)
        {
            Trace("overlay.tsv missing");
            SeedBuiltinExact();
            return;
        }
        try
        {
            foreach (var raw in File.ReadAllLines(path))
            {
                var line = raw.TrimEnd('\r');
                if (line.Length == 0 || line[0] == '#')
                    continue;
                var parts = line.Split('\t');
                if (parts.Length < 3)
                    continue;
                var kind = parts[0];
                var src = Unescape(parts[1]);
                var zh = Unescape(parts[2]);
                if (string.IsNullOrEmpty(src) || string.IsNullOrEmpty(zh) || src == zh)
                    continue;
                if (kind == "K")
                    Keys[src] = zh;
                else if (kind == "E")
                {
                    if (src == "Play" || src == "Buy" || src == "OK")
                        continue;
                    AddExact(src, zh);
                }
            }
            Trace("loaded overlay " + path + " keys=" + Keys.Count + " exact=" + Exact.Count);
        }
        catch (Exception ex)
        {
            Trace("overlay load failed: " + ex);
        }
        SeedBuiltinExact();
    }

    static void SeedBuiltinExact()
    {
        void add(string en, string zh)
        {
            if (!Exact.ContainsKey(en))
                AddExact(en, zh);
        }
        add("Menu", "菜单");
        add("Exit", "退出");
        add("Offline", "离线");
        add("Online", "在线");
        add("Music", "音乐");
        add("Sound Effects", "音效");
        add("Cultist Screams", "邪教徒惨叫");
        add("PLAY ALL", "全部打出");
        add("Play All", "全部打出");
        add("Lobby", "大厅");
        add("Back", "返回");
        add("Hero", "英雄");
        add("LOG", "记录");
        add("Log", "记录");
        add("Player", "玩家");
        add("Offline Games", "离线对局");
        add("App Store", "商店");
        add("In-App Store", "商店");
        add("内购店", "商店");
        add("应用商店", "商店");
        add("END TURN", "结束回合");
        add("End Turn", "结束回合");
        add("END\nTURN", "结束回合");
        add("End\nTurn", "结束回合");
        add("Play Your Turn", "请出牌");
        add("Player 1", "玩家 1");
        add("Player 2", "玩家 2");
        add("Player 3", "玩家 3");
        add("Player 4", "玩家 4");
        add("Continue", "继续");
        add("CONTINUE", "继续");
        add("Common", "普通");
        add("Loading cards, please wait...", "正在加载卡牌，请稍候…");
        add("Loading Cards, please wait...", "正在加载卡牌，请稍候…");
        add("Loading rulebook,\nplease wait...", "正在加载规则书，\n请稍候…");
        add("Loading rulebook, please wait...", "正在加载规则书，请稍候…");
        add("Enlightened Hero", "圣贤英雄");
        add("Enlightened Construct", "圣贤神器");
        add("Lifebound Hero", "命约英雄");
        add("Lifebound Construct", "命约神器");
        add("Mechana Hero", "机械英雄");
        add("Mechana Construct", "机械神器");
        add("Void Hero", "虚空英雄");
        add("Void Construct", "虚空神器");
        add("Enlightened Monster", "圣贤怪物");
        add("Lifebound Monster", "命约怪物");
        add("Mechana Monster", "机械怪物");
        add("Void Monster", "虚空怪物");
        add("Common Monster", "普通怪物");
        add("Monster", "怪物");
        add("Enlightened", "圣贤");
        add("Lifebound", "命约");
        add("Mechana", "机械");
        add("Void", "虚空");
        add("Cancel", "取消");
        add("Confirm", "确认");
        add("Achievements", "成就");
        add("All", "全部");
        add("Owned", "已拥有");
        add("Coming Soon", "即将推出");
        add("Now Available", "现已推出");
        add("Stone Blade Newsletter Sign-up", "订阅 Stone Blade 通讯");
        add("Stone Blade Newsletter Sign-Up", "订阅 Stone Blade 通讯");
        add("Sign up to get the latest information and special deals direct to you.", "订阅即可获取最新资讯与优惠，直接发到你的邮箱。");
        add("Downloadable Content", "可下载内容");
        add("Promo 7", "特典 7");
        add("Key Bindings", "按键绑定");
        add("Play Card", "打出卡牌");
        add("Magnify Card", "放大卡牌");
        add("Scroll Magnified Card Left", "放大卡牌向左移");
        add("Scroll Magnified Card Right", "放大卡牌向右移");
        add("Show/Hide Pause Menu", "显示/隐藏暂停菜单");
        add("Unmagnify Card & Close Card Trays", "取消放大并关闭卡牌托盘");
        add("Play All Cards From Hand", "打出全部手牌");
        add("End Your Turn", "结束回合");
        add("Open/Close Construct Tray", "打开/关闭神器托盘");
        add("Open/Close Discard Pile", "打开/关闭弃牌堆");
        add("Open/Close Deck List", "打开/关闭牌库");
        add("Open/Close Void List", "打开/关闭虚空区");
        add("Open/Close Dreamborn List", "打开/关闭梦生列表");
        add("Open/Close Renown Track", "打开/关闭声望轨道");
        add("Event - Monster", "事件 - 怪物");
        add("Event - Enlightened", "事件 - 圣贤");
        add("Event - Lifebound", "事件 - 命约");
        add("Event - Mechana", "事件 - 机械");
        add("Event - Void", "事件 - 虚空");
        add("Event - Common", "事件 - 普通");
        add("Hero - Enlightened", "英雄 - 圣贤");
        add("Hero - Lifebound", "英雄 - 命约");
        add("Hero - Mechana", "英雄 - 机械");
        add("Hero - Void", "英雄 - 虚空");
        add("Construct - Enlightened", "神器 - 圣贤");
        add("Construct - Lifebound", "神器 - 命约");
        add("Construct - Mechana", "神器 - 机械");
        add("Construct - Void", "神器 - 虚空");
        add("Monster - Enlightened", "怪物 - 圣贤");
        add("Monster - Lifebound", "怪物 - 命约");
        add("Monster - Mechana", "怪物 - 机械");
        add("Monster - Void", "怪物 - 虚空");
        add("Monster - Common", "怪物 - 普通");
        add("Event Trophy", "事件战利品");
        add("Event Trophy:", "事件战利品：");
        add("<b>Event Trophy:</b>", "<b>事件战利品：</b>");
    }

    static string Unescape(string value)
    {
        return value
            .Replace("\\\\", "\u0001")
            .Replace("\\n", "\n")
            .Replace("\\r", "\r")
            .Replace("\\t", "\t")
            .Replace("\u0001", "\\");
    }

    static string UnifyNewlines(string value)
    {
        if (string.IsNullOrEmpty(value))
            return value;
        return value.Replace("\r\n", "\n").Replace("\r", "\n");
    }

    /// <summary>
    /// Prefab rulebook bodies mix \r, \t, and uneven blank lines; Exact keys often
    /// use cleaner newlines. Collapse so those still match.
    /// </summary>
    static string CollapseExactKey(string value)
    {
        if (string.IsNullOrEmpty(value))
            return value;
        var s = UnifyNewlines(value).Replace('\t', ' ');
        while (s.Contains("  "))
            s = s.Replace("  ", " ");
        s = Regex.Replace(s, @" *\n *", "\n");
        while (s.Contains("\n\n\n"))
            s = s.Replace("\n\n\n", "\n\n");
        return s.Trim();
    }

    static void AddExact(string en, string zh)
    {
        if (string.IsNullOrEmpty(en) || string.IsNullOrEmpty(zh))
            return;
        Exact[en] = zh;
        var unified = UnifyNewlines(en);
        if (unified != en)
            Exact[unified] = zh;
        var trimmed = unified.Trim();
        if (trimmed != unified && trimmed.Length > 0)
            Exact[trimmed] = zh;
        var collapsed = CollapseExactKey(en);
        if (collapsed.Length > 0)
            Exact[collapsed] = zh;
    }

    internal static void EnsureCjkFallback()
    {
        if (_installed || _attempted)
            return;
        _attempted = true;
        try
        {
            Trace("EnsureCjkFallback begin");
            _cjk = CreateCjkFont();
            if (_cjk == null)
            {
                Trace("Could not create CJK TMP font");
                return;
            }

            var settingsList = TMP_Settings.fallbackFontAssets;
            if (settingsList == null)
            {
                settingsList = new Il2CppSystem.Collections.Generic.List<TMP_FontAsset>();
                TMP_Settings.fallbackFontAssets = settingsList;
                Trace("created fallbackFontAssets list");
            }
            settingsList.Add(_cjk);
            var def = TMP_Settings.defaultFontAsset;
            if (def != null)
            {
                var table = def.fallbackFontAssetTable;
                if (table != null)
                    table.Add(_cjk);
            }
            _installed = true;
            Trace("Attached CJK fallback font");
            QueueGlyphPrewarm();
            _cacheDirty = true;
            _boostFrames = 30;
            Trace("Chinese overlay font ready");
        }
        catch (Exception ex)
        {
            Trace(ex.ToString());
        }
    }

    static void PatchLocalization()
    {
        if (_locPatched)
            return;
        _locPatched = true;
        try
        {
            var locType = AccessTools.TypeByName("LocalizationService");
            if (locType == null)
                Trace("LocalizationService type not found");
            else
            {
            foreach (var method in locType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance))
            {
                if (method.Name != "ConvertEmbeddedLocalizationKeys" && method.Name != "ConvertLocalizationKeys")
                    continue;
                var args = method.GetParameters();
                if (args.Length == 1 && args[0].ParameterType == typeof(string))
                {
                    _convertEmbedded = method;
                    Trace("convert helper " + method);
                    break;
                }
            }
            }
            _harmony = new Harmony("ascension.zh.cn");
            if (locType != null)
            {
            foreach (var method in locType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance))
            {
                if (method.Name != "GetTextByKey")
                    continue;
                try
                {
                    _harmony.Patch(
                        method,
                        prefix: new HarmonyMethod(typeof(Plugin), nameof(LocPrefix)),
                        postfix: new HarmonyMethod(typeof(Plugin), nameof(LocPostfix)));
                    Trace("patched " + method);
                }
                catch (Exception ex)
                {
                    try
                    {
                        _harmony.Patch(
                            method,
                            prefix: new HarmonyMethod(typeof(Plugin), nameof(LocPrefixNoInstance)),
                            postfix: new HarmonyMethod(typeof(Plugin), nameof(LocPostfix)));
                        Trace("patched (no instance) " + method);
                    }
                    catch (Exception ex2)
                    {
                        Trace("skip " + method + " : " + ex.Message + " / " + ex2.Message);
                    }
                }
            }
            }
            PatchRulebookUi();
            PatchUiTransitions();
            if (PrefixSetText == null || PrefixSetText.Value)
                PatchSetTextPrefix();
            else
                Trace("PrefixSetText disabled");
        }
        catch (Exception ex)
        {
            Trace("Harmony loc patch failed: " + ex);
        }
    }

    static void PatchSetTextPrefix()
    {
        if (_harmony == null)
            return;
        PatchSetter(typeof(TMP_Text));
        PatchSetter(typeof(Text));
    }

    static void PatchSetter(Type type)
    {
        if (type == null)
            return;
        foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly))
        {
            if (method.Name != "set_text")
                continue;
            var args = method.GetParameters();
            if (args.Length != 1)
                continue;
            var first = args[0].ParameterType;
            if (first != typeof(string) && first.Name != "String")
                continue;
            try
            {
                _harmony.Patch(method, prefix: new HarmonyMethod(typeof(Plugin), nameof(SetTextPrefix)));
                Trace("patched prefix " + type.Name + "." + method);
            }
            catch (Exception ex)
            {
                Trace("skip set_text " + type.Name + ": " + ex.Message);
            }
        }
    }

    // Prefix only — do not patch SetText, do not assign tmp.text here (that recursed and crashed).
    static void SetTextPrefix(ref string __0)
    {
        if (_inRulebook || string.IsNullOrEmpty(__0) || __0.Length > 2000)
            return;
        try
        {
            if (HasCjk(__0) && __0.IndexOf("Reward:", StringComparison.Ordinal) < 0
                && __0.IndexOf("Loading", StringComparison.OrdinalIgnoreCase) < 0)
                return;
            string zh;
            if (TryExact(__0, out zh))
            {
                __0 = zh;
                return;
            }
            if (__0.Length > 160)
                return;
            zh = TranslateDisplay(__0);
            if (zh != null && zh != __0)
                __0 = zh;
        }
        catch
        {
        }
    }

    static void PatchUiTransitions()
    {
        if (_harmony == null)
            return;
        var type = AccessTools.TypeByName("ScreenManager");
        if (type == null)
        {
            Trace("ScreenManager type not found");
            return;
        }
        var names = new HashSet<string> { "PushScene", "PopScene", "EnterScene", "EnterScene2" };
        var patched = 0;
        foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static))
        {
            if (!names.Contains(method.Name))
                continue;
            try
            {
                _harmony.Patch(method, postfix: new HarmonyMethod(typeof(Plugin), nameof(UiDirtyPostfix)));
                patched++;
                Trace("patched " + method);
            }
            catch (Exception ex)
            {
                Trace("skip " + method + " : " + ex.Message);
            }
        }
        Trace("ScreenManager patches " + patched);
    }

    static void UiDirtyPostfix()
    {
        _cacheDirty = true;
        _boostFrames = 20;
        _activeSlice = 0;
    }

    static void MaybeDump(string kind, string src, string sample)
    {
        try
        {
            if (DumpUntranslated == null || !DumpUntranslated.Value)
                return;
            if (string.IsNullOrEmpty(src) || string.IsNullOrEmpty(DumpPath) || Dumped.Count >= DumpMax)
                return;
            if (kind == "E")
            {
                if (src.IndexOf("${", StringComparison.Ordinal) >= 0)
                    return;
                if (src.Length > 180)
                    return;
                if (src.Length < 60 && src.IndexOf("<sprite", StringComparison.OrdinalIgnoreCase) >= 0)
                    return;
                if (!LooksEnglishUi(src))
                    return;
            }
            var token = kind + "\t" + src;
            if (!Dumped.Add(token))
                return;
            var line = kind + "\t" + EscapeDump(src);
            if (!string.IsNullOrEmpty(sample) && sample != src)
                line += "\t" + EscapeDump(sample);
            File.AppendAllText(DumpPath, line + "\n");
        }
        catch
        {
        }
    }

    static bool LooksEnglishUi(string text)
    {
        if (text.Length < 3 || text.Length > 4000 || HasCjk(text))
            return false;
        var letters = 0;
        foreach (var ch in text)
        {
            if ((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z'))
                letters++;
        }
        if (text.Length > 400)
            return letters >= 20;
        return letters >= 3;
    }

    static string EscapeDump(string value)
    {
        return value.Replace("\\", "\\\\").Replace("\r", "\\r").Replace("\n", "\\n").Replace("\t", "\\t");
    }

    static bool LocPrefixNoInstance(string __0, ref string __result)
    {
        return LocPrefix(null, __0, ref __result);
    }

    static bool LocPrefix(object __instance, string __0, ref string __result)
    {
        if (_locDepth > 8 || string.IsNullOrEmpty(__0))
            return true;
        try
        {
            if (!Keys.TryGetValue(__0, out var zh) || string.IsNullOrEmpty(zh))
                return true;
            _locDepth++;
            try
            {
                __result = ExpandEmbedded(__instance, zh);
            }
            finally
            {
                _locDepth--;
            }
            return false;
        }
        catch
        {
            return true;
        }
    }

    static string ExpandEmbedded(object instance, string zh)
    {
        if (string.IsNullOrEmpty(zh) || zh.IndexOf("${", StringComparison.Ordinal) < 0)
            return zh;
        if (_convertEmbedded != null)
        {
            try
            {
                var target = _convertEmbedded.IsStatic ? null : instance;
                var converted = _convertEmbedded.Invoke(target, new object[] { zh }) as string;
                if (!string.IsNullOrEmpty(converted))
                    return converted;
            }
            catch
            {
            }
        }
        return ExpandPlaceholders(zh);
    }

    static string ExpandPlaceholders(string zh)
    {
        var start = zh.IndexOf("${", StringComparison.Ordinal);
        if (start < 0)
            return zh;
        var sb = new System.Text.StringBuilder(zh.Length + 16);
        var i = 0;
        while (i < zh.Length)
        {
            start = zh.IndexOf("${", i, StringComparison.Ordinal);
            if (start < 0)
            {
                sb.Append(zh, i, zh.Length - i);
                break;
            }
            sb.Append(zh, i, start - i);
            var end = zh.IndexOf('}', start + 2);
            if (end < 0)
            {
                sb.Append(zh, start, zh.Length - start);
                break;
            }
            var key = zh.Substring(start + 2, end - start - 2);
            string inner;
            if (Keys.TryGetValue(key, out inner) && !string.IsNullOrEmpty(inner))
            {
                if (inner.IndexOf("${", StringComparison.Ordinal) >= 0)
                    sb.Append(ExpandEmbedded(null, inner));
                else
                    sb.Append(inner);
            }
            else
                sb.Append(zh, start, end + 1 - start);
            i = end + 1;
        }
        return sb.ToString();
    }

    static void LocPostfix(string __0, ref string __result)
    {
        try
        {
            if (string.IsNullOrEmpty(__0))
                return;
            if (!Keys.TryGetValue(__0, out var zh) || string.IsNullOrEmpty(zh))
            {
                MaybeDump("K", __0, __result);
                return;
            }
            if (!string.IsNullOrEmpty(__result) && HasCjk(__result) && __result.IndexOf("${", StringComparison.Ordinal) < 0)
                return;
            __result = ExpandEmbedded(null, zh);
        }
        catch
        {
        }
    }

    static bool HasCjk(string text)
    {
        foreach (var ch in text)
        {
            if (ch >= 0x4E00 && ch <= 0x9FFF)
                return true;
        }
        return false;
    }

    static string NormalizeUi(string text)
    {
        // Drop-cap first: gallery filters are "<size=141%>M</size>onster".
        // Stripping <size> tags before this leaves "M onster" and breaks Exact maps.
        var s = DropCap.Replace(text ?? "", "$1$2");
        s = Tags.Replace(s, " ");
        s = s.Replace('\u00a0', ' ').Replace('\r', ' ').Replace('\n', ' ');
        while (s.Contains("  "))
            s = s.Replace("  ", " ");
        return s.Trim();
    }

    static string RewriteClickPrompt(string text)
    {
        var next = text;
        next = Regex.Replace(next, @"\s*to Continue\.?", " 继续", RegexOptions.IgnoreCase);
        next = Regex.Replace(next, @"\s*TO CONTINUE\.?", " 继续", RegexOptions.IgnoreCase);
        next = Regex.Replace(next, @"\s*the End Turn button", " 结束回合按钮", RegexOptions.IgnoreCase);
        return next != text ? next : null;
    }

    static string RewritePlayerNames(string text)
    {
        var stripped = NormalizeUi(text);
        if (Regex.IsMatch(stripped, @"^Player \d+$"))
            return stripped.Replace("Player ", "玩家 ");
        if (Regex.IsMatch(stripped, @"^AI Player \d+$"))
            return stripped.Replace("AI Player ", "AI 玩家 ");
        var lines = text.Replace("\r\n", "\n").Split('\n');
        if (lines.Length < 2)
            return null;
        for (var i = 0; i < lines.Length; i++)
        {
            var line = lines[i].Trim();
            if (line.Length == 0)
                continue;
            if (!Regex.IsMatch(line, @"^(?:AI )?Player \d+$"))
                return null;
        }
        return text.Replace("AI Player ", "AI 玩家 ").Replace("Player ", "玩家 ");
    }

    static readonly Regex FactionFilter = new Regex(
        @"^(Monster|Enlightened|Lifebound|Mechana|Void|Common)(?:\s+(Hero|Construct|Monster))?\s*(\d+)?$",
        RegexOptions.IgnoreCase);
    static readonly Dictionary<string, string> Factions = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
    {
        { "Monster", "怪物" },
        { "Enlightened", "圣贤" },
        { "Lifebound", "命约" },
        { "Mechana", "机械" },
        { "Void", "虚空" },
        { "Common", "普通" },
    };
    static readonly Dictionary<string, string> CardTypes = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
    {
        { "Hero", "英雄" },
        { "Construct", "神器" },
        { "Monster", "怪物" },
        { "Event", "事件" },
        { "Treasure", "宝藏" },
        { "Soul Gem", "灵魂宝石" },
        { "Portal", "传送门" },
        { "Temple", "神殿" },
    };
    static readonly Regex TypeFactionLine = new Regex(
        @"^(Event|Hero|Construct|Monster|Treasure|Soul Gem|Portal|Temple)\s*[-–—]\s*(Enlightened|Lifebound|Mechana|Void|Monster|Common)$",
        RegexOptions.IgnoreCase);

    static string ReplaceRemainders(string text)
    {
        var next = text;
        next = Regex.Replace(
            next,
            @"\(?The Cultist does not go to the void when defeated\.\s*You can defeat the Cultist any number of times each turn\.\)?",
            "（邪教徒被击败后不会进入虚空区。每回合可以任意次数击败邪教徒。）",
            RegexOptions.IgnoreCase);
        next = Regex.Replace(
            next,
            @"(.+?) does not go to the void when defeated\.\s*You can defeat (?:the )?(.+?) any number of times each turn\.",
            "$1被击败后不会进入虚空区。每回合可以任意次数击败$2。",
            RegexOptions.IgnoreCase);
        next = Regex.Replace(next, @"Reward:\s*Gain\s+(\d+)\s*H\.?", "奖励：获得$1荣誉。", RegexOptions.IgnoreCase);
        next = Regex.Replace(next, @"Reward:\s*(\d+)\s*Honor\.?", "奖励：$1荣誉", RegexOptions.IgnoreCase);
        next = next.Replace("Loading cards, please wait...", "正在加载卡牌，请稍候…");
        next = next.Replace("Loading Cards, please wait...", "正在加载卡牌，请稍候…");
        next = next.Replace("Loading cards, please wait", "正在加载卡牌，请稍候");
        next = next.Replace("Loading rulebook,\nplease wait...", "正在加载规则书，\n请稍候…");
        next = next.Replace("Loading rulebook, please wait...", "正在加载规则书，请稍候…");
        next = Regex.Replace(next, @"\bReward:\s*", "奖励：", RegexOptions.IgnoreCase);
        next = Regex.Replace(next, @"Purchase:\s*\$(\d+(?:\.\d+)?)", "购买：$$$1");
        next = Regex.Replace(next, @"\bPromo\s+(\d+)\b", "特典 $1", RegexOptions.IgnoreCase);
        return next != text ? next : null;
    }

    internal static string Rewrite(string text)
    {
        if (string.IsNullOrEmpty(text))
            return null;
        if (text.IndexOf("CLICK", StringComparison.OrdinalIgnoreCase) >= 0
            || text.IndexOf("<link", StringComparison.OrdinalIgnoreCase) >= 0)
        {
            return RewriteClickPrompt(text);
        }
        var remainder = ReplaceRemainders(text);
        if (remainder != null)
            text = remainder;
        if (text.Contains("${"))
            return remainder;
        if (HasCjk(text))
        {
            var mixed = ReplaceRemainders(text);
            return mixed ?? remainder;
        }
        string zh;
        if (TryExact(text, out zh))
            return zh;
        var trimmed = text.Trim();
        if (trimmed != text && TryExact(trimmed, out zh))
            return zh;
        var unified = UnifyNewlines(text);
        if (unified != text && TryExact(unified, out zh))
            return zh;
        var normalized = NormalizeUi(text);
        if (normalized.Length != 0 && TryExact(normalized, out zh))
            return zh;
        if (trimmed.Length <= 4 && trimmed != "Menu" && trimmed != "Exit" && trimmed != "VOID" && trimmed != "Back" && trimmed != "Hero" && trimmed != "LOG")
            return null;
        var names = RewritePlayerNames(text);
        if (names != null)
            return names;
        if (Regex.IsMatch(normalized, @"^Round \d+$"))
            return "第 " + normalized.Substring(6) + " 回合";
        var faction = FactionFilter.Match(normalized.Length > 0 ? normalized : trimmed);
        if (faction.Success)
        {
            string label;
            if (Factions.TryGetValue(faction.Groups[1].Value, out label))
            {
                if (faction.Groups[2].Success && faction.Groups[2].Value.Length > 0)
                {
                    string type;
                    if (CardTypes.TryGetValue(faction.Groups[2].Value, out type))
                        label = label + type;
                }
                if (faction.Groups[3].Success && faction.Groups[3].Value.Length > 0)
                    return label + " " + faction.Groups[3].Value;
                return label;
            }
        }
        var typeLine = TypeFactionLine.Match(normalized.Length > 0 ? normalized : trimmed);
        if (typeLine.Success)
        {
            string typeZh;
            string factionZh;
            if (CardTypes.TryGetValue(typeLine.Groups[1].Value, out typeZh)
                && Factions.TryGetValue(typeLine.Groups[2].Value, out factionZh))
                return typeZh + " - " + factionZh;
        }
        return remainder;
    }

    static bool TryExact(string text, out string zh)
    {
        zh = null;
        if (string.IsNullOrEmpty(text))
            return false;
        if (Exact.TryGetValue(text, out zh) && zh != text)
            return true;
        var unified = UnifyNewlines(text);
        if (unified != text && Exact.TryGetValue(unified, out zh) && zh != unified)
            return true;
        var collapsed = CollapseExactKey(text);
        if (collapsed.Length > 0 && collapsed != text && collapsed != unified
            && Exact.TryGetValue(collapsed, out zh) && zh != collapsed)
            return true;
        return false;
    }

    static void PatchRulebookUi()
    {
        if (_harmony == null)
            return;
        try
        {
            var type = AccessTools.TypeByName("UI_Rulebook");
            if (type == null)
            {
                Trace("UI_Rulebook type not found");
                return;
            }
            var patched = 0;
            foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static))
            {
                if (method.Name != "TurnOnRulebook" && method.Name != "RebuildRulebookObj")
                    continue;
                try
                {
                    _harmony.Patch(
                        method,
                        prefix: new HarmonyMethod(typeof(Plugin), nameof(RulebookPrefix)),
                        postfix: new HarmonyMethod(typeof(Plugin), nameof(RulebookPostfix)));
                    patched++;
                    Trace("patched " + method);
                }
                catch (Exception ex)
                {
                    Trace("skip " + method + " : " + ex.Message);
                }
            }
            Trace("UI_Rulebook patches " + patched);
        }
        catch (Exception ex)
        {
            Trace("UI_Rulebook patch failed: " + ex.Message);
        }
    }

    static void RulebookPrefix()
    {
        _inRulebook = true;
    }

    static void RulebookPostfix(object __instance)
    {
        _inRulebook = false;
        _rulebookRoot = __instance as Component;
        _rulebookTmps = null;
        _rulebookIndex = 0;
        _rulebookNeedsSweep = true;
        _rulebookSweepIdle = 0;
        _cacheDirty = true;
        _boostFrames = 20;
    }

    internal static void SweepPendingRulebook()
    {
        if (!_rulebookNeedsSweep)
            return;
        try
        {
            var go = _rulebookRoot == null ? null : _rulebookRoot.gameObject;
            if (go == null)
            {
                _rulebookNeedsSweep = false;
                return;
            }
            if (_rulebookTmps == null)
            {
                _rulebookTmps = go.GetComponentsInChildren<TMP_Text>(false);
                _rulebookIndex = 0;
                return;
            }
            var changed = SliceTmp(_rulebookTmps, ref _rulebookIndex, 10, false);
            if (changed == 0)
                _rulebookSweepIdle++;
            else
                _rulebookSweepIdle = 0;
            if (_rulebookIndex == 0 && _rulebookSweepIdle >= 2)
                _rulebookNeedsSweep = false;
            if (changed > 0)
                Trace("rulebook sweep " + changed);
        }
        catch (Exception ex)
        {
            Trace("SweepPendingRulebook: " + ex.Message);
            _rulebookNeedsSweep = false;
        }
    }

    static void QueueGlyphPrewarm()
    {
        try
        {
            var seen = new HashSet<char>();
            void add(string s)
            {
                if (string.IsNullOrEmpty(s))
                    return;
                foreach (var ch in s)
                {
                    if (ch >= 0x4E00 && ch <= 0x9FFF)
                        seen.Add(ch);
                }
            }
            foreach (var zh in Keys.Values)
                add(zh);
            foreach (var kv in Exact)
            {
                if (kv.Key.Length <= 32)
                    add(kv.Value);
            }
            _prewarmChars = seen.Count == 0 ? "" : new string(new List<char>(seen).ToArray());
            _prewarmAt = 0;
            Trace("queued CJK prewarm " + seen.Count);
        }
        catch (Exception ex)
        {
            Trace("queue CJK: " + ex.Message);
        }
    }

    static void StepGlyphPrewarm()
    {
        if (_cjk == null || string.IsNullOrEmpty(_prewarmChars) || _prewarmAt >= _prewarmChars.Length)
            return;
        try
        {
            var take = Math.Min(80, _prewarmChars.Length - _prewarmAt);
            var chunk = _prewarmChars.Substring(_prewarmAt, take);
            _prewarmAt += take;
            foreach (var method in typeof(TMP_FontAsset).GetMethods(BindingFlags.Public | BindingFlags.Instance))
            {
                if (method.Name != "TryAddCharacters")
                    continue;
                var args = method.GetParameters();
                if (args.Length < 1 || args[0].ParameterType != typeof(string))
                    continue;
                var call = new object[args.Length];
                call[0] = chunk;
                for (var i = 1; i < args.Length; i++)
                {
                    if (args[i].HasDefaultValue)
                        call[i] = args[i].DefaultValue;
                    else if (args[i].ParameterType == typeof(bool))
                        call[i] = true;
                    else if (args[i].ParameterType.IsByRef)
                        call[i] = null;
                    else if (args[i].ParameterType.IsValueType)
                        call[i] = Activator.CreateInstance(args[i].ParameterType);
                }
                method.Invoke(_cjk, call);
                break;
            }
        }
        catch
        {
        }
    }

    static void RefreshActiveCache()
    {
        try
        {
            _activeTmps = UnityEngine.Object.FindObjectsOfType<TMP_Text>();
            LastActiveTmpCount = _activeTmps == null ? 0 : _activeTmps.Length;
            _activeSlice = 0;
        }
        catch
        {
            _activeTmps = null;
        }
    }

    static void RefreshAllCache()
    {
        try
        {
            _allTmps = Resources.FindObjectsOfTypeAll<TMP_Text>();
            _allSlice = 0;
        }
        catch
        {
            _allTmps = null;
        }
    }

    static int SliceTmp(TMP_Text[] texts, ref int index, int budgetMs, bool dumpMisses)
    {
        if (texts == null || texts.Length == 0)
            return 0;
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var changed = 0;
        var n = texts.Length;
        var start = index;
        do
        {
            if (sw.ElapsedMilliseconds >= budgetMs)
                break;
            var tmp = texts[index];
            index++;
            if (index >= n)
                index = 0;
            try
            {
                if (tmp == null || tmp.gameObject == null || !tmp.gameObject.activeInHierarchy)
                    continue;
                if (ApplyTmp(tmp, dumpMisses, false))
                    changed++;
            }
            catch
            {
            }
        } while (index != start);
        return changed;
    }

    internal static void TickSweep()
    {
        SweepPendingRulebook();
        if (_cacheDirty)
        {
            RefreshActiveCache();
            _cacheDirty = false;
            _boostFrames = Math.Max(_boostFrames, 12);
            return;
        }
        if (_boostFrames > 0)
        {
            var changed = SliceTmp(_activeTmps, ref _activeSlice, 8, false);
            if (changed > 0)
                Trace("boost slice " + changed);
            _boostFrames--;
            if (_activeSlice == 0 && changed == 0)
                _boostFrames = Math.Min(_boostFrames, 2);
            StepGlyphPrewarm();
            _ready = true;
            return;
        }
        _idleFrames++;
        if (_idleFrames % 180 == 1)
        {
            RefreshAllCache();
            return;
        }
        if (_idleFrames % 2 == 0)
            SliceTmp(_allTmps ?? _activeTmps, ref _allSlice, 4, false);
        StepGlyphPrewarm();
        _ready = true;
    }

    static bool IsRulebookObject(GameObject go)
    {
        try
        {
            var t = go == null ? null : go.transform;
            for (var i = 0; i < 14 && t != null; i++)
            {
                var n = t.name ?? "";
                if (n.IndexOf("Rulebook", StringComparison.OrdinalIgnoreCase) >= 0)
                    return true;
                if (n.IndexOf("Rules Text", StringComparison.OrdinalIgnoreCase) >= 0)
                    return true;
                if (n.IndexOf("RulesFlavor", StringComparison.OrdinalIgnoreCase) >= 0)
                    return true;
                t = t.parent;
            }
        }
        catch
        {
        }
        return false;
    }

    static Font UiCjkFont()
    {
        if (_uiCjk == null)
        {
            try
            {
                _uiCjk = Font.CreateDynamicFontFromOSFont("Microsoft YaHei", 16);
                if (_uiCjk == null)
                    _uiCjk = Font.CreateDynamicFontFromOSFont("SimHei", 16);
            }
            catch (Exception ex)
            {
                Trace("UI CJK font failed: " + ex.Message);
            }
        }
        return _uiCjk;
    }

    static readonly HashSet<int> FontsHooked = new HashSet<int>();
    static readonly HashSet<int> RulebookFontFit = new HashSet<int>();
    static readonly Dictionary<int, int> LastTextHash = new Dictionary<int, int>();

    static void FitRulebookTmp(TMP_Text tmp, string text)
    {
        if (tmp == null || !IsRulebookObject(tmp.gameObject))
            return;
        try
        {
            tmp.overflowMode = TextOverflowModes.Overflow;
            tmp.enableWordWrapping = true;
        }
        catch
        {
        }
        if (!HasCjk(text))
            return;
        var id = tmp.GetInstanceID();
        if (!RulebookFontFit.Add(id))
            return;
        try
        {
            var current = tmp.fontSize;
            if (current < 1f)
                current = 24f;
            // CJK glyphs are wider; shrink once so callout boxes stop clipping.
            tmp.enableAutoSizing = true;
            tmp.fontSizeMax = current * 0.82f;
            tmp.fontSizeMin = Math.Max(9f, current * 0.42f);
            tmp.fontSize = tmp.fontSizeMax;
        }
        catch
        {
        }
    }

    static string TranslateDisplay(string text)
    {
        if (string.IsNullOrEmpty(text))
            return text;
        if (HasCjk(text) && text.IndexOf("Reward:", StringComparison.Ordinal) < 0
            && text.IndexOf("Loading", StringComparison.OrdinalIgnoreCase) < 0)
            return text;
        var zh = Rewrite(text);
        return zh != null && zh != text ? zh : text;
    }

    static void AttachCjkFont(TMP_Text tmp)
    {
        if (_cjk == null || tmp == null)
            return;
        try
        {
            var font = tmp.font;
            if (font == null || font == _cjk)
                return;
            var fid = font.GetInstanceID();
            if (FontsHooked.Contains(fid))
                return;
            var table = font.fallbackFontAssetTable;
            if (table != null)
                table.Add(_cjk);
            FontsHooked.Add(fid);
        }
        catch
        {
        }
    }

    static void AttachUiFont(Text label)
    {
        if (label == null || !HasCjk(label.text))
            return;
        var font = UiCjkFont();
        if (font != null)
            label.font = font;
    }

    static void AttachMeshFont(TextMesh mesh)
    {
        if (mesh == null || !HasCjk(mesh.text))
            return;
        var font = UiCjkFont();
        if (font != null)
            mesh.font = font;
    }

    static void ApplyTmpOverflow(TMP_Text tmp, string text)
    {
        if (IsRulebookObject(tmp.gameObject))
        {
            FitRulebookTmp(tmp, text);
            return;
        }
        if (!HasCjk(text))
            return;
        try
        {
            tmp.overflowMode = TextOverflowModes.Overflow;
            tmp.enableWordWrapping = true;
        }
        catch
        {
        }
    }

    static bool ApplyTmp(TMP_Text tmp, bool dumpMisses, bool fitOverflow = true)
    {
        if (tmp == null || tmp.gameObject == null)
            return false;
        AttachCjkFont(tmp);
        var text = tmp.text;
        if (string.IsNullOrEmpty(text))
            return false;
        var id = tmp.GetInstanceID();
        var hash = text.GetHashCode();
        int prev;
        if (LastTextHash.TryGetValue(id, out prev) && prev == hash && HasCjk(text))
            return false;
        if (HasCjk(text) && text.IndexOf("Reward:", StringComparison.Ordinal) < 0
            && text.IndexOf("Loading", StringComparison.OrdinalIgnoreCase) < 0)
        {
            LastTextHash[id] = hash;
            if (fitOverflow)
                ApplyTmpOverflow(tmp, text);
            return false;
        }
        var zh = TranslateDisplay(text);
        if (zh != null && zh != text)
        {
            tmp.text = zh;
            LastTextHash[id] = zh.GetHashCode();
            if (fitOverflow)
                ApplyTmpOverflow(tmp, zh);
            return true;
        }
        LastTextHash[id] = hash;
        if (dumpMisses)
            MaybeDump("E", text, null);
        if (fitOverflow)
            ApplyTmpOverflow(tmp, text);
        return false;
    }

    static bool ApplyUiLabel(Text label, bool dumpMisses)
    {
        if (label == null || label.gameObject == null)
            return false;
        var text = label.text;
        if (string.IsNullOrEmpty(text))
            return false;
        if (HasCjk(text))
        {
            AttachUiFont(label);
            return false;
        }
        var zh = TranslateDisplay(text);
        if (zh != null && zh != text)
        {
            label.text = zh;
            AttachUiFont(label);
            return true;
        }
        if (dumpMisses)
            MaybeDump("E", text, null);
        return false;
    }

    static bool ApplyMesh(TextMesh mesh, bool dumpMisses)
    {
        if (mesh == null || mesh.gameObject == null)
            return false;
        var text = mesh.text;
        if (string.IsNullOrEmpty(text))
            return false;
        if (HasCjk(text))
        {
            AttachMeshFont(mesh);
            return false;
        }
        var zh = TranslateDisplay(text);
        if (zh != null && zh != text)
        {
            mesh.text = zh;
            AttachMeshFont(mesh);
            return true;
        }
        if (dumpMisses)
            MaybeDump("E", text, null);
        return false;
    }

    static bool IsSceneText(Component c)
    {
        try
        {
            return c != null && c.gameObject != null && c.gameObject.scene.IsValid();
        }
        catch
        {
            return false;
        }
    }

    static bool IsActiveText(Component c)
    {
        try
        {
            return c.gameObject.activeInHierarchy;
        }
        catch
        {
            return false;
        }
    }

    internal static int RelocalizeUi()
    {
        return RelocalizeUi(false, 10, true);
    }

    internal static int RelocalizeUi(bool activeOnly, int budgetMs)
    {
        return RelocalizeUi(activeOnly, budgetMs, !activeOnly);
    }

    internal static int RelocalizeUi(bool activeOnly, int budgetMs, bool dumpMisses)
    {
        try
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            if (budgetMs < 1)
                budgetMs = 10;
            TMP_Text[] texts;
            if (activeOnly)
                texts = UnityEngine.Object.FindObjectsOfType<TMP_Text>();
            else
                texts = Resources.FindObjectsOfTypeAll<TMP_Text>();
            if (texts == null)
                return 0;
            if (activeOnly)
            {
                LastActiveTmpCount = texts.Length;
                if (texts.Length > 220)
                {
                    Trace("skip dense active scan count=" + texts.Length);
                    return 0;
                }
            }
            var changed = 0;
            var scanned = 0;
            var budgetHit = false;

            foreach (var tmp in texts)
            {
                if (sw.ElapsedMilliseconds > budgetMs)
                {
                    budgetHit = true;
                    Trace("relocalize TMP budget hit after " + scanned + " objs changed=" + changed);
                    break;
                }
                try
                {
                    if (tmp == null || tmp.gameObject == null)
                        continue;
                    if (!activeOnly && !IsSceneText(tmp))
                        continue;
                    if (!activeOnly && !IsActiveText(tmp))
                        continue;
                    scanned++;
                    if (ApplyTmp(tmp, dumpMisses))
                        changed++;
                }
                catch
                {
                }
            }

            if (!activeOnly && !budgetHit)
            {
                texts = Resources.FindObjectsOfTypeAll<TMP_Text>();
                if (texts != null)
                {
                    foreach (var tmp in texts)
                    {
                        if (sw.ElapsedMilliseconds > budgetMs)
                            break;
                        try
                        {
                            if (!IsSceneText(tmp) || IsActiveText(tmp))
                                continue;
                            scanned++;
                            if (ApplyTmp(tmp, dumpMisses))
                                changed++;
                        }
                        catch
                        {
                        }
                    }
                }
            }

            try
            {
                Text[] uiTexts;
                if (activeOnly)
                    uiTexts = UnityEngine.Object.FindObjectsOfType<Text>();
                else
                    uiTexts = Resources.FindObjectsOfTypeAll<Text>();
                if (uiTexts != null)
                {
                    foreach (var label in uiTexts)
                    {
                        if (sw.ElapsedMilliseconds > budgetMs)
                            break;
                        try
                        {
                            if (label == null || label.gameObject == null)
                                continue;
                            if (!activeOnly && !IsSceneText(label))
                                continue;
                            if (ApplyUiLabel(label, dumpMisses))
                                changed++;
                        }
                        catch
                        {
                        }
                    }
                }
            }
            catch
            {
            }
            try
            {
                TextMesh[] meshes;
                if (activeOnly)
                    meshes = UnityEngine.Object.FindObjectsOfType<TextMesh>();
                else
                    meshes = Resources.FindObjectsOfTypeAll<TextMesh>();
                if (meshes != null)
                {
                    foreach (var mesh in meshes)
                    {
                        if (sw.ElapsedMilliseconds > budgetMs)
                            break;
                        try
                        {
                            if (mesh == null || mesh.gameObject == null)
                                continue;
                            if (!activeOnly && !IsSceneText(mesh))
                                continue;
                            if (ApplyMesh(mesh, dumpMisses))
                                changed++;
                        }
                        catch
                        {
                        }
                    }
                }
            }
            catch
            {
            }
            if (changed > 0)
                Trace("relocalized " + changed + " texts in " + sw.ElapsedMilliseconds + "ms");
            _ready = true;
            return changed;
        }
        catch (Exception ex)
        {
            Trace("RelocalizeUi: " + ex.Message);
            return 0;
        }
    }

    static TMP_FontAsset CreateCjkFont()
    {
        foreach (var family in new[] { "Microsoft YaHei", "Microsoft YaHei UI", "SimHei" })
        {
            var created = InvokeCreateFontAsset(family, false);
            if (created != null)
            {
                created.name = "AscensionZhCn-CJK";
                Trace("CJK font family " + family);
                return created;
            }
        }

        var fontsDir = Environment.GetFolderPath(Environment.SpecialFolder.Fonts);
        var streaming = Path.Combine(Application.dataPath, "StreamingAssets", "zh-cn", "cjk-overlay.ttf");
        foreach (var path in new[]
                 {
                     Path.Combine(fontsDir, "msyh.ttc"),
                     Path.Combine(fontsDir, "msyh.ttf"),
                     Path.Combine(fontsDir, "simhei.ttf"),
                     streaming,
                 })
        {
            if (!File.Exists(path))
            {
                Trace("missing " + path);
                continue;
            }
            var created = InvokeCreateFontAsset(path, true);
            if (created != null)
            {
                created.name = "AscensionZhCn-CJK";
                Trace("CJK font from " + path);
                return created;
            }
        }
        return null;
    }

    static TMP_FontAsset InvokeCreateFontAsset(string first, bool isPath)
    {
        try
        {
            foreach (var method in typeof(TMP_FontAsset).GetMethods(BindingFlags.Public | BindingFlags.Static))
            {
                if (method.Name != "CreateFontAsset")
                    continue;
                var argsInfo = method.GetParameters();
                if (argsInfo.Length == 0 || argsInfo[0].ParameterType != typeof(string))
                    continue;
                if (isPath && argsInfo.Length >= 2 && argsInfo[1].ParameterType == typeof(string))
                    continue;
                if (!isPath && (argsInfo.Length < 2 || argsInfo[1].ParameterType != typeof(string)))
                    continue;

                var call = new object[argsInfo.Length];
                for (var i = 0; i < argsInfo.Length; i++)
                    call[i] = ValueFor(argsInfo[i], i, first, isPath);
                Trace("invoke " + method);
                var created = method.Invoke(null, call) as TMP_FontAsset;
                if (created != null)
                    return created;
                Trace("CreateFontAsset returned null");
            }
        }
        catch (Exception ex)
        {
            Trace("CreateFontAsset failed: " + ex);
        }
        return null;
    }

    static object ValueFor(ParameterInfo arg, int index, string first, bool isPath)
    {
        var name = (arg.Name ?? "").ToLowerInvariant();
        var type = arg.ParameterType;
        if (index == 0 && type == typeof(string))
            return first;
        if (index == 1 && type == typeof(string))
            return "Regular";
        if (type == typeof(bool))
            return true;
        if (type.IsEnum)
        {
            var names = Enum.GetNames(type);
            foreach (var candidate in new[] { "SDFAA", "SDF", "SMOOTH", "RASTER" })
            {
                foreach (var n in names)
                {
                    if (n.Equals(candidate, StringComparison.OrdinalIgnoreCase))
                        return Enum.Parse(type, n);
                }
            }
            if (name.Contains("population") || name.Contains("atlas"))
            {
                foreach (var n in names)
                {
                    if (n.IndexOf("Dynamic", StringComparison.OrdinalIgnoreCase) >= 0)
                        return Enum.Parse(type, n);
                }
            }
            try
            {
                return Enum.ToObject(type, name.Contains("render") ? 4168 : 1);
            }
            catch
            {
                return Activator.CreateInstance(type);
            }
        }
        if (type == typeof(int))
        {
            if (name.Contains("face"))
                return 0;
            if (name.Contains("sampling") || name.Contains("point"))
                return 90;
            if (name.Contains("padding"))
                return 9;
            if (name.Contains("width") || name.Contains("height"))
                return 1024;
            if (index == 1 && isPath)
                return 0;
            if (index == 2)
                return 90;
            if (index == 3)
                return 9;
            return 1024;
        }
        if (arg.HasDefaultValue && arg.DefaultValue != null)
            return arg.DefaultValue;
        if (type.IsValueType)
            return Activator.CreateInstance(type);
        return null;
    }
}

public class CjkFontBehaviour : MonoBehaviour
{
    int _frames;
    bool _fontDone;

    public CjkFontBehaviour(IntPtr ptr) : base(ptr)
    {
    }

    void Update()
    {
        _frames++;
        if (!_fontDone)
        {
            Plugin.Trace("first Update: CJK font then leftover sweep");
            Plugin.EnsureCjkFallback();
            _fontDone = true;
            return;
        }
    }

    void LateUpdate()
    {
        if (_fontDone)
            Plugin.TickSweep();
    }
}
