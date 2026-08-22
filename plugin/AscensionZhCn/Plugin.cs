using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime.Injection;
using Il2CppInterop.Runtime;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace AscensionZhCn;

[BepInPlugin("ascension.zh.cn", "Ascension Chinese overlay", "1.5.0")]
public class Plugin : BasePlugin
{
    internal static Plugin Instance;
    static TMP_FontAsset _cjk;
    static bool _installed;
    const int CjkMaxAttempts = 5;
    static int _cjkAttempts;
    static bool _locPatched;
    static bool _setterPatched;
    static bool _sceneHooked;
    static bool _preRenderHooked;
    static bool _ready;
    internal static bool IsReady
    {
        get { return _ready; }
    }
    static string LogPath = "";
    static string DumpPath = "";
    static ConfigEntry<bool> DumpUntranslated;
    static ConfigEntry<bool> DumpLongStrings;
    static readonly HashSet<string> Dumped = new HashSet<string>();
    const int DumpMax = 5000;
    const int DumpLongMaxLen = 10000;
    // Re-entrancy guard: when we rewrite text and write it back via
    // tmp.text = zh, Unity's layout system may fire set_text again.
    // Without this guard, long rulebook text can trigger infinite loops.
    [ThreadStatic] static bool _inRewrite;
    const int RewriteMaxLen = 8000;  // Skip regex chain for very long text (catastrophic backtracking risk)
    static Harmony _harmony;
    static MethodInfo _convertEmbedded;

    internal static readonly Dictionary<string, string> Keys = new Dictionary<string, string>();
    internal static readonly Dictionary<string, string> Exact = new Dictionary<string, string>();
    // Normalized key → zh: keys are produced by stripping all rich-text tags
    // and normalizing whitespace.  This lets us match game-rendered text that
    // has subtle whitespace/tag differences from the dump.
    internal static readonly Dictionary<string, string> NormalizedExact = new Dictionary<string, string>();
    // Prefix index: maps normalized text prefixes (>=40 chars) to zh translations.
    // This handles the case where the game sends individual paragraphs but our
    // overlay stores the full concatenated multi-paragraph text.
    internal static readonly Dictionary<string, string> NormalizedPrefix = new Dictionary<string, string>();
    // Sentence index: maps normalized individual sentences to their zh translations.
    // Built by splitting overlay entries into sentences so that even if the game
    // renders text at sentence-level granularity, we can still match.
    internal static readonly Dictionary<string, string> NormalizedSentence = new Dictionary<string, string>();
    // Contains index: maps short normalized fragments to zh translations.
    // For game text that is a substring of an overlay entry, we can find
    // the full overlay entry and return its Chinese translation.
    internal static readonly Dictionary<string, string> NormalizedContains = new Dictionary<string, string>();
    // Sorted list of normalized keys for binary-search reverse prefix matching
    private static List<string> _sortedNormKeys;
    private static List<string> _sortedNormValues;

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
            File.WriteAllText(LogPath, DateTime.Now + " plugin Load() 1.5.0 (phase3 anti-flicker: preRender + L1 exact fallback + rulebook panels)\n");
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
                true,
                "Write unseen English loc keys and TMP strings to StreamingAssets/zh-cn/untranslated.tsv");
            DumpLongStrings = Config.Bind(
                "Debug",
                "DumpLongStrings",
                false,
                "Dump long English strings (rulebook/DLC) as kind 'L'. Keep false during normal play — enabling this while opening the store/rulebook can freeze the game due to disk I/O.");
            if (DumpUntranslated.Value && !string.IsNullOrEmpty(DumpPath) && !File.Exists(DumpPath))
                File.WriteAllText(DumpPath, "# kind\tsrc\tsample\n# play menus/gallery once, then: python tools/ingest_untranslated.py\n");
        }
        catch (Exception ex)
        {
            Trace("config bind failed: " + ex.Message);
        }

        LoadOverlay();
        PatchLocalization();

        // Sync CJK fallback install: avoids the tofu flash where L1 already
        // returns Chinese but the font isn't attached yet. If TMP isn't ready
        // at Load() time, CjkFontBehaviour retries and arms the L2 hooks once
        // the font is in place.
        try
        {
            EnsureCjkFallback();
            if (_ready)
            {
                PatchTextSetters();
                PatchSceneLoaded();
                PatchPreRender();
                Trace("sync CJK install OK; L2 hooks active");
            }
            else
            {
                Trace("sync CJK install not ready; will retry via CjkFontBehaviour");
            }
        }
        catch (Exception ex)
        {
            Trace("sync CJK install failed: " + ex.Message);
        }

        try
        {
            ClassInjector.RegisterTypeInIl2Cpp<CjkFontBehaviour>();
            AddComponent<CjkFontBehaviour>();
            Trace("injected CjkFontBehaviour (fallback + safety sweep)");
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
            // Avoid flooding plugin.log — only persist non-spam lines.
            if (message != null && message.StartsWith("ForceStateMarkers:", StringComparison.Ordinal))
                return;
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
                    Exact[src] = zh;
                }
            }
            // Build normalized index: strip all TMP rich-text tags and collapse
            // whitespace so that game-rendered text with minor formatting
            // differences still matches our rulebook.csv / overlay entries.
            BuildNormalizedExact();
            Trace("loaded overlay " + path + " keys=" + Keys.Count + " exact=" + Exact.Count + " normExact=" + NormalizedExact.Count);
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
                Exact[en] = zh;
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
        add("Owned", "已拥有");
        add("Coming Soon", "即将推出");
        add("Now Available", "现已推出");
        add("Stone Blade Newsletter Sign-up", "订阅 Stone Blade 通讯");
        add("Stone Blade Newsletter Sign-Up", "订阅 Stone Blade 通讯");
        add("Sign up to get the latest information and special deals direct to you.", "订阅即可获取最新资讯与优惠，直接发到你的邮箱。");
        add("Downloadable Content", "可下载内容");
        add("Promo 7", "特典 7");
        // ======= 新增焦点区域 =======
        // 离线对局空存档提示（多行变体）
        add("No saved games found.\nSelect \"Create Game\"\nto start a new game.\n", "暂无保存的对局。\n选择「创建对局」\n开始新游戏。\n");
        add("No saved games found.\r\nSelect \"Create Game\"\r\nto start a new game.\r\n", "暂无保存的对局。\n选择「创建对局」\n开始新游戏。\n");
        add("No saved games found.\nSelect \"Create Game\"\nto start a new game.", "暂无保存的对局。\n选择「创建对局」\n开始新游戏。");
        add("Create Game", "创建对局");
        // 选项
        add("Theme", "主题");
        add("Theme Selection", "主题选择");
        add("Analytics", "分析");
        add("Share Analytics", "分享分析数据");
        add("Gameplay Analytics", "游戏分析");
        add("Game Speed", "游戏速度");
        add("Animation Speed", "动画速度");
        add("Fast", "快");
        add("Slow", "慢");
        add("Medium", "中");
        add("On", "开启");
        add("Off", "关闭");
        add("Resolution", "分辨率");
        add("Fullscreen", "全屏");
        add("Windowed", "窗口");
        add("Windowed Mode", "窗口模式");
        // 卡包缩略
        add("CotG", "弑神编");
        add("10th", "十周年");
        add("RotF", "邪神归来");
        add("SoS", "灵魂风暴");
        add("IH", "不朽英雄");
        add("RoV", "祈夜崛起");
        add("DU", "黑暗释放");
        add("RU", "领域解开");
        add("DoC", "冠军黎明");
        add("DS", "梦境");
        add("WoS", "暗影之战");
        add("GotE", "元素馈赠");
        add("VotA", "上古山谷");
        add("DLV", "救赎");
        add("DLRM", "谵妄");
        add("LGS", "史诗传奇");
        // 成就 / 图鉴 / 标题
        add("Achievements", "成就");
        add("Card Gallery", "卡牌图鉴");
        add("Gallery", "图鉴");
        add("Collection", "收藏");
        add("Key Bindings", "按键绑定");
        add("Options", "选项");
        // 按键绑定
        add("Play Card", "出牌");
        add("Magnify Card", "放大卡牌");
        add("Scroll Magnified Card Left", "放大卡左翻");
        add("Scroll Magnified Card Right", "放大卡右翻");
        add("Show/Hide Pause Menu", "显示/隐藏暂停菜单");
        add("Unmagnify Card & Close Card Trays", "缩小并关闭卡列表");
        add("Play All Cards From Hand", "打出全部手牌");
        add("End Your Turn", "结束回合");
        add("Open/Close Construct Tray", "打开/关闭神器栏");
        add("Open/Close Discard Pile", "打开/关闭弃牌堆");
        add("Open/Close Deck List", "打开/关闭牌库列表");
        add("Open/Close Void List", "打开/关闭虚空列表");
        add("Open/Close Dreamborn List", "打开/关闭梦生列表");
        add("Open/Close Renown Track", "打开/关闭名望轨道");
        add("L Mouse", "鼠标左键");
        add("R Mouse", "鼠标右键");
        add("LeftArrow", "← 方向键左");
        add("RightArrow", "→ 方向键右");
        add("Escape", "Esc 键");
        add("Space", "空格键");
        // 其它常见
        add("Are you sure you wish to end your turn?", "确定要结束你的回合吗？");
        add("Share your gameplay analytics with Playdek to help improve Ascension? This can be changed anytime in the Options Menu.", "向 Playdek 分享你的游戏分析数据以帮助改进《创升纪元》？此选项可随时在选项菜单中修改。");
        add("Share your gameplay analytics with Playdek to help improve Ascension? This can be changed anytime in the Options Menu", "向 Playdek 分享你的游戏分析数据以帮助改进《创升纪元》？此选项可随时在选项菜单中修改");
        // ======= 梦境选择界面 =======
        add("Choose 1 More Card for your Dreamscape", "为你的梦境选择一张额外的卡牌");
        add("Choose 2 More Cards for your Dreamscape", "为你的梦境选择两张额外的卡牌");
        add("Choose 3 Cards for your Dreamscape", "为你的梦境选择三张卡牌");
    }

    static string Unescape(string value)
    {
        if (string.IsNullOrEmpty(value))
            return value;
        // CSV/overlay historically double-escaped CR as "\\r" (two backslashes).
        // Normalize both "\\r" and "\r" to newline so Exact/Normalized keys match
        // game TMP text (which uses real CR or bare paragraphs).
        var s = value
            .Replace("\\\\r\\\\n", "\n")
            .Replace("\\\\r", "\n")
            .Replace("\\\\n", "\n");
        s = s
            .Replace("\\r\\n", "\n")
            .Replace("\\r", "\n")
            .Replace("\\n", "\n")
            .Replace("\\t", "\t");
        // Remaining doubled backslashes → single
        s = s.Replace("\\\\", "\\");
        return s;
    }

    static readonly Regex StripAllTags = new Regex(@"<[^>]*>", RegexOptions.Compiled);
    static readonly Regex NormalizeWs = new Regex(@"\s+", RegexOptions.Compiled);

    // Common Unicode → ASCII punctuation mappings for fuzzy matching
    static readonly Dictionary<char, char> UnicodePuncMap = new Dictionary<char, char>
    {
        ['\u2014'] = '-', // em dash
        ['\u2013'] = '-', // en dash
        ['\u2018'] = '\'', // left single quote
        ['\u2019'] = '\'', // right single quote
        ['\u201C'] = '"', // left double quote
        ['\u201D'] = '"', // right double quote
        ['\u2026'] = '.', // ellipsis
        ['\u00A0'] = ' ', // non-breaking space
        ['\u3000'] = ' ', // CJK space
        ['\uff0c'] = ',', // full-width comma
        ['\uff0e'] = '.', // full-width period
        ['\uff1a'] = ':', // full-width colon
        ['\uff01'] = '!', // full-width exclaim
        ['\uff1f'] = '?', // full-width question
        ['\uff08'] = '(', // full-width paren
        ['\uff09'] = ')', // full-width paren
        ['\u300A'] = '[', // left angle bracket
        ['\u300B'] = ']', // right angle bracket
        ['\u3010'] = '[', // left black square
        ['\u3011'] = ']', // right black square
    };

    static string NormalizeForLookup(string text)
    {
        if (string.IsNullOrEmpty(text))
            return "";
        // Fast path for huge DLC/rulebook blobs: avoid catastrophic Regex on multi-KB.
        // IMPORTANT: replace tags with a space (same as StripAllTags path).
        // Otherwise "unique<br>new" collapses to "uniquenew" and store blurbs
        // never hit NormalizedExact.
        if (text.Length > 500)
        {
            var sbFast = new System.Text.StringBuilder(text.Length);
            bool inTag = false;
            bool prevSpace = false;
            foreach (char c in text)
            {
                if (c == '<')
                {
                    inTag = true;
                    if (!prevSpace)
                    {
                        sbFast.Append(' ');
                        prevSpace = true;
                    }
                    continue;
                }
                if (inTag)
                {
                    if (c == '>') inTag = false;
                    continue;
                }
                if (c == '\\')
                    continue;
                char mapped = c;
                if (UnicodePuncMap.TryGetValue(c, out var m))
                    mapped = m;
                if (char.IsWhiteSpace(mapped) || mapped == '\r' || mapped == '\n')
                {
                    if (!prevSpace)
                    {
                        sbFast.Append(' ');
                        prevSpace = true;
                    }
                    continue;
                }
                prevSpace = false;
                if (mapped >= 'A' && mapped <= 'Z')
                    mapped = (char)(mapped + 32);
                sbFast.Append(mapped);
            }
            return sbFast.ToString().Trim();
        }
        // Strip all TMP/HTML-style tags
        var stripped = StripAllTags.Replace(text, " ");
        // Drop leftover backslashes from historical double-escaping in overlay.tsv
        stripped = stripped.Replace("\\", " ");
        // Map Unicode punctuation to ASCII equivalents
        var sb = new System.Text.StringBuilder(stripped.Length);
        foreach (char c in stripped)
        {
            if (UnicodePuncMap.TryGetValue(c, out var mapped))
                sb.Append(mapped);
            else
                sb.Append(c);
        }
        stripped = sb.ToString();
        // Collapse whitespace (including \r\n → space)
        stripped = NormalizeWs.Replace(stripped, " ");
        return stripped.Trim().ToLowerInvariant();
    }

    static void BuildNormalizedExact()
    {
        NormalizedExact.Clear();
        NormalizedPrefix.Clear();
        NormalizedSentence.Clear();
        NormalizedContains.Clear();
        foreach (var kv in Exact)
        {
            var norm = NormalizeForLookup(kv.Key);
            if (norm.Length >= 4)
            {
                // Prefer the entry with the longest zh translation
                // (most complete). This handles the case where multiple
                // Exact keys normalize to the same form (e.g. different
                // whitespace/escape variants of the same rulebook paragraph).
                if (!NormalizedExact.ContainsKey(norm)
                    || kv.Value.Length > NormalizedExact[norm].Length)
                {
                    NormalizedExact[norm] = kv.Value;
                }

                // Build prefix index: for every entry >= 30 chars, register
                // prefixes at 5-char intervals so we can match partial paragraphs
                // that the game renders as individual TMP_Text components.
                if (norm.Length >= 30)
                {
                    for (int len = 30; len <= Math.Min(norm.Length, 120); len += 5)
                    {
                        var prefix = norm.Substring(0, len);
                        if (!NormalizedPrefix.ContainsKey(prefix)
                            || kv.Value.Length > NormalizedPrefix[prefix].Length)
                        {
                            NormalizedPrefix[prefix] = kv.Value;
                        }
                    }
                }

                // Build sentence index: split long entries into individual
                // sentences and index each one. This handles the case where
                // the game renders each sentence as a separate TMP_Text.
                if (norm.Length >= 80)
                {
                    var sentences = norm.Split(new[] { ". ", "! ", "? " }, StringSplitOptions.None);
                    foreach (var sent in sentences)
                    {
                        var s = sent.Trim();
                        if (s.Length >= 25)
                        {
                            if (!NormalizedSentence.ContainsKey(s)
                                || kv.Value.Length > NormalizedSentence[s].Length)
                            {
                                NormalizedSentence[s] = kv.Value;
                            }
                        }
                    }
                }

                // Build contains index only for medium paragraphs (not multi-KB
                // DLC blurbs — those explode index size and lookup cost).
                if (norm.Length >= 60 && norm.Length <= 400)
                {
                    int step = Math.Max(5, (norm.Length - 30) / 10);
                    for (int pos = 0; pos <= norm.Length - 30; pos += step)
                    {
                        var fragment = norm.Substring(pos, 30);
                        if (!NormalizedContains.ContainsKey(fragment)
                            || kv.Value.Length > NormalizedContains[fragment].Length)
                        {
                            NormalizedContains[fragment] = kv.Value;
                        }
                    }
                }
            }
        }

        // Build sorted lists for binary-search reverse prefix matching
        _sortedNormKeys = new List<string>(NormalizedExact.Keys);
        _sortedNormKeys.Sort(StringComparer.Ordinal);
        _sortedNormValues = new List<string>(_sortedNormKeys.Count);
        foreach (var k in _sortedNormKeys)
            _sortedNormValues.Add(NormalizedExact[k]);
    }

    static string LookupExactOrNormalized(string text)
    {
        // 1) Direct exact match
        string zh;
        if (Exact.TryGetValue(text, out zh) && zh != text)
            return zh;
        // 2) Trimmed exact
        var trimmed = text.Trim();
        if (trimmed != text && Exact.TryGetValue(trimmed, out zh) && zh != trimmed)
            return zh;

        // Store/IAP long marketing copy: Exact + NormalizedExact only (no fuzzy).
        // Skipping Normalize entirely made store blurbs stay English in 1.4.3.
        if (text.Length > 220)
        {
            var normLong = NormalizeForLookup(text);
            if (normLong.Length >= 4 && NormalizedExact.TryGetValue(normLong, out zh))
                return zh;
            return null;
        }

        // 3) Normalized full-text match
        var norm = NormalizeForLookup(text);
        if (norm.Length >= 4 && NormalizedExact.TryGetValue(norm, out zh))
            return zh;

        // Long copy (DLC store / full rulebook pages): ONLY exact+normalized.
        // Prefix/contains scans on multi-KB strings froze the main thread.
        if (norm.Length > 280 || text.Length > 400)
            return null;

        // 4) Prefix-based match — only when the game text itself is a substantial
        //    prefix (avoid matching a short UI chip to a whole DLC blurb).
        if (norm.Length >= 40)
        {
            int maxLen = Math.Min(norm.Length, 120);
            for (int len = maxLen; len >= 40; len -= 5)
            {
                var prefix = norm.Substring(0, len);
                if (NormalizedPrefix.TryGetValue(prefix, out zh))
                {
                    // Reject if translation is wildly longer than source (wrong hit).
                    if (zh.Length <= text.Length * 3 + 80)
                        return zh;
                }
            }
        }
        // 5) Sentence-level match
        if (norm.Length >= 25 && norm.Length <= 200)
        {
            if (NormalizedSentence.TryGetValue(norm, out zh))
                return zh;
        }
        // 6) Contains index (short/medium only)
        if (norm.Length >= 40 && norm.Length <= 160)
        {
            for (int pos = 0; pos <= norm.Length - 30; pos += 5)
            {
                var fragment = norm.Substring(pos, 30);
                if (NormalizedContains.TryGetValue(fragment, out zh))
                {
                    if (zh.Length <= text.Length * 3 + 80)
                        return zh;
                }
            }
        }
        // 7) Reverse prefix binary search
        if (norm.Length >= 40 && norm.Length <= 160)
        {
            zh = FindByReversePrefixBinary(norm);
            if (zh != null && zh.Length <= text.Length * 3 + 80)
                return zh;
        }
        return null;
    }

    static string FindByReversePrefix(string norm)
    {
        // Search for overlay keys that start with the given normalized text.
        // This handles the case where the game renders only a portion of
        // the paragraph that's stored in the overlay.
        foreach (var kv in NormalizedExact)
        {
            if (kv.Key.StartsWith(norm, StringComparison.Ordinal))
                return kv.Value;
        }
        return null;
    }

    static string FindByReversePrefixBinary(string norm)
    {
        // Binary search: find the first key >= norm, then check if it starts with norm
        if (_sortedNormKeys == null || _sortedNormKeys.Count == 0)
            return null;
        int idx = _sortedNormKeys.BinarySearch(norm);
        if (idx < 0)
            idx = ~idx; // First key >= norm
        // Check nearby entries
        for (int i = Math.Max(0, idx - 2); i < Math.Min(_sortedNormKeys.Count, idx + 5); i++)
        {
            if (_sortedNormKeys[i].StartsWith(norm, StringComparison.Ordinal))
                return _sortedNormValues[i];
        }
        return null;
    }

    static string FindByContains(string norm)
    {
        // Find an overlay key that contains the given normalized text.
        // This is the reverse of the contains index: it checks if the game
        // text is fully contained within an overlay entry.
        // Limit search to entries that are likely matches (similar length).
        int targetLen = norm.Length;
        foreach (var kv in NormalizedExact)
        {
            if (kv.Key.Length >= targetLen && kv.Key.Length <= targetLen + 300)
            {
                if (kv.Key.IndexOf(norm, StringComparison.Ordinal) >= 0)
                    return kv.Value;
            }
        }
        return null;
    }

    internal static void EnsureCjkFallback()
    {
        if (_installed || _cjkAttempts >= CjkMaxAttempts)
            return;
        _cjkAttempts++;
        try
        {
            Trace("EnsureCjkFallback attempt " + _cjkAttempts);
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
            RelocalizeUi();
            _ready = true;
            Trace("Chinese overlay ready");
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
            {
                Trace("LocalizationService type not found");
                return;
            }
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
            _harmony = new Harmony("ascension.zh.cn");
            foreach (var method in locType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance))
            {
                if (method.Name != "GetTextByKey")
                    continue;
                try
                {
                    _harmony.Patch(method, postfix: new HarmonyMethod(typeof(Plugin), nameof(LocPostfix)));
                    Trace("patched " + method);
                }
                catch (Exception ex)
                {
                    Trace("skip " + method + " : " + ex.Message);
                }
            }
        }
        catch (Exception ex)
        {
            Trace("Harmony loc patch failed: " + ex);
        }
    }

    internal static void PatchTextSetters()
    {
        if (_setterPatched)
            return;
        _setterPatched = true;
        if (_harmony == null)
            _harmony = new Harmony("ascension.zh.cn");
        try
        {
            // set_text: rewrite incoming text to Chinese PREFIX (visual),
            // cache original English for state-markers so the game's own
            // toggle logic still sees the original value when it reads back.
            PatchTextProp(typeof(TMP_Text), "set_text", nameof(TmpTextSetPrefix), null);
            PatchTextProp(typeof(Text), "set_text", nameof(UiTextSetPrefix), null);
            PatchTextProp(typeof(TextMesh), "set_text", nameof(TextMeshSetPrefix), null);

            // get_text: return cached original English for state-markers so
            // the game's internal comparison (`text == "Play Your Turn"`)
            // keeps working while the player sees Chinese visually.
            PatchTextProp(typeof(TMP_Text), "get_text", null, nameof(TmpTextGetPostfix));
            PatchTextProp(typeof(Text), "get_text", null, nameof(UiTextGetPostfix));
            PatchTextProp(typeof(TextMesh), "get_text", null, nameof(TextMeshGetPostfix));

            // Only the single-argument SetText(string). Format overloads
            // SetText(string, float, ...) froze the IAP store in 1.4.2.
            PatchSetTextStringOnly();
        }
        catch (Exception ex)
        {
            Trace("text setter patch failed: " + ex);
        }
    }

    static void PatchSetTextStringOnly()
    {
        try
        {
            foreach (var m in typeof(TMP_Text).GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (m.Name != "SetText")
                    continue;
                var ps = m.GetParameters();
                // Exactly one parameter, and it must be string (not StringBuilder).
                if (ps.Length != 1 || ps[0].ParameterType != typeof(string))
                    continue;
                try
                {
                    // Prefix rewrites the argument before TMP stores it — more
                    // reliable than postfix reading .text under IL2CPP.
                    _harmony.Patch(m, prefix: new HarmonyMethod(typeof(Plugin), nameof(TmpSetTextStringPrefix)));
                    Trace("patched SetText(string) prefix only");
                }
                catch (Exception ex)
                {
                    Trace("SetText(string) patch failed: " + ex.Message);
                }
            }
        }
        catch (Exception ex)
        {
            Trace("PatchSetTextStringOnly: " + ex.Message);
        }
    }

    // Prefix for SetText(string) — menus/rulebook/store blurbs use this.
    // Must NOT patch format overloads (store freeze).
    static void TmpSetTextStringPrefix(ref string text)
    {
        if (string.IsNullOrEmpty(text) || _inRewrite || !_ready)
            return;
        if (HasCjk(text) || IsTutorialProtected(text))
            return;
        _inRewrite = true;
        var zh = RewriteIncoming(text);
        _inRewrite = false;
        if (zh != null && zh != text)
            text = zh;
    }

    static void PatchTextProp(Type type, string methodName, string prefixName, string postfixName)
    {
        try
        {
            var methods = type.GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            MethodInfo method = null;
            var allCandidates = new List<string>();
            foreach (var m in methods)
            {
                if (m.Name != methodName)
                    continue;
                var ps = m.GetParameters();
                var sig = string.Join(", ", ps.Select(p => p.ParameterType.Name + " " + p.Name)) + " -> " + m.ReturnType.Name;
                allCandidates.Add(sig);
                if (methodName == "get_text")
                {
                    if (ps.Length == 0 && m.ReturnType == typeof(string))
                    {
                        method = m;
                        break;
                    }
                }
                else if (ps.Length == 1 && ps[0].ParameterType == typeof(string))
                {
                    method = m;
                    break;
                }
            }
            if (method == null)
            {
                Trace(methodName + " not found on " + type.FullName + " (candidates: " + string.Join("; ", allCandidates.ToArray()) + ")");
                return;
            }
            HarmonyMethod pre = prefixName != null ? new HarmonyMethod(typeof(Plugin), prefixName) : null;
            HarmonyMethod post = postfixName != null ? new HarmonyMethod(typeof(Plugin), postfixName) : null;
            _harmony.Patch(method, prefix: pre, postfix: post);
            Trace("patched " + type.FullName + "." + methodName + " (prefix=" + (prefixName ?? "-") + ", postfix=" + (postfixName ?? "-") + ")");
        }
        catch (Exception ex)
        {
            Trace("patch " + type.FullName + "." + methodName + " failed: " + ex.Message);
        }
    }

    // Per-instance cache: when we rewrite a state-marker to Chinese for display,
    // we keep the original English here so get_text can return it to the game's
    // own read-back logic (prevents the oscillation, eliminates the flash).
    // Keyed by the text object's GetInstanceID().
    static readonly Dictionary<int, string> StateMarkerOriginals = new Dictionary<int, string>();
    static readonly List<int> _recentTextIds = new List<int>(64);
    static int _forceMarkerCalls;
    static int _forceMarkerHits;

    // Cached state-marker TMP_Text instances. Once found, we reuse them every
    // frame instead of calling Resources.FindObjectsOfTypeAll (expensive).
    static readonly List<TMP_Text> _cachedMarkerTexts = new List<TMP_Text>();
    static bool _loggedEmptyMarkerScan;
    static int _emptyMarkerScanBackoff = 120; // frames between empty scans (grows)
    static int _nextMarkerScanAt;

    internal static void ForceStateMarkersToChinese()
    {
        ForceStateMarkersToChineseCore();
    }

    static void ForceStateMarkersToChineseCore()
    {
        _forceMarkerCalls++;
        try
        {
            // First call: scan all TMP_Text and find state-markers.
            // Cache them so we don't scan every frame.
            if (_cachedMarkerTexts.Count == 0)
            {
                // Back off aggressively while not in a match (store/rulebook/menu
                // have zero state markers). FindObjectsOfTypeAll here was freezing
                // the store and making rulebook open crawl.
                if (_forceMarkerCalls < _nextMarkerScanAt)
                    return;

                var scan = Resources.FindObjectsOfTypeAll<TMP_Text>();
                _nextMarkerScanAt = _forceMarkerCalls + _emptyMarkerScanBackoff;
                if (_emptyMarkerScanBackoff < 3600)
                    _emptyMarkerScanBackoff = Math.Min(3600, _emptyMarkerScanBackoff * 2);

                if (scan == null)
                    return;

                int found = 0;
                foreach (var tmp in scan)
                {
                    if (tmp == null || tmp.gameObject == null)
                        continue;
                    if (!tmp.gameObject.scene.IsValid())
                        continue;
                    var raw = tmp.text;
                    if (string.IsNullOrEmpty(raw))
                        continue;
                    if (IsTutorialProtected(raw))
                        continue;
                    // Only match exact English markers — ignore already-Chinese.
                    if (!PrefixStateMarkers.Contains(raw))
                        continue;
                    _cachedMarkerTexts.Add(tmp);
                    found++;
                }
                if (found == 0)
                {
                    if (!_loggedEmptyMarkerScan)
                    {
                        _loggedEmptyMarkerScan = true;
                        Trace("ForceStateMarkers: no board markers yet; backing off scans");
                    }
                    return;
                }
                _emptyMarkerScanBackoff = 120;
                _loggedEmptyMarkerScan = false;
                Trace("ForceStateMarkers: cached " + found + " state-marker texts");
            }

            // Apply Chinese to all cached marker texts every call.
            var stillValid = new List<TMP_Text>(_cachedMarkerTexts.Count);
            int changed = 0;
            for (int i = 0; i < _cachedMarkerTexts.Count; i++)
            {
                var tmp = _cachedMarkerTexts[i];
                if (tmp == null || tmp.gameObject == null)
                    continue;
                if (!tmp.gameObject.scene.IsValid())
                    continue;
                var raw = tmp.text;
                if (string.IsNullOrEmpty(raw))
                {
                    stillValid.Add(tmp);
                    continue;
                }
                // If the cached text changed to something else (e.g., game
                // progressed to a different turn state), update our cache.
                if (!PrefixStateMarkers.Contains(raw))
                {
                    stillValid.Add(tmp);
                    continue;
                }
                var zh = Rewrite(raw);
                if (zh == null || zh == raw)
                {
                    stillValid.Add(tmp);
                    continue;
                }
                CacheOriginal(tmp.GetInstanceID(), raw);
                // Write Chinese via property setter (goes through our Prefix
                // which already has the translation logic).
                tmp.text = zh;
                try { tmp.ForceMeshUpdate(); } catch { }
                changed++;
                stillValid.Add(tmp);
            }
            _cachedMarkerTexts.Clear();
            _cachedMarkerTexts.AddRange(stillValid);

            if (changed > 0 && _forceMarkerHits < 10)
            {
                _forceMarkerHits++;
                Trace("ForceStateMarkers changed=" + changed + " (call " + _forceMarkerCalls + ")");
            }
        }
        catch (Exception ex)
        {
            Trace("ForceStateMarkers error: " + ex.Message + "\n" + ex.StackTrace);
        }
    }

    static void CacheOriginal(int id, string original)
    {
        if (id == 0 || string.IsNullOrEmpty(original))
            return;
        StateMarkerOriginals[id] = original;
        _recentTextIds.Add(id);
        if (_recentTextIds.Count > 64)
        {
            var oldId = _recentTextIds[0];
            _recentTextIds.RemoveAt(0);
            StateMarkerOriginals.Remove(oldId);
        }
    }

    static string GetCachedOriginal(int id)
    {
        if (id == 0)
            return null;
        return StateMarkerOriginals.TryGetValue(id, out var v) ? v : null;
    }

    static string RewriteIncoming(string value)
    {
        if (string.IsNullOrEmpty(value))
            return null;
        if (HasCjk(value))
            return null;
        if (IsTutorialProtected(value))
            return null;

        bool longCopy = value.Length > 220;
        bool isRulebook = LooksLikeRulebookText(value);
        bool hasKw = ContainsRulebookGameplayKeyword(value);

        var zh = LookupExactOrNormalized(value);
        if (zh != null)
        {
            if (isRulebook || hasKw)
                LogRulebookMatch(value, zh);
            return zh;
        }

        // Long store/rulebook pages: Exact/Norm may miss when the game joins
        // several overlay paragraphs into one TMP. Sentence/paragraph partial
        // rewrite is O(n sentences × dict) and safe — no format SetText hooks.
        if (longCopy || (value.Length >= 80 && (isRulebook || hasKw)))
        {
            var partialZh = TryPartialRewrite(value);
            if (partialZh != null && partialZh != value)
            {
                if (isRulebook || hasKw)
                    LogRulebookMatch(value, partialZh);
                return partialZh;
            }
            if (longCopy)
            {
                if (isRulebook || hasKw)
                {
                    var norm = NormalizeForLookup(value);
                    WriteRulebookDiagnostic($"MISS len={value.Length} normLen={norm.Length} text='{value.Substring(0, Math.Min(150, value.Length))}'");
                }
                return null;
            }
        }

        if (isRulebook || hasKw)
        {
            var norm = NormalizeForLookup(value);
            WriteRulebookDiagnostic($"MISS len={value.Length} normLen={norm.Length} text='{value.Substring(0, Math.Min(150, value.Length))}'");
            return null;
        }

        return Rewrite(value);
    }

    static void LogRulebookMatch(string original, string translated)
    {
        // Disk I/O here previously froze the store/rulebook UI (hundreds of
        // TMP_Text rewrites per RelocalizeUi). Keep diagnostics off unless
        // DumpUntranslated is enabled AND DumpLongStrings is on.
        try
        {
            if (DumpUntranslated == null || !DumpUntranslated.Value)
                return;
            if (DumpLongStrings == null || !DumpLongStrings.Value)
                return;
            var snippet = original.Substring(0, Math.Min(100, original.Length));
            var diagPath = DumpPath.Replace("untranslated.tsv", "rulebook_diagnostic.log");
            File.AppendAllText(diagPath, $"MATCH\t{original.Length}\t{snippet.Replace('\t', ' ').Replace('\r', ' ').Replace('\n', ' ')}\t→\t{translated.Substring(0, Math.Min(80, translated.Length))}\n");
        }
        catch { }
    }

    static void WriteRulebookDiagnostic(string message)
    {
        try
        {
            if (DumpUntranslated == null || !DumpUntranslated.Value)
                return;
            if (DumpLongStrings == null || !DumpLongStrings.Value)
                return;
            var diagPath = DumpPath.Replace("untranslated.tsv", "rulebook_diagnostic.log");
            File.AppendAllText(diagPath, DateTime.Now.ToString("HH:mm:ss.fff") + " " + message + "\n");
        }
        catch { }
    }

    static string TryPartialRewrite(string text)
    {
        // Split text into sentences and try to match each one.
        // Returns the text with matched sentences replaced by their translations.
        // If no sentences match, returns null.
        var sentences = new List<string>();
        var separators = new List<string>();
        int i = 0;
        while (i < text.Length)
        {
            // Find sentence boundaries: ". ", "! ", "? ", or newlines
            int nextEnd = -1;
            int endLen = 0;
            string[] patterns = { ". ", "! ", "? ", ".\n", "!\n", "?\n", "\n", "\r" };
            foreach (var p in patterns)
            {
                int idx = text.IndexOf(p, i, StringComparison.Ordinal);
                if (idx > 0 && (nextEnd < 0 || idx < nextEnd))
                {
                    nextEnd = idx;
                    endLen = p.Length;
                }
            }
            if (nextEnd < 0)
            {
                sentences.Add(text.Substring(i));
                separators.Add("");
                break;
            }
            sentences.Add(text.Substring(i, nextEnd - i));
            separators.Add(text.Substring(nextEnd, endLen));
            i = nextEnd + endLen;
        }

        var result = new System.Text.StringBuilder(text.Length);
        int matchedCount = 0;
        for (int j = 0; j < sentences.Count; j++)
        {
            var sent = sentences[j].Trim();
            if (sent.Length >= 25)
            {
                var zhSent = LookupExactOrNormalized(sent);
                if (zhSent != null && zhSent != sent)
                {
                    result.Append(zhSent);
                    matchedCount++;
                }
                else
                {
                    result.Append(sent);
                }
            }
            else
            {
                result.Append(sent);
            }
            if (j < separators.Count)
                result.Append(separators[j]);
        }

        // Only return the result if we matched at least one sentence
        if (matchedCount > 0 && matchedCount >= sentences.Count / 2)
            return result.ToString();
        return null;
    }

    static bool ContainsRulebookGameplayKeyword(string text)
    {
        if (string.IsNullOrEmpty(text) || text.Length < 40)
            return false;
        var lower = text.ToLowerInvariant();
        foreach (var kw in RulebookGameplayKeywords)
        {
            if (lower.IndexOf(kw, StringComparison.Ordinal) >= 0)
                return true;
        }
        return false;
    }

    static readonly HashSet<string> RulebookGameplayKeywords = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        "runes", "heroes", "constructs", "monsters", "honor",
        "play cards", "acquire", "defeat", "discard pile", "personal deck",
        "shuffled", "deck building", "gain runes", "future turns",
        "replenish", "eligible to be acquired", "glow green",
        "earn rewards", "play your turn",
    };

    // Rulebook-specific keywords that indicate text is part of a rulebook
    // flavor narrative. These are unique enough to not appear in normal UI text.
    static readonly HashSet<string> RulebookKeywords = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        // Lore / story keywords
        "kythis", "gatekeeper", "samael", "deofol", "vigil", "divinations",
        "fallen one", "fallen god", "storm of souls", "godslayer",
        "souls", "afterlife", "purgatory",
        "mortal will", "divine spirit", "yawning gate", "stream of souls",
        "pulsating force", "cosmic events", "darkest portent",
        "frightful tale", "reddened", "wrathful and red",
        "the cultist", "end turn", "end your turn",
        "flames of war", "war's wake", "storm looms", "call echo",
        "reckoning", "ghostly tide", "event zone", "trophy monster",
        "fanatic", "construct tray", "center row", "honor points",
        "play order", "end game", "lifebound", "mechana", "void",
        "dream vision", "champion", "dreams", "nightmares",
        "insight", "dreamborn", "goblin", "temple",
        "multi-faction", "war of shadows", "dawn of champions",
        "realms unraveled", "dreamscape", "valley of the ancients",
        "rise of vigil", "darkness unleashed", "delirium",
        "portal deck", "portal cards", "ethereal",
        // Gameplay keywords (for detecting plain-text rulebook paragraphs)
        "runes", "heroes", "constructs", "monsters", "honor",
        "play cards", "acquire", "defeat", "discard pile", "personal deck",
        "shuffled", "deck building", "card from your hand",
        "gain runes", "future turns", "rewards", "replenish",
        "placed into your discard", "eligible to be acquired",
        "glow green", "play your turn", "earn rewards",
    };

    static bool LooksLikeRulebookText(string text)
    {
        if (string.IsNullOrEmpty(text))
            return false;
        int len = text.Length;

        // Has rich-text tags — hallmark of rulebook body text
        if (text.IndexOf("<br", StringComparison.OrdinalIgnoreCase) >= 0)
            return true;
        if (text.IndexOf("<sprite", StringComparison.OrdinalIgnoreCase) >= 0)
            return true;
        if (text.IndexOf("<allcaps", StringComparison.OrdinalIgnoreCase) >= 0)
            return true;
        if (text.IndexOf("<indent=", StringComparison.OrdinalIgnoreCase) >= 0)
            return true;
        if (text.IndexOf("<margin=", StringComparison.OrdinalIgnoreCase) >= 0)
            return true;
        if (text.IndexOf("<smallcaps", StringComparison.OrdinalIgnoreCase) >= 0)
            return true;

        // Long text with multiple lines (may have <br> or actual newlines)
        if (len > 200 && (text.IndexOf('\n') >= 0 || text.IndexOf('\r') >= 0))
            return true;

        // Plain-text rulebook paragraph detection:
        // 1) Numbered list items (e.g., "1. Play cards...", "2. After you...")
        //    with rulebook keywords
        if (len >= 80)
        {
            var lower = text.ToLowerInvariant();
            int kwCount = 0;
            foreach (var kw in RulebookKeywords)
            {
                if (lower.IndexOf(kw, StringComparison.Ordinal) >= 0)
                    kwCount++;
            }
            if (kwCount >= 2)
                return true;
        }

        // 2) Plain text >= 100 chars that starts with a number prefix ("1.", "2.", etc.)
        //    followed by rulebook content
        if (len >= 100 && len <= 600)
        {
            var trimmed = text.TrimStart();
            if (trimmed.Length > 0 && char.IsDigit(trimmed[0]))
            {
                // Check if there's a period or paren after the digit(s)
                int idx = 0;
                while (idx < trimmed.Length && char.IsDigit(trimmed[idx]))
                    idx++;
                if (idx < trimmed.Length && (trimmed[idx] == '.' || trimmed[idx] == ')' || trimmed[idx] == ' '))
                {
                    // Numbered item — likely rulebook list
                    return true;
                }
            }
        }

        // 3) Long plain text with multiple sentences and rulebook keywords
        if (len >= 120 && len <= 800)
        {
            var lower = text.ToLowerInvariant();
            int kwCount = 0;
            foreach (var kw in RulebookKeywords)
            {
                if (lower.IndexOf(kw, StringComparison.Ordinal) >= 0)
                    kwCount++;
            }
            if (kwCount >= 1)
            {
                // Count sentences
                int sentences = 0;
                for (int i = 0; i < text.Length; i++)
                {
                    char c = text[i];
                    if (c == '.' || c == '!' || c == '?')
                    {
                        if (i == text.Length - 1 || char.IsWhiteSpace(text[i + 1]))
                            sentences++;
                    }
                }
                if (sentences >= 2)
                    return true;
            }
        }

        return false;
    }

    static bool ShouldDumpAsLong(string text)
    {
        if (string.IsNullOrEmpty(text))
            return false;
        // Always dump long text
        if (text.Length > 400)
            return true;
        // Always dump text with sprite tags
        if (text.IndexOf("<sprite", StringComparison.OrdinalIgnoreCase) >= 0)
            return true;
        // Also dump rulebook-like short text (has <br>, <allcaps>, <indent>, <margin>, <smallcaps>)
        // These are individual rulebook paragraphs that need full-sentence translation.
        if (LooksLikeRulebookText(text))
            return true;
        return false;
    }

    // === set_text / SetText Prefixes: rewrite incoming text to Chinese ===

    static void TmpTextSetPrefix(ref string value, TMP_Text __instance)
    {
        if (string.IsNullOrEmpty(value))
            return;
        if (_inRewrite)
            return; // re-entrancy guard
        if (IsTutorialProtected(value))
            return;
        // State markers: rewrite to Chinese visually AND cache the original
        // English so the game's own read-back (via get_text) still works.
        if (PrefixStateMarkers.Contains(value))
        {
            _inRewrite = true;
            var zh = Rewrite(value);
            _inRewrite = false;
            if (zh != null && zh != value)
            {
                CacheOriginal(__instance != null ? __instance.GetInstanceID() : 0, value);
                value = zh;
            }
            return;
        }
        _inRewrite = true;
        var translated = RewriteIncoming(value);
        _inRewrite = false;
        if (translated != null)
            value = translated;
        else if (ShouldDumpAsLong(value))
            MaybeDump("L", value, null);
    }

    static void UiTextSetPrefix(ref string value, Text __instance)
    {
        if (string.IsNullOrEmpty(value))
            return;
        if (_inRewrite)
            return;
        if (IsTutorialProtected(value))
            return;
        if (PrefixStateMarkers.Contains(value))
        {
            _inRewrite = true;
            var zh = Rewrite(value);
            _inRewrite = false;
            if (zh != null && zh != value)
            {
                CacheOriginal(__instance != null ? __instance.GetInstanceID() : 0, value);
                value = zh;
            }
            return;
        }
        _inRewrite = true;
        var translated = RewriteIncoming(value);
        _inRewrite = false;
        if (translated != null)
            value = translated;
        else if (ShouldDumpAsLong(value))
            MaybeDump("L", value, null);
    }

    static void TextMeshSetPrefix(ref string value, TextMesh __instance)
    {
        if (string.IsNullOrEmpty(value))
            return;
        if (_inRewrite)
            return;
        if (IsTutorialProtected(value))
            return;
        if (PrefixStateMarkers.Contains(value))
        {
            _inRewrite = true;
            var zh = Rewrite(value);
            _inRewrite = false;
            if (zh != null && zh != value)
            {
                CacheOriginal(__instance != null ? __instance.GetInstanceID() : 0, value);
                value = zh;
            }
            return;
        }
        _inRewrite = true;
        var translated = RewriteIncoming(value);
        _inRewrite = false;
        if (translated != null)
            value = translated;
        else if (ShouldDumpAsLong(value))
            MaybeDump("L", value, null);
    }

    // === get_text Postfixes: return cached original English for state markers ===

    static void TmpTextGetPostfix(TMP_Text __instance, ref string __result)
    {
        if (__instance == null || string.IsNullOrEmpty(__result))
            return;
        if (IsTutorialProtected(__result))
            return;
        if (!PrefixStateMarkers.Contains(__result))
            return;
        var original = GetCachedOriginal(__instance.GetInstanceID());
        if (original != null)
            __result = original;
    }

    static void UiTextGetPostfix(Text __instance, ref string __result)
    {
        if (__instance == null || string.IsNullOrEmpty(__result))
            return;
        if (IsTutorialProtected(__result))
            return;
        if (!PrefixStateMarkers.Contains(__result))
            return;
        var original = GetCachedOriginal(__instance.GetInstanceID());
        if (original != null)
            __result = original;
    }

    static void TextMeshGetPostfix(TextMesh __instance, ref string __result)
    {
        if (__instance == null || string.IsNullOrEmpty(__result))
            return;
        if (IsTutorialProtected(__result))
            return;
        if (!PrefixStateMarkers.Contains(__result))
            return;
        var original = GetCachedOriginal(__instance.GetInstanceID());
        if (original != null)
            __result = original;
    }

    internal static void PatchSceneLoaded()
    {
        if (_sceneHooked)
            return;
        _sceneHooked = true;
        try
        {
            SceneManager.sceneLoaded += DelegateSupport.ConvertDelegate<UnityEngine.Events.UnityAction<Scene, LoadSceneMode>>(OnSceneLoaded);
            Trace("sceneLoaded hooked");
        }
        catch (Exception ex)
        {
            Trace("sceneLoaded hook failed: " + ex);
        }
    }

    static void OnSceneLoaded(Scene scene, LoadSceneMode mode)
    {
        try
        {
            // Drop marker cache — previous scene's TMP instances are gone.
            _cachedMarkerTexts.Clear();
            _loggedEmptyMarkerScan = false;
            _emptyMarkerScanBackoff = 180;
            _nextMarkerScanAt = _forceMarkerCalls + 180;

            RelocalizeUi();
            RelocalizeKnownPanels();
            // Match / board scenes need marker cache sooner than menus/store.
            var sn = scene.name ?? "";
            if (sn.IndexOf("Match", StringComparison.OrdinalIgnoreCase) >= 0
                || sn.IndexOf("Game", StringComparison.OrdinalIgnoreCase) >= 0
                || sn.IndexOf("Battle", StringComparison.OrdinalIgnoreCase) >= 0
                || sn.IndexOf("Play", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                _emptyMarkerScanBackoff = 30;
                _nextMarkerScanAt = _forceMarkerCalls + 15;
            }
            Trace("sceneLoaded: " + scene.name + " relocalized");
        }
        catch (Exception ex)
        {
            Trace("sceneLoaded relocalize failed: " + ex.Message);
        }
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
                if (src.IndexOf("<sprite", StringComparison.OrdinalIgnoreCase) >= 0)
                    return;
                if (!LooksEnglishUi(src))
                    return;
            }
            else if (kind == "L")
            {
                // Long-string path: rulebook body text + DLC store copy.
                // Skip ${...} templates (LocalizationService placeholders);
                // allow <sprite> tags and strings up to DumpLongMaxLen.
                if (DumpLongStrings == null || !DumpLongStrings.Value)
                    return;
                if (src.IndexOf("${", StringComparison.Ordinal) >= 0)
                    return;
                if (src.Length > DumpLongMaxLen)
                    return;
                if (!LooksLongEnglish(src))
                    return;
            }
            else
            {
                // kind == "K" or anything else: fall through to dedup/write.
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

    static bool LooksLongEnglish(string text)
    {
        if (text.Length < 3 || HasCjk(text))
            return false;
        var letters = 0;
        foreach (var ch in text)
        {
            if ((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z'))
                letters++;
        }
        return letters >= 3;
    }

    static bool LooksEnglishUi(string text)
    {
        if (text.Length < 3 || text.Length > 400 || HasCjk(text))
            return false;
        var letters = 0;
        foreach (var ch in text)
        {
            if ((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z'))
                letters++;
        }
        return letters >= 3;
    }

    static string EscapeDump(string value)
    {
        return value.Replace("\\", "\\\\").Replace("\r", "\\r").Replace("\n", "\\n").Replace("\t", "\\t");
    }

    static void LocPostfix(string __0, ref string __result)
    {
        try
        {
            if (string.IsNullOrEmpty(__0))
                return;
            if (!Keys.TryGetValue(__0, out var zh) || string.IsNullOrEmpty(zh))
            {
                // Phase 3: expand effective L1 — if GetTextByKey still returns
                // English but Exact/Norm already knows it, rewrite here so TMP
                // never flashes the English sample (L2 would catch it one frame later).
                if (!string.IsNullOrEmpty(__result) && !HasCjk(__result))
                {
                    var viaExact = LookupExactOrNormalized(__result);
                    if (!string.IsNullOrEmpty(viaExact) && viaExact != __result)
                    {
                        __result = viaExact;
                        return;
                    }
                }
                MaybeDump("K", __0, __result);
                return;
            }
            if (zh.Contains("${") && _convertEmbedded != null)
            {
                try
                {
                    var converted = _convertEmbedded.Invoke(_convertEmbedded.IsStatic ? null : null, new object[] { zh }) as string;
                    if (!string.IsNullOrEmpty(converted))
                        zh = converted;
                }
                catch
                {
                }
            }
            __result = zh;
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
    };

    static string ReplaceRemainders(string text)
    {
        if (string.IsNullOrEmpty(text))
            return null;
        // Skip regex chain for very long text to avoid catastrophic
        // backtracking (rulebook pages are often 2000+ chars).
        if (text.Length > RewriteMaxLen)
            return null;
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
        next = Regex.Replace(next, @"\bReward:\s*", "奖励：", RegexOptions.IgnoreCase);
        next = Regex.Replace(next, @"Purchase:\s*\$(\d+(?:\.\d+)?)", "购买：$$$1");
        next = Regex.Replace(next, @"\bPromo\s+(\d+)\b", "特典 $1", RegexOptions.IgnoreCase);
        return next != text ? next : null;
    }

    internal static string Rewrite(string text)
    {
        if (string.IsNullOrEmpty(text))
            return null;
        // Tutorial click prompts are game-critical (hit-testing for the
        // continue button). Never translate them — the overlay generator
        // also deliberately skips them in Phase 0 (project memory).
        if (IsTutorialProtected(text))
            return null;
        if (text.IndexOf("CLICK", StringComparison.OrdinalIgnoreCase) >= 0
            || text.IndexOf("<link", StringComparison.OrdinalIgnoreCase) >= 0)
        {
            return RewriteClickPrompt(text);
        }
        // Safety: skip word-by-word rewriting for rulebook-like text.
        // This prevents the mixed Chinese/English garbage seen in rulebook pages.
        if (LooksLikeRulebookText(text) || ContainsRulebookGameplayKeyword(text))
        {
            // Try overlay lookup one last time
            var translated = LookupExactOrNormalized(text);
            return translated; // null if not found (preserve original)
        }
        // For very long text (rulebook pages), skip regex chain and go
        // straight to Exact / Normalized lookup to avoid catastrophic
        // backtracking.
        if (text.Length > RewriteMaxLen)
        {
            return LookupExactOrNormalized(text);
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
        if (Exact.TryGetValue(text, out zh) && zh != text)
            return zh;
        var trimmed = text.Trim();
        if (trimmed != text && Exact.TryGetValue(trimmed, out zh) && zh != trimmed)
            return zh;
        var normalized = NormalizeUi(text);
        if (normalized.Length != 0 && Exact.TryGetValue(normalized, out zh) && zh != normalized)
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
        return remainder;
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

    // Rulebook sweep state
    static readonly HashSet<int> RulebookSeenIds = new HashSet<int>();
    const int RulebookSweepInterval = 3; // frames
    static int _rulebookSweepCounter;
    static int _rulebookMissLogged;

    internal static void SweepAllTexts()
    {
        try
        {
            _rulebookSweepCounter++;
            if (_rulebookSweepCounter < RulebookSweepInterval)
                return;
            _rulebookSweepCounter = 0;

            var texts = Resources.FindObjectsOfTypeAll<TMP_Text>();
            if (texts == null)
                return;
            int changed = 0;
            foreach (var tmp in texts)
            {
                if (tmp == null || tmp.gameObject == null || !tmp.gameObject.scene.IsValid())
                    continue;
                var text = tmp.text;
                if (string.IsNullOrEmpty(text) || HasCjk(text))
                    continue;
                // Skip tutorial-protected text
                if (IsTutorialProtected(text))
                    continue;
                // State markers are handled by ForceStateMarkers
                if (PrefixStateMarkers.Contains(text))
                    continue;

                // Try full lookup (both exact and normalized)
                var zh = LookupExactOrNormalized(text);
                if (zh != null && zh != text)
                {
                    _inRewrite = true;
                    tmp.text = zh;
                    _inRewrite = false;
                    try { tmp.ForceMeshUpdate(); } catch { }
                    changed++;
                    continue;
                }

                // If it looks like rulebook text, log the miss and skip
                // word-by-word rewriting to avoid garbage output.
                if (LooksLikeRulebookText(text))
                {
                    _rulebookMissLogged++;
                    if (_rulebookMissLogged <= 50)
                    {
                        var norm = NormalizeForLookup(text);
                        Trace($"RULEBOOK_MISS: len={text.Length} normLen={norm.Length} sample='{text.Substring(0, Math.Min(100, text.Length))}'...");
                    }
                    // Still dump it so we can ingest it
                    MaybeDump("L", text, null);
                    continue;
                }

                // For non-rulebook text, try Rewrite for word-level fixes
                var rewritten = Rewrite(text);
                if (rewritten != null && rewritten != text)
                {
                    _inRewrite = true;
                    tmp.text = rewritten;
                    _inRewrite = false;
                    try { tmp.ForceMeshUpdate(); } catch { }
                    changed++;
                }
            }
            if (changed > 0)
                Trace("sweep translated " + changed + " texts");
        }
        catch
        {
        }
    }

    static readonly HashSet<int> FontsHooked = new HashSet<int>();

    // Text that the game uses for internal state comparison / toggle logic.
    // If the Prefix rewrites these, the game's own read-back sees Chinese,
    // takes the wrong branch, and oscillates on the next click. These fall
    // back to the Postfix (which rewrites AFTER the game's toggle logic ran)
    // for translation, giving a one-frame lag but stable game behavior.
    static readonly HashSet<string> PrefixStateMarkers = new HashSet<string>(StringComparer.Ordinal)
    {
        "Play Your Turn",
        "PLAY YOUR TURN",
        "End Turn",
        "END TURN",
        "End\nTurn",
        "END\nTURN",
    };

    // Tutorial click prompts contain "CLICK" or <link> tags that the game
    // uses for hit-testing the tutorial continue button. Rewriting these
    // breaks the click relay (memory: tutorial translation deliberately
    // disabled in overlay.py Phase 0 until click functionality is restored).
    // These are NEVER rewritten by either Prefix or Postfix.
    static bool IsTutorialProtected(string value)
    {
        if (string.IsNullOrEmpty(value))
            return false;
        if (value.IndexOf("CLICK", StringComparison.OrdinalIgnoreCase) >= 0)
            return true;
        if (value.IndexOf("<link", StringComparison.OrdinalIgnoreCase) >= 0)
            return true;
        return false;
    }

    static bool IsPrefixDenied(string value)
    {
        if (string.IsNullOrEmpty(value))
            return false;
        if (IsTutorialProtected(value))
            return true; // never touch tutorial prompts in the Prefix
        if (PrefixStateMarkers.Contains(value))
            return true;
        return false;
    }

    // Postfix helper: rewrite only state markers (tutorial text stays untouched).
    static bool IsPostfixCandidate(string value)
    {
        if (string.IsNullOrEmpty(value))
            return false;
        if (IsTutorialProtected(value))
            return false; // tutorial text: NEVER rewrite
        return PrefixStateMarkers.Contains(value);
    }

    static readonly string[] KnownPanelNames =
    {
        // Only rulebook roots — store is handled by set_text/SetText hooks.
        // Sweeping a Store root with GetComponentsInChildren(true) re-scanned
        // hundreds of inactive DLC blurbs every 40 frames and froze the UI.
        "Rulebook", "RuleBooks", "Rulebooks", "RulebookPanel", "RulebookMenu",
        "RulebookASCL", "RulebookCotG", "RulebookDLRM", "RulebookDLV", "RulebookDS",
        "RulebookDU", "RulebookDoC", "RulebookGotE", "RulebookIH", "RulebookRoV",
        "RulebookRotF", "RulebookSoS", "RulebookVotA", "RulebookWoS", "RulebookRU",
    };


    internal static void PatchPreRender()
    {
        if (_preRenderHooked)
            return;
        _preRenderHooked = true;
        try
        {
            // Last chance before the camera draws — closes the one-frame EN
            // window that LateUpdate alone can miss when the game resets
            // state-marker text after LateUpdate.
            Camera.onPreRender += DelegateSupport.ConvertDelegate<Camera.CameraCallback>(OnCameraPreRender);
            Trace("Camera.onPreRender hooked");
        }
        catch (Exception ex)
        {
            Trace("onPreRender hook failed: " + ex.Message);
        }
    }

    static void OnCameraPreRender(Camera cam)
    {
        if (!_ready)
            return;
        ForceStateMarkersToChinese();
    }

    internal static void RelocalizeKnownPanels()
    {
        if (!_installed || _cjk == null)
            return;
        try
        {
            int changed = 0;
            foreach (var name in KnownPanelNames)
            {
                GameObject go = null;
                try { go = GameObject.Find(name); } catch { }
                if (go == null)
                    continue;
                changed += RelocalizeUnder(go.transform, 120);
                if (changed >= 80)
                    break;
            }
            if (changed > 0)
                Trace("panelSweep changed=" + changed);
        }
        catch (Exception ex)
        {
            Trace("RelocalizeKnownPanels: " + ex.Message);
        }
    }

    static int RelocalizeUnder(Transform root, int budget)
    {
        if (root == null || budget <= 0)
            return 0;
        int changed = 0;
        TMP_Text[] texts = null;
        try { texts = root.GetComponentsInChildren<TMP_Text>(false); } catch { return 0; }
        if (texts == null)
            return 0;
        foreach (var tmp in texts)
        {
            if (changed >= budget)
                break;
            if (tmp == null)
                continue;
            try
            {
                var text = tmp.text;
                if (string.IsNullOrEmpty(text) || HasCjk(text))
                    continue;
                if (IsTutorialProtected(text))
                    continue;
                var zh = LookupExactOrNormalized(text);
                if (zh == null || zh == text)
                    continue;
                _inRewrite = true;
                tmp.text = zh;
                _inRewrite = false;
                changed++;
            }
            catch
            {
                _inRewrite = false;
            }
        }
        return changed;
    }

    internal static void RelocalizeUi()
    {
        if (!_installed || _cjk == null)
            return;
        try
        {
            var texts = Resources.FindObjectsOfTypeAll<TMP_Text>();
            if (texts == null)
                return;
            var changed = 0;
            foreach (var tmp in texts)
            {
                try
                {
                    if (tmp == null || tmp.gameObject == null || !tmp.gameObject.scene.IsValid())
                        continue;
                    // Include inactive scene objects: hex menu labels are often
                    // inactive at FrontEnd load and only SetText(string) later.
                    // Still skip assets not in a scene (prefab isolates).
                    var font = tmp.font;
                    if (font != null && font != _cjk)
                    {
                        var fid = font.GetInstanceID();
                        if (!FontsHooked.Contains(fid))
                        {
                            var table = font.fallbackFontAssetTable;
                            if (table != null)
                                table.Add(_cjk);
                            FontsHooked.Add(fid);
                        }
                    }
                    var text = tmp.text;
                    if (string.IsNullOrEmpty(text) || HasCjk(text))
                        continue;

                    // Inactive long copy: skip (store keeps dormant DLC TMP alive).
                    // Inactive short labels: still rewrite (hex menu buttons).
                    if (!tmp.isActiveAndEnabled && text.Length > 80)
                        continue;

                    // Prefer RewriteIncoming (Exact/Norm/overlay) over Rewrite.
                    var rewriteResult = RewriteIncoming(text);
                    if (rewriteResult == null && text.Length <= 220)
                        rewriteResult = Rewrite(text);
                    if (rewriteResult != null && rewriteResult != text)
                    {
                        _inRewrite = true;
                        tmp.text = rewriteResult;
                        _inRewrite = false;
                        text = rewriteResult;
                        changed++;
                    }
                    else if (text.Length <= 220)
                    {
                        MaybeDump("E", text, null);
                    }
                    if (HasCjk(text) && text.Length <= 40)
                    {
                        try
                        {
                            tmp.overflowMode = TextOverflowModes.Overflow;
                        }
                        catch
                        {
                        }
                    }
                }
                catch
                {
                }
            }
            try
            {
                var uiTexts = Resources.FindObjectsOfTypeAll<Text>();
                if (uiTexts != null)
                {
                    foreach (var label in uiTexts)
                    {
                        try
                        {
                            if (label == null || label.gameObject == null || !label.gameObject.scene.IsValid())
                                continue;
                            var zh = Rewrite(label.text);
                            if (zh != null && zh != label.text)
                            {
                                label.text = zh;
                                changed++;
                            }
                            else
                            {
                                MaybeDump("E", label.text, null);
                                if (label.text != null && (label.text.Length > 400 || label.text.IndexOf("<sprite", StringComparison.OrdinalIgnoreCase) >= 0))
                                    MaybeDump("L", label.text, null);
                            }
                            if (HasCjk(label.text))
                            {
                                var font = UiCjkFont();
                                if (font != null)
                                    label.font = font;
                            }
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
                var meshes = Resources.FindObjectsOfTypeAll<TextMesh>();
                if (meshes != null)
                {
                    foreach (var mesh in meshes)
                    {
                        try
                        {
                            if (mesh == null || mesh.gameObject == null || !mesh.gameObject.scene.IsValid())
                                continue;
                            var zh = Rewrite(mesh.text);
                            if (zh != null && zh != mesh.text)
                            {
                                mesh.text = zh;
                                changed++;
                            }
                            if (HasCjk(mesh.text))
                            {
                                var font = UiCjkFont();
                                if (font != null)
                                    mesh.font = font;
                            }
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
                Trace("relocalized " + changed + " texts");
        }
        catch (Exception ex)
        {
            Trace("RelocalizeUi: " + ex.Message);
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
    bool _loggedFirst;

    public CjkFontBehaviour(IntPtr ptr) : base(ptr)
    {
    }

    void Update()
    {
        _frames++;
        if (!_loggedFirst)
        {
            _loggedFirst = true;
            Plugin.Trace("first Update frame (CJK fallback watcher)");
        }
        if (!Plugin.IsReady)
        {
            if (_frames >= 30 && _frames % 30 == 0)
            {
                Plugin.EnsureCjkFallback();
                if (Plugin.IsReady)
                {
                    Plugin.PatchTextSetters();
                    Plugin.PatchSceneLoaded();
                    Plugin.PatchPreRender();
                }
            }
            return;
        }
        if (_frames % 3600 == 0)
            Plugin.RelocalizeUi();
        // Rulebook roots only — cheap GameObject.Find, no store freeze risk.
        if (_frames % 90 == 0)
            Plugin.RelocalizeKnownPanels();
        // Catch menus that activate after scene load (hex buttons).
        // Budget: every ~3s (was 2s); RelocalizeUi is Exact/Norm-safe.
        if (_frames % 180 == 0)
            Plugin.RelocalizeUi();
    }

    // LateUpdate runs AFTER all Update() calls in the scene, meaning
    // the game's per-frame text resets (Play Your Turn → English) have
    // already happened. We run the watchdog here as a belt-and-suspenders
    // approach — Camera.onPreRender also handles it for the absolute last
    // write before render.
    void LateUpdate()
    {
        if (!Plugin.IsReady)
            return;
        // Run every frame (not every 3) to minimize the window where
        // English might be visible.
        Plugin.ForceStateMarkersToChinese();
        // SweepAllTexts is intentionally NOT called here — it did a full
        // scene scan (Resources.FindObjectsOfTypeAll) every 3 frames which
        // caused the game to freeze when entering rulebook scenes with many
        // TMP_Text components. The set_text PREFIX hook already handles
        // runtime text changes; the sweep is only needed once on scene load
        // (handled by RelocalizeScene).
    }
}
