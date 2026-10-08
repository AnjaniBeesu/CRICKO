"use client";

import { useState } from "react";
import { ArrowUpRight, BarChart3, ChevronRight, CircleDot, Search, Sparkles, Trophy, Zap } from "lucide-react";

const suggestions=[
  "Compare Bumrah and Starc in World Cup knockout matches",
  "Who is India's best death-over bowler since 2022?",
  "How has Kohli's T20 strike rate changed since 2020?"
];

const insights=[
  {label:"LIVE SIGNAL",value:"India vs Australia",meta:"ODI · 18.4 overs",icon:CircleDot},
  {label:"FORM INDEX",value:"Jasprit Bumrah",meta:"94 / 100 · +8 this month",icon:Zap},
  {label:"NEXT MATCH",value:"India vs England",meta:"Tomorrow · Ahmedabad",icon:Trophy}
];

export default function Home(){
  const [query,setQuery]=useState("");
  const [asked,setAsked]=useState("");
  const ask=(q=query)=>{if(!q.trim())return;setQuery(q);setAsked(q)};
  return <main>
    <nav className="nav">
      <div className="brand"><span className="brand-mark">C</span><span>cricko</span></div>
      <div className="nav-links"><a href="#ask">Ask</a><a href="#insights">Insights</a><a href="#method">How it works</a></div>
      <button className="nav-cta" onClick={()=>document.getElementById("ask")?.scrollIntoView({behavior:"smooth"})}>Explore <ArrowUpRight size={15}/></button>
    </nav>

    <section className="hero" id="ask">
      <div className="eyebrow"><span className="pulse"/>CRICKET INTELLIGENCE, REIMAGINED</div>
      <h1>Ask cricket.<br/><em>Know more.</em></h1>
      <p className="hero-copy">A domain-specific AI that connects live signals, historical statistics and match context — then shows you why the answer is true.</p>

      <div className="search-shell">
        <Search size={20}/>
        <input value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==="Enter"&&ask()} placeholder="Ask anything about cricket…" />
        <button onClick={()=>ask()} aria-label="Ask Cricko"><ArrowUpRight size={20}/></button>
      </div>

      <div className="suggestions">{suggestions.map(s=><button key={s} onClick={()=>ask(s)}>{s}<ChevronRight size={14}/></button>)}</div>

      {asked && <div className="answer-card">
        <div className="answer-head"><span><Sparkles size={15}/> CRICKO ANALYSIS</span><span className="live-tag">EVIDENCE BACKED</span></div>
        <h2>{asked}</h2>
        <p>Cricko would route this question through cricket-aware entity extraction, structured statistics and contextual retrieval. The production pipeline is ready to connect to your data/API keys.</p>
        <div className="answer-grid"><div><b>Retrieval</b><span>Structured + semantic</span></div><div><b>Reasoning</b><span>Statistical + LLM</span></div><div><b>Evidence</b><span>Source-linked</span></div></div>
      </div>}
    </section>

    <section className="signal-section" id="insights">
      <div className="section-kicker">01 / LIVE SIGNALS</div>
      <div className="section-title"><h2>The game,<br/><em>in context.</em></h2><p>Not another scoreboard. Cricko turns cricket data into signals you can actually reason about.</p></div>
      <div className="insight-grid">{insights.map(({label,value,meta,icon:Icon})=><article className="insight" key={label}><div className="insight-top"><span>{label}</span><Icon size={17}/></div><h3>{value}</h3><p>{meta}</p></article>)}</div>
    </section>

    <section className="method" id="method">
      <div className="section-kicker">02 / THE ENGINE</div>
      <div className="method-layout">
        <div><h2>RAG,<br/><em>but cricket-native.</em></h2><p>Cricko does not ask an LLM to guess statistics. It understands cricket entities, retrieves the right evidence, calculates derived metrics and only then writes the answer.</p></div>
        <div className="pipeline">
          {["Natural language query","Cricket entity recognition","SQL + vector retrieval","Statistical reasoning","Evidence-backed answer"].map((x,i)=><div className="pipeline-row" key={x}><span>0{i+1}</span><b>{x}</b><ChevronRight size={16}/></div>)}
        </div>
      </div>
    </section>

    <section className="final-cta">
      <BarChart3 size={22}/><h2>Make the numbers<br/><em>say something.</em></h2><p>Built for analysts, fans and anyone who asks better questions about the game.</p>
      <button onClick={()=>document.getElementById("ask")?.scrollIntoView({behavior:"smooth"})}>Ask Cricko <ArrowUpRight size={17}/></button>
    </section>
    <footer><div className="brand"><span className="brand-mark">C</span><span>cricko</span></div><span>Cricket intelligence engine · 2026</span></footer>
  </main>
}