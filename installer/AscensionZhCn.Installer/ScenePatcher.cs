using System.Text;

namespace AscensionZhCn.Installer;

internal static class ScenePatcher
{
    static readonly (string En, string Zh)[] Replacements =
    {
        ("Offline", "离线 "),
        ("Online", "在线"),
        ("In-App Store", "商店      "),
        ("App Store", "商店   "),
        ("Stone Blade Newsletter Sign-Up", "订阅 Stone Blade 通讯     "),
        ("Stone Blade Newsletter Sign-up", "订阅 Stone Blade 通讯     "),
        ("Sign up to get the latest information and special deals direct to you.", "订阅即可获取最新资讯与优惠，直接发到你的邮箱。 "),
        ("Cancel", "取消"),
        ("Key Bindings", "按键绑定"),
    };

    public static int Apply(string gameRoot, string backupDir, Action<string> log)
    {
        Directory.CreateDirectory(backupDir);
        var live = Path.Combine(gameRoot, "AscensionGame_Data", "level1");
        var backup = Path.Combine(backupDir, "level1");
        if (!File.Exists(backup))
        {
            File.Copy(live, backup);
            log("已备份 level1");
        }
        File.Copy(backup, live, overwrite: true);
        var data = File.ReadAllBytes(live);
        var patched = 0;
        foreach (var (en, zh) in Replacements)
        {
            var oldBytes = Prefixed(en);
            var newBytes = Prefixed(zh);
            if (oldBytes.Length != newBytes.Length)
            {
                log($"跳过场景 {en}：字节长度不一致");
                continue;
            }
            var count = ReplaceAll(ref data, oldBytes, newBytes);
            if (count == 0)
                log("场景未找到: " + en);
            else
            {
                patched += count;
                log($"场景 {en} -> 中文（{count} 处）");
            }
        }
        File.WriteAllBytes(live, data);
        log($"已写入 level1（{patched} 处）");
        return patched;
    }

    public static void Restore(string gameRoot, string backupDir, Action<string> log)
    {
        var src = Path.Combine(backupDir, "level1");
        if (!File.Exists(src))
        {
            log("没有 level1 备份，跳过");
            return;
        }
        File.Copy(src, Path.Combine(gameRoot, "AscensionGame_Data", "level1"), overwrite: true);
        log("已还原 level1");
    }

    static byte[] Prefixed(string text)
    {
        var raw = Encoding.UTF8.GetBytes(text);
        var buf = new byte[4 + raw.Length];
        System.Buffers.Binary.BinaryPrimitives.WriteInt32LittleEndian(buf, raw.Length);
        raw.CopyTo(buf, 4);
        return buf;
    }

    static int ReplaceAll(ref byte[] data, byte[] oldBytes, byte[] newBytes)
    {
        var count = 0;
        var positions = new List<int>();
        for (var i = 0; i <= data.Length - oldBytes.Length; i++)
        {
            var ok = true;
            for (var j = 0; j < oldBytes.Length; j++)
            {
                if (data[i + j] != oldBytes[j])
                {
                    ok = false;
                    break;
                }
            }
            if (ok)
            {
                positions.Add(i);
                i += oldBytes.Length - 1;
            }
        }
        if (positions.Count == 0)
            return 0;
        foreach (var pos in positions)
        {
            Buffer.BlockCopy(newBytes, 0, data, pos, newBytes.Length);
            count++;
        }
        return count;
    }
}
