'use client';

import { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import styles from './LayoutWrapper.module.css';

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const [isMobile, setIsMobile] = useState(false);
  const [isDesktopCollapsed, setIsDesktopCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    setTimeout(() => {
      setIsMounted(true);
      
      const stored = localStorage.getItem('sidebar-desktop-collapsed');
      if (stored !== null) {
        setIsDesktopCollapsed(stored === 'true');
      }

      checkIsMobile();
    }, 0);

    window.addEventListener('resize', checkIsMobile);
    return () => window.removeEventListener('resize', checkIsMobile);
  }, []);


  const toggleSidebar = () => {
    if (isMobile) {
      setIsMobileOpen(prev => !prev);
    } else {
      setIsDesktopCollapsed(prev => {
        const next = !prev;
        localStorage.setItem('sidebar-desktop-collapsed', String(next));
        return next;
      });
    }
  };

  // Determine current active collapsed state
  // On desktop: collapsed if isDesktopCollapsed is true
  // On mobile: collapsed if isMobileOpen is false (i.e. sidebar is closed)
  const activeCollapsed = isMobile ? !isMobileOpen : isDesktopCollapsed;

  // CSS classes to apply
  // Only apply when mounted to prevent SSR hydration mismatch.
  // When not mounted, it has no override class, letting CSS media queries handle default styles.
  const collapsedClass = isMounted
    ? (activeCollapsed ? styles.collapsed : styles.expanded)
    : '';

  return (
    <div className={`${styles.layoutContainer} ${collapsedClass}`}>
      <Sidebar 
        isCollapsed={activeCollapsed} 
        toggleSidebar={toggleSidebar} 
      />

      
      {/* Mobile Backdrop Overlay */}
      {isMounted && isMobile && isMobileOpen && (
        <div className={styles.backdrop} onClick={toggleSidebar} />
      )}

      {/* Floating burger menu button:
          - Floats in top-left on mobile when menu is closed.
          - Centers in the 60px sidebar on desktop when collapsed.
      */}
      {isMounted && activeCollapsed && (
        <button 
          className={styles.floatingBurger} 
          onClick={toggleSidebar}
          aria-label="Toggle Navigation Sidebar"
        >
          ☰
        </button>
      )}

      <main className={styles.mainContent}>
        {children}
      </main>
    </div>
  );
}
