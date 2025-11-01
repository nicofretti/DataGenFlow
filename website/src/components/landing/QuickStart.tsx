import { useState } from "react";
import { Link } from "react-router-dom";
import Button from "../shared/Button";

export default function QuickStart() {
  const [copied, setCopied] = useState(false);

  const installCommand = `make setup
make dev
make run

# Open http://localhost:8000, make sure to have .env configured`;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(installCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="quick-start" className="section-padding bg-background-dark">
      <div className="container-custom">
        <h2 className="text-4xl md:text-5xl font-bold text-center mb-4">
          Get Started in <span className="gradient-text">Under 2 Minutes</span>
        </h2>

        <p className="text-xl text-gray-400 text-center mb-12">
          No complex configuration, no external dependencies required
        </p>

        <div className="max-w-3xl mx-auto">
          <div className="card-dark p-6 relative">
            <button
              onClick={handleCopy}
              className="absolute top-4 right-4 px-3 py-1 text-sm bg-primary/20 hover:bg-primary/30 text-primary rounded transition-colors"
            >
              {copied ? "Copied!" : "Copy"}
            </button>

            <pre className="text-sm text-gray-300 overflow-x-auto pt-8">
              <code>{installCommand}</code>
            </pre>
          </div>

          <div className="mt-8 text-center">
            <p className="text-gray-400 mb-6">That&apos;s it! No complex configuration required.</p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="https://github.com/nicofretti/DataGenFlow"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="primary" size="lg">
                  View on GitHub
                </Button>
              </a>

              <Link to="/docs/overview">
                <Button variant="outline" size="lg">
                  Read Documentation
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
