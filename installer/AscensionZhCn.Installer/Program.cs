namespace AscensionZhCn.Installer;

internal static class Program
{
    [STAThread]
    static int Main(string[] args)
    {
        Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        if (args.Length > 0)
            return Cli.Run(args);

        Application.Run(new MainForm());
        return 0;
    }
}

internal static class Cli
{
    public static int Run(string[] args)
    {
        var cmd = args[0].Trim().ToLowerInvariant();
        var log = new Action<string>(line => Console.WriteLine(line));
        try
        {
            var service = PatchService.Create(log);
            switch (cmd)
            {
                case "install":
                case "enable":
                    service.Install();
                    return 0;
                case "restore":
                case "disable":
                    service.Restore();
                    return 0;
                case "status":
                    log(service.DescribeStatus());
                    return 0;
                default:
                    Console.Error.WriteLine("Usage: AscensionZhCn-Setup.exe [install|restore|status]");
                    return 2;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }
}
