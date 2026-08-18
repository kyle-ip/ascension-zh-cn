using System.Text;
using System.Text.RegularExpressions;

namespace AscensionZhCn.Installer;

internal static class AssetPatcher
{
    static readonly Encoding Latin1 = Encoding.Latin1;

    public static void BackupIfNeeded(string gameRoot, string backupDir, Action<string> log)
    {
        Directory.CreateDirectory(backupDir);
        var src = Path.Combine(gameRoot, "AscensionGame_Data", "resources.assets");
        var dest = Path.Combine(backupDir, "resources.assets");
        if (!File.Exists(dest))
        {
            File.Copy(src, dest);
            log("已备份 resources.assets");
        }
    }

    public static void Restore(string gameRoot, string backupDir, Action<string> log)
    {
        var src = Path.Combine(backupDir, "resources.assets");
        if (!File.Exists(src))
        {
            log("没有 resources.assets 备份，跳过");
            return;
        }
        File.Copy(src, Path.Combine(gameRoot, "AscensionGame_Data", "resources.assets"), overwrite: true);
        log("已还原 resources.assets");
    }

    public static void ApplyTextAsset(string gameRoot, string backupDir, string assetName, string csvPath, byte[][] markers, Action<string> log)
    {
        var live = Path.Combine(gameRoot, "AscensionGame_Data", "resources.assets");
        var backup = Path.Combine(backupDir, "resources.assets");
        File.Copy(backup, live, overwrite: true);
        var blob = File.ReadAllBytes(live);
        blob = ReplaceNamedBlob(blob, Encoding.ASCII.GetBytes(assetName), markers, File.ReadAllText(csvPath));
        File.WriteAllBytes(live, blob);
        log("已写入 TextAsset " + assetName);
    }

    public static void ApplyLocJson(string gameRoot, Dictionary<string, string> mapping, Action<string> log)
    {
        var path = Path.Combine(gameRoot, "AscensionGame_Data", "resources.assets");
        var data = File.ReadAllBytes(path);
        var marker = Encoding.ASCII.GetBytes("\"1:1\":\"Key\"");
        var pattern = new Regex(
            "\"(\\d+):1\":\"((?:CARDNAME_|EFFECT_|LABEL_|FATE_|TROPHY_|ENERGY_|DAY_|NIGHT_|Key_|TUTORIAL_|FLAVOR_|IAP_|DLC_)[^\"]+)\",\"\\1:2\":\"((?:\\\\.|[^\"\\\\])*)\"",
            RegexOptions.Compiled);
        var patched = 0;
        var skipped = 0;
        var blobs = 0;
        var pos = 0;
        while (true)
        {
            var start = IndexOf(data, marker, pos);
            if (start < 0)
                break;
            var jsonAt = LastIndexOf(data, (byte)'{', Math.Max(0, start - 80), start);
            if (jsonAt < 0)
                jsonAt = start;
            var end = IndexOf(data, new byte[] { 0 }, start);
            if (end < 0)
                break;
            var slice = new byte[end - jsonAt];
            Buffer.BlockCopy(data, jsonAt, slice, 0, slice.Length);
            var text = Latin1.GetString(slice);
            var next = pattern.Replace(text, m =>
            {
                var key = m.Groups[2].Value;
                if (key.StartsWith("Key_Hint_", StringComparison.Ordinal) || key.StartsWith("TUTORIAL_", StringComparison.Ordinal))
                    return m.Value;
                if (!mapping.TryGetValue(key, out var zh) || string.IsNullOrEmpty(zh))
                    return m.Value;
                var oldVal = Latin1.GetBytes(m.Groups[3].Value);
                var newVal = Encoding.UTF8.GetBytes(JsonEscape(zh));
                if (newVal.Length > oldVal.Length)
                {
                    skipped++;
                    return m.Value;
                }
                var padded = new byte[oldVal.Length];
                Buffer.BlockCopy(newVal, 0, padded, 0, newVal.Length);
                for (var i = newVal.Length; i < padded.Length; i++)
                    padded[i] = (byte)' ';
                patched++;
                return "\"" + m.Groups[1].Value + ":1\":\"" + m.Groups[2].Value + "\",\"" + m.Groups[1].Value + ":2\":\""
                    + Latin1.GetString(padded) + "\"";
            });
            var newSlice = Latin1.GetBytes(next);
            if (newSlice.Length != slice.Length)
                throw new InvalidOperationException($"loc JSON 长度变化 {slice.Length} -> {newSlice.Length}");
            Buffer.BlockCopy(newSlice, 0, data, jsonAt, newSlice.Length);
            blobs++;
            pos = end + 1;
        }
        File.WriteAllBytes(path, data);
        log($"已写入 loc JSON：{patched} 格，{blobs} 张表（跳过过长 {skipped}）");
    }

    static byte[] ReplaceNamedBlob(byte[] data, byte[] assetName, byte[][] markers, string newText)
    {
        var nameAt = IndexOf(data, assetName, 0);
        if (nameAt < 0)
            throw new FileNotFoundException("找不到资源: " + Encoding.ASCII.GetString(assetName));
        var start = -1;
        var widerLen = Math.Min(256, data.Length - nameAt);
        foreach (var marker in markers)
        {
            var rel = IndexOf(data, marker, nameAt, nameAt + widerLen);
            if (rel >= 0)
            {
                start = rel;
                break;
            }
        }
        if (start < 0)
            throw new FileNotFoundException("找不到资源正文: " + Encoding.ASCII.GetString(assetName));
        var end = IndexOf(data, new byte[] { 0 }, start);
        if (end < 0)
            throw new InvalidOperationException("资源正文未终止");
        var originalLen = end - start;
        var payload = newText.Contains("\r\n", StringComparison.Ordinal) ? newText : newText.Replace("\n", "\r\n");
        var raw = Encoding.UTF8.GetBytes(payload);
        if (raw.Length > originalLen)
            throw new InvalidOperationException(
                $"{Encoding.ASCII.GetString(assetName)} 中文 {raw.Length} 字节，原文 {originalLen}，无法拉长 TextAsset");
        var padded = new byte[originalLen];
        Buffer.BlockCopy(raw, 0, padded, 0, raw.Length);
        for (var i = raw.Length; i < originalLen; i++)
            padded[i] = (byte)' ';
        var result = new byte[data.Length];
        Buffer.BlockCopy(data, 0, result, 0, start);
        Buffer.BlockCopy(padded, 0, result, start, padded.Length);
        Buffer.BlockCopy(data, end, result, start + padded.Length, data.Length - end);
        return result;
    }

    static string JsonEscape(string value) =>
        value.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "\\r");

    static int IndexOf(byte[] data, byte[] needle, int start, int endExclusive = -1)
    {
        if (endExclusive < 0)
            endExclusive = data.Length;
        var last = endExclusive - needle.Length;
        for (var i = start; i <= last; i++)
        {
            var ok = true;
            for (var j = 0; j < needle.Length; j++)
            {
                if (data[i + j] != needle[j])
                {
                    ok = false;
                    break;
                }
            }
            if (ok)
                return i;
        }
        return -1;
    }

    static int LastIndexOf(byte[] data, byte value, int start, int endExclusive)
    {
        for (var i = endExclusive - 1; i >= start; i--)
        {
            if (data[i] == value)
                return i;
        }
        return -1;
    }
}
