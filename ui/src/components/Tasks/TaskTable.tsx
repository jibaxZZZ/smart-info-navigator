import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useToolMetadata } from '@/hooks/useToolMetadata'

export type TaskPriority = 'low' | 'medium' | 'high'
export type TaskStatus = 'pending' | 'in_progress' | 'completed'

export interface TaskRow {
  id: string
  title: string
  description?: string | null
  status: TaskStatus
  priority: TaskPriority
  dueDate?: string | null
  createdAt?: string | null
  updatedAt?: string | null
}

interface TaskTableProps {
  tasks?: TaskRow[]
  onUpdateStatus?: (taskId: string, nextStatus: TaskStatus) => void
}

type SortKey = 'title' | 'status' | 'priority' | 'dueDate'
type SortDirection = 'asc' | 'desc'

const priorityVariant: Record<TaskPriority, 'secondary' | 'default' | 'destructive'> =
  {
    low: 'secondary',
    medium: 'default',
    high: 'destructive',
  }

const statusLabel: Record<TaskStatus, string> = {
  pending: 'Pending',
  in_progress: 'In progress',
  completed: 'Completed',
}

const priorityRank: Record<TaskPriority, number> = {
  low: 1,
  medium: 2,
  high: 3,
}

const statusRank: Record<TaskStatus, number> = {
  pending: 1,
  in_progress: 2,
  completed: 3,
}

export function TaskTable({ tasks, onUpdateStatus }: TaskTableProps) {
  const metadata = useToolMetadata<{ tasks?: TaskRow[] }>()
  const resolvedTasks = tasks ?? metadata?.tasks ?? []
  const [sortKey, setSortKey] = useState<SortKey>('dueDate')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  const handleStatusUpdate = async (taskId: string, nextStatus: TaskStatus) => {
    if (onUpdateStatus) {
      onUpdateStatus(taskId, nextStatus)
      return
    }

    const openAiApi = (window as any).openai
    if (openAiApi?.callTool) {
      await openAiApi.callTool('update_task_status', {
        task_id: taskId,
        status: nextStatus,
      })
    }
  }

  const sortedTasks = useMemo(() => {
    const tasksCopy = [...resolvedTasks]

    const compare = (a: TaskRow, b: TaskRow) => {
      switch (sortKey) {
        case 'title':
          return a.title.localeCompare(b.title)
        case 'status':
          return statusRank[a.status] - statusRank[b.status]
        case 'priority':
          return priorityRank[a.priority] - priorityRank[b.priority]
        case 'dueDate': {
          const aTime = a.dueDate ? new Date(a.dueDate).getTime() : Infinity
          const bTime = b.dueDate ? new Date(b.dueDate).getTime() : Infinity
          return aTime - bTime
        }
        default:
          return 0
      }
    }

    tasksCopy.sort((a, b) =>
      sortDirection === 'asc' ? compare(a, b) : compare(b, a)
    )

    return tasksCopy
  }, [resolvedTasks, sortDirection, sortKey])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((direction) => (direction === 'asc' ? 'desc' : 'asc'))
      return
    }

    setSortKey(key)
    setSortDirection('asc')
  }

  const sortIndicator = (key: SortKey) => {
    if (sortKey !== key) return ''
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  if (resolvedTasks.length === 0) {
    return (
      <div className='rounded-lg border border-dashed p-6 text-sm text-muted-foreground'>
        No tasks to display yet.
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>
            <Button
              type='button'
              variant='ghost'
              className='-ml-2 h-8 px-2 text-xs font-semibold'
              onClick={() => handleSort('title')}
            >
              Title {sortIndicator('title')}
            </Button>
          </TableHead>
          <TableHead>
            <Button
              type='button'
              variant='ghost'
              className='-ml-2 h-8 px-2 text-xs font-semibold'
              onClick={() => handleSort('status')}
            >
              Status {sortIndicator('status')}
            </Button>
          </TableHead>
          <TableHead>
            <Button
              type='button'
              variant='ghost'
              className='-ml-2 h-8 px-2 text-xs font-semibold'
              onClick={() => handleSort('priority')}
            >
              Priority {sortIndicator('priority')}
            </Button>
          </TableHead>
          <TableHead>
            <Button
              type='button'
              variant='ghost'
              className='-ml-2 h-8 px-2 text-xs font-semibold'
              onClick={() => handleSort('dueDate')}
            >
              Due {sortIndicator('dueDate')}
            </Button>
          </TableHead>
          <TableHead className='text-right'>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sortedTasks.map((task) => (
          <TableRow key={task.id}>
            <TableCell className='font-medium'>
              <div className='flex flex-col gap-1'>
                <span>{task.title}</span>
                <span className='text-xs text-muted-foreground'>
                  {task.description ?? 'No description'}
                </span>
              </div>
            </TableCell>
            <TableCell>
              <Badge variant='outline'>{statusLabel[task.status]}</Badge>
            </TableCell>
            <TableCell>
              <Badge variant={priorityVariant[task.priority]}>{task.priority}</Badge>
            </TableCell>
            <TableCell>
              {task.dueDate
                ? new Date(task.dueDate).toLocaleDateString()
                : '—'}
            </TableCell>
            <TableCell className='text-right'>
              {task.status !== 'completed' ? (
                <Button
                  size='sm'
                  onClick={() => handleStatusUpdate(task.id, 'completed')}
                >
                  Mark complete
                </Button>
              ) : (
                <span className='text-xs text-muted-foreground'>Done</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
