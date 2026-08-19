using System.Drawing.Drawing2D;

namespace AscensionZhCn.Installer;

/// <summary>
/// Modern flat WinForms UI for the Ascension Chinese patch installer.
/// Design tokens (Tailwind-ish):
///   Primary:   #6366F1 (Indigo-500)  — install button, focus rings, accent
///   Primary-H: #4F46E5 (Indigo-600)  — hover
///   Secondary: #0F172A (Slate-900)   — headings
///   Muted:     #64748B (Slate-500)   — secondary text
///   Border:    #E2E8F0 (Slate-200)   — card borders
///   Surface:   #FFFFFF               — card background
///   Bg:        #F8FAFC (Slate-50)    — window background
///   Success:   #10B981 (Emerald-500) — installed status dot
///   Neutral:   #64748B (Slate-500)   — english status dot
/// </summary>
internal sealed class MainForm : Form
{
    // ── Palette ────────────────────────────────────────────────────────────
    static readonly Color C_Bg          = Color.FromArgb(0xF8, 0xFA, 0xFC);
    static readonly Color C_Surface     = Color.FromArgb(0xFF, 0xFF, 0xFF);
    static readonly Color C_Border      = Color.FromArgb(0xE2, 0xE8, 0xF0);
    static readonly Color C_Primary     = Color.FromArgb(0x63, 0x66, 0xF1);
    static readonly Color C_PrimaryHov  = Color.FromArgb(0x4F, 0x46, 0xE5);
    static readonly Color C_PrimaryPre  = Color.FromArgb(0x43, 0x38, 0xCA);
    static readonly Color C_PrimaryTxt  = Color.White;
    static readonly Color C_Danger      = Color.FromArgb(0xEF, 0x44, 0x44);
    static readonly Color C_DangerHov   = Color.FromArgb(0xDC, 0x26, 0x26);
    static readonly Color C_DangerPre   = Color.FromArgb(0xB9, 0x1C, 0x1C);
    static readonly Color C_Text        = Color.FromArgb(0x0F, 0x17, 0x2A);
    static readonly Color C_TextMuted   = Color.FromArgb(0x64, 0x74, 0x8B);
    static readonly Color C_Success     = Color.FromArgb(0x10, 0xB9, 0x81);
    static readonly Color C_Warn        = Color.FromArgb(0xF5, 0x9E, 0x0B);
    static readonly Color C_TermBg      = Color.FromArgb(0x0F, 0x17, 0x2A);
    static readonly Color C_TermFg      = Color.FromArgb(0xE2, 0xE8, 0xF0);
    static readonly Color C_TermAccent  = Color.FromArgb(0xA5, 0xB4, 0xFC);

    readonly TextBox _path = new();
    readonly RichTextBox _log = new();
    readonly Button _install = new();
    readonly Button _restore = new();
    readonly Button _browse  = new();
    readonly Panel  _statusDot = new();
    readonly Label  _statusLbl = new();
    bool _busy;

    public MainForm()
    {
        Text = "Ascension 简体中文补丁";
        Font = new Font("Microsoft YaHei UI", 10F);
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(720, 600);
        Size = new Size(820, 640);
        BackColor = C_Bg;
        ForeColor = C_Text;
        DoubleBuffered = true;
        AutoScaleMode = AutoScaleMode.Dpi;

        BuildLayout();
        Load += (_, _) => InitPath();
    }

    // ════════════════════════════════════════════════════════════════════════
    // LAYOUT
    // ════════════════════════════════════════════════════════════════════════
    void BuildLayout()
    {
        const int PAD    = 24;
        const int GAP    = 16;
        int w = ClientSize.Width;

        // ── 1. Header (title + subtitle, no icon) ─────────────────────────────
        var headerPanel = new Panel
        {
            Dock = DockStyle.Top,
            Height = 140,
            BackColor = C_Bg,
        };

        var titleLbl = new Label
        {
            Text = "Ascension 简体中文补丁",
            AutoSize = false,
            Size = new Size(820 - PAD * 2, 52),
            Font = new Font("Microsoft YaHei UI", 18F, FontStyle.Bold),
            ForeColor = C_Text,
            Location = new Point(PAD, 22),
            TextAlign = ContentAlignment.MiddleLeft,
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
        };
        var subLbl = new Label
        {
            Text = "一键安装 · 随时可恢复原版",
            AutoSize = false,
            Size = new Size(820 - PAD * 2, 32),
            Font = new Font("Microsoft YaHei UI", 10F),
            ForeColor = C_TextMuted,
            Location = new Point(PAD, 80),
            TextAlign = ContentAlignment.MiddleLeft,
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
        };
        headerPanel.Controls.AddRange(new Control[] { titleLbl, subLbl });
        Controls.Add(headerPanel);

        // ── 2. Game directory card ────────────────────────────────────────────
        var dirCard = MakeCard(PAD, headerPanel.Bottom + 4, w - PAD * 2, 148, "游戏目录");

        var pathContainer = new Panel
        {
            Location = new Point(20, 48),
            Size = new Size(dirCard.ClientSize.Width - 40, 48),
            BackColor = C_Bg,
        };
        // Do NOT set Region-clipping here; pathContainer uses plain rounded-rect
        // look via background color only, otherwise the browse button / input
        // bottom pixels get clipped by the arc.

        _path.BorderStyle = BorderStyle.None;
        _path.BackColor = C_Bg;
        _path.ForeColor = C_Text;
        _path.Font = new Font("Microsoft YaHei UI", 10F);
        _path.Location = new Point(14, 14);
        _path.Size = new Size(pathContainer.ClientSize.Width - 14 - 118 - 14, 24);
        _path.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        _path.PlaceholderText = "选择包含 AscensionGame.exe 的文件夹…";

        _browse.Text = "浏览";
        StyleTinted(_browse);
        _browse.Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold);
        _browse.Location = new Point(pathContainer.ClientSize.Width - 110 - 8, 8);
        _browse.Size = new Size(102, 32);
        _browse.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        _browse.Click += (_, _) => Browse();
        // Keep browse visually rounded via FlatAppearance; no Region clipping.

        pathContainer.Controls.AddRange(new Control[] { _path, _browse });
        AddToCard(dirCard, pathContainer);

        var warnLbl = new Label
        {
            Text = "⚠  安装 / 恢复前请先完全退出游戏，否则可能因为文件被占用而失败。",
            AutoSize = false,
            Size = new Size(dirCard.ClientSize.Width - 40, 28),
            ForeColor = C_Warn,
            Font = new Font("Microsoft YaHei UI", 9F),
            Location = new Point(20, 110),
            TextAlign = ContentAlignment.MiddleLeft,
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
        };
        AddToCard(dirCard, warnLbl);
        Controls.Add(dirCard);

        // ── 3. Action bar (buttons + status) ──────────────────────────────────
        var actionBar = new Panel
        {
            Location = new Point(PAD, dirCard.Bottom + GAP),
            Size = new Size(w - PAD * 2, 64),
            BackColor = Color.Transparent,
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
        };

        _install.Text = "安装";
        StylePrimary(_install);
        _install.Location = new Point(0, 12);
        _install.Size = new Size(156, 44);
        _install.Click += async (_, _) => await RunSafe(true);

        _restore.Text = "恢复";
        StyleSecondary(_restore);
        _restore.Location = new Point(156 + 12, 12);
        _restore.Size = new Size(156, 44);
        _restore.Click += async (_, _) => await RunSafe(false);

        // Status: dot + label (right-aligned; reserve enough width for the longest
        // text "状态：英文（未安装或已恢复）" + Chinese punctuation ~= 340px in 9.5pt).
        const int STATUS_BLOCK_W = 360;
        _statusDot.Size = new Size(10, 10);
        _statusDot.BackColor = C_TextMuted;
        _statusDot.Location = new Point(actionBar.ClientSize.Width - STATUS_BLOCK_W, 12 + 17);
        _statusDot.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        using (var gp = new GraphicsPath()) { gp.AddEllipse(0, 0, _statusDot.Width, _statusDot.Height); _statusDot.Region = new Region(gp); }

        _statusLbl.AutoSize = false;
        _statusLbl.AutoEllipsis = true;
        _statusLbl.Size = new Size(STATUS_BLOCK_W - 10 - 8 - 8, 24);
        _statusLbl.Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold);
        _statusLbl.ForeColor = C_TextMuted;
        _statusLbl.Text = "状态：检测中…";
        _statusLbl.Location = new Point(_statusDot.Right + 8, 12 + 10);
        _statusLbl.Anchor = AnchorStyles.Top | AnchorStyles.Right;

        actionBar.Controls.AddRange(new Control[] { _install, _restore, _statusDot, _statusLbl });
        Controls.Add(actionBar);

        // ── 4. Log area (light, no heading) ───────────────────────────────────
        var logCardTop = actionBar.Bottom + GAP;
        var logCardH = ClientSize.Height - logCardTop - PAD;
        var logCard = MakeCard(PAD, logCardTop, w - PAD * 2, logCardH, null);
        logCard.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;

        _log.BorderStyle = BorderStyle.None;
        _log.BackColor = Color.White;
        _log.ForeColor = C_Text;
        _log.Font = new Font("Cascadia Mono", 9.5F);
        _log.Location = new Point(20, 20);
        _log.Size = new Size(logCard.ClientSize.Width - 40, logCard.ClientSize.Height - 40);
        _log.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
        _log.ReadOnly = true;
        _log.WordWrap = false;
        _log.ScrollBars = RichTextBoxScrollBars.Vertical;

        AddToCard(logCard, _log);
        Controls.Add(logCard);
    }

    // ════════════════════════════════════════════════════════════════════════
    // UI HELPERS
    // ════════════════════════════════════════════════════════════════════════
    Panel MakeCard(int x, int y, int w, int h, string? heading)
    {
        var card = new Panel
        {
            Location = new Point(x, y),
            Size = new Size(w, h),
            BackColor = C_Border, // 1px "border" color; Padding=1 on inner shows this
        };
        // Only the OUTER card uses Region clipping (rounded shape).
        // border/inner do NOT clip so child labels at the bottom never get
        // their bottom rows shaved off by the 14px radius arc.
        RoundControl(card, 14);

        var inner = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = C_Surface,
            Margin = new Padding(0),
            Padding = new Padding(1), // leaves a 1px ring of card.BackColor (border)
        };
        card.Controls.Add(inner);

        if (heading != null)
        {
            var head = new Label
            {
                Text = heading,
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 10.5F, FontStyle.Bold),
                ForeColor = C_Text,
                Location = new Point(20, 18),
            };
            inner.Controls.Add(head);
        }

        card.Tag = inner;
        return card;
    }

    // MakeCard returns a card with a nested border+inner surface. Callers MUST
    // add children via this helper (instead of card.Controls.Add) so the Z-order
    // stays correct (border fills the card, and user content sits inside inner).
    static void AddToCard(Control card, Control child)
    {
        if (card.Tag is Control inner) inner.Controls.Add(child);
        else card.Controls.Add(child);
    }
    // Convenience: all card children (heading, panels) are added to inner.
    static Control InnerOf(Control card) => (card.Tag as Control) ?? card;

    // Tinted "primary" button (light indigo bg + dark indigo text).
    // Used for both 安装汉化 and 浏览 so the UI stays light.
    static readonly Color C_TintBg   = Color.FromArgb(0xEE, 0xF2, 0xFF); // Indigo-50
    static readonly Color C_TintFg   = Color.FromArgb(0x43, 0x38, 0xCA); // Indigo-700
    static readonly Color C_TintBd   = Color.FromArgb(0xC7, 0xD2, 0xFE); // Indigo-200
    static readonly Color C_TintHov  = Color.FromArgb(0xE0, 0xE7, 0xFF); // Indigo-100
    static readonly Color C_TintPre  = Color.FromArgb(0xC7, 0xD2, 0xFE); // Indigo-200
    static readonly Color C_TintDis  = Color.FromArgb(0xF5, 0xF3, 0xFF); // disabled

    void StylePrimary(Button b)
    {
        b.FlatStyle = FlatStyle.Flat;
        b.FlatAppearance.BorderColor = C_TintBd;
        b.FlatAppearance.BorderSize = 1;
        b.BackColor = C_TintBg;
        b.ForeColor = C_TintFg;
        b.Font = new Font("Microsoft YaHei UI", 10.5F, FontStyle.Bold);
        b.Cursor = Cursors.Hand;
        // No Region clipping — text inside the button must never be shaved.
        HoverColors(b, C_TintBg, C_TintHov, C_TintPre);
    }

    // Alias used for smaller tinted buttons inside the path panel (浏览).
    void StyleTinted(Button b) => StylePrimary(b);

    void StyleSecondary(Button b)
    {
        b.FlatStyle = FlatStyle.Flat;
        b.FlatAppearance.BorderColor = C_Border;
        b.FlatAppearance.BorderSize = 1;
        b.BackColor = Color.White;
        b.ForeColor = C_Text;
        b.Font = new Font("Microsoft YaHei UI", 10.5F, FontStyle.Regular);
        b.Cursor = Cursors.Hand;
        // No Region clipping.
        b.MouseEnter += (_, _) => { b.BackColor = C_Bg; };
        b.MouseLeave += (_, _) => { b.BackColor = Color.White; };
        b.MouseDown  += (_, _) => { b.BackColor = Color.FromArgb(0xE2, 0xE8, 0xF0); };
        b.MouseUp    += (_, _) => { b.BackColor = b.ClientRectangle.Contains(b.PointToClient(Cursor.Position)) ? C_Bg : Color.White; };
    }

    static void HoverColors(Button b, Color normal, Color hover, Color pressed)
    {
        b.BackColor = normal;
        b.MouseEnter += (_, _) => { b.BackColor = hover; };
        b.MouseLeave += (_, _) => { b.BackColor = normal; };
        b.MouseDown  += (_, _) => { b.BackColor = pressed; };
        b.MouseUp    += (_, _) => { b.BackColor = b.ClientRectangle.Contains(b.PointToClient(Cursor.Position)) ? hover : normal; };
    }

    static void RoundControl(Control c, int radius)
    {
        c.Resize += (_, _) => ApplyRegion(c, radius);
        ApplyRegion(c, radius);
    }

    static void ApplyRegion(Control c, int radius)
    {
        using var gp = new GraphicsPath();
        var r = new Rectangle(0, 0, c.Width, c.Height);
        int d = radius * 2;
        gp.AddArc(r.X, r.Y, d, d, 180, 90);
        gp.AddArc(r.Right - d, r.Y, d, d, 270, 90);
        gp.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
        gp.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
        gp.CloseFigure();
        try { c.Region?.Dispose(); } catch { }
        c.Region = new Region(gp);
    }

    // ════════════════════════════════════════════════════════════════════════
    // LOGIC (copied almost verbatim — only the MakeCard callers need patching)
    // ════════════════════════════════════════════════════════════════════════
    void InitPath()
    {
        try
        {
            var service = PatchService.Create(AppendLog, null);
            _path.Text = service.GameRoot;
            SetStatus(service.LooksInstalled());
            AppendLog(service.DescribeStatus());
        }
        catch (Exception ex)
        {
            _statusLbl.Text = "未找到游戏，请点击「浏览」选择";
            _statusLbl.ForeColor = C_Warn;
            _statusDot.BackColor = C_Warn;
            AppendLog(ex.Message);
        }
    }

    void SetStatus(bool installed)
    {
        if (installed)
        {
            _statusLbl.Text = "状态：已安装中文";
            _statusLbl.ForeColor = C_Success;
            _statusDot.BackColor = C_Success;
        }
        else
        {
            _statusLbl.Text = "状态：英文（未安装或已恢复）";
            _statusLbl.ForeColor = C_TextMuted;
            _statusDot.BackColor = C_TextMuted;
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
    }

    async Task RunSafe(bool install)
    {
        if (_busy) return;
        if (!GameLocator.LooksLikeGame(_path.Text))
        {
            MessageBox.Show(this, "请先选择正确的游戏目录。", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        _busy = true;
        _install.Enabled = false;
        _restore.Enabled = false;
        _install.BackColor = C_TintDis;
        _install.ForeColor = Color.FromArgb(0xA5, 0xB4, 0xFC); // Indigo-300 (disabled text)
        _restore.BackColor = C_Bg;
        _restore.ForeColor = C_TextMuted;
        try
        {
            var service = PatchService.Create(AppendLog, _path.Text);
            if (install) await service.InstallAsync();
            else await Task.Run(() => service.Restore());
            SetStatus(install);
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
            StylePrimary(_install);   // re-apply colors (BackColor overridden above)
            StyleSecondary(_restore); // re-apply
        }
    }

    void AppendLog(string line)
    {
        if (IsDisposed) return;
        if (InvokeRequired) { BeginInvoke(() => AppendLog(line)); return; }

        // Timestamp in a light accent color, message in neutral. Any message
        // containing OK/成功/已/写 -> green, WARN/失败/跳过/无法 -> amber/red.
        var ts = $"[{DateTime.Now:HH:mm:ss}] ";
        var msg = line + Environment.NewLine;
        _log.SelectionStart = _log.TextLength;
        _log.SelectionLength = 0;
        _log.SelectionColor = C_Primary; // Indigo timestamp on white background
        _log.SelectedText = ts;
        Color fg;
        var lower = (line ?? "").ToLowerInvariant();
        if (lower.Contains("失败") || lower.Contains("error") || lower.Contains("denied")) fg = Color.FromArgb(0xDC, 0x26, 0x26); // Red-600
        else if (lower.Contains("warn") || lower.Contains("跳过") || lower.Contains("无法") || lower.Contains("not")) fg = Color.FromArgb(0xD9, 0x77, 0x06); // Amber-600
        else if (lower.Contains("ok") || lower.Contains("已") || lower.Contains("成功") || lower.Contains("写入") || lower.Contains("复制")) fg = Color.FromArgb(0x05, 0x96, 0x69); // Emerald-600
        else fg = C_Text;
        _log.SelectionColor = fg;
        _log.SelectedText = msg;
        _log.SelectionStart = _log.TextLength;
        _log.ScrollToCaret();
    }
}
