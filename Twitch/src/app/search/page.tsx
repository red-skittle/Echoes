"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Clock3, Search as SearchIcon, Video } from "lucide-react";
import { api, formatTime } from "@/lib/api";

type Result = { id: string; slug: string; title: string; summary: string; category: string; is_sample: boolean; relevance: number; source?: { start_seconds: number; video: { id: string; title: string; url?: string } } | null };
type SearchResult = { answer: string; grounded: boolean; mode: string; results: Result[] };

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const initial = new URLSearchParams(window.location.search).get("q");
    if (!initial) return;
    setQuery(initial);
    setLoading(true);
    api<SearchResult>("/api/search/ask", { method: "POST", body: JSON.stringify({ query: initial, streamer_username: "mossybytes" }) })
      .then(setResult).catch((e: Error) => setError(e.message)).finally(() => setLoading(false));
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setLoading(true); setResult(null);
    try { setResult(await api<SearchResult>("/api/search/ask", { method: "POST", body: JSON.stringify({ query, streamer_username: "mossybytes" }) })); }
    catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }
  return <main className="subpage"><header><Link href="/" className="sub-back"><ArrowLeft size={15}/> Afterlife</Link><Link href="/explore" className="sub-top-link">Explore wikis <ArrowRight size={14}/></Link></header><section className="sub-content"><span className="section-kicker">SEARCH COMMUNITY HISTORY</span><h1>What do you remember?</h1><p className="sub-intro">Ask a question about mossybytes’ sample wiki. Answers only use the source-linked entries in the API.</p><form className="search-page-form" onSubmit={submit}><SearchIcon size={17}/><input required minLength={3} value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="When did chat name the underground village?"/><button disabled={loading}>{loading?"Searching…":"Search"}</button></form>{error&&<div className="sub-error">{error}</div>}{result&&<section className="answer-panel"><span className="section-kicker">{result.grounded ? "FROM THE WIKI" : "NO MATCH"} · {result.mode.toUpperCase()}</span><p>{result.answer}</p>{result.results.length>0&&<div className="result-list">{result.results.map((item)=><article className="result-card" key={item.id}><div className="result-category">{item.category}{item.is_sample&&<span>SAMPLE</span>}</div><h2><Link href={`/wiki/${item.slug}`}>{item.title}</Link></h2><p>{item.summary}</p>{item.source&&<div className="result-source"><Video size={14}/><span>{item.source.video.title}</span><span className="source-time"><Clock3 size={12}/>{formatTime(item.source.start_seconds)}</span></div>}<Link className="read-link" href={`/wiki/${item.slug}`}>Read story <ArrowRight size={13}/></Link></article>)}</div>}</section>}<div className="suggested-queries"><span>Try asking</span>{["When was the underground village found?", "What is the door problem?", "Who is Moss the axolotl?"].map((q)=><button key={q} onClick={()=>setQuery(q)}>{q}</button>)}</div></section></main>;
}
