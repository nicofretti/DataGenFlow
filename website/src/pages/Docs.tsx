import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Sidebar, Content } from "@/components/docs";
import { fetchDoc } from "@/lib/docs";
import { DocFile } from "@/lib/types";

export default function Docs() {
  const { "*": slug } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<DocFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [invalidSlug, setInvalidSlug] = useState<string | null>(null);

  useEffect(() => {
    // redirect to first doc if no slug
    if (!slug) {
      navigate("/docs/overview");
      return;
    }

    setLoading(true);
    setInvalidSlug(null);
    fetchDoc(slug)
      .then((result) => {
        if (!result) {
          setInvalidSlug(slug);
        }
        setDoc(result);
      })
      .finally(() => setLoading(false));
  }, [slug, navigate]);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <main className="flex-1 w-full mt-16 lg:mt-0">
        <div className="max-w-5xl mx-auto px-6 py-12 md:px-12 lg:px-16">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-pulse text-gray-400">Loading...</div>
            </div>
          ) : doc ? (
            <>
              <Content markdown={doc.content} title={doc.title} />

              <div className="mt-16 pt-8 border-t border-gray-800">
                <a
                  href={`https://github.com/nicofretti/DataGenFlow/edit/main/${slug === "README" || slug === "DEVELOPERS" || slug === "CONTRIBUTING" || slug === "CHANGELOG" ? slug + ".md" : "docs/" + slug + ".md"}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-primary transition-colors group"
                >
                  <span>Edit this page on GitHub</span>
                </a>
              </div>
            </>
          ) : (
            <div className="text-center py-20">
              <div className="mb-6">
                <svg
                  className="w-24 h-24 mx-auto text-gray-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h1 className="text-3xl font-bold mb-4 text-white">Page Not Found</h1>
              <p className="text-gray-400 mb-2 text-lg">
                The documentation page you&apos;re looking for doesn&apos;t exist.
              </p>
              {invalidSlug && (
                <p className="text-gray-500 mb-8 text-sm font-mono">
                  Invalid slug: <span className="text-red-400">&quot;{invalidSlug}&quot;</span>
                </p>
              )}
              <div className="space-y-4">
                <Link
                  to="/docs/overview"
                  className="inline-block px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
                >
                  Go to documentation home
                </Link>
                <p className="text-gray-500 text-sm">or choose a page from the sidebar</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
