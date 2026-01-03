import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useToolMetadata } from '@/hooks/useToolMetadata'

export type TaskStatus = 'pending' | 'in_progress' | 'completed'

export interface StatusUpdateMeta {
  task: {
    id: string
    title: string
    status: TaskStatus
    updatedAt?: string | null
  }
}

interface StatusUpdateProps {
  update?: StatusUpdateMeta
}

const statusLabel: Record<TaskStatus, string> = {
  pending: 'Pending',
  in_progress: 'In progress',
  completed: 'Completed',
}

export function StatusUpdate({ update }: StatusUpdateProps) {
  const metadata = useToolMetadata<StatusUpdateMeta>()
  const resolvedUpdate = update ?? metadata

  if (!resolvedUpdate?.task) {
    return (
      <Card className='border-dashed'>
        <CardHeader>
          <CardTitle>No update details</CardTitle>
          <CardDescription>Waiting for MCP metadata.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className='text-lg'>Task updated</CardTitle>
        <CardDescription>Task #{resolvedUpdate.task.id}</CardDescription>
      </CardHeader>
      <CardContent className='space-y-3'>
        <div className='text-sm font-medium'>{resolvedUpdate.task.title}</div>
        <div className='flex flex-wrap items-center gap-2'>
          <Badge variant='outline'>{statusLabel[resolvedUpdate.task.status]}</Badge>
          {resolvedUpdate.task.updatedAt ? (
            <span className='text-xs text-muted-foreground'>
              Updated {new Date(resolvedUpdate.task.updatedAt).toLocaleString()}
            </span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}
