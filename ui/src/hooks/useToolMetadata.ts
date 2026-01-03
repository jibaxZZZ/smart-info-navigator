import { useMemo } from 'react'

type OpenAiWindow = {
  openai?: {
    toolResponseMetadata?: {
      _meta?: Record<string, unknown>
      [key: string]: unknown
    }
  }
  __storybookMeta?: {
    _meta?: Record<string, unknown>
    [key: string]: unknown
  }
}

export function useToolMetadata<T>(fallback?: T): T | undefined {
  return useMemo(() => {
    const windowWithOpenAi = window as OpenAiWindow
    const metadata =
      windowWithOpenAi.openai?.toolResponseMetadata ??
      windowWithOpenAi.__storybookMeta

    if (metadata && '_meta' in metadata) {
      return metadata._meta as T
    }

    return fallback
  }, [fallback])
}
