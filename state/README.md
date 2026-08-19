Local-only cache. **Do not commit.**

| Path | What |
| --- | --- |
| `backups/` | English Lua, `resources.assets`, `level1` copies from the game install |
| `dotnet-sdk/` | Portable .NET SDK (`.\install.ps1`) |
| `*.zip` | BepInEx pack and SDK zips |
| `install.ok` | Marker written by `.\install.ps1` |

Game path: repo-root `config.json` (`gameRoot`). Use `.\install.ps1` to fetch vendor tools. Game backups are created by `.\enable.ps1` (or the shipped installer).
