/** Tiptap editor that stores Markdown, so existing notes, search and version history keep working unchanged. */
import { useEffect } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { Markdown } from "tiptap-markdown";
import { Bold, Code2, Heading1, Heading2, Italic, List, ListOrdered, Quote } from "lucide-react";
import { cn } from "../lib/utils";

export default function RichEditor({ value, onChange, autoFocus, dark, className }: { value: string; onChange: (md: string) => void; autoFocus?: boolean; dark?: boolean; className?: string }) {
  const editor = useEditor({
    extensions: [StarterKit, Placeholder.configure({ placeholder: "Start writing… select text for formatting, or use # for headings and - for lists" }), Markdown.configure({ html: false, tightLists: true, linkify: true })],
    content: value,
    autofocus: autoFocus ? "end" : false,
    editorProps: { attributes: { "aria-label": "Page content", class: "rich-doc min-h-[440px] outline-none" } },
    onUpdate: ({ editor: e }) => onChange((e.storage as any).markdown.getMarkdown()),
  });
  // keep in sync if the page is replaced from outside (version restore)
  useEffect(() => {
    if (editor && (editor.storage as any).markdown.getMarkdown() !== value) editor.commands.setContent(value, false);
  }, [value, editor]);
  if (!editor) return null;
  const B = ({ on, active, label, children }: { on: () => void; active?: boolean; label: string; children: React.ReactNode }) => (
    <button type="button" aria-label={label} title={label} onMouseDown={(e) => e.preventDefault()} onClick={on} className={cn("grid h-8 w-8 place-items-center rounded-lg transition-colors", active ? "bg-brand-600 text-white" : dark ? "text-white/70 hover:bg-white/10" : "text-ink-600 hover:bg-sage-200")}>{children}</button>
  );
  return (
    <div className={className}>
      <div className={cn("sticky top-0 z-10 mb-2 flex flex-wrap gap-1 rounded-xl p-1 backdrop-blur", dark ? "bg-black/30" : "bg-white/70")} role="toolbar" aria-label="Formatting">
        <B label="Bold" active={editor.isActive("bold")} on={() => editor.chain().focus().toggleBold().run()}><Bold size={15} /></B>
        <B label="Italic" active={editor.isActive("italic")} on={() => editor.chain().focus().toggleItalic().run()}><Italic size={15} /></B>
        <B label="Heading 1" active={editor.isActive("heading", { level: 1 })} on={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}><Heading1 size={15} /></B>
        <B label="Heading 2" active={editor.isActive("heading", { level: 2 })} on={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}><Heading2 size={15} /></B>
        <B label="Bullet list" active={editor.isActive("bulletList")} on={() => editor.chain().focus().toggleBulletList().run()}><List size={15} /></B>
        <B label="Numbered list" active={editor.isActive("orderedList")} on={() => editor.chain().focus().toggleOrderedList().run()}><ListOrdered size={15} /></B>
        <B label="Quote" active={editor.isActive("blockquote")} on={() => editor.chain().focus().toggleBlockquote().run()}><Quote size={15} /></B>
        <B label="Code block" active={editor.isActive("codeBlock")} on={() => editor.chain().focus().toggleCodeBlock().run()}><Code2 size={15} /></B>
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
