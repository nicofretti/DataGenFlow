import type { Preview } from "@storybook/react-vite";
import React, { useEffect } from "react";
import { ThemeProvider as ShadcnThemeProvider } from "next-themes";
import "../index.css";

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      disable: true,
    },
  },
  decorators: [
    (Story, context) => {
      const theme = context.globals.theme || "light";

      useEffect(() => {
        if (theme === "dark") {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }
      }, [theme]);

      return (
        <ShadcnThemeProvider attribute="class" defaultTheme={theme} enableSystem={false} forcedTheme={theme}>
          <div className="p-4 min-h-screen bg-background text-foreground">
            <Story />
          </div>
        </ShadcnThemeProvider>
      );
    },
  ],
  globalTypes: {
    theme: {
      description: "Global theme for components",
      defaultValue: "light",
      toolbar: {
        title: "Theme",
        icon: "circlehollow",
        items: [
          { value: "light", icon: "circlehollow", title: "Light" },
          { value: "dark", icon: "circle", title: "Dark" },
        ],
        dynamicTitle: true,
      },
    },
  },
};

export default preview;
