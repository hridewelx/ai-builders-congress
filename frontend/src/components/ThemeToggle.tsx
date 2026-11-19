import { useEffect, useState } from "react";
import { Icon } from "./ui";

/** The theme chooser that lives in /static/theme.js, surfaced in React. */
type ThemeName = "light" | "dark";

declare global {
  interface Window {
    LotlineTheme?: {
      set: (theme: ThemeName) => void;
      current: () => ThemeName;
    };
  }
}

function currentTheme(): ThemeName {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeName>(currentTheme);

  useEffect(() => {
    setTheme(currentTheme());
  }, []);

  const flip = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    const next: ThemeName = theme === "dark" ? "light" : "dark";
    window.LotlineTheme?.set(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      window.localStorage.setItem("ll-theme", next);
    } catch {
      /* preference simply does not persist */
    }
    setTheme(next);
  };

  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";

  return (
    <button
      className="theme-toggle"
      type="button"
      onClick={(event) => flip(event)}
      aria-pressed={theme === "dark"}
      aria-label={label}
      title={label}
      data-theme-toggle=""
    >
      {theme === "dark" ? <Icon name="sun" size={16} /> : <Icon name="moon" size={16} />}
    </button>
  );
}
