import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
// One stylesheet for both UIs: the built-in page and this React app share the design tokens.
import "../../backend/app/static/app.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root missing from index.html");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
