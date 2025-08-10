import type { Metadata } from "next";
import "./globals.css"; // Импорт globals.css (если файл в app/globals.css)

export const metadata: Metadata = {
  title: "LLM chat",
  description: "чат с авторизацией",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}