let db;
const $ = (s) => document.querySelector(s);

const normalize = (s) => String(s ?? '')
  .toLocaleLowerCase('hu-HU')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g,'')
  .replace(/[^a-z0-9 ]/g,' ')
  .replace(/\s+/g,' ')
  .trim();

function groupNumber(song, gid){
  const entries = song.groups[gid] || [];
  if (!entries.length) return Number.POSITIVE_INFINITY;
  return Math.min(...entries.map(e => Number(e.number)).filter(Number.isFinite));
}

async function init(){
  try {
    db = window.SONG_DB || await fetch('data/songs.json').then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    });

    $('#search').addEventListener('input', render);
    $('#groupFilter').addEventListener('change', render);
    $('#sortMode').addEventListener('change', render);
    $('#searchForm').addEventListener('submit', (event) => {
      event.preventDefault();
      render();
    });

    render();
  } catch (error) {
    console.error(error);
    $('#status').textContent = 'Nem sikerült betölteni az énekadatokat.';
    $('#results').innerHTML = '<div class="empty">Az adatfájl nem tölthető be.</div>';
  }
}

function render(){
  if (!db) return;

  const qRaw = $('#search').value.trim();
  const q = normalize(qRaw);
  const gf = $('#groupFilter').value;
  const sortMode = $('#sortMode')?.value || 'abc';

  let hits = db.songs.filter(song => {
    if (gf !== 'all' && !song.groups[gf]) return false;
    if (!q) return true;

    const nums = Object.values(song.groups).flat().map(x => String(x.number));
    const aliases = (song.aliases || []).map(normalize);
    return normalize(song.searchTitle || song.title).includes(q) ||
           aliases.some(a => a.includes(q)) ||
           nums.some(n => n.includes(q));
  });

  // User-controlled sorting.
  if (sortMode === 'number') {
    hits.sort((a,b) => {
      // If one group is selected, use that group's numbering.
      if (gf !== 'all') {
        const numberDiff = groupNumber(a, gf) - groupNumber(b, gf);
        if (numberDiff !== 0) return numberDiff;
      } else {
        // In "Összes csoport" mode there is no single authoritative number.
        // Use the smallest number found among all group versions.
        const minNumber = song => {
          const nums = Object.values(song.groups)
            .flat()
            .map(e => Number(e.number))
            .filter(Number.isFinite);
          return nums.length ? Math.min(...nums) : Number.POSITIVE_INFINITY;
        };
        const numberDiff = minNumber(a) - minNumber(b);
        if (numberDiff !== 0) return numberDiff;
      }
      return a.title.localeCompare(b.title, 'hu-HU', {sensitivity:'base'});
    });
  } else {
    hits.sort((a,b) => a.title.localeCompare(b.title, 'hu-HU', {
      sensitivity: 'base',
      numeric: true
    }));
  }

  $('#status').textContent = q ? `Találatok erre: „${qRaw}”` : '';
  $('#count').textContent = `${hits.length} ének`;
  $('#results').innerHTML = hits.length
    ? hits.map(song => card(song, gf)).join('')
    : '<div class="empty">Nincs találat.</div>';
}

function card(song, selectedGroup){
  const groupEntries = selectedGroup !== 'all'
    ? Object.entries(song.groups).filter(([gid]) => gid === selectedGroup)
    : Object.entries(song.groups);

  const meta = groupEntries.map(([gid, entries]) => {
    const nums = entries.map(e => `${e.number}`).join(', ');
    return `<span class="badge badge-${escapeHtml(gid)}">${escapeHtml(db.groups[gid].name)}: <span class="number">${escapeHtml(nums)}</span></span>`;
  }).join('');

  const preferred = selectedGroup !== 'all' && song.groups[selectedGroup]
    ? `&group=${encodeURIComponent(selectedGroup)}`
    : '';

  return `<a class="song song-link" href="song.html?id=${encodeURIComponent(song.id)}${preferred}">
    <div class="song-main">
      <h2>${escapeHtml(song.title)}</h2>
      <div class="meta">${meta}</div>
    </div>
    <span class="open-arrow" aria-hidden="true">→</span>
  </a>`;
}

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'
  }[c]));
}

init();
