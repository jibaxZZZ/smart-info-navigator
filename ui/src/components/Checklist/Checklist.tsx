import { useMemo, useState } from 'react'

import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'

export interface ChecklistItem {
  id: string
  label: string
  completed: boolean
}

interface ChecklistProps {
  title?: string
  items: ChecklistItem[]
  onToggle?: (itemId: string, completed: boolean) => void
}

export function Checklist({ title, items, onToggle }: ChecklistProps) {
  const [localItems, setLocalItems] = useState<ChecklistItem[]>(items)

  const resolvedItems = useMemo(() => {
    return onToggle ? items : localItems
  }, [items, localItems, onToggle])

  const handleToggle = (itemId: string) => {
    const nextItems = resolvedItems.map((item) =>
      item.id === itemId ? { ...item, completed: !item.completed } : item
    )

    if (onToggle) {
      const updatedItem = nextItems.find((item) => item.id === itemId)
      if (updatedItem) {
        onToggle(itemId, updatedItem.completed)
      }
      return
    }

    setLocalItems(nextItems)
  }

  return (
    <div className='rounded-lg border border-border bg-card p-6 shadow-sm'>
      {title ? <h3 className='text-lg font-semibold'>{title}</h3> : null}
      <div className='mt-4 space-y-3'>
        {resolvedItems.map((item) => (
          <button
            key={item.id}
            type='button'
            onClick={() => handleToggle(item.id)}
            className='flex w-full items-start gap-3 rounded-md px-2 py-2 text-left transition hover:bg-muted/60'
          >
            <Checkbox checked={item.completed} aria-label={item.label} />
            <span
              className={cn(
                'text-sm text-foreground',
                item.completed && 'text-muted-foreground line-through'
              )}
            >
              {item.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
