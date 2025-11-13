import { useState, createContext, useContext } from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { Box, IconButton, ThemeProvider, useTheme, Heading, Text } from "@primer/react";
import {
  SunIcon,
  MoonIcon,
  BeakerIcon,
  ChecklistIcon,
  WorkflowIcon,
  GearIcon,
} from "@primer/octicons-react";
import Generator from "./pages/Generator";
import Review from "./pages/Review";
import Pipelines from "./pages/Pipelines";
import Settings from "./pages/Settings";
import GlobalJobIndicator from "./components/GlobalJobIndicator";
import { JobProvider } from "./contexts/JobContext";
import { useTheme as shadcnUseTheme, ThemeProvider as ShadcnThemeProvider } from "next-themes";
import { Toaster } from "./components/ui/sonner";

// context to control navigation visibility
const NavigationContext = createContext<{
  hideNavigation: boolean;
  setHideNavigation: (hide: boolean) => void;
}>({
  hideNavigation: false,
  setHideNavigation: () => {},
});

export const useNavigation = () => useContext(NavigationContext);

function Navigation() {
  const location = useLocation();
  const { resolvedColorScheme, setColorMode } = useTheme();
  const { setTheme } = shadcnUseTheme();
  const isDark = resolvedColorScheme === "dark";
  const { hideNavigation } = useNavigation();

  const navItems = [
    { path: "/pipelines", label: "Pipelines", icon: WorkflowIcon },
    { path: "/", label: "Generator", icon: BeakerIcon },
    { path: "/review", label: "Review", icon: ChecklistIcon },
    { path: "/settings", label: "Settings", icon: GearIcon },
  ];

  const handleToggleTheme = () => {
    const newMode = isDark ? "light" : "dark";
    setColorMode(newMode);
    setTheme(newMode);
    localStorage.setItem("colorMode", newMode);
  };

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      {/* left sidebar */}
      {!hideNavigation && (
        <Box
          sx={{
            width: 240,
            borderRight: "1px solid",
            borderColor: "border.default",
            bg: "canvas.subtle",
            display: "flex",
            flexDirection: "column",
            position: "fixed",
            height: "100vh",
            overflowY: "auto",
          }}
        >
          {/* brand */}
          <Box sx={{ p: 4, borderBottom: "1px solid", borderColor: "border.default" }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
              <img
                src="/logo.png"
                alt="DataGenFlow Logo"
                style={{ width: "40px", height: "40px" }}
              />
              <Heading sx={{ fontSize: 3, color: "fg.default" }}>DataGenFlow</Heading>
            </Box>
            <GlobalJobIndicator />
          </Box>

          {/* navigation links */}
          <Box sx={{ flex: 1, p: 3 }}>
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Box
                  key={item.path}
                  as={Link}
                  to={item.path}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    p: 2,
                    mb: 1,
                    borderRadius: 2,
                    textDecoration: "none",
                    color: isActive ? "fg.default" : "fg.muted",
                    bg: isActive ? "accent.subtle" : "transparent",
                    fontWeight: isActive ? "bold" : "normal",
                    "&:hover": {
                      bg: isActive ? "accent.subtle" : "neutral.subtle",
                    },
                    transition: "all 0.2s",
                  }}
                >
                  <item.icon size={20} />
                  <Text sx={{ fontSize: 2 }}>{item.label}</Text>
                </Box>
              );
            })}
          </Box>

          {/* theme toggle at bottom */}
          <Box sx={{ p: 3, borderTop: "1px solid", borderColor: "border.default" }}>
            <IconButton
              icon={isDark ? SunIcon : MoonIcon}
              aria-label="Toggle theme"
              onClick={handleToggleTheme}
              variant="invisible"
              size="large"
              sx={{ width: "100%" }}
            />
          </Box>
        </Box>
      )}

      {/* main content */}
      <Box
        sx={{
          flex: 1,
          ml: hideNavigation ? 0 : "240px",
          p: hideNavigation ? 0 : 4,
          bg: "canvas.default",
        }}
      >
        <Box sx={{ maxWidth: hideNavigation ? "none" : 1280, mx: "auto" }}>
          <Routes>
            <Route path="/" element={<Generator />} />
            <Route path="/review" element={<Review />} />
            <Route path="/pipelines" element={<Pipelines />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Box>
      </Box>
    </Box>
  );
}

export default function App() {
  const [colorMode] = useState<"light" | "dark" | "auto">(() => {
    // read from localStorage or default to light
    const stored = localStorage.getItem("colorMode");
    if (stored === "dark" || stored === "light" || stored === "auto") {
      return stored;
    }
    return "light";
  });

  const [hideNavigation, setHideNavigation] = useState(false);

  // @todo: remove primer in favor of shadcn themes
  return (
    <ShadcnThemeProvider
      defaultTheme="system"
      attribute="class"
      enableSystem
      storageKey="colorMode"
    >
      <ThemeProvider colorMode={colorMode}>
        <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
          <JobProvider>
            <NavigationContext.Provider value={{ hideNavigation, setHideNavigation }}>
              <Navigation />
            </NavigationContext.Provider>
            <Toaster />
          </JobProvider>
        </BrowserRouter>
      </ThemeProvider>
    </ShadcnThemeProvider>
  );
}
