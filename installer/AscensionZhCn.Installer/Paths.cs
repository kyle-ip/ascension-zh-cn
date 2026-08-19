using System.Text.Json;
using Microsoft.Win32;

namespace AscensionZhCn.Installer;

internal sealed class AppPaths
{
    public const string BepInExPackUrl = "https://gcdn.thunderstore.io/live/repository/packages/BepInEx-BepInExPack_IL2CPP-6.0.755.zip";
    public const string BepInExZipName = "BepInExPack_IL2CPP-6.0.755.zip";

    public string? RepoRoot { get; }
    public string PayloadDir { get; }
    public string StateDir { get; }
    public string BackupDir { get; }
    public string PatchJson { get; }
    public string ConfigJson { get; }

    AppPaths(string? repoRoot, string payloadDir, string stateDir)
    {
        RepoRoot = repoRoot;
        PayloadDir = payloadDir;
        StateDir = stateDir;
        BackupDir = Path.Combine(stateDir, "backups");
        PatchJson = repoRoot is null ? Path.Combine(stateDir, "patch.json") : Path.Combine(repoRoot, "patch.json");
        ConfigJson = repoRoot is null ? Path.Combine(stateDir, "config.json") : Path.Combine(repoRoot, "config.json");
    }

    public static AppPaths Discover()
    {
        var exeDir = AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var payloadBesideExe = Path.Combine(exeDir, "payload");
        var repo = FindRepoRoot(exeDir);
        if (repo != null)
        {
            var locPayload = Path.Combine(repo, "loc", "zh-Hans");
            var payload = Directory.Exists(payloadBesideExe) && File.Exists(Path.Combine(payloadBesideExe, "overlay.tsv"))
                ? payloadBesideExe
                : locPayload;
            return new AppPaths(repo, payload, Path.Combine(repo, "state"));
        }

        var cache = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ascension-zh-cn");
        Directory.CreateDirectory(cache);
        if (!Directory.Exists(payloadBesideExe))
            throw new DirectoryNotFoundException("找不到汉化数据（payload/overlay.tsv）。请从本仓库发布的 dist 目录运行安装器。");
        return new AppPaths(null, payloadBesideExe, cache);
    }

    static string? FindRepoRoot(string start)
    {
        var dir = new DirectoryInfo(start);
        for (var i = 0; i < 8 && dir != null; i++, dir = dir.Parent)
        {
            if (File.Exists(Path.Combine(dir.FullName, "patch.json"))
                && Directory.Exists(Path.Combine(dir.FullName, "loc", "zh-Hans")))
                return dir.FullName;
        }
        return null;
    }

    public string Require(string fileName)
    {
        var path = Path.Combine(PayloadDir, fileName);
        if (!File.Exists(path))
            throw new FileNotFoundException("汉化数据包缺少文件: " + fileName, path);
        return path;
    }

    public string? Optional(string fileName)
    {
        var path = Path.Combine(PayloadDir, fileName);
        return File.Exists(path) ? path : null;
    }
}

internal static class GameLocator
{
    public static bool LooksLikeGame(string? root)
    {
        if (string.IsNullOrWhiteSpace(root))
            return false;
        return File.Exists(Path.Combine(root, "AscensionGame.exe"))
            && Directory.Exists(Path.Combine(root, "AscensionGame_Data", "StreamingAssets", "Lua"));
    }

    public static string Detect(AppPaths paths, string? explicitRoot = null)
    {
        if (LooksLikeGame(explicitRoot))
            return Path.GetFullPath(explicitRoot!);

        var fromConfig = ReadGameRoot(paths.ConfigJson);
        if (LooksLikeGame(fromConfig))
            return Path.GetFullPath(fromConfig!);

        // Legacy: older builds stored gameRoot in patch.json
        var fromPatch = ReadGameRoot(paths.PatchJson);
        if (LooksLikeGame(fromPatch))
            return Path.GetFullPath(fromPatch!);

        if (paths.RepoRoot != null)
        {
            var parent = Directory.GetParent(paths.RepoRoot)?.FullName;
            if (LooksLikeGame(parent))
                return parent!;
        }

        foreach (var candidate in SteamInstalls())
        {
            if (LooksLikeGame(candidate))
                return candidate;
        }

        throw new DirectoryNotFoundException("找不到《创升纪元》安装目录。请在安装器里浏览选择 AscensionGame.exe 所在文件夹。");
    }

    static string? ReadGameRoot(string jsonPath)
    {
        try
        {
            if (!File.Exists(jsonPath))
                return null;
            using var doc = JsonDocument.Parse(File.ReadAllText(jsonPath));
            if (doc.RootElement.TryGetProperty("gameRoot", out var el))
                return el.GetString();
        }
        catch
        {
        }
        return null;
    }

    public static void WriteGameRoot(AppPaths paths, string gameRoot)
    {
        try
        {
            var json = JsonSerializer.Serialize(new Dictionary<string, object?>
            {
                ["gameRoot"] = gameRoot,
            }, new JsonSerializerOptions { WriteIndented = true });
            Directory.CreateDirectory(Path.GetDirectoryName(paths.ConfigJson)!);
            File.WriteAllText(paths.ConfigJson, json + "\n");
        }
        catch
        {
        }
    }

    public static void WriteEnabled(AppPaths paths, bool enabled)
    {
        try
        {
            var notes = "Runtime state for the installer / tools/patch.py. Game path lives in config.json.";
            if (File.Exists(paths.PatchJson))
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(paths.PatchJson));
                if (doc.RootElement.TryGetProperty("notes", out var n))
                    notes = n.GetString() ?? notes;
            }
            var json = JsonSerializer.Serialize(new Dictionary<string, object?>
            {
                ["name"] = "ascension-zh-cn",
                ["enabled"] = enabled,
                ["locale"] = "zh-Hans",
                ["notes"] = notes,
            }, new JsonSerializerOptions { WriteIndented = true });
            Directory.CreateDirectory(Path.GetDirectoryName(paths.PatchJson)!);
            File.WriteAllText(paths.PatchJson, json + "\n");
        }
        catch
        {
        }
    }

    static IEnumerable<string> SteamInstalls()
    {
        var steamRoots = new List<string>();
        foreach (var hive in new[] { Registry.CurrentUser, Registry.LocalMachine })
        {
            try
            {
                using var key = hive.OpenSubKey(@"Software\Valve\Steam")
                    ?? hive.OpenSubKey(@"SOFTWARE\WOW6432Node\Valve\Steam");
                var path = key?.GetValue("SteamPath") as string ?? key?.GetValue("InstallPath") as string;
                if (!string.IsNullOrWhiteSpace(path))
                    steamRoots.Add(path.Replace('/', '\\'));
            }
            catch
            {
            }
        }

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var steam in steamRoots)
        {
            if (!seen.Add(steam))
                continue;
            yield return Path.Combine(steam, "steamapps", "common", "Ascension");
            var vdf = Path.Combine(steam, "steamapps", "libraryfolders.vdf");
            if (!File.Exists(vdf))
                continue;
            foreach (var lib in ParseLibraryFolders(File.ReadAllText(vdf)))
                yield return Path.Combine(lib, "steamapps", "common", "Ascension");
        }
    }

    static IEnumerable<string> ParseLibraryFolders(string vdf)
    {
        foreach (System.Text.RegularExpressions.Match m in
                 System.Text.RegularExpressions.Regex.Matches(vdf, "\"path\"\\s+\"([^\"]+)\""))
        {
            yield return m.Groups[1].Value.Replace(@"\\", @"\");
        }
    }
}
