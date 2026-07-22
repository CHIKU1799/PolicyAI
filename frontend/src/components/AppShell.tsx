"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { Toaster } from "@/components/Toast";

// Client shell owning the mobile navigation drawer. On lg+ the sidebar is the
// familiar static column; below that it slides in over an overlay.
export default function AppShell({ children }: { children: React.ReactNode }) {
  const [navOpen, setNavOpen] = useState(false);
  const pathname = usePathname();

  // Navigating closes the drawer; so does Escape.
  useEffect(() => setNavOpen(false), [pathname]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setNavOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="flex h-dvh overflow-hidden">
      {navOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/35 backdrop-blur-[2px] lg:hidden"
          onClick={() => setNavOpen(false)}
          aria-hidden
        />
      )}
      <div
        className={
          "fixed inset-y-0 left-0 z-50 transition-transform duration-200 ease-out lg:static lg:z-auto lg:translate-x-0 " +
          (navOpen ? "translate-x-0" : "-translate-x-full")
        }
      >
        <Sidebar />
      </div>
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Topbar onMenu={() => setNavOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="anim-in mx-auto max-w-[1280px] px-4 pb-16 pt-4 sm:px-7 sm:pt-6">{children}</div>
        </main>
      </div>
      <Toaster />
    </div>
  );
}
