import Sidebar from "@/components/Sidebar";
import AlertFeed from "@/components/AlertFeed";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center justify-between border-b border-[var(--border)] bg-white px-6">
          <div className="text-sm text-[var(--muted)]">
            Indian financial-sector compliance
          </div>
          <div className="flex items-center gap-3">
            <AlertFeed />
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#4b40c4] text-xs font-semibold text-white">
              CO
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
