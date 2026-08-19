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

[BepInPlugin("ascension.zh.cn", "Ascension Chinese overlay", "1.3.2")]
public class Plugin : BasePlugin
{
    internal static Plugin Instance;
    static TMP_FontAsset _cjk;
    static bool _installed;
    static bool _attempted;
    static bool _locPatched;
    static bool _ready;
    internal static bool IsReady
    {
        get { return _ready; }
    }
    static string LogPath = "";
    static string DumpPath = "";
    static ConfigEntry<bool> DumpUntranslated;
    static readonly HashSet<string> Dumped = new HashSet<string>();
    const int DumpMax = 2500;
    static Harmony _harmony;
    static MethodInfo _convertEmbedded;

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
            File.WriteAllText(LogPath, DateTime.Now + " plugin Load() 1.3.2 (gallery drop-cap + glossary)\n");
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
                    Exact[src] = zh;
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
    }

    static string Unescape(string value)
    {
        return value.Replace("\\n", "\n").Replace("\\t", "\t").Replace("\\\\", "\\");
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

    static readonly HashSet<int> FontsHooked = new HashSet<int>();

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
                    var zh = Rewrite(text);
                    if (zh != null && zh != text)
                    {
                        tmp.text = zh;
                        text = zh;
                        changed++;
                    }
                    else
                        MaybeDump("E", text, null);
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
                                MaybeDump("E", label.text, null);
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
            Plugin.Trace("first Update frame (waiting before touching TMP)");
        }
        if (_frames == 50)
            Plugin.Trace("delay elapsed, installing CJK font");
        if (_frames < 50)
            return;
        Plugin.EnsureCjkFallback();
        if (_frames % 30 == 0)
            Plugin.RelocalizeUi();
    }
}
