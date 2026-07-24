import { createTheme } from "@mantine/core";

export const theme = createTheme({
  primaryColor: "orange",
  primaryShade: 6,

  white: "#FFFFFF",
  black: "#1A1512",

  fontFamily: "Inter, system-ui, sans-serif",
  fontFamilyMonospace: "Monaco, Courier, monospace",

  headings: {
    fontFamily: "DM Serif Display, Inter, system-ui, sans-serif",
    sizes: {
      h1: {
        fontSize: "40px",
        lineHeight: "1.25",
        fontWeight: "700",
      },
      h2: {
        fontSize: "32px",
        lineHeight: "1.25",
        fontWeight: "700",
      },
      h3: {
        fontSize: "24px",
        lineHeight: "1.3",
        fontWeight: "700",
      },
      h4: {
        fontSize: "20px",
        lineHeight: "1.35",
        fontWeight: "650",
      },
    },
  },

  colors: {
    orange: [
      "#FEF5F1",
      "#FDE8DD",
      "#FBCFBA",
      "#F8AB88",
      "#F47D54",
      "#EE5D2F",
      "#D94518",
      "#B53515",
      "#932E18",
      "#782A17",
    ],

    red: [
      "#FFEAEA",
      "#FDD5D5",
      "#F2A9A9",
      "#EA7A7A",
      "#E25252",
      "#DE3939",
      "#DC2626",
      "#C41E1F",
      "#B0171A",
      "#9A0A14",
    ],
  },

  radius: {
    sm: "8px",
    md: "12px",
    lg: "16px",
  },

  defaultRadius: "md",

  spacing: {
    xs: "8px",
    sm: "12px",
    md: "16px",
    lg: "24px",
    xl: "32px",
  },

  shadows: {
    sm: "0 0px 8px rgba(0, 0, 0, 0.04)",
  },

  components: {
    Button: {
      defaultProps: {
        radius: "md",
      },
      styles: {
        root: {
          fontFamily: "Inter, system-ui, sans-serif",
          fontSize: "14px",
          fontWeight: 600,
        },
      },
    },

    TextInput: {
      defaultProps: {
        radius: "sm",
      },
      styles: {
        input: {
          fontFamily: "Inter, system-ui, sans-serif",
          fontSize: "16px",
          fontWeight: 400,
          lineHeight: "40px",
        },
      },
    },

    PasswordInput: {
      defaultProps: {
        radius: "sm",
      },
      styles: {
        input: {
          fontFamily: "Inter, system-ui, sans-serif",
          fontSize: "16px",
          fontWeight: 400,
          lineHeight: "40px",
        },
      },
    },

    Card: {
      defaultProps: {
        radius: "md",
        shadow: "sm",
        padding: "xl",
      },
    },

    Chip: {
      defaultProps: {
        type: "checkbox",
        variant: "light",
        size: "sm"
      }
    },

    Paper: {
      defaultProps: {
        p: "xl",
        withBorder: true,
        shadow: "sm",
        radius: "md",
      }
    },

    Modal: {
      styles: {
        title: {
          fontFamily: "Inter, system-ui, sans-serif",
          fontSize: "24px",
          fontWeight: 700,
          lineHeight: 1.2,
        },
      },
    },

  },
});
