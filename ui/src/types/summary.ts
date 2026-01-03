export interface SummarySection {
  title: string
  content: string
  order: number
}

export interface SummaryMetadata {
  wordCount: number
  readTime: string
  createdAt: string
}

export interface Summary {
  id: string
  title: string
  sections: SummarySection[]
  metadata: SummaryMetadata
  originalTextPreview?: string
}
