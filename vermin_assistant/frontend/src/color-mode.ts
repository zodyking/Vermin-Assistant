export type ColorMode = "light" | "dark";

function channel(value: number): number {
  const scaled = value / 255;
  return scaled <= 0.04045 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4;
}

function luminance(color: string): number | null {
  const value = color.trim().toLowerCase();
  const hex = value.match(/^#([\da-f]{3}|[\da-f]{6})$/);
  if (hex) {
    const raw = hex[1];
    const full = raw.length === 3 ? raw.split("").map((part) => part + part).join("") : raw;
    const red = parseInt(full.slice(0, 2), 16);
    const green = parseInt(full.slice(2, 4), 16);
    const blue = parseInt(full.slice(4, 6), 16);
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue);
  }
  const rgb = value.match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/);
  if (!rgb) return null;
  return (
    0.2126 * channel(Number(rgb[1])) +
    0.7152 * channel(Number(rgb[2])) +
    0.0722 * channel(Number(rgb[3]))
  );
}

function systemMode(): ColorMode {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Follow the Home Assistant theme when this panel is inside ingress. */
export function readColorMode(): ColorMode {
  try {
    if (window.parent !== window) {
      const background = getComputedStyle(window.parent.document.documentElement)
        .getPropertyValue("--primary-background-color")
        .trim();
      const value = luminance(background);
      if (value != null) return value < 0.45 ? "dark" : "light";
    }
  } catch {
    return systemMode();
  }
  return systemMode();
}
