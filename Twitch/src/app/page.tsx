"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, ArrowDownRight, ArrowRight, Bookmark, Check, ChevronDown, CircleHelp, Compass, ExternalLink, Film, History, House, Menu, MessageSquareText, Search, Settings2, Sparkles, Twitch, Users, X } from "lucide-react";

const navigation = [
  { name: "Explore", icon: Compass, href: "/explore" }, { name: "Search", icon: Search, href: "/search" }, { name: "My wikis", icon: Bookmark, href: "/dashboard" },
  { name: "Sample wiki", icon: History, href: "/streamer/mossybytes" }, { name: "Video wiki", icon: Film, href: "/streamer/mossybytes#stories" }, { name: "Contributions", icon: MessageSquareText, href: "/contributions" },
];

const moments = [
  { time: "00:42:18", title: "The Underneath", slug: "the-underneath", stream: "A very normal Minecraft Monday", date: "Oct 24, 2025", image: "#29443a", tag: "Minecraft", detail: "The server's underground village began as an unexpected discovery beneath spawn." },
  { time: "00:24:10", title: "The door problem", slug: "the-door-problem", stream: "A very normal Minecraft Monday", date: "Oct 24, 2025", image: "#463b59", tag: "Community lore", detail: "Every build session brings a new debate about how many doors a house really needs." },
  { time: "00:13:40", title: "The first community build", slug: "first-community-build", stream: "A very normal Minecraft Monday", date: "Oct 24, 2025", image: "#3d4748", tag: "Milestone", detail: "A tiny spawn house became a shared project and a permanent meeting spot." },
];
const articles = [
  { title: "The Underneath", slug: "the-underneath", kind: "COMMUNITY LORE", text: "The server's underground village began as an unexpected discovery beneath spawn.", count: "1 source" },
  { title: "The door problem", slug: "the-door-problem", kind: "RUNNING JOKE", text: "Every build session brings a new debate about how many doors a house really needs.", count: "1 source" },
  { title: "The first community build", slug: "first-community-build", kind: "MILESTONE", text: "A tiny spawn house became a shared project and a permanent meeting spot.", count: "1 source" },
];

export default function Home() {
  const [active, setActive] = useState("Explore");
  const [query, setQuery] = useState("");
  const [saved, setSaved] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { setSaved(localStorage.getItem("afterlife:saved-wiki") === "true"); }, []);
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return moments;
    return moments.filter((item) => `${item.title} ${item.stream} ${item.tag} ${item.detail}`.toLowerCase().includes(normalized));
  }, [query]);

  return <main className="shell">
    <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
      <a className="brand" href="#home" onClick={() => setActive("Explore")}><span className="brand-mark"><Activity size={20} strokeWidth={2.5}/></span><span>afterlife<span className="brand-period">.</span></span></a>
      <div className="workspace-label">YOUR SPACE</div>
      <nav aria-label="Main navigation">{navigation.map(({name, icon: Icon, href}) => <Link key={name} href={href} className={`nav-item ${active === name ? "nav-active" : ""}`} onClick={() => {setActive(name);setMenuOpen(false);}}><Icon size={17}/><span>{name}</span></Link>)}</nav>
      <div className="sidebar-bottom"><Link className="sidebar-note" href="/contributions"><span className="note-icon"><Sparkles size={15}/></span><div><strong>A little more history?</strong><span>Help fill in the gaps.</span></div><ArrowRight size={15}/></Link><Link className="nav-item settings" href="/settings"><Settings2 size={17}/><span>Settings</span></Link><div className="profile"><div className="user-avatar">J</div><div className="profile-copy"><strong>Guest viewer</strong><span>Not signed in</span></div></div></div>
    </aside>
    {menuOpen && <button className="mobile-scrim" onClick={() => setMenuOpen(false)} aria-label="Close menu"/>}
    <section className="main-column" id="home">
      <header className="topbar"><button className="mobile-menu" aria-label="Open menu" onClick={() => setMenuOpen(true)}><Menu size={20}/></button><div className="breadcrumbs"><span>Communities</span><span className="crumb-slash">/</span><strong>Explore</strong></div><div className="top-actions"><Link href="/search" className="help-button" aria-label="Search stories"><Search size={17}/></Link><Link href="/dashboard" className="top-avatar" aria-label="Creator dashboard">J</Link></div></header>
      <div className="content">
        <div className="eyebrow"><span className="eyebrow-line"/> A HOME FOR EVERY COMMUNITY</div>
        <div className="hero-row"><div><h1>Every streamer<br/>has a <span>story.</span></h1><p className="hero-subtitle">The moments, memories, and little bits of lore<br className="desktop-break"/> that make a community yours.</p></div><div className="hero-side-note"><span className="side-note-dot"/><span>COMMUNITY HISTORY<br/><b>IN ITS OWN WORDS</b></span></div></div>
        <div className="hero-actions"><Link className="primary-button" href="/explore">Explore wikis <ArrowRight size={16}/></Link><Link className="text-button" href="/dashboard"><Twitch size={16}/> Creator dashboard</Link><span className="demo-label"><i/> SAMPLE COMMUNITY</span></div>

        <div className="section-heading featured-heading" id="featured"><div><span className="section-kicker">PICK UP WHERE CHAT LEFT OFF</span><h2>A community, remembered.</h2></div><Link className="quiet-link" href="/explore">Browse all wikis <ArrowRight size={14}/></Link></div>
        <article className="community-card">
          <div className="cover-art"><div className="cover-orbit orbit-one"/><div className="cover-orbit orbit-two"/><div className="cover-block block-one"/><div className="cover-block block-two"/><div className="cover-block block-three"/><div className="cover-cross">✳</div><span className="cover-caption">A WORLD IN PROGRESS</span><span className="sample-stamp">SAMPLE</span></div>
          <div className="community-info"><div className="community-overline"><span className="live-dot"/> COMMUNITY WIKI <span className="separator">·</span> DEMO CONTENT</div><div className="streamer-row"><div className="streamer-avatar">m<span>✦</span></div><div><h3>mossybytes</h3><span className="twitch-handle">Sample community</span></div><button className={`save-button ${saved ? "is-saved" : ""}`} onClick={() => {const next=!saved;setSaved(next);localStorage.setItem("afterlife:saved-wiki",String(next));}} aria-label={saved ? "Remove saved wiki" : "Save wiki"}>{saved ? <Check size={16}/> : <Bookmark size={16}/>}</button></div><p className="community-bio">Cozy games, questionable builds, and a chat that remembers absolutely everything.</p><div className="stat-line"><span><b>12</b> moments</span><i/><span><b>12</b> stories</span><i/><span><b>3</b> video records</span></div><div className="topic-list"><span className="topic">Minecraft</span><span className="topic">Community builds</span><span className="topic">&quot;The Underneath&quot;</span></div><button className="open-wiki" onClick={() => window.location.assign("/streamer/mossybytes")}>Step into the wiki <ArrowRight size={15}/></button></div>
        </article>

        <div className="section-heading moments-heading"><div><span className="section-kicker">LITTLE MOMENTS, BIG STORIES</span><h2>Recently remembered</h2></div><span className="sample-badge"><span className="sample-dot"/> Sample entries</span></div>
        <div className="moment-grid">{filtered.map((moment, index) => <article className="moment-card" key={moment.title}><button className="moment-image" style={{"--scene":moment.image} as React.CSSProperties} aria-label={`Open ${moment.title}`} onClick={() => window.location.assign(`/wiki/${moment.slug}`)}><span className={`scene-shape shape-${index+1}`}/><span className="play-button"><ArrowDownRight size={16}/></span><span className="timestamp">{moment.time}</span><span className="moment-image-caption">AFTERLIFE <span>·</span> SAMPLE</span></button><div className="moment-meta"><span>{moment.tag}</span><span>{moment.date}</span></div><h3>{moment.title}</h3><p className="stream-title">{moment.stream}</p><button className="moment-link" onClick={() => window.location.assign(`/wiki/${moment.slug}`)}>Explore this moment <ArrowRight size={13}/></button></article>)}</div>
        {filtered.length===0 && <div className="empty-search"><Search size={20}/><strong>No sample moments found</strong><span>Try “Minecraft”, “village”, or “chat”.</span></div>}

        <div className="section-heading lore-heading"><div><span className="section-kicker">A WIKI WITH VIDEO AT ITS HEART</span><h2>Stories worth keeping.</h2></div><Link className="quiet-link" href="/search">Explore the history <ArrowRight size={14}/></Link></div>
        <div className="lore-grid">{articles.map((article,i)=><button className="lore-card" key={article.title} onClick={() => window.location.assign(`/wiki/${article.slug}`)}><div className="lore-top"><span className="lore-icon">{i===0?<Users size={16}/>:i===1?<MessageSquareText size={16}/>:<Sparkles size={16}/>}</span><span className="lore-kind">{article.kind}</span><ArrowRight size={15} className="lore-arrow"/></div><h3>{article.title}</h3><p>{article.text}</p><span className="lore-count"><Film size={13}/>{article.count}</span></button>)}</div>

        <section className="search-banner"><div className="search-banner-copy"><span className="section-kicker">THE GOOD STUFF IS IN THERE SOMEWHERE</span><h2>Remember a moment?</h2><p>Ask a question. Follow a timestamp. Find the story.</p></div><form className="search-form" action="/search"><Search size={17}/><input name="q" aria-label="Search sample community" placeholder="Try ‘When did the village get its name?’" value={query} onChange={e=>setQuery(e.target.value)}/><button className="search-submit" type="submit"><ArrowRight size={17}/></button></form></section>

        <section className="how-section"><div className="how-title"><span className="section-kicker">HOW AFTERLIFE WORKS</span><h2>Streams fade.<br/>Stories stay.</h2><p>A searchable memory for the moments that make a community feel like home.</p></div><div className="how-steps"><div className="how-step"><span>01</span><div><h3>Find the moment</h3><p>Search a community’s stories, jokes, and history in plain language.</p></div></div><div className="how-step"><span>02</span><div><h3>See where it happened</h3><p>Every story points back to a timestamp in the original stream.</p></div></div><div className="how-step"><span>03</span><div><h3>Keep it together</h3><p>Community context connects little moments into a bigger story.</p></div></div></div></section>
        <footer><a className="footer-brand" href="#home">afterlife<span>.</span></a><span>A living memory for the communities we love.</span><span className="footer-status"><i/> FOUNDATION DEMO</span></footer>
      </div>
    </section>
  </main>;
}
