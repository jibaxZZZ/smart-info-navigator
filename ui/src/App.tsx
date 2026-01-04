import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { mcpClient, Task } from './lib/mcp-client'
import { TaskTable } from './components/Tasks/TaskTable'
import { Button } from './components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card'

function App() {
  const [activeTab, setActiveTab] = useState<'tasks' | 'workflows' | 'integrations'>('tasks')
  const queryClient = useQueryClient()

  // Fetch tasks using React Query
  const { data: tasksResponse, isLoading, error } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => mcpClient.listTasks(),
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  // Update task status mutation
  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: 'pending' | 'in_progress' | 'completed' }) =>
      mcpClient.updateTaskStatus({ task_id: taskId, status }),
    onSuccess: () => {
      // Refetch tasks after successful update
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })

  const handleUpdateStatus = async (taskId: string, newStatus: 'pending' | 'in_progress' | 'completed') => {
    try {
      await updateTaskMutation.mutateAsync({ taskId, status: newStatus })
    } catch (err) {
      console.error('Failed to update task status:', err)
    }
  }

  const tasks = tasksResponse?.data?.tasks || []

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-4">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">
            Workflow Orchestrator
          </h1>
          <p className="text-muted-foreground mt-2">
            Manage tasks, workflows, and integrations through natural language commands
          </p>
        </header>

        <main>
          <div className="border-b border-border mb-4">
            <nav className="flex gap-4">
              <button
                onClick={() => setActiveTab('tasks')}
                className={`px-4 py-2 border-b-2 transition-colors ${
                  activeTab === 'tasks'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                Tasks
              </button>
              <button
                onClick={() => setActiveTab('workflows')}
                className={`px-4 py-2 border-b-2 transition-colors ${
                  activeTab === 'workflows'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                Workflows
              </button>
              <button
                onClick={() => setActiveTab('integrations')}
                className={`px-4 py-2 border-b-2 transition-colors ${
                  activeTab === 'integrations'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                Integrations
              </button>
            </nav>
          </div>

          <div className="mt-6">
            {activeTab === 'tasks' && (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-2xl font-semibold">Your Tasks</h2>
                  <Button variant="default">Create Task</Button>
                </div>

                {isLoading && (
                  <div className="text-muted-foreground">Loading tasks...</div>
                )}

                {error && (
                  <div className="text-destructive">
                    Error loading tasks: {error instanceof Error ? error.message : 'Unknown error'}
                  </div>
                )}

                {!isLoading && !error && (
                  <TaskTable
                    tasks={tasks}
                    onUpdateStatus={handleUpdateStatus}
                  />
                )}
              </div>
            )}

            {activeTab === 'workflows' && (
              <Card>
                <CardHeader>
                  <CardTitle>Workflow Scheduling</CardTitle>
                  <CardDescription>
                    Automate task workflows and schedule recurring actions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    Workflow scheduling will be available in Phase 2
                  </p>
                </CardContent>
              </Card>
            )}

            {activeTab === 'integrations' && (
              <Card>
                <CardHeader>
                  <CardTitle>External Integrations</CardTitle>
                  <CardDescription>
                    Connect with Jira, Email, Slack, and other services
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 border rounded">
                      <div>
                        <h3 className="font-medium">Email (Gmail)</h3>
                        <p className="text-sm text-muted-foreground">
                          Send task notifications via email
                        </p>
                      </div>
                      <Button variant="outline" size="sm">
                        Configure
                      </Button>
                    </div>
                    <div className="flex items-center justify-between p-4 border rounded">
                      <div>
                        <h3 className="font-medium">Jira</h3>
                        <p className="text-sm text-muted-foreground">
                          Sync tasks with Jira (Phase 2)
                        </p>
                      </div>
                      <Button variant="outline" size="sm" disabled>
                        Coming Soon
                      </Button>
                    </div>
                    <div className="flex items-center justify-between p-4 border rounded">
                      <div>
                        <h3 className="font-medium">Slack</h3>
                        <p className="text-sm text-muted-foreground">
                          Send updates to Slack (Phase 2)
                        </p>
                      </div>
                      <Button variant="outline" size="sm" disabled>
                        Coming Soon
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
