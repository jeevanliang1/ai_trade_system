type Props<T extends string> = {
  options: { label: string; value: T }[];
  value: T;
  onChange: (value: T) => void;
};

export function SegmentedControl<T extends string>({ options, value, onChange }: Props<T>) {
  return (
    <div className="segmented">
      {options.map((option) => (
        <button className={option.value === value ? "selected" : ""} key={option.value} onClick={() => onChange(option.value)}>
          {option.label}
        </button>
      ))}
    </div>
  );
}
