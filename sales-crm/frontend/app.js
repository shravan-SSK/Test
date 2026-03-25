/* ── Sales CRM – frontend SPA ─────────────────────────────────────────────── */

const API = '/api/v1';

// ── Utilities ─────────────────────────────────────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  if (res.status === 204) return null;
  return res.json();
}

function toast(msg, ok = true) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${ok ? 'toast-ok' : 'toast-err'}`;
  setTimeout(() => el.classList.add('hidden'), 3000);
}

function openModal(title, html, onSubmit) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal-overlay').classList.remove('hidden');
  if (onSubmit) {
    document.getElementById('crm-form')?.addEventListener('submit', async e => {
      e.preventDefault();
      try {
        await onSubmit(e);
        closeModal();
      } catch (err) { toast(err.message, false); }
    });
  }
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

function badge(text, colorClass = 'badge-gray') {
  return `<span class="badge ${colorClass}">${text}</span>`;
}

const STAGE_COLORS = {
  prospecting:        'badge-gray',
  qualification:      'badge-blue',
  needs_analysis:     'badge-blue',
  value_proposition:  'badge-purple',
  proposal:           'badge-yellow',
  negotiation:        'badge-yellow',
  closed_won:         'badge-green',
  closed_lost:        'badge-red',
};

const LEAD_COLORS = {
  new: 'badge-blue', contacted: 'badge-yellow',
  qualified: 'badge-green', unqualified: 'badge-red', converted: 'badge-purple',
};

// ── Pages ─────────────────────────────────────────────────────────────────────

async function renderDashboard() {
  let leads = [], contacts = [], accounts = [], projects = [], pipeline = {};
  try {
    [leads, contacts, accounts, projects, pipeline] = await Promise.all([
      api('GET', '/leads?limit=1000'),
      api('GET', '/contacts?limit=1000'),
      api('GET', '/accounts?limit=1000'),
      api('GET', '/projects?limit=1000'),
      api('GET', '/sales-cycle/pipeline'),
    ]);
  } catch { toast('Could not load dashboard', false); }

  const wonValue = pipeline['closed_won']?.total_value || 0;
  const openValue = Object.entries(pipeline)
    .filter(([k]) => !['closed_won','closed_lost'].includes(k))
    .reduce((s, [, v]) => s + (v.total_value || 0), 0);

  return `
    <div class="stats-grid">
      <div class="stat-card accent">
        <div class="stat-label">Leads</div>
        <div class="stat-value">${leads.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Contacts</div>
        <div class="stat-value">${contacts.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Accounts</div>
        <div class="stat-value">${accounts.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Projects</div>
        <div class="stat-value">${projects.length}</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">Won Pipeline ($)</div>
        <div class="stat-value" style="font-size:22px">$${wonValue.toLocaleString()}</div>
      </div>
      <div class="stat-card warning">
        <div class="stat-label">Open Pipeline ($)</div>
        <div class="stat-value" style="font-size:22px">$${openValue.toLocaleString()}</div>
      </div>
    </div>

    <h2 style="margin-bottom:14px;font-size:15px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em">Recent Leads</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Name</th><th>Email</th><th>Company</th><th>Source</th><th>Status</th></tr></thead>
        <tbody>
          ${leads.slice(0,8).map(l => `
            <tr>
              <td>${l.first_name || ''} ${l.last_name || ''}</td>
              <td>${l.email || '—'}</td>
              <td>${l.company || '—'}</td>
              <td>${l.source || '—'}</td>
              <td>${badge(l.status, LEAD_COLORS[l.status] || 'badge-gray')}</td>
            </tr>`).join('') || '<tr><td colspan="5" style="color:var(--muted);text-align:center">No leads yet</td></tr>'}
        </tbody>
      </table>
    </div>`;
}

// ── Leads ─────────────────────────────────────────────────────────────────────

async function renderLeads() {
  const leads = await api('GET', '/leads?limit=500').catch(() => []);
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Title</th><th>Name</th><th>Email</th><th>Company</th><th>Source</th><th>Status</th><th>Score</th><th></th></tr></thead>
        <tbody>
          ${leads.map(l => `
            <tr>
              <td>${l.title}</td>
              <td>${l.first_name || ''} ${l.last_name || ''}</td>
              <td>${l.email || '—'}</td>
              <td>${l.company || '—'}</td>
              <td>${l.source || '—'}</td>
              <td>${badge(l.status, LEAD_COLORS[l.status])}</td>
              <td>${l.score}</td>
              <td style="display:flex;gap:4px">
                <button class="btn btn-sm btn-ghost" onclick="openLeadDetail(${l.id})">View</button>
                <button class="btn btn-sm btn-ghost" onclick="convertLead(${l.id})">Convert</button>
                <button class="btn btn-sm btn-danger" onclick="deleteLead(${l.id})">Del</button>
              </td>
            </tr>`).join('') || '<tr><td colspan="8" style="color:var(--muted);text-align:center">No leads</td></tr>'}
        </tbody>
      </table>
    </div>`;
}

function addLeadForm() {
  openModal('Add Lead', `
    <form id="crm-form">
      <div class="form-grid">
        <div class="form-group"><label>Title *</label><input name="title" required /></div>
        <div class="form-group"><label>Company</label><input name="company" /></div>
        <div class="form-group"><label>First Name</label><input name="first_name" /></div>
        <div class="form-group"><label>Last Name</label><input name="last_name" /></div>
        <div class="form-group"><label>Email</label><input name="email" type="email" /></div>
        <div class="form-group"><label>Phone</label><input name="phone" /></div>
        <div class="form-group"><label>Source</label>
          <select name="source"><option>email</option><option>linkedin</option><option>web</option><option>manual</option></select>
        </div>
        <div class="form-group"><label>Score (0-100)</label><input name="score" type="number" min="0" max="100" value="0" /></div>
      </div>
      <div class="form-group"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Lead</button>
      </div>
    </form>`, async (e) => {
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    body.score = parseInt(body.score) || 0;
    await api('POST', '/leads', body);
    toast('Lead created'); navigate('leads');
  });
}

async function convertLead(id) {
  try {
    const res = await api('POST', `/leads/${id}/convert`);
    toast(`Converted → Contact #${res.contact_id}, Project #${res.project_id}`);
    navigate('leads');
  } catch (err) { toast(err.message, false); }
}

async function deleteLead(id) {
  if (!confirm('Delete this lead?')) return;
  await api('DELETE', `/leads/${id}`).catch(err => toast(err.message, false));
  toast('Deleted'); navigate('leads');
}

// ── Contacts ──────────────────────────────────────────────────────────────────

async function renderContacts() {
  const contacts = await api('GET', '/contacts?limit=500').catch(() => []);
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Job Title</th><th>LinkedIn</th><th></th></tr></thead>
        <tbody>
          ${contacts.map(c => `
            <tr>
              <td>${c.first_name} ${c.last_name || ''}</td>
              <td>${c.email || '—'}</td>
              <td>${c.phone || '—'}</td>
              <td>${c.job_title || '—'}</td>
              <td>${c.linkedin_url ? `<a href="${c.linkedin_url}" target="_blank" style="color:var(--accent)">Profile</a>` : '—'}</td>
              <td style="display:flex;gap:4px">
                <button class="btn btn-sm btn-ghost" onclick="openContactDetail(${c.id})">View</button>
                <button class="btn btn-sm btn-ghost" onclick="scanLinkedIn('contact',${c.id})">Scan LI</button>
                <button class="btn btn-sm btn-danger" onclick="deleteContact(${c.id})">Del</button>
              </td>
            </tr>`).join('') || '<tr><td colspan="6" style="color:var(--muted);text-align:center">No contacts</td></tr>'}
        </tbody>
      </table>
    </div>`;
}

function addContactForm() {
  openModal('Add Contact', `
    <form id="crm-form">
      <div class="form-grid">
        <div class="form-group"><label>First Name *</label><input name="first_name" required /></div>
        <div class="form-group"><label>Last Name</label><input name="last_name" /></div>
        <div class="form-group"><label>Email</label><input name="email" type="email" /></div>
        <div class="form-group"><label>Phone</label><input name="phone" /></div>
        <div class="form-group"><label>Job Title</label><input name="job_title" /></div>
        <div class="form-group"><label>Department</label><input name="department" /></div>
      </div>
      <div class="form-group"><label>LinkedIn URL</label><input name="linkedin_url" /></div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Contact</button>
      </div>
    </form>`, async (e) => {
    const fd = new FormData(e.target);
    await api('POST', '/contacts', Object.fromEntries(fd.entries()));
    toast('Contact created'); navigate('contacts');
  });
}

async function deleteContact(id) {
  if (!confirm('Delete this contact?')) return;
  await api('DELETE', `/contacts/${id}`).catch(err => toast(err.message, false));
  toast('Deleted'); navigate('contacts');
}

// ── Accounts ──────────────────────────────────────────────────────────────────

async function renderAccounts() {
  const accounts = await api('GET', '/accounts?limit=500').catch(() => []);
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Name</th><th>Domain</th><th>Industry</th><th>Website</th><th>Employees</th><th></th></tr></thead>
        <tbody>
          ${accounts.map(a => `
            <tr>
              <td>${a.name}</td>
              <td>${a.domain || '—'}</td>
              <td>${a.industry || '—'}</td>
              <td>${a.website ? `<a href="${a.website}" target="_blank" style="color:var(--accent)">${a.website}</a>` : '—'}</td>
              <td>${a.employees || '—'}</td>
              <td style="display:flex;gap:4px">
                <button class="btn btn-sm btn-ghost" onclick="openAccountDetail(${a.id})">View</button>
                <button class="btn btn-sm btn-danger" onclick="deleteAccount(${a.id})">Del</button>
              </td>
            </tr>`).join('') || '<tr><td colspan="6" style="color:var(--muted);text-align:center">No accounts</td></tr>'}
        </tbody>
      </table>
    </div>`;
}

function addAccountForm() {
  openModal('Add Account', `
    <form id="crm-form">
      <div class="form-grid">
        <div class="form-group"><label>Name *</label><input name="name" required /></div>
        <div class="form-group"><label>Domain</label><input name="domain" placeholder="acme.com" /></div>
        <div class="form-group"><label>Industry</label><input name="industry" /></div>
        <div class="form-group"><label>Website</label><input name="website" /></div>
        <div class="form-group"><label>Revenue ($)</label><input name="revenue" type="number" /></div>
        <div class="form-group"><label>Employees</label><input name="employees" type="number" /></div>
      </div>
      <div class="form-group"><label>Address</label><textarea name="address" rows="2"></textarea></div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Account</button>
      </div>
    </form>`, async (e) => {
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    if (body.revenue) body.revenue = parseFloat(body.revenue);
    if (body.employees) body.employees = parseInt(body.employees);
    await api('POST', '/accounts', body);
    toast('Account created'); navigate('accounts');
  });
}

async function deleteAccount(id) {
  if (!confirm('Delete this account?')) return;
  await api('DELETE', `/accounts/${id}`).catch(err => toast(err.message, false));
  toast('Deleted'); navigate('accounts');
}

// ── Projects ──────────────────────────────────────────────────────────────────

async function renderProjects() {
  const projects = await api('GET', '/projects?limit=500').catch(() => []);
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Name</th><th>Status</th><th>Value</th><th>Close Date</th><th></th></tr></thead>
        <tbody>
          ${projects.map(p => `
            <tr>
              <td>${p.name}</td>
              <td>${badge(p.status, p.status === 'active' ? 'badge-green' : p.status === 'closed' ? 'badge-red' : 'badge-blue')}</td>
              <td>${p.value ? '$' + Number(p.value).toLocaleString() + ' ' + (p.currency||'USD') : '—'}</td>
              <td>${p.close_date ? new Date(p.close_date).toLocaleDateString() : '—'}</td>
              <td style="display:flex;gap:4px">
                <button class="btn btn-sm btn-ghost" onclick="openProjectDetail(${p.id})">View</button>
                <button class="btn btn-sm btn-ghost" onclick="identifyStakeholders(${p.id})">Find Stakeholders</button>
                <button class="btn btn-sm btn-danger" onclick="deleteProject(${p.id})">Del</button>
              </td>
            </tr>`).join('') || '<tr><td colspan="5" style="color:var(--muted);text-align:center">No projects</td></tr>'}
        </tbody>
      </table>
    </div>`;
}

function addProjectForm() {
  openModal('Add Project', `
    <form id="crm-form">
      <div class="form-grid">
        <div class="form-group"><label>Name *</label><input name="name" required /></div>
        <div class="form-group"><label>Value ($)</label><input name="value" type="number" /></div>
        <div class="form-group"><label>Currency</label><input name="currency" value="USD" /></div>
        <div class="form-group"><label>Close Date</label><input name="close_date" type="date" /></div>
      </div>
      <div class="form-group"><label>Description</label><textarea name="description" rows="2"></textarea></div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Project</button>
      </div>
    </form>`, async (e) => {
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    if (body.value) body.value = parseFloat(body.value);
    if (body.close_date) body.close_date = new Date(body.close_date).toISOString();
    await api('POST', '/projects', body);
    toast('Project created'); navigate('projects');
  });
}

async function identifyStakeholders(projectId) {
  try {
    const res = await api('POST', `/stakeholders/identify-from-project/${projectId}`);
    toast(`Identified ${res.length} stakeholder(s)`);
    navigate('stakeholders');
  } catch (err) { toast(err.message, false); }
}

async function deleteProject(id) {
  if (!confirm('Delete this project?')) return;
  await api('DELETE', `/projects/${id}`).catch(err => toast(err.message, false));
  toast('Deleted'); navigate('projects');
}

// ── Stakeholders ──────────────────────────────────────────────────────────────

async function renderStakeholders() {
  const stakeholders = await api('GET', '/stakeholders?limit=500').catch(() => []);
  return stakeholders.map(s => {
    let liData = {};
    try { liData = JSON.parse(s.linkedin_data || '{}'); } catch {}
    let signals = [];
    try { signals = JSON.parse(s.buying_signals || '[]'); } catch {}
    const initials = (s.name || '?').split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase();
    const aiEnriched = !!s.ai_enriched_at;

    return `
      <div class="profile-card">
        <div class="pc-header">
          <div class="pc-avatar">${initials}</div>
          <div class="pc-info">
            <h3>${s.name} ${aiEnriched ? '<span style="font-size:11px;color:var(--accent);font-weight:400">✦ AI enriched</span>' : ''}</h3>
            <p>${liData.headline || s.role || '—'} ${liData.current_company ? '@ ' + liData.current_company : ''}</p>
            <p style="font-size:12px;color:var(--muted)">
              ${s.email || ''}
              ${liData.location ? '· ' + liData.location : ''}
              ${s.account_id ? '· Account #' + s.account_id : ''}
              ${s.lead_id ? '· Lead #' + s.lead_id : ''}
            </p>
          </div>
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
          ${badge(s.influence_level || 'unknown', s.influence_level === 'high' ? 'badge-red' : s.influence_level === 'medium' ? 'badge-yellow' : 'badge-gray')}
          ${badge(s.sentiment || 'neutral', s.sentiment === 'positive' ? 'badge-green' : s.sentiment === 'negative' ? 'badge-red' : 'badge-gray')}
          ${s.role ? badge(s.role, 'badge-blue') : ''}
        </div>

        ${s.ai_summary ? `
          <div style="background:var(--surface2);border-left:3px solid var(--accent);border-radius:4px;padding:10px 12px;margin-bottom:10px">
            <div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--accent);margin-bottom:4px">✦ AI Summary</div>
            <p style="font-size:12.5px;line-height:1.5">${s.ai_summary}</p>
          </div>` : liData.summary ? `<p style="color:var(--muted);font-size:12.5px;margin-bottom:10px">${liData.summary}</p>` : ''}

        ${s.approach_recommendation ? `
          <div style="background:var(--surface2);border-left:3px solid var(--success);border-radius:4px;padding:10px 12px;margin-bottom:10px">
            <div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--success);margin-bottom:4px">✦ How to Approach</div>
            <p style="font-size:12.5px;line-height:1.5">${s.approach_recommendation}</p>
          </div>` : ''}

        ${signals.length ? `
          <div style="margin-bottom:10px">
            <div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--warning);margin-bottom:6px">✦ Buying Signals</div>
            <div class="pc-skills">${signals.map(sig => `<span class="skill-tag" style="border-color:var(--warning);color:var(--warning)">${sig}</span>`).join('')}</div>
          </div>` : ''}

        ${liData.skills?.length ? `
          <div style="margin-bottom:10px">
            <div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:6px">Skills</div>
            <div class="pc-skills">${liData.skills.map(sk => `<span class="skill-tag">${sk}</span>`).join('')}</div>
          </div>` : ''}

        <div style="display:flex;gap:6px;margin-top:12px;flex-wrap:wrap">
          <button class="btn btn-sm btn-ghost" onclick="openStakeholderDetail(${s.id})">View Details</button>
          ${s.linkedin_url ? `<button class="btn btn-sm btn-ghost" onclick="rescanLinkedIn('stakeholder',${s.id},'${s.linkedin_url}')">Re-scan + Re-analyse</button>` : ''}
          <button class="btn btn-sm btn-ghost" onclick="scanLinkedIn('stakeholder',${s.id})">Add LinkedIn</button>
          <button class="btn btn-sm btn-danger" onclick="deleteStakeholder(${s.id})">Del</button>
        </div>
      </div>`;
  }).join('') || '<p style="color:var(--muted)">No stakeholders yet. Open a project and click "Find Stakeholders".</p>';
}

function addStakeholderForm() {
  openModal('Add Stakeholder', `
    <form id="crm-form">
      <div class="form-grid">
        <div class="form-group"><label>Name *</label><input name="name" required /></div>
        <div class="form-group"><label>Email</label><input name="email" type="email" /></div>
        <div class="form-group"><label>Role</label>
          <select name="role"><option>decision-maker</option><option>influencer</option><option>user</option><option>champion</option><option>unknown</option></select>
        </div>
        <div class="form-group"><label>Influence</label>
          <select name="influence_level"><option>high</option><option value="medium" selected>medium</option><option>low</option></select>
        </div>
        <div class="form-group"><label>Sentiment</label>
          <select name="sentiment"><option>positive</option><option value="neutral" selected>neutral</option><option>negative</option></select>
        </div>
      </div>
      <div class="form-group"><label>LinkedIn URL</label><input name="linkedin_url" /></div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Save</button>
      </div>
    </form>`, async (e) => {
    const fd = new FormData(e.target);
    await api('POST', '/stakeholders', Object.fromEntries(fd.entries()));
    toast('Stakeholder created'); navigate('stakeholders');
  });
}

async function scanLinkedIn(entityType, entityId, prefillUrl = '') {
  openModal('Scan LinkedIn Profile', `
    <form id="crm-form">
      <div class="form-group">
        <label>LinkedIn Profile URL</label>
        <input name="linkedin_url" value="${prefillUrl}" placeholder="https://www.linkedin.com/in/..." required />
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Scan</button>
      </div>
    </form>`, async (e) => {
    const fd = new FormData(e.target);
    const body = { linkedin_url: fd.get('linkedin_url'), entity_type: entityType, entity_id: entityId };
    await api('POST', '/stakeholders/scan-linkedin', body);
    toast('Profile scanned!'); navigate('stakeholders');
  });
}

async function rescanLinkedIn(entityType, entityId, url) {
  try {
    await api('POST', '/stakeholders/scan-linkedin', { linkedin_url: url, entity_type: entityType, entity_id: entityId });
    toast('Profile refreshed!'); navigate('stakeholders');
  } catch (err) { toast(err.message, false); }
}

async function deleteStakeholder(id) {
  if (!confirm('Delete this stakeholder?')) return;
  await api('DELETE', `/stakeholders/${id}`).catch(err => toast(err.message, false));
  toast('Deleted'); navigate('stakeholders');
}

// ── Pipeline ──────────────────────────────────────────────────────────────────

async function renderPipeline() {
  const [pipeline, cycles, projects] = await Promise.all([
    api('GET', '/sales-cycle/pipeline').catch(() => ({})),
    api('GET', '/sales-cycle?limit=500').catch(() => []),
    api('GET', '/projects?limit=500').catch(() => []),
  ]);

  const projectMap = Object.fromEntries(projects.map(p => [p.id, p]));

  const stages = [
    'prospecting','qualification','needs_analysis',
    'value_proposition','proposal','negotiation','closed_won','closed_lost',
  ];

  const cols = stages.map(stage => {
    const info = pipeline[stage] || {};
    const stageCycles = cycles.filter(c => c.stage === stage);
    const cards = stageCycles.map(c => {
      const proj = projectMap[c.project_id] || {};
      return `
        <div class="pipeline-card" onclick="openCycleDetail(${c.id})">
          <div class="pc-name">${proj.name || `Project #${c.project_id}`}</div>
          <div class="pc-value">${proj.value ? '$' + Number(proj.value).toLocaleString() : '—'}</div>
          <div class="pc-prob">${c.probability}% probability</div>
        </div>`;
    }).join('');

    const label = stage.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase());
    return `
      <div class="pipeline-col">
        <h3>${label} <span class="col-count">${info.count || 0}</span></h3>
        ${cards || '<p style="color:var(--muted);font-size:12px">Empty</p>'}
      </div>`;
  });

  return `<div class="pipeline">${cols.join('')}</div>`;
}

async function openCycleDetail(cycleId) {
  const [cycle, activities] = await Promise.all([
    api('GET', `/sales-cycle/${cycleId}`),
    api('GET', `/sales-cycle/${cycleId}/activities`),
  ]);

  const stages = ['prospecting','qualification','needs_analysis','value_proposition','proposal','negotiation','closed_won','closed_lost'];
  const stageOptions = stages.map(s =>
    `<option value="${s}" ${s === cycle.stage ? 'selected' : ''}>${s.replace(/_/g,' ')}</option>`).join('');

  openModal(`Deal #${cycle.project_id} – Sales Cycle`, `
    <div style="margin-bottom:16px">
      ${badge(cycle.stage, STAGE_COLORS[cycle.stage])}
      <span style="margin-left:10px;color:var(--muted)">${cycle.probability}% probability</span>
    </div>
    <div style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:12px;margin-bottom:16px">
      <div style="color:var(--muted);font-size:11px;text-transform:uppercase;margin-bottom:4px">Next Action</div>
      <div>${cycle.next_action || '—'}</div>
    </div>
    <form id="crm-form">
      <div class="form-group">
        <label>Advance to Stage</label>
        <select name="new_stage">${stageOptions}</select>
      </div>
      <div class="form-group"><label>Notes</label><textarea name="notes" rows="2"></textarea></div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Close</button>
        <button type="submit" class="btn btn-primary">Advance Stage</button>
      </div>
    </form>
    <h4 style="margin:16px 0 8px;color:var(--muted);font-size:11px;text-transform:uppercase">Activity Log</h4>
    ${activities.map(a => `
      <div style="border-left:2px solid var(--border);padding:6px 12px;margin-bottom:8px">
        <div style="font-weight:600;font-size:13px">${a.title}</div>
        <div style="color:var(--muted);font-size:12px">${a.description || ''}</div>
        <div style="color:var(--muted);font-size:11px">${new Date(a.created_at).toLocaleString()}</div>
      </div>`).join('') || '<p style="color:var(--muted);font-size:12px">No activity yet</p>'}
  `, async (e) => {
    const fd = new FormData(e.target);
    const res = await api('POST', `/sales-cycle/${cycleId}/advance`, {
      new_stage: fd.get('new_stage'),
      notes: fd.get('notes'),
    });
    toast(res.message);
    navigate('pipeline');
  });
}

// ── Emails ────────────────────────────────────────────────────────────────────

async function renderEmails() {
  const threads = await api('GET', '/emails?limit=200').catch(() => []);
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Subject</th><th>From</th><th>To</th><th>Received</th><th>Contact</th><th>Project</th></tr></thead>
        <tbody>
          ${threads.map(t => `
            <tr>
              <td>${t.subject || '(no subject)'}</td>
              <td>${t.from_email}</td>
              <td>${t.to_emails || '—'}</td>
              <td>${t.received_at ? new Date(t.received_at).toLocaleDateString() : '—'}</td>
              <td>${t.contact_id ? `#${t.contact_id}` : badge('unmatched','badge-yellow')}</td>
              <td>${t.project_id ? `#${t.project_id}` : '—'}</td>
            </tr>`).join('') || '<tr><td colspan="6" style="color:var(--muted);text-align:center">No emails ingested</td></tr>'}
        </tbody>
      </table>
    </div>`;
}

function addEmailForm() {
  openModal('Ingest Email Thread', `
    <form id="crm-form">
      <div class="form-group"><label>From Email *</label><input name="from_email" type="email" required /></div>
      <div class="form-group"><label>To (comma-separated)</label><input name="to_emails" /></div>
      <div class="form-group"><label>CC</label><input name="cc_emails" /></div>
      <div class="form-group"><label>Subject</label><input name="subject" /></div>
      <div class="form-group"><label>Body</label><textarea name="body" rows="4"></textarea></div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Ingest & Map</button>
      </div>
    </form>`, async (e) => {
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    await api('POST', '/emails/ingest', body);
    toast('Email ingested & mapped'); navigate('emails');
  });
}

// ── Detail Modals ─────────────────────────────────────────────────────────────

function sectionHdr(title) {
  return `<div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin:14px 0 5px;font-weight:600">${title}</div>`;
}

function relRow(label, sub, actions = '') {
  return `<div style="display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border)">
    <div><div style="font-weight:500;font-size:13px">${label}</div>${sub ? `<div style="color:var(--muted);font-size:11px">${sub}</div>` : ''}</div>
    <div style="display:flex;gap:4px">${actions}</div>
  </div>`;
}

function relList(rows, empty = 'None') {
  return rows.length ? rows.join('') : `<p style="color:var(--muted);font-size:12px;padding:4px 0">${empty}</p>`;
}

// ── Account detail ────────────────────────────────────────────────────────────

async function openAccountDetail(id) {
  const [acct, contacts, leads, projects, stakeholders] = await Promise.all([
    api('GET', `/accounts/${id}`),
    api('GET', `/accounts/${id}/contacts`).catch(() => []),
    api('GET', `/accounts/${id}/leads`).catch(() => []),
    api('GET', `/accounts/${id}/projects`).catch(() => []),
    api('GET', `/accounts/${id}/stakeholders`).catch(() => []),
  ]);
  openModal(acct.name, `
    <div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
        ${acct.industry ? badge(acct.industry,'badge-blue') : ''}
        ${acct.employees ? `<span style="font-size:12px;color:var(--muted)">${acct.employees} employees</span>` : ''}
        ${acct.revenue ? `<span style="font-size:12px;color:var(--muted)">$${Number(acct.revenue).toLocaleString()} rev</span>` : ''}
      </div>
      ${acct.domain ? `<p style="font-size:12px;color:var(--muted);margin-bottom:8px">${acct.domain}${acct.website ? ' · <a href="'+acct.website+'" target="_blank" style="color:var(--accent)">website</a>' : ''}</p>` : ''}
      ${sectionHdr('Contacts ('+contacts.length+')')}
      ${relList(contacts.map(c => relRow(
        `${c.first_name} ${c.last_name||''}`, c.email||'',
        `<button class="btn btn-sm btn-danger" onclick="unlinkThen('accounts',${id},'contact',${c.id},openAccountDetail)">Unlink</button>`)))}
      <button class="btn btn-sm btn-ghost" style="margin-top:6px" onclick="linkEntityModal('accounts',${id},'contact','contacts',openAccountDetail)">+ Link Contact</button>
      ${sectionHdr('Leads ('+leads.length+')')}
      ${relList(leads.map(l => relRow(l.title, (l.email||l.company||'')+'  '+badge(l.status,LEAD_COLORS[l.status]||'badge-gray'), `<button class="btn btn-sm btn-ghost" onclick="openLeadDetail(${l.id})">View</button>`)))}
      ${sectionHdr('Projects ('+projects.length+')')}
      ${relList(projects.map(p => relRow(p.name, badge(p.status,'badge-gray'), `<button class="btn btn-sm btn-ghost" onclick="openProjectDetail(${p.id})">View</button>`)))}
      ${sectionHdr('Stakeholders ('+stakeholders.length+')')}
      ${relList(stakeholders.map(s => relRow(s.name, s.role||s.email||'', `<button class="btn btn-sm btn-ghost" onclick="openStakeholderDetail(${s.id})">View</button>`)))}
      <div style="margin-top:16px;text-align:right"><button class="btn btn-ghost" onclick="closeModal()">Close</button></div>
    </div>`);
}

async function unlinkThen(resource, id, entityType, entityId, reopenFn) {
  try {
    await api('DELETE', `/${resource}/${id}/unlink/${entityType}/${entityId}`);
    toast('Unlinked'); reopenFn(id);
  } catch(e) { toast(e.message, false); }
}

async function linkEntityModal(resource, id, entityType, listResource, reopenFn) {
  const items = await api('GET', `/${listResource}?limit=500`).catch(() => []);
  const opts = items.map(e => {
    const lbl = e.first_name ? `${e.first_name} ${e.last_name||''} (${e.email||'#'+e.id})` : (e.title || e.name || '#'+e.id);
    return `<option value="${e.id}">${lbl}</option>`;
  }).join('');
  openModal(`Link ${entityType}`, `
    <form id="crm-form">
      <div class="form-group"><label>Select ${entityType}</label>
        <select name="eid">${opts||'<option disabled>No items found</option>'}</select>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Link</button>
      </div>
    </form>`, async (e) => {
    const eid = new FormData(e.target).get('eid');
    await api('POST', `/${resource}/${id}/link/${entityType}/${eid}`);
    toast('Linked'); reopenFn(id);
  });
}

// ── Contact detail ────────────────────────────────────────────────────────────

async function openContactDetail(id) {
  const [c, accounts, projects, leads] = await Promise.all([
    api('GET', `/contacts/${id}`),
    api('GET', `/contacts/${id}/accounts`).catch(() => []),
    api('GET', `/contacts/${id}/projects`).catch(() => []),
    api('GET', `/contacts/${id}/leads`).catch(() => []),
  ]);
  const stakeholder = await api('GET', `/contacts/${id}/stakeholder`).catch(() => null);
  openModal(`${c.first_name} ${c.last_name||''}`, `
    <div>
      <p style="font-size:12px;color:var(--muted);margin-bottom:10px">${c.email||''} ${c.phone ? '· '+c.phone : ''} ${c.job_title ? '· '+c.job_title : ''}</p>
      ${sectionHdr('Accounts ('+accounts.length+')')}
      ${relList(accounts.map(a => relRow(a.name, a.domain||'',
        `<button class="btn btn-sm btn-ghost" onclick="openAccountDetail(${a.id})">View</button>
         <button class="btn btn-sm btn-danger" onclick="unlinkThen('contacts',${id},'account',${a.id},openContactDetail)">Unlink</button>`)))}
      <button class="btn btn-sm btn-ghost" style="margin-top:6px" onclick="linkEntityModal('contacts',${id},'account','accounts',openContactDetail)">+ Link Account</button>
      ${sectionHdr('Projects ('+projects.length+')')}
      ${relList(projects.map(p => relRow(p.name, badge(p.status,'badge-gray'),
        `<button class="btn btn-sm btn-ghost" onclick="openProjectDetail(${p.id})">View</button>
         <button class="btn btn-sm btn-danger" onclick="unlinkThen('contacts',${id},'project',${p.id},openContactDetail)">Unlink</button>`)))}
      <button class="btn btn-sm btn-ghost" style="margin-top:6px" onclick="linkEntityModal('contacts',${id},'project','projects',openContactDetail)">+ Link Project</button>
      ${sectionHdr('Leads ('+leads.length+')')}
      ${relList(leads.map(l => relRow(l.title, badge(l.status,LEAD_COLORS[l.status]||'badge-gray'),
        `<button class="btn btn-sm btn-ghost" onclick="openLeadDetail(${l.id})">View</button>`)))}
      ${sectionHdr('Stakeholder Profile')}
      ${stakeholder ? relRow(stakeholder.name, (stakeholder.role||'')+(stakeholder.influence_level?' · '+stakeholder.influence_level:''),
        `<button class="btn btn-sm btn-ghost" onclick="openStakeholderDetail(${stakeholder.id})">View</button>`) : '<p style="color:var(--muted);font-size:12px">No stakeholder profile yet. Use "Scan LI" to create one.</p>'}
      <div style="margin-top:16px;text-align:right"><button class="btn btn-ghost" onclick="closeModal()">Close</button></div>
    </div>`);
}

// ── Lead detail ────────────────────────────────────────────────────────────────

async function openLeadDetail(id) {
  const lead = await api('GET', `/leads/${id}`);
  const contact = await api('GET', `/leads/${id}/contact`).catch(() => null);
  const account = await api('GET', `/leads/${id}/account`).catch(() => null);
  const project = await api('GET', `/leads/${id}/project`).catch(() => null);
  const stakeholders = await api('GET', `/leads/${id}/stakeholders`).catch(() => []);
  openModal(lead.title, `
    <div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
        ${badge(lead.status, LEAD_COLORS[lead.status]||'badge-gray')}
        <span style="font-size:12px;color:var(--muted)">Score: ${lead.score||0}</span>
        ${lead.source ? badge(lead.source,'badge-blue') : ''}
      </div>
      <p style="font-size:12px;color:var(--muted);margin-bottom:8px">${lead.email||''} ${lead.company ? '· '+lead.company : ''}</p>
      ${sectionHdr('Linked Contact')}
      ${contact ? relRow(`${contact.first_name} ${contact.last_name||''}`, contact.email||'',
        `<button class="btn btn-sm btn-ghost" onclick="openContactDetail(${contact.id})">View</button>`) :
        `<p style="color:var(--muted);font-size:12px">None</p><button class="btn btn-sm btn-ghost" style="margin-top:4px" onclick="linkLeadFK('contact',${id})">+ Link Contact</button>`}
      ${sectionHdr('Linked Account')}
      ${account ? relRow(account.name, account.domain||'',
        `<button class="btn btn-sm btn-ghost" onclick="openAccountDetail(${account.id})">View</button>`) :
        `<p style="color:var(--muted);font-size:12px">None</p><button class="btn btn-sm btn-ghost" style="margin-top:4px" onclick="linkLeadFK('account',${id})">+ Link Account</button>`}
      ${sectionHdr('Linked Project')}
      ${project ? relRow(project.name, badge(project.status,'badge-gray'),
        `<button class="btn btn-sm btn-ghost" onclick="openProjectDetail(${project.id})">View</button>`) :
        '<p style="color:var(--muted);font-size:12px">None – convert this lead to create a project.</p>'}
      ${sectionHdr('Stakeholders ('+stakeholders.length+')')}
      ${relList(stakeholders.map(s => relRow(s.name, s.role||'',
        `<button class="btn btn-sm btn-ghost" onclick="openStakeholderDetail(${s.id})">View</button>`)))}
      <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
        <button class="btn btn-ghost" onclick="convertLead(${id})">Convert Lead</button>
        <button class="btn btn-ghost" onclick="closeModal()">Close</button>
      </div>
    </div>`);
}

async function linkLeadFK(entityType, leadId) {
  const items = await api('GET', `/${entityType}s?limit=500`).catch(() => []);
  const opts = items.map(e => {
    const lbl = e.first_name ? `${e.first_name} ${e.last_name||''} (${e.email||'#'+e.id})` : (e.name||'#'+e.id);
    return `<option value="${e.id}">${lbl}</option>`;
  }).join('');
  openModal(`Link ${entityType} to Lead`, `
    <form id="crm-form">
      <div class="form-group"><label>Select ${entityType}</label>
        <select name="eid">${opts}</select>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Link</button>
      </div>
    </form>`, async (e) => {
    const eid = new FormData(e.target).get('eid');
    await api('PATCH', `/leads/${leadId}/link/${entityType}/${eid}`);
    toast('Linked'); openLeadDetail(leadId);
  });
}

// ── Project detail ────────────────────────────────────────────────────────────

async function openProjectDetail(id) {
  const [proj, contacts, stakeholders] = await Promise.all([
    api('GET', `/projects/${id}`),
    api('GET', `/projects/${id}/contacts`).catch(() => []),
    api('GET', `/projects/${id}/stakeholders`).catch(() => []),
  ]);
  const account = await api('GET', `/projects/${id}/account`).catch(() => null);
  const lead = await api('GET', `/projects/${id}/lead`).catch(() => null);
  const cycle = proj.sales_cycle;
  openModal(proj.name, `
    <div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
        ${badge(proj.status, proj.status==='active'?'badge-green':proj.status==='closed'?'badge-red':'badge-gray')}
        ${proj.value ? `<span style="font-size:12px;color:var(--muted)">$${Number(proj.value).toLocaleString()} ${proj.currency||'USD'}</span>` : ''}
        ${cycle ? badge(cycle.stage, STAGE_COLORS[cycle.stage]||'badge-gray') : ''}
        ${cycle ? `<span style="font-size:12px;color:var(--muted)">${cycle.probability}%</span>` : ''}
      </div>
      ${sectionHdr('Account')}
      ${account ? relRow(account.name, account.domain||'',
        `<button class="btn btn-sm btn-ghost" onclick="openAccountDetail(${account.id})">View</button>`) :
        `<p style="color:var(--muted);font-size:12px">None</p><button class="btn btn-sm btn-ghost" style="margin-top:4px" onclick="linkProjectFK('account',${id})">+ Link Account</button>`}
      ${sectionHdr('Lead')}
      ${lead ? relRow(lead.title, badge(lead.status,LEAD_COLORS[lead.status]||'badge-gray'),
        `<button class="btn btn-sm btn-ghost" onclick="openLeadDetail(${lead.id})">View</button>`) :
        `<p style="color:var(--muted);font-size:12px">None</p><button class="btn btn-sm btn-ghost" style="margin-top:4px" onclick="linkProjectFK('lead',${id})">+ Link Lead</button>`}
      ${sectionHdr('Contacts ('+contacts.length+')')}
      ${relList(contacts.map(c => relRow(`${c.first_name} ${c.last_name||''}`, c.email||'',
        `<button class="btn btn-sm btn-ghost" onclick="openContactDetail(${c.id})">View</button>
         <button class="btn btn-sm btn-danger" onclick="unlinkThen('projects',${id},'contact',${c.id},openProjectDetail)">Unlink</button>`)))}
      <button class="btn btn-sm btn-ghost" style="margin-top:6px" onclick="linkEntityModal('projects',${id},'contact','contacts',openProjectDetail)">+ Link Contact</button>
      ${sectionHdr('Stakeholders ('+stakeholders.length+')')}
      ${relList(stakeholders.map(s => relRow(s.name, s.role||s.email||'',
        `<button class="btn btn-sm btn-ghost" onclick="openStakeholderDetail(${s.id})">View</button>
         <button class="btn btn-sm btn-danger" onclick="unlinkThen('projects',${id},'stakeholder',${s.id},openProjectDetail)">Unlink</button>`)))}
      <button class="btn btn-sm btn-ghost" style="margin-top:6px" onclick="linkEntityModal('projects',${id},'stakeholder','stakeholders',openProjectDetail)">+ Link Stakeholder</button>
      <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
        <button class="btn btn-ghost" onclick="identifyStakeholders(${id})">Find Stakeholders</button>
        <button class="btn btn-ghost" onclick="closeModal()">Close</button>
      </div>
    </div>`);
}

async function linkProjectFK(entityType, projectId) {
  const items = await api('GET', `/${entityType}s?limit=500`).catch(() => []);
  const opts = items.map(e => `<option value="${e.id}">${e.title||e.name||'#'+e.id}</option>`).join('');
  openModal(`Link ${entityType} to Project`, `
    <form id="crm-form">
      <div class="form-group"><label>Select ${entityType}</label>
        <select name="eid">${opts}</select>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Link</button>
      </div>
    </form>`, async (e) => {
    const eid = new FormData(e.target).get('eid');
    await api('PATCH', `/projects/${projectId}/link/${entityType}/${eid}`);
    toast('Linked'); openProjectDetail(projectId);
  });
}

// ── Stakeholder detail ────────────────────────────────────────────────────────

async function openStakeholderDetail(id) {
  const s = await api('GET', `/stakeholders/${id}`);
  const projects = await api('GET', `/stakeholders/${id}/projects`).catch(() => []);
  const account = await api('GET', `/stakeholders/${id}/account`).catch(() => null);
  const lead = await api('GET', `/stakeholders/${id}/lead`).catch(() => null);
  const contact = await api('GET', `/stakeholders/${id}/contact`).catch(() => null);
  let signals = []; try { signals = JSON.parse(s.buying_signals||'[]'); } catch {}
  const initials = (s.name||'?').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase();
  openModal(s.name, `
    <div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
        ${badge(s.influence_level||'unknown', s.influence_level==='high'?'badge-red':s.influence_level==='medium'?'badge-yellow':'badge-gray')}
        ${badge(s.sentiment||'neutral', s.sentiment==='positive'?'badge-green':s.sentiment==='negative'?'badge-red':'badge-gray')}
        ${s.role ? badge(s.role,'badge-blue') : ''}
        ${s.ai_enriched_at ? '<span style="font-size:11px;color:var(--accent)">✦ AI enriched</span>' : ''}
      </div>
      ${s.ai_summary ? `<div style="background:var(--surface2);border-left:3px solid var(--accent);border-radius:4px;padding:8px 12px;margin-bottom:8px;font-size:12.5px">${s.ai_summary}</div>` : ''}
      ${signals.length ? `<div style="margin-bottom:8px"><span style="font-size:10px;color:var(--warning);text-transform:uppercase">Buying Signals: </span>${signals.map(sig=>`<span class="skill-tag" style="border-color:var(--warning);color:var(--warning)">${sig}</span>`).join(' ')}</div>` : ''}
      ${sectionHdr('Account')}
      ${account ? relRow(account.name, account.domain||'',
        `<button class="btn btn-sm btn-ghost" onclick="openAccountDetail(${account.id})">View</button>`) :
        `<p style="color:var(--muted);font-size:12px">None</p><button class="btn btn-sm btn-ghost" style="margin-top:4px" onclick="linkStakeholderFK('account',${id})">+ Link Account</button>`}
      ${sectionHdr('Lead')}
      ${lead ? relRow(lead.title, badge(lead.status,LEAD_COLORS[lead.status]||'badge-gray'),
        `<button class="btn btn-sm btn-ghost" onclick="openLeadDetail(${lead.id})">View</button>`) :
        `<p style="color:var(--muted);font-size:12px">None</p><button class="btn btn-sm btn-ghost" style="margin-top:4px" onclick="linkStakeholderFK('lead',${id})">+ Link Lead</button>`}
      ${sectionHdr('Contact')}
      ${contact ? relRow(`${contact.first_name} ${contact.last_name||''}`, contact.email||'',
        `<button class="btn btn-sm btn-ghost" onclick="openContactDetail(${contact.id})">View</button>`) :
        `<p style="color:var(--muted);font-size:12px">None</p><button class="btn btn-sm btn-ghost" style="margin-top:4px" onclick="linkStakeholderFK('contact',${id})">+ Link Contact</button>`}
      ${sectionHdr('Projects ('+projects.length+')')}
      ${relList(projects.map(p => relRow(p.name, badge(p.status,'badge-gray'),
        `<button class="btn btn-sm btn-ghost" onclick="openProjectDetail(${p.id})">View</button>
         <button class="btn btn-sm btn-danger" onclick="unlinkStakeholderProject(${id},${p.id})">Unlink</button>`)))}
      <button class="btn btn-sm btn-ghost" style="margin-top:6px" onclick="linkEntityModal('stakeholders',${id},'project','projects',openStakeholderDetail)">+ Link Project</button>
      <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end">
        ${s.linkedin_url ? `<button class="btn btn-ghost" onclick="closeModal();rescanLinkedIn('stakeholder',${id},'${s.linkedin_url}')">Re-scan LinkedIn</button>` : `<button class="btn btn-ghost" onclick="closeModal();scanLinkedIn('stakeholder',${id})">Add LinkedIn</button>`}
        <button class="btn btn-ghost" onclick="closeModal()">Close</button>
      </div>
    </div>`);
}

async function unlinkStakeholderProject(stakeholderId, projectId) {
  try {
    await api('DELETE', `/stakeholders/${stakeholderId}/unlink/project/${projectId}`);
    toast('Unlinked'); openStakeholderDetail(stakeholderId);
  } catch(e) { toast(e.message, false); }
}

async function linkStakeholderFK(entityType, stakeholderId) {
  const items = await api('GET', `/${entityType}s?limit=500`).catch(() => []);
  const opts = items.map(e => {
    const lbl = e.first_name ? `${e.first_name} ${e.last_name||''} (${e.email||'#'+e.id})` : (e.title||e.name||'#'+e.id);
    return `<option value="${e.id}">${lbl}</option>`;
  }).join('');
  openModal(`Link ${entityType} to Stakeholder`, `
    <form id="crm-form">
      <div class="form-group"><label>Select ${entityType}</label>
        <select name="eid">${opts}</select>
      </div>
      <div class="form-actions">
        <button type="button" class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Link</button>
      </div>
    </form>`, async (e) => {
    const eid = new FormData(e.target).get('eid');
    await api('PATCH', `/stakeholders/${stakeholderId}/link/${entityType}/${eid}`);
    toast('Linked'); openStakeholderDetail(stakeholderId);
  });
}

// ── Router ────────────────────────────────────────────────────────────────────

const ADD_HANDLERS = {
  dashboard:    null,
  leads:        addLeadForm,
  contacts:     addContactForm,
  accounts:     addAccountForm,
  projects:     addProjectForm,
  stakeholders: addStakeholderForm,
  pipeline:     null,
  emails:       addEmailForm,
};

const PAGE_TITLES = {
  dashboard: 'Dashboard', leads: 'Leads', contacts: 'Contacts',
  accounts: 'Accounts', projects: 'Projects', stakeholders: 'Stakeholders',
  pipeline: 'Pipeline', emails: 'Emails',
};

let currentPage = 'dashboard';

async function navigate(page) {
  currentPage = page;

  document.querySelectorAll('.nav-item').forEach(el =>
    el.classList.toggle('active', el.dataset.page === page));

  document.getElementById('page-title').textContent = PAGE_TITLES[page] || page;

  const addBtn = document.getElementById('btn-add');
  addBtn.style.display = ADD_HANDLERS[page] ? 'inline-block' : 'none';

  const content = document.getElementById('app-content');
  content.innerHTML = '<p style="color:var(--muted)">Loading…</p>';

  try {
    const renderers = {
      dashboard:    renderDashboard,
      leads:        renderLeads,
      contacts:     renderContacts,
      accounts:     renderAccounts,
      projects:     renderProjects,
      stakeholders: renderStakeholders,
      pipeline:     renderPipeline,
      emails:       renderEmails,
    };
    content.innerHTML = await (renderers[page] || renderDashboard)();
  } catch (err) {
    content.innerHTML = `<p style="color:var(--danger)">Error: ${err.message}</p>`;
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Nav clicks
  document.querySelectorAll('.nav-item').forEach(el =>
    el.addEventListener('click', () => navigate(el.dataset.page)));

  // Add button
  document.getElementById('btn-add').addEventListener('click', () => {
    ADD_HANDLERS[currentPage]?.();
  });

  // Modal close
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
  });

  navigate('dashboard');
});
