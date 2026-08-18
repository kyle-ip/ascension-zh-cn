Local-only cache. **Do not commit.**

| Path | What |
| --- | --- |
| `backups/` | English Lua, `resources.assets`, `level1` copies from the Steam install |
| `dotnet-sdk/` | Portable .NET SDK (`scripts/download-tools.ps1`) |
| `*.zip` | BepInEx pack and SDK zips |

Use `scripts/download-tools.ps1` to fetch vendor tools. Game backups are created by the installer or `python tools/patch.py enable`.
