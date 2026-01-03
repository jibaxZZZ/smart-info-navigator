export type Priority = 'high' | 'medium' | 'low'

export interface ChecklistItem {
  id: string
  content: string
  completed: boolean
  priority?: Priority
  createdAt: string
}

export interface Checklist {
  id: string
  title: string
  items: ChecklistItem[]
  createdAt: string
  updatedAt: string
}

export interface ChecklistFilter {
  priority?: Priority
  completed?: boolean
  sortBy: 'createdAt' | 'priority' | 'content'
  sortOrder: 'asc' | 'desc'
}
