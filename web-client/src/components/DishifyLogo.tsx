import welcomeBowlUrl from "../assets/welcome-bowl.svg";

export type DishifyLogoSize = "icon" | "compact" | "hero";

const LOGO_SIZES: Record<DishifyLogoSize, number> = {
  icon: 36,
  compact: 120,
  hero: 240,
};

type DishifyLogoProps = {
  size?: DishifyLogoSize;
  className?: string;
};

export function DishifyLogo({ size = "hero", className }: DishifyLogoProps) {
  const dimension = LOGO_SIZES[size];
  const classes = ["dishify-logo", `dishify-logo-${size}`, className].filter(Boolean).join(" ");

  return (
    <img
      src={welcomeBowlUrl}
      alt="Dishify"
      width={dimension}
      height={dimension}
      className={classes}
    />
  );
}
