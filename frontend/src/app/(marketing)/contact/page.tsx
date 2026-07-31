import type { Metadata } from "next";
import MarketingShell from "@/components/marketing/Shell";
import ContactClient from "@/components/marketing/mkt2/ContactClient";

export const metadata: Metadata = {
  title: "Contact · PolicyAI",
  description:
    "Book a demo on your segment's regulations or talk to sales. We reply within one business day.",
};

export default function ContactPage() {
  return (
    <MarketingShell>
      <main className="mx-auto max-w-[1304px] px-5 pb-24 pt-12 md:px-8 md:pt-16">
        <ContactClient />
      </main>
    </MarketingShell>
  );
}
