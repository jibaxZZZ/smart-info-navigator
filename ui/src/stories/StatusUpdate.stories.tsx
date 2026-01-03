import type { Meta, StoryObj } from '@storybook/react'
import { StatusUpdate } from '@/components/Tasks/StatusUpdate'

const meta: Meta<typeof StatusUpdate> = {
  title: 'Tasks/StatusUpdate',
  component: StatusUpdate,
  args: {
    update: {
      task: {
        id: 'task-002',
        title: 'Close client feedback loop',
        status: 'completed',
        updatedAt: new Date().toISOString(),
      },
    },
  },
}

export default meta

type Story = StoryObj<typeof StatusUpdate>

export const Default: Story = {}
