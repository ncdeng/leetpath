import type { GenerationGate } from './problemDraftSession.ts'

export type QuizTab = 'practice' | 'wrongbook' | 'banks' | 'favorites' | 'exam'

export interface QuizQuestionFilters {
  tab: QuizTab
  selectedBank: string
  onlyUnanswered: boolean
  randomOrder: boolean
}

export interface QuestionRequestToken {
  generation: number
  questionId: number
}

export function isCurrentQuestionRequest(
  gate: GenerationGate,
  token: QuestionRequestToken,
  currentQuestionId: number | undefined,
): boolean {
  return gate.isCurrent(token.generation) && currentQuestionId === token.questionId
}

export function buildQuizQuestionParams(filters: QuizQuestionFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.tab === 'wrongbook') {
    params.set('status', 'wrong')
  } else if (filters.tab === 'favorites') {
    params.set('status', 'favorited')
  } else if (filters.tab === 'exam') {
    params.set('limit', '20')
    params.set('random_order', 'true')
    params.set('exclude_open', 'true')
    params.set('exclude_skipped', 'true')
  } else if (filters.tab === 'practice') {
    if (filters.selectedBank) params.set('bank', filters.selectedBank)
    if (filters.onlyUnanswered) params.set('status', 'unanswered')
    if (filters.randomOrder) params.set('random_order', 'true')
  }
  return params
}

export function quizEnterHint(isOpenQuestion: boolean, openRevealed: boolean): string {
  if (!isOpenQuestion) return '提交/下一题'
  return openRevealed ? '下一题' : '查看答案'
}
