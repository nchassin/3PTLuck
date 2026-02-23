const formatNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toFixed(1);
};

const renderGame = (game) => {
  const home = game.home;
  const away = game.away;
  const homeDiff = home.adjusted_pts - home.actual_pts;
  const awayDiff = away.adjusted_pts - away.actual_pts;

  return `
    <article class="game-card">
      <div class="game-header">
        <span>${game.game_status || "Final"}</span>
        <span>${game.game_id}</span>
      </div>
      <div class="teams">
        <div class="team-row">
          <span class="abbr">${away.team_abbr}</span>
          <span class="actual">${formatNumber(away.actual_pts)}</span>
          <span class="adjusted">Adj: ${formatNumber(away.adjusted_pts)}</span>
          <span class="diff">Δ ${formatNumber(awayDiff)}</span>
        </div>
        <div class="team-row">
          <span class="abbr">${home.team_abbr}</span>
          <span class="actual">${formatNumber(home.actual_pts)}</span>
          <span class="adjusted">Adj: ${formatNumber(home.adjusted_pts)}</span>
          <span class="diff">Δ ${formatNumber(homeDiff)}</span>
        </div>
      </div>
    </article>
  `;
};

const loadData = async () => {
  const res = await fetch("./data/latest.json", { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load data");
  return res.json();
};

const init = async () => {
  const gamesEl = document.getElementById("games");
  try {
    const data = await loadData();
    document.getElementById("updated").textContent = data.generated_at || "—";
    document.getElementById("game-date").textContent = data.date || "—";

    if (!data.games || data.games.length === 0) {
      gamesEl.innerHTML = `<div class="game-card">No games found for this date.</div>`;
      return;
    }

    gamesEl.innerHTML = data.games.map(renderGame).join("");
  } catch (err) {
    gamesEl.innerHTML = `<div class="game-card">Unable to load data.</div>`;
  }
};

init();
