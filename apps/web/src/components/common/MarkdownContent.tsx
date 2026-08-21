"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
  className?: string;
}

/** Renders a Markdown string (headings, lists, bold, tables, fenced code
 * blocks, etc.) as styled HTML. Safe against XSS by construction — react-markdown
 * escapes raw HTML in the source rather than rendering it, since no
 * rehype-raw plugin is used. */
export function MarkdownContent({ content, className }: Props) {
  return (
    <div className={`prose prose-sm dark:prose-invert leading-relaxed ${className ?? ""}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
