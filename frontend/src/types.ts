// 与后端契约对齐的类型定义

export type Language = 'python3' | 'cpp'
export type IoMode = 'acm' | 'leetcode'
export type Difficulty = 'easy' | 'medium' | 'hard'
export type SubmissionStatus =
  | 'pending'
  | 'judging'
  | 'AC'
  | 'WA'
  | 'TLE'
  | 'MLE'
  | 'CE'
  | 'RE'
  | 'IE'

export interface User {
  id: number
  username: string
  email: string | null
  is_admin: boolean
  avatar_url: string | null
}

export interface InviteSummary {
  id: number
  expires_at: string
  used_at: string | null
  revoked_at: string | null
  created_at: string
}

export interface InviteCreated extends InviteSummary {
  code: string
}

export interface ProblemListItem {
  id: number
  slug: string
  leetcode_id: number | null
  title: string
  difficulty: Difficulty
  source: 'hot100' | 'mianjing'
  tags: string[]
  my_status: 'solved' | 'attempted' | null
  has_solution: boolean
  memory: 'remembered' | 'unremembered' | null
}

export function problemHeading(p: { leetcode_id?: number | null; title: string }): string {
  return p.leetcode_id != null ? `${p.leetcode_id}. ${p.title}` : p.title
}

/** 来源筛选：Hot100 撞车题仍 source=hot100，用标签「面经」同时出现在面经列表。 */
export function belongsToSource(
  p: { source: string; tags?: string[] | null },
  source: string,
): boolean {
  if (!source) return true
  if (p.source === source) return true
  return source === 'mianjing' && (p.tags || []).includes('面经')
}

export function sourceBadgeTexts(
  p: { source: string; tags?: string[] | null },
  compact = false,
): string[] {
  const mianjing = compact ? '面经' : '面经手撕'
  const out: string[] = []
  if (p.source === 'hot100') out.push('热题100')
  if (p.source === 'mianjing' || (p.tags || []).includes('面经')) out.push(mianjing)
  return out
}

export interface SampleTest {
  ordinal: number
  input: string
  expected_output: string
}

export interface ProblemDetail extends Omit<ProblemListItem, 'my_status'> {
  statement_md: string
  time_limit_ms: number
  memory_limit_mb: number
  samples: SampleTest[]
  leetcode_available: boolean
  leetcode_starters?: Record<Language, string> | null
}

export interface TestResult {
  ordinal: number
  is_sample: boolean
  status: SubmissionStatus
  runtime_ms?: number | null
  input?: string
  expected?: string
  output?: string
  stderr?: string
}

export interface Submission {
  id: number
  problem_slug: string
  problem_title?: string
  language: Language
  io_mode?: IoMode
  code?: string
  status: SubmissionStatus
  runtime_ms: number | null
  compile_output: string | null
  detail: TestResult[] | null
  created_at: string
}

export interface Draft {
  code: string
  updated_at: string | null
  is_default?: boolean
}

export interface Job {
  id: number
  company: string
  position: string
  tier: 'big' | 'mid' | 'small'
  batch: string | null
  open_at: string | null
  deadline_at: string | null
  jd_text: string | null
  apply_url: string | null
  status: string
  days_left: number | null
  created_at?: string
}

export interface LinkItem {
  category: string
  title: string
  url: string
  note?: string
}

export const FINAL_STATUSES: SubmissionStatus[] = ['AC', 'WA', 'TLE', 'MLE', 'CE', 'RE', 'IE']

export function isFinal(s: SubmissionStatus): boolean {
  return FINAL_STATUSES.includes(s)
}

export type QuizQuestionType = 'single' | 'multiple' | 'judge' | 'open'

export interface QuizBank {
  bank: string
  category: string
  total: number
  answered: number
  correct: number
  wrong: number
}

export interface QuizQuestionItem {
  id: number
  bank: string
  category: string
  type: QuizQuestionType
  ordinal: number
  stem: string
  options: Record<string, string>
  tags?: string[]
  answer_status?: string | null
  is_answered: boolean
  is_correct: boolean | null
  user_answer: string | null
  is_favorite: boolean
  is_slashed: boolean
  wrong_count: number
  attempts_count: number
  answer: string | null
  analysis: string | null
}

export interface QuizAnswerResult {
  id: number
  is_correct: boolean
  correct_answer: string
  analysis: string
  user_answer: string
  wrong_count: number
  attempts_count: number
  is_slashed: boolean
}

export interface QuizStats {
  total_questions: number
  answered_count: number
  correct_count: number
  wrong_count: number
  slashed_count: number
  favorite_count: number
  accuracy_rate: number
  today_count: number
}

export type LeaderboardBoard = 'problems' | 'quiz' | 'duration'
export type LeaderboardPeriod = 'today' | 'week' | 'all'

export interface LeaderboardEntry {
  rank: number
  username: string
  avatar_url?: string | null
  value: number
  is_me: boolean
}

export interface LeaderboardResponse {
  board: LeaderboardBoard
  period: LeaderboardPeriod
  timezone: string
  metric: 'solved_count' | 'quiz_solved_count' | 'active_seconds'
  me: { rank: number | null; username: string; avatar_url?: string | null; value: number }
  entries: LeaderboardEntry[]
}

export interface ActivityHeartbeatRequest {
  session_id: string
  surface: 'problem' | 'quiz' | 'review' | 'handbook' | 'jobs'
  elapsed_seconds: number
}

export interface ActivityHeartbeatResponse {
  accepted_seconds: number
  daily_seconds: number
}

