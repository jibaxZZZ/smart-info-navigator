import type { Meta, StoryObj } from '@storybook/react'
import { Checklist } from '@/components/Checklist/Checklist'

const meta: Meta<typeof Checklist> = {
  title: 'Checklist/Checklist',
  component: Checklist,
  args: {
    title: 'Launch checklist',
    items: [
      {
        id: 'item-1',
        label: 'Finalize tool schemas',
        completed: true,
      },
      {
        id: 'item-2',
        label: 'Review authentication flow',
        completed: false,
      },
      {
        id: 'item-3',
        label: 'Prepare demo scripts',
        completed: false,
      },
    ],
  },
}

export default meta

type Story = StoryObj<typeof Checklist>

export const Default: Story = {}
