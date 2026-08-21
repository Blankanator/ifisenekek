const params = new URLSearchParams(location.search);
const songId = params.get('id');
const requestedGroup = params.get('group');
const db = window.SONG_DB;
const root = document.querySelector('#songView');

let currentWidth = 100;
let currentSong = null;
let currentVersions = [];
let currentActive = null;

function esc(s){
  return String(s).replace(/[&<>"']/g,c=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'
  }[c]));
}

function groupNumber(song, gid){
  const entries = song.groups[gid] || [];
  if (!entries.length) return Number.POSITIVE_INFINITY;
  return Math.min(...entries.map(e => Number(e.number)).filter(Number.isFinite));
}

function orderedSongsForGroup(gid){
  return db.songs
    .filter(song => song.groups[gid])
    .slice()
    .sort((a,b) => {
      const numberDiff = groupNumber(a, gid) - groupNumber(b, gid);
      if (numberDiff !== 0) return numberDiff;
      return a.title.localeCompare(b.title, 'hu-HU', {sensitivity:'base'});
    });
}

function init(){
  if (!db || !songId) return fail('Az ének nem található.');

  const song = db.songs.find(s => s.id === songId);
  if (!song) return fail('Az ének nem található.');

  currentSong = song;
  document.title = `${song.title} – Ifis énekek`;

  const versions = [];
  Object.entries(song.groups).forEach(([gid, entries]) => {
    entries.forEach((entry,index)=>versions.push({gid,index,...entry}));
  });

  // Group-version references are always shown in Hungarian ABC order.
  versions.sort((a,b) => {
    const groupDiff = db.groups[a.gid].name.localeCompare(
      db.groups[b.gid].name, 'hu-HU', {sensitivity:'base'}
    );
    if (groupDiff !== 0) return groupDiff;

    const an = Number(a.number);
    const bn = Number(b.number);
    if (Number.isFinite(an) && Number.isFinite(bn) && an !== bn) return an - bn;

    return String(a.section || '').localeCompare(
      String(b.section || ''), 'hu-HU', {sensitivity:'base'}
    );
  });

  currentVersions = versions;
  const active = versions.find(v=>v.gid===requestedGroup) || versions[0];
  currentActive = active;

  render(song, versions, active);
}

function render(song, versions, active){
  const buttons = versions.map(v => {
    const sameGroupCount = versions.filter(x=>x.gid===v.gid).length;
    const label = `${db.groups[v.gid].name} · ${v.number}${sameGroupCount>1 ? ` · ${v.section}` : ''}`;
    const selected = v.gid===active.gid && v.index===active.index;

    return `<button class="version-btn version-${esc(v.gid)}${selected?' active':''}"
      data-gid="${esc(v.gid)}" data-index="${v.index}">${esc(label)}</button>`;
  }).join('');

  root.innerHTML = `
    <header class="song-detail-header">
      <p class="eyebrow">Ének</p>
      <h1>${esc(song.title)}</h1>
      <div class="version-picker">${buttons}</div>
    </header>

    <nav id="songNav" class="song-navigation" aria-label="Előző és következő ének"></nav>

    <section class="song-sheet-search">
      <label class="sheet-search-label" for="sheetSearch">Ének keresése</label>
      <div class="sheet-search-wrap">
        <input id="sheetSearch" class="sheet-search-input" type="search"
          placeholder="Kezdj el gépelni…" autocomplete="off">
        <div id="sheetSearchResults" class="sheet-search-results" hidden></div>
      </div>
    </section>

    <section id="sourceCard" class="source-card sheet-card">
      <div class="source-card-head">
        <div>
          <div id="sourceGroup" class="source-group"></div>
          <div id="sourceMeta" class="source-meta"></div>
        </div>
      </div>

      <div class="sheet-controls">
        <label for="sheetWidth">Kotta szélessége</label>
        <input id="sheetWidth" type="range" min="35" max="150" value="100" step="1">
        <output id="sheetWidthValue" for="sheetWidth">100%</output>
        <div class="zoom-presets" aria-label="Gyors nagyítás">
          <button class="small-button zoom-preset" type="button" data-zoom="50">50%</button>
          <button class="small-button zoom-preset" type="button" data-zoom="100">100%</button>
          <button class="small-button zoom-preset" type="button" data-zoom="150">150%</button>
        </div>
      </div>

      <div id="sheetStage" class="sheet-stage" tabindex="0"
        aria-label="Kotta nézet. Nagyításkor húzással mozgatható."></div>
    </section>`;

  document.querySelectorAll('.version-btn').forEach(btn=>btn.addEventListener('click',()=>{
    const nextActive = versions.find(v =>
      v.gid===btn.dataset.gid && v.index===Number(btn.dataset.index)
    );
    setActive(nextActive);
  }));

  const slider = document.querySelector('#sheetWidth');
  const output = document.querySelector('#sheetWidthValue');
  const stage = document.querySelector('#sheetStage');

  function applyWidth(value){
    const pct = Number(value);
    currentWidth = pct;
    document.documentElement.style.setProperty('--sheet-width', `${pct}%`);
    output.value = `${pct}%`;
    stage.classList.toggle('is-pannable', pct > 100);
    if (pct <= 100) stage.scrollLeft = 0;
  }

  // Always start every song view at 100%.
  slider.value = 100;
  applyWidth(100);

  slider.addEventListener('input', ()=>applyWidth(slider.value));

  document.querySelectorAll('.zoom-preset').forEach(btn => {
    btn.addEventListener('click', () => {
      const value = Number(btn.dataset.zoom);
      slider.value = value;
      applyWidth(value);
    });
  });

  enableDragPan(stage);
  setupSheetSearch();
  updateSource(active);
}

function enableDragPan(stage){
  let dragging = false;
  let startX = 0;
  let startY = 0;
  let startScrollLeft = 0;
  let startScrollTop = 0;

  stage.addEventListener('pointerdown', e=>{
    if (currentWidth <= 100) return;

    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    startScrollLeft = stage.scrollLeft;
    startScrollTop = stage.scrollTop;

    stage.setPointerCapture(e.pointerId);
    stage.classList.add('is-dragging');
    e.preventDefault();
  });

  stage.addEventListener('pointermove', e=>{
    if (!dragging) return;
    stage.scrollLeft = startScrollLeft - (e.clientX - startX);
  });

  function endDrag(e){
    if (!dragging) return;
    dragging = false;
    stage.classList.remove('is-dragging');
    try { stage.releasePointerCapture(e.pointerId); } catch (_) {}
  }

  stage.addEventListener('pointerup', endDrag);
  stage.addEventListener('pointercancel', endDrag);
  stage.addEventListener('lostpointercapture', ()=>{
    dragging = false;
    stage.classList.remove('is-dragging');
  });

    stage.addEventListener('wheel', e => {
    if (Math.abs(e.deltaY) >= Math.abs(e.deltaX) && e.deltaY !== 0) {
      window.scrollBy({top:e.deltaY,left:0,behavior:'auto'});
      e.preventDefault();
    }
  }, {passive:false});
}

function setActive(active){
  currentActive = active;

  document.querySelectorAll('.version-btn').forEach(btn=>{
    btn.classList.toggle(
      'active',
      btn.dataset.gid===active.gid && Number(btn.dataset.index)===active.index
    );
  });

  const url = new URL(location.href);
  url.searchParams.set('group',active.gid);
  history.replaceState(null,'',url);

  updateSource(active);
}

function updateNavigation(active){
  const nav = document.querySelector('#songNav');
  const ordered = orderedSongsForGroup(active.gid);
  const index = ordered.findIndex(song => song.id === currentSong.id);

  const prev = index > 0 ? ordered[index-1] : null;
  const next = index >= 0 && index < ordered.length-1 ? ordered[index+1] : null;

  const prevHtml = prev
    ? `<a class="song-nav-link prev" href="song.html?id=${encodeURIComponent(prev.id)}&group=${encodeURIComponent(active.gid)}">
         <span class="song-nav-direction">← Előző</span>
         <span class="song-nav-title">${esc(groupNumber(prev, active.gid))} · ${esc(prev.title)}</span>
       </a>`
    : `<span class="song-nav-link disabled">
         <span class="song-nav-direction">← Előző</span>
         <span class="song-nav-title">Nincs korábbi ének</span>
       </span>`;

  const nextHtml = next
    ? `<a class="song-nav-link next" href="song.html?id=${encodeURIComponent(next.id)}&group=${encodeURIComponent(active.gid)}">
         <span class="song-nav-direction">Következő →</span>
         <span class="song-nav-title">${esc(groupNumber(next, active.gid))} · ${esc(next.title)}</span>
       </a>`
    : `<span class="song-nav-link disabled next">
         <span class="song-nav-direction">Következő →</span>
         <span class="song-nav-title">Nincs következő ének</span>
       </span>`;

  nav.innerHTML = prevHtml + nextHtml;
}

function updateSource(active){
  const group = db.groups[active.gid];
  const firstPage = Number(active.sourcePage || 1);

  const pages = (Array.isArray(active.sourcePages) && active.sourcePages.length)
    ? active.sourcePages.map(Number)
    : [firstPage];

  const segments = active.imageMissing
    ? []
    : ((Array.isArray(active.sourceSegments) && active.sourceSegments.length)
      ? active.sourceSegments
      : pages.map(page => ({
          image: `sheets/${active.gid}/${String(page).padStart(3,'0')}.jpg`,
          page
        })));

  document.querySelector('#sourceGroup').textContent = group.name;
  document.querySelector('#sourceMeta').textContent =
    `${active.number} · ${active.section}${segments.length>1 ? ` · ${segments.length} rész` : ''}`;

  const sourceCard = document.querySelector('#sourceCard');
  [...sourceCard.classList]
    .filter(cls => cls.startsWith('group-'))
    .forEach(cls => sourceCard.classList.remove(cls));
  sourceCard.classList.add(`group-${active.gid}`);

  const stage = document.querySelector('#sheetStage');
  stage.scrollLeft = 0;
  stage.scrollTop = 0;

  stage.innerHTML = segments.length
    ? segments.map((segment, i)=>`
        <figure class="sheet-page">
          <img
            class="sheet-image"
            src="${segment.image}"
            alt="${esc(group.name)} ${esc(active.number)} – ${i+1}. rész"
            loading="${i===0?'eager':'lazy'}"
            draggable="false">
          ${segments.length>1
            ? `<figcaption>${segment.continuation ? 'Versszakok' : `${i+1}. rész`}</figcaption>`
            : ''}
        </figure>
      `).join('')
    : `<div class="missing-sheet">
         Ehhez a változathoz jelenleg nincs megjeleníthető kép.
         Az eredeti PDF a fenti gombbal továbbra is megnyitható.
       </div>`;

  updateNavigation(active);
}

function normalizeSearch(s){
  return String(s ?? '')
    .toLocaleLowerCase('hu-HU')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g,'')
    .replace(/[^a-z0-9 ]/g,' ')
    .replace(/\s+/g,' ')
    .trim();
}

function setupSheetSearch(){
  const input = document.querySelector('#sheetSearch');
  const results = document.querySelector('#sheetSearchResults');
  if (!input || !results) return;

  function close(){
    results.hidden = true;
    results.innerHTML = '';
  }

  function renderResults(){
    const q = normalizeSearch(input.value);
    if (!q){
      close();
      return;
    }

    const matches = db.songs
      .filter(song => {
        const hay = [
          song.title,
          ...(song.aliases || []),
          song.searchTitle || ''
        ].map(normalizeSearch);
        return hay.some(x => x.includes(q));
      })
      .sort((a,b) => a.title.localeCompare(b.title,'hu-HU',{sensitivity:'base'}))
      .slice(0,10);

    if (!matches.length){
      results.innerHTML = '<div class="sheet-search-empty">Nincs találat.</div>';
      results.hidden = false;
      return;
    }

    const activeGroup = currentActive?.gid;
    results.innerHTML = matches.map(song => {
      let targetGroup = activeGroup && song.groups[activeGroup]
        ? activeGroup
        : Object.keys(song.groups)[0];

      const number = targetGroup ? groupNumber(song, targetGroup) : '';
      const groupName = targetGroup ? db.groups[targetGroup].name : '';

      return `<a class="sheet-search-result"
        href="song.html?id=${encodeURIComponent(song.id)}${targetGroup ? `&group=${encodeURIComponent(targetGroup)}` : ''}">
        <span class="sheet-search-title">${esc(song.title)}</span>
        <span class="sheet-search-meta">${number !== Infinity ? esc(number) : ''}${groupName ? ` · ${esc(groupName)}` : ''}</span>
      </a>`;
    }).join('');

    results.hidden = false;
  }

  input.addEventListener('input', renderResults);
  input.addEventListener('focus', renderResults);

  document.addEventListener('click', e => {
    if (!e.target.closest('.sheet-search-wrap')) close();
  });

  input.addEventListener('keydown', e => {
    if (e.key === 'Escape') close();
    if (e.key === 'Enter'){
      const first = results.querySelector('.sheet-search-result');
      if (first){
        e.preventDefault();
        location.href = first.href;
      }
    }
  });
}

function fail(message){
  root.innerHTML = `<div class="empty">${esc(message)}</div>`;
}

init();
