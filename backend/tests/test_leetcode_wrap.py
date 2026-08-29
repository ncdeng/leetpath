import contextlib
import io
import os
import runpy
import sys
import tempfile
from pathlib import Path

from judge.leetcode_catalog import SPECS, spec_for
from judge.leetcode_wrap import generate_starter, wrap_user_code
from judge.worker import normalize

SEED = Path(__file__).resolve().parents[1] / "app" / "seed" / "problems"


def _exec_wrap(wrapped: str, stdin_text: str) -> str:
    buf_out = io.StringIO()
    fd, path = tempfile.mkstemp(suffix=".py")
    old_in = sys.stdin
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            fd = -1
            f.write(wrapped)
        sys.stdin = io.StringIO(stdin_text)
        with contextlib.redirect_stdout(buf_out):
            runpy.run_path(path, run_name="__main__")
        return buf_out.getvalue()
    finally:
        sys.stdin = old_in
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            os.unlink(path)
        except OSError:
            pass


def _assert_seed(slug: str, user_code: str) -> None:
    spec = spec_for(slug)
    assert spec is not None, slug
    wrapped = wrap_user_code("python3", user_code, spec)
    tests_dir = SEED / slug / "tests"
    cases = sorted(tests_dir.glob("*.in"))
    assert cases, slug
    for inp in cases:
        got = _exec_wrap(wrapped, inp.read_text(encoding="utf-8"))
        expected = inp.with_suffix(".out").read_text(encoding="utf-8")
        assert normalize(got) == normalize(expected), f"{slug} {inp.name}"


def test_catalog_covers_every_seed_slug():
    slugs = {p.name for p in SEED.iterdir() if p.is_dir()}
    missing = slugs - set(SPECS)
    extra = set(SPECS) - slugs
    assert not missing, missing
    assert not extra, extra


def test_two_sum_starter_matches_leetcode_style():
    spec = spec_for("two-sum")
    py = generate_starter(spec, "python3")
    assert "class Solution:" in py
    assert "def twoSum(self, nums: List[int], target: int) -> List[int]:" in py
    assert "if __name__" not in py
    assert "stdin" not in py
    cpp = generate_starter(spec, "cpp")
    assert "class Solution" in cpp
    assert "vector<int> twoSum(vector<int>& nums, int target)" in cpp
    assert "int main" not in cpp


def test_linked_list_starter_has_commented_definition():
    spec = spec_for("add-two-numbers")
    py = generate_starter(spec, "python3")
    assert "# Definition for singly-linked list." in py
    assert "def addTwoNumbers(self, l1: Optional[ListNode], l2: Optional[ListNode]) -> Optional[ListNode]:" in py
    cpp = generate_starter(spec, "cpp")
    assert "Definition for singly-linked list." in cpp
    assert "ListNode* addTwoNumbers(ListNode* l1, ListNode* l2)" in cpp


def test_lru_starter_is_design_class():
    spec = spec_for("lru-cache")
    py = generate_starter(spec, "python3")
    assert "class LRUCache:" in py
    assert "def __init__(self, capacity: int) -> None:" in py
    assert "def get(self, key: int) -> int:" in py
    assert "def put(self, key: int, value: int) -> None:" in py
    assert "class Solution" not in py
    cpp = generate_starter(spec, "cpp")
    assert "class LRUCache" in cpp
    assert "LRUCache(int capacity)" in cpp
    assert "int get(int key)" in cpp
    assert "void put(int key, int value)" in cpp


def test_wrap_rejects_missing_spec():
    try:
        wrap_user_code("python3", "class Solution:\n    pass\n", None)
    except ValueError as exc:
        assert "力扣" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_wrap_two_sum_against_seed():
    _assert_seed(
        "two-sum",
        """
class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, x in enumerate(nums):
            y = target - x
            if y in seen:
                return [seen[y], i]
            seen[x] = i
""",
    )


def test_wrap_climbing_stairs_against_seed():
    _assert_seed(
        "climbing-stairs",
        """
class Solution:
    def climbStairs(self, n):
        a, b = 1, 1
        for _ in range(n):
            a, b = b, a + b
        return a
""",
    )


def test_wrap_valid_parentheses_against_seed():
    _assert_seed(
        "valid-parentheses",
        """
class Solution:
    def isValid(self, s):
        st = []
        pair = {')': '(', ']': '[', '}': '{'}
        for ch in s:
            if ch in '([{':
                st.append(ch)
            elif not st or st.pop() != pair[ch]:
                return False
        return not st
""",
    )


def test_wrap_unique_paths_against_seed():
    _assert_seed(
        "unique-paths",
        """
class Solution:
    def uniquePaths(self, m, n):
        dp = [1] * n
        for _ in range(1, m):
            for j in range(1, n):
                dp[j] += dp[j - 1]
        return dp[-1]
""",
    )


def test_wrap_word_break_mixed_string_io():
    _assert_seed(
        "word-break",
        """
class Solution:
    def wordBreak(self, s, wordDict):
        words = set(wordDict)
        n = len(s)
        dp = [False] * (n + 1)
        dp[0] = True
        for i in range(1, n + 1):
            for j in range(i):
                if dp[j] and s[j:i] in words:
                    dp[i] = True
                    break
        return dp[n]
""",
    )


def test_wrap_permutations_keeps_inner_order():
    _assert_seed(
        "permutations",
        """
import itertools
class Solution:
    def permute(self, nums):
        return [list(p) for p in itertools.permutations(nums)]
""",
    )


def test_wrap_subsets_sorts_by_length():
    _assert_seed(
        "subsets",
        """
class Solution:
    def subsets(self, nums):
        n = len(nums)
        out = []
        for mask in range(1 << n):
            out.append([nums[i] for i in range(n) if mask & (1 << i)])
        return out
""",
    )


def test_wrap_three_sum_canonical_lines():
    _assert_seed(
        "3sum",
        """
class Solution:
    def threeSum(self, nums):
        nums = sorted(nums)
        n = len(nums)
        res = []
        for i in range(n):
            if i and nums[i] == nums[i - 1]:
                continue
            l, r = i + 1, n - 1
            while l < r:
                s = nums[i] + nums[l] + nums[r]
                if s < 0:
                    l += 1
                elif s > 0:
                    r -= 1
                else:
                    res.append([nums[i], nums[l], nums[r]])
                    l += 1
                    r -= 1
                    while l < r and nums[l] == nums[l - 1]:
                        l += 1
                    while l < r and nums[r] == nums[r + 1]:
                        r -= 1
        return res
""",
    )


def test_wrap_group_anagrams_and_empty_string():
    _assert_seed(
        "group-anagrams",
        """
from collections import defaultdict
class Solution:
    def groupAnagrams(self, strs):
        g = defaultdict(list)
        for s in strs:
            g[''.join(sorted(s))].append(s)
        return list(g.values())
""",
    )


def test_wrap_n_queens_prints_count():
    _assert_seed(
        "n-queens",
        """
class Solution:
    def solveNQueens(self, n):
        col = [False] * n
        d1 = [False] * (2 * n)
        d2 = [False] * (2 * n)
        boards = []
        row_s = ['.'] * n

        def dfs(r, path):
            if r == n:
                boards.append(path[:])
                return
            for c in range(n):
                a, b = r - c + n - 1, r + c
                if col[c] or d1[a] or d2[b]:
                    continue
                col[c] = d1[a] = d2[b] = True
                row_s[c] = 'Q'
                path.append(''.join(row_s))
                row_s[c] = '.'
                dfs(r + 1, path)
                path.pop()
                col[c] = d1[a] = d2[b] = False
        dfs(0, [])
        return boards
""",
    )


def test_wrap_level_order_no_extra_count():
    _assert_seed(
        "binary-tree-level-order-traversal",
        """
from collections import deque
class Solution:
    def levelOrder(self, root):
        if not root:
            return []
        q = deque([root])
        out = []
        while q:
            level = []
            for _ in range(len(q)):
                node = q.popleft()
                level.append(node.val)
                if node.left:
                    q.append(node.left)
                if node.right:
                    q.append(node.right)
            out.append(level)
        return out
""",
    )


def test_wrap_min_stack_design():
    _assert_seed(
        "min-stack",
        """
class MinStack:
    def __init__(self):
        self.st = []
        self.mins = []
    def push(self, val):
        self.st.append(val)
        if not self.mins or val <= self.mins[-1]:
            self.mins.append(val)
    def pop(self):
        val = self.st.pop()
        if val == self.mins[-1]:
            self.mins.pop()
    def top(self):
        return self.st[-1]
    def getMin(self):
        return self.mins[-1]
""",
    )


def test_wrap_merge_intervals():
    _assert_seed(
        "merge-intervals",
        """
class Solution:
    def merge(self, intervals):
        intervals.sort()
        out = []
        for a, b in intervals:
            if not out or out[-1][1] < a:
                out.append([a, b])
            elif b > out[-1][1]:
                out[-1][1] = b
        return out
""",
    )


def test_wrap_course_schedule_edges():
    _assert_seed(
        "course-schedule",
        """
from collections import deque
class Solution:
    def canFinish(self, numCourses, prerequisites):
        g = [[] for _ in range(numCourses)]
        indeg = [0] * numCourses
        for a, b in prerequisites:
            g[b].append(a)
            indeg[a] += 1
        q = deque(i for i in range(numCourses) if indeg[i] == 0)
        taken = 0
        while q:
            u = q.popleft()
            taken += 1
            for v in g[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)
        return taken == numCourses
""",
    )


def test_wrap_add_two_numbers_lists():
    _assert_seed(
        "add-two-numbers",
        """
class Solution:
    def addTwoNumbers(self, l1, l2):
        dummy = ListNode()
        cur = dummy
        carry = 0
        while l1 or l2 or carry:
            s = carry
            if l1:
                s += l1.val
                l1 = l1.next
            if l2:
                s += l2.val
                l2 = l2.next
            cur.next = ListNode(s % 10)
            cur = cur.next
            carry = s // 10
        return dummy.next
""",
    )


def test_wrap_same_tree_two_trees():
    _assert_seed(
        "same-tree",
        """
class Solution:
    def isSameTree(self, p, q):
        if not p or not q:
            return p is q
        return p.val == q.val and self.isSameTree(p.left, q.left) and self.isSameTree(p.right, q.right)
""",
    )


def test_wrap_image_diff_two_matrices():
    _assert_seed(
        "image-diff-min-bounding-rectangle",
        """
class Solution:
    def minBoundingRect(self, a, b):
        min_r = min_c = 10**9
        max_r = max_c = -1
        for i in range(len(a)):
            for j in range(len(a[0])):
                if a[i][j] != b[i][j]:
                    min_r = min(min_r, i)
                    max_r = max(max_r, i)
                    min_c = min(min_c, j)
                    max_c = max(max_c, j)
        if max_r < 0:
            return [-1]
        return [min_r, min_c, max_r, max_c]
""",
    )


def test_wrap_number_of_islands_grid01():
    _assert_seed(
        "number-of-islands",
        """
class Solution:
    def numIslands(self, grid):
        if not grid:
            return 0
        m, n = len(grid), len(grid[0])
        def dfs(i, j):
            if i < 0 or i >= m or j < 0 or j >= n or grid[i][j] != '1':
                return
            grid[i][j] = '0'
            dfs(i + 1, j); dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1)
        ans = 0
        for i in range(m):
            for j in range(n):
                if grid[i][j] == '1':
                    ans += 1
                    dfs(i, j)
        return ans
""",
    )


def test_wrap_minimum_window_two_strings():
    _assert_seed(
        "minimum-window-substring",
        """
from collections import Counter
class Solution:
    def minWindow(self, s, t):
        need = Counter(t)
        required = len(need)
        formed = 0
        window = {}
        left = 0
        best_len, best_l = 10**18, 0
        for right, ch in enumerate(s):
            window[ch] = window.get(ch, 0) + 1
            if ch in need and window[ch] == need[ch]:
                formed += 1
            while left <= right and formed == required:
                if right - left + 1 < best_len:
                    best_len = right - left + 1
                    best_l = left
                cl = s[left]
                window[cl] -= 1
                if cl in need and window[cl] < need[cl]:
                    formed -= 1
                left += 1
        return '' if best_len == 10**18 else s[best_l:best_l + best_len]
""",
    )


def test_wrap_linked_list_cycle():
    _assert_seed(
        "linked-list-cycle",
        """
class Solution:
    def hasCycle(self, head):
        slow = fast = head
        while fast and fast.next:
            slow = slow.next
            fast = fast.next.next
            if slow is fast:
                return True
        return False
""",
    )


def test_wrap_invert_tree():
    _assert_seed(
        "invert-binary-tree",
        """
class Solution:
    def invertTree(self, root):
        if not root:
            return None
        root.left, root.right = self.invertTree(root.right), self.invertTree(root.left)
        return root
""",
    )


def test_wrap_move_zeroes_in_place():
    _assert_seed(
        "move-zeroes",
        """
class Solution:
    def moveZeroes(self, nums):
        w = 0
        for x in nums:
            if x != 0:
                nums[w] = x
                w += 1
        for i in range(w, len(nums)):
            nums[i] = 0
""",
    )


def test_wrap_cpp_two_sum_contains_harness():
    spec = spec_for("two-sum")
    src = wrap_user_code(
        "cpp",
        generate_starter(spec, "cpp").replace("        \n    }", "        return {};\n    }"),
        spec,
    )
    assert "int main()" in src
    assert "sol.twoSum" in src
    assert "struct ListNode" in src
