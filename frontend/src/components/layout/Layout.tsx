import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-slate-100">
      <Sidebar />
      <div className="ml-56">
        <Header />
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
