'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import styles from './ModelModal.module.css';

interface LLMModel {
  id?: string;
  name: string;
  hf_repo_id: string;
  gguf_filename: string;
  ram_required_mb: number;
  context_size: number;
  llamacpp_version_hash: string;
  parameter_count?: string;
  quantization?: string;
  recommended_tasks?: string[];
  llamacpp_args?: Record<string, any>;
}

interface ModelModalProps {
  initialData?: LLMModel | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ModelModal({ initialData, onClose, onSuccess }: ModelModalProps) {
  const [formData, setFormData] = useState<LLMModel>(() => initialData || {
    name: '',
    hf_repo_id: '',
    gguf_filename: '',
    ram_required_mb: 8192,
    context_size: 4096,
    llamacpp_version_hash: 'ff52ee9',
    parameter_count: '',
    quantization: '',
    recommended_tasks: [],
    llamacpp_args: {}
  });
  
  const [availableTasks, setAvailableTasks] = useState<string[]>([]);
  const [argsEntries, setArgsEntries] = useState<{key: string, value: string}[]>(() => {
    if (!initialData?.llamacpp_args) return [];
    return Object.entries(initialData.llamacpp_args).map(([k, v]) => ({ key: k, value: String(v) }));
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get('/models/tasks').then(data => setAvailableTasks(data)).catch(console.error);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    const finalArgs: Record<string, any> = {};
    for (const entry of argsEntries) {
      if (entry.key.trim()) {
        let val: any = entry.value.trim();
        if (val === 'true') val = true;
        else if (val === 'false') val = false;
        else if (!isNaN(Number(val)) && val !== '') val = Number(val);
        finalArgs[entry.key.trim()] = val;
      }
    }
    
    const payload = {
      ...formData,
      llamacpp_args: Object.keys(finalArgs).length > 0 ? finalArgs : null,
      parameter_count: formData.parameter_count || null,
      quantization: formData.quantization || null,
    };

    try {
      if (initialData?.id) {
        await apiClient.put(`/models/${initialData.id}`, payload);
      } else {
        await apiClient.post('/models', payload);
      }
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to save model');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? Number(value) : value
    }));
  };
  
  const handleTaskToggle = (task: string) => {
    setFormData(prev => {
      const tasks = prev.recommended_tasks || [];
      if (tasks.includes(task)) {
        return { ...prev, recommended_tasks: tasks.filter(t => t !== task) };
      } else {
        return { ...prev, recommended_tasks: [...tasks, task] };
      }
    });
  };

  const addArgRow = () => setArgsEntries(prev => [...prev, { key: '', value: '' }]);
  const removeArgRow = (idx: number) => setArgsEntries(prev => prev.filter((_, i) => i !== idx));
  const updateArgRow = (idx: number, field: 'key'|'value', val: string) => {
    setArgsEntries(prev => prev.map((item, i) => i === idx ? { ...item, [field]: val } : item));
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <h2>{initialData ? 'Edit Model' : 'Add a model'}</h2>
          <button className={styles.closeButton} onClick={onClose}>&times;</button>
        </div>
        
        {error && <div className={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label>Name</label>
            <input required type="text" name="name" value={formData.name} onChange={handleChange} placeholder="e.g. Llama-3-8B" />
          </div>

          <div className={styles.field}>
            <label>HuggingFace Repo ID</label>
            <input required type="text" name="hf_repo_id" value={formData.hf_repo_id} onChange={handleChange} placeholder="e.g. QuantFactory/Meta-Llama-3-8B-Instruct-GGUF" />
          </div>

          <div className={styles.field}>
            <label>GGUF Filename</label>
            <input required type="text" name="gguf_filename" value={formData.gguf_filename} onChange={handleChange} placeholder="e.g. Meta-Llama-3-8B-Instruct.Q4_K_M.gguf" />
          </div>

          <div className={styles.row}>
            <div className={styles.field}>
              <label>RAM Required (MB)</label>
              <input required type="number" name="ram_required_mb" value={formData.ram_required_mb} onChange={handleChange} />
            </div>
            
            <div className={styles.field}>
              <label>Context Size</label>
              <input required type="number" name="context_size" value={formData.context_size} onChange={handleChange} />
            </div>
            <div className={styles.field}>
              <label>llama.cpp Hash</label>
              <input required type="text" name="llamacpp_version_hash" value={formData.llamacpp_version_hash} onChange={handleChange} />
            </div>
          </div>
          
          <div className={styles.row}>
            <div className={styles.field}>
              <label>Parameter Count</label>
              <input type="text" name="parameter_count" value={formData.parameter_count || ''} onChange={handleChange} placeholder="e.g. 8B" />
            </div>
            <div className={styles.field}>
              <label>Quantization</label>
              <input type="text" name="quantization" value={formData.quantization || ''} onChange={handleChange} placeholder="e.g. Q4_K_M" />
            </div>
          </div>

          <div className={styles.field}>
            <label>Recommended Tasks</label>
            <div className={styles.taskGrid}>
              {availableTasks.map(task => (
                <label key={task} className={styles.taskCheckbox}>
                  <input 
                    type="checkbox" 
                    checked={(formData.recommended_tasks || []).includes(task)} 
                    onChange={() => handleTaskToggle(task)}
                  />
                  {task}
                </label>
              ))}
            </div>
          </div>

          <div className={styles.field}>
            <label>llama.cpp Arguments</label>
            <div className={styles.argsTable}>
              {argsEntries.map((entry, idx) => (
                <div key={idx} className={styles.argRow}>
                  <input type="text" placeholder="Key (e.g. -ngl)" value={entry.key} onChange={e => updateArgRow(idx, 'key', e.target.value)} />
                  <input type="text" placeholder="Value (e.g. 99)" value={entry.value} onChange={e => updateArgRow(idx, 'value', e.target.value)} />
                  <button type="button" onClick={() => removeArgRow(idx)} className={styles.removeArgBtn}>&times;</button>
                </div>
              ))}
              <button type="button" onClick={addArgRow} className={styles.addArgBtn}>+ Add Argument</button>
            </div>
          </div>

          <div className={styles.actions}>
            <button type="button" className={styles.cancelButton} onClick={onClose} disabled={loading}>Cancel</button>
            <button type="submit" className={styles.submitButton} disabled={loading}>
              {loading ? 'Saving...' : (initialData ? 'Update Model' : 'Add Model')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
