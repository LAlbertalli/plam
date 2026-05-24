'use client';

import { useEffect, useState, useRef, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import styles from './page.module.css';


interface Agent {
  id: string;
  name: string;
}

interface ChatSession {
  id: string;
  title?: string;
  created_at: string;
}

interface ShortTermMemory {
  id: string;
  session_id: string;
  agent_id?: string | null;
  sequence_id: number;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content?: string;
  thinking_trace?: string;
  timestamp: string;
}

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionIdParam = searchParams.get('session_id');

  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ShortTermMemory[]>([]);
  
  // Streaming message buffer
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState(false);
  
  // Form input
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);

  // Thought Drawer toggle states
  const [openThoughtIds, setOpenThoughtIds] = useState<Record<string, boolean>>({});
  const [showStreamingThoughts, setShowStreamingThoughts] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchAgents = async () => {
    try {
      const data = await apiClient.get('/agents');
      setAgents(data);
      if (data.length > 0) {
        setSelectedAgentId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err);
    }
  };

  const fetchSessions = async () => {
    try {
      const data = await apiClient.get('/chat/sessions');
      setSessions(data);
      if (data.length > 0 && !currentSessionId && !sessionIdParam) {
        router.replace(`/chat?session_id=${data[0].id}`);
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = useCallback(async (sessionId: string) => {
    try {
      const data = await apiClient.get(`/chat/sessions/${sessionId}/history`);
      setMessages(data);
    } catch (err) {
      console.error('Failed to fetch session history:', err);
    }
  }, []);

  useEffect(() => {
    if (sessionIdParam) {
      setCurrentSessionId(sessionIdParam);
    }
  }, [sessionIdParam]);

  useEffect(() => {
    fetchAgents();

    fetchSessions();
  }, []);

  useEffect(() => {
    if (currentSessionId) {
      fetchHistory(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId, fetchHistory]);

  useEffect(() => {
    if (messagesEndRef.current?.scrollIntoView) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamingMessage]);

  const handleCreateSession = async () => {
    try {
      const newSession = await apiClient.post('/chat/sessions', {
        title: 'New Discussion'
      });
      setSessions(prev => [newSession, ...prev]);
      router.push(`/chat?session_id=${newSession.id}`);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this session?')) return;
    try {
      await apiClient.delete(`/chat/sessions/${id}`);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (currentSessionId === id) {
        router.push('/chat');
      }
    } catch (err) {
      console.error('Failed to delete session:', err);

    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !currentSessionId || !selectedAgentId || isStreaming) return;

    const userMsg = input.trim();
    setInput('');
    setIsStreaming(true);
    setStreamingMessage('');
    setShowStreamingThoughts(false);


    // Prepend user message locally to speed up UI response
    const tempUserMsg: ShortTermMemory = {
      id: 'temp-user',
      session_id: currentSessionId,
      agent_id: null,
      sequence_id: messages.length,
      role: 'user',
      content: userMsg,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${API_BASE_URL}/chat/sessions/${currentSessionId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: selectedAgentId, content: userMsg })
      });

      if (!response.ok) {
        throw new Error('Streaming failed');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');

      if (!reader) return;

      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Save the last partial line back to buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr);
              if (data.index !== undefined && data.text !== undefined) {
                setStreamingMessage(prev => prev.slice(0, data.index) + data.text);
              } else if (data.error) {
                setStreamingMessage(prev => prev + `\n[ERROR: ${data.error}]`);
              } else if (data.done) {
                // Fetch updated history to replace temporary streaming messages with actual DB record
                await fetchHistory(currentSessionId);
                setIsStreaming(false);
                setStreamingMessage('');
                fetchSessions(); // Refresh titles
                break;
              }
            } catch (err) {
              // Ignore partial JSON parses
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      setStreamingMessage(prev => prev + '\n[Connection lost during generation]');
      setIsStreaming(false);
    }
  };

  const toggleThoughts = (id: string) => {
    setOpenThoughtIds(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  if (loading) return <div className={styles.container}>Loading chat interface...</div>;

  return (
    <div className={styles.chatLayout}>
      {/* Session Sidebar */}
      <aside className={styles.sidebar}>
        <button className={styles.newChatBtn} onClick={handleCreateSession}>
          ➕ New Chat
        </button>
        <div className={styles.sessionList}>
          {sessions.map(s => (
            <div 
              key={s.id} 
              className={`${styles.sessionItem} ${currentSessionId === s.id ? styles.active : ''}`}
              onClick={() => router.push(`/chat?session_id=${s.id}`)}
            >

              <span className={styles.sessionIcon}>💬</span>
              <span className={styles.sessionTitle}>{s.title || 'Discussion'}</span>
              <button 
                className={styles.deleteSessionBtn}
                onClick={(e) => handleDeleteSession(e, s.id)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main Conversation Pane */}
      <div className={styles.chatArea}>
        {currentSessionId ? (
          <>
            {/* Topbar selectors */}
            <div className={styles.topbar}>
              <div className={styles.topbarLeft}>
                <span className={styles.activeSessionIcon}>💬</span>
                <span className={styles.activeSessionTitle}>
                  {sessions.find(s => s.id === currentSessionId)?.title || 'Discussion'}
                </span>
              </div>
              
              <div className={styles.agentSelectContainer}>
                <label className={styles.agentLabel}>Talking to</label>
                <select 
                  value={selectedAgentId} 
                  onChange={e => setSelectedAgentId(e.target.value)} 
                  className={styles.agentSelect}
                >
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Scrollable Message List */}
            <div className={styles.messageThread}>
              {messages.map((msg) => {
                const isUser = msg.role === 'user';
                return (
                  <div key={msg.id} className={`${styles.messageRow} ${isUser ? styles.userRow : styles.agentRow}`}>
                    <div className={styles.avatar}>{isUser ? '👤' : '🕵️'}</div>
                    <div className={styles.bubble}>
                      <span className={styles.senderName}>{isUser ? 'You' : 'Agent'}</span>
                      
                      {/* Thought process folding drawer */}
                      {msg.thinking_trace && (
                        <div className={styles.thoughtContainer}>
                          <button 
                            type="button"
                            className={styles.thoughtToggle} 
                            onClick={() => toggleThoughts(msg.id)}
                          >
                            🧠 {openThoughtIds[msg.id] ? 'Hide thinking ▴' : 'Show thinking ▾'}
                          </button>
                          {openThoughtIds[msg.id] && (
                            <pre className={styles.thoughtTrace}>{msg.thinking_trace}</pre>
                          )}
                        </div>
                      )}

                      <p className={styles.messageContent}>{msg.content}</p>
                    </div>
                  </div>
                );
              })}

              {/* Waiting spinner before stream starts */}
              {isStreaming && !streamingMessage && (
                <div className={`${styles.messageRow} ${styles.agentRow}`}>
                  <div className={styles.avatar}>🕵️</div>
                  <div className={styles.bubble}>
                    <span className={styles.senderName}>Agent</span>
                    <div className={styles.spinnerContainer}>
                      <div className={styles.spinner}>
                        <span className={styles.dot}></span>
                        <span className={styles.dot}></span>
                        <span className={styles.dot}></span>
                      </div>
                      <span className={styles.spinnerText}>Agent is preparing a response...</span>
                    </div>
                  </div>
                </div>
              )}

              {isStreaming && streamingMessage && (() => {
                const hasThoughts = streamingMessage.includes('<thought>');
                let streamingThoughts = '';
                let streamingContent = streamingMessage;

                if (hasThoughts) {
                  const parts = streamingMessage.split('</thought>');
                  streamingThoughts = parts[0].replace('<thought>', '').trim();
                  streamingContent = parts[1] ? parts[1].trim() : '';
                }



                return (
                  <div className={`${styles.messageRow} ${styles.agentRow}`}>
                    <div className={styles.avatar}>🕵️</div>
                    <div className={styles.bubble}>
                      <span className={styles.senderName}>
                        {isStreaming ? 'Agent (typing...)' : 'Agent'}
                      </span>
                      
                      {hasThoughts && streamingThoughts && (
                        <div className={styles.thoughtContainer}>
                          <button 
                            type="button"
                            className={styles.thoughtToggle} 
                            onClick={() => setShowStreamingThoughts(!showStreamingThoughts)}
                          >
                            🧠 {showStreamingThoughts ? 'Hide thinking ▴' : 'Show thinking ▾'}
                          </button>
                          {showStreamingThoughts && (
                            <pre className={styles.thoughtTrace}>{streamingThoughts}</pre>
                          )}
                        </div>
                      )}
                      
                      {streamingContent && (
                        <p className={styles.messageContent}>{streamingContent}</p>
                      )}
                    </div>
                  </div>
                );
              })()}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Input Form Box */}
            <form onSubmit={handleSendMessage} className={styles.inputContainer}>
              <textarea 
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
                placeholder="Type a message, press Enter to send..."
                className={styles.chatInput}
                rows={2}
                disabled={isStreaming}
              />
              <button 
                type="submit" 
                className={styles.sendBtn}
                disabled={!input.trim() || isStreaming}
              >
                ⚡ Send
              </button>
            </form>
          </>
        ) : (
          <div className={styles.emptyState}>
            <span className={styles.emptyIcon}>💬</span>
            <h2>No Conversations Selected</h2>
            <p>Create a chat session from the sidebar to start prompting local agents.</p>
            <button className={styles.emptyBtn} onClick={handleCreateSession}>Start a Chat</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', color: '#64748b' }}>Loading chat interface...</div>}>
      <ChatPageContent />
    </Suspense>
  );
}

