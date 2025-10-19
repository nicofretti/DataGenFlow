interface Feature {
  icon: string
  title: string
  description: string
}

const features: Feature[] = [
  {
    icon: '🔌',
    title: 'Easy to Extend',
    description: 'Add custom blocks in minutes with auto-discovery. Drop your file in user_blocks/ and it\'s automatically available—no configuration needed.'
  },
  {
    icon: '⚡',
    title: 'Faster Development',
    description: 'Visual pipeline builder eliminates boilerplate code. Connect blocks and they automatically share data through accumulated state.'
  },
  {
    icon: '🎯',
    title: 'Simple to Use',
    description: 'Intuitive drag-and-drop interface, no training required. Build complex data generation workflows without writing orchestration code.'
  },
  {
    icon: '🔍',
    title: 'Full Transparency',
    description: 'Complete execution traces for debugging. See exactly how each result was generated with full visibility into every pipeline step.'
  }
]

export default function Features() {
  return (
    <section className="section-padding bg-background-dark">
      <div className="container-custom">
        <h2 className="text-4xl md:text-5xl font-bold text-center mb-4">
          Why <span className="gradient-text">DataGenFlow</span>
        </h2>

        <p className="text-xl text-gray-400 text-center mb-16 max-w-3xl mx-auto">
          Transform complex data generation workflows into intuitive visual pipelines
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="card-dark p-6 hover:border-primary/50 transition-colors"
            >
              <div className="text-4xl mb-4">{feature.icon}</div>
              <h3 className="text-xl font-semibold mb-3 text-primary">
                {feature.title}
              </h3>
              <p className="text-gray-400">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
