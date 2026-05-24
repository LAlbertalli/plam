'use client';

import { use, useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
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

interface RegexRule {
  id: string;
  model_id: string;
  name: string;
  pattern: string;
  replacement: string;
  chain: 'input_chain' | 'output_chain';
  order: number;
  is_active: boolean;
}

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ModelDetailPage({ params }: PageProps) {
  const { id: modelId } = use(params);

  const [model, setModel] = useState<LLMModel | null>(null);
  const [rules, setRules] = useState<RegexRule[]>([]);
  const [activeTab, setActiveTab] = useState<'input_chain' | 'output_chain'>('input_chain');
  const [loading, setLoading] = useState(true);

  // Form State for Regex Rule Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<RegexRule | null>(null);
  const [name, setName] = useState('');
  const [pattern, setPattern] = useState('');
  const [replacement, setReplacement] = useState('');
  const [order, setOrder] = useState(1);
  const [isActive, setIsActive] = useState(true);

  // Live Testing Pane State
  const [testText, setTestText] = useState('');
  const [testResult, setTestResult] = useState('');
  const [testLoading, setTestLoading] = useState(false);

  const fetchModelDetails = useCallback(async () => {
    try {
      const data = await apiClient.get(`/models/${modelId}`);
      setModel(data);
    } catch (err) {
      console.error('Failed to fetch model details:', err);
    }
  }, [modelId]);

  const fetchRules = useCallback(async () => {
    try {
      const data = await apiClient.get(`/proxies?model_id=${modelId}`);
      setRules(data);
    } catch (err) {
      console.error('Failed to fetch rules:', err);
    }
  }, [modelId]);

  const initData = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchModelDetails(), fetchRules()]);
    setLoading(false);
  }, [fetchModelDetails, fetchRules]);

  useEffect(() => {
    initData();
    // Poll model status every 5 seconds to show state transitions
    const interval = setInterval(fetchModelDetails, 5000);
    return () => clearInterval(interval);
  }, [initData, fetchModelDetails]);

  // Model Operations
  const handleDownload = async () => {
    if (!model) return;
    try {
      const updated = await apiClient.post(`/models/${modelId}/download`, {});
      setModel(updated);
    } catch (err) {
      console.error('Failed to start download:', err);
    }
  };

  const handleStart = async () => {
    if (!model) return;
    try {
      const updated = await apiClient.post(`/models/${modelId}/start`, {});
      setModel(updated);
    } catch (err) {
      console.error('Failed to start model:', err);
    }
  };

  const handleStop = async () => {
    if (!model) return;
    try {
      const updated = await apiClient.post(`/models/${modelId}/stop`, {});
      setModel(updated);
    } catch (err) {
      console.error('Failed to stop model:', err);
    }
  };

  // Run live test
  const handleTestRegex = useCallback(async () => {
    if (!testText) {
      setTestResult('');
      return;
    }
    setTestLoading(true);
    try {
      const res = await apiClient.post('/proxies/test', {
        text: testText,
        model_id: modelId,
        chain: activeTab
      });
      setTestResult(res.result);
    } catch (err) {
      console.error(err);
      setTestResult('Error executing regex replacement.');
    } finally {
      setTestLoading(false);
    }
  }, [modelId, testText, activeTab]);

  useEffect(() => {
    const timer = setTimeout(() => {
      handleTestRegex();
    }, 400);
    return () => clearTimeout(timer);
  }, [testText, activeTab, handleTestRegex]);

  // Regex Rule Operations
  const openAdd = () => {
    setEditingRule(null);
    setName('');
    setPattern('');
    setReplacement('');
    const currentTabRules = rules.filter(r => r.chain === activeTab);
    setOrder(currentTabRules.length + 1);
    setIsActive(true);
    setIsModalOpen(true);
  };

  const openEdit = (rule: RegexRule) => {
    setEditingRule(rule);
    setName(rule.name);
    setPattern(rule.pattern);
    setReplacement(rule.replacement);
    setOrder(rule.order);
    setIsActive(rule.is_active);
    setIsModalOpen(true);
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this regex rule?')) return;
    try {
      await apiClient.delete(`/proxies/${ruleId}`);
      fetchRules();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmitRule = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      model_id: modelId,
      name,
      pattern,
      replacement,
      chain: activeTab,
      order: Number(order),
      is_active: isActive
    };

    try {
      if (editingRule) {
        await apiClient.put(`/proxies/${editingRule.id}`, payload);
      } else {
        await apiClient.post('/proxies', payload);
      }
      setIsModalOpen(false);
      fetchRules();
    } catch (err: any) {
      alert(err.message || 'Failed to save regex rule. Ensure Order is unique within the chain.');
    }
  };

  const handleToggleActive = async (rule: RegexRule) => {
    try {
      await apiClient.put(`/proxies/${rule.id}`, {
        ...rule,
        is_active: !rule.is_active
      });
      fetchRules();
    } catch (err) {
      console.error(err);
    }
  };

  const handleMoveRule = async (rule: RegexRule, direction: 'up' | 'down') => {
    const currentRules = rules.filter(r => r.chain === activeTab).sort((a, b) => a.order - b.order);
    const index = currentRules.findIndex(r => r.id === rule.id);
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === currentRules.length - 1) return;

    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    const targetRule = currentRules[targetIndex];

    try {
      // Temporary swap high order logic to avoid DB unique constraints
      const tempOrder = 9999;
      await apiClient.put(`/proxies/${rule.id}`, { ...rule, order: tempOrder });
      await apiClient.put(`/proxies/${targetRule.id}`, { ...targetRule, order: rule.order });
      await apiClient.put(`/proxies/${rule.id}`, { ...rule, order: targetRule.order });
      fetchRules();
    } catch (err) {
      console.error('Failed to swap rule ordering:', err);
    }
  };

  const filteredRules = rules
    .filter(r => r.chain === activeTab)
    .sort((a, b) => a.order - b.order);

  if (loading) return <div className={styles.container}>Loading model details...</div>;
  if (!model) return <div className={styles.container}>Model not found.</div>;

  return (
    <div className={styles.container}>
      {/* Header / Back Navigation */}
      <header className={styles.header}>
        <Link href="/models" className={styles.backLink}>
          ← Back to Models
        </Link>
        <div className={styles.headerTitleRow}>
          <h1 className={styles.title}>{model.name}</h1>
          <div className={styles.modelStatusActions}>
            <span className={`${styles.statusPill} ${styles[model.status]}`}>{model.status}</span>
            {model.status === 'stopped' && (
              <button className={styles.actionBtn} onClick={handleStart}>Start Model</button>
            )}
            {model.status === 'running' && (
              <button className={`${styles.actionBtn} ${styles.stop}`} onClick={handleStop}>Stop Model</button>
            )}
            <button 
              className={styles.actionBtn} 
              onClick={handleDownload}
              disabled={model.local_path != null || model.status === 'downloading' || model.status === 'running'}
            >
              {model.local_path != null ? 'Downloaded' : (model.status === 'downloading' ? 'Downloading...' : 'Download GGUF')}
            </button>
          </div>
        </div>
      </header>

      {/* Detail Dashboard Cards */}
      <section className={styles.metaDashboard}>
        <div className={styles.metaCard}>
          <span className={styles.metaLabel}>HuggingFace Repo ID</span>
          <span className={styles.metaValue}>{model.hf_repo_id}</span>
        </div>
        <div className={styles.metaCard}>
          <span className={styles.metaLabel}>GGUF Filename</span>
          <span className={styles.metaValue}>{model.gguf_filename}</span>
        </div>
        <div className={styles.metaGrid}>
          <div className={styles.metaCard}>
            <span className={styles.metaLabel}>RAM Required</span>
            <span className={styles.metaValue}>{(model.ram_required_mb / 1024).toFixed(1)} GB</span>
          </div>
          <div className={styles.metaCard}>
            <span className={styles.metaLabel}>Context Size</span>
            <span className={styles.metaValue}>{model.context_size} tokens</span>
          </div>
          <div className={styles.metaCard}>
            <span className={styles.metaLabel}>Parameters</span>
            <span className={styles.metaValue}>{model.parameter_count || 'N/A'}</span>
          </div>
          <div className={styles.metaCard}>
            <span className={styles.metaLabel}>Quantization</span>
            <span className={styles.metaValue}>{model.quantization || 'N/A'}</span>
          </div>
        </div>
      </section>

      {/* Embedded Regex Rules Editor */}
      <section className={styles.rulesSection}>
        <div className={styles.rulesSectionHeader}>
          <div>
            <h2 className={styles.sectionTitle}>🛡️ Regex Rewriting Proxy</h2>
            <p className={styles.sectionSubtitle}>Sequentially alter prompts sent to this model and refine responses streamed back.</p>
          </div>
          <button className={styles.addButton} onClick={openAdd}>Add Rule</button>
        </div>

        {/* Tab Selection */}
        <div className={styles.tabsContainer}>
          <div className={styles.tabs}>
            <button 
              className={`${styles.tab} ${activeTab === 'input_chain' ? styles.active : ''}`}
              onClick={() => setActiveTab('input_chain')}
            >
              Input Chain <span>(Prompt Adaptation)</span>
            </button>
            <button 
              className={`${styles.tab} ${activeTab === 'output_chain' ? styles.active : ''}`}
              onClick={() => setActiveTab('output_chain')}
            >
              Output Chain <span>(Hallucination Cleanup)</span>
            </button>
          </div>
        </div>

        <div className={styles.rulesContentLayout}>
          {/* Rules Table */}
          <div className={styles.rulesList}>
            {filteredRules.length === 0 ? (
              <div className={styles.emptyState}>No regex rules defined for this chain.</div>
            ) : (
              <div className={styles.rulesTableContainer}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th style={{ width: '80px' }}>Order</th>
                      <th>Name</th>
                      <th>Pattern</th>
                      <th>Replacement</th>
                      <th style={{ width: '100px' }}>Status</th>
                      <th style={{ width: '150px' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRules.map((rule, idx) => (
                      <tr key={rule.id}>
                        <td>
                          <div className={styles.orderControl}>
                            <span className={styles.orderVal}>{rule.order}</span>
                            <div className={styles.arrows}>
                              <button 
                                onClick={() => handleMoveRule(rule, 'up')} 
                                disabled={idx === 0}
                                className={styles.arrowBtn}
                              >
                                ▲
                              </button>
                              <button 
                                onClick={() => handleMoveRule(rule, 'down')} 
                                disabled={idx === filteredRules.length - 1}
                                className={styles.arrowBtn}
                              >
                                ▼
                              </button>
                            </div>
                          </div>
                        </td>
                        <td><strong className={styles.ruleName}>{rule.name}</strong></td>
                        <td><code className={styles.code}>{rule.pattern}</code></td>
                        <td><code className={styles.code}>{rule.replacement || '(Empty)'}</code></td>
                        <td>
                          <button 
                            className={`${styles.statusToggle} ${rule.is_active ? styles.active : ''}`}
                            onClick={() => handleToggleActive(rule)}
                          >
                            {rule.is_active ? 'Active' : 'Disabled'}
                          </button>
                        </td>
                        <td>
                          <div className={styles.actions}>
                            <button className={styles.editBtn} onClick={() => openEdit(rule)}>Edit</button>
                            <button className={styles.deleteBtn} onClick={() => handleDeleteRule(rule.id)}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Simulator Pane */}
          <div className={styles.testingPane}>
            <h3 className={styles.testingTitle}>⚡ Live Chain Simulator</h3>
            <p className={styles.testingSubtitle}>Type text to simulate how current active rules rewrite it in real time.</p>
            
            <div className={styles.testingForm}>
              <div className={styles.testGroup}>
                <label className={styles.testLabel}>Original Input</label>
                <textarea 
                  value={testText}
                  onChange={e => setTestText(e.target.value)}
                  placeholder="Enter text to test Match Patterns against..."
                  className={styles.testTextarea}
                  rows={4}
                />
              </div>
              
              <div className={styles.testGroup}>
                <label className={styles.testLabel}>Rewritten Output</label>
                <div className={`${styles.testOutput} ${testLoading ? styles.loading : ''}`}>
                  {testResult || <span className={styles.outputPlaceholder}>Simulated output will render here...</span>}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Create / Edit Modal */}
      {isModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <h2 className={styles.modalTitle}>{editingRule ? 'Edit Rule' : 'Create Rule'}</h2>
            <form onSubmit={handleSubmitRule} className={styles.form}>
              <div className={styles.formGroup}>
                <label className={styles.label}>Rule Name</label>
                <input 
                  type="text" 
                  value={name} 
                  onChange={e => setName(e.target.value)} 
                  required 
                  className={styles.input} 
                  placeholder="e.g. Clean trailing whitespace"
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>Match Pattern (Regex)</label>
                <input 
                  type="text" 
                  value={pattern} 
                  onChange={e => setPattern(e.target.value)} 
                  required 
                  className={styles.input} 
                  placeholder="e.g. (?i)\b(hallucinate)\b"
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>Replacement Pattern</label>
                <input 
                  type="text" 
                  value={replacement} 
                  onChange={e => setReplacement(e.target.value)} 
                  className={styles.input} 
                  placeholder="e.g. generate facts"
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup} style={{ flex: 1 }}>
                  <label className={styles.label}>Order Number</label>
                  <input 
                    type="number" 
                    value={order} 
                    onChange={e => setOrder(Number(e.target.value))} 
                    required 
                    min={1}
                    className={styles.input}
                  />
                </div>
                <div className={styles.formGroup} style={{ flex: 1, justifyContent: 'flex-end', paddingBottom: '10px' }}>
                  <div className={styles.checkboxGroup}>
                    <input 
                      type="checkbox" 
                      id="isRuleActive"
                      checked={isActive} 
                      onChange={e => setIsActive(e.target.checked)}
                      className={styles.checkbox}
                    />
                    <label htmlFor="isRuleActive" className={styles.checkboxLabel}>Active</label>
                  </div>
                </div>
              </div>

              <div className={styles.modalActions}>
                <button type="button" className={styles.cancelBtn} onClick={() => setIsModalOpen(false)}>Cancel</button>
                <button type="submit" className={styles.submitBtn}>{editingRule ? 'Save Changes' : 'Create Rule'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
