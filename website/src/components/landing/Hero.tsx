import Button from '../shared/Button'

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-background via-background-dark to-background">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(16,185,129,0.1),transparent_50%)]" />
      </div>

      {/* content */}
      <div className="relative z-10 container-custom text-center pt-20">
        <h1 className="text-5xl md:text-7xl font-bold mb-6">
          Transform Data Generation<br />
          Into <span className="gradient-text">Visual Pipelines</span>
        </h1>

        <p className="text-xl md:text-2xl text-gray-400 mb-12 max-w-3xl mx-auto">
          Build, validate, and export quality data with drag-and-drop simplicity
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
          <Button
            variant="primary"
            size="lg"
            onClick={() => {
              const element = document.getElementById('quick-start')
              element?.scrollIntoView({ behavior: 'smooth' })
            }}
          >
            Get Started
          </Button>

          <Button
            variant="outline"
            size="lg"
            onClick={() => {
              const element = document.getElementById('demo')
              element?.scrollIntoView({ behavior: 'smooth' })
            }}
          >
            View Demo
          </Button>
        </div>

        {/* demo video */}
        <div id="demo" className="max-w-5xl mx-auto">
          <div className="card-dark p-2">
            <video
              className="w-full rounded"
              controls
              poster="/images/logo/banner.png"
            >
              <source src="/images/video/full_video.mp4" type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>
        </div>
      </div>
    </section>
  )
}
