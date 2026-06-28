"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Brain, FileText, GitCompareArrows, LogOut, MessageSquareText, RefreshCcw, Search, Trash2, UploadCloud } from "lucide-react";
import { api, apiUrl, AdminOverview, ApiKeyRecord, changePassword, Citation, createApiKey, DocumentItem, downloadText, EvaluationRecord, LiteratureMatrixRow, login, logout, OperationalStatus, Project, register, ResearchNote, revokeApiKey, SavedQuery, UsageSummary } from "@/lib/api";
import { SourceList } from "@/components/SourceList";

type Mode = "ask" | "search" | "compare";
const API_KEY_SCOPES = ["*", "documents:read", "documents:write", "search:read", "qa:read", "research:read", "research:write", "projects:read", "projects:write", "exports:read", "history:read", "ops:read", "profile:read"];

export default function Page() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("researcher@example.com");
  const [password, setPassword] = useState("researcher123");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [name, setName] = useState("Researcher");
  const [authMode, setAuthMode] = useState<"login" | "register">("register");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [savedQueries, setSavedQueries] = useState<SavedQuery[]>([]);
  const [notes, setNotes] = useState<ResearchNote[]>([]);
  const [usage, setUsage] = useState<UsageSummary[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationRecord[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKeyRecord[]>([]);
  const [opsStatus, setOpsStatus] = useState<OperationalStatus | null>(null);
  const [adminOverview, setAdminOverview] = useState<AdminOverview | null>(null);
  const [exportPreview, setExportPreview] = useState("");
  const [projectName, setProjectName] = useState("Reading List");
  const [uploadTags, setUploadTags] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [apiKeyName, setApiKeyName] = useState("Research CLI");
  const [apiKeyScopes, setApiKeyScopes] = useState<string[]>(["*"]);
  const [apiKeyDailyLimit, setApiKeyDailyLimit] = useState("");
  const [newApiKey, setNewApiKey] = useState("");
  const [noteBody, setNoteBody] = useState("");
  const [selectedDocument, setSelectedDocument] = useState<string>("");
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [secondDocument, setSecondDocument] = useState<string>("");
  const [mode, setMode] = useState<Mode>("ask");
  const [query, setQuery] = useState("What are the central findings and limitations?");
  const [retrievalMode, setRetrievalMode] = useState<"hybrid" | "vector" | "keyword">("hybrid");
  const [rewriteQuery, setRewriteQuery] = useState(true);
  const [resultLimit, setResultLimit] = useState(8);
  const [minScore, setMinScore] = useState(0.05);
  const [sourceTypeFilter, setSourceTypeFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [editTitle, setEditTitle] = useState("");
  const [editTags, setEditTags] = useState("");
  const [rewrittenQuery, setRewrittenQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Citation[]>([]);
  const [matrixRows, setMatrixRows] = useState<LiteratureMatrixRow[]>([]);
  const [literatureSynthesis, setLiteratureSynthesis] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [accountMessage, setAccountMessage] = useState("");

  const readyDocs = useMemo(() => documents.filter((doc) => doc.status === "ready"), [documents]);

  useEffect(() => {
    const saved = localStorage.getItem("research_token");
    if (saved) setToken(saved);
  }, []);

  useEffect(() => {
    if (!token) return;
    void loadDocuments();
    void loadMatrix();
    void loadWorkspace();
    const timer = window.setInterval(() => {
      void loadDocuments();
      void loadMatrix();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [token]);

  useEffect(() => {
    if (!token) return;
    void loadDocuments();
  }, [selectedProject, includeDeleted]);

  useEffect(() => {
    const current = documents.find((doc) => doc.id === selectedDocument);
    setEditTitle(current?.title || "");
    setEditTags(current?.tags || "");
  }, [selectedDocument, documents]);

  async function loadDocuments() {
    if (!token) return;
    const params = new URLSearchParams();
    if (selectedProject) params.set("project_id", selectedProject);
    if (includeDeleted) params.set("include_deleted", "true");
    const queryString = params.toString() ? `?${params.toString()}` : "";
    const items = await api<DocumentItem[]>(`/documents${queryString}`, token);
    setDocuments(items);
    if (!selectedDocument && items[0]) setSelectedDocument(items[0].id);
  }

  async function loadWorkspace() {
    if (!token) return;
    const [projectItems, savedItems, noteItems] = await Promise.all([
      api<Project[]>("/projects", token),
      api<SavedQuery[]>("/projects/saved-queries", token),
      api<ResearchNote[]>("/projects/notes", token)
    ]);
    setProjects(projectItems);
    setSavedQueries(savedItems);
    setNotes(noteItems);
    const [usageItems, evaluationItems, apiKeyItems] = await Promise.all([
      api<UsageSummary[]>("/exports/usage", token),
      api<EvaluationRecord[]>("/exports/evaluations", token),
      api<ApiKeyRecord[]>("/auth/api-keys", token)
    ]);
    setUsage(usageItems);
    setEvaluations(evaluationItems);
    setApiKeys(apiKeyItems);
    setOpsStatus(await api<OperationalStatus>("/ops/status", token));
    try {
      setAdminOverview(await api<AdminOverview>("/admin/overview", token));
    } catch {
      setAdminOverview(null);
    }
  }

  async function loadMatrix() {
    if (!token) return;
    try {
      const rows = await api<LiteratureMatrixRow[]>("/research/matrix", token);
      setMatrixRows(rows);
    } catch {
      setMatrixRows([]);
    }
  }

  async function submitAuth(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const response = authMode === "login" ? await login(email, password) : await register(email, password, name);
      localStorage.setItem("research_token", response.access_token);
      localStorage.setItem("research_refresh_token", response.refresh_token);
      setToken(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    }
  }

  async function signOut() {
    const refreshToken = localStorage.getItem("research_refresh_token");
    try {
      await logout(token, refreshToken);
    } catch {
      // Local session cleanup still wins if the revoke request cannot reach the API.
    } finally {
      localStorage.removeItem("research_token");
      localStorage.removeItem("research_refresh_token");
      setToken(null);
      setDocuments([]);
      setSources([]);
      setAnswer("");
    }
  }

  async function submitPasswordChange(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    setAccountMessage("");
    try {
      await changePassword(token, currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setAccountMessage("Password updated. Sign in again to continue.");
      localStorage.removeItem("research_token");
      localStorage.removeItem("research_refresh_token");
      setToken(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password change failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitApiKey(event: FormEvent) {
    event.preventDefault();
    if (!token || !apiKeyName.trim()) return;
    setBusy(true);
    setError("");
    setAccountMessage("");
    try {
      const dailyLimit = apiKeyDailyLimit.trim() ? Number(apiKeyDailyLimit) : null;
      const created = await createApiKey(token, apiKeyName.trim(), apiKeyScopes, dailyLimit);
      setNewApiKey(created.api_key);
      setApiKeyName("");
      setApiKeyScopes(["*"]);
      setApiKeyDailyLimit("");
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "API key creation failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleApiKeyScope(scope: string) {
    if (scope === "*") {
      setApiKeyScopes(["*"]);
      return;
    }
    setApiKeyScopes((current) => {
      const scoped = current.filter((item) => item !== "*");
      if (scoped.includes(scope)) {
        const next = scoped.filter((item) => item !== scope);
        return next.length ? next : ["*"];
      }
      return [...scoped, scope];
    });
  }

  async function removeApiKey(apiKeyId: string) {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await revokeApiKey(token, apiKeyId);
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "API key revoke failed");
    } finally {
      setBusy(false);
    }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const file = new FormData(event.currentTarget).get("file");
    if (!(file instanceof File) || !file.name) return;
    setBusy(true);
    setError("");
    const body = new FormData();
    body.set("file", file);
    if (selectedProject) body.set("project_id", selectedProject);
    if (uploadTags.trim()) body.set("tags", uploadTags.trim());
    try {
      await api<DocumentItem>("/documents", token, { method: "POST", body });
      event.currentTarget.reset();
      await loadDocuments();
      await loadMatrix();
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function ingestUrl(event: FormEvent) {
    event.preventDefault();
    if (!token || !sourceUrl.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api<DocumentItem>("/documents/url", token, {
        method: "POST",
        body: JSON.stringify({
          url: sourceUrl.trim(),
          project_id: selectedProject || null,
          tags: uploadTags.trim() || null
        })
      });
      setSourceUrl("");
      await loadDocuments();
      await loadMatrix();
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "URL ingestion failed");
    } finally {
      setBusy(false);
    }
  }

  async function runResearch(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    setAnswer("");
    setSources([]);
    setRewrittenQuery("");
    try {
      const retrievalOptions = {
        mode: retrievalMode,
        rewrite_query: rewriteQuery,
        min_score: minScore,
        limit: resultLimit,
        project_id: selectedProject || null,
        document_type: sourceTypeFilter || null,
        tags: tagFilter.trim() || null
      };
      if (mode === "search") {
        const response = await api<{ results: Citation[]; rewritten_query: string | null }>("/search", token, {
          method: "POST",
          body: JSON.stringify({ query, document_id: selectedDocument || null, ...retrievalOptions })
        });
        setSources(response.results);
        setRewrittenQuery(response.rewritten_query || "");
        setAnswer(`${response.results.length} relevant passages found.`);
      } else if (mode === "compare") {
        const response = await api<{ answer: string; sources: Citation[]; rewritten_query: string | null }>("/qa/compare", token, {
          method: "POST",
          body: JSON.stringify({ left_document_id: selectedDocument, right_document_id: secondDocument, focus: query })
        });
        setAnswer(response.answer);
        setSources(response.sources);
        setRewrittenQuery(response.rewritten_query || "");
      } else {
        const response = await api<{ answer: string; sources: Citation[]; rewritten_query: string | null }>("/qa/ask", token, {
          method: "POST",
          body: JSON.stringify({ question: query, document_id: selectedDocument || null, ...retrievalOptions })
        });
        setAnswer(response.answer);
        setSources(response.sources);
        setRewrittenQuery(response.rewritten_query || "");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function streamAnswer() {
    if (!token) return;
    setBusy(true);
    setError("");
    setAnswer("");
    setSources([]);
    try {
      const response = await fetch(apiUrl("/qa/ask/stream"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          question: query,
          document_id: selectedDocument || null,
          mode: retrievalMode,
          rewrite_query: rewriteQuery,
          min_score: minScore,
          limit: resultLimit,
          project_id: selectedProject || null,
          document_type: sourceTypeFilter || null,
          tags: tagFilter.trim() || null
        })
      });
      if (!response.ok || !response.body) throw new Error(await response.text());
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";
        for (const event of events) handleStreamEvent(event);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Streaming failed");
    } finally {
      setBusy(false);
    }
  }

  function handleStreamEvent(event: string) {
    const eventType = event.split("\n").find((line) => line.startsWith("event: "))?.slice(7);
    const dataLine = event.split("\n").find((line) => line.startsWith("data: "));
    if (!dataLine) return;
    const data = dataLine.slice(6);
    if (eventType === "metadata") {
      const metadata = JSON.parse(data) as { rewritten_query?: string; sources?: Citation[] };
      setRewrittenQuery(metadata.rewritten_query || "");
      setSources(metadata.sources || []);
    }
    if (eventType === "token") {
      const tokenText = JSON.parse(data);
      setAnswer((current) => current + tokenText);
    }
  }

  async function reprocessDocument(documentId: string) {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await api<DocumentItem>(`/documents/${documentId}/reprocess`, token, { method: "POST" });
      await loadDocuments();
      await loadMatrix();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reprocess failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteDocument(documentId: string) {
    if (!token) return;
    if (!window.confirm("Move this document to deleted items?")) return;
    setBusy(true);
    setError("");
    try {
      await api<void>(`/documents/${documentId}`, token, { method: "DELETE" });
      if (selectedDocument === documentId) setSelectedDocument("");
      await loadDocuments();
      await loadMatrix();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function restoreDocument(documentId: string) {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await api<DocumentItem>(`/documents/${documentId}/restore`, token, { method: "POST" });
      await loadDocuments();
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Restore failed");
    } finally {
      setBusy(false);
    }
  }

  async function purgeDocument(documentId: string) {
    if (!token) return;
    if (!window.confirm("Permanently purge this document and its metadata? This cannot be undone.")) return;
    setBusy(true);
    setError("");
    try {
      await api<void>(`/documents/${documentId}/purge`, token, { method: "DELETE" });
      if (selectedDocument === documentId) setSelectedDocument("");
      await loadDocuments();
      await loadWorkspace();
      await loadMatrix();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Purge failed");
    } finally {
      setBusy(false);
    }
  }

  async function extractResearch(documentId: string) {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      await api(`/research/documents/${documentId}/extract`, token, { method: "POST" });
      await loadMatrix();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research extraction failed");
    } finally {
      setBusy(false);
    }
  }

  async function synthesizeLiterature() {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      const response = await api<{ synthesis: string }>("/research/synthesize", token, {
        method: "POST",
        body: JSON.stringify({ focus: query })
      });
      setLiteratureSynthesis(response.synthesis);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Synthesis failed");
    } finally {
      setBusy(false);
    }
  }

  async function createProject(event: FormEvent) {
    event.preventDefault();
    if (!token || !projectName.trim()) return;
    setBusy(true);
    setError("");
    try {
      const project = await api<Project>("/projects", token, {
        method: "POST",
        body: JSON.stringify({ name: projectName.trim() })
      });
      setSelectedProject(project.id);
      setProjectName("");
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Project creation failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveCurrentQuery() {
    if (!token || !query.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api<SavedQuery>("/projects/saved-queries", token, {
        method: "POST",
        body: JSON.stringify({
          title: query.trim().slice(0, 80),
          query,
          mode: retrievalMode,
          project_id: selectedProject || null
        })
      });
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save query failed");
    } finally {
      setBusy(false);
    }
  }

  async function pinNote() {
    if (!token || !noteBody.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api<ResearchNote>("/projects/notes", token, {
        method: "POST",
        body: JSON.stringify({
          title: noteBody.trim().slice(0, 80),
          body: noteBody.trim(),
          project_id: selectedProject || null,
          document_id: selectedDocument || null,
          pinned: true
        })
      });
      setNoteBody("");
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save note failed");
    } finally {
      setBusy(false);
    }
  }

  async function previewExport(kind: "report" | "bib") {
    if (!token) return;
    const projectQuery = selectedProject ? `?project_id=${selectedProject}` : "";
    const path = kind === "report" ? `/exports/report.md${projectQuery}` : `/exports/bibliography.bib${projectQuery}`;
    try {
      setExportPreview(await downloadText(path, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  }

  async function previewManifest() {
    if (!token) return;
    const projectQuery = selectedProject ? `?project_id=${selectedProject}` : "";
    try {
      const manifest = await api<Record<string, unknown>>(`/exports/manifest.json${projectQuery}`, token);
      setExportPreview(JSON.stringify(manifest, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Manifest export failed");
    }
  }

  async function updateSelectedDocument(event: FormEvent) {
    event.preventDefault();
    if (!token || !selectedDocument) return;
    setBusy(true);
    setError("");
    try {
      await api<DocumentItem>(`/documents/${selectedDocument}`, token, {
        method: "PATCH",
        body: JSON.stringify({
          title: editTitle || null,
          tags: editTags || null,
          project_id: selectedProject || null
        })
      });
      await loadDocuments();
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Metadata update failed");
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <main className="mx-auto flex min-h-screen max-w-6xl items-center px-6 py-10">
        <section className="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <div>
            <div className="flex items-center gap-3 text-teal">
              <Brain size={34} />
              <span className="text-sm font-bold uppercase tracking-widest">LangChain + Qdrant</span>
            </div>
            <h1 className="mt-5 max-w-3xl text-5xl font-black leading-tight text-ink md:text-6xl">Semantic Research Assistant</h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-stone-700">
              Upload research PDFs, index them into Qdrant, ask cited questions, compare papers, and turn dense documents into structured findings.
            </p>
          </div>
          <form onSubmit={submitAuth} className="rounded-lg border border-stone-200 bg-white p-6 shadow-soft">
            <div className="grid grid-cols-2 rounded-lg bg-stone-100 p-1 text-sm font-semibold">
              <button type="button" onClick={() => setAuthMode("register")} className={`rounded-md py-2 ${authMode === "register" ? "bg-white shadow-sm" : ""}`}>Register</button>
              <button type="button" onClick={() => setAuthMode("login")} className={`rounded-md py-2 ${authMode === "login" ? "bg-white shadow-sm" : ""}`}>Login</button>
            </div>
            <label className="mt-5 block text-sm font-semibold">Name</label>
            <input className="focus-ring mt-2 w-full rounded-lg border border-stone-300 px-3 py-2" value={name} onChange={(event) => setName(event.target.value)} />
            <label className="mt-4 block text-sm font-semibold">Email</label>
            <input className="focus-ring mt-2 w-full rounded-lg border border-stone-300 px-3 py-2" value={email} onChange={(event) => setEmail(event.target.value)} />
            <label className="mt-4 block text-sm font-semibold">Password</label>
            <input className="focus-ring mt-2 w-full rounded-lg border border-stone-300 px-3 py-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            {accountMessage ? <p className="mt-4 rounded-lg bg-teal/10 p-3 text-sm font-semibold text-teal">{accountMessage}</p> : null}
            {error ? <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
            <button className="focus-ring mt-6 w-full rounded-lg bg-teal px-4 py-3 font-bold text-white" type="submit">{authMode === "login" ? "Login" : "Create account"}</button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-stone-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <Brain className="text-teal" />
            <div>
              <h1 className="text-lg font-black">Semantic Research Assistant</h1>
              <p className="text-xs text-stone-500">FastAPI, LangChain, Qdrant, Celery</p>
            </div>
          </div>
          <button className="focus-ring rounded-lg border border-stone-300 p-2" onClick={signOut} aria-label="Log out">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-5">
          <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="flex items-center gap-2 font-bold">Projects</div>
            <select className="focus-ring mt-4 w-full rounded-lg border border-stone-300 px-3 py-2" value={selectedProject} onChange={(event) => setSelectedProject(event.target.value)}>
              <option value="">All projects</option>
              {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
            </select>
            <form className="mt-3 flex gap-2" onSubmit={createProject}>
              <input className="focus-ring min-w-0 flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm" value={projectName} onChange={(event) => setProjectName(event.target.value)} />
              <button className="focus-ring rounded-lg bg-teal px-3 py-2 text-sm font-bold text-white" disabled={busy}>Add</button>
            </form>
          </section>

          <form onSubmit={submitPasswordChange} className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="font-bold">Account</div>
            <input className="focus-ring mt-4 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" type="password" placeholder="Current password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
            <input className="focus-ring mt-3 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" type="password" placeholder="New password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
            {accountMessage ? <p className="mt-3 text-xs font-semibold text-teal">{accountMessage}</p> : null}
            <button className="focus-ring mt-4 w-full rounded-lg border border-ink px-4 py-2 text-sm font-bold text-ink" disabled={busy || !currentPassword || !newPassword}>Change password</button>
          </form>

          <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="font-bold">API Keys</div>
            <form onSubmit={submitApiKey} className="mt-4 space-y-3">
              <div className="flex gap-2">
                <input className="focus-ring min-w-0 flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm" placeholder="Key name" value={apiKeyName} onChange={(event) => setApiKeyName(event.target.value)} />
                <button className="focus-ring rounded-lg bg-ink px-3 py-2 text-sm font-bold text-white" disabled={busy || !apiKeyName.trim()}>Create</button>
              </div>
              <input className="focus-ring w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" type="number" min="1" placeholder="daily request limit" value={apiKeyDailyLimit} onChange={(event) => setApiKeyDailyLimit(event.target.value)} />
              <div className="flex flex-wrap gap-2">
                {API_KEY_SCOPES.map((scope) => (
                  <label key={scope} className={`flex items-center gap-1 rounded-lg border px-2 py-1 text-xs font-semibold ${apiKeyScopes.includes(scope) ? "border-teal bg-teal/10 text-teal" : "border-stone-200 text-stone-600"}`}>
                    <input className="h-3 w-3 accent-teal" type="checkbox" checked={apiKeyScopes.includes(scope)} onChange={() => toggleApiKeyScope(scope)} />
                    {scope}
                  </label>
                ))}
              </div>
            </form>
            {newApiKey ? (
              <div className="mt-3 rounded-lg border border-teal/30 bg-teal/10 p-3">
                <div className="text-xs font-bold text-teal">Copy this key now</div>
                <code className="mt-2 block break-all text-xs text-ink">{newApiKey}</code>
              </div>
            ) : null}
            <div className="mt-4 space-y-2">
              {apiKeys.length === 0 ? <p className="text-xs text-stone-500">No API keys yet.</p> : null}
              {apiKeys.map((key) => (
                <div key={key.id} className="rounded-lg border border-stone-200 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold">{key.name}</div>
                      <div className="mt-1 text-xs text-stone-500">{key.key_prefix}... / {key.revoked ? "revoked" : "active"}</div>
                      <div className="mt-1 text-xs text-stone-500">{key.scopes}</div>
                      <div className="mt-1 text-xs text-stone-500">{key.daily_request_limit ? `${key.requests_today}/${key.daily_request_limit} today` : `${key.requests_today} requests today`}</div>
                    </div>
                    {!key.revoked ? (
                      <button className="focus-ring rounded-lg border border-stone-300 px-2 py-1 text-xs font-bold text-ink" onClick={() => removeApiKey(key.id)} disabled={busy}>Revoke</button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <form onSubmit={upload} className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="flex items-center gap-2 font-bold"><UploadCloud size={19} /> Add Source</div>
            <input className="focus-ring mt-4 w-full rounded-lg border border-dashed border-stone-300 p-3 text-sm" name="file" type="file" accept="application/pdf,text/plain,text/markdown,.md,.markdown" />
            <input className="focus-ring mt-3 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" placeholder="tags: rag, survey, methods" value={uploadTags} onChange={(event) => setUploadTags(event.target.value)} />
            <button className="focus-ring mt-4 w-full rounded-lg bg-ink px-4 py-2 font-bold text-white" disabled={busy}>Queue document</button>
          </form>

          <form onSubmit={ingestUrl} className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="font-bold">Ingest URL</div>
            <input className="focus-ring mt-3 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" placeholder="https://example.com/article" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} />
            <button className="focus-ring mt-3 w-full rounded-lg bg-teal px-4 py-2 font-bold text-white" disabled={busy}>Fetch and index</button>
          </form>

          <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 font-bold"><FileText size={19} /> Documents</div>
              <label className="flex items-center gap-2 text-xs font-semibold text-stone-600">
                <input className="h-4 w-4 accent-teal" type="checkbox" checked={includeDeleted} onChange={(event) => setIncludeDeleted(event.target.checked)} />
                Deleted
              </label>
            </div>
            <div className="mt-4 space-y-3">
              {documents.map((doc) => (
                <div key={doc.id} className={`rounded-lg border p-3 ${selectedDocument === doc.id ? "border-teal bg-teal/5" : "border-stone-200"}`}>
                  <button onClick={() => setSelectedDocument(doc.id)} className="focus-ring w-full text-left">
                    <div className="truncate text-sm font-bold">{doc.title || doc.filename}</div>
                    {doc.source_url ? <div className="truncate text-xs text-teal">{doc.source_url}</div> : null}
                    <div className="mt-1 flex justify-between text-xs text-stone-500">
                      <span>{doc.status} / {doc.document_type}</span>
                      <span>{doc.page_count} pages / {doc.chunk_count} chunks</span>
                    </div>
                  </button>
                  <div className="mt-3 flex gap-2">
                    {doc.status === "deleted" ? (
                      <>
                        <button title="Restore document" className="focus-ring rounded-md border border-stone-300 px-2 py-1 text-xs font-bold text-teal" onClick={() => restoreDocument(doc.id)} disabled={busy}>
                          Restore
                        </button>
                        <button title="Permanently purge document" className="focus-ring rounded-md border border-stone-300 px-2 py-1 text-xs font-bold text-red-700" onClick={() => purgeDocument(doc.id)} disabled={busy}>
                          Purge
                        </button>
                      </>
                    ) : (
                      <>
                        <button title="Reprocess document" className="focus-ring rounded-md border border-stone-300 p-2 text-stone-700" onClick={() => reprocessDocument(doc.id)} disabled={busy}>
                          <RefreshCcw size={15} />
                        </button>
                        <button title="Extract research profile" className="focus-ring rounded-md border border-stone-300 px-2 py-1 text-xs font-bold text-teal" onClick={() => extractResearch(doc.id)} disabled={busy || doc.status !== "ready"}>
                          Extract
                        </button>
                        <button title="Delete document" className="focus-ring rounded-md border border-stone-300 p-2 text-red-700" onClick={() => deleteDocument(doc.id)} disabled={busy}>
                          <Trash2 size={15} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
              {!documents.length ? <p className="text-sm text-stone-500">No documents yet.</p> : null}
            </div>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="font-bold">Saved Queries</div>
            <div className="mt-3 space-y-2">
              {savedQueries.slice(0, 5).map((saved) => (
                <button key={saved.id} className="focus-ring w-full rounded-lg border border-stone-200 p-2 text-left text-sm" onClick={() => { setQuery(saved.query); setRetrievalMode(saved.mode as "hybrid" | "vector" | "keyword"); }}>
                  {saved.title}
                </button>
              ))}
              {!savedQueries.length ? <p className="text-sm text-stone-500">No saved queries yet.</p> : null}
            </div>
          </section>
        </aside>

        <section className="space-y-5">
          <form onSubmit={runResearch} className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="flex flex-wrap gap-2">
              {([
                ["ask", MessageSquareText, "Ask"],
                ["search", Search, "Search"],
                ["compare", GitCompareArrows, "Compare"]
              ] as const).map(([key, Icon, label]) => (
                <button key={key} type="button" onClick={() => setMode(key)} className={`focus-ring flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-bold ${mode === key ? "border-teal bg-teal text-white" : "border-stone-300 bg-white"}`}>
                  <Icon size={16} /> {label}
                </button>
              ))}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <select className="focus-ring rounded-lg border border-stone-300 px-3 py-2" value={selectedDocument} onChange={(event) => setSelectedDocument(event.target.value)}>
                <option value="">All ready documents</option>
                {readyDocs.map((doc) => <option key={doc.id} value={doc.id}>{doc.title || doc.filename}</option>)}
              </select>
              {mode === "compare" ? (
                <select className="focus-ring rounded-lg border border-stone-300 px-3 py-2" value={secondDocument} onChange={(event) => setSecondDocument(event.target.value)}>
                  <option value="">Choose second document</option>
                  {readyDocs.map((doc) => <option key={doc.id} value={doc.id}>{doc.title || doc.filename}</option>)}
                </select>
              ) : null}
            </div>
            <textarea className="focus-ring mt-4 min-h-32 w-full rounded-lg border border-stone-300 px-3 py-3" value={query} onChange={(event) => setQuery(event.target.value)} />
            <div className="mt-4 grid gap-3 md:grid-cols-4">
              <label className="text-sm font-semibold">
                Retrieval
                <select className="focus-ring mt-2 w-full rounded-lg border border-stone-300 px-3 py-2 font-normal" value={retrievalMode} onChange={(event) => setRetrievalMode(event.target.value as "hybrid" | "vector" | "keyword")}>
                  <option value="hybrid">Hybrid</option>
                  <option value="vector">Vector</option>
                  <option value="keyword">Keyword</option>
                </select>
              </label>
              <label className="text-sm font-semibold">
                Results
                <input className="focus-ring mt-2 w-full rounded-lg border border-stone-300 px-3 py-2 font-normal" type="number" min={3} max={20} value={resultLimit} onChange={(event) => setResultLimit(Number(event.target.value))} />
              </label>
              <label className="text-sm font-semibold">
                Min score
                <input className="focus-ring mt-2 w-full rounded-lg border border-stone-300 px-3 py-2 font-normal" type="number" min={0} max={1} step={0.01} value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} />
              </label>
              <label className="flex items-end gap-2 text-sm font-semibold">
                <input className="h-4 w-4 accent-teal" type="checkbox" checked={rewriteQuery} onChange={(event) => setRewriteQuery(event.target.checked)} />
                Rewrite query
              </label>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="text-sm font-semibold">
                Source type
                <select className="focus-ring mt-2 w-full rounded-lg border border-stone-300 px-3 py-2 font-normal" value={sourceTypeFilter} onChange={(event) => setSourceTypeFilter(event.target.value)}>
                  <option value="">Any type</option>
                  <option value="pdf">PDF</option>
                  <option value="text">Text</option>
                  <option value="markdown">Markdown</option>
                  <option value="url">URL</option>
                </select>
              </label>
              <label className="text-sm font-semibold">
                Required tags
                <input className="focus-ring mt-2 w-full rounded-lg border border-stone-300 px-3 py-2 font-normal" placeholder="survey, methods" value={tagFilter} onChange={(event) => setTagFilter(event.target.value)} />
              </label>
            </div>
            {error ? <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="focus-ring rounded-lg bg-coral px-5 py-3 font-bold text-white" disabled={busy}>{busy ? "Working..." : "Run"}</button>
              <button type="button" className="focus-ring rounded-lg border border-stone-300 px-4 py-3 font-bold" onClick={streamAnswer} disabled={busy || mode !== "ask"}>Stream</button>
              <button type="button" className="focus-ring rounded-lg border border-stone-300 px-4 py-3 font-bold" onClick={saveCurrentQuery} disabled={busy}>Save query</button>
            </div>
          </form>

          {answer ? (
            <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-black">Result</h2>
              {rewrittenQuery && rewrittenQuery !== query ? (
                <p className="mt-2 rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-600">Retrieval query: {rewrittenQuery}</p>
              ) : null}
              <div className="mt-3 whitespace-pre-wrap leading-7 text-stone-800">{answer}</div>
              <div className="mt-4 flex gap-2">
                <input className="focus-ring min-w-0 flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm" placeholder="Turn this into a pinned note..." value={noteBody} onChange={(event) => setNoteBody(event.target.value)} />
                <button className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm font-bold" onClick={pinNote}>Pin</button>
              </div>
            </section>
          ) : null}

          {selectedDocument ? (
            <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-black">Document Summary</h2>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-stone-700">
                {documents.find((doc) => doc.id === selectedDocument)?.summary || "Summary appears here after background processing completes."}
              </p>
              <form className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]" onSubmit={updateSelectedDocument}>
                <input className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm" placeholder="Document title" value={editTitle} onChange={(event) => setEditTitle(event.target.value)} />
                <input className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm" placeholder="tags" value={editTags} onChange={(event) => setEditTags(event.target.value)} />
                <button className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm font-bold" disabled={busy}>Update</button>
              </form>
            </section>
          ) : null}

          <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-black">Literature Matrix</h2>
              <button className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm font-bold" onClick={synthesizeLiterature} disabled={busy || !matrixRows.length}>Synthesize</button>
            </div>
            {literatureSynthesis ? <p className="mt-3 whitespace-pre-wrap rounded-lg bg-stone-100 p-3 text-sm leading-6 text-stone-700">{literatureSynthesis}</p> : null}
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-[900px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-200 text-xs uppercase text-stone-500">
                    <th className="p-2">Paper</th>
                    <th className="p-2">Methods</th>
                    <th className="p-2">Claims</th>
                    <th className="p-2">Findings</th>
                    <th className="p-2">Limitations</th>
                  </tr>
                </thead>
                <tbody>
                  {matrixRows.map((row) => (
                    <tr key={row.document_id} className="border-b border-stone-100 align-top">
                      <td className="max-w-52 p-2">
                        <div className="font-bold">{row.title || row.filename}</div>
                        <div className="mt-1 text-xs text-stone-500">{row.authors || "Unknown authors"} {row.year ? `(${row.year})` : ""}</div>
                      </td>
                      <td className="max-w-64 p-2 text-stone-700">{row.methods || "-"}</td>
                      <td className="max-w-64 p-2 text-stone-700">{row.claims || "-"}</td>
                      <td className="max-w-64 p-2 text-stone-700">{row.findings || "-"}</td>
                      <td className="max-w-64 p-2 text-stone-700">{row.limitations || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!matrixRows.length ? <p className="py-4 text-sm text-stone-500">Research profiles appear here after extraction finishes.</p> : null}
            </div>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <h2 className="text-lg font-black">Pinned Notes</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {notes.filter((note) => note.pinned).slice(0, 6).map((note) => (
                <div key={note.id} className="rounded-lg border border-stone-200 p-3">
                  <div className="font-bold">{note.title}</div>
                  <p className="mt-2 text-sm leading-6 text-stone-700">{note.body}</p>
                </div>
              ))}
              {!notes.filter((note) => note.pinned).length ? <p className="text-sm text-stone-500">Pinned notes appear here.</p> : null}
            </div>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-black">Exports And Quality</h2>
              <div className="flex gap-2">
                <button className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm font-bold" onClick={() => previewExport("report")}>Report</button>
                <button className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm font-bold" onClick={() => previewExport("bib")}>BibTeX</button>
                <button className="focus-ring rounded-lg border border-stone-300 px-3 py-2 text-sm font-bold" onClick={previewManifest}>Manifest</button>
              </div>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-lg border border-stone-200 p-3">
                <div className="text-sm font-bold">Operations</div>
                <div className="mt-2 space-y-1 text-sm text-stone-700">
                  {opsStatus ? Object.entries(opsStatus.documents_by_status).map(([status, count]) => (
                    <div key={status} className="flex justify-between gap-3">
                      <span>{status}</span>
                      <span>{count}</span>
                    </div>
                  )) : <p className="text-stone-500">No status yet.</p>}
                </div>
              </div>
              <div className="rounded-lg border border-stone-200 p-3">
                <div className="text-sm font-bold">Usage</div>
                <div className="mt-2 space-y-1 text-sm text-stone-700">
                  {usage.map((item) => (
                    <div key={item.operation} className="flex justify-between gap-3">
                      <span>{item.operation}</span>
                      <span>{item.calls} calls / {item.estimated_tokens} tok</span>
                    </div>
                  ))}
                  {!usage.length ? <p className="text-stone-500">No usage recorded yet.</p> : null}
                </div>
              </div>
              <div className="rounded-lg border border-stone-200 p-3">
                <div className="text-sm font-bold">Recent Groundedness</div>
                <div className="mt-2 space-y-2 text-sm text-stone-700">
                  {evaluations.slice(0, 4).map((item) => (
                    <div key={item.id} className="rounded-md bg-stone-50 p-2">
                      <div className="font-semibold">{item.groundedness_score}% grounded</div>
                      <div className="line-clamp-2 text-xs text-stone-500">{item.question}</div>
                    </div>
                  ))}
                  {!evaluations.length ? <p className="text-stone-500">No evaluations yet.</p> : null}
                </div>
              </div>
            </div>
            {exportPreview ? (
              <pre className="mt-4 max-h-80 overflow-auto rounded-lg bg-ink p-4 text-xs leading-5 text-white">{exportPreview}</pre>
            ) : null}
          </section>

          {adminOverview ? (
            <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
              <h2 className="text-lg font-black">Admin Operations</h2>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-lg border border-stone-200 p-3">
                  <div className="text-sm font-bold">Users</div>
                  <div className="mt-2 space-y-2 text-sm text-stone-700">
                    {adminOverview.users.slice(0, 5).map((user) => (
                      <div key={user.id} className="rounded-md bg-stone-50 p-2">
                        <div className="truncate font-semibold">{user.email}</div>
                        <div className="text-xs text-stone-500">{user.document_count} docs / {user.api_key_count} keys</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-lg border border-stone-200 p-3">
                  <div className="text-sm font-bold">Failed Jobs</div>
                  <div className="mt-2 space-y-2 text-sm text-stone-700">
                    {adminOverview.failed_jobs.slice(0, 4).map((job) => (
                      <div key={job.document_id} className="rounded-md bg-red-50 p-2">
                        <div className="truncate font-semibold text-red-700">{job.filename}</div>
                        <div className="truncate text-xs text-red-600">{job.owner_email} / {job.status}</div>
                      </div>
                    ))}
                    {!adminOverview.failed_jobs.length ? <p className="text-stone-500">No failed jobs.</p> : null}
                  </div>
                </div>
                <div className="rounded-lg border border-stone-200 p-3">
                  <div className="text-sm font-bold">Storage</div>
                  <div className="mt-2 space-y-1 text-sm text-stone-700">
                    <div className="flex justify-between gap-3"><span>Backend</span><span>{adminOverview.storage.backend}</span></div>
                    <div className="flex justify-between gap-3"><span>Files</span><span>{adminOverview.storage.local_upload_files}</span></div>
                    <div className="flex justify-between gap-3"><span>Local MB</span><span>{(adminOverview.storage.local_upload_bytes / 1024 / 1024).toFixed(2)}</span></div>
                  </div>
                </div>
              </div>
            </section>
          ) : null}

          <SourceList sources={sources} />
        </section>
      </div>
    </main>
  );
}
