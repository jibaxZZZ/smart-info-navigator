import { useState } from 'react'

function App() {
  const [activeTab, setActiveTab] = useState<'summary' | 'checklist' | 'export'>('summary')

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-4">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">
            Smart Info Navigator
          </h1>
          <p className="text-muted-foreground mt-2">
            Transform text into structured summaries and actionable checklists
          </p>
        </header>

        <main>
          <div className="border-b border-border mb-4">
            <nav className="flex gap-4">
              <button
                onClick={() => setActiveTab('summary')}
                className={`px-4 py-2 border-b-2 transition-colors ${
                  activeTab === 'summary'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                Summary
              </button>
              <button
                onClick={() => setActiveTab('checklist')}
                className={`px-4 py-2 border-b-2 transition-colors ${
                  activeTab === 'checklist'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                Checklist
              </button>
              <button
                onClick={() => setActiveTab('export')}
                className={`px-4 py-2 border-b-2 transition-colors ${
                  activeTab === 'export'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                Export
              </button>
            </nav>
          </div>

          <div className="mt-6">
            {activeTab === 'summary' && (
              <div className="text-muted-foreground">
                Summary view - Coming soon
              </div>
            )}
            {activeTab === 'checklist' && (
              <div className="text-muted-foreground">
                Checklist view - Coming soon
              </div>
            )}
            {activeTab === 'export' && (
              <div className="text-muted-foreground">
                Export panel - Coming soon
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
