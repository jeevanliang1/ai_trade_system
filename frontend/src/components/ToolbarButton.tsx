import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  icon?: ReactNode;
  variant?: "primary" | "success" | "ghost";
  disabled?: boolean;
  onClick?: () => void;
};

export function ToolbarButton({ children, icon, variant = "ghost", disabled, onClick }: Props) {
  return (
    <button className={`toolbar-button ${variant}`} disabled={disabled} onClick={onClick}>
      {icon}
      <span>{children}</span>
    </button>
  );
}
