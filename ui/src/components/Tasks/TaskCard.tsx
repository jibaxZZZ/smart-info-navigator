import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useToolMetadata } from '@/hooks/useToolMetadata'

export type TaskPriority = 'low' | 'medium' | 'high'
export type TaskStatus = 'pending' | 'in_progress' | 'completed'

export interface TaskMeta {
  id: string
  title: string
  description?: string | null
  status: TaskStatus
  priority: TaskPriority
  dueDate?: string | null
  createdAt?: string | null
}

interface TaskCardProps {
  task?: TaskMeta
}

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

export function TaskCard({ task }: TaskCardProps) {
  const metadata = useToolMetadata<{ task?: TaskMeta }>()
  const resolvedTask = task ?? metadata?.task

  if (!resolvedTask) {
    return (
      <Card className='border-dashed'>
        <CardHeader>
          <CardTitle>No task data</CardTitle>
          <CardDescription>Waiting for MCP metadata.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className='flex flex-row items-start justify-between gap-4'>
        <div>
          <CardTitle className='text-lg'>{resolvedTask.title}</CardTitle>
          <CardDescription>Task #{resolvedTask.id}</CardDescription>
        </div>
        <Badge variant={priorityVariant[resolvedTask.priority]}>
          {resolvedTask.priority}
        </Badge>
      </CardHeader>
      <CardContent className='space-y-4'>
        {resolvedTask.description ? (
          <p className='text-sm text-muted-foreground'>
            {resolvedTask.description}
          </p>
        ) : (
          <p className='text-sm text-muted-foreground'>No description provided.</p>
        )}
        <div className='flex flex-wrap items-center gap-2 text-sm'>
          <Badge variant='outline'>{statusLabel[resolvedTask.status]}</Badge>
          {resolvedTask.dueDate ? (
            <span className='text-muted-foreground'>
              Due {new Date(resolvedTask.dueDate).toLocaleDateString()}
            </span>
          ) : (
            <span className='text-muted-foreground'>No due date</span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
