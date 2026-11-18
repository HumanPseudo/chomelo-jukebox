import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./styles/global.css"
import "./styles/shell.css"
import "./styles/auth.css"
import "./styles/jukebox.css"
import "./styles/admin.css"
import { App } from "./App"
import { AdminApp } from "./AdminApp"

const RootApp = import.meta.env.VITE_ENTRY === "admin" ? AdminApp : App

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RootApp />
  </StrictMode>,
)
