"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, Check, Clock3, MessageSquareText, Send, X } from "lucide-react";
import { api } from "@/lib/api";

type Contribution = { id: string; title: string; body: string; kind: string; contributor_name: string; status: string; created_at: string };

export default function ContributionsPage() {
  const [items, setItems] = useState<Contribution[]>([]);
  const [entryId, setEntryId] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState("suggestion");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [reviewToken, setReviewToken] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { setEntryId(new URLSearchParams(window.location.search).get("entry_id") || ""); api<{ items: Contribution[] }>("/api/contributions").then(x => setItems(x.items)).catch(() => {}); }, []);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage(""); setError("");
    try {
      const result = await api<{ id: string; status: string; message: string }>("/api/contributions", {
        method: "POST", body: JSON.stringify({ contributor_name: name, kind, title, body, streamer_username: "mossybytes", wiki_entry_id: entryId || null }),
      });
      setMessage(result.message);
      setItems(old => [{ id: result.id, title, body, kind, contributor_name: name, status: result.status, created_at: new Date().toISOString() }, ...old]);
      setTitle(""); setBody("");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function review(id: string, status: "approved" | "rejected") {
    setError("");
    try {
      await api(`/api/contributions/${id}/review`, { method: "PATCH", headers: { "X-Review-Token": reviewToken }, body: JSON.stringify({ status }) });
      setItems(old => old.map(item => item.id === id ? { ...item, status } : item));
    } catch (e) { setError((e as Error).message); }
  }

  return <main className="subpage">
    <header><Link href="/streamer/mossybytes" className="sub-back"><ArrowLeft size={15}/> mossybytes wiki</Link><span className="sub-top-link"><MessageSquareText size={15}/> Community contributions</span></header>
    <section className="sub-content"><span className="section-kicker">THE COMMUNITY KNOWS THE DETAILS</span><h1>Keep the story right.</h1>
      <p className="sub-intro">{entryId ? "Your suggestion will be attached to the article you came from. " : ""}Suggest a new entry, add missing context, or point out a correction. Submissions stay pending until a configured reviewer approves them.</p>
      <form className="contribution-form" onSubmit={submit}>
        <label>Your name<input required minLength={2} maxLength={100} value={name} onChange={e => setName(e.target.value)} placeholder="How should we credit you?"/></label>
        <label>Contribution type<select value={kind} onChange={e => setKind(e.target.value)}><option value="suggestion">Suggest a story</option><option value="correction">Correction</option><option value="timestamp">Missing timestamp</option></select></label>
        <label>Title<input required minLength={4} maxLength={240} value={title} onChange={e => setTitle(e.target.value)} placeholder="A short description"/></label>
        <label>What should the wiki know?<textarea required minLength={10} maxLength={5000} rows={5} value={body} onChange={e => setBody(e.target.value)} placeholder="Share context, a source stream, or a timestamp if you know it."/></label>
        <button disabled={busy}><Send size={15}/>{busy ? "Sending…" : "Submit for review"}</button>
        {message && <p className="form-success"><Check size={15}/>{message}</p>}{error && <p className="form-error">{error}</p>}
      </form>
      <div className="inner-section-heading contributions-heading"><div><span className="section-kicker">COMMUNITY QUEUE</span><h2>Recent submissions</h2></div></div>
      <label className="review-key">Authorized reviewer token<input type="password" autoComplete="off" value={reviewToken} onChange={e => setReviewToken(e.target.value)} placeholder="Only needed by wiki reviewers"/><small>Used for this session only. Review is disabled on the server until a token is configured.</small></label>
      <div className="contribution-list">{items.map(item => <article className="contribution-item" key={item.id}>
        <span className={`contribution-state state-${item.status}`}><Clock3 size={12}/>{item.status}</span><span className="contribution-kind">{item.kind}</span><h3>{item.title}</h3><p>{item.body}</p><small>Submitted by {item.contributor_name}</small>
        {item.status === "pending" && reviewToken && <div className="review-actions"><button onClick={() => review(item.id, "approved")}><Check size={13}/>Approve</button><button onClick={() => review(item.id, "rejected")}><X size={13}/>Reject</button></div>}
      </article>)}{items.length === 0 && <div className="sub-empty">No community submissions yet. Start the conversation.</div>}</div>
    </section>
  </main>;
}
