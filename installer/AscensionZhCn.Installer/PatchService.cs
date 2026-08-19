using System.Diagnostics;

namespace AscensionZhCn.Installer;

internal sealed class PatchService
{
    readonly AppPaths _paths;
    readonly Action<string> _log;

    public string GameRoot { get; }
    public AppPaths Paths => _paths;

    PatchService(AppPaths paths, string gameRoot, Action<string> log)
    {
        _paths = paths;
        GameRoot = gameRoot;
        _log = log;
    }

    public static PatchService Create(Action<string> log, string? gameRoot = null)
    {
        var paths = AppPaths.Discover();
        var game = GameLocator.Detect(paths, gameRoot);
        return new PatchService(paths, game, log);
    }

    public string DescribeStatus()
    {
        var overlay = File.Exists(Path.Combine(GameRoot, "AscensionGame_Data", "StreamingAssets", "zh-cn", "overlay.tsv"));
        var plugin = File.Exists(Path.Combine(GameRoot, "BepInEx", "plugins", "AscensionZhCn.dll"));
        var backup = Directory.Exists(Path.Combine(_paths.BackupDir, "Lua"));
        return $"游戏: {GameRoot}\nBepInEx: {(BepInExSetup.Installed(GameRoot) ? "已安装" : "未安装")}\n插件: {(plugin ? "有" : "无")}\noverlay: {(overlay ? "有" : "无")}\n备份: {(backup ? "有" : "无")}";
    }

    public bool LooksInstalled() =>
        File.Exists(Path.Combine(GameRoot, "AscensionGame_Data", "StreamingAssets", "zh-cn", "overlay.tsv"))
        && File.Exists(Path.Combine(GameRoot, "BepInEx", "plugins", "AscensionZhCn.dll"));

    public async Task InstallAsync(CancellationToken ct = default)
    {
        EnsureGameClosed();
        _log("游戏目录: " + GameRoot);
        Directory.CreateDirectory(_paths.BackupDir);

        var luaDir = Path.Combine(GameRoot, "AscensionGame_Data", "StreamingAssets", "Lua");
        LuaPatcher.PatchDirectory(
            luaDir,
            Path.Combine(_paths.BackupDir, "Lua"),
            _paths.Require("lua_cards.csv"),
            _paths.Optional("combat_log.csv"),
            _log);

        AssetPatcher.BackupIfNeeded(GameRoot, _paths.BackupDir, _log);
        File.Copy(
            Path.Combine(_paths.BackupDir, "resources.assets"),
            Path.Combine(GameRoot, "AscensionGame_Data", "resources.assets"),
            overwrite: true);
        var packed = _paths.Optional("cards_packed.csv") ?? _paths.Optional("cards.csv");
        if (packed != null)
        {
            try
            {
                AssetPatcher.ApplyTextAsset(
                    GameRoot,
                    _paths.BackupDir,
                    "cards_EN",
                    packed,
                    new[] { "LABEL_REWARD"u8.ToArray() },
                    _log);
            }
            catch (Exception ex)
            {
                _log("cards_EN 跳过: " + ex.Message);
            }
        }

        var loc = new Dictionary<string, string>(StringComparer.Ordinal);
        var cardsCsv = _paths.Optional("cards.csv");
        if (cardsCsv != null)
        {
            foreach (var row in CsvUtil.ReadRows(cardsCsv))
            {
                if (row.Length >= 2 && row[0].Length > 0 && row[0] is not "key" and not "en")
                    loc[row[0]] = row[1];
            }
        }
        var uiCsv = _paths.Optional("ui.csv");
        if (uiCsv != null)
        {
            foreach (var pair in CsvUtil.TwoCol(uiCsv, "key", "zh"))
            {
                if (pair.Key.StartsWith("Key_", StringComparison.Ordinal) || pair.Key.StartsWith("IAP_", StringComparison.Ordinal))
                    loc[pair.Key] = pair.Value;
            }
        }
        if (loc.Count > 0)
        {
            try
            {
                AssetPatcher.ApplyLocJson(GameRoot, loc, _log);
            }
            catch (Exception ex)
            {
                _log("loc JSON 跳过: " + ex.Message);
            }
        }

        ScenePatcher.Apply(GameRoot, _paths.BackupDir, _log);

        await BepInExSetup.InstallAsync(GameRoot, _paths.StateDir, _log, ct);
        var plugin = _paths.Optional("AscensionZhCn.dll");
        if (plugin is null && _paths.RepoRoot != null)
        {
            var built = Path.Combine(_paths.RepoRoot, "plugin", "AscensionZhCn", "bin", "Release", "AscensionZhCn.dll");
            if (File.Exists(built))
                plugin = built;
        }
        BepInExSetup.CopyPlugin(GameRoot, plugin, _paths.Require("overlay.tsv"), _log);
        GameLocator.WriteEnabled(_paths, true);
        _log("安装完成。请从 Steam 启动游戏。");
        _log("若第一次进游戏只有英文，完全退出后再开一次。");
    }

    public void Restore()
    {
        EnsureGameClosed();
        _log("游戏目录: " + GameRoot);
        LuaPatcher.RestoreDirectory(
            Path.Combine(GameRoot, "AscensionGame_Data", "StreamingAssets", "Lua"),
            Path.Combine(_paths.BackupDir, "Lua"));
        _log("已还原 Lua");
        AssetPatcher.Restore(GameRoot, _paths.BackupDir, _log);
        ScenePatcher.Restore(GameRoot, _paths.BackupDir, _log);

        var zh = Path.Combine(GameRoot, "AscensionGame_Data", "StreamingAssets", "zh-cn");
        if (Directory.Exists(zh))
        {
            foreach (var name in new[] { "overlay.tsv", "plugin.log", "cjk-overlay.ttf", "untranslated.tsv", "AscensionZhCn.dll" })
            {
                var file = Path.Combine(zh, name);
                if (File.Exists(file))
                    File.Delete(file);
            }
            if (Directory.GetFileSystemEntries(zh).Length == 0)
                Directory.Delete(zh);
        }
        try
        {
            BepInExSetup.Uninstall(GameRoot, _log);
        }
        catch (Exception ex)
        {
            _log("卸载 BepInEx 跳过: " + ex.Message);
        }
        GameLocator.WriteEnabled(_paths, false);
        _log("已恢复英文。");
    }

    public void Install() => InstallAsync().GetAwaiter().GetResult();

    void EnsureGameClosed()
    {
        var procs = Process.GetProcessesByName("AscensionGame");
        if (procs.Length == 0)
            return;
        foreach (var p in procs)
            p.Dispose();
        throw new InvalidOperationException("请先完全退出游戏（任务管理器里不要有 AscensionGame.exe），再安装或恢复。");
    }
}
