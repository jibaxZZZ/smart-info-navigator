import type { Meta, StoryObj } from '@storybook/react'
import { EmailConfirmation } from '@/components/Integrations/EmailConfirmation'

const meta: Meta<typeof EmailConfirmation> = {
  title: 'Integrations/EmailConfirmation',
  component: EmailConfirmation,
  args: {
    confirmation: {
      details: {
        to: 'ops@example.com',
        subject: 'Overdue tasks report',
        sentAt: new Date().toISOString(),
      },
    },
  },
}

export default meta

type Story = StoryObj<typeof EmailConfirmation>

export const Default: Story = {}
