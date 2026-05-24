'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import ModelModal from '@/components/ModelModal';
import styles from './page.module.css';


interface LLMModel {
  id: string;
  name: string;
  hf_repo_id: string;
  gguf_filename: string;
  status: 'stopped' | 'running' | 'downloading' | 'error';
  ram_required_mb: number;
  context_size: number;
  llamacpp_version_hash: string;
  parameter_count?: string;
  quantization?: string;
  recommended_tasks?: string[];
  llamacpp_args?: Record<string, any>;
  local_path?: string | null;
}

export default function ModelsPage() {
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalMode, setModalMode] = useState<'add' | 'edit' | null>(null);
  const [editingModel, setEditingModel] = useState<LLMModel | null>(null);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  const fetchModels = async () => {
    try {
      const data = await apiClient.get('/models');
      setModels(data);
    } catch (error) {
      console.error('Failed to fetch models:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
    const interval = setInterval(fetchModels, 5000); // Poll status
    return () => clearInterval(interval);
  }, []);

  const handleDownload = async (id: string) => {
    setOpenDropdown(null);
    try {
      await apiClient.post(`/models/${id}/download`, {});
      fetchModels();
    } catch (error) {
      console.error('Failed to start download:', error);
    }
  };

  const handleStart = async (id: string) => {
    setOpenDropdown(null);
    try {
      await apiClient.post(`/models/${id}/start`, {});
      fetchModels();
    } catch (error) {
      console.error('Failed to start model:', error);
    }
  };

  const handleStop = async (id: string) => {
    setOpenDropdown(null);
    try {
      await apiClient.post(`/models/${id}/stop`, {});
      fetchModels();
    } catch (error) {
      console.error('Failed to stop model:', error);
    }
  };

  const handleDelete = async (id: string) => {
    setOpenDropdown(null);
    if (!confirm('Are you sure you want to delete this model configuration? This will also remove the GGUF file if downloaded.')) return;
    try {
      await apiClient.delete(`/models/${id}`);
      fetchModels();
    } catch (error) {
      console.error('Failed to delete model:', error);
    }
  };

  const openEdit = (model: LLMModel) => {
    setEditingModel(model);
    setModalMode('edit');
    setOpenDropdown(null);
  };

  if (loading) return <div className={styles.container}>Loading models...</div>;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Model Management</h1>
        <button className={styles.addButton} onClick={() => setModalMode('add')}>Add a model</button>
      </header>

      <div className={styles.grid}>
        {models.map((model) => (
          <div key={model.id} className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardHeaderTop}>
                <Link href={`/models/${model.id}`} className={styles.modelNameLink}>
                  {model.name}
                </Link>
                
                <div className={styles.dropdown}>
                  <button 
                    className={styles.dropdownTrigger}
                    onClick={() => setOpenDropdown(openDropdown === model.id ? null : model.id)}
                  >
                    Actions ▾
                  </button>
                  {openDropdown === model.id && (
                    <div className={styles.dropdownMenu}>
                      <button className={styles.dropdownItem} onClick={() => openEdit(model)}>Edit</button>
                      <Link href={`/models/${model.id}`} className={styles.dropdownLinkItem}>
                        Configure Rules 🛡️
                      </Link>
                      
                      {model.status === 'stopped' && (
                        <button className={styles.dropdownItem} onClick={() => handleStart(model.id)}>Start</button>
                      )}
                      
                      {model.status === 'running' && (
                        <button className={styles.dropdownItem} onClick={() => handleStop(model.id)}>Stop</button>
                      )}

                      <button 
                        className={styles.dropdownItem} 
                        onClick={() => handleDownload(model.id)}
                        disabled={model.local_path != null || model.status === 'downloading' || model.status === 'running'}
                      >
                        {model.local_path != null ? 'Downloaded' : (model.status === 'downloading' ? 'Downloading...' : 'Download')}
                      </button>
                      
                      <button className={`${styles.dropdownItem} ${styles.danger}`} onClick={() => handleDelete(model.id)}>Delete</button>
                    </div>
                  )}
                </div>
              </div>
              
              <div className={styles.pills}>
                <span className={`${styles.pill} ${styles.status} ${styles[model.status]}`}>{model.status}</span>
                <span className={`${styles.pill} ${styles.ram}`}>{(model.ram_required_mb / 1024).toFixed(1)} GB</span>
                {model.parameter_count && <span className={`${styles.pill} ${styles.size}`}>{model.parameter_count}</span>}
                {model.quantization && <span className={`${styles.pill} ${styles.quant}`}>{model.quantization}</span>}
                {model.recommended_tasks?.map(task => (
                  <span key={task} className={`${styles.pill} ${styles.task}`}>{task}</span>
                ))}
              </div>
            </div>
            

          </div>
        ))}
      </div>

      {modalMode && (
        <ModelModal 
          initialData={modalMode === 'edit' ? editingModel : null}
          onClose={() => {
            setModalMode(null);
            setEditingModel(null);
          }} 
          onSuccess={() => {
            setModalMode(null);
            setEditingModel(null);
            fetchModels();
          }} 
        />
      )}
    </div>
  );
}
