using System.Text;
using System.Text.RegularExpressions;

namespace AscensionZhCn.Installer;

internal static class LuaPatcher
{
    public static int PatchDirectory(string luaDir, string backupDir, string cardsCsv, string? combatLogCsv, Action<string> log)
    {
        Directory.CreateDirectory(backupDir);
        if (!Directory.Exists(backupDir) || Directory.GetFiles(backupDir, "*.lua").Length == 0)
        {
            foreach (var src in Directory.GetFiles(luaDir, "*.lua"))
                File.Copy(src, Path.Combine(backupDir, Path.GetFileName(src)), overwrite: true);
            log("已备份 Lua -> " + backupDir);
        }
        else
        {
            foreach (var src in Directory.GetFiles(backupDir, "*.lua"))
                File.Copy(src, Path.Combine(luaDir, Path.GetFileName(src)), overwrite: true);
            log("已从备份还原英文 Lua，再写入中文效果");
        }

        var cards = CsvUtil.Named(cardsCsv);
        var messages = string.IsNullOrEmpty(combatLogCsv)
            ? new Dictionary<string, string>()
            : CsvUtil.TwoCol(combatLogCsv, "en", "zh");

        var changed = 0;
        foreach (var path in Directory.GetFiles(luaDir, "*.lua"))
        {
            var original = File.ReadAllText(path);
            var patched = PatchFile(original, cards, messages);
            if (patched != original)
            {
                File.WriteAllText(path, patched.Replace("\r\n", "\n"), new UTF8Encoding(false));
                changed++;
            }
        }
        log($"已改写 {changed} 个 Lua 文件");
        return changed;
    }

    public static void RestoreDirectory(string luaDir, string backupDir)
    {
        if (!Directory.Exists(backupDir))
            throw new DirectoryNotFoundException("没有 Lua 备份，无法恢复。路径: " + backupDir);
        var files = Directory.GetFiles(backupDir, "*.lua");
        if (files.Length == 0)
            throw new DirectoryNotFoundException("Lua 备份是空的: " + backupDir);
        foreach (var src in files)
            File.Copy(src, Path.Combine(luaDir, Path.GetFileName(src)), overwrite: true);
    }

    static string PatchFile(string text, Dictionary<string, Dictionary<string, string>> cards, Dictionary<string, string> messages)
    {
        var outParts = new StringBuilder();
        var last = 0;
        foreach (Match m in Regex.Matches(text, @"g_ascension_cards\[""([^""]+)""\]\s*=\s*\{"))
        {
            outParts.Append(text, last, m.Index + m.Length - 1 - last);
            var start = m.Index + m.Length - 1;
            var depth = 0;
            var i = start;
            var closed = false;
            while (i < text.Length)
            {
                var ch = text[i];
                if (ch == '{')
                    depth++;
                else if (ch == '}')
                {
                    depth--;
                    if (depth == 0)
                    {
                        var body = text.Substring(start + 1, i - start - 1);
                        if (cards.TryGetValue(m.Groups[1].Value, out var row))
                        {
                            if (row.TryGetValue("effect_text", out var effect) && !string.IsNullOrEmpty(effect))
                                body = ReplaceField(body, "effect_text", effect);
                            if (row.TryGetValue("flavor_text", out var flavor) && !string.IsNullOrEmpty(flavor))
                                body = ReplaceField(body, "flavor_text", flavor);
                        }
                        outParts.Append('{');
                        outParts.Append(body);
                        outParts.Append('}');
                        last = i + 1;
                        closed = true;
                        break;
                    }
                }
                else if (ch == '"')
                {
                    i++;
                    while (i < text.Length)
                    {
                        if (text[i] == '\\')
                        {
                            i += 2;
                            continue;
                        }
                        if (text[i] == '"')
                            break;
                        i++;
                    }
                }
                i++;
            }
            if (!closed)
            {
                outParts.Append(text, start, text.Length - start);
                last = text.Length;
                break;
            }
        }
        outParts.Append(text, last, text.Length - last);
        var patched = outParts.ToString();
        foreach (var pair in messages)
        {
            if (!string.IsNullOrEmpty(pair.Key) && !string.IsNullOrEmpty(pair.Value))
                patched = patched.Replace(pair.Key, pair.Value);
        }
        return patched;
    }

    static string ReplaceField(string body, string field, string newValue)
    {
        var escaped = '"' + LuaEscape(newValue) + '"';
        var pattern = new Regex(
            "(" + Regex.Escape(field) + @"\s*=\s*)(?:""(?:\\.|[^""\\])*""(?:\s*\.\.\s*)?)+",
            RegexOptions.Singleline);
        var replaced = pattern.Replace(body, m => m.Groups[1].Value + escaped, 1);
        return replaced;
    }

    static string LuaEscape(string value)
    {
        value = value.Replace("\r\n", " ").Replace("\n", " ").Replace("\r", " ").Trim();
        return value.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }
}
