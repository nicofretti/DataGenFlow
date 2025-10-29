import React from "react";
import ReactDOM from "react-dom/client";
import { BaseStyles, ThemeProvider } from "@primer/react";
import App from "./App";
import { Toaster } from "react-hot-toast";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <BaseStyles>
        <App />
        <Toaster position="top-right" />
      </BaseStyles>
    </ThemeProvider>
  </React.StrictMode>
);
