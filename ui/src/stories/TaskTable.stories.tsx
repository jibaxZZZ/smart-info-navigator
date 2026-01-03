import type { Meta, StoryObj } from '@storybook/react'
import { TaskTable } from '@/components/Tasks/TaskTable'

const meta: Meta<typeof TaskTable> = {
  title: 'Tasks/TaskTable',
  component: TaskTable,
  args: {
    tasks: [
      {
        id: 'task-001',
        title: 'Prepare weekly report',
        description: 'Compile KPIs and highlight risks.',
        status: 'pending',
        priority: 'medium',
        dueDate: new Date().toISOString(),
      },
      {
        id: 'task-002',
        title: 'Close client feedback loop',
        description: 'Reply to open feedback items.',
        status: 'in_progress',
        priority: 'high',
        dueDate: new Date(Date.now() + 86400000).toISOString(),
      },
      {
        id: 'task-003',
        title: 'Sync with design team',
        description: 'Review component library updates.',
        status: 'completed',
        priority: 'low',
      },
    ],
  },
}

export default meta

type Story = StoryObj<typeof TaskTable>

export const Default: Story = {
  render: (args) => (
    <div className='bg-background p-6'>
      <TaskTable {...args} />
    </div>
  ),
}

export const Light: Story = {
  render: (args) => (
    <div className='bg-background p-6'>
      <TaskTable {...args} />
    </div>
  ),
}

export const Dark: Story = {
  render: (args) => (
    <div className='dark bg-background p-6'>
      <TaskTable {...args} />
    </div>
  ),
}
