import AppShell from "@/components/AppShell";
import OnboardingTour from "@/components/OnboardingTour";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AppShell>{children}</AppShell>
      <OnboardingTour />
    </>
  );
}
