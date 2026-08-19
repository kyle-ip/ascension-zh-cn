namespace AscensionZhCn.Installer;

internal sealed class MainForm : Form
{
    readonly TextBox _path = new();
    readonly TextBox _log = new();
    readonly Button _install = new();
    readonly Button _restore = new();
    readonly Button _browse = new();
    readonly Label _status = new();
    bool _busy;

    public MainForm()
    {
        Text = "《创升纪元》简体中文补丁";
        Font = new Font("Microsoft YaHei UI", 10F);
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(640, 480);
        Size = new Size(720, 560);
        BackColor = Color.FromArgb(248, 246, 241);
        ForeColor = Color.FromArgb(32, 32, 32);

        var title = new Label
        {
            Text = "一键安装 / 恢复英文",
            AutoSize = true,
            Font = new Font("Microsoft YaHei UI", 16F, FontStyle.Bold),
            Location = new Point(20, 18),
        };
        var hint = new Label
        {
            Text = "请先退出游戏。本程序只改本机 Steam 安装，不上传任何文件。",
            AutoSize = true,
            ForeColor = Color.FromArgb(90, 90, 90),
            Location = new Point(22, 56),
        };

        var pathLabel = new Label { Text = "游戏目录", AutoSize = true, Location = new Point(22, 92) };
        _path.Location = new Point(22, 116);
        _path.Width = 540;
        _path.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;

        _browse.Text = "浏览…";
        _browse.Location = new Point(572, 114);
        _browse.Width = 110;
        _browse.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        _browse.Click += (_, _) => Browse();

        _install.Text = "安装汉化";
        _install.Location = new Point(22, 160);
        _install.Size = new Size(160, 40);
        _install.Click += async (_, _) => await RunSafe(true);

        _restore.Text = "恢复英文";
        _restore.Location = new Point(196, 160);
        _restore.Size = new Size(160, 40);
        _restore.Click += async (_, _) => await RunSafe(false);

        _status.AutoSize = true;
        _status.Location = new Point(372, 170);
        _status.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;

        _log.Multiline = true;
        _log.ReadOnly = true;
        _log.ScrollBars = ScrollBars.Vertical;
        _log.Location = new Point(22, 216);
        _log.Size = new Size(660, 280);
        _log.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
        _log.BackColor = Color.White;
        _log.Font = new Font("Consolas", 9.5F);

        Controls.AddRange(new Control[] { title, hint, pathLabel, _path, _browse, _install, _restore, _status, _log });
        Load += (_, _) => InitPath();
    }

    void InitPath()
    {
        try
        {
            var service = PatchService.Create(AppendLog, null);
            _path.Text = service.GameRoot;
            _status.Text = service.LooksInstalled() ? "状态：已安装中文" : "状态：英文（未安装或已恢复）";
            AppendLog(service.DescribeStatus());
        }
        catch (Exception ex)
        {
            _status.Text = "状态：未找到游戏，请浏览选择";
            AppendLog(ex.Message);
        }
    }

    void Browse()
    {
        using var dlg = new FolderBrowserDialog
        {
            Description = "选择包含 AscensionGame.exe 的文件夹",
            UseDescriptionForTitle = true,
        };
        if (!string.IsNullOrWhiteSpace(_path.Text) && Directory.Exists(_path.Text))
            dlg.SelectedPath = _path.Text;
        if (dlg.ShowDialog(this) != DialogResult.OK)
            return;
        if (!GameLocator.LooksLikeGame(dlg.SelectedPath))
        {
            MessageBox.Show(this, "这个文件夹里没有 AscensionGame.exe。", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        _path.Text = dlg.SelectedPath;
        try
        {
            GameLocator.WriteGameRoot(AppPaths.Discover(), dlg.SelectedPath);
        }
        catch
        {
        }
    }

    async Task RunSafe(bool install)
    {
        if (_busy)
            return;
        if (!GameLocator.LooksLikeGame(_path.Text))
        {
            MessageBox.Show(this, "请先选择正确的游戏目录。", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        _busy = true;
        _install.Enabled = false;
        _restore.Enabled = false;
        try
        {
            var paths = AppPaths.Discover();
            GameLocator.WriteGameRoot(paths, _path.Text);
            var service = PatchService.Create(AppendLog, _path.Text);
            if (install)
                await service.InstallAsync();
            else
                await Task.Run(() => service.Restore());
            _status.Text = install ? "状态：已安装中文" : "状态：已恢复英文";
        }
        catch (UnauthorizedAccessException)
        {
            var msg = "没有写入游戏目录的权限。请关闭游戏后，右键本程序「以管理员身份运行」。";
            AppendLog(msg);
            MessageBox.Show(this, msg, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        catch (Exception ex)
        {
            AppendLog(ex.Message);
            MessageBox.Show(this, ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            _busy = false;
            _install.Enabled = true;
            _restore.Enabled = true;
        }
    }

    void AppendLog(string line)
    {
        if (IsDisposed)
            return;
        if (InvokeRequired)
        {
            BeginInvoke(() => AppendLog(line));
            return;
        }
        _log.AppendText($"[{DateTime.Now:HH:mm:ss}] {line}{Environment.NewLine}");
    }
}
