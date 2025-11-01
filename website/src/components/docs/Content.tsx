import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";
import { Link } from "react-router-dom";
import { ReactNode, useState } from "react";

interface ContentProps {
  markdown: string;
  title: string;
}

// copy button component for code blocks
function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      // try modern clipboard API first
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback to legacy method
      const textArea = document.createElement("textarea");
      textArea.value = code;
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand("copy");
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (e) {
        console.error("Failed to copy:", e);
      }
      document.body.removeChild(textArea);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 rounded transition-colors"
      title="Copy code"
    >
      {copied ? "✓ Copied!" : "Copy"}
    </button>
  );
}

// convert heading text to anchor ID
function generateId(children: ReactNode): string {
  const text = extractText(children);
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "") // remove special characters
    .replace(/\s+/g, "-") // spaces to hyphens
    .replace(/-+/g, "-") // collapse multiple hyphens
    .replace(/^-|-$/g, ""); // trim hyphens from start/end
}

// extract plain text from react node (handles nested elements)
function extractText(node: ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (node && typeof node === "object" && "props" in node) {
    const props = (node as any).props;
    return extractText(props.children);
  }
  return "";
}

// check if blockquote is an admonition (Note/Warning/Tip)
function parseAdmonition(children: ReactNode): {
  type: "note" | "warning" | "tip" | null;
  content: ReactNode;
} {
  const text = extractText(children);
  const match = text.match(/^\*\*(Note|Warning|Tip)\*\*:\s*/);

  if (match) {
    const type = match[1].toLowerCase() as "note" | "warning" | "tip";
    return { type, content: children };
  }

  return { type: null, content: children };
}

export default function Content({ markdown, title }: ContentProps) {
  return (
    <article className="prose prose-invert prose-green max-w-none">
      <h1 className="text-5xl font-bold mb-12 gradient-text leading-tight">{title}</h1>

      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code(props) {
            const { inline, className, children, ...rest } = props as any;
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : "";
            const codeString = String(children).replace(/\n$/, "");

            return !inline && language ? (
              <div className="relative my-4">
                <CopyButton code={codeString} />
                <SyntaxHighlighter
                  style={vscDarkPlus as any}
                  language={language}
                  PreTag="div"
                  className="rounded-lg"
                  customStyle={{
                    margin: 0,
                    paddingTop: "2.5rem", // space for copy button
                  }}
                >
                  {codeString}
                </SyntaxHighlighter>
              </div>
            ) : (
              <code
                className="bg-background-card px-1.5 py-0.5 rounded text-primary text-sm font-mono"
                {...rest}
              >
                {children}
              </code>
            );
          },
          a({ href, children }) {
            const isExternal = href?.startsWith("http");
            const isAnchor = href?.startsWith("#");

            // convert markdown links to website routes
            let processedHref = href;
            let isInternalDoc = false;

            if (!isExternal && !isAnchor && href) {
              // remove .md extension
              processedHref = href.replace(/\.md$/, "");

              // convert docs/page links to /docs/page
              if (processedHref.startsWith("docs/")) {
                processedHref = "/" + processedHref;
                isInternalDoc = true;
              }
              // convert FILENAME.md links to /docs/FILENAME
              else if (processedHref.match(/^[A-Z_]+$/)) {
                processedHref = "/docs/" + processedHref;
                isInternalDoc = true;
              }
            }

            // use Link for internal doc navigation (no page reload)
            if (isInternalDoc) {
              return (
                <Link
                  to={processedHref || "#"}
                  className="text-primary hover:text-primary-light transition-colors underline decoration-primary/30 hover:decoration-primary"
                >
                  {children}
                </Link>
              );
            }

            // use regular anchor for external links and anchors
            return (
              <a
                href={processedHref}
                target={isExternal ? "_blank" : undefined}
                rel={isExternal ? "noopener noreferrer" : undefined}
                className="text-primary hover:text-primary-light transition-colors underline decoration-primary/30 hover:decoration-primary"
              >
                {children}
              </a>
            );
          },
          img({ src, alt }) {
            return (
              <img
                src={src?.startsWith("/") ? src : `/images/${src}`}
                alt={alt || ""}
                className="rounded-lg border border-gray-800 my-6 max-w-full"
              />
            );
          },
          h1() {
            // skip h1 from markdown since we already show title at top
            return null;
          },
          h2({ children }) {
            const id = generateId(children);
            return (
              <h2
                id={id}
                className="text-2xl font-bold mt-12 mb-4 text-white border-b border-gray-800 pb-2 scroll-mt-20"
              >
                {children}
              </h2>
            );
          },
          h3({ children }) {
            const id = generateId(children);
            return (
              <h3 id={id} className="text-xl font-semibold mt-8 mb-3 text-white scroll-mt-20">
                {children}
              </h3>
            );
          },
          h4({ children }) {
            const id = generateId(children);
            return (
              <h4 id={id} className="text-lg font-semibold mt-6 mb-2 text-gray-200 scroll-mt-20">
                {children}
              </h4>
            );
          },
          p({ children }) {
            return <p className="text-gray-300 leading-relaxed my-4">{children}</p>;
          },
          ul({ children }) {
            return (
              <ul className="list-disc list-inside space-y-2 my-4 text-gray-300">{children}</ul>
            );
          },
          ol({ children }) {
            return (
              <ol className="list-decimal list-inside space-y-2 my-4 text-gray-300">{children}</ol>
            );
          },
          li({ children }) {
            return <li className="ml-4">{children}</li>;
          },
          blockquote({ children }) {
            const { type, content } = parseAdmonition(children);

            // admonition styles
            const admonitionStyles = {
              note: {
                border: "border-blue-500",
                bg: "bg-blue-500/10",
                icon: "💡",
                label: "Note",
              },
              warning: {
                border: "border-yellow-500",
                bg: "bg-yellow-500/10",
                icon: "⚠️",
                label: "Warning",
              },
              tip: {
                border: "border-green-500",
                bg: "bg-green-500/10",
                icon: "💡",
                label: "Tip",
              },
            };

            if (type) {
              const style = admonitionStyles[type];
              return (
                <div
                  className={`border-l-4 ${style.border} ${style.bg} pl-4 pr-4 py-3 my-4 rounded-r`}
                >
                  <div className="flex gap-2">
                    <span className="text-lg flex-shrink-0">{style.icon}</span>
                    <div className="text-gray-200 not-italic">{content}</div>
                  </div>
                </div>
              );
            }

            // regular blockquote
            return (
              <blockquote className="border-l-4 border-primary pl-4 py-2 my-4 italic text-gray-400 bg-background-card rounded-r">
                {children}
              </blockquote>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-6">
                <table className="min-w-full border border-gray-800 rounded-lg">{children}</table>
              </div>
            );
          },
          thead({ children }) {
            return (
              <thead className="bg-background-card border-b border-gray-800">{children}</thead>
            );
          },
          tbody({ children }) {
            return <tbody className="divide-y divide-gray-800">{children}</tbody>;
          },
          tr({ children }) {
            return <tr className="hover:bg-background-card/50 transition-colors">{children}</tr>;
          },
          th({ children }) {
            return (
              <th className="px-4 py-3 text-left text-sm font-semibold text-white">{children}</th>
            );
          },
          td({ children }) {
            return <td className="px-4 py-3 text-sm text-gray-300">{children}</td>;
          },
          hr() {
            return <hr className="my-8 border-gray-800" />;
          },
          strong({ children }) {
            return <strong className="font-bold text-white">{children}</strong>;
          },
          em({ children }) {
            return <em className="italic text-gray-200">{children}</em>;
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </article>
  );
}
