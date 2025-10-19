import { Header } from '@/components/shared'
import { Hero, Features, HowItWorks, QuickStart, Footer } from '@/components/landing'

export default function Landing() {
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <QuickStart />
      </main>
      <Footer />
    </div>
  )
}
