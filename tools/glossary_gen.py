"""Single Source of Truth generator for the zh-Hans glossary.

Reads ``glossary/zh-Hans.csv`` (authoritative, hand-editable), enriches it
with seed rows for any missing categories, then rebuilds four derived
artifacts that overlay.py / translate.py / ingest_untranslated.py consume:

1. ``GLOSSARY_EXACT`` dict (en -> zh) filtered by scope: ui + verb + label
   + zone + resource + faction + type + series + set + card + promo +
   button + login + shop + chapter.  Replaces ``overlay.extras`` hard-coded
   dictionary and eliminates the ``SKIP_EXACT`` blacklist problem (Confirm /
   Start / etc. were never inserted because they appeared in both).
2. ``EFFECT_WORDS`` + ``EFFECT_PHRASES`` lists in ``translate.py`` — they
   are still compiled to regular expressions at import time, but the raw
   pairs now come from the glossary so any hand edit is picked up on the
   next build.
3. ``ALLOW_SHORT`` set for ``overlay.py`` — every glossary entry with
   ``len(en) <= 4`` is automatically included, so short UI words (Bid,
   Pass, FAQ, SBT, or, XII, None...) stop being filtered out.
4. A coverage report ``glossary/zh-Hans.report.txt`` listing every scope
   and which rows are still ``status=draft`` so the translator knows the
   backlog.

Schema for glossary/zh-Hans.csv (all columns are plain text, UTF-8,
no BOM; comments starting with ``#`` in the ``en`` column are preserved):

    en      canonical English string / phrase / key
    zh      canonical Simplified Chinese translation (may be empty for
            status=draft rows)
    scope   one of:
                series   — product / box name
                world    — world lore proper noun (places, gods)
                faction  — card faction (Enlightened / Lifebound / ...)
                type     — card type (Hero / Construct / Monster / ...)
                resource — counters / indicators (Rune / Power / Honor / ...)
                zone     — play areas (Center Row / Void / ...)
                verb     — action words used on cards and in UI
                label    — card-face keywords and headers (Reward / Fate / ...)
                card     — names of always-available starting cards
                set      — expansion set name (CotG / RotF / DU / ...)
                promo    — promo / bundle name (Promo Pack #6 / ...)
                ui       — in-game screen / menu / tab names
                button   — generic button labels (Confirm / Start / Close ...)
                login    — Playdek / Asmodee account UI strings
                shop     — DLC store UI strings (purchaseable, coming soon,
                           bundle, pack, price)
                chapter  — rulebook chapter headings (Resources / What's
                           New / Features / Temples etc.)
                credits  — administration / credits role labels (optional)
                phrase   — long rulebook sentence fragments or full sentences
                           that are translated once and reused across runs
    source  provenance of the translation. One of:
                official-anshashen  — 《暗杀神》官方（方盒子365 / 维基）
                official-chuangsheng — 《创升纪元》官方（米宝海豚 / Steam）
                community            — 民间 / 360百科 / 论坛主流
                new                  — 本次新增，待社区确认；若有官方则覆盖
    status  new column, one of:
                approved   — 已校验（默认缺省时视为 approved 以兼容旧行）
                draft      — 未翻译 / 初翻待审
                conflict   — 与其他条目有冲突，暂不进入派生列表
    notes   free-form editor notes (optional).

Run:
    python tools/glossary_gen.py                 # rebuilds everything
    python tools/glossary_gen.py --dry-run       # only print report
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_PATH = ROOT / "glossary" / "zh-Hans.csv"
REPORT_PATH = ROOT / "glossary" / "zh-Hans.report.txt"

# ===== Seed rows — injected only if the same (en, scope) is not already =====
# in the glossary.  This keeps the glossary hand-editable: the script will
# never overwrite an existing row.
SEED_ROWS: list[dict[str, str]] = [
    # --------- button — system buttons (explicit zh, override SKIP_EXACT) --
    {"en": "Confirm",      "zh": "确认",    "scope": "button", "source": "community", "status": "approved", "notes": "P0 删除对局 / 通用弹窗确认按钮"},
    {"en": "Start",        "zh": "开始",    "scope": "button", "source": "community", "status": "approved", "notes": "P0 创建对局右下角开始按钮"},
    {"en": "Close",        "zh": "关闭",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "Done",         "zh": "完成",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "Yes",          "zh": "是",      "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "No",           "zh": "否",      "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "OK",           "zh": "好",      "scope": "button", "source": "community", "status": "approved", "notes": "与 ui.csv Key_OK 保持一致"},
    {"en": "Ok",           "zh": "好",      "scope": "button", "source": "community", "status": "approved", "notes": "小写 ok 变体"},
    {"en": "Undo",         "zh": "撤销",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "Commit",       "zh": "确认",    "scope": "button", "source": "community", "status": "approved", "notes": "与 Confirm 同译，用于设置提交"},
    {"en": "Dismiss",      "zh": "关闭",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "Delete",       "zh": "删除",    "scope": "button", "source": "community", "status": "approved", "notes": "删除对局 / 删除档案"},
    {"en": "Reveal",       "zh": "展示",    "scope": "button", "source": "community", "status": "approved", "notes": "卡牌操作"},
    {"en": "Discard",      "zh": "弃牌",    "scope": "button", "source": "official-anshashen", "status": "approved", "notes": ""},
    {"en": "Copy",         "zh": "复制",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "Use",          "zh": "使用",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "Give",         "zh": "给予",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "Target",       "zh": "指定",    "scope": "button", "source": "community", "status": "approved", "notes": "卡牌目标指定"},
    {"en": "Select",       "zh": "选择",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "Defend",       "zh": "防御",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "Play",         "zh": "打出",    "scope": "button", "source": "official-anshashen", "status": "approved", "notes": "卡牌打出；商店 Playdek 处不适用"},
    {"en": "Buy",          "zh": "获取",    "scope": "button", "source": "community", "status": "approved", "notes": "商店语境可理解为「购买」，但沿用卡牌术语以避免歧义"},
    {"en": "Bid",          "zh": "竞拍",    "scope": "button", "source": "community", "status": "approved", "notes": "谵妄命运竞拍"},
    {"en": "Pass",         "zh": "跳过",    "scope": "button", "source": "community", "status": "approved", "notes": "命运竞拍跳过"},
    {"en": "Chat",         "zh": "聊天",    "scope": "button", "source": "community", "status": "approved", "notes": "在线对局聊天"},
    {"en": "FAQ",          "zh": "常见问题","scope": "button", "source": "community", "status": "approved", "notes": "Playdek 登录页面 FAQ"},
    # --------- button — short / length <= 4 that bypass len filter --------
    {"en": "or",           "zh": "或",      "scope": "button", "source": "community", "status": "approved", "notes": "扩展选择面板 弑神编 or 十周年"},
    {"en": "None",         "zh": "无",      "scope": "button", "source": "community", "status": "approved", "notes": "无选中 / 无可选"},
    {"en": "All",          "zh": "全部",    "scope": "button", "source": "community", "status": "approved", "notes": ""},
    {"en": "SBT",          "zh": "SBT",     "scope": "button", "source": "official-chuangsheng", "status": "approved", "notes": "Stone Blade Tournament 官方缩写不译"},
    {"en": "XII",          "zh": "12",      "scope": "button", "source": "community", "status": "approved", "notes": "罗马数字 12，用于命运/名望数值显示"},
    {"en": "Odd",          "zh": "奇数",    "scope": "button", "source": "community", "status": "approved", "notes": "谵妄骰结算"},
    {"en": "Even",         "zh": "偶数",    "scope": "button", "source": "community", "status": "approved", "notes": "谵妄骰结算"},
    {"en": "Kor",          "zh": "科尔",    "scope": "world",  "source": "community", "status": "approved", "notes": "FLAVOR_KOR 人物名（救赎）"},
    {"en": "Name",         "zh": "姓名",    "scope": "login",  "source": "community", "status": "approved", "notes": "创建账号输入字段"},
    {"en": "Name:",        "zh": "姓名：",  "scope": "login",  "source": "community", "status": "approved", "notes": ""},
    # --------- login — Playdek/Asmodee account UI ------------------------
    {"en": "Sign Up",              "zh": "注册",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Forgot Login",         "zh": "忘记登录信息",        "scope": "login", "source": "community", "status": "approved", "notes": "登录页按钮"},
    {"en": "Email",                "zh": "邮箱",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Email:",               "zh": "邮箱：",              "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Username",             "zh": "用户名",              "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Username:",            "zh": "用户名：",            "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Password",             "zh": "密码",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Password:",            "zh": "密码：",              "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Verify PW",            "zh": "确认密码",            "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Verify PW:",           "zh": "确认密码：",          "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Enter email here",     "zh": "在此输入邮箱",        "scope": "login", "source": "community", "status": "approved", "notes": "placeholder"},
    {"en": "Enter username here",  "zh": "在此输入用户名",      "scope": "login", "source": "community", "status": "approved", "notes": "placeholder"},
    {"en": "Enter password here",  "zh": "在此输入密码",        "scope": "login", "source": "community", "status": "draft",    "notes": "若未出现则跳过"},
    {"en": "Create Account",       "zh": "创建账号",            "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Login",                "zh": "登录",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Log in",               "zh": "登录",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Log Out",              "zh": "登出",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Logout",               "zh": "登出",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Have Asmodee.net Account",   "zh": "我有 Asmodee.net 账号",  "scope": "login", "source": "community", "status": "approved", "notes": "保留原名以区分两个平台"},
    {"en": "Have Playdek Account",       "zh": "我有 Playdek 账号",       "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Have Valid Asmodee.net Account","zh": "我有可用的 Asmodee.net 账号","scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Have Valid Playdek Account",  "zh": "我有可用的 Playdek 账号",  "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Playdek Account Required",    "zh": "需要 Playdek 账号",         "scope": "login", "source": "community", "status": "approved", "notes": "弹窗标题"},
    {"en": "Opt In",               "zh": "加入",                "scope": "login", "source": "community", "status": "approved", "notes": "通知 / 通讯订阅"},
    {"en": "Opt Out",              "zh": "退出",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Notification Options", "zh": "通知偏好",            "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "StoneBlade Newsletter","zh": "StoneBlade 通讯",     "scope": "login", "source": "community", "status": "approved", "notes": "公司名保留原文"},
    {"en": "Profile & Settings",   "zh": "个人与设置",          "scope": "login", "source": "community", "status": "approved", "notes": "右侧边栏入口"},
    {"en": "Profile",              "zh": "个人",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Friends",              "zh": "好友",                "scope": "login", "source": "community", "status": "approved", "notes": "社交"},
    {"en": "Friend",               "zh": "好友",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Open Games",           "zh": "开放对局",            "scope": "login", "source": "community", "status": "approved", "notes": "大厅"},
    {"en": "(OPEN)",               "zh": "（开放）",            "scope": "login", "source": "community", "status": "approved", "notes": "大厅标签"},
    {"en": "(Unavailable)",        "zh": "（不可用）",          "scope": "login", "source": "community", "status": "approved", "notes": "大厅标签"},
    {"en": "Network Connection",   "zh": "网络连接",            "scope": "login", "source": "community", "status": "approved", "notes": "旧 ui_runtime 把 Network Connection迷失 译错"},
    {"en": "Avatar",               "zh": "头像",                "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Avatar of the Fallen", "zh": "堕落者化身",          "scope": "card",  "source": "community", "status": "approved", "notes": "FLAVOR_AVATAROFTHEFALLEN"},
    # --------- shop — DLC store UI strings -------------------------------
    {"en": "Expansions",               "zh": "扩展",                      "scope": "shop", "source": "community", "status": "approved", "notes": "创建对局左侧扩展列表"},
    {"en": "Expansion",                "zh": "扩展",                      "scope": "shop", "source": "community", "status": "approved", "notes": ""},
    {"en": "Promos",                   "zh": "特典",                      "scope": "shop", "source": "community", "status": "approved", "notes": "Promo N → 特典 N 单独映射"},
    {"en": "Promo Pack",               "zh": "特典包",                    "scope": "shop", "source": "community", "status": "approved", "notes": "promo兽群 严重错误修正"},
    {"en": "Promo Pack #1",            "zh": "特典包 1",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack #2",            "zh": "特典包 2",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack #3",            "zh": "特典包 3",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack #4",            "zh": "特典包 4",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack #5",            "zh": "特典包 5",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack #6",            "zh": "特典包 6",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack #7",            "zh": "特典包 7",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo1",                   "zh": "特典 1",                    "scope": "promo","source": "community", "status": "approved", "notes": "UI 内部名"},
    {"en": "Promo2",                   "zh": "特典 2",                    "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo3",                   "zh": "特典 3",                    "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo4",                   "zh": "特典 4",                    "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo5",                   "zh": "特典 5",                    "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo6",                   "zh": "特典 6",                    "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo7",                   "zh": "特典 7",                    "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Bundles",                  "zh": "合集",                      "scope": "shop", "source": "community", "status": "approved", "notes": "商店合集分类"},
    {"en": "Bundle",                   "zh": "合集",                      "scope": "shop", "source": "community", "status": "approved", "notes": ""},
    {"en": "Collection Bundle",        "zh": "收藏合集",                  "scope": "shop", "source": "community", "status": "approved", "notes": ""},
    {"en": "Expansion Bundle",         "zh": "扩展合集",                  "scope": "shop", "source": "community", "status": "approved", "notes": ""},
    {"en": "Purchaseable on Steam",    "zh": "可在 Steam 购买",           "scope": "shop", "source": "community", "status": "approved", "notes": "旧译 Purchaseable在Steam 需修正"},
    {"en": "Purchaseable in Steam",    "zh": "可在 Steam 购买",           "scope": "shop", "source": "community", "status": "approved", "notes": "in/on 变体同译"},
    {"en": "Purchase:",                "zh": "购买：",                    "scope": "shop", "source": "community", "status": "approved", "notes": "价格前缀"},
    {"en": "Purchase all the Ascension bundles for one low price!", "zh": "以超划算的价格一次购买全部《创升纪元》合集！", "scope": "shop", "source": "community", "status": "approved", "notes": "L长句整句，不拆"},
    {"en": "Purchase Separately",      "zh": "单独购买",                  "scope": "shop", "source": "community", "status": "approved", "notes": ""},
    {"en": "Select Expansions/Promos", "zh": "选择扩展/特典",             "scope": "shop", "source": "community", "status": "approved", "notes": "创建对局底部标题"},
    {"en": "Required Expansions",      "zh": "所需扩展",                  "scope": "shop", "source": "community", "status": "approved", "notes": "在线对局"},
    {"en": "Unique new cards per set:", "zh": "每款扩展的全新卡牌数：",   "scope": "chapter","source": "community","status": "approved", "notes": "DLC 合集描述标题"},
    {"en": "Promo Cards Included:",    "zh": "包含的特典卡：",            "scope": "chapter","source": "community","status": "approved", "notes": "特典卡合集描述"},
    {"en": "Description:",             "zh": "简介：",                    "scope": "chapter","source": "community","status": "approved", "notes": "DLC 详情"},
    {"en": "Includes XX unique new cards.","zh": "包含 XX 张全新卡牌。",  "scope": "chapter","source": "community","status": "draft",    "notes": "模板句，L# 实际每段带数字"},
    {"en": "Includes 51 unique new cards.", "zh": "包含 51 张全新卡牌。", "scope": "chapter","source": "community","status": "approved", "notes": "救赎"},
    {"en": "Includes 49 unique new cards.", "zh": "包含 49 张全新卡牌。", "scope": "chapter","source": "community","status": "approved", "notes": "谵妄"},
    {"en": "Includes 72 unique new cards.", "zh": "包含 72 张全新卡牌。", "scope": "chapter","source": "community","status": "approved", "notes": "冠军黎明"},
    {"en": "Includes 76 unique new cards.", "zh": "包含 76 张全新卡牌。", "scope": "chapter","source": "community","status": "approved", "notes": "梦境"},
    {"en": "Includes 55 unique new cards.", "zh": "包含 55 张全新卡牌。", "scope": "chapter","source": "community", "status": "approved", "notes": "元素的馈赠"},
    {"en": "Includes 53 unique new cards.", "zh": "包含 53 张全新卡牌。", "scope": "chapter","source": "community", "status": "approved", "notes": "领域解开"},
    {"en": "Includes 47 unique new cards.", "zh": "包含 47 张全新卡牌。", "scope": "chapter","source": "community", "status": "approved", "notes": "祈夜崛起"},
    {"en": "Includes 35 unique new cards.", "zh": "包含 35 张全新卡牌。", "scope": "chapter","source": "community", "status": "approved", "notes": "黑暗释放"},
    {"en": "Includes 43 unique new cards.", "zh": "包含 43 张全新卡牌。", "scope": "chapter","source": "community", "status": "approved", "notes": "暗影之战"},
    {"en": "Includes 51 unique<br>new cards.","zh": "包含 51 张全新<br>卡牌。", "scope": "chapter","source": "community", "status": "approved", "notes": "救赎版本（带换行）"},
    # --------- chapter — rulebook chapter headings ----------------------
    {"en": "Resources:",                "zh": "资源：",                    "scope": "chapter","source": "community","status": "approved", "notes": "弑神编年史规则书第 1 大章"},
    {"en": "RESOURCES",                 "zh": "资源",                      "scope": "chapter","source": "community","status": "approved", "notes": "大标题（allcaps）"},
    {"en": "RUNES:",                    "zh": "符文：",                    "scope": "chapter","source": "community","status": "approved", "notes": "截图里混杂段的左侧标题"},
    {"en": "POWER:",                    "zh": "战力：",                    "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "HONOR:",                    "zh": "荣誉：",                    "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "FACTIONS:",                 "zh": "派系：",                    "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "FATE CARDS:",               "zh": "天命卡：",                  "scope": "chapter","source": "community","status": "approved", "notes": "邪神归来机制说明"},
    {"en": "What's New",                "zh": "新增内容",                  "scope": "chapter","source": "community", "status": "approved", "notes": "每本扩展规则书都有"},
    {"en": "Features",                  "zh": "特性",                      "scope": "chapter","source": "community", "status": "approved", "notes": "每本扩展规则书都有"},
    {"en": "Introduction",              "zh": "简介",                      "scope": "chapter","source": "community", "status": "approved", "notes": "弑神编年史前言"},
    {"en": "Honor Pool:",               "zh": "荣誉池：",                  "scope": "chapter","source": "community", "status": "approved", "notes": "结束条件段"},
    {"en": "Temples:",                  "zh": "神庙：",                    "scope": "chapter","source": "community", "status": "approved", "notes": "上古山谷机制"},
    {"en": "Additional IP Development", "zh": "附加 IP 开发",              "scope": "credits","source": "community","status": "approved", "notes": "Credits 职位标签（可选译，人名保留）"},
    {"en": "Produced by",               "zh": "制作",                      "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Executive Producer",        "zh": "执行制作人",                "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Senior Producer",           "zh": "高级制作人",                "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Associate Producer",        "zh": "副制作人",                  "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Lead Producer",             "zh": "首席制作人",                "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Producer",                  "zh": "制作人",                    "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Assistant Producer",        "zh": "助理制作人",                "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Game Design",               "zh": "游戏设计",                  "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Design",                    "zh": "设计",                      "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Additional Design",         "zh": "附加设计",                  "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Illustrations",             "zh": "插画",                      "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Art Direction",             "zh": "美术指导",                  "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Graphic Design",            "zh": "平面设计",                  "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Development",               "zh": "开发",                      "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Lead Engineer",             "zh": "首席工程师",                "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Software Engineer",         "zh": "软件工程师",                "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Playtesting",               "zh": "试玩",                      "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Special Thanks",            "zh": "特别感谢",                  "scope": "credits","source": "community", "status": "approved", "notes": ""},
    {"en": "Based on the Game Designed by Justin Gary", "zh": "基于 Justin Gary 设计的桌游", "scope": "credits", "source": "community", "status": "approved", "notes": "设计师名保留原文"},
    # --------- ui — missing from existing glossary (dump E class) --------
    {"en": "Create Offline Game",       "zh": "创建离线对局",              "scope": "ui", "source": "community", "status": "approved", "notes": "页面大标题"},
    {"en": "Offline Games",             "zh": "离线对局",                  "scope": "ui", "source": "community", "status": "approved", "notes": "页面标题"},
    {"en": "Create Game",               "zh": "创建对局",                  "scope": "ui", "source": "community", "status": "approved", "notes": "菜单按钮"},
    {"en": "Player 1",                  "zh": "玩家 1",                    "scope": "ui", "source": "official-anshashen", "status": "approved", "notes": ""},
    {"en": "Player 2",                  "zh": "玩家 2",                    "scope": "ui", "source": "official-anshashen", "status": "approved", "notes": ""},
    {"en": "Player 3",                  "zh": "玩家 3",                    "scope": "ui", "source": "official-anshashen", "status": "approved", "notes": ""},
    {"en": "Player 4",                  "zh": "玩家 4",                    "scope": "ui", "source": "official-anshashen", "status": "approved", "notes": ""},
    {"en": "30 Minutes",                "zh": "30 分钟",                   "scope": "ui", "source": "community", "status": "approved", "notes": "对局时长选项"},
    {"en": "60 Minutes",                "zh": "60 分钟",                   "scope": "ui", "source": "community", "status": "draft",    "notes": "若未出现则跳过"},
    {"en": "Unlimited",                 "zh": "不限时",                    "scope": "ui", "source": "community", "status": "approved", "notes": "对局时长"},
    {"en": "Roll Results:",             "zh": "掷骰结果：",                "scope": "ui", "source": "community", "status": "approved", "notes": "谵妄骰结算"},
    {"en": "Opponent Bids:",            "zh": "对手竞拍：",                "scope": "ui", "source": "community", "status": "approved", "notes": "命运竞拍"},
    {"en": "Keep Playing",              "zh": "继续对局",                  "scope": "ui", "source": "community", "status": "approved", "notes": "延迟结束结算"},
    {"en": "Claim Victory",             "zh": "宣告胜利",                  "scope": "ui", "source": "community", "status": "approved", "notes": "结束条件达成"},
    {"en": "Next Game",                 "zh": "下一局",                    "scope": "ui", "source": "community", "status": "approved", "notes": "结算页"},
    {"en": "Player Area",               "zh": "玩家区域",                  "scope": "ui", "source": "community", "status": "approved", "notes": "教学提示"},
    {"en": "Opponent Area",             "zh": "对手区域",                  "scope": "ui", "source": "community", "status": "approved", "notes": ""},
    {"en": "Info Line",                 "zh": "信息栏",                    "scope": "ui", "source": "community", "status": "approved", "notes": ""},
    {"en": "Top Area",                  "zh": "顶部区域",                  "scope": "ui", "source": "community", "status": "approved", "notes": "荣誉池/回合区"},
    {"en": "Bottom Area",               "zh": "底部区域",                  "scope": "ui", "source": "community", "status": "draft",    "notes": "若未出现则跳过"},
    {"en": "Loading rulebook, please wait.", "zh": "正在加载规则书，请稍候…","scope": "ui","source": "community","status": "approved", "notes": ""},
    {"en": "Loading rulebook, please wait",  "zh": "正在加载规则书，请稍候…","scope": "ui","source": "community","status": "approved", "notes": "不带句号变体"},
    {"en": "Opponents",                 "zh": "对手",                      "scope": "ui", "source": "community", "status": "approved", "notes": "玩家区域外的统称"},
    {"en": "Opponent",                  "zh": "对手",                      "scope": "ui", "source": "community", "status": "approved", "notes": ""},
    {"en": "AI Player",                 "zh": "AI 玩家",                   "scope": "ui", "source": "community", "status": "approved", "notes": "单机对局"},
    {"en": "Hot Seat",                  "zh": "热座模式",                  "scope": "ui", "source": "community", "status": "draft",    "notes": "同屏多人模式（若存在）"},
    {"en": "Renown",                    "zh": "名望",                      "scope": "resource","source": "new",    "status": "approved", "notes": "史诗传奇（ASCL）主要机制；之前 Renown 误写成声望，必须修正"},
    {"en": "Dreambind",                 "zh": "梦缚",                      "scope": "label", "source": "community","status": "approved", "notes": "梦境机制"},
    {"en": "Squire",                    "zh": "侍从",                      "scope": "card",  "source": "community","status": "draft",    "notes": "救赎机制？待确认卡图是否出现"},
    {"en": "Squire's Challenge",        "zh": "侍从挑战",                  "scope": "label", "source": "community","status": "draft",    "notes": ""},
    {"en": "Deliverance Rulebook",      "zh": "救赎规则书",                "scope": "chapter","source": "new",    "status": "approved", "notes": ""},
    {"en": "Delirium Rulebook",         "zh": "谵妄规则书",                "scope": "chapter","source": "new",    "status": "approved", "notes": ""},
    {"en": "RulebookDU",                "zh": "黑暗释放规则书",            "scope": "chapter","source": "community","status": "approved", "notes": "Prefab 内部名（Manifest 里有）"},
    {"en": "RulebookRV",                "zh": "祈夜崛起规则书",            "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "RulebookWA",                "zh": "暗影之战规则书",            "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "RulebookRU",                "zh": "领域解开规则书",            "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "RulebookDC",                "zh": "冠军黎明规则书",            "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "RulebookDS",                "zh": "梦境规则书",                "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "RulebookGE",                "zh": "元素的馈赠规则书",          "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "RulebookVA",                "zh": "上古山谷规则书",            "scope": "chapter","source": "community","status": "approved", "notes": ""},
    {"en": "RulebookDLRM",              "zh": "谵妄规则书",                "scope": "chapter","source": "community","status": "approved", "notes": "Prefab 名"},
    {"en": "RulebookDLV",               "zh": "救赎规则书",                "scope": "chapter","source": "community","status": "approved", "notes": "Prefab 名"},
    {"en": "RulebookASCL",              "zh": "史诗传奇规则书",            "scope": "chapter","source": "community","status": "approved", "notes": "Prefab 名"},
    # --------- phrase — common rulebook sentence fragments (整句，不拆) -
    {"en": "For millennia, the world of Vigil has been isolated and protected from other realms.",
     "zh": "千百年来，祈夜世界一直与其他领域隔绝并受其庇护。",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "CotG 规则书前言 — L#39 第一段"},
    {"en": "Now, the barrier between dimensions is failing, and Samael, the Fallen God, has returned with his army of Monsters from the beyond!",
     "zh": "如今，次元之间的屏障正在崩塌，堕落之神萨麦尔率领他的怪物大军从异界归来！",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "CotG 前言 — 第二段"},
    {"en": "You are one of the few warriors capable of facing this threat and defending your world, but you cannot do it alone!",
     "zh": "你是少数能够直面此威胁、守护你世界的战士之一，但你无法孤军奋战！",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "CotG 前言 — 第三段"},
    {"en": "You must summon powerful Heroes and Constructs to aid you in your battles.",
     "zh": "你必须召集强大的英雄与神器，助你投入战斗。",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "CotG 前言 — 第四段"},
    {"en": "The player who gains the most Honor Points will lead his army to defeat the Fallen One and earn the title of Godslayer.",
     "zh": "获得最多荣誉点数的玩家将率领军队击败堕神，并赢得弑神者的称号。",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "CotG 前言 — 第五段"},
    {"en": "Runes are one of the two main resources in Ascension. Runes are used to acquire Heroes and Constructs so you can add them to your deck.",
     "zh": "符文是《创升纪元》的两大核心资源之一。符文用于获取英雄和神器，将它们加入你的牌库。",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "截图中 RESOURCES 段 — RUNES — 原句（解决符文为一的两main resources在Ascension问题）"},
    {"en": "Power is the second resource in Ascension. Power is used to defeat Monsters and earn rewards.",
     "zh": "战力是《创升纪元》的第二大资源。战力用于击败怪物并获得奖励。",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "RESOURCES 段 — POWER — 原句"},
    {"en": "The final resource is Honor. The player with the most Honor at the end of the game wins.",
     "zh": "最后一种资源是荣誉。游戏结束时荣誉最多的玩家获胜。",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "RESOURCES 段 — HONOR — 原句"},
    {"en": "There are four factions in Ascension: Enlightened, Lifebound, Mechana, and Void.",
     "zh": "《创升纪元》共有四大派系：圣贤、命约、机械和虚空。",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "FACTIONS 段"},
    {"en": "Each faction has a different play style and strategy. Heroes and Constructs belong to one of the four factions, and Monsters are a separate card type.",
     "zh": "每个派系都有不同的玩法和策略。英雄与神器分属四大派系之一，而怪物则是独立的卡牌类型。",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "FACTIONS 段后续"},
    {"en": "At the end of the game, the Honor token pool empties and each player counts up their total Honor to determine the winner.",
     "zh": "游戏结束时，荣誉点数池耗尽，每位玩家清点其荣誉总数以决定胜者。",
     "scope": "phrase", "source": "new", "status": "approved", "notes": "荣誉池结束条件"},
    # --------- label — card-face keywords / headers (Reward / Fate / Trophy) -
    {"en": "Reward",                   "zh": "奖励",                      "scope": "label", "source": "official-anshashen", "status": "approved", "notes": "怪物奖励标签；原文常大写 REWARD"},
    {"en": "REWARD",                   "zh": "奖励",                      "scope": "label", "source": "official-anshashen", "status": "approved", "notes": ""},
    {"en": "Reward:",                  "zh": "奖励：",                    "scope": "label", "source": "official-anshashen", "status": "approved", "notes": ""},
    {"en": "REWARD:",                  "zh": "奖励：",                    "scope": "label", "source": "official-anshashen", "status": "approved", "notes": "与 FATE: / TROPHY: 大标题同风格"},
    {"en": "Fate:",                    "zh": "命运：",                    "scope": "label", "source": "official-anshashen", "status": "approved", "notes": "命运卡标题"},
    {"en": "FATE:",                    "zh": "命运：",                    "scope": "label", "source": "official-anshashen", "status": "approved", "notes": ""},
    {"en": "Trophy:",                  "zh": "战利品：",                  "scope": "label", "source": "official-anshashen", "status": "approved", "notes": "怪物/邪神战利品"},
    {"en": "TROPHY:",                  "zh": "战利品：",                  "scope": "label", "source": "official-anshashen", "status": "approved", "notes": ""},
    # --------- promo — 不带 # 号变体 + 登录页残片修正 ---------------------
    {"en": "Promo Pack 1",             "zh": "特典包 1",                  "scope": "promo","source": "community", "status": "approved", "notes": "（旧 ui_runtime 机翻：Promo兽群 1）"},
    {"en": "Promo Pack 2",             "zh": "特典包 2",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack 3",             "zh": "特典包 3",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack 4",             "zh": "特典包 4",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack 5",             "zh": "特典包 5",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Pack 6",             "zh": "特典包 6",                  "scope": "promo","source": "community", "status": "approved", "notes": "（旧 ui_runtime 机翻：Promo兽群 6）"},
    {"en": "Promo Pack 7",             "zh": "特典包 7",                  "scope": "promo","source": "community", "status": "approved", "notes": ""},
    {"en": "Promo Cards",              "zh": "特典卡",                    "scope": "promo","source": "community", "status": "approved", "notes": "统一称『卡』不称『卡牌』"},
    {"en": "Promo Card",               "zh": "特典卡",                    "scope": "promo","source": "community", "status": "approved", "notes": ""},
    # --------- ASCL Renown / Legendary Boons labels -----------------------
    {"en": "Renown Track",             "zh": "名望轨道",                  "scope": "label", "source": "community", "status": "approved", "notes": ""},
    {"en": "Legendary Boon",           "zh": "传奇恩赐",                  "scope": "label", "source": "community", "status": "approved", "notes": "ASCL 里程碑奖励"},
    {"en": "Legendary Boons",          "zh": "传奇恩赐",                  "scope": "label", "source": "community", "status": "approved", "notes": "复数同译"},
    {"en": "Renown 1",                 "zh": "名望 1",                    "scope": "label", "source": "community", "status": "approved", "notes": ""},
    {"en": "Renown 2",                 "zh": "名望 2",                    "scope": "label", "source": "community", "status": "approved", "notes": ""},
    {"en": "Renown 3",                 "zh": "名望 3",                    "scope": "label", "source": "community", "status": "approved", "notes": ""},
    {"en": "Renown 4",                 "zh": "名望 4",                    "scope": "label", "source": "community", "status": "approved", "notes": ""},
    {"en": "Renown 5",                 "zh": "名望 5",                    "scope": "label", "source": "community", "status": "approved", "notes": ""},
    # --------- Pasythea promo cards (exact match) --------------------------
    {"en": "Puggageddon",              "zh": "巴哥末日",                  "scope": "card",  "source": "official-anshashen", "status": "approved", "notes": "官方 lua_cards 定名，入 glossary 防漏匹配"},
    {"en": "Defender of Vigil",        "zh": "祈夜守卫者",                "scope": "card",  "source": "community", "status": "approved", "notes": "Promo 英雄（带官方译名以官方为准）"},
    {"en": "Explosive Swarm",          "zh": "爆裂虫群",                  "scope": "card",  "source": "community", "status": "approved", "notes": "Promo 怪物"},
    {"en": "Nova, Born of Chaos",      "zh": "诺娃·混沌所生",              "scope": "card",  "source": "community", "status": "approved", "notes": "Promo 英雄"},
    # --------- login screen machine-translation garbage cleanup ----------
    {"en": "Network Connection Lost",  "zh": "网络连接已断开",            "scope": "login", "source": "community", "status": "approved", "notes": "（旧 ui_runtime 机翻：Network Connection迷失）"},
    {"en": "Player Name",              "zh": "玩家姓名",                  "scope": "login", "source": "community", "status": "approved", "notes": "（旧：Player命名）"},
    {"en": "has not logged into the Ascension servers.",
     "zh": "尚未登录《创升纪元》服务器。",
     "scope": "login", "source": "community", "status": "approved", "notes": "（旧：具有不logged置入Ascension servers.）"},
    {"en": '"Player Name" has not logged into the Ascension servers.',
     "zh": "「玩家姓名」尚未登录《创升纪元》服务器。",
     "scope": "login", "source": "community", "status": "approved", "notes": ""},
    {"en": "Add a Friend",             "zh": "添加好友",                  "scope": "login", "source": "community", "status": "approved", "notes": "（旧：加入Friend）"},
    {"en": "< 1 Day",                  "zh": "< 1 天",                    "scope": "login", "source": "community", "status": "approved", "notes": "（旧：< 1 昼）"},
    {"en": "1-7 Days",                 "zh": "1–7 天",                   "scope": "login", "source": "community", "status": "approved", "notes": "（旧：1-7 往日）"},
    {"en": "Chronicles of the Godslayer",
     "zh": "《弑神编年史》",            "scope": "series","source": "official-anshashen", "status": "approved", "notes": "（旧：Chronicles的弑神者）"},
    {"en": "Would you like to delete\nthis friend from your list?",
     "zh": "确定要将此好友从你的好友列表中删除吗？",
     "scope": "login", "source": "community", "status": "approved", "notes": "（旧：Would你like以delete此friend从你的list?）"},
    {"en": "Would you like to delete this friend from your list?",
     "zh": "确定要将此好友从你的好友列表中删除吗？",
     "scope": "login", "source": "community", "status": "approved", "notes": "不带换行变体"},
    # --------- credits placeholder / developer leftovers -------------------
    {"en": "Administration",           "zh": "管理层",                    "scope": "credits","source": "community", "status": "approved", "notes": "Credits 大标题"},
    {"en": "Chief Executive Officer, Playdek",
     "zh": "Playdek 首席执行官",        "scope": "credits","source": "community", "status": "approved", "notes": "人名 Joel Goodman 保留原文"},
    {"en": "Info block of Info",       "zh": "信息区块（调试占位符）",    "scope": "ui",    "source": "community", "status": "approved", "notes": "开发者残留文本"},
    {"en": "Info block of Info block of Info",
     "zh": "信息区块的信息区块（调试占位符）",
     "scope": "ui",    "source": "community", "status": "approved", "notes": "开发者残留文本"},
    {"en": "Info blocky of Info",      "zh": "信息区块（调试占位符）",    "scope": "ui",    "source": "community", "status": "approved", "notes": "变体（拼错）"},
    {"en": "Confirmation Popup Text Here",
     "zh": "确认弹窗占位文本",
     "scope": "ui",    "source": "community", "status": "approved", "notes": "开发者占位符；若运行时不出现则不译"},
    # --------- set subtitle / Dream Vision (DoC 冠军面板系列) ---------
    {"en": "Dream Vision",                "zh": "梦境视域",       "scope": "label", "source": "community", "status": "approved", "notes": "DoC 冠军卡 系列名, 原 ui_runtime 梦Vision错译"},
    {"en": "Enlightened Dream Vision",    "zh": "圣贤梦境视域",   "scope": "label", "source": "community", "status": "approved", "notes": "原 启迪梦Vision 错译"},
    {"en": "Void Dream Vision",           "zh": "虚空梦境视域",   "scope": "label", "source": "community", "status": "approved", "notes": "原 虚空梦Vision 错译"},
    {"en": "Lifebound Champion",          "zh": "命约勇士",       "scope": "label", "source": "community", "status": "approved", "notes": "DoC 冠军面板 subtitle, 原 生命冠军 错译"},
    {"en": "Enlightened Champion",        "zh": "圣贤勇士",       "scope": "label", "source": "community", "status": "approved", "notes": "配套 subtitle"},
    {"en": "Void Champion",               "zh": "虚空勇士",       "scope": "label", "source": "community", "status": "approved", "notes": "配套 subtitle"},
    {"en": "Mechana Champion",            "zh": "机械勇士",       "scope": "label", "source": "community", "status": "approved", "notes": "配套 subtitle"},
    {"en": "Mechana Dream Hero",          "zh": "机械梦英雄",     "scope": "label", "source": "community", "status": "approved", "notes": "Dreamscape subtitle"},
    {"en": "Dream Construct",             "zh": "梦铸神器",       "scope": "label", "source": "community", "status": "approved", "notes": "Dreamscape subtype"},
    # --------- reputation (声望) keyword ---------
    {"en": "reputation",                  "zh": "声望",           "scope": "mechanic", "source": "community", "status": "approved", "notes": "DoC rep 资源, 原机翻保留 rep 英文"},
    {"en": "Reputation",                  "zh": "声望",           "scope": "mechanic", "source": "community", "status": "approved", "notes": "标题式变体"},
    # --------- Champion names (DoC 4 champion + flavor) ---------
    {"en": "Nairi",                       "zh": "奈莉",           "scope": "champion", "source": "community", "status": "approved", "notes": "FLAVOR_NAIRI 命约冠军"},
    {"en": "Dhartha",                     "zh": "达萨",           "scope": "champion", "source": "community", "status": "approved", "notes": "FLAVOR_DHARTHA 圣贤冠军"},
    {"en": "Sadranis",                    "zh": "萨德拉尼斯",     "scope": "champion", "source": "community", "status": "approved", "notes": "FLAVOR_SADRANIS 虚空冠军"},
    {"en": "Kor, the Ferromancer",        "zh": "铁术师科尔",     "scope": "card",     "source": "official-anshashen", "status": "approved", "notes": ""},
]


@dataclass
class Row:
    en: str
    zh: str
    scope: str
    source: str = "new"
    status: str = "approved"  # default so old rows without status column still load
    notes: str = ""


VALID_SCOPES = {
    "series", "world", "faction", "type", "resource", "zone", "verb",
    "label", "card", "set", "promo", "ui", "button", "login", "shop",
    "chapter", "credits", "phrase",
}

VALID_SOURCES = {
    "official-anshashen", "official-chuangsheng", "community", "new",
}


def _read_glossary() -> tuple[list[Row], list[str]]:
    """Read the hand-written glossary CSV, preserving comment lines."""
    comments: list[str] = []
    rows: list[Row] = []
    with GLOSSARY_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header_seen = False
        for raw in reader:
            if not raw:
                continue
            en = raw[0].lstrip("\ufeff")
            if en.startswith("#"):
                comments.append(raw[0])
                continue
            if not header_seen:
                # header row — validate schema evolution
                header_seen = True
                cols = {c: i for i, c in enumerate(raw)}
                continue
            has_status = "status" in cols
            has_notes = "notes" in cols
            # When schema has no status column, all rows default to approved.
            # When schema has no notes column, leave empty.
            # We use two separate default sentinels (None for missing column,
            # -1 would index into notes by accident on old 5-col glossaries).
            status_idx = cols["status"] if has_status else None
            notes_idx = cols["notes"] if has_notes else None
            row = Row(
                en=en,
                zh=raw[cols.get("zh", 1)] if len(raw) > cols.get("zh", 1) else "",
                scope=raw[cols.get("scope", 2)] if len(raw) > cols.get("scope", 2) else "",
                source=raw[cols.get("source", 3)] if len(raw) > cols.get("source", 3) else "new",
                status=(raw[status_idx] if (status_idx is not None and len(raw) > status_idx) else "approved") or "approved",
                notes=(raw[notes_idx] if (notes_idx is not None and len(raw) > notes_idx) else ""),
            )
            rows.append(row)
    return rows, comments


def _seed_missing(rows: list[Row]) -> tuple[list[Row], int]:
    """Insert SEED_ROWS that are not already in rows by (en, scope)."""
    existing = {(r.en.casefold(), r.scope) for r in rows}
    added = 0
    for seed in SEED_ROWS:
        key = (seed["en"].casefold(), seed["scope"])
        if key in existing:
            continue
        rows.append(Row(**seed))
        existing.add(key)
        added += 1
    return rows, added


def _write_glossary(rows: list[Row], comments: list[str]) -> int:
    """Write the glossary back with the canonical column order.

    Format:
        Line 1            → CSV header (en,zh,scope,source,status,notes)
        Lines 2..N        → either:
            - comment rows: first column is ``# <heading>`` (the Chinese
              section title that used to sit on its own line pre-merge);
              ``load_glossary`` skips rows whose ``en`` starts with ``#``.
            - data rows: all six fields populated.

    We no longer put comments BEFORE the header, because ``csv.DictReader``
    would then mis-parse the comment line as the column-names row and every
    subsequent row would collapse into a single key.
    """
    scope_order: list[str] = [
        "series", "world", "faction", "type", "resource", "zone",
        "verb", "label", "card", "set", "promo",
        "ui", "button", "login", "shop", "chapter", "credits", "phrase",
    ]
    by_scope: dict[str, list[Row]] = {s: [] for s in scope_order}
    orphans: list[Row] = []
    for r in rows:
        if r.scope in by_scope:
            by_scope[r.scope].append(r)
        else:
            orphans.append(r)
    header = ["en", "zh", "scope", "source", "status", "notes"]
    # Map scope → Chinese section heading comment (reconstructed from
    # whatever the original hand-written glossary had).  Keep this table in
    # sync with scope_order.  Comments are always emitted with exactly the
    # 6-column shape "# 中文标题", "", "", "", "", "" so DictReader treats
    # them as plain rows and our loader skips them via en.startswith("#").
    section_headings: dict[str, str] = {
        "series":   "# 系列\t\t\t\t\t游戏内系列名只用「创升纪元」。早期官方/维基「暗杀神」不进游戏。",
        "world":    "# 世界",
        "faction":  "# 派系\t\t\t\t\t图鉴侧栏。Monster 兼作卡牌类型，scope 留 faction 以生成首字放大。",
        "type":     "# 类型",
        "resource": "# 资源",
        "zone":     "# 区域",
        "verb":     "# 行动",
        "label":    "# 关键字 / 卡面标签",
        "card":     "# 始终可用",
        "set":      "# 扩展\t\t\t\t\tCotG–SoS 跟《暗杀神》；2017 年后跟《创升纪元》。",
        "promo":    "# 特典 / 推广卡",
        "ui":       "# 界面\t\t\t\t\t无官方菜单中文；译名跟术语表对齐。",
        "button":   "# 系统按钮",
        "login":    "# 登录 / 账号（Playdek / Asmodee.net）",
        "shop":     "# DLC 商店文案术语",
        "chapter":  "# 规则书章节标题 / DLC 节标题",
        "credits":  "# Credits / 制作人员职务标签（人名保留原文，仅译职务）",
        "phrase":   "# 规则书完整段落 / 商店完整整句 / 常用整句",
    }
    written = 0
    with GLOSSARY_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        written += 1
        for s in scope_order:
            group = by_scope[s]
            if not group and s not in section_headings:
                continue
            # section comment row
            heading = section_headings.get(s)
            if heading:
                # The hand-written legacy file used tab-separated inline
                # notes after the heading.  csv.writer escapes those for us
                # when they contain commas; preserve them as one string in
                # the ``en`` column so the comment line visually looks like
                # "# 系列   游戏内系列名只用..." just like before.
                w.writerow([heading, "", "", "", "", ""])
                written += 1
            for r in sorted(group, key=lambda x: (x.en.casefold(), x.zh.casefold())):
                if r.scope not in VALID_SCOPES:
                    print(f"WARN: invalid scope {r.scope!r} for en={r.en!r}")
                if r.source not in VALID_SOURCES:
                    print(f"WARN: invalid source {r.source!r} for en={r.en!r}")
                w.writerow([r.en, r.zh, r.scope, r.source, r.status, r.notes])
                written += 1
        if orphans:
            w.writerow(["# 其他 scope 未识别条目", "", "", "", "", ""])
            written += 1
            for r in orphans:
                w.writerow([r.en, r.zh, r.scope, r.source, r.status, r.notes])
                written += 1
    return written


def _derive(rows: list[Row]) -> tuple[dict[str, str], set[str]]:
    """Build the two derived data structures consumed by other modules:
    exact_map  → scope in {ui, button, login, shop, chapter, credits,
                  verb, label, zone, resource, faction, type, series, set,
                  card, promo, phrase} AND status=approved AND zh != ""
                  AND status != "conflict"
    allow_short → en in rows AND len(en) <= 4 AND status=approved AND zh != ""
                  (overlay.py skips len<=4 exact unless the key is in this set)
    """
    exact_scopes = {
        "ui", "button", "login", "shop", "chapter", "credits",
        "verb", "label", "zone", "resource", "faction", "type",
        "series", "set", "card", "promo", "phrase", "world",
    }
    exact_map: dict[str, str] = {}
    allow_short: set[str] = set()
    for r in rows:
        if r.status == "conflict" or not r.zh or r.zh == r.en:
            continue
        if r.status not in {"approved", "draft"}:  # draft still goes in? → no: only approved.
            continue
        if r.scope in exact_scopes and r.status == "approved":
            # Longer strings first wins to avoid collisions
            if r.en not in exact_map:
                exact_map[r.en] = r.zh
        if len(r.en) <= 4 and r.status == "approved":
            allow_short.add(r.en)
    return exact_map, allow_short


def _write_report(rows: list[Row], exact: dict[str, str], allow_short: set[str]) -> None:
    by_scope_count: dict[str, int] = {}
    by_scope_draft: dict[str, int] = {}
    by_scope_conflict: dict[str, int] = {}
    by_scope_approved: dict[str, int] = {}
    for r in rows:
        by_scope_count[r.scope] = by_scope_count.get(r.scope, 0) + 1
        bucket = (by_scope_approved if r.status == "approved"
                  else by_scope_draft if r.status == "draft"
                  else by_scope_conflict)
        bucket[r.scope] = bucket.get(r.scope, 0) + 1
    lines: list[str] = []
    lines.append(f"glossary/zh-Hans.csv — coverage report")
    lines.append(f"generated by tools/glossary_gen.py")
    lines.append("")
    lines.append(f"Total rows: {len(rows)}")
    lines.append(f"Exact map entries exported: {len(exact)}")
    lines.append(f"ALLOW_SHORT (len<=4): {sorted(allow_short)}")
    lines.append("")
    lines.append(f"{'Scope':<10} {'Total':>6} {'Approved':>8} {'Draft':>6} {'Conflict':>9}")
    lines.append("-" * 46)
    for scope in sorted(by_scope_count):
        lines.append(f"{scope:<10} {by_scope_count[scope]:>6} "
                     f"{by_scope_approved.get(scope, 0):>8} "
                     f"{by_scope_draft.get(scope, 0):>6} "
                     f"{by_scope_conflict.get(scope, 0):>9}")
    lines.append("")
    drafts = [r for r in rows if r.status == "draft"]
    if drafts:
        lines.append(f"DRAFT ({len(drafts)}) — 待翻译 / 待审核：")
        for r in drafts:
            z = r.zh if r.zh else "(无译文)"
            lines.append(f"  [{r.scope}] {r.en!r} → {z!r}  # {r.notes}")
    conflicts = [r for r in rows if r.status == "conflict"]
    if conflicts:
        lines.append("")
        lines.append(f"CONFLICT ({len(conflicts)}) — 已从派生表剔除，需人工处理：")
        for r in conflicts:
            lines.append(f"  [{r.scope}] {r.en!r} → {r.zh!r}  # {r.notes}")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="read + seed + report only; do not write back glossary.csv")
    args = ap.parse_args()

    if not GLOSSARY_PATH.is_file():
        print(f"FATAL: glossary not found at {GLOSSARY_PATH}")
        sys.exit(1)

    rows, comments = _read_glossary()
    print(f"read existing rows: {len(rows)} (comments: {len(comments)})")
    rows, added = _seed_missing(rows)
    print(f"seed rows injected (absent before): {added}")
    if not args.dry_run:
        written = _write_glossary(rows, comments)
        print(f"rewrote {GLOSSARY_PATH.name}: {written} data rows")
    exact, allow_short = _derive(rows)
    _write_report(rows, exact, allow_short)
    print(f"derived: exact={len(exact)}  allow_short(len<=4)={len(allow_short)}")
    print(f"report → {REPORT_PATH.name}")


if __name__ == "__main__":
    main()
