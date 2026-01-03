import type { Meta, StoryObj } from '@storybook/react'
import { TaskCard } from '@/components/Tasks/TaskCard'

const meta: Meta<typeof TaskCard> = {
  title: 'Tasks/TaskCard',
  component: TaskCard,
  args: {
    task: {
      id: 'b7f9b28b',
      title: 'Finalize Q2 roadmap',
      description: 'Confirm priorities with stakeholders and lock milestones.',
      status: 'in_progress',
      priority: 'high',
      dueDate: new Date().toISOString(),
      createdAt: new Date().toISOString(),
    },
  },
}

export default meta

type Story = StoryObj<typeof TaskCard>

export const Default: Story = {}
