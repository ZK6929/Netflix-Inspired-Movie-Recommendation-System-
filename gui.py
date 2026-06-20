# gui.py  –  Modern Netflix-style web GUI
# Replaces tkinter with a browser-served interface.
# All recommendation logic is unchanged; only the presentation layer is new.
# Run:  python gui.py   then open  http://localhost:5000

import json, threading, webbrowser, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── load recommendation modules (same as original) ──────────────────────────
from load_data_zun import load_data
from movie_info_zainab import load_movie_info, format_movie
from weighted_score_common import get_trending
from similarity_engine_common import get_similar_user_recommendations
from item_item_sidrah import get_item_item_recommendations
from user_profiles_zainab import (
    load_actor_movie_matrix, get_continue_watching,
    update_watch_progress, get_genre_recommendations,
    get_actor_recommendations, is_new_user,
    get_seeded_genre_recommendations
)
from recommender_sidrah import get_hybrid_recommendations
from sparse_matrix_zun import insert_sparmat, create_sparmat

# ── global data ──────────────────────────────────────────────────────────────
ratings, movie_genre, progress, title_map, genres_map = load_data(
    'u.data', 'u.item', progress_filepath='watch_progress.csv')
movie_info   = load_movie_info('u.item')
actor_movie, actor_names = load_actor_movie_matrix('actors.csv')

current_user   = None
user_genre_seed = {}

ALL_GENRES = [
    'Action','Adventure','Animation',"Children's",'Comedy',
    'Crime','Documentary','Drama','Fantasy','Film-Noir',
    'Horror','Musical','Mystery','Romance','Sci-Fi',
    'Thriller','War','Western'
]

# ── helpers ──────────────────────────────────────────────────────────────────
def get_users():
    return list(ratings.keys())[:10]

def api_trending():
    return get_trending(ratings, top_n=15)

def api_continue():
    return get_continue_watching(current_user, progress, movie_info) or []

def api_genre():
    if is_new_user(current_user, ratings):
        seed = user_genre_seed.get(current_user)
        if seed:
            return get_seeded_genre_recommendations(current_user, seed, movie_genre, ratings, movie_info)
        return []
    return get_genre_recommendations(current_user, ratings, movie_genre, movie_info)

def api_item_item():
    return get_item_item_recommendations(current_user, ratings, genres_map)

def api_user_user():
    return get_similar_user_recommendations(current_user, ratings, genres_map, top_n=10)

def api_actor(actor_ids):
    valid = [a for a in actor_ids if a in actor_names]
    if not valid:
        return []
    return get_actor_recommendations(current_user, valid, actor_movie, ratings, movie_info)

def api_hybrid():
    return get_hybrid_recommendations(current_user, ratings, movie_genre, genres_map, top_n=5)

def api_rate(mid, rating):
    title = format_movie(mid, movie_info)
    if title.startswith("Movie #"):
        return False, "Movie not found"
    insert_sparmat(ratings, current_user, mid, float(rating))
    update_watch_progress(current_user, mid, 100, progress)
    return True, title

def api_onboard(chosen_genres):
    seed = create_sparmat()
    for g in chosen_genres:
        insert_sparmat(seed, current_user, g, 1.0)
    user_genre_seed[current_user] = seed
    return get_trending(ratings, top_n=10)

def movie_list_to_json(lst, mode="score"):
    """Convert [(id, val), ...] to JSON-safe dicts."""
    out = []
    if mode == "progress":
        for label, pct in lst:
            out.append({"title": label, "pct": int(pct)})
    else:
        for mid, score in lst:
            out.append({"id": mid, "title": format_movie(mid, movie_info),
                        "score": round(float(score), 2) if score is not None else None})
    return out

# ── HTML template ─────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Cinemax — Movie Recommendations</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet"/>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --red:#E50914;--red2:#ff1f2c;--bg:#080808;--bg2:#111;--bg3:#1a1a1a;
  --bg4:#222;--txt:#f0f0f0;--muted:#888;--border:#2a2a2a;
  --card-h:88px;--nav-w:220px;
}
html,body{height:100%;background:var(--bg);color:var(--txt);font-family:'DM Sans',sans-serif;overflow:hidden}
/* ── layout ── */
#app{display:flex;height:100vh}
#sidebar{
  width:var(--nav-w);min-width:var(--nav-w);background:linear-gradient(180deg,#0d0d0d 0%,#080808 100%);
  border-right:1px solid var(--border);display:flex;flex-direction:column;z-index:10;
}
#main{flex:1;display:flex;flex-direction:column;overflow:hidden}
/* ── sidebar ── */
.logo{padding:28px 24px 20px;letter-spacing:.12em;font-family:'Bebas Neue',sans-serif;
  font-size:26px;color:var(--red);border-bottom:1px solid var(--border)}
.logo span{color:var(--txt);font-size:14px;display:block;font-family:'DM Sans',sans-serif;
  letter-spacing:.04em;margin-top:2px;font-weight:300}
.nav-section{padding:18px 0 8px 24px;font-size:10px;letter-spacing:.14em;color:var(--muted);text-transform:uppercase}
.nav-btn{
  display:flex;align-items:center;gap:10px;padding:11px 24px;
  cursor:pointer;font-size:13.5px;color:#aaa;transition:all .18s;border:none;
  background:none;width:100%;text-align:left;border-left:3px solid transparent;
}
.nav-btn:hover{color:var(--txt);background:rgba(255,255,255,.04)}
.nav-btn.active{color:var(--txt);border-left-color:var(--red);background:rgba(229,9,20,.08)}
.nav-btn .icon{font-size:16px;width:20px;text-align:center}
.nav-spacer{flex:1}
#user-badge{
  margin:16px;padding:12px 14px;background:var(--bg3);border-radius:10px;
  border:1px solid var(--border);display:flex;align-items:center;gap:10px
}
.avatar{width:34px;height:34px;border-radius:50%;background:var(--red);display:flex;
  align-items:center;justify-content:center;font-weight:500;font-size:13px;flex-shrink:0}
.user-name{font-size:13px;font-weight:500}
.user-sub{font-size:11px;color:var(--muted)}
/* ── topbar ── */
#topbar{
  height:58px;min-height:58px;background:rgba(8,8,8,.95);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--border);display:flex;align-items:center;
  padding:0 28px;gap:16px;z-index:5
}
#page-title{font-family:'Bebas Neue',sans-serif;font-size:22px;letter-spacing:.06em;color:var(--txt)}
.spacer{flex:1}
#search-wrap{position:relative}
#search-input{
  background:var(--bg3);border:1px solid var(--border);border-radius:8px;
  color:var(--txt);font-family:'DM Sans',sans-serif;font-size:13px;
  padding:7px 12px 7px 34px;width:220px;outline:none;transition:border .2s
}
#search-input:focus{border-color:#444}
#search-input::placeholder{color:var(--muted)}
.search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:14px;pointer-events:none}
/* ── content ── */
#content{flex:1;overflow-y:auto;padding:28px 32px 40px;scroll-behavior:smooth}
#content::-webkit-scrollbar{width:6px}
#content::-webkit-scrollbar-track{background:transparent}
#content::-webkit-scrollbar-thumb{background:#2a2a2a;border-radius:3px}
/* ── login overlay ── */
#login-overlay{
  position:fixed;inset:0;background:radial-gradient(ellipse at 50% 0%,#1a0000 0%,#080808 60%);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  z-index:100;gap:0
}
.login-logo{font-family:'Bebas Neue',sans-serif;font-size:56px;color:var(--red);
  letter-spacing:.1em;margin-bottom:6px}
.login-sub{font-size:14px;color:var(--muted);margin-bottom:48px;font-weight:300}
.login-heading{font-size:28px;font-weight:300;margin-bottom:32px;letter-spacing:.02em}
.profiles-row{display:flex;gap:20px;flex-wrap:wrap;justify-content:center;margin-bottom:40px}
.profile-btn{
  width:100px;height:100px;border-radius:12px;background:var(--bg3);border:2px solid var(--border);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;
  cursor:pointer;transition:all .2s;font-size:12px;color:#bbb
}
.profile-btn:hover{border-color:var(--red);transform:scale(1.04);background:var(--bg4)}
.profile-btn .av{width:44px;height:44px;border-radius:50%;background:var(--red);display:flex;
  align-items:center;justify-content:center;font-size:16px;font-weight:500}
.login-divider{color:var(--muted);font-size:12px;margin:0 0 16px}
.login-row{display:flex;gap:10px;align-items:center}
.login-input{
  background:var(--bg3);border:1px solid var(--border);border-radius:8px;
  color:var(--txt);font-family:'DM Sans',sans-serif;font-size:15px;
  padding:10px 16px;width:200px;outline:none;text-align:center
}
.login-input:focus{border-color:var(--red)}
.btn-red{
  background:var(--red);color:#fff;border:none;border-radius:8px;
  padding:10px 22px;font-size:14px;font-weight:500;cursor:pointer;font-family:'DM Sans',sans-serif;
  transition:background .18s
}
.btn-red:hover{background:var(--red2)}
/* ── cards ── */
.section-header{display:flex;align-items:baseline;gap:14px;margin-bottom:18px}
.section-title{font-family:'Bebas Neue',sans-serif;font-size:28px;letter-spacing:.05em}
.section-count{font-size:12px;color:var(--muted)}
.cards-grid{display:flex;flex-direction:column;gap:10px}
.movie-card{
  background:var(--bg2);border:1px solid var(--border);border-radius:12px;
  display:flex;align-items:center;gap:16px;padding:0 20px;height:var(--card-h);
  transition:all .2s;position:relative;overflow:hidden;cursor:default
}
.movie-card::before{
  content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:transparent;transition:.2s
}
.movie-card:hover{background:var(--bg3);border-color:#333;transform:translateX(3px)}
.movie-card:hover::before{background:var(--red)}
.rank-num{font-family:'Bebas Neue',sans-serif;font-size:36px;color:var(--border);
  width:36px;text-align:right;flex-shrink:0;letter-spacing:-.02em}
.thumb{width:52px;height:68px;border-radius:6px;background:var(--bg4);
  display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;
  border:1px solid var(--border)}
.card-info{flex:1;min-width:0}
.card-title{font-size:15px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card-meta{font-size:12px;color:var(--muted);margin-top:3px}
.score-pill{
  background:rgba(229,9,20,.12);border:1px solid rgba(229,9,20,.3);
  color:#ff6b6b;border-radius:20px;padding:4px 12px;font-size:12px;font-weight:500;
  flex-shrink:0
}
/* progress bar card */
.prog-bar-wrap{flex:1;min-width:0}
.prog-label{font-size:14px;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prog-track{height:4px;background:var(--bg4);border-radius:2px;overflow:hidden}
.prog-fill{height:100%;background:var(--red);border-radius:2px;transition:width .6s ease}
.prog-pct{font-size:11px;color:var(--muted);margin-top:4px}
/* empty / error state */
.empty-state{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:80px 0;color:var(--muted);gap:12px
}
.empty-icon{font-size:48px;opacity:.3}
.empty-text{font-size:15px}
/* loading */
.loading{display:flex;align-items:center;gap:8px;color:var(--muted);padding:60px 0}
.spinner{width:18px;height:18px;border:2px solid var(--border);border-top-color:var(--red);
  border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
/* modal */
.modal-bg{
  position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:200;
  display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)
}
.modal{
  background:var(--bg2);border:1px solid var(--border);border-radius:16px;
  padding:32px 36px;width:420px;max-width:95vw
}
.modal-title{font-family:'Bebas Neue',sans-serif;font-size:24px;letter-spacing:.05em;margin-bottom:20px}
.modal-input{
  background:var(--bg3);border:1px solid var(--border);border-radius:8px;
  color:var(--txt);font-family:'DM Sans',sans-serif;font-size:14px;
  padding:10px 14px;width:100%;outline:none;margin-bottom:14px
}
.modal-input:focus{border-color:#555}
.modal-row{display:flex;gap:10px;justify-content:flex-end;margin-top:8px}
.btn-ghost{
  background:transparent;color:#aaa;border:1px solid var(--border);border-radius:8px;
  padding:9px 18px;font-size:13px;cursor:pointer;font-family:'DM Sans',sans-serif
}
.btn-ghost:hover{border-color:#555;color:var(--txt)}
/* genre onboarding grid */
.genre-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:20px}
.genre-chip{
  padding:10px 8px;border:1px solid var(--border);border-radius:10px;text-align:center;
  cursor:pointer;font-size:13px;transition:all .18s;background:var(--bg3);color:#bbb
}
.genre-chip:hover{border-color:#555;color:var(--txt)}
.genre-chip.selected{border-color:var(--red);background:rgba(229,9,20,.12);color:#ff8080}
/* actor list */
.actor-list{max-height:220px;overflow-y:auto;background:var(--bg3);border-radius:8px;
  border:1px solid var(--border);margin-bottom:14px;padding:4px 0}
.actor-item{
  display:flex;align-items:center;gap:10px;padding:8px 14px;cursor:pointer;
  font-size:13px;transition:background .15s
}
.actor-item:hover{background:var(--bg4)}
.actor-item input[type=checkbox]{accent-color:var(--red)}
/* toast */
#toast{
  position:fixed;bottom:28px;right:28px;background:var(--bg3);border:1px solid var(--border);
  border-radius:10px;padding:12px 20px;font-size:13px;z-index:300;
  opacity:0;transform:translateY(10px);transition:all .3s;pointer-events:none;max-width:300px
}
#toast.show{opacity:1;transform:translateY(0)}
</style>
</head>
<body>

<!-- Login overlay -->
<div id="login-overlay">
  <div class="login-logo">CINEMAX</div>
  <div class="login-sub">Powered by intelligent recommendations</div>
  <div class="login-heading">Who's watching?</div>
  <div class="profiles-row" id="profiles-row"></div>
  <div class="login-divider">— or enter a user ID —</div>
  <div class="login-row">
    <input class="login-input" id="login-input" placeholder="User ID" type="text"/>
    <button class="btn-red" onclick="doLogin(document.getElementById('login-input').value)">Enter</button>
  </div>
</div>

<!-- Main app -->
<div id="app">
  <!-- Sidebar -->
  <nav id="sidebar">
    <div class="logo">CINEMAX<span>Movie Recommendations</span></div>
    <div class="nav-section">Discover</div>
    <button class="nav-btn" data-view="trending"  onclick="navigate('trending')">  <span class="icon">🔥</span> Trending Now</button>
    <button class="nav-btn" data-view="continue"  onclick="navigate('continue')">  <span class="icon">▶</span>  Continue Watching</button>
    <button class="nav-btn" data-view="genre"     onclick="navigate('genre')">     <span class="icon">🎭</span> Genre Picks</button>
    <div class="nav-section">Smart Picks</div>
    <button class="nav-btn" data-view="user-user" onclick="navigate('user-user')"> <span class="icon">👥</span> Similar Users</button>
    <button class="nav-btn" data-view="item-item" onclick="navigate('item-item')"> <span class="icon">🎞</span> Because You Watched</button>
    <button class="nav-btn" data-view="actor"     onclick="navigate('actor')">     <span class="icon">⭐</span> Actor Picks</button>
    <button class="nav-btn" data-view="hybrid"    onclick="navigate('hybrid')">    <span class="icon">🧬</span> Hybrid Engine</button>
    <div class="nav-section">My Account</div>
    <button class="nav-btn" data-view="rate"      onclick="openRate()">            <span class="icon">✍</span>  Rate a Movie</button>
    <button class="nav-btn" data-view="setup"     onclick="openOnboard()">         <span class="icon">🆕</span> New User Setup</button>
    <div class="nav-spacer"></div>
    <div id="user-badge">
      <div class="avatar" id="avatar-initials">?</div>
      <div><div class="user-name" id="badge-name">Not logged in</div><div class="user-sub" id="badge-sub">—</div></div>
    </div>
    <button class="nav-btn" style="margin-bottom:10px;color:var(--muted)" onclick="doLogout()">
      <span class="icon">↩</span> Logout
    </button>
  </nav>

  <!-- Main -->
  <div id="main">
    <div id="topbar">
      <div id="page-title">Trending Now</div>
      <div class="spacer"></div>
      <div id="search-wrap">
        <span class="search-icon">🔍</span>
        <input id="search-input" placeholder="Filter results…" oninput="filterCards(this.value)"/>
      </div>
    </div>
    <div id="content">
      <div class="loading"><div class="spinner"></div> Loading…</div>
    </div>
  </div>
</div>

<!-- Modals (injected by JS) -->
<div id="modal-container"></div>
<div id="toast"></div>

<script>
const TITLES = {
  trending:'Trending Now', continue:'Continue Watching', genre:'Genre Picks',
  'user-user':'People Like You', 'item-item':'Because You Watched',
  actor:'Actor Picks', hybrid:'Hybrid Engine'
};

let currentView = '';
let allCards = [];  // for client-side filtering

// ── boot: load users ─────────────────────────────────────────────────────────
fetch('/api/users').then(r=>r.json()).then(users=>{
  const row = document.getElementById('profiles-row');
  users.forEach(uid=>{
    const btn = document.createElement('button');
    btn.className = 'profile-btn';
    btn.innerHTML = `<div class="av">${String(uid).slice(-2)}</div><div>User ${uid}</div>`;
    btn.onclick = ()=>doLogin(uid);
    row.appendChild(btn);
  });
});

// ── login/logout ─────────────────────────────────────────────────────────────
function doLogin(uid){
  uid = String(uid).trim();
  if(!uid) return;
  fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({uid})})
    .then(r=>r.json()).then(d=>{
      if(d.ok){
        document.getElementById('login-overlay').style.display='none';
        document.getElementById('badge-name').textContent = `User ${uid}`;
        document.getElementById('badge-sub').textContent  = d.new_user ? 'New user' : 'Returning viewer';
        document.getElementById('avatar-initials').textContent = String(uid).slice(-2);
        navigate('trending');
      }
    });
}
function doLogout(){
  fetch('/api/logout',{method:'POST'}).then(()=>{
    document.getElementById('login-overlay').style.display='flex';
    document.getElementById('content').innerHTML='<div class="loading"><div class="spinner"></div> Loading…</div>';
  });
}

// ── navigation ────────────────────────────────────────────────────────────────
function navigate(view){
  currentView = view;
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.toggle('active', b.dataset.view===view));
  document.getElementById('page-title').textContent = TITLES[view] || view;
  document.getElementById('search-input').value = '';
  setContent('<div class="loading"><div class="spinner"></div> Loading…</div>');
  fetch(`/api/${view}`).then(r=>r.json()).then(data=>{
    if(data.error){ setContent(emptyState(data.error)); return; }
    if(view==='continue') renderContinue(data);
    else renderMovies(data.movies || []);
  });
}

// ── renderers ─────────────────────────────────────────────────────────────────
function renderMovies(movies){
  if(!movies.length){ setContent(emptyState('Nothing to show here yet.')); return; }
  allCards = movies;
  const wrap = document.createElement('div');
  wrap.innerHTML = `<div class="section-header">
    <span class="section-title">${TITLES[currentView]||''}</span>
    <span class="section-count">${movies.length} titles</span></div>`;
  const grid = document.createElement('div'); grid.className='cards-grid'; grid.id='cards-grid';
  movies.forEach((m,i)=>{
    grid.appendChild(buildCard(m,i+1));
  });
  wrap.appendChild(grid);
  setContent(wrap.innerHTML);
}

function buildCard(m, rank){
  const d = document.createElement('div');
  d.className='movie-card'; d.dataset.title=(m.title||'').toLowerCase();
  const score = m.score!=null ? `<div class="score-pill">★ ${m.score.toFixed(2)}</div>` : '';
  const year = extractYear(m.title);
  const clean = cleanTitle(m.title);
  d.innerHTML = `
    <div class="rank-num">${rank}</div>
    <div class="thumb">🎬</div>
    <div class="card-info">
      <div class="card-title">${clean}</div>
      <div class="card-meta">${year ? year : '—'} &nbsp;·&nbsp; Movie ID: ${m.id}</div>
    </div>
    ${score}`;
  return d;
}

function renderContinue(data){
  const items = data.items || [];
  if(!items.length){ setContent(emptyState('No movies in progress.')); return; }
  let html = `<div class="section-header"><span class="section-title">Continue Watching</span>
    <span class="section-count">${items.length} in progress</span></div><div class="cards-grid">`;
  items.forEach(it=>{
    html += `<div class="movie-card">
      <div class="thumb">▶</div>
      <div class="prog-bar-wrap">
        <div class="prog-label">${it.title}</div>
        <div class="prog-track"><div class="prog-fill" style="width:${it.pct}%"></div></div>
        <div class="prog-pct">${it.pct}% watched</div>
      </div></div>`;
  });
  html += '</div>';
  setContent(html);
}

// ── search / filter ───────────────────────────────────────────────────────────
function filterCards(q){
  q = q.toLowerCase();
  document.querySelectorAll('.movie-card[data-title]').forEach(c=>{
    c.style.display = c.dataset.title.includes(q) ? '' : 'none';
  });
}

// ── actor modal ───────────────────────────────────────────────────────────────
function openRate(){
  showModal(`
    <div class="modal-title">Rate a Movie</div>
    <input class="modal-input" id="m-mid" placeholder="Movie ID (e.g. 42)"/>
    <input class="modal-input" id="m-rating" type="number" min="1" max="5" step="0.5" placeholder="Rating 1 – 5"/>
    <div class="modal-row">
      <button class="btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn-red" onclick="submitRate()">Submit Rating</button>
    </div>`);
}
function submitRate(){
  const mid = document.getElementById('m-mid').value.trim();
  const rat = document.getElementById('m-rating').value.trim();
  if(!mid||!rat) return;
  fetch('/api/rate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mid,rating:rat})})
    .then(r=>r.json()).then(d=>{
      closeModal();
      if(d.ok) toast(`Rated "${d.title}": ${parseFloat(rat).toFixed(1)} ★`);
      else toast(d.error, true);
    });
}

function openActor(){
  fetch('/api/actors').then(r=>r.json()).then(actors=>{
    let items = actors.map(a=>`
      <label class="actor-item">
        <input type="checkbox" value="${a.id}"/>
        <span>${a.name}</span>
      </label>`).join('');
    showModal(`
      <div class="modal-title">Actor Picks</div>
      <div class="actor-list">${items}</div>
      <div class="modal-row">
        <button class="btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn-red" onclick="submitActor()">Get Picks</button>
      </div>`);
  });
}
document.querySelector('[data-view=actor]').onclick = openActor;

function submitActor(){
  const ids = [...document.querySelectorAll('.actor-list input:checked')].map(i=>i.value);
  if(!ids.length){ toast('Select at least one actor', true); return; }
  closeModal();
  currentView = 'actor';
  document.getElementById('page-title').textContent = 'Actor Picks';
  setContent('<div class="loading"><div class="spinner"></div> Loading…</div>');
  fetch('/api/actor', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})})
    .then(r=>r.json()).then(d=>renderMovies(d.movies||[]));
}

// ── onboarding ────────────────────────────────────────────────────────────────
const ALL_GENRES = ["Action","Adventure","Animation","Children's","Comedy","Crime",
  "Documentary","Drama","Fantasy","Film-Noir","Horror","Musical","Mystery","Romance",
  "Sci-Fi","Thriller","War","Western"];
let chosenGenres = [];

function openOnboard(){
  chosenGenres = [];
  const chips = ALL_GENRES.map(g=>`<div class="genre-chip" onclick="toggleGenre(this,'${g}')">${g}</div>`).join('');
  showModal(`
    <div class="modal-title">New User Setup</div>
    <p style="font-size:13px;color:var(--muted);margin-bottom:16px">Pick 3 genres you love:</p>
    <div class="genre-grid">${chips}</div>
    <div id="genre-count" style="font-size:12px;color:var(--muted);margin-bottom:14px">0 / 3 selected</div>
    <div class="modal-row">
      <button class="btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn-red" onclick="submitOnboard()">Continue</button>
    </div>`);
}
function toggleGenre(el, g){
  if(el.classList.contains('selected')){
    el.classList.remove('selected'); chosenGenres=chosenGenres.filter(x=>x!==g);
  } else {
    if(chosenGenres.length>=3){ toast('Max 3 genres',true); return; }
    el.classList.add('selected'); chosenGenres.push(g);
  }
  document.getElementById('genre-count').textContent=`${chosenGenres.length} / 3 selected`;
}
function submitOnboard(){
  if(chosenGenres.length<1){ toast('Pick at least 1 genre',true); return; }
  closeModal();
  fetch('/api/onboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({genres:chosenGenres})})
    .then(r=>r.json()).then(d=>{
      currentView='trending';
      document.getElementById('page-title').textContent=`Welcome! (${chosenGenres.join(', ')})`;
      renderMovies(d.movies||[]);
      toast('Setup complete! Enjoy your picks.');
    });
}

// ── modal helpers ─────────────────────────────────────────────────────────────
function showModal(html){
  document.getElementById('modal-container').innerHTML=`<div class="modal-bg" onclick="if(event.target===this)closeModal()"><div class="modal">${html}</div></div>`;
}
function closeModal(){ document.getElementById('modal-container').innerHTML=''; }

// ── toast ─────────────────────────────────────────────────────────────────────
let toastTimer;
function toast(msg, err=false){
  const t=document.getElementById('toast');
  t.textContent=msg; t.style.borderColor=err?'#c0392b':'var(--border)';
  t.classList.add('show'); clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>t.classList.remove('show'),3000);
}

// ── utilities ─────────────────────────────────────────────────────────────────
function setContent(html){ document.getElementById('content').innerHTML = typeof html==='string'?html:html.outerHTML||''; }
function emptyState(msg){ return `<div class="empty-state"><div class="empty-icon">🎬</div><div class="empty-text">${msg}</div></div>`; }
function extractYear(title){ const m=(title||'').match(/\((\d{4})\)/); return m?m[1]:''; }
function cleanTitle(title){ return (title||'').replace(/\s*\(\d{4}\)$/,''); }
</script>
</body>
</html>
"""

# ── HTTP handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass  # silence access log

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global current_user
        path = urlparse(self.path).path

        if path == '/' or path == '/index.html':
            body = HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
            return

        if not current_user and path not in ('/api/users', '/api/login'):
            self.send_json({'error': 'Not logged in'}, 401); return

        if path == '/api/users':
            self.send_json(get_users()); return

        if path == '/api/trending':
            movies = movie_list_to_json(api_trending())
            self.send_json({'movies': movies}); return

        if path == '/api/continue':
            items = movie_list_to_json(api_continue(), mode='progress')
            self.send_json({'items': items}); return

        if path == '/api/genre':
            movies = movie_list_to_json(api_genre())
            self.send_json({'movies': movies}); return

        if path == '/api/user-user':
            movies = movie_list_to_json(api_user_user())
            self.send_json({'movies': movies}); return

        if path == '/api/item-item':
            movies = movie_list_to_json(api_item_item())
            self.send_json({'movies': movies}); return

        if path == '/api/hybrid':
            movies = movie_list_to_json(api_hybrid())
            self.send_json({'movies': movies}); return

        if path == '/api/actors':
            actors = [{'id': aid, 'name': name} for aid, name in
                      sorted(actor_names.items(), key=lambda x: int(x[0]))[:40]]
            self.send_json(actors); return

        self.send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        global current_user
        length = int(self.headers.get('Content-Length', 0))
        body   = json.loads(self.rfile.read(length) or b'{}')
        path   = urlparse(self.path).path

        if path == '/api/login':
            current_user = str(body.get('uid', '')).strip()
            new = is_new_user(current_user, ratings) if current_user else True
            self.send_json({'ok': bool(current_user), 'new_user': new}); return

        if path == '/api/logout':
            current_user = None
            self.send_json({'ok': True}); return

        if not current_user:
            self.send_json({'error': 'Not logged in'}, 401); return

        if path == '/api/rate':
            ok, title = api_rate(str(body.get('mid','')), body.get('rating', 3))
            self.send_json({'ok': ok, 'title': title, 'error': title if not ok else ''}); return

        if path == '/api/actor':
            ids = [str(i) for i in body.get('ids', [])]
            movies = movie_list_to_json(api_actor(ids))
            self.send_json({'movies': movies}); return

        if path == '/api/onboard':
            genres = body.get('genres', [])
            movies = movie_list_to_json(api_onboard(genres))
            self.send_json({'movies': movies}); return

        self.send_json({'error': 'Not found'}, 404)

# ── entry point ───────────────────────────────────────────────────────────────
def run():
    port = 5000
    server = HTTPServer(('localhost', port), Handler)
    print(f"  Cinemax running →  http://localhost:{port}")
    print("  Press Ctrl+C to quit.\n")
    threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{port}')).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")

if __name__ == '__main__':
    run()
