'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import styles from './Sidebar.module.css';
import ResourceMonitor from './ResourceMonitor';

interface ChatSession {
  id: string;
  title?: string;
}

interface SidebarProps {
  isCollapsed?: boolean | null;
  toggleSidebar?: () => void;
}

export default function Sidebar({
  isCollapsed = false,
  toggleSidebar = () => {}
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const currentSessionId = searchParams.get('session_id');

  const fetchSessions = async () => {
    try {
      const data = await apiClient.get('/chat/sessions');
      setSessions(data); // show all recent chats
    } catch (err) {
      console.error('Failed to fetch sessions in Sidebar:', err);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [pathname]);

  useEffect(() => {
    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this discussion?')) return;
    try {
      await apiClient.delete(`/chat/sessions/${id}`);
      fetchSessions();
      if (currentSessionId === id) {
        router.push('/chat');
      }
    } catch (err) {
      console.error('Failed to delete session from Sidebar:', err);
    }
  };

  const handleNewChat = async (e: React.MouseEvent) => {
    e.preventDefault();
    try {
      const newSession = await apiClient.post('/chat/sessions', {
        title: 'New Discussion'
      });
      fetchSessions();
      router.push(`/chat?session_id=${newSession.id}`);
    } catch (err) {
      console.error('Failed to create session from Sidebar:', err);
    }
  };

  const navItems = [
    { name: 'Models', href: '/models', icon: '🤖' },
    { name: 'Agents', href: '/agents', icon: '🕵️' },
    { 
      name: 'Chat', 
      href: sessions.length > 0 ? `/chat?session_id=${sessions[0].id}` : '/chat', 
      icon: '💬' 
    }
  ];

  return (
    <aside className={`${styles.sidebar} ${isCollapsed ? styles.collapsed : ''}`}>
      <div className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoGradient}>PLAM</span>
        </div>
        {!isCollapsed && (
          <button 
            className={styles.closeButton} 
            onClick={toggleSidebar}
            aria-label="Collapse Sidebar"
          >
            ❮
          </button>
        )}
      </div>
      <nav className={styles.nav}>
        {navItems.map(item => {
          const isActive = item.name === 'Chat'
            ? pathname.startsWith('/chat')
            : pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <div key={item.name} className={styles.navGroup}>
              <Link 
                href={item.href}
                className={`${styles.navLink} ${isActive ? styles.active : ''}`}
                title={isCollapsed ? item.name : undefined}
              >
                <span className={styles.icon}>{item.icon}</span>
                <span className={styles.name}>{item.name}</span>
              </Link>
              
              {item.name === 'Chat' && (
                <div className={styles.subMenu}>
                  <button onClick={handleNewChat} className={styles.subMenuItemBtn}>
                    ➕ New Chat
                  </button>
                   {sessions.map(s => {
                    const isSessionActive = pathname.startsWith('/chat') && currentSessionId === s.id;
                    return (
                      <div key={s.id} className={styles.subMenuItemContainer}>
                        <Link
                          href={`/chat?session_id=${s.id}`}
                          className={`${styles.subMenuItem} ${isSessionActive ? styles.subActive : ''}`}
                          title={s.title || 'Discussion'}
                        >
                          💬 {s.title || 'Discussion'}
                        </Link>
                        {!isCollapsed && (
                          <button 
                            className={styles.deleteSubMenuItemBtn}
                            onClick={(e) => handleDeleteSession(e, s.id)}
                            title="Delete Discussion"
                            aria-label="Delete Discussion"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>
      <div className={styles.spacer} />
      <div className={styles.resourceMonitorContainer}>
        <ResourceMonitor />
      </div>
    </aside>
  );
}



