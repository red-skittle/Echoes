"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, BookOpen, Search, Twitch } from "lucide-react";
import { API_URL, api } from "@/lib/api";

type Community = { id: string; username: string; display_name: string; description: string; video_count: number; article_count: number; is_sample: boolean };

export default function ExplorePage() {
  const [items, setItems] = useState<Community[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [channel, setChannel] = useState("");
  const [importMessage, setImportMessage] = useState("");
  const [importing, setImporting] = useState(false);
  const [oauthReady, setOauthReady] = useState(false);
  useEffect(() => { api<{items: Community[]}>('/api/streamers').then((data) => setItems(data.items)).catch((e: Error) => setError(e.message)); }, []);
  useEffect(() => { api<{twitch_oauth_configured:boolean}>('/api/auth/status').then(x=>setOauthReady(x.twitch_oauth_configured)).catch(()=>{}); }, []);
  async function importVideos(event: FormEvent) {
    event.preventDefault(); setImporting(true); setError(""); setImportMessage("");
    try {
      const result = await api<{imported:number;received:number;message:string}>('/api/videos/import', {method:'POST',body:JSON.stringify({streamer_username:channel})});
      setImportMessage(`${result.message} Added ${result.imported} new video records.`);
      const refreshed = await api<{items:Community[]}>('/api/streamers'); setItems(refreshed.items);
    } catch(e) { setError((e as Error).message); }
    finally { setImporting(false); }
  }
  const filtered = items.filter((x) => `${x.username} ${x.description}`.toLowerCase().includes(query.toLowerCase()));
  return <main className="subpage"><header><Link href="/" className="sub-back"><ArrowLeft size={15}/> Afterlife</Link><Link href="/search" className="sub-top-link"><Search size={15}/> Search stories</Link></header><section className="sub-content"><span className="section-kicker">COMMUNITIES, REMEMBERED</span><h1>Explore wikis.</h1><p className="sub-intro">Browse community knowledge or import publicly available Twitch video metadata. Imports never include the video itself.</p><label className="sub-search"><Search size={16}/><input placeholder="Find a streamer wiki" value={query} onChange={(e)=>setQuery(e.target.value)}/></label><form className="metadata-import" onSubmit={importVideos}><div><span className="section-kicker">PUBLIC TWITCH VIDEO METADATA</span><small>Requires server-side Twitch app credentials. No VOD media is downloaded.</small></div><input aria-label="Twitch channel login" required minLength={1} maxLength={100} pattern="[A-Za-z0-9_]+" placeholder="Twitch channel login" value={channel} onChange={e=>setChannel(e.target.value)}/><button disabled={importing}>{importing?"Importing…":"Import metadata"}</button></form>{error&&<div className="sub-error">{error}</div>}{importMessage&&<div className="import-success">{importMessage}</div>}<div className="community-list">{filtered.map((item)=><Link className="community-list-card" href={`/streamer/${item.username}`} key={item.id}><div className="list-avatar">{item.display_name[0]}</div><div className="list-body"><div className="list-title">{item.display_name}{item.is_sample&&<span className="sample-tag">SAMPLE CONTENT</span>}</div><p>{item.description}</p><div className="list-counts"><span><BookOpen size={13}/>{item.article_count} wiki entries</span><span><Twitch size={13}/>{item.video_count} videos</span></div></div><ArrowRight size={17}/></Link>)}{!error&&filtered.length===0&&<div className="sub-empty">{items.length ? "No wikis match that search." : "Loading community wikis…"}</div>}</div>{oauthReady?<a className="sub-connect" href={`${API_URL}/api/auth/twitch`}><Twitch size={16}/> Connect a Twitch account <span>OAuth is enabled for this server.</span></a>:<div className="sub-connect"><Twitch size={16}/> Connect a Twitch account <span>Add server credentials to enable sign-in.</span></div>}</section></main>;
}
