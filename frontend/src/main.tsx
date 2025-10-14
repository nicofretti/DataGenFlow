import React from "react";
import ReactDOM from "react-dom/client";
import { ThemeProvider, BaseStyles } from "@primer/react";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <BaseStyles>
        <App />
      </BaseStyles>
    </ThemeProvider>
  </React.StrictMode>
);
