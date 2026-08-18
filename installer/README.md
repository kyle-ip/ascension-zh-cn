# Installer

Windows GUI that installs or removes the overlay.

```powershell
.\scripts\publish-installer.ps1
```

Writes `dist/AscensionZhCn-Setup.exe`. Needs `loc/zh-Hans/overlay.tsv` and `payload/AscensionZhCn.dll` (copied from the plugin build when BepInEx interop is present).
