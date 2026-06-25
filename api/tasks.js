// JARVIS — task checkbox persistence
// Stores a { "<taskId>": "<YYYY-MM-DD done date>" } map in task_state.json
// on a dedicated branch (task-state) so it never collides with data.json /
// push.sh deploys on main.
//
// GET  /api/tasks            -> { done: { id: date, ... } }
// POST /api/tasks  {id,done}  -> updates the map, returns { done: {...} }

const OWNER = 'Darkfloww';
const REPO = 'jarvis-dashboard';
const BRANCH = 'task-state';
const PATH = 'task_state.json';

const GH = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${PATH}`;

function headers() {
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw new Error('GITHUB_TOKEN not configured');
  return {
    Authorization: `Bearer ${token}`,
    Accept: 'application/vnd.github+json',
    'User-Agent': 'jarvis-dashboard',
    'X-GitHub-Api-Version': '2022-11-28',
  };
}

// Read current file (content + sha). Returns { map, sha } or { map:{}, sha:null }.
async function readState() {
  const res = await fetch(`${GH}?ref=${BRANCH}&t=${Date.now()}`, {
    headers: headers(),
    cache: 'no-store',
  });
  if (res.status === 404) return { map: {}, sha: null };
  if (!res.ok) throw new Error(`GitHub read failed: ${res.status} ${await res.text()}`);
  const json = await res.json();
  const decoded = Buffer.from(json.content || '', 'base64').toString('utf8') || '{}';
  let map = {};
  try { map = JSON.parse(decoded); } catch (e) { map = {}; }
  return { map, sha: json.sha };
}

async function writeState(map, sha, message) {
  const body = {
    message,
    content: Buffer.from(JSON.stringify(map, null, 2)).toString('base64'),
    branch: BRANCH,
  };
  if (sha) body.sha = sha;
  const res = await fetch(GH, {
    method: 'PUT',
    headers: { ...headers(), 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const txt = await res.text();
    const err = new Error(`GitHub write failed: ${res.status} ${txt}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  try {
    if (req.method === 'OPTIONS') { res.status(204).end(); return; }

    if (req.method === 'GET') {
      const { map } = await readState();
      res.status(200).json({ done: map });
      return;
    }

    if (req.method === 'POST') {
      // body may arrive parsed or as a raw string depending on runtime
      let body = req.body;
      if (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) { body = {}; } }
      body = body || {};
      const id = String(body.id);
      const done = !!body.done;
      const date = body.date || new Date().toISOString().slice(0, 10);
      if (!id || id === 'undefined') { res.status(400).json({ error: 'missing id' }); return; }

      // optimistic-with-retry on sha conflict
      for (let attempt = 0; attempt < 3; attempt++) {
        const { map, sha } = await readState();
        if (done) map[id] = date; else delete map[id];
        try {
          await writeState(map, sha, `tasks: ${done ? 'done' : 'undo'} #${id} (${date})`);
          res.status(200).json({ done: map });
          return;
        } catch (e) {
          if (e.status === 409 && attempt < 2) continue; // sha race, retry
          throw e;
        }
      }
      res.status(409).json({ error: 'conflict' });
      return;
    }

    res.status(405).json({ error: 'method not allowed' });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
};
