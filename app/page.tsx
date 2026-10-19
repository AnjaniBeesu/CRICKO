"use client";

import { useEffect, useState } from "react";
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

type Batter = { player_id: string; player: string; runs: number; balls_faced: number; matches: number; strike_rate: number | null };
type Leaderboard = { scope: string; definition: string; count: number; results: Batter[] };
type QueryAnswer = { status: string; answer: string; scope?: string };

export default function Home(){
  const [query,setQuery]=useState("");
  const [leaderboard,setLeaderboard]=useState<Leaderboard|null>(null);
  const [leaderboardError,setLeaderboardError]=useState("");
  const [leaderboardLoading,setLeaderboardLoading]=useState(true);

  useEffect(()=>{
    let active=true;
    fetch("/api/stats/top-batters?limit=5&min_balls=30",{cache:"no-store"})
      .then(async response=>{
        const payload=await response.json();
        if(!response.ok) throw new Error(payload.detail||payload.error||"Statistics service unavailable");
        return payload as Leaderboard;
      })
      .then(payload=>{if(active)setLeaderboard(payload);})
      .catch(error=>{if(active)setLeaderboardError(error instanceof Error?error.message:"Unable to load statistics");})
      .finally(()=>{if(active)setLeaderboardLoading(false);});
    return ()=>{active=false;};
  },[]);

  const [asked,setAsked]=useState("");
  const [answer,setAnswer]=useState<QueryAnswer|null>(null);
  const [answerLoading,setAnswerLoading]=useState(false);
  const [answerError,setAnswerError]=useState("");
  const ask=async(q=query)=>{if(!q.trim()||answerLoading)return;setQuery(q);setAsked(q);setAnswer(null);setAnswerError("");setAnswerLoading(true);try{const response=await fetch("/api/query",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question:q}),cache:"no-store"});const payload=await response.json();if(!response.ok)throw new Error(payload.detail||"Cricko could not process that question.");setAnswer(payload as QueryAnswer);}catch(error){setAnswerError(error instanceof Error?error.message:"Unable to reach the CRICKO API.");}finally{setAnswerLoading(false);}};
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
        <p>{answerLoading?"Querying the CRICKO database…":answerError?answerError:answer?.answer||"No answer returned."}</p>{answer?.scope&&<p className="leaderboard-scope">Dataset: {answer.scope}</p>}</div>
      </div>}
    </section>

    <section className="signal-section" id="insights">
      <div className="section-kicker">01 / LIVE SIGNALS</div>
      <div className="section-title"><h2>The game,<br/><em>in context.</em></h2><p>Not another scoreboard. Cricko turns cricket data into signals you can actually reason about.</p></div>
      <div className="insight-grid">{insights.map(({label,value,meta,icon:Icon})=><article className="insight" key={label}><div className="insight-top"><span>{label}</span><Icon size={17}/></div><h3>{value}</h3><p>{meta}</p></article>)}</div>
      <div className="leaderboard">
        <div className="leaderboard-heading"><div><span className="section-kicker">DATABASE QUERY / 01</span><h3>Most runs.<br/><em>No guesswork.</em></h3></div><span className="query-badge">DETERMINISTIC SQL</span></div>
        <p className="leaderboard-definition">Top batters in the loaded Cricsheet snapshot, ranked by batter-attributed runs with a 30-ball minimum.</p>
        {leaderboardLoading&&<p className="service-message">Querying the CRICKO stats API…</p>}
        {!leaderboardLoading&&leaderboardError&&<p className="service-message service-error">Stats API not connected yet. {leaderboardError}</p>}
        {leaderboard&&<><div className="leaderboard-table-wrap"><table className="leaderboard-table"><thead><tr><th>#</th><th>BATTER</th><th>RUNS</th><th>BALLS</th><th>SR</th><th>MATCHES</th></tr></thead><tbody>{leaderboard.results.map((batter,index)=><tr key={batter.player_id}><td>{String(index+1).padStart(2,"0")}</td><td>{batter.player}</td><td>{batter.runs.toLocaleString("en-IN")}</td><td>{batter.balls_faced.toLocaleString("en-IN")}</td><td>{batter.strike_rate===null?"—":batter.strike_rate.toFixed(2)}</td><td>{batter.matches}</td></tr>)}</tbody></table></div><p className="leaderboard-scope">{leaderboard.scope} {leaderboard.count===0?"No batters meet the current minimum sample size.":""}</p></>}
      </div>
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