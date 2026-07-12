import { describe, expect, it } from "vitest";

import { theme } from "./theme";

describe("theme", () => {
  it("does not force a fixed button line-height so loading spinners stay centered", () => {
    const buttonStyles = theme.components?.Button?.styles;
    const styles = typeof buttonStyles === "object" ? buttonStyles : {};
    const rootStyles = "root" in styles ? styles.root : undefined;

    expect(rootStyles).not.toMatchObject({ lineHeight: expect.any(String) });
  });
});
