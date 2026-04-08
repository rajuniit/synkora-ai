'use client'

// Auth is already guarded by the parent (dashboard) layout.
// This layout only overrides the container to be full-screen.
export default function ChatLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 bg-white">
      {children}
    </div>
  )
}
