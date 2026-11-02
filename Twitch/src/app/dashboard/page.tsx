"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, BookOpen, Check, Clock3, Database, Film, ShieldAlert, Twitch, Upload } from "lucide-react";
import { API_URL, api } from "@/lib/api";

type Stats = { streamers: number; videos: number; wiki_entries: number; pending_contributions: number; pending_drafts: number; queued_jobs: number; demo_mode: boolean; indexing_enabled: boolean };
type Auth = { authenticated: boolean; display_name: string | null; twitch_oauth_configured: boolean; streamers: { id: string; username: string }[] };
type ReviewDraft = { id: string; title: string; summary: string; category: string; source?: { start_seconds: number; video: { title: string } } | null };

function CreatorUpload({ streamers }: { streamers: Auth["streamers"] }) {
  const [streamer, setStreamer] = useState(streamers[0]?.username || "");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true); setMessage(""); setError("");
    const data = new FormData();
    data.set("streamer_username", streamer); data.set("title", title); data.set("media", file);
    try {
      const result = await api<{ id: string; title: string; status: string; message: string }>("/api/videos/upload", { method: "POST", body: data });
      setMessage(`${result.title}: ${result.message}`); setTitle(""); setFile(null);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <section className="creator-upload"><div><span className="section-kicker">CREATOR-AUTHORIZED MEDIA</span><h2>Upload a recording.</h2><p>Files are only accepted for Twitch channels owned by your connected account. Uploading doesn’t mean media has been processed.</p></div><form onSubmit={submit}><label>Channel<select value={streamer} onChange={e => setStreamer(e.target.value)}>{streamers.map(x => <option key={x.id} value={x.username}>{x.username}</option>)}</select></label><label>Video title<input required minLength={3} maxLength={300} value={title} onChange={e => setTitle(e.target.value)} placeholder="Name this recording"/></label><label className="upload-file-label"><Upload size={15}/>{file ? file.name : "Choose authorized media"}<input type="file" required accept=".mp4,.mov,.mkv,.webm,.m4v,.mp3,.wav,.m4a" onChange={e => setFile(e.target.files?.[0] || null)}/></label><button disabled={busy || !streamer || !file}>{busy ? "Uploading…" : "Upload recording"}</button></form>{message && <p className="upload-success"><Check size={14}/>{message}</p>}{error && <p className="form-error">{error}</p>}</section>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [auth, setAuth] = useState<Auth | null>(null);
  const [drafts, setDrafts] = useState<ReviewDraft[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Stats>("/api/dashboard/stats").then(setStats).catch(e => setError(e.message));
    api<Auth>("/api/auth/status").then(status => {
      setAuth(status);
      if (status.authenticated && status.streamers.length) api<{ items: ReviewDraft[] }>("/api/dashboard/review").then(x => setDrafts(x.items)).catch(e => setError(e.message));
    }).catch(() => setAuth({ authenticated: false, display_name: null, twitch_oauth_configured: false, streamers: [] }));
  }, []);
  async function signOut() { await api("/api/auth/logout", { method: "POST" }); location.reload(); }
  async function reviewDraft(draft: ReviewDraft, status: "verified" | "rejected") {
    try {
      await api(`/api/wiki/${draft.id}/review`, { method: "PATCH", body: JSON.stringify({ status }) });
      setDrafts(items => items.filter(item => item.id !== draft.id));
      if (status === "verified") setStats(value => value ? { ...value, wiki_entries: value.wiki_entries + 1 } : value);
    } catch (e) { setError((e as Error).message); }
  }
  return <main className="subpage">
    <header><Link href="/" className="sub-back"><ArrowLeft size={15}/> Afterlife</Link><span className="sub-top-link"><Database size={15}/> Workspace overview</span></header>
    <section className="sub-content"><span className="section-kicker">CREATOR WORKSPACE</span><h1>Wiki dashboard.</h1><p className="sub-intro">A live view of this workspace. Sample records are separate from real creator media.</p>
      {error && <div className="sub-error">{error}</div>}
      {stats ? <>
        <div className="dashboard-grid">{[["Community wikis", stats.streamers, <Twitch size={17}/>], ["Video records", stats.videos, <Film size={17}/>], ["Wiki entries", stats.wiki_entries, <BookOpen size={17}/>], ["AI drafts to review", stats.pending_drafts, <Clock3 size={17}/>], ["Pending contributions", stats.pending_contributions, <Clock3 size={17}/>]].map(([name, value, icon]) => <div className="dashboard-stat" key={String(name)}><span>{icon}{name}</span><b>{value}</b><small>Current database count</small></div>)}</div>
        <div className="dashboard-warning"><ShieldAlert size={18}/><div><b>{auth?.authenticated ? `Connected as ${auth.display_name}` : stats.demo_mode ? "Sample data is active" : "No Twitch account connected"}</b><p>Public Twitch metadata import is available from Explore. Video processing requires an authorized upload, FFmpeg, and an OpenAI key.</p></div></div>
        <div className="dashboard-actions"><Link href="/explore"><Twitch size={16}/>Browse wiki <ArrowRight size={14}/></Link><Link href="/contributions"><BookOpen size={16}/>Contribution queue <ArrowRight size={14}/></Link>
          {auth?.authenticated ? <button onClick={signOut}>Sign out</button> : auth?.twitch_oauth_configured ? <a href={`${API_URL}/api/auth/twitch`}><Twitch size={16}/>Connect Twitch <ArrowRight size={14}/></a> : <span className="disabled-action"><Twitch size={16}/>Connect Twitch · configure OAuth</span>}
        </div>
        {auth?.authenticated && auth.streamers.length > 0 && <CreatorUpload streamers={auth.streamers}/>}
        {auth?.authenticated && auth.streamers.length === 0 && <div className="upload-info">This account is connected, but no owner channel is available for upload.</div>}
        {drafts.length > 0 && <section className="draft-review"><div><span className="section-kicker">AI-GENERATED · NEEDS YOUR REVIEW</span><h2>Wiki drafts</h2></div>{drafts.map(draft => <article key={draft.id}><span>{draft.category.toUpperCase()}</span><b>{draft.title}</b><p>{draft.summary}</p>{draft.source && <small>{draft.source.video.title} · {draft.source.start_seconds}s</small>}<div><button onClick={() => reviewDraft(draft, "verified")}>Approve</button><button onClick={() => reviewDraft(draft, "rejected")}>Reject</button></div></article>)}</section>}
      </> : <div className="sub-empty">Loading workspace…</div>}
    </section>
  </main>;
}
