interface Step {
  number: number
  title: string
  description: string
  code?: string
  language?: string
}

const steps: Step[] = [
  {
    number: 1,
    title: 'Define Seed Data',
    description: 'Start by creating a JSON seed file with the variables your pipeline will use.',
    code: `{
  "repetitions": 2,
  "metadata": {
    "topic": "AI",
    "level": "basic"
  }
}`,
    language: 'json'
  },
  {
    number: 2,
    title: 'Build Pipeline',
    description: 'Design your workflow using drag-and-drop blocks. Each block adds data to the accumulated state.',
    code: `LLM Block → Validator Block → Output Block
    ↓            ↓                ↓
  assistant  + is_valid    + formatted`
  },
  {
    number: 3,
    title: 'Review Results',
    description: 'Review your results with keyboard shortcuts and configure the view to easily see the needed data.',
    code: `Keyboard Shortcuts:
A → Accept  |  R → Reject  |  U → Pending
E → Edit    |  N → Next    |  P → Previous

Field Configuration:
Primary: [output]
Secondary: [metadata]
Hidden: [created_at, updated_at]`,
    language: 'text'
  },
  {
    number: 4,
    title: 'Export Data',
    description: 'Export your data in JSONL format, filtered by status (accepted, rejected, pending).',
    code: `{
  "id": 71,
  "output": "{"title": "..."}",
  "metadata": {...},
  "status": "accepted"
}`,
    language: 'json'
  }
]

export default function HowItWorks() {
  return (
    <section className="section-padding">
      <div className="container-custom">
        <h2 className="text-4xl md:text-5xl font-bold text-center mb-4">
          How It <span className="gradient-text">Works</span>
        </h2>

        <p className="text-xl text-gray-400 text-center mb-16 max-w-3xl mx-auto">
          From seed data to exported results in four simple steps
        </p>

        <div className="space-y-16">
          {steps.map((step, index) => (
            <div
              key={index}
              className="flex flex-col lg:flex-row gap-8 items-center"
            >
              <div className={`flex-1 ${index % 2 === 1 ? 'lg:order-2' : ''}`}>
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-primary/20 border-2 border-primary flex items-center justify-center text-2xl font-bold text-primary">
                    {step.number}
                  </div>
                  <h3 className="text-2xl font-semibold">{step.title}</h3>
                </div>
                <p className="text-gray-400 text-lg">{step.description}</p>
              </div>

              {step.code && (
                <div className={`flex-1 ${index % 2 === 1 ? 'lg:order-1' : ''}`}>
                  <div className="card-dark p-6">
                    <pre className="text-sm text-gray-300 overflow-x-auto">
                      <code>{step.code}</code>
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
