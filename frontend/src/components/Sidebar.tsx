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

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const currentSessionId = searchParams.get('session_id');

  const fetchSessions = async () => {
    try {
      const data = await apiClient.get('/chat/sessions');
      setSessions(data.slice(0, 5)); // show top 5 recent chats
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
    { name: 'Chat', href: '/chat', icon: '💬' }
  ];

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <span className={styles.logoGradient}>PLAM</span>
      </div>
      <nav className={styles.nav}>
        {navItems.map(item => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <div key={item.href} className={styles.navGroup}>
              <Link 
                href={item.href}
                className={`${styles.navLink} ${isActive ? styles.active : ''}`}
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
                      <Link
                        key={s.id}
                        href={`/chat?session_id=${s.id}`}
                        className={`${styles.subMenuItem} ${isSessionActive ? styles.subActive : ''}`}
                        title={s.title || 'Discussion'}
                      >
                        💬 {s.title || 'Discussion'}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>
      <div className={styles.spacer} />
      <ResourceMonitor />
    </aside>
  );
}


