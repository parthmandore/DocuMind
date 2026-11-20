import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNav } from './TopNav';
import { storage } from '@/utils/storage';

export const AppLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    return storage.getSidebarCollapsed();
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleToggleCollapse = (): void => {
    setCollapsed((prev) => {
      const next = !prev;
      storage.setSidebarCollapsed(next);
      return next;
    });
  };

  const handleToggleMobile = (): void => {
    setMobileOpen((prev) => !prev);
  };

  const handleCloseMobile = (): void => {
    setMobileOpen(false);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-app text-content-primary font-sans">
      {/* Primary Sidebar (Responsive drawer on mobile, inline on desktop) */}
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={handleToggleCollapse}
        mobileOpen={mobileOpen}
        onCloseMobile={handleCloseMobile}
      />

      {/* Main Content Column */}
      <div className="flex flex-col flex-1 min-w-0 h-full overflow-hidden">
        {/* Top Navigation */}
        <TopNav onToggleMobileMenu={handleToggleMobile} />

        {/* Dynamic Page Container */}
        <main className="flex-1 overflow-y-auto bg-app p-4 sm:p-6 lg:p-6 flex flex-col">
          <div className="max-w-7xl mx-auto w-full flex-1 flex flex-col min-h-0">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
