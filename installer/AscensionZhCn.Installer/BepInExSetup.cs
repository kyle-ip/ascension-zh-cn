using System.IO.Compression;
using System.Net.Http;
using System.Text;

namespace AscensionZhCn.Installer;

internal static class BepInExSetup
{
    static readonly string[] MarkerFiles = { "winhttp.dll", "doorstop_config.ini", ".doorstop_version" };

    public static bool Installed(string gameRoot) =>
        File.Exists(Path.Combine(gameRoot, "BepInEx", "core", "BepInEx.Unity.IL2CPP.dll"))
        && File.Exists(Path.Combine(gameRoot, "winhttp.dll"));

    public static async Task InstallAsync(string gameRoot, string stateDir, Action<string> log, CancellationToken ct)
    {
        if (Installed(gameRoot))
        {
            QuietConsole(gameRoot, log);
            log("BepInEx 已安装");
            return;
        }

        Directory.CreateDirectory(stateDir);
        var zipPath = Path.Combine(stateDir, AppPaths.BepInExZipName);
        if (!File.Exists(zipPath) || new FileInfo(zipPath).Length < 1_000_000)
        {
            log("正在下载 BepInEx 6 IL2CPP…");
            await DownloadAsync(AppPaths.BepInExPackUrl, zipPath, log, ct);
        }

        log("正在解压 BepInEx 到游戏目录…");
        using (var zf = ZipFile.OpenRead(zipPath))
        {
            foreach (var entry in zf.Entries)
            {
                var name = entry.FullName.Replace('\\', '/');
                if (!name.StartsWith("BepInExPack/", StringComparison.Ordinal) || name.EndsWith('/'))
                    continue;
                var rel = name["BepInExPack/".Length..];
                if (rel.Length == 0)
                    continue;
                var dest = Path.Combine(gameRoot, rel.Replace('/', Path.DirectorySeparatorChar));
                if (string.IsNullOrEmpty(entry.Name))
                {
                    Directory.CreateDirectory(dest);
                    continue;
                }
                Directory.CreateDirectory(Path.GetDirectoryName(dest)!);
                entry.ExtractToFile(dest, overwrite: true);
            }
        }
        QuietConsole(gameRoot, log);
        log("BepInEx 已安装（第一次进游戏会生成互操作文件，可能要一两分钟）");
    }

    public static void Uninstall(string gameRoot, Action<string> log)
    {
        foreach (var name in MarkerFiles)
        {
            var path = Path.Combine(gameRoot, name);
            if (File.Exists(path))
                File.Delete(path);
        }
        foreach (var folder in new[] { "BepInEx", "dotnet" })
        {
            var path = Path.Combine(gameRoot, folder);
            if (Directory.Exists(path))
                Directory.Delete(path, recursive: true);
        }
        var changelog = Path.Combine(gameRoot, "changelog.txt");
        if (File.Exists(changelog))
        {
            var head = File.ReadAllText(changelog, Encoding.UTF8);
            if (head.Contains("BepInEx", StringComparison.Ordinal))
                File.Delete(changelog);
        }
        log("已移除 BepInEx");
    }

    public static void CopyPlugin(string gameRoot, string? pluginDll, string overlayTsv, Action<string> log)
    {
        var plugins = Path.Combine(gameRoot, "BepInEx", "plugins");
        Directory.CreateDirectory(plugins);
        if (!string.IsNullOrEmpty(pluginDll) && File.Exists(pluginDll))
        {
            File.Copy(pluginDll, Path.Combine(plugins, "AscensionZhCn.dll"), overwrite: true);
            log("已复制插件 DLL");
        }
        else
            log("警告：没有 AscensionZhCn.dll。中文界面可能缺字或无法替换 loc 键。请先运行 scripts/publish-installer.ps1。");

        var zh = Path.Combine(gameRoot, "AscensionGame_Data", "StreamingAssets", "zh-cn");
        Directory.CreateDirectory(zh);
        File.Copy(overlayTsv, Path.Combine(zh, "overlay.tsv"), overwrite: true);
        File.Copy(overlayTsv, Path.Combine(plugins, "overlay.tsv"), overwrite: true);
        log("已复制 overlay.tsv");
    }

    public static void QuietConsole(string gameRoot, Action<string> log)
    {
        var cfg = Path.Combine(gameRoot, "BepInEx", "config", "BepInEx.cfg");
        if (File.Exists(cfg))
        {
            var text = File.ReadAllText(cfg);
            var updated = SetIni(text, "[Logging.Console]", "Enabled", "false");
            updated = SetIni(updated, "[Logging.Disk]", "Enabled", "true");
            if (updated != text)
            {
                File.WriteAllText(cfg, updated);
                log("已关闭 BepInEx 控制台窗口");
            }
        }
        var door = Path.Combine(gameRoot, "doorstop_config.ini");
        if (File.Exists(door))
        {
            var text = File.ReadAllText(door);
            var updated = text.Replace("ignore_disable_switch = false", "ignore_disable_switch = true");
            if (updated != text)
            {
                File.WriteAllText(door, updated);
                log("已设置 Doorstop 忽略 Steam 的 DOORSTOP_DISABLE");
            }
        }
    }

    static string SetIni(string text, string section, string key, string value)
    {
        var idx = text.IndexOf(section, StringComparison.Ordinal);
        if (idx < 0)
            return text;
        var head = text[..idx];
        var rest = text[(idx + section.Length)..];
        var nxt = rest.IndexOf("\n[", StringComparison.Ordinal);
        var body = nxt < 0 ? rest : rest[..nxt];
        var tail = nxt < 0 ? "" : rest[nxt..];
        var lines = new List<string>();
        var replaced = false;
        using var reader = new StringReader(body);
        while (reader.ReadLine() is { } line)
        {
            var stripped = line.TrimStart();
            if (stripped.StartsWith(key + " =", StringComparison.Ordinal) || stripped.StartsWith(key + "=", StringComparison.Ordinal))
            {
                lines.Add($"{key} = {value}");
                replaced = true;
            }
            else
                lines.Add(line);
        }
        if (!replaced)
            lines.Add($"{key} = {value}");
        var nl = text.Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n";
        return head + section + nl + string.Join(nl, lines) + (tail.Length == 0 ? "" : nl + tail.TrimStart('\r', '\n'));
    }

    static async Task DownloadAsync(string url, string dest, Action<string> log, CancellationToken ct)
    {
        using var http = new HttpClient();
        http.Timeout = TimeSpan.FromMinutes(3);
        http.DefaultRequestHeaders.UserAgent.ParseAdd("ascension-zh-cn-installer");
        using var resp = await http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, ct);
        resp.EnsureSuccessStatusCode();
        var tmp = dest + ".partial";
        await using (var fs = File.Create(tmp))
            await resp.Content.CopyToAsync(fs, ct);
        File.Move(tmp, dest, overwrite: true);
        log($"已下载 {Path.GetFileName(dest)}（{new FileInfo(dest).Length / 1024 / 1024} MB）");
    }
}
