# Fonts

`enable` subsets a CJK TTF into `StreamingAssets/zh-cn/cjk-overlay.ttf`. A BepInEx plugin loads it as a TextMeshPro fallback at runtime.

Do not splice fonts into `resources.assets` or flip TMP atlas modes — that crashed Unity with *Position out of bounds*.

## Source (do not commit binaries)

1. Any `.ttf` / `.otf` you drop in this folder (prefer [Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC), SIL OFL)
2. Windows `msyh.ttc` (Microsoft YaHei)
3. Windows `simhei.ttf`

Generated `NotoSansSC-overlay.ttf` is gitignored. Microsoft fonts must not be uploaded to GitHub.
