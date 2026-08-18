"""One-shot: emit the translation-gap canvas. ASCII stdout only."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "state" / "gap_canvas.json"
OUT = Path(
    r"C:\Users\kylei\.cursor\projects\c-Program-Files-x86-Steam-steamapps-common-Ascension\canvases\zh-cn-translation-gaps.canvas.tsx"
)

data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
raw = json.dumps(data, ensure_ascii=False, indent=2).replace("\ufffd", "Ae")

tsx = r'''import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  CollapsibleSection,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  UsageBar,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

type TabId =
  | "overview"
  | "names"
  | "mixed"
  | "effects"
  | "flavor"
  | "ui"
  | "skip";

const DATA = ''' + raw + r''' as const;

const SETS: { id: string; label: string; zh: string }[] = [
  { id: "CotG10", label: "CotG 10th", zh: "弑神编年史十周年" },
  { id: "RotF", label: "RotF", zh: "邪神归来" },
  { id: "SoS", label: "SoS", zh: "灵魂风暴" },
  { id: "IH", label: "IH", zh: "不朽英雄" },
  { id: "RoV", label: "RoV", zh: "祈夜崛起" },
  { id: "DU", label: "DU", zh: "黑暗释放" },
  { id: "RU", label: "RU", zh: "领域解开" },
  { id: "DoC", label: "DoC", zh: "冠军黎明" },
  { id: "DS", label: "DS", zh: "梦境" },
  { id: "WoS", label: "WoS", zh: "暗影之战" },
  { id: "GotE", label: "GotE", zh: "元素的馈赠" },
  { id: "VotA", label: "VotA", zh: "上古山谷" },
  { id: "Del", label: "Del", zh: "谵妄" },
  { id: "Dlvr", label: "Dlvr", zh: "救赎" },
  { id: "promo", label: "Promo", zh: "推广卡" },
  { id: "?", label: "Unmatched", zh: "未能对上系列" },
];

const TABS: { id: TabId; label: string }[] = [
  { id: "overview", label: "总览" },
  { id: "names", label: "卡牌名" },
  { id: "mixed", label: "半成品名" },
  { id: "effects", label: "效果与关键字" },
  { id: "flavor", label: "风味" },
  { id: "ui", label: "界面" },
  { id: "skip", label: "不译 / 范围外" },
];

function matches(text: string, q: string): boolean {
  if (!q) return true;
  return text.toLowerCase().includes(q.toLowerCase());
}

function NameFlow({ names }: { names: readonly string[] }) {
  const theme = useHostTheme();
  if (names.length === 0) return null;
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 6,
      }}
    >
      {names.map((name) => (
        <span
          key={name}
          style={{
            fontSize: 12,
            lineHeight: "18px",
            color: theme.text.primary,
            background: theme.fill.tertiary,
            padding: "2px 8px",
            borderRadius: 4,
          }}
        >
          {name}
        </span>
      ))}
    </div>
  );
}

export default function TranslationGaps() {
  const theme = useHostTheme();
  const [tab, setTab] = useCanvasState<TabId>("tab", "overview");
  const [query, setQuery] = useCanvasState("query", "");
  const q = query.trim();

  const leftoverBySet = DATA.cardnameBySet;
  const leftoverTotal = Object.values(leftoverBySet).reduce(
    (n, list) => n + list.length,
    0,
  );

  return (
    <Stack gap={20}>
      <Stack gap={8}>
        <H1>简体中文覆盖：还缺哪些翻译</H1>
        <Text tone="secondary">
          对照 `loc/zh-Hans/cards.csv`、`lua_cards.csv`、`ui.csv`。牌面运行时走
          LocalizationService 的 `Ascension_Cards`，不走 Lua `display_name`。
          源：2026-08-18 审计。
        </Text>
      </Stack>

      <Row gap={8} wrap>
        {TABS.map((item) => (
          <Pill
            key={item.id}
            active={tab === item.id}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </Pill>
        ))}
      </Row>

      {tab !== "overview" && tab !== "ui" && tab !== "skip" ? (
        <TextInput
          value={query}
          onChange={setQuery}
          placeholder="筛选卡名 / 半成品 / 风味…"
        />
      ) : null}

      {tab === "overview" ? <Overview leftoverTotal={leftoverTotal} /> : null}
      {tab === "names" ? (
        <NamesTab leftoverBySet={leftoverBySet} query={q} />
      ) : null}
      {tab === "mixed" ? (
        <MixedTab query={q} names={DATA.mixedNames} />
      ) : null}
      {tab === "effects" ? <EffectsTab /> : null}
      {tab === "flavor" ? <FlavorTab query={q} /> : null}
      {tab === "ui" ? <UiTab /> : null}
      {tab === "skip" ? <SkipTab /> : null}

      <Text size="small" tone="tertiary">
        颜色：蓝 = 已有汉字，橙 = 中英混杂，红 = 仍全英文。半成品名单独成类，不算「已完成」。
      </Text>
    </Stack>
  );
}

function Overview({ leftoverTotal }: { leftoverTotal: number }) {
  return (
    <Stack gap={20}>
      <Callout tone="warning" title="最大缺口是卡牌文案，不是菜单 Key">
        `Common_Strings` 299 条和 `Common_Ingame` 24
        条已经有中文。教程正文 104 行也有中文。真正没译完的是牌名、风味，以及后期套牌效果里残留的英文单词。
      </Callout>

      <Row gap={24} wrap>
        <Stat value="167" label="牌名已完整中文 / 852" tone="success" />
        <Stat value={String(leftoverTotal)} label="牌名仍全英文（去重）" tone="danger" />
        <Stat value="112" label="牌名半成品（词表拼接）" tone="warning" />
        <Stat value="336" label="风味仍全英文" tone="danger" />
      </Row>

      <Stack gap={8}>
        <H2>牌面字符串覆盖</H2>
        <Text size="small" tone="secondary">
          Source: loc/zh-Hans/cards.csv · 完整中文 / 中英混杂 / 仍全英文
        </Text>
        <UsageBar
          total={852}
          topLeftLabel="CARDNAME 852"
          topRightLabel="167 完整 · 112 半成品 · 571 全英文（含重复键）"
          segments={[
            { id: "done", value: 167, color: "blue" },
            { id: "mixed", value: 112, color: "orange" },
            { id: "en", value: 573, color: "red" },
          ]}
        />
        <UsageBar
          total={839}
          topLeftLabel="EFFECT 839"
          topRightLabel="106 完整 · 731 混杂 · 2 全英文"
          segments={[
            { id: "done", value: 106, color: "blue" },
            { id: "mixed", value: 731, color: "orange" },
            { id: "en", value: 2, color: "red" },
          ]}
        />
        <UsageBar
          total={515}
          topLeftLabel="FLAVOR 515"
          topRightLabel="1 完整 · 178 混杂 · 336 全英文"
          segments={[
            { id: "done", value: 1, color: "blue" },
            { id: "mixed", value: 178, color: "orange" },
            { id: "en", value: 336, color: "red" },
          ]}
        />
      </Stack>

      <H2>建议翻译顺序</H2>
      <Table
        headers={["优先级", "范围", "条数", "原因"]}
        columnAlign={["left", "left", "right", "left"]}
        rows={[
          [
            "P0",
            "CotG 未译牌名 + 核心套风味",
            "Kor / Xeron；约 81 张已有中文名的风味",
            "实体中文存在；牌面现在是中文效果 + 斜体英文风味",
          ],
          [
            "P0",
            "关键字标签残留英文",
            "3",
            "Ongoing 战利品 / Event 战利品 / MULTI-联合",
          ],
          [
            "P0",
            "两条全英文效果",
            "2",
            "Loa, Dream Dragon；Destroyer's Gate",
          ],
          [
            "P1",
            "RotF / SoS / IH 全英文牌名",
            "25 + 39 + 27",
            "早期实体套，官方中文可对照",
          ],
          [
            "P2",
            "其余系列全英文牌名",
            "约 470",
            "机翻名没写上，display_name 仍是英文",
          ],
          [
            "P2",
            "半成品牌名",
            "112",
            "只替换了 灵魂/僧侣/暴君 等词根，专名还在",
          ],
          [
            "P3",
            "效果句去英文",
            "731 + 全部 Fate/Trophy/Energy/Day/Night",
            "机翻留下 honor/you/banish/Dreamscape 等",
          ],
          [
            "P4",
            "后期套风味 + 史诗传奇 Lua 名",
            "240 + 69",
            "无官方中文；Legends 多半不在 Ascension_Cards 表",
          ],
        ]}
        striped
        stickyHeader
      />

      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader>已经有中文草稿、不是缺翻译</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>菜单 `Key_*` 299 条、局内提示 24 条、教程正文 104 行、战斗记录 14 条。</Text>
              <Text>
                截图里的 Music / PLAY ALL / Lobby / Hero
                已写入 `ui_runtime.csv`。若游戏里仍是英文，是运行时没换到新 DLL，不是词条空缺。
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>Lua 表与牌面是两套</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                `lua_cards.csv` 仍有 767 条英文牌名、269 条混杂效果、938 条风味全空。当前 enable 不再把这些写进 Lua 显示字段，避免中英叠字。
              </Text>
              <Text>
                史诗传奇 69 条独特名几乎只存在于 Lua，Localization 表对不上。
              </Text>
            </Stack>
          </CardBody>
        </Card>
      </Grid>
    </Stack>
  );
}

function NamesTab({
  leftoverBySet,
  query,
}: {
  leftoverBySet: Record<string, readonly string[]>;
  query: string;
}) {
  const cotg = DATA.cotgLua.filter((n) => matches(n, query));
  const lgnd = DATA.lgndLua.filter((n) => matches(n, query));
  const unknown = DATA.unknownLua.filter((n) => matches(n, query));
  const promoLuaExtra = DATA.promoLua.filter((n) => matches(n, query));

  return (
    <Stack gap={16}>
      <Callout tone="info" title="弑神编年史几乎齐了">
        Lua 里核心套只剩 <Code>Kor, the Ferromancer</Code> 和{" "}
        <Code>Xeron, Duke of Lies</Code>（含十周年重印）。其余 CotG 名已在 overrides。
      </Callout>

      {cotg.length > 0 ? (
        <Stack gap={8}>
          <H2>弑神编年史未译牌名</H2>
          <NameFlow names={cotg} />
        </Stack>
      ) : null}

      {SETS.map((set) => {
        const names = (leftoverBySet[set.id] ?? []).filter((n) =>
          matches(n, query),
        );
        if (names.length === 0) return null;
        return (
          <CollapsibleSection
            key={set.id}
            title={`${set.zh} · ${set.label}`}
            count={names.length}
            defaultOpen={set.id === "RotF" || Boolean(query)}
          >
            <NameFlow names={names} />
          </CollapsibleSection>
        );
      })}

      {lgnd.length > 0 ? (
        <CollapsibleSection
          title="史诗传奇 · Lua 独有"
          count={lgnd.length}
          defaultOpen={Boolean(query)}
        >
          <Stack gap={8}>
            <Text size="small" tone="secondary">
              不在 CARDNAME_* 表里，或对不上。Boon / Legend / Remnant 前缀仍是英文。
            </Text>
            <NameFlow names={lgnd} />
          </Stack>
        </CollapsibleSection>
      ) : null}

      {unknown.length > 0 ? (
        <CollapsibleSection title="Lua 无系列标记" count={unknown.length}>
          <NameFlow names={unknown} />
        </CollapsibleSection>
      ) : null}

      {promoLuaExtra.length > 0 && !query ? (
        <Text size="small" tone="secondary">
          推广卡 Lua 还多出若干半成品名（Aetherspring 女巫、Puggageddon 等），与 CARDNAME 列表不完全重合。
        </Text>
      ) : null}
    </Stack>
  );
}

function MixedTab({
  query,
  names,
}: {
  query: string;
  names: readonly string[];
}) {
  const filtered = names.filter((n) => matches(n, query));
  return (
    <Stack gap={12}>
      <H2>词表拼接出来的半成品牌名</H2>
      <Text>
        机翻只替换了 glossary 词根：灵魂→之魂、僧侣、暴君、女巫、圣殿武士、使魔、试炼。专名和语法还在英文里，例如{" "}
        <Code>之魂shaper</Code>、<Code>金鱼草Witch</Code>、<Code>Venom 祭司ess</Code>。
      </Text>
      <Text tone="secondary">{filtered.length} / {names.length}</Text>
      <NameFlow names={filtered} />
    </Stack>
  );
}

function EffectsTab() {
  return (
    <Stack gap={16}>
      <H2>仍全英文的效果（2）</H2>
      <Table
        headers={["键", "英文"]}
        rows={[
          ["EFFECT_LOADREAMDRAGON", "Roll the Delirium Die."],
          [
            "EFFECT_DESTROYERSGATE",
            "After a certain amount of time, this transforms into something awesome!",
          ],
        ]}
      />

      <H2>关键字标签残留英文</H2>
      <Table
        headers={["键", "当前文案", "应改"]}
        rows={[
          ["LABEL_TROPHY_ONGOING", "Ongoing 战利品：", "持续战利品："],
          ["LABEL_EVENT_TROPHY", "Event 战利品：", "事件战利品："],
          ["LABEL_MULTIUNITE", "MULTI-联合：", "多重联合："],
        ]}
      />

      <H2>效果句里残留最多的英文词</H2>
      <Text size="small" tone="secondary">
        Source: leftover Latin tokens in EFFECT_* that already contain CJK · 731 rows
      </Text>
      <Table
        headers={["词", "出现次数", "说明"]}
        columnAlign={["left", "right", "left"]}
        rows={[
          ["honor / rune / power", "286 / 249 / 240", "资源名没走图标替换"],
          ["reward", "155", "应并进「奖励：」"],
          ["insight", "85", "洞察 / 元素套资源"],
          ["pay / spend / put / add", "44–22", "动词没译完"],
          ["unite / rally / transform / empower", "28–15", "关键字"],
          ["banish / acquire", "17 / 14", "应是放逐 / 获取"],
          ["Dreamscape", "14", "应是梦境"],
          ["Event / energy", "18 / 15", "事件 / 充能"],
        ]}
        striped
      />

      <H3>连带层（全部中英混杂，没有一行干净）</H3>
      <Table
        headers={["层", "条数", "例子"]}
        rows={[
          ["FATE_*", "25 / 25", "当 this 进入 the 中央牌列…"],
          ["TROPHY_*", "16 / 16", "你可以banish this to 抽一张牌"],
          ["ENERGY_*", "41 / 41", "获得an 额外的 … for 每个 ${ICON_ENERGY}"],
          ["DAY_* / NIGHT_*", "10 + 13", "抽 2 Cards / 获得an 额外的"],
        ]}
      />

      <Callout tone="warning" title="Lua effect_text 是另一份半成品">
        `lua_cards.csv` 还有 269 条混杂效果。当前补丁不再用它画牌面，修 cards.csv 的 EFFECT_* 才进游戏。
      </Callout>
    </Stack>
  );
}

function FlavorTab({ query }: { query: string }) {
  const cjk = DATA.flavorNameCjk.filter((n) => matches(n, query));
  const en = DATA.flavorNameEn.filter((n) => matches(n, query));
  return (
    <Stack gap={16}>
      <Callout tone="danger" title="apply_loc_json 跳过了 FLAVOR_*">
        即使把风味译进 cards.csv，同尺寸写入 Google Sheet 缓存时也会跳过。要上牌面还得改补丁策略，或确认 GetTextByKey 是否读取 FLAVOR 键。Lua 的 flavor_text 938 条全空。
      </Callout>

      <CollapsibleSection
        title="已有中文牌名、风味仍是英文"
        count={cjk.length}
        defaultOpen
      >
        <Stack gap={8}>
          <Text size="small" tone="secondary">
            多为 CotG / 十周年：制表师祭坛、狼萨满、金鱼草、达萨大师等。这就是截图里中文效果下面那行斜体英文。
          </Text>
          <NameFlow names={cjk} />
        </Stack>
      </CollapsibleSection>

      <CollapsibleSection
        title="牌名和风味都还是英文"
        count={en.length}
        defaultOpen={Boolean(query)}
      >
        <NameFlow names={en} />
      </CollapsibleSection>
    </Stack>
  );
}

function UiTab() {
  return (
    <Stack gap={16}>
      <H2>Localization 表：没有空缺</H2>
      <Text>
        `Common_Strings` 299 键、`Common_Ingame` 24 键，`ui.csv` 全部有汉字。教程 104 行正文已译；`TUTORIAL_PROMPT_CONTINUE` / `ENDTURN` 故意保留英文。
      </Text>

      <H2>硬编码英文（表里已有译文）</H2>
      <Text tone="secondary">
        这些不在 `Key_*` 里，所以 Harmony 换键名换不到。已写入 `ui_runtime.csv` 做 TMP 精确替换。游戏里若仍显示英文，先完全退出再拷插件。
      </Text>
      <Table
        headers={["英文", "已有译文", "出现位置"]}
        rows={[
          ["Music", "音乐", "设置"],
          ["Sound Effects", "音效", "设置"],
          ["Cultist Screams", "邪教徒惨叫", "设置"],
          ["PLAY ALL / Play All", "全部打出", "出牌"],
          ["Lobby", "大厅", "底栏"],
          ["Back", "返回", "列表"],
          ["Offline Games", "离线对局", "标题"],
          ["LOG / Log", "记录", "对局"],
          ["Player", "玩家", "无编号栏位"],
          ["Hero / Construct / Monster", "英雄 / 神器 / 怪物", "卡牌类型"],
          ["Version:", "版本：", "关于"],
          ["Always Available", "始终可用", "常备牌"],
          ["Center Row", "中央牌列", "区域名"],
          ["Enlightened / Lifebound / Mechana", "启迪 / 生命 / 机械", "筛选"],
          ["各扩展英文套名", "glossary 已有", "图鉴筛选"],
        ]}
        striped
      />

      <H2>界面上还可能漏掉、词表未收录</H2>
      <Table
        headers={["字符串", "状态"]}
        rows={[
          ["AI 难度 Easy / Hard / Expert 等具体档位", "只有 Key_AIDifficulty「AI 难度」，档位名未提取"],
          ["内购商品标题 / 价格旁的商店文案", "走商店 SDK，不在三张 loc 表"],
          ["制作人员名单", "专名，未提取"],
          ["荣誉池数字旁的短标签（若不是 Honor）", "未从 TMP 再 dump 一轮"],
          ["规则书页", "位图，不是字符串"],
          ["设置页标题错成「按键绑定」", "键用错（Key_KeyBindings vs Key_Settings），不是缺译"],
        ]}
      />
    </Stack>
  );
}

function SkipTab() {
  return (
    <Stack gap={16}>
      <H2>故意保持英文</H2>
      <Table
        headers={["内容", "原因"]}
        rows={[
          ["ASCENSION DECKBUILDING GAME 标题", "商标 / Logo"],
          ["${CLICK_C} to Continue", "点击热区绑定 CLICK 标记"],
          ["${CLICK_C} the End Turn button", "同上"],
          ["Lua card_name 标识符", "内部 ID，对局逻辑用"],
          ["{0} / %s / %d / ${ICON_*} / <sprite>", "格式令牌"],
          ["通讯里的 Stone Blade", "公司名"],
          ["版本号 2.5.3.531", "数字本身"],
        ]}
      />

      <H2>范围外</H2>
      <Table
        headers={["内容", "原因"]}
        rows={[
          ["规则书扫描页", "图，不是 TextAsset"],
          ["卡图上的英文（若烧进贴图）", "要重绘"],
          ["Steam 好友 / 成就 / 叠层", "Steam 客户端"],
          ["语音", "无中文音轨"],
          ["繁体", "简体冻结后再转"],
        ]}
      />
    </Stack>
  );
}
'''

tsx = tsx.replace(
    """  const theme = useHostTheme();
  const [tab, setTab] = useCanvasState<TabId>("tab", "overview");""",
    """  const [tab, setTab] = useCanvasState<TabId>("tab", "overview");""",
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(tsx, encoding="utf-8")
print("wrote", OUT, "chars", len(tsx))
