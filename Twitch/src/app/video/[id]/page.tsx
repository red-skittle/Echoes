"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Clock3, ExternalLink, Film } from "lucide-react";
import { api, formatTime } from "@/lib/api";

type VideoRecord = {
  id: string; title: string; url?: string; twitch_video_id?: string; status: string; is_sample: boolean; streamer: string;
  moments: { slug: string; title: string; summary: string; start_seconds: number; end_seconds: number }[];
};

function twitchTime(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  return `${hours ? `${hours}h` : ""}${minutes ? `${minutes}m` : ""}${remainder}s`;
}

export default function VideoPage({ params }: { params: Promise<{ id: string }> }) {
  const [item, setItem] = useState<VideoRecord | null>(null);
  const [error, setError] = useState("");
  const [parent, setParent] = useState("");
  const [seek, setSeek] = useState(0);
  const [authenticated, setAuthenticated] = useState(false);
  const [processError, setProcessError] = useState("");
  const [processMessage, setProcessMessage] = useState("");
  useEffect(() => {
    setParent(window.location.hostname);
    const start = Number(new URLSearchParams(window.location.search).get("t") || 0);
    if (Number.isFinite(start) && start > 0) setSeek(start);
    params.then(({ id }) => api<VideoRecord>(`/api/videos/${encodeURIComponent(id)}`).then(setItem).catch((e: Error) => setError(e.message)));
    api<{ authenticated: boolean }>("/api/auth/status").then(status => setAuthenticated(status.authenticated)).catch(() => {});
  }, [params]);
  useEffect(() => {
    if (!item || !["queued", "processing"].includes(item.status)) return;
    const timer = window.setInterval(() => api<VideoRecord>(`/api/videos/${encodeURIComponent(item.id)}`).then(setItem).catch(() => {}), 3000);
    return () => window.clearInterval(timer);
  }, [item?.id, item?.status]);
  async function startIndexing() {
    if (!item) return;
    setProcessError(""); setProcessMessage("");
    try {
      const result = await api<{ message: string }>(`/api/videos/${item.id}/process`, { method: "POST" });
      setProcessMessage(result.message);
      const updated = await api<VideoRecord>(`/api/videos/${item.id}`); setItem(updated);
    } catch (e) { setProcessError((e as Error).message); }
  }
  const player = item?.twitch_video_id && parent
    ? `https://player.twitch.tv/?video=v${encodeURIComponent(item.twitch_video_id)}&parent=${encodeURIComponent(parent)}&autoplay=false&time=${twitchTime(seek)}`
    : null;

  return <main className="subpage">
    <header><Link href="/explore" className="sub-back"><ArrowLeft size={15}/> Communities</Link><Link href="/streamer/mossybytes" className="sub-top-link">mossybytes wiki <ArrowRight size={14}/></Link></header>
    <section className="sub-content">
      {error ? <div className="sub-error">{error}</div> : !item ? <div className="sub-empty">Loading video record…</div> : <>
        <span className="section-kicker">{item.is_sample ? "SAMPLE VIDEO REFERENCE" : "VIDEO RECORD"} · {item.status.toUpperCase()}</span>
        <h1>{item.title}</h1>
        <p className="sub-intro">{item.is_sample ? "This synthetic sample has no real stream attached." : "Twitch video metadata is shown separately from creator-authorized media processing."}</p>
        {authenticated && ["uploaded", "processing_failed"].includes(item.status) && <button className="process-video-button" onClick={startIndexing}><Film size={15}/>Start indexing this authorized upload</button>}
        {processMessage && <p className="upload-success">{processMessage}</p>}{processError && <div className="sub-error">{processError}</div>}
        {player ? <div className="twitch-player"><iframe key={`${item.twitch_video_id}-${seek}`} src={player} title={`Twitch video: ${item.title}`} allow="autoplay; fullscreen" allowFullScreen/></div> : <div className="video-placeholder"><Film size={32}/><b>{item.is_sample ? "Synthetic sample record" : "No playable Twitch recording"}</b><span>{item.is_sample ? "No real stream or Twitch timestamp is represented by this sample." : "The Twitch API does not provide raw VOD media."}</span>{item.url && <a href={item.url} target="_blank" rel="noreferrer">Open original Twitch page <ExternalLink size={13}/></a>}</div>}
        <div className="inner-section-heading"><div><span className="section-kicker">CHAPTERS & MOMENTS</span><h2>Related wiki entries</h2></div></div>
        <div className="video-moments">{item.moments.map(moment => <article className="video-moment" key={moment.slug}><button className="moment-time seek-button" onClick={() => { setSeek(moment.start_seconds); history.replaceState(null, "", `?t=${moment.start_seconds}`); }} title="Seek the Twitch player"><Clock3 size={12}/>{formatTime(moment.start_seconds)}</button><Link href={`/wiki/${moment.slug}`}><b>{moment.title}</b><small>{moment.summary}</small></Link><ArrowRight size={15}/></article>)}{item.moments.length === 0 && <div className="sub-empty">No indexed chapters for this video.</div>}</div>
      </>}
    </section>
  </main>;
}
