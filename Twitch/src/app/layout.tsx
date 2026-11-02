import type { Metadata } from "next";
import "./globals.css";
import "./subpages.css";

export const metadata: Metadata = {
  title: "Afterlife — Every streamer has a story",
  description: "A video-first encyclopedia for Twitch communities.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
