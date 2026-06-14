type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function SourceEditor({ value, onChange }: Props) {
  const lineCount = Math.max(1, value.split("\n").length);
  const lineNumbers = Array.from({ length: lineCount }, (_, index) => index + 1).join("\n");

  return (
    <div className="source-editor" data-testid="source-editor">
      <pre className="source-line-numbers" aria-label="源码行号">
        {lineNumbers}
      </pre>
      <textarea
        aria-label="策略源码编辑器"
        className="source-editor-textarea"
        spellCheck={false}
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
      />
    </div>
  );
}
