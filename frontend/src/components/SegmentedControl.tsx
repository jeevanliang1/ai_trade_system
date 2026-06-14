type Props<T extends string> = {
  options: { label: string; value: T }[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
};

export function SegmentedControl<T extends string>({ options, value, onChange, disabled = false }: Props<T>) {
  return (
    <div className="segmented">
      {options.map((option) => (
        <button className={option.value === value ? "selected" : ""} disabled={disabled} key={option.value} onClick={() => onChange(option.value)}>
          {option.label}
        </button>
      ))}
    </div>
  );
}
