<template>
  <div class="container handbook-page">
    <div class="page-head">
      <div>
        <div class="kicker">Handbook & Roadmap</div>
        <h1 class="display">算法新手村与速查手册</h1>
      </div>
      <div class="head-stats">
        <div class="stat">
          <span class="num accent">9</span>
          <span class="lbl">基础扫盲条目</span>
        </div>
        <div class="stat">
          <span class="num">7</span>
          <span class="lbl">必背模板</span>
        </div>
        <div class="stat">
          <span class="num">Py / C++</span>
          <span class="lbl">双语对齐</span>
        </div>
      </div>
    </div>

    <!-- 导航选项卡：iOS 分段器，移动端可横向滑动 -->
    <div class="handbook-tabs-wrap">
      <div class="segmented handbook-tabs">
        <button :class="{ active: currentTab === 'basics' }" @click="currentTab = 'basics'">
          零基础扫盲
        </button>
        <button :class="{ active: currentTab === 'links' }" @click="currentTab = 'links'">
          顶流开源笔记导航
        </button>
        <button :class="{ active: currentTab === 'complexity' }" @click="currentTab = 'complexity'">
          数据规模与复杂度速查
        </button>
        <button :class="{ active: currentTab === 'syntax' }" @click="currentTab = 'syntax'">
          Python ⇋ C++ 语法对齐
        </button>
        <button :class="{ active: currentTab === 'templates' }" @click="currentTab = 'templates'">
          7 大核心算法通用模板
        </button>
      </div>
    </div>

    <!-- 模块 0: 零基础扫盲 -->
    <section v-if="currentTab === 'basics'" class="handbook-section">
      <div class="card rule-card">
        <h2>刷题入门路线（先建立手感，再上强度）</h2>
        <ol class="basics-roadmap">
          <li><strong>数组 + 哈希表</strong>：最简单也最高频，先学会「以空间换时间」的思考方式（如两数之和）。</li>
          <li><strong>双指针 + 链表</strong>：体会「原地操作」和指针移动的套路（反转链表、合并有序链表）。</li>
          <li><strong>栈与队列</strong>：理解 LIFO / FIFO，为后面的 BFS、单调栈打底（有效括号、每日温度）。</li>
          <li><strong>二叉树 + 递归</strong>：前中后序遍历是最好的递归思维训练场，卡住就先背遍历框架。</li>
          <li><strong>二分 / 滑动窗口 / 回溯</strong>：中等题三大套路，配合右侧「模板」页直接背骨架。</li>
          <li><strong>动态规划 + 图</strong>：放到最后，前面攒够手感再来啃。</li>
        </ol>
        <p class="rule-intro rule-flush">
          每道题先想暴力解，再问自己「哪一步在重复劳动」，优化的方向往往就藏在这个答案里。题解看不懂很正常——去「背题」页把对应模板先背下来，回头再看就通了。
        </p>
      </div>

      <!-- ACM 模式 vs 力扣模式扫盲 -->
      <div class="card rule-card rule-card-gap">
        <h2>ACM 模式 vs 力扣模式（刷题页可切换）</h2>
        <p class="rule-intro">
          力扣上你只需要写一个函数，平台帮你处理输入输出；而<strong>校招笔试（牛客、各厂自家 OJ）几乎全是 ACM 模式</strong>——自己从标准输入读数据、把答案打印到标准输出。本站两种模式都支持：编辑器工具栏可切换，草稿分开保存。建议笔试前用 ACM 模式练手。
        </p>
        <div class="table-wrap">
          <table class="handbook-table">
            <thead>
              <tr>
                <th></th>
                <th>力扣模式（函数式）</th>
                <th>ACM 模式（校招笔试）</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="bold">你要写什么</td>
                <td>只写 <code>class Solution</code> 里的函数体</td>
                <td>完整的程序：<code>main</code> + 读输入 + 解题 + 打印输出</td>
              </tr>
              <tr>
                <td class="bold">输入</td>
                <td>平台把参数直接传给你的函数</td>
                <td>自己读 stdin：<code>sys.stdin.read()</code> / <code>cin</code></td>
              </tr>
              <tr>
                <td class="bold">输出</td>
                <td>return 返回值即可</td>
                <td>自己 print / cout，格式必须和题面完全一致</td>
              </tr>
              <tr>
                <td class="bold">常见翻车点</td>
                <td>几乎没有</td>
                <td>输出多了空格/换行、读入没转 int、大数据量输入超时（需极速 I/O）</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3 class="rule-h3">同一道「两数之和」，两种模式的写法对比</h3>
        <div class="io-templates-grid">
          <div class="io-temp-box">
            <div class="io-temp-head">
              <span>力扣模式（只写函数）</span>
              <button class="btn btn-xs" @click="copy(LC_STYLE_CODE)">复制</button>
            </div>
            <pre class="mono io-pre">{{ LC_STYLE_CODE }}</pre>
          </div>
          <div class="io-temp-box">
            <div class="io-temp-head">
              <span>ACM 模式（笔试提交格式）</span>
              <button class="btn btn-xs" @click="copy(ACM_STYLE_CODE)">复制</button>
            </div>
            <pre class="mono io-pre">{{ ACM_STYLE_CODE }}</pre>
          </div>
        </div>
        <p class="rule-intro rule-after">
          力扣模式下模板签名与力扣一致（<code>class Solution</code> / 设计类），评测仍用本题 ACM 用例，由平台代读入。ACM 模式大数据量输入请用「语法对齐」页底部的极速 I/O 模板防 TLE。
        </p>
      </div>

      <h3 class="basics-sub-title">核心数据结构与基础手法扫盲（点卡片看用法代码）</h3>
      <div class="curated-grid">
        <div
          v-for="(d, idx) in BASICS_DS"
          :key="d.name"
          class="card curated-card ds-card"
          :class="{ selected: selectedDsIdx === idx }"
          @click="selectedDsIdx = idx"
        >
          <div class="curated-top">
            <span class="curated-badge">{{ d.badge }}</span>
            <span class="curated-star">{{ d.cost }}</span>
          </div>
          <h3 class="curated-title">{{ d.name }}</h3>
          <p class="curated-desc">{{ d.what }}</p>
          <div class="curated-footer">
            <span class="curated-tag">{{ d.usage }}</span>
            <span class="curated-link">
              {{ selectedDsIdx === idx ? '收起' : '看用法' }}
              <AppIcon name="chevron-down" :size="13" class="fold-icon" :class="{ open: selectedDsIdx === idx }" />
            </span>
          </div>
        </div>
      </div>

      <!-- 数据结构详情：介绍 + 基础用法代码 -->
      <div class="card rule-card ds-detail" v-if="currentDs">
        <div class="tpl-header">
          <div>
            <h2>{{ currentDs.name }} · 基础用法</h2>
            <p class="tpl-desc">{{ currentDs.intro }}</p>
          </div>
          <div class="tpl-actions">
            <div class="segmented">
              <button :class="{ active: tplLang === 'python3' }" @click="tplLang = 'python3'">Python 3</button>
              <button :class="{ active: tplLang === 'cpp' }" @click="tplLang = 'cpp'">C++ 20</button>
            </div>
            <button class="btn btn-sm btn-primary" @click="copy(currentDs[tplLang])">复制代码</button>
          </div>
        </div>
        <div class="tpl-code-block">
          <pre class="mono">{{ currentDs[tplLang] }}</pre>
        </div>
      </div>

      <div class="card rule-card rule-card-gap">
        <h2>大 O 复杂度直觉（越大越慢，从左到右恶化）</h2>
        <p class="rule-intro">
          大 O 描述的是「数据量 n 变大时，运行时间增长得多快」。面试中说出复杂度级别，比背出精确数字重要得多：
        </p>
        <div class="table-wrap">
          <table class="handbook-table">
            <thead>
              <tr>
                <th>复杂度</th>
                <th>名字</th>
                <th>代表操作</th>
                <th>一句话直觉</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in BIGO_LEVELS" :key="r.big_o">
                <td class="mono bold accent-cell">{{ r.big_o }}</td>
                <td>{{ r.name }}</td>
                <td>{{ r.typical }}</td>
                <td class="muted">{{ r.intuition }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="rule-intro rule-after">
          拿到题先看数据范围 n，再对照「数据规模与复杂度速查」页倒推允许的复杂度——这是面试秒出思路的关键习惯。
        </p>
      </div>
    </section>

    <!-- 模块 1: 顶流开源笔记推荐 -->
    <section v-if="currentTab === 'links'" class="handbook-section">
      <div class="curated-grid">
        <a
          v-for="item in CURATED_RESOURCES"
          :key="item.title"
          :href="item.url"
          target="_blank"
          rel="noopener"
          class="card curated-card"
        >
          <div class="curated-top">
            <span class="curated-badge">{{ item.badge }}</span>
            <span class="curated-star">{{ item.stars }}</span>
          </div>
          <h3 class="curated-title">{{ item.title }}</h3>
          <p class="curated-desc">{{ item.desc }}</p>
          <div class="curated-footer">
            <span class="curated-tag">{{ item.tag }}</span>
            <span class="curated-link">前往阅读 <AppIcon name="arrow-right" :size="13" class="ext-icon" /></span>
          </div>
        </a>
      </div>
    </section>

    <!-- 模块 2: 数据规模倒推法则 -->
    <section v-if="currentTab === 'complexity'" class="handbook-section">
      <div class="card rule-card">
        <h2>数据规模与时间复杂度倒推法则（面试秒出思路）</h2>
        <p class="rule-intro">
          在算法面试和 OJ 中，<strong>看一眼题目给出的数据范围 n，就能直接倒推本题允许的理论最大时间复杂度</strong>（以单核 1 秒运算 10⁸ 次为基准）：
        </p>

        <div class="table-wrap">
          <table class="handbook-table">
            <thead>
              <tr>
                <th>数据规模 $n$</th>
                <th>允许的最大时间复杂度</th>
                <th>常见算法与思路提示</th>
                <th>典型面试题型</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in COMPLEXITY_RULES" :key="r.range">
                <td class="mono bold accent-cell">{{ r.range }}</td>
                <td class="mono bold">{{ r.complexity }}</td>
                <td>{{ r.algorithms }}</td>
                <td class="muted">{{ r.examples }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 模块 3: Python 3 ⇋ C++ 20 语法对齐 -->
    <section v-if="currentTab === 'syntax'" class="handbook-section">
      <div class="card rule-card">
        <h2>Python 3 ⇋ C++ 20 高频数据结构与常用内置方法对照</h2>
        <p class="rule-intro">
          结对刷题或双语学习时随手查阅，涵盖竞赛与面试中最常用的标准库操作：
        </p>

        <div class="table-wrap">
          <table class="handbook-table">
            <thead>
              <tr>
                <th>场景 / 数据结构</th>
                <th>Python 3 写法</th>
                <th>C++ 20 (STL) 写法</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in SYNTAX_ALIGN" :key="s.name">
                <td class="bold">{{ s.name }}</td>
                <td class="mono code-cell">{{ s.python }}</td>
                <td class="mono code-cell">{{ s.cpp }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ACM 模式极速 I/O 模板 -->
        <h3 class="rule-h3">ACM 模式极速 I/O 输入输出防 TLE 模板</h3>
        <div class="io-templates-grid">
          <div class="io-temp-box">
            <div class="io-temp-head">
              <span>Python 3 极速读取</span>
              <button class="btn btn-xs" @click="copy(PY_IO_CODE)">复制</button>
            </div>
            <pre class="mono io-pre">{{ PY_IO_CODE }}</pre>
          </div>

          <div class="io-temp-box">
            <div class="io-temp-head">
              <span>C++ 20 关同步极速 I/O</span>
              <button class="btn btn-xs" @click="copy(CPP_IO_CODE)">复制</button>
            </div>
            <pre class="mono io-pre">{{ CPP_IO_CODE }}</pre>
          </div>
        </div>
      </div>
    </section>

    <!-- 模块 4: 7 大核心算法通用骨架模板 -->
    <section v-if="currentTab === 'templates'" class="handbook-section">
      <div class="template-layout">
        <!-- 侧边模板列表 -->
        <div class="template-menu card">
          <button
            v-for="(t, idx) in TEMPLATES"
            :key="t.title"
            class="template-menu-item"
            :class="{ active: selectedTemplateIdx === idx }"
            @click="selectedTemplateIdx = idx"
          >
            <span class="tpl-idx">#0{{ idx + 1 }}</span>
            <span class="tpl-name">{{ t.title }}</span>
          </button>
        </div>

        <!-- 模板代码展示区 -->
        <div class="template-content card" v-if="currentTemplate">
          <div class="tpl-header">
            <div>
              <h2>{{ currentTemplate.title }}</h2>
              <p class="tpl-desc">{{ currentTemplate.desc }}</p>
            </div>
            <div class="tpl-actions">
              <div class="segmented">
                <button
                  :class="{ active: tplLang === 'python3' }"
                  @click="tplLang = 'python3'"
                >
                  Python 3
                </button>
                <button
                  :class="{ active: tplLang === 'cpp' }"
                  @click="tplLang = 'cpp'"
                >
                  C++ 20
                </button>
              </div>
              <button class="btn btn-sm btn-primary" @click="copy(currentTemplate[tplLang])">
                复制完整模板
              </button>
            </div>
          </div>

          <div class="tpl-code-block">
            <pre class="mono">{{ currentTemplate[tplLang] }}</pre>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useToast } from '../stores/toast'
import { useLangPref } from '../stores/pref'
import { copyToClipboard } from '../clipboard'
import AppIcon from '../components/AppIcon.vue'

const toast = useToast()
const { langPref } = useLangPref()
const currentTab = ref<'basics' | 'links' | 'complexity' | 'syntax' | 'templates'>('basics')
const selectedTemplateIdx = ref(0)
const selectedDsIdx = ref(0)
const currentDs = computed(() => BASICS_DS[selectedDsIdx.value])
const tplLang = ref<'python3' | 'cpp'>(langPref.value)

watch(langPref, (newLang) => {
  tplLang.value = newLang
})

async function copy(text: string) {
  const ok = await copyToClipboard(text)
  if (ok) toast.success('模板代码已复制到剪贴板')
  else toast.error('复制失败，请手动选择复制')
}

const BASICS_DS = [
  {
    name: '数组 Array',
    badge: '入门第一课',
    cost: '访问 O(1)',
    what: '一块连续内存，按下标直接取元素。插入/删除中间元素要整体搬移，是 O(n)。',
    usage: '几乎所有题的起点',
    intro: '刷题里 80% 的输入都是数组。必须熟练的四件事：遍历、排序、切片、前缀和（prefix[i] 表示前 i 个元素之和，区间求和从 O(n) 降到 O(1)）。',
    python3: `nums = [3, 1, 2]
nums.append(4)      # 尾部追加，O(1)
nums.sort()         # 原地升序，O(n log n)
print(nums[0])      # 按下标访问，O(1)

# 前缀和：区间 [l, r) 求和只需 prefix[r] - prefix[l]
prefix = [0]
for x in nums:
    prefix.append(prefix[-1] + x)
print(prefix[2] - prefix[0])   # 前 2 个元素之和`,
    cpp: `#include <vector>
#include <algorithm>
using namespace std;

vector<int> nums = {3, 1, 2};
nums.push_back(4);                   // 尾部追加，O(1)
sort(nums.begin(), nums.end());      // 升序，O(n log n)

// 前缀和：区间 [l, r) 求和只需 prefix[r] - prefix[l]
vector<int> prefix(nums.size() + 1, 0);
for (int i = 0; i < (int)nums.size(); ++i)
    prefix[i + 1] = prefix[i] + nums[i];`,
  },
  {
    name: '链表 Linked List',
    badge: '指针基本功',
    cost: '插入 O(1)',
    what: '节点之间用指针串联，不连续存储。改指针就能插入删除，但想找第 k 个只能从头走。',
    usage: '反转 · 环检测 · 合并',
    intro: 'OJ 会直接给你 ListNode 定义，你要做的只是操作 next 指针。做链表题的铁律：动手画指针变化图，别在脑子里空想。',
    python3: `class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

# 遍历整条链表
cur = head
while cur:
    print(cur.val)
    cur = cur.next

# 在 cur 后面插入新节点 node
node.next = cur.next
cur.next = node`,
    cpp: `struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

// 遍历整条链表
for (ListNode* cur = head; cur; cur = cur->next)
    cout << cur->val << " ";

// 在 cur 后面插入新节点 node
node->next = cur->next;
cur->next = node;`,
  },
  {
    name: '栈 Stack',
    badge: 'LIFO',
    cost: '进出 O(1)',
    what: '后进先出，只能从栈顶放取。遇到「最近匹配」「成对消除」类问题先想它。',
    usage: '括号匹配 · 单调栈',
    intro: '栈顶永远在「末尾」。Python 直接用 list 当栈（append/pop 都是 O(1)）；C++ 用 stack 适配器，注意 pop() 不返回值，要先 top()。',
    python3: `stack = []          # list 就是栈
stack.append(x)     # 入栈（栈顶在末尾）
top = stack[-1]     # 看栈顶，不弹出
stack.pop()         # 弹出栈顶
if not stack:       # 判空
    print("栈空了")

# 经典：有效括号
pairs = {')': '(', ']': '[', '}': '{'}
for ch in s:
    if ch in pairs.values():
        stack.append(ch)
    elif not stack or stack.pop() != pairs[ch]:
        return False`,
    cpp: `#include <stack>
using namespace std;

stack<int> st;
st.push(x);      // 入栈
st.top();        // 看栈顶，不弹出
st.pop();        // 弹出（无返回值！先 top 再 pop）
st.empty();      // 判空

// 单调栈套路：维护一个单调递减栈
// while (!st.empty() && nums[i] > st.top()) st.pop();`,
  },
  {
    name: '队列 Queue',
    badge: 'FIFO',
    cost: '进出 O(1)',
    what: '先进先出，队尾进队头出。BFS 层序遍历的标配；双端队列（Deque）可两头操作。',
    usage: 'BFS · 层序遍历',
    intro: '普通队列一头进一头出；双端队列 deque 两头都能 O(1) 操作，滑动窗口最大值靠它。Python 千万别用 list.pop(0) 当队列——那是 O(n)。',
    python3: `from collections import deque

q = deque()
q.append(x)       # 队尾进
q.popleft()       # 队头出，O(1)

# BFS 骨架
q = deque([start])
while q:
    node = q.popleft()
    for nxt in neighbors(node):
        q.append(nxt)`,
    cpp: `#include <queue>
#include <deque>
using namespace std;

queue<int> q;
q.push(x);       // 队尾进
q.front();       // 看队头
q.pop();         // 队头出（无返回值）

// 双端队列：滑动窗口最大值的核心
deque<int> dq;
dq.push_back(x); dq.pop_front();`,
  },
  {
    name: '哈希表 Hash Map',
    badge: '空间换时间',
    cost: '查找 O(1)',
    what: 'key → value 的映射，查一个值平均只要 O(1)。「边遍历边记录见过什么」是它的灵魂。',
    usage: '两数之和 · 计数去重',
    intro: '凡是「判断某个值之前见没见过」「统计出现次数」的题，哈希表几乎是最优解。Python 的 Counter/defaultdict 能省掉大量判空代码。',
    python3: `from collections import Counter, defaultdict

cnt = Counter(nums)        # 一行统计每个元素出现次数
seen = set()               # 只要去重/判存在用 set
seen.add(x)
if x in seen: ...          # O(1) 判存在

mp = defaultdict(int)      # 取值不存在时默认 0，不用判空
for x in nums:
    mp[x] += 1`,
    cpp: `#include <unordered_map>
#include <unordered_set>
using namespace std;

unordered_map<int, int> cnt;
for (int x : nums) cnt[x]++;        // 不存在自动初始化为 0

unordered_set<int> seen;
seen.insert(x);
if (seen.count(x)) { /* 存在 */ }   // O(1) 判存在`,
  },
  {
    name: '堆 Heap / 优先队列',
    badge: 'Top K 神器',
    cost: '取顶 O(log n)',
    what: '一棵能自动维持最大/最小值在堆顶的二叉树，不用全排序就能反复取极值。',
    usage: 'Top K · 合并有序流',
    intro: 'Python 的 heapq 是小顶堆，要取最大就把元素取负再入堆；C++ 的 priority_queue 默认大顶堆。Top K 问题用大小为 K 的堆，把 O(n log n) 降到 O(n log k)。',
    python3: `import heapq

h = []
heapq.heappush(h, x)     # 入堆，O(log n)
smallest = heapq.heappop(h)   # 弹出最小值
heapq.heapify(nums)      # 原地建堆，O(n)

# 大顶堆技巧：存负数
heapq.heappush(h, -x)
largest = -heapq.heappop(h)`,
    cpp: `#include <queue>
using namespace std;

// 默认大顶堆
priority_queue<int> pq;
pq.push(x);          // 入堆，O(log n)
pq.top();            // 看堆顶（最大值）
pq.pop();            // 弹出堆顶

// 小顶堆
priority_queue<int, vector<int>, greater<int>> minPq;`,
  },
  {
    name: '二叉树 Binary Tree',
    badge: '递归训练场',
    cost: '遍历 O(n)',
    what: '每个节点最多两个孩子。前/中/后序遍历就是三种递归时机；二叉搜索树满足左小右大。',
    usage: '遍历 · 最近公共祖先',
    intro: '树的题 90% 是递归：先写「递」下去的终止条件，再想「归」回来时组装什么。前中后序唯一的区别只是「处理当前节点」这行代码的位置。',
    python3: `class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def traverse(root):
    if not root:          # 递归出口：空节点直接返回
        return
    # print(root.val)     # 写在这 = 前序
    traverse(root.left)
    # print(root.val)     # 写在这 = 中序
    traverse(root.right)
    # print(root.val)     # 写在这 = 后序`,
    cpp: `struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

void traverse(TreeNode* root) {
    if (!root) return;    // 递归出口
    traverse(root->left); // 处理语句放哪，就是哪种序
    traverse(root->right);
}`,
  },
  {
    name: '图 Graph',
    badge: '关系网络',
    cost: '视算法而定',
    what: '节点加边的关系网，树是特殊的不带环的图。最短路径、拓扑排序、并查集都围绕它展开。',
    usage: '课程表 · 岛屿数量',
    intro: '刷题中图一般用邻接表表示：g[i] 存 i 的所有邻居。网格题（岛屿数量）本身就是隐式的图——上下左右四个方向就是边。',
    python3: `from collections import defaultdict, deque

# 建邻接表：edges = [[0,1],[1,2],...]
g = defaultdict(list)
for u, v in edges:
    g[u].append(v)
    g[v].append(u)        # 无向图加双向

# BFS 最短路骨架
dist = {start: 0}
q = deque([start])
while q:
    u = q.popleft()
    for v in g[u]:
        if v not in dist:
            dist[v] = dist[u] + 1
            q.append(v)`,
    cpp: `#include <vector>
#include <queue>
using namespace std;

// 建邻接表
vector<vector<int>> g(n);
for (auto& e : edges) {
    g[e[0]].push_back(e[1]);
    g[e[1]].push_back(e[0]);   // 无向图加双向
}

// BFS 骨架
vector<int> dist(n, -1);
queue<int> q;
dist[0] = 0; q.push(0);
while (!q.empty()) {
    int u = q.front(); q.pop();
    for (int v : g[u])
        if (dist[v] == -1) { dist[v] = dist[u] + 1; q.push(v); }
}`,
  },
  {
    name: '双指针 Two Pointers',
    badge: '基础手法',
    cost: '一趟 O(n)',
    what: '两个指针在数组上协同移动：对撞（两头往中间）或快慢（同向不同速）。把双重循环压成一趟。',
    usage: '三数之和 · 回文判断',
    intro: '双指针不是数据结构，是使用频率最高的基础手法。数组有序时想对撞指针（一头一尾向中间夹），判回文/去重/环形链表想快慢指针。',
    python3: `# 对撞指针：有序数组找两数之和
left, right = 0, len(nums) - 1
while left < right:
    s = nums[left] + nums[right]
    if s == target:
        break
    elif s < target:
        left += 1    # 偏小，左指针右移
    else:
        right -= 1   # 偏大，右指针左移

# 快慢指针：判链表有环
# slow = slow.next; fast = fast.next.next
# 若相遇则有环`,
    cpp: `// 对撞指针：有序数组找两数之和
int left = 0, right = (int)nums.size() - 1;
while (left < right) {
    int s = nums[left] + nums[right];
    if (s == target) break;
    else if (s < target) ++left;   // 偏小，左指针右移
    else --right;                  // 偏大，右指针左移
}

// 快慢指针：判链表有环
// slow = slow->next; fast = fast->next->next;
// 若相遇则有环`,
  },
]

const BIGO_LEVELS = [
  { big_o: 'O(1)', name: '常数', typical: '哈希表查 key、数组按下标访问', intuition: '数据再涨也不慌' },
  { big_o: 'O(log n)', name: '对数', typical: '二分查找', intuition: '每步砍掉一半，越砍越快' },
  { big_o: 'O(n)', name: '线性', typical: '把数组完整遍历一遍', intuition: '中规中矩的底线' },
  { big_o: 'O(n log n)', name: '线性对数', typical: '快排 / 归并 / 堆排序', intuition: '比较排序的天花板' },
  { big_o: 'O(n²)', name: '平方', typical: '双重循环两两枚举', intuition: 'n 过千就要警惕' },
  { big_o: 'O(2ⁿ) / O(n!)', name: '指数 / 阶乘', typical: '回溯爆搜、全排列', intuition: '只在 n ≤ 20 左右能用' },
]

const CURATED_RESOURCES = [
  {
    title: 'Hello 算法 (Hello Algo)',
    url: 'https://www.hello-algo.com/',
    badge: '动画图解顶流',
    stars: '100k+ Stars',
    desc: '全网零基础入门最友好的开源算法教程！动画生动展示数据结构与算法执行全过程，覆盖 Python/C++/Java/Go 全语言。',
    tag: '零基础 · 图解 · 交互式学习',
  },
  {
    title: '代码随想录 (Programmer Carl)',
    url: 'https://programmercarl.com/',
    badge: '校招面试必读',
    stars: '50k+ Stars',
    desc: '国内程序员校招刷题人手一本的求职宝典！按专题（二叉树、动态规划五步法、回溯、双指针）归纳总结通用做题套路。',
    tag: '专题刷题 · 模板总结 · 面试高频',
  },
  {
    title: 'labuladong 的算法笔记',
    url: 'https://labuladong.online/',
    badge: '算法框架思维',
    stars: '120k+ Stars',
    desc: '主打手把手拆解通用算法框架，将滑动窗口、二分查找、二叉树遍历框架化，掌握一个框架轻松秒杀一整类算法题。',
    tag: '框架思维 · 递归模式 · 核心模板',
  },
  {
    title: 'OI Wiki 算法竞赛百科',
    url: 'https://oi-wiki.org/',
    badge: '权威算法百科',
    stars: '30k+ Stars',
    desc: '由算法竞赛圈共同维护的最权威中文算法百科全书，数学推导严谨，涵盖从基础数据结构到高级图论算法的全部细节。',
    tag: '百科全书 · 严谨推导 · 竞赛进阶',
  },
]

const COMPLEXITY_RULES = [
  {
    range: 'n ≤ 10 ~ 20',
    complexity: 'O(2ⁿ) 或 O(n!)',
    algorithms: '指数级回溯爆搜、全排列枚举、状态压缩 DP',
    examples: 'N 皇后、全排列、子集划分、旅行商问题',
  },
  {
    range: 'n ≤ 100',
    complexity: 'O(n³)',
    algorithms: '三重循环枚举、Floyd 多源最短路、区间 DP',
    examples: '矩阵连乘、戳气球、多源最短路径',
  },
  {
    range: 'n ≤ 1,000',
    complexity: 'O(n²)',
    algorithms: '双重循环、二维动态规划、稠密图 Dijkstra',
    examples: '最长公共子序列、编辑距离、打家劫舍 II',
  },
  {
    range: 'n ≤ 10⁵ ~ 10⁶',
    complexity: 'O(n log n) 或 O(n)',
    algorithms: '快速排序/归并排序、堆/二分、双指针、滑动窗口、单调栈/单调队列',
    examples: '三数之和、接雨水、滑动窗口最大值、最长上升子序列',
  },
  {
    range: 'n ≥ 10⁹',
    complexity: 'O(log n) 或 O(1)',
    algorithms: '二分查找、快速幂、数论公式推导、位运算',
    examples: 'Pow(x, n)、两数相除、只出现一次的数字',
  },
]

const SYNTAX_ALIGN = [
  {
    name: '双端队列 (Deque)',
    python: 'from collections import deque\nq = deque()\nq.append(x); q.popleft()',
    cpp: '#include <deque>\nstd::deque<int> q;\nq.push_back(x); q.pop_front();',
  },
  {
    name: '大顶堆 (Max Heap)',
    python: 'import heapq\nh = []\nheapq.heappush(h, -x)\nval = -heapq.heappop(h)',
    cpp: '#include <queue>\nstd::priority_queue<int> pq;\npq.push(x);\nval = pq.top(); pq.pop();',
  },
  {
    name: '小顶堆 (Min Heap)',
    python: 'import heapq\nh = []\nheapq.heappush(h, x)\nval = heapq.heappop(h)',
    cpp: 'std::priority_queue<int, vector<int>, greater<int>> pq;\npq.push(x);\nval = pq.top(); pq.pop();',
  },
  {
    name: '哈希计数器 (Counter)',
    python: 'from collections import Counter\ncnt = Counter(nums)\n# 自动计数',
    cpp: '#include <unordered_map>\nstd::unordered_map<int, int> cnt;\nfor (int x : nums) cnt[x]++;',
  },
  {
    name: '二分查找 (下界 ≥ x)',
    python: 'import bisect\nidx = bisect.bisect_left(nums, target)',
    cpp: '#include <algorithm>\nauto it = std::lower_bound(nums.begin(), nums.end(), target);\nint idx = it - nums.begin();',
  },
  {
    name: '自定义排序 (降序/多键)',
    python: 'nums.sort(key=lambda x: (x[0], -x[1]))',
    cpp: 'std::sort(nums.begin(), nums.end(), [](const auto& a, const auto& b) {\n    return a[0] != b[0] ? a[0] < b[0] : a[1] > b[1];\n});',
  },
]

const LC_STYLE_CODE = `# 力扣模式：平台调用你的函数，不需要碰输入输出
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for i, x in enumerate(nums):
            if target - x in seen:
                return [seen[target - x], i]
            seen[x] = i`

const ACM_STYLE_CODE = `# ACM 模式：自己读 stdin、打印 stdout
# 输入约定：第一行 n 和 target，第二行 n 个整数
# 输出约定：一行两个下标，空格分隔
import sys

def main():
    data = sys.stdin.read().split()
    n, target = int(data[0]), int(data[1])
    nums = [int(x) for x in data[2:2 + n]]

    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            print(seen[target - x], i)   # 直接打印答案
            return
        seen[x] = i

if __name__ == "__main__":
    main()`

const PY_IO_CODE = `import sys

def solve():
    # 一次性读入所有数据，极速切片
    input_data = sys.stdin.read().split()
    if not input_data:
        return
    
    # 示例：读入一个整数 n
    it = iter(input_data)
    n = int(next(it))
    nums = [int(next(it)) for _ in range(n)]
    
    # 业务解题逻辑
    res = sum(nums)
    print(res)

if __name__ == "__main__":
    solve()`

const CPP_IO_CODE = `#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
using namespace std;

int main() {
    // 关闭同步流加速，避免大规模输入 TLE
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (cin >> n) {
        vector<int> nums(n);
        for (int i = 0; i < n; ++i) {
            cin >> nums[i];
        }
        // 业务解题逻辑
        long long res = 0;
        for (int x : nums) res += x;
        cout << res << "\\n";
    }
    return 0;
}`

const TEMPLATES = [
  {
    title: '二分查找 (Binary Search)',
    desc: '左右闭区间统一模板，杜绝死循环与边界越界错误。',
    python3: `def binary_search(nums: list[int], target: int) -> int:
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1  # 未找到`,
    cpp: `int binarySearch(const vector<int>& nums, int target) {
    int left = 0, right = static_cast<int>(nums.size()) - 1;
    while (left <= right) {
        int mid = left + (right - left) / 2;
        if (nums[mid] == target) return mid;
        else if (nums[mid] < target) left = mid + 1;
        else right = mid - 1;
    }
    return -1;
}`,
  },
  {
    title: '滑动窗口 (Sliding Window)',
    desc: '双指针快慢指针同向移动，维护区间动态合法状态。',
    python3: `def sliding_window(s: str) -> int:
    from collections import defaultdict
    window = defaultdict(int)
    left = right = 0
    ans = 0
    
    while right < len(s):
        c = s[right]
        right += 1
        window[c] += 1
        
        # 当窗口需要收缩时
        while window[c] > 1: # 满足收缩条件
            d = s[left]
            left += 1
            window[d] -= 1
            
        ans = max(ans, right - left)
    return ans`,
    cpp: `int slidingWindow(const string& s) {
    unordered_map<char, int> window;
    int left = 0, right = 0, ans = 0;
    while (right < s.size()) {
        char c = s[right++];
        window[c]++;
        
        while (window[c] > 1) {
            char d = s[left++];
            window[d]--;
        }
        ans = max(ans, right - left);
    }
    return ans;
}`,
  },
  {
    title: '二叉树递归遍历 (Tree Traversal)',
    desc: '标准前/中/后序统一递归框架与叶节点递归出口。',
    python3: `class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def traverse(root: TreeNode | None):
    if not root:
        return
    # 前序位置: print(root.val)
    traverse(root.left)
    # 中序位置: print(root.val)
    traverse(root.right)
    # 后序位置: print(root.val)`,
    cpp: `struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

void traverse(TreeNode* root) {
    if (!root) return;
    // 前序位置
    traverse(root->left);
    // 中序位置
    traverse(root->right);
    // 后序位置
}`,
  },
  {
    title: '回溯搜索与剪枝 (Backtracking)',
    desc: '路径选择与撤销选择通用框架，应对排列组合与子集问题。',
    python3: `def backtrack(choices: list[int], path: list[int], res: list[list[int]], used: list[bool]):
    # 满足终止条件
    if len(path) == len(choices):
        res.append(path[:])
        return
        
    for i in range(len(choices)):
        if used[i]:
            continue
        # 剪枝判断...
        
        # 做出选择
        used[i] = True
        path.append(choices[i])
        
        backtrack(choices, path, res, used)
        
        # 撤销选择
        path.pop()
        used[i] = False`,
    cpp: `void backtrack(const vector<int>& nums, vector<int>& path, vector<vector<int>>& res, vector<bool>& used) {
    if (path.size() == nums.size()) {
        res.push_back(path);
        return;
    }
    for (size_t i = 0; i < nums.size(); ++i) {
        if (used[i]) continue;
        used[i] = true;
        path.push_back(nums[i]);
        
        backtrack(nums, path, res, used);
        
        path.pop_back();
        used[i] = false;
    }
}`,
  },
  {
    title: '并查集 (Union-Find 带路径压缩)',
    desc: '高效处理图的连通分量与环路检测。',
    python3: `class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.count = n
        
    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x]) # 路径压缩
        return self.parent[x]
        
    def union(self, x: int, y: int) -> bool:
        root_x, root_y = self.find(x), self.find(y)
        if root_x == root_y:
            return False
        self.parent[root_x] = root_y
        self.count -= 1
        return True`,
    cpp: `class UnionFind {
public:
    vector<int> parent;
    int count;
    UnionFind(int n) : parent(n), count(n) {
        for (int i = 0; i < n; ++i) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    bool unite(int x, int y) {
        int rx = find(x), ry = find(y);
        if (rx == ry) return false;
        parent[rx] = ry;
        count--;
        return true;
    }
};`,
  },
  {
    title: '单调栈 (Monotonic Stack)',
    desc: 'O(N) 线性时间快速找到数组中每个元素左/右第一个更大或更小元素。',
    python3: `def next_greater_element(nums: list[int]) -> list[int]:
    n = len(nums)
    res = [-1] * n
    stack = []  # 存索引，单调递减
    
    for i in range(n):
        while stack and nums[i] > nums[stack[-1]]:
            idx = stack.pop()
            res[idx] = nums[i]
        stack.append(i)
    return res`,
    cpp: `vector<int> nextGreaterElement(const vector<int>& nums) {
    int n = nums.size();
    vector<int> res(n, -1);
    vector<int> st; // 单调递减栈
    
    for (int i = 0; i < n; ++i) {
        while (!st.empty() && nums[i] > nums[st.back()]) {
            res[st.back()] = nums[i];
            st.pop_back();
        }
        st.push_back(i);
    }
    return res;
}`,
  },
  {
    title: '拓扑排序 (Topological Sort / Kahn 算法)',
    desc: '检测有向图环路与确定依赖任务执行顺序。',
    python3: `def topological_sort(num_courses: int, prerequisites: list[list[int]]) -> list[int]:
    from collections import deque, defaultdict
    in_degree = [0] * num_courses
    adj = defaultdict(list)
    
    for cur, pre in prerequisites:
        adj[pre].append(cur)
        in_degree[cur] += 1
        
    q = deque([i for i in range(num_courses) if in_degree[i] == 0])
    order = []
    
    while q:
        node = q.popleft()
        order.append(node)
        for nxt in adj[node]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                q.append(nxt)
                
    return order if len(order) == num_courses else []`,
    cpp: `vector<int> topologicalSort(int numCourses, const vector<vector<int>>& prerequisites) {
    vector<int> inDegree(numCourses, 0);
    vector<vector<int>> adj(numCourses);
    for (const auto& p : prerequisites) {
        adj[p[1]].push_back(p[0]);
        inDegree[p[0]]++;
    }
    queue<int> q;
    for (int i = 0; i < numCourses; ++i) {
        if (inDegree[i] == 0) q.push(i);
    }
    vector<int> order;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (int v : adj[u]) {
            if (--inDegree[v] == 0) q.push(v);
        }
    }
    return order.size() == numCourses ? order : vector<int>{};
}`,
  },
]

const currentTemplate = computed(() => TEMPLATES[selectedTemplateIdx.value])
</script>
