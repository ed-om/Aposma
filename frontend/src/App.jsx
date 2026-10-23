import { useCallback, useEffect, useMemo, useState } from 'react';

const API = '/api';

function isGitHubSource(value) {
  const source = value.trim();
  return /^https?:\/\/(?:www\.)?github\.com\//i.test(source)
    || /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?:\.git)?$/.test(source);
}

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === 'string'
      ? data.detail
      : data.detail
        ? JSON.stringify(data.detail)
        : `Request failed (${response.status})`;
    const hint = response.status >= 500
      ? ' (see the FastAPI terminal for the traceback)'
      : '';
    throw new Error(`HTTP ${response.status}: ${detail}${hint}`);
  }
  return data;
}

function Icon({ name, size = 18 }) {
  const paths = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="4" rx="1.5" /><rect x="14" y="10" width="7" height="11" rx="1.5" /><rect x="3" y="13" width="7" height="8" rx="1.5" /></>,
    review: <><path d="M9 11l2 2 4-4" /><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8" /><path d="M14 3h7v7" /><path d="M21 3l-9 9" /></>,
    docs: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h8" /></>,
    history: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /><path d="M3 12a9 9 0 0 1 2.4-6.1L3 3" /></>,
    arrow: <><path d="M5 12h14M12 5l7 7-7 7" /></>,
    folder: <><path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></>,
    refresh: <><path d="M20 7v5h-5" /><path d="M4 17v-5h5" /><path d="M5.6 9A7 7 0 0 1 17 5l3 7M4 12l3 7a7 7 0 0 0 11.4-2" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    alert: <><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 3.9 1.9 18.1A2 2 0 0 0 3.6 21h16.8a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z" /></>,
    spark: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /><path d="m19 15 .9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.spark}</svg>;
}

function StatePill({ good, children }) {
  return <span className={`state-pill ${good ? 'good' : 'bad'}`}><span className="state-dot" />{children}</span>;
}

function Severity({ value }) {
  const severity = (value || 'INFO').toUpperCase();
  return <span className={`severity severity-${severity.toLowerCase()}`}>{severity}</span>;
}

function EmptyState({ title, detail }) {
  return <div className="empty-state"><span className="empty-icon"><Icon name="spark" size={21} /></span><strong>{title}</strong><p>{detail}</p></div>;
}

export default function App() {
  const [page, setPage] = useState('overview');
  const [repoPath, setRepoPath] = useState('examples/sample_cpp');
  const [base, setBase] = useState('');
  const [useAi, setUseAi] = useState(true);
  const [status, setStatus] = useState(null);
  const [statusError, setStatusError] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [review, setReview] = useState(null);
  const [documentation, setDocumentation] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeFinding, setActiveFinding] = useState(0);

  const refreshStatus = useCallback(async () => {
    try {
      const data = await request('/status');
      setStatus(data);
      setStatusError('');
    } catch (err) {
      setStatus(null);
      setStatusError(err.message || 'Could not reach the API');
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const data = await request('/history?limit=12');
      setHistory(data.analyses || []);
    } catch (err) {
      setError(err.message || 'Could not load history');
    }
  }, []);

  useEffect(() => { refreshStatus(); refreshHistory(); }, [refreshStatus, refreshHistory]);

  const totalFindings = review?.findings?.length ?? 0;
  const highCount = useMemo(() => (review?.findings || []).filter((item) => item.severity?.toUpperCase() === 'HIGH').length, [review]);

  async function runReview(event) {
    event.preventDefault();
    setLoading(true); setError(''); setReview(null); setActiveFinding(0);
    try {
      const result = await request('/review', {
        method: 'POST',
        body: JSON.stringify({ repo_path: repoPath, base: base.trim() || null, use_ai: useAi }),
      });
      setReview(result);
      setPage('review');
      await refreshHistory();
    } catch (err) {
      setError(err.message || 'Review failed');
    } finally { setLoading(false); }
  }

  async function runDocs(event) {
    event.preventDefault();
    setLoading(true); setError(''); setDocumentation(null);
    try {
      const result = await request('/docs', { method: 'POST', body: JSON.stringify({ repo_path: repoPath, use_ai: useAi }) });
      setDocumentation(result);
      setPage('docs');
    } catch (err) {
      setError(err.message || 'Documentation generation failed');
    } finally { setLoading(false); }
  }

  async function openHistory() {
    setError(''); setPage('history'); await refreshHistory();
  }

  const navigate = (target) => { setError(''); setPage(target); if (target === 'history') refreshHistory(); };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark">a<span>.</span></div>
          <div><div className="brand-name">aposma</div><div className="brand-caption">CODE INTELLIGENCE</div></div>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="nav-list" aria-label="Main navigation">
          <button className={`nav-item ${page === 'overview' ? 'active' : ''}`} onClick={() => navigate('overview')}><Icon name="overview" /><span>Overview</span></button>
          <button className={`nav-item ${page === 'review' ? 'active' : ''}`} onClick={() => navigate('review')}><Icon name="review" /><span>Code review</span>{review && <span className="nav-count">{totalFindings}</span>}</button>
          <button className={`nav-item ${page === 'docs' ? 'active' : ''}`} onClick={() => navigate('docs')}><Icon name="docs" /><span>Documentation</span></button>
          <button className={`nav-item ${page === 'history' ? 'active' : ''}`} onClick={openHistory}><Icon name="history" /><span>Analysis history</span></button>
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-card"><div className="privacy-icon"><Icon name="check" size={16} /></div><div><strong>Local by design</strong><p>Your code stays on your machine. Aposma uses your local analyzer and Ollama setup.</p></div></div>
          <div className="sidebar-version"><span className="version-dot" /> Local workspace <span className="version-number">v0.2</span></div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>{({ overview: 'Overview', review: 'Code review', docs: 'Documentation', history: 'Analysis history' })[page]}</strong></div><div className="topbar-status">{status?.analyzer?.available ? <StatePill good>Analyzer ready</StatePill> : <StatePill good={false}>Analyzer unavailable</StatePill>}{status?.ollama?.model_installed ? <StatePill good>Local SLM ready</StatePill> : <StatePill good={false}>SLM not ready</StatePill>}</div></header>

        {page === 'overview' && <section className="content-page">
          <div className="eyebrow"><span className="eyebrow-line" /> LOCAL-FIRST CODE INTELLIGENCE</div>
          <div className="hero-row"><div className="hero-copy"><h1>Understand your code.<br /><span>Trust the evidence.</span></h1><p>Aposma combines deterministic C++ analysis with a local language model to help you review changes and document unfamiliar code.</p></div><div className="hero-art" aria-hidden="true"><div className="art-orbit orbit-one"/><div className="art-orbit orbit-two"/><div className="art-core"><span>a.</span></div><span className="art-dot dot-one"/><span className="art-dot dot-two"/><span className="art-dot dot-three"/><span className="art-label">CODE<br/>→ CONTEXT</span></div></div>

          <div className="section-heading"><div><span className="section-kicker">GET STARTED</span><h2>Run an analysis</h2></div><span className="section-note">Local C++ folder or GitHub repository</span></div>
          <div className="analysis-card">
            <form onSubmit={runReview} className="analysis-form">
              <label className="field-label" htmlFor="repo-path">Repository path or GitHub URL</label>
              <div className="path-input-wrap"><Icon name="folder" size={19}/><input id="repo-path" value={repoPath} onChange={(e) => setRepoPath(e.target.value)} placeholder="/home/you/project or https://github.com/owner/repo" required /><span className="input-tag">{isGitHubSource(repoPath) ? 'GITHUB REPOSITORY' : 'LOCAL PATH'}</span></div>
              <p className="source-hint">{isGitHubSource(repoPath) ? 'GitHub source detected · the repository will be cloned into your local Aposma workspace.' : 'Enter an existing local directory or paste a GitHub repository URL.'}</p>
              <div className="form-row"><div className="form-field"><label className="field-label" htmlFor="base-ref">Compare against <span>(optional)</span></label><input id="base-ref" className="text-input" value={base} onChange={(e) => setBase(e.target.value)} placeholder="main, HEAD~1, or commit" /></div><div className="ai-toggle-block"><div><strong>Use local SLM</strong><p>Evidence-grounded review with Ollama</p></div><button type="button" role="switch" aria-checked={useAi} className={`switch ${useAi ? 'on' : ''}`} onClick={() => setUseAi(!useAi)}><span /></button></div></div>
              {error && <div className="error-banner"><Icon name="alert" size={17}/><span>{error}</span><button type="button" onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
              <div className="form-actions"><div className="form-hint"><span className="secure-mark"><Icon name="check" size={13}/></span> Local folders stay local; GitHub repos are cloned to your workspace</div><button className="primary-button" type="submit" disabled={loading}>{loading ? <><span className="spinner"/> Running review…</> : <>Review repository <Icon name="arrow" size={17}/></>}</button></div>
            </form>
            <div className="card-divider" />
            <div className="secondary-action"><div className="secondary-icon"><Icon name="docs" size={18}/></div><div><strong>Generate project documentation</strong><p>Create Markdown docs from the code structure</p></div><button type="button" className="secondary-button" onClick={runDocs} disabled={loading || !repoPath.trim()}>{loading ? 'Working…' : 'Generate docs'} <Icon name="arrow" size={15}/></button></div>
          </div>

          <div className="section-heading lower-heading"><div><span className="section-kicker">SYSTEM CHECK</span><h2>Your local setup</h2></div><button className="text-button" onClick={refreshStatus}><Icon name="refresh" size={15}/> Refresh</button></div>
          <div className="system-grid">
            <div className="system-card"><div className="system-card-top"><span className="system-icon"><Icon name="review" size={18}/></span><StatePill good={!!status?.analyzer?.available}>{status?.analyzer?.available ? 'Ready' : 'Not found'}</StatePill></div><h3>C++ analyzer</h3><p>{status?.analyzer?.available ? status.analyzer.path : status?.analyzer?.error || 'Waiting for API status…'}</p></div>
            <div className="system-card"><div className="system-card-top"><span className="system-icon"><Icon name="spark" size={18}/></span><StatePill good={!!status?.ollama?.model_installed}>{status?.ollama?.model_installed ? 'Ready' : status?.ollama?.reachable ? 'Model missing' : 'Offline'}</StatePill></div><h3>Local language model</h3><p>{status?.ollama?.model || 'Configured via APOSMA_OLLAMA_MODEL'}{status?.ollama?.error ? ` · ${status.ollama.error}` : ''}</p></div>
            <div className="system-card"><div className="system-card-top"><span className="system-icon"><Icon name="history" size={18}/></span><StatePill good={!statusError}>{statusError ? 'Unavailable' : 'Connected'}</StatePill></div><h3>Analysis history</h3><p>{history.length} recent run{history.length === 1 ? '' : 's'} available in the local SQLite database.</p></div>
          </div>
          {statusError && <div className="notice-banner"><Icon name="alert" size={17}/><span>{statusError.includes('HTTP 5') ? `The API is running, but its status check failed: ${statusError}` : `Cannot reach the Aposma API: ${statusError}. Start FastAPI on 127.0.0.1:8000 from the project root.`}</span></div>}
        </section>}

        {page === 'review' && <section className="content-page results-page">
          <div className="page-intro"><div><div className="eyebrow"><span className="eyebrow-line"/> ANALYSIS RESULTS</div><h1>Code review</h1><p>Findings grounded in the local analyzer and repository evidence.</p></div><button className="secondary-button" onClick={() => setPage('overview')}>New review <Icon name="arrow" size={15}/></button></div>
          {error && <div className="error-banner"><Icon name="alert" size={17}/>{error}</div>}
          {!review ? <EmptyState title="No review run yet" detail="Go to Overview, enter a repository path, and run a review to see findings here."/> : <>
            <div className="result-summary"><div className="summary-icon"><Icon name="check" size={20}/></div><div className="summary-body"><span className="section-kicker">REVIEW #{review.analysis_id}</span><h2>{review.summary}</h2><p className="repo-location"><Icon name="folder" size={14}/>{review.source_label || review.repo_path}{review.source_type === 'github' ? ' · GitHub workspace' : ''}</p></div><div className="summary-metrics"><div><strong>{totalFindings}</strong><span>Findings</span></div><div><strong>{highCount}</strong><span>High severity</span></div></div></div>
            <div className="result-toolbar"><h2>Findings <span>{totalFindings}</span></h2><span className="muted">{review.ai_used ? 'Enhanced by local SLM' : 'Deterministic analysis'}</span></div>
            {totalFindings === 0 ? <EmptyState title="No findings returned" detail="The analysis completed without findings. That does not guarantee the repository is bug-free."/> : <div className="findings-layout"><div className="finding-list">{review.findings.map((finding, index) => <button key={`${finding.location}-${finding.title}-${index}`} className={`finding-item ${activeFinding === index ? 'selected' : ''}`} onClick={() => setActiveFinding(index)}><div className="finding-item-top"><Severity value={finding.severity}/><span>{finding.category}</span></div><strong>{finding.title || finding.finding}</strong><small>{finding.location}</small></button>)}</div><article className="finding-detail">{review.findings[activeFinding] && <><div className="detail-top"><Severity value={review.findings[activeFinding].severity}/><span className="category-label">{review.findings[activeFinding].category}</span><span className="confidence">{Math.round((review.findings[activeFinding].confidence || 0) * 100)}% confidence</span></div><h2>{review.findings[activeFinding].title}</h2><p className="detail-finding">{review.findings[activeFinding].finding}</p><div className="detail-section"><h3>Why it matters</h3><p>{review.findings[activeFinding].reason || 'No additional reasoning was provided.'}</p></div><div className="detail-section"><h3>Evidence</h3>{(review.findings[activeFinding].evidence || []).length ? <ul>{review.findings[activeFinding].evidence.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>No evidence items returned.</p>}</div></>}</article></div>}
          </>}
        </section>}

        {page === 'docs' && <section className="content-page results-page">
          <div className="page-intro"><div><div className="eyebrow"><span className="eyebrow-line"/> CODEBASE KNOWLEDGE</div><h1>Documentation</h1><p>Generate concise Markdown documentation from extracted code structure.</p></div><button className="secondary-button" onClick={() => setPage('overview')}>Back to overview <Icon name="arrow" size={15}/></button></div>
          {error && <div className="error-banner"><Icon name="alert" size={17}/>{error}</div>}
          {documentation?.warning && <div className="notice-banner"><Icon name="alert" size={17}/>{documentation.warning}</div>}
          {!documentation ? <div className="docs-start-card"><div className="docs-illustration"><Icon name="docs" size={30}/><span>MD</span></div><div><h2>Make the codebase easier to understand</h2><p>Enter a local folder or GitHub repository on Overview to generate an indexed set of Markdown files in <code>.aposma/docs/</code>. GitHub repositories are kept in your local Aposma workspace.</p><button className="primary-button" onClick={runDocs} disabled={loading || !repoPath.trim()}>{loading ? <><span className="spinner"/> Generating…</> : <>Generate from current repository <Icon name="arrow" size={16}/></>}</button></div></div> : <><div className="result-summary"><div className="summary-icon"><Icon name="docs" size={20}/></div><div className="summary-body"><span className="section-kicker">DOCUMENTATION OUTPUT · {documentation.ai_used ? 'AI + STRUCTURAL FACTS' : 'DETERMINISTIC'}</span><h2>{documentation.summary}</h2><p className="repo-location"><Icon name="folder" size={14}/>{documentation.source_label || documentation.repo_path}</p><p className="repo-location"><Icon name="docs" size={14}/>Output: {documentation.docs_directory || `${documentation.repo_path}/.aposma/docs`}</p></div><div className="summary-metrics"><div><strong>{documentation.documents.length}</strong><span>Documents</span></div></div></div><div className="docs-grid">{documentation.documents.map((doc, index) => <article className="doc-card" key={`${doc.name}-${index}`}><div className="doc-card-head"><span className="doc-type">{doc.kind || 'document'}</span><span className="doc-index">{String(index + 1).padStart(2, '0')}</span></div><h3>{doc.name}</h3><pre>{doc.markdown}</pre><div className="doc-card-footer">Saved to <code>{doc.path || documentation.saved_to?.[index] || '.aposma/docs/'}</code></div></article>)}</div></>}
        </section>}

        {page === 'history' && <section className="content-page results-page"><div className="page-intro"><div><div className="eyebrow"><span className="eyebrow-line"/> LOCAL RECORDS</div><h1>Analysis history</h1><p>A record of recent repositories reviewed by Aposma.</p></div><button className="text-button" onClick={refreshHistory}><Icon name="refresh" size={15}/> Refresh</button></div><div className="history-card"><div className="history-header"><h2>Recent analyses</h2><span>{history.length} shown</span></div>{history.length === 0 ? <EmptyState title="Nothing here yet" detail="Your completed repository reviews will appear here."/> : <div className="history-table-wrap"><table className="history-table"><thead><tr><th>Analysis</th><th>Repository</th><th>Created</th><th>Summary</th></tr></thead><tbody>{history.map((item) => <tr key={item.id}><td><span className="analysis-id">#{item.id}</span></td><td><div className="history-repo"><Icon name="folder" size={15}/>{item.repository}</div></td><td>{new Date(item.created_at).toLocaleString()}</td><td>{item.summary}</td></tr>)}</tbody></table></div>}</div></section>}

        <footer className="footer"><span>APOSMA <span className="footer-dot">·</span> LOCAL-FIRST CODE INTELLIGENCE</span><span>Deterministic facts first. AI interpretation second.</span></footer>
      </main>
    </div>
  );
}
