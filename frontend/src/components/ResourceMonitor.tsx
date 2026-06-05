'use client';

import { useEffect, useState } from 'react';
import styles from './ResourceMonitor.module.css';

import { API_BASE_URL } from '@/lib/api';

interface Metrics {
  cpu_percent: number;
  ram_total_mb: number;
  ram_used_mb: number;
  ram_free_mb: number;
}

export default function ResourceMonitor() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    // Determine the WS URL (handling local dev vs production, custom ports, etc.)
    let wsUrl = "ws://localhost:8000/ws/metrics";
    try {
      const url = new URL(API_BASE_URL);
      const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${wsProtocol}//${url.host}/ws/metrics`;
    } catch (e) {
      console.error("Failed to parse NEXT_PUBLIC_API_URL for WebSocket, falling back", e);
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      wsUrl = `${protocol}//${host}:8000/ws/metrics`;
    }

    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMetrics(data);
      } catch (e) {
        console.error("Failed to parse metrics", e);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  if (!metrics) return null;

  const ramPercent = (metrics.ram_used_mb / metrics.ram_total_mb) * 100;
  const isDanger = metrics.ram_free_mb < 10240; // Less than 10GB free

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>System Resources</h3>
      
      <div className={styles.metrics}>
        <div className={styles.metricRow}>
          <span>CPU</span>
          <span className={styles.value}>{metrics.cpu_percent.toFixed(1)}%</span>
        </div>
        <div className={styles.progressBg}>
          <div 
            className={styles.progressFill} 
            style={{ width: `${metrics.cpu_percent}%` }}
          />
        </div>
      </div>

      <div className={styles.metrics}>
        <div className={styles.metricRow}>
          <span>RAM</span>
          <span className={styles.value}>
            {(metrics.ram_used_mb / 1024).toFixed(1)} / {(metrics.ram_total_mb / 1024).toFixed(1)} GB
          </span>
        </div>
        <div className={styles.progressBg}>
          <div 
            className={`${styles.progressFill} ${isDanger ? styles.danger : ''}`} 
            style={{ width: `${ramPercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}
