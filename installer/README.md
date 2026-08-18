# Windows 安装器

玩家用的一键安装 / 恢复程序。源码在本目录，**编译出的 exe 不进 GitHub**（体积来自自包含 .NET 运行时）。

```powershell
# 仓库根目录
powershell -ExecutionPolicy Bypass -File scripts\download-tools.ps1
powershell -ExecutionPolicy Bypass -File scripts\publish-installer.ps1
# 然后运行 dist\AscensionZhCn-Setup.exe
```

需要已生成的 `loc/zh-Hans/overlay.tsv` 和插件 DLL（`publish-installer.ps1` 会从 `plugin/bin/Release` 拷贝）。
