import type { ReactNode } from "react";
import { Icon } from "./icons";

type ButtonProps = {
  children: ReactNode;
  icon?: string;
  iconAfter?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "subtle";
  size?: "sm" | "md" | "lg";
  href?: string;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  title?: string;
  className?: string;
};

export function Button({
  children,
  icon,
  iconAfter,
  variant = "secondary",
  size,
  href,
  onClick,
  type = "button",
  disabled,
  title,
  className = "",
}: ButtonProps) {
  const classes = ["btn", variant !== "secondary" ? variant : "", size || "", disabled ? "is-disabled" : "", className]
    .filter(Boolean)
    .join(" ");
  const body = (
    <>
      {icon ? <Icon name={icon} size={16} /> : null}
      <span>{children}</span>
      {iconAfter ? <Icon name={iconAfter} size={16} /> : null}
    </>
  );
  if (href && !disabled) {
    return (
      <a className={classes} href={href} title={title}>
        {body}
      </a>
    );
  }
  return (
    <button className={classes} type={type} onClick={onClick} disabled={disabled} title={title}>
      {body}
    </button>
  );
}

export function IconButton({
  name,
  label,
  onClick,
  size = 18,
}: {
  name: string;
  label: string;
  onClick?: () => void;
  size?: number;
}) {
  return (
    <button className="icon-btn" type="button" onClick={onClick} aria-label={label} title={label}>
      <Icon name={name} size={size} />
    </button>
  );
}
