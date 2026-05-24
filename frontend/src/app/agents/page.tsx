'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import styles from './page.module.css';

interface LLMModel {
  id: string;
  name: string;
}

interface Agent {
  id: string;
  name: string;
  description?: string;
  model_id: string;
  system_prompt: string;
  is_orchestrator: boolean;
  is_abstract: boolean;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [modelId, setModelId] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [isOrchestrator, setIsOrchestrator] = useState(false);

  const fetchData = async () => {
    try {
      const [agentsData, modelsData] = await Promise.all([
        apiClient.get('/agents'),
        apiClient.get('/models')
      ]);
      setAgents(agentsData);
      setModels(modelsData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openAdd = () => {
    setEditingAgent(null);
    setName('');
    setDescription('');
    setModelId(models[0]?.id || '');
    setSystemPrompt('');
    setIsOrchestrator(false);
    setIsModalOpen(true);
  };

  const openEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setName(agent.name);
    setDescription(agent.description || '');
    setModelId(agent.model_id);
    setSystemPrompt(agent.system_prompt);
    setIsOrchestrator(agent.is_orchestrator);
    setIsModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this agent?')) return;
    try {
      await apiClient.delete(`/agents/${id}`);
      fetchData();
    } catch (error) {
      console.error('Failed to delete agent:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name,
      description: description || null,
      model_id: modelId,
      system_prompt: systemPrompt,
      is_orchestrator: isOrchestrator,
      is_abstract: false
    };

    try {
      if (editingAgent) {
        await apiClient.put(`/agents/${editingAgent.id}`, payload);
      } else {
        await apiClient.post('/agents', payload);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (error) {
      console.error('Failed to save agent:', error);
    }
  };

  if (loading) return <div className={styles.container}>Loading agents...</div>;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Agent Builder</h1>
          <p className={styles.subtitle}>Define agentic personalities and map them to local models.</p>
        </div>
        <button className={styles.addButton} onClick={openAdd}>Create Agent</button>
      </header>

      <div className={styles.grid}>
        {agents.map((agent) => {
          const matchedModel = models.find(m => m.id === agent.model_id);
          return (
            <div key={agent.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <div className={styles.titleRow}>
                  <h2 className={styles.agentName}>{agent.name}</h2>
                  <div className={styles.actions}>
                    <button className={styles.actionBtn} onClick={() => openEdit(agent)}>Edit</button>
                    <button className={`${styles.actionBtn} ${styles.danger}`} onClick={() => handleDelete(agent.id)}>Delete</button>
                  </div>
                </div>
                {agent.is_orchestrator && (
                  <span className={`${styles.pill} ${styles.orchestratorPill}`}>Orchestrator</span>
                )}
                {matchedModel && (
                  <span className={`${styles.pill} ${styles.modelPill}`}>🤖 {matchedModel.name}</span>
                )}
              </div>
              
              <p className={styles.description}>{agent.description || 'No description provided.'}</p>
              
              <div className={styles.promptPreview}>
                <span className={styles.promptLabel}>System Persona</span>
                <p className={styles.promptText}>{agent.system_prompt}</p>
              </div>
            </div>
          );
        })}
      </div>

      {isModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <h2 className={styles.modalTitle}>{editingAgent ? 'Edit Agent' : 'Create Agent'}</h2>
            <form onSubmit={handleSubmit} className={styles.form}>
              <div className={styles.formGroup}>
                <label className={styles.label}>Name</label>
                <input 
                  type="text" 
                  value={name} 
                  onChange={e => setName(e.target.value)} 
                  required 
                  className={styles.input} 
                  placeholder="e.g. Coder Agent"
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>Description</label>
                <input 
                  type="text" 
                  value={description} 
                  onChange={e => setDescription(e.target.value)} 
                  className={styles.input} 
                  placeholder="e.g. Specialized in Python code compilation"
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>Backing Model</label>
                <select 
                  value={modelId} 
                  onChange={e => setModelId(e.target.value)} 
                  required 
                  className={styles.select}
                >
                  <option value="" disabled>Select a model...</option>
                  {models.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>System Persona Prompt</label>
                <textarea 
                  value={systemPrompt} 
                  onChange={e => setSystemPrompt(e.target.value)} 
                  required 
                  rows={6}
                  className={styles.textarea} 
                  placeholder="Describe how the agent behaves, instructions it must follow, and its format requirements..."
                />
              </div>

              <div className={styles.checkboxGroup}>
                <input 
                  type="checkbox" 
                  id="isOrchestrator"
                  checked={isOrchestrator} 
                  onChange={e => setIsOrchestrator(e.target.checked)}
                  className={styles.checkbox}
                />
                <label htmlFor="isOrchestrator" className={styles.checkboxLabel}>Set as Orchestrator Agent</label>
              </div>

              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={() => setIsModalOpen(false)}>Cancel</button>
                <button type="submit" className={styles.submitBtn}>{editingAgent ? 'Save Changes' : 'Create Agent'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
