import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  metadataBase: new URL('https://whisplet.tobithedev.chatgpt.site'),
  title: 'Whisplet — Your voice, right on your Mac',
  description: 'Private local dictation for Apple Silicon Macs. Hold a key, speak, release. No account or subscription. Open-source, with optional S1-mini cleanup.',
  icons: { icon: '/whisplet.svg', apple: '/whisplet.svg' },
  openGraph: { title: 'Whisplet — Think it. Say it. There it is.', description: 'Local dictation. A little less typing. A little more you.', type: 'website' },
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
