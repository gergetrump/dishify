import type { ReactNode } from "react";

import { DishifyLogo } from "./DishifyLogo";

type BrandedEmptyStateProps = {
  children: ReactNode;
};

export function BrandedEmptyState({ children }: BrandedEmptyStateProps) {
  return (
    <div className="branded-empty-state">
      <DishifyLogo size="compact" />
      {children}
    </div>
  );
}
