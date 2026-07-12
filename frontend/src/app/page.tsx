import { landingHtml } from "./(marketing)/landing";

// Public marketing landing page. The product lives behind /login -> /dashboard.
export default function Home() {
  return <div dangerouslySetInnerHTML={{ __html: landingHtml }} />;
}
