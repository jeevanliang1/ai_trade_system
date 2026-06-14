type Props = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
};

export function Switch({ checked, onChange, label }: Props) {
  return (
    <label className="switch">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.currentTarget.checked)} />
    </label>
  );
}
