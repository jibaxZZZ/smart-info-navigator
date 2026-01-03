import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useToolMetadata } from '@/hooks/useToolMetadata'

export interface EmailConfirmationMeta {
  details: {
    to?: string | null
    subject?: string | null
    sentAt?: string | null
  }
}

interface EmailConfirmationProps {
  confirmation?: EmailConfirmationMeta
}

export function EmailConfirmation({ confirmation }: EmailConfirmationProps) {
  const metadata = useToolMetadata<EmailConfirmationMeta>()
  const resolvedConfirmation = confirmation ?? metadata

  if (!resolvedConfirmation?.details) {
    return (
      <Card className='border-dashed'>
        <CardHeader>
          <CardTitle>No email confirmation</CardTitle>
          <CardDescription>Waiting for MCP metadata.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className='text-lg'>Email sent</CardTitle>
        <CardDescription>Integration: SMTP</CardDescription>
      </CardHeader>
      <CardContent className='space-y-2 text-sm'>
        <div>
          <span className='text-muted-foreground'>To:</span>{' '}
          {resolvedConfirmation.details.to ?? 'Unknown recipient'}
        </div>
        <div>
          <span className='text-muted-foreground'>Subject:</span>{' '}
          {resolvedConfirmation.details.subject ?? 'No subject'}
        </div>
        {resolvedConfirmation.details.sentAt ? (
          <div className='text-xs text-muted-foreground'>
            Sent {new Date(resolvedConfirmation.details.sentAt).toLocaleString()}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
