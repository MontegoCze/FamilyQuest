import { FormEvent, useEffect, useMemo, useState } from 'react';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';
type User = { id: string; email: string; full_name: string; role: 'parent' | 'child'; avatar?: string };
type Task = { id: string; title: string; description?: string; category?: string; difficulty?: number; xp: number; due_date?: string; assignments: { user_id: string; user_name?: string }[]; completions: { id: string; user_id: string; status: string; notes?: string; completed_at?: string }[] };
type Stats = { user_id: string; total_tasks_completed: number; total_xp: number; level: number; xp_in_level: number; xp_for_next_level: number; average_rating: number; current_streak: number; achievements_count: number; pending_completions: number };
type Member = { id: string; user_id: string; family_id: string; full_name?: string; email?: string; role: 'parent' | 'child'; avatar?: string; is_active?: boolean };
type Notification = { id: string; title: string; message: string; is_read: boolean };
type Invitation = { id: string; invited_email: string; invited_name: string; role: 'parent' | 'child'; status: string; expires_at: string; token: string };
type Achievement = { id: string; name: string; icon: string; description: string; requirement?: string; xp_reward?: number; is_unlocked: boolean; progress: number };
type Reward = { id: string; name: string; description?: string; cost: number };
type Redemption = { id: string; reward_id: string; user_id: string; status: string; requested_at: string; reward_name?: string; reward_cost?: number };
type AdventurePoint = { id: string; title: string; name?: string; description?: string; icon: string; image?: string; position_x: number; position_y: number; order_index: number; required_xp: number; required_level?: number; reward_xp: number; is_active: boolean; status: 'locked' | 'current' | 'completed' };
const defaultAdventurePoints: AdventurePoint[] = [
  { id: 'default-start', title: 'Zahájení cesty', description: 'Vydej se na svou první výpravu.', icon: '🏠', position_x: 14, position_y: 82, order_index: 0, required_xp: 0, reward_xp: 50, is_active: true, status: 'completed' },
  { id: 'default-steps', title: 'První krůčky', description: 'Každý splněný úkol tě posune dál.', icon: '🌱', position_x: 28, position_y: 68, order_index: 1, required_xp: 50, reward_xp: 75, is_active: true, status: 'current' },
  { id: 'default-cave', title: 'Tajná jeskyně', description: 'Objev skryté místo na své mapě.', icon: '🪨', position_x: 20, position_y: 48, order_index: 2, required_xp: 100, reward_xp: 100, is_active: true, status: 'locked' },
  { id: 'default-forest', title: 'Lesní průsmyk', description: 'Projdi kouzelným lesem.', icon: '🌲', position_x: 44, position_y: 55, order_index: 3, required_xp: 250, reward_xp: 125, is_active: true, status: 'locked' },
  { id: 'default-waterfall', title: 'Vodopád odvahy', description: 'Překonej další velkou výzvu.', icon: '💧', position_x: 64, position_y: 38, order_index: 4, required_xp: 500, reward_xp: 150, is_active: true, status: 'locked' },
  { id: 'default-guardian', title: 'Strážce hor', description: 'Jsi blízko vrcholu své cesty.', icon: '🏔️', position_x: 49, position_y: 22, order_index: 5, required_xp: 750, reward_xp: 200, is_active: true, status: 'locked' },
  { id: 'default-castle', title: 'Rodinný hrad', description: 'Cílový bod společné výpravy.', icon: '🏰', position_x: 80, position_y: 14, order_index: 6, required_xp: 1000, reward_xp: 250, is_active: true, status: 'locked' },
];
type TaskCategory = 'home' | 'school';
const categoryInfo: Record<TaskCategory, { icon: string; label: string }> = { home: { icon: '🏠', label: 'DOMA' }, school: { icon: '🎒', label: 'ŠKOLA' } };
const normalizeCategory = (category?: string): TaskCategory => category === 'school' ? 'school' : 'home';
function CategoryBadge({ category }: { category?: string }) { const item = categoryInfo[normalizeCategory(category)]; return <span className={`category-badge category-${normalizeCategory(category)}`}>{item.icon} {item.label}</span>; }

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? 'Požadavek se nepodařilo dokončit.');
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

const navItems = [
  { label: 'Dashboard', icon: '⌂', target: '#top' },
  { label: 'Statistiky', icon: '◒', target: '#stats' },
  { label: 'Moje úkoly', icon: '✓', target: '#missions' },
  { label: 'Achievementy', icon: '♛', target: '#achievements' },
  { label: 'Odměny', icon: '♢', target: '#rewards' },
  { label: 'Dobrodružství', icon: '◈', target: '#adventure' },
];
const parentNavItems = [
  { label: 'Dashboard', icon: '⌂', target: '#top' },
  { label: 'Statistiky', icon: '◒', target: '#stats' },
  { label: 'Moje úkoly', icon: '✓', target: '#missions' },
  { label: 'Správa účtů', icon: '👤', target: '#accounts' },
  { label: 'Achievementy', icon: '♛', target: '#achievements' },
  { label: 'Odměny', icon: '♢', target: '#rewards' },
  { label: 'Dobrodružství', icon: '◈', target: '#adventure' },
];
const mobileItems = [
  { label: 'Domů', icon: '⌂', target: '#top' },
  { label: 'Úkoly', icon: '✓', target: '#missions' },
  { label: 'Achievementy', icon: '♛', target: '#achievements' },
  { label: 'Odměny', icon: '♢', target: '#rewards' },
  { label: 'Dobrodružství', icon: '◈', target: '#adventure' },
  { label: 'Profil', icon: '◉', target: '#profile' },
];
const achievementRatio = (item: Achievement) => item.progress / Math.max(1, Number(item.requirement?.match(/\d+/)?.[0] ?? 1));

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('familyquest_token'));
  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState('');
  const invitationToken = window.location.pathname.match(/^\/invite\/([^/]+)$/)?.[1];

  useEffect(() => {
    if (!token) return;
    request<User>('/auth/me', {}, token).then(setUser).catch(() => { localStorage.removeItem('familyquest_token'); setToken(null); }).finally(() => setLoading(false));
  }, [token]);

  const signOut = () => { localStorage.removeItem('familyquest_token'); setToken(null); setUser(null); };
  const completeLogin = (nextToken: string, nextUser: User) => { localStorage.setItem('familyquest_token', nextToken); setToken(nextToken); setUser(nextUser); };
  if (invitationToken) return <InviteScreen token={invitationToken} authToken={token} onLogin={completeLogin} />;
  if (!token) return <AuthScreen mode={authMode} setMode={setAuthMode} onLogin={completeLogin} error={error} setError={setError} />;
  if (loading) return <div className="loading"><div className="loading-spinner">✦</div><span>Načítám FamilyQuest…</span></div>;
  if (!user) return <AuthScreen mode={authMode} setMode={setAuthMode} onLogin={completeLogin} error={error} setError={setError} />;
  return <Dashboard user={user} token={token} onLogout={signOut} />;
}

function AuthScreen({ mode, setMode, onLogin, error, setError }: { mode: 'login' | 'register'; setMode: (mode: 'login' | 'register') => void; onLogin: (token: string, user: User) => void; error: string; setError: (value: string) => void }) {
  const [showPassword, setShowPassword] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError('');
    const form = new FormData(event.currentTarget);
    try {
      const payload = { email: String(form.get('email')), password: String(form.get('password')), full_name: String(form.get('full_name') ?? '') };
      if (mode === 'register') await request('/auth/register', { method: 'POST', body: JSON.stringify(payload) });
      const login = await request<{ access_token: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ email: payload.email, password: payload.password }) });
      onLogin(login.access_token, await request<User>('/auth/me', {}, login.access_token));
    } catch (err) { setError(err instanceof Error ? err.message : 'Přihlášení se nezdařilo.'); }
  };
  return <main className="auth-layout">
    <section className="brand-panel">
      <div className="brand-lockup">
        <svg className="brand-mark" viewBox="0 0 180 180" role="img" aria-label="FamilyQuest logo">
          <defs><linearGradient id="mark-gradient" x1="20%" y1="0%" x2="80%" y2="100%"><stop stopColor="#ce6bff" /><stop offset="1" stopColor="#5b2ce8" /></linearGradient></defs>
          <path fill="url(#mark-gradient)" d="M90 11 22 69v39c0 5 3 10 8 12l60 38 60-38c5-2 8-7 8-12V69L90 11Z" />
          <path fill="#0b082b" d="m90 39-45 38v22l45 29 45-29V77L90 39Z" />
          <g fill="url(#mark-gradient)"><circle cx="61" cy="82" r="17" /><circle cx="119" cy="82" r="17" /><circle cx="90" cy="101" r="12" /><path d="M32 119c0-19 12-31 28-31s28 12 28 31l-28 22-28-22Zm60 0c0-19 12-31 28-31s28 12 28 31l-28 22-28-22Z" /></g>
          <path fill="#0b082b" d="m90 150-21-18c-19-16-17-33-4-40 11-6 21 1 25 10 4-9 14-16 25-10 13 7 15 24-4 40l-21 18Z" />
          <g fill="#ce6bff"><rect x="78" y="53" width="8" height="8" rx="1" /><rect x="94" y="53" width="8" height="8" rx="1" /><rect x="78" y="65" width="8" height="8" rx="1" /><rect x="94" y="65" width="8" height="8" rx="1" /></g>
        </svg>
        <strong>FamilyQuest</strong>
        <span>ÚKOLY. ORGANIZACE. RODINA.</span>
      </div>
    </section>
    <section className="auth-stage">
      <div className="auth-intro">
        <svg className="intro-mark" viewBox="0 0 90 90" aria-hidden="true"><path fill="#5c35df" d="M45 5 15 31v25c0 3 2 6 5 8l25 15 25-15c3-2 5-5 5-8V31L45 5Z" /><path fill="#fff" d="m45 20-19 16v14l19 11 19-11V36L45 20Z" /><circle cx="35" cy="40" r="5" fill="#5c35df" /><circle cx="55" cy="40" r="5" fill="#5c35df" /><path fill="#5c35df" d="M45 48c-8 0-15 6-15 13l15 9 15-9c0-7-7-13-15-13Z" /></svg>
        <h1>Každý úkol<br />je malé<br /><em>dobrodružství.</em></h1>
        <p className="intro-lead">Proměňte domácí povinnosti<br />v týmovou hru plnou odměn.</p>
        <div className="feature-list">
          <div className="feature-item"><span className="feature-icon">♟</span><div><strong>Společně</strong><small>Zapojíte celou rodinu<br />a spolupracujete.</small></div></div>
          <div className="feature-item"><span className="feature-icon">★</span><div><strong>S radostí</strong><small>Motivujte a odměňujte<br />za každý úspěch.</small></div></div>
        </div>
      </div>
      <section className="auth-card">
        <p className="eyebrow">Vítejte zpět</p>
        <h2>{mode === 'login' ? <>Přihlaste se<br />do rodiny</> : 'Vytvořte účet rodiče'}</h2>
        <form onSubmit={submit}>
          {mode === 'register' && <label>Jméno<input name="full_name" required minLength={2} autoComplete="name" /></label>}
          <label>E-mail<input name="email" type="email" placeholder="zadejte svůj e-mail" required autoComplete="email" /></label>
          <label>Heslo<span className="password-field"><input name="password" type={showPassword ? 'text' : 'password'} placeholder="zadejte své heslo" required minLength={8} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} /><button type="button" className="password-toggle" aria-label={showPassword ? 'Skrýt heslo' : 'Zobrazit heslo'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? '◉' : '◌'}</button></span></label>
          {error && <p className="error">{error}</p>}
          <button className="primary" type="submit">{mode === 'login' ? 'Přihlásit se' : 'Zaregistrovat se'}</button>
        </form>
        <button className="link-button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>{mode === 'login' ? 'Nemáte účet? Zaregistrujte se' : 'Už účet máte? Přihlaste se'}</button>
      </section>
      <div className="landscape" aria-hidden="true"><div className="sunset-hill hill-back" /><div className="sunset-hill hill-mid" /><div className="sunset-hill hill-front" /><div className="house"><i /><b /><span /></div><div className="road" /></div>
    </section>
  </main>;
}

function Dashboard({ user, token, onLogout }: { user: User; token: string; onLogout: () => void }) {
  return user.role === 'child' ? <ChildDashboard user={user} token={token} onLogout={onLogout} /> : <ParentDashboard user={user} token={token} onLogout={onLogout} />;
}

function DashboardSidebar({ user, familyName, onLogout }: { user: User; familyName: string; onLogout: () => void }) {
  const items = user.role === 'parent' ? parentNavItems : navItems;
  const [activeTarget, setActiveTarget] = useState(window.location.hash || '#top');
  useEffect(() => {
    const updateActiveTarget = () => setActiveTarget(window.location.hash || '#top');
    window.addEventListener('hashchange', updateActiveTarget);
    updateActiveTarget();
    return () => window.removeEventListener('hashchange', updateActiveTarget);
  }, []);
  return <aside className="dashboard-sidebar"><a className="sidebar-brand" href="#top"><span className="logo small">✦</span><span><strong>FamilyQuest</strong><small>{familyName}</small></span></a><nav className="sidebar-nav" aria-label="Hlavní navigace">{items.map((item) => <a className={activeTarget === item.target ? 'active' : ''} href={item.target} key={item.label}><span>{item.icon}</span>{item.label}</a>)}</nav><div className="sidebar-footer"><a className={activeTarget === '#profile' ? 'active' : ''} href="#profile"><span>◉</span> Profil</a><button onClick={onLogout}><span>↪</span> Odhlásit se</button><div className="sidebar-user"><span className="user-avatar">{user.avatar || user.full_name.charAt(0)}</span><span><strong>{user.full_name}</strong><small>{user.role === 'parent' ? 'Rodič' : 'Dobrodruh'}</small></span></div></div></aside>;
}

function MobileNav({ role }: { role: 'parent' | 'child' }) {
  const [activeTarget, setActiveTarget] = useState(window.location.hash || '#top');
  useEffect(() => {
    const updateActiveTarget = () => setActiveTarget(window.location.hash || '#top');
    window.addEventListener('hashchange', updateActiveTarget);
    updateActiveTarget();
    return () => window.removeEventListener('hashchange', updateActiveTarget);
  }, []);
  return <nav className="mobile-nav" aria-label="Mobilní navigace">{mobileItems.map((item) => <a className={activeTarget === item.target ? 'active' : ''} href={item.target} key={`${role}-${item.label}`}><span>{item.icon}</span><small>{item.label}</small></a>)}</nav>;
}

function ParentDashboard({ user, token, onLogout }: { user: User; token: string; onLogout: () => void }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [leaderboard, setLeaderboard] = useState<Stats[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [redemptions, setRedemptions] = useState<Redemption[]>([]);
  const [adventurePoints, setAdventurePoints] = useState<AdventurePoint[]>(defaultAdventurePoints);
  const [family, setFamily] = useState<{ name: string } | null>(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState<'main' | 'accounts'>('main');
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [showMemberForm, setShowMemberForm] = useState(false);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<'all' | TaskCategory>('all');
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const children = useMemo(() => members.filter((member) => member.role === 'child'), [members]);
  const removeMember = async (member: Member) => {
    if (member.user_id === user.id || !window.confirm(`Opravdu chcete odebrat ${member.full_name ?? member.email} z rodiny?`)) return;
    try { await request(`/family/members/${member.user_id}`, { method: 'DELETE' }, token); setMessage('Člen byl odebrán z rodiny. Historická data zůstala zachována.'); refresh(); }
    catch (err) { setMessage(err instanceof Error ? err.message : 'Člena se nepodařilo odebrat.'); }
  };

  const refresh = async () => {
    try {
      const [nextTasks, nextStats, nextMembers, nextNotifications, nextAchievements, nextFamily, nextRewards, nextRedemptions, nextLeaderboard, nextAdventurePoints, nextInvitations] = await Promise.all([
        request<Task[]>('/tasks', {}, token), request<Stats>('/stats', {}, token), request<Member[]>('/family/members', {}, token),
        request<Notification[]>('/notifications', {}, token), request<Achievement[]>('/achievements', {}, token), request<{ name: string } | null>('/family', {}, token),
        request<Reward[]>('/rewards', {}, token), request<Redemption[]>('/redemptions', {}, token), request<Stats[]>('/leaderboard', {}, token), request<AdventurePoint[]>('/adventure', {}, token), request<Invitation[]>('/family/invitations', {}, token),
      ]);
      setTasks(nextTasks); setStats(nextStats); setMembers(nextMembers); setNotifications(nextNotifications); setAchievements(nextAchievements); setFamily(nextFamily); setRewards(nextRewards); setRedemptions(nextRedemptions); setLeaderboard(nextLeaderboard); setAdventurePoints(nextAdventurePoints); setInvitations(nextInvitations);
    } catch (err) { setMessage(err instanceof Error ? err.message : 'Data se nepodařilo načíst.'); } finally { setLoading(false); }
  };
  useEffect(() => { refresh(); }, []);

  const complete = async (taskId: string) => { try { await request(`/tasks/${taskId}/complete`, { method: 'POST', body: JSON.stringify({}) }, token); setMessage('Úkol odeslán ke schválení.'); refresh(); } catch (err) { setMessage(err instanceof Error ? err.message : 'Úkol se nepodařilo dokončit.'); } };
  const review = async (completionId: string, status: 'approved' | 'rejected', notes?: string) => { try { await request(`/completions/${completionId}/review`, { method: 'POST', body: JSON.stringify({ status, notes: notes || null }) }, token); setMessage(status === 'rejected' ? 'Úkol byl vrácen dítěti k přepracování.' : 'Úkol byl schválen.'); refresh(); } catch (err) { setMessage(err instanceof Error ? err.message : 'Schválení se nezdařilo.'); } };
  const reviewReward = async (id: string, status: 'approved' | 'rejected') => { try { await request(`/redemptions/${id}/review`, { method: 'POST', body: JSON.stringify({ status }) }, token); setMessage(status === 'approved' ? 'Odměna byla schválena.' : 'Žádost o odměnu byla zamítnuta.'); refresh(); } catch (err) { setMessage(err instanceof Error ? err.message : 'Odměnu se nepodařilo zpracovat.'); } };
  const markRead = async (id: string) => { await request(`/notifications/${id}/read`, { method: 'POST' }, token); setNotifications(notifications.map((item) => item.id === id ? { ...item, is_read: true } : item)); };
  const createFamily = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const name = new FormData(event.currentTarget).get('name'); try { await request('/family', { method: 'POST', body: JSON.stringify({ name }) }, token); refresh(); } catch (err) { setMessage(err instanceof Error ? err.message : 'Rodinu se nepodařilo vytvořit.'); } };

  const pendingReviews = tasks.flatMap((task) => task.completions.filter((completion) => completion.status === 'pending').map((completion) => ({ task, completion, name: task.assignments.find((assignment) => assignment.user_id === completion.user_id)?.user_name ?? 'Člen rodiny' })));
  const completedToday = tasks.filter((task) => task.completions.some((completion) => completion.status === 'approved')).length;
  const totalXp = leaderboard.reduce((sum, item) => sum + item.total_xp, 0) || stats?.total_xp || 0;
  const visibleTasks = categoryFilter === 'all' ? tasks : tasks.filter((task) => normalizeCategory(task.category) === categoryFilter);

  if (!family && !loading) return <main className="app-shell"><DashboardSidebar user={user} familyName="Vaše rodina" onLogout={onLogout} /><div className="dashboard-main"><section className="setup-card"><span className="setup-icon">✦</span><p className="eyebrow">Začněme spolu</p><h1>Vytvořte svou rodinu</h1><p className="muted">Pojmenujte rodinu a pak pozvěte děti do společného dobrodružství.</p><form onSubmit={createFamily}><input name="name" required minLength={2} placeholder="Např. Novákovi" /><button className="primary" type="submit">Vytvořit rodinu</button></form></section></div></main>;
  return <main className="app-shell" id="top"><DashboardSidebar user={user} familyName={family?.name ?? 'Vaše rodina'} onLogout={onLogout} /><div className="dashboard-main"><div className="dashboard-content"><header className="page-heading"><div><p className="eyebrow">Rodičovský přehled</p><h1>Ahoj, {user.full_name.split(' ')[0]} 👋</h1><p className="muted">Tady je dnešní přehled rodiny.</p></div><div className="heading-actions"><button className="secondary" onClick={() => setShowMemberForm(true)}>+ Přidat člena</button><button className="primary" onClick={() => setShowTaskForm(true)}>+ Nový úkol</button></div></header>{message && <p className="notice">{message}</p>}{(showTaskForm || editingTask) && <TaskForm token={token} children={children} task={editingTask} onDone={() => { setShowTaskForm(false); setEditingTask(null); refresh(); }} />}{showMemberForm && <MemberForm token={token} onDone={() => { setShowMemberForm(false); refresh(); }} />}{loading ? <DashboardSkeleton /> : <><section className="stats-grid" id="stats"><Stat label="Členové rodiny" value={String(members.length)} icon="♧" tone="purple" /><Stat label="Splněné úkoly" value={String(completedToday)} icon="✓" tone="green" /><Stat label="Získané XP" value={String(totalXp)} icon="✦" tone="amber" /><Stat label="Čeká na hodnocení" value={String(pendingReviews.length)} icon="◷" tone="rose" /></section><section className="panel family-members-panel" id="accounts"><div className="panel-heading"><div><p className="eyebrow">Rodina</p><h2>Členové rodiny</h2></div></div><div className="family-members-grid">{members.map((member) => <article className="family-member-card" key={member.user_id}><span className="user-avatar child-avatar">{member.avatar || (member.full_name ?? '?').charAt(0)}</span><div><strong>{member.full_name ?? member.email}</strong><small>{member.role === 'parent' ? 'Rodič' : 'Dítě'} · {member.email}</small></div><button className="danger compact" onClick={() => removeMember(member)} disabled={member.user_id === user.id}>Odebrat</button></article>)}</div></section>{invitations.length > 0 && <section className="panel invitation-panel"><div className="panel-heading"><div><p className="eyebrow">Čekající pozvánky</p><h2>Pozvánky do rodiny</h2></div></div>{invitations.map((invitation) => <article className="invitation-row" key={invitation.id}><div><strong>{invitation.invited_email}</strong><small>{invitation.role === 'parent' ? 'Rodič' : 'Dítě'} · čeká na přijetí</small></div><button className="secondary compact" onClick={async () => { try { await request(`/family/invitations/${invitation.id}/resend`, { method: 'POST' }, token); setMessage('Pozvánka byla znovu odeslána.'); } catch (err) { setMessage(err instanceof Error ? err.message : 'Pozvánku se nepodařilo odeslat.'); } }}>Znovu odeslat</button><button className="danger compact" onClick={async () => { try { await request(`/family/invitations/${invitation.id}`, { method: 'DELETE' }, token); setMessage('Pozvánka byla zrušena.'); refresh(); } catch (err) { setMessage(err instanceof Error ? err.message : 'Pozvánku se nepodařilo zrušit.'); } }}>Zrušit</button></article>)}</section>}<section className="panel all-tasks-panel" id="missions"><div className="panel-heading"><div><p className="eyebrow">Přehled</p><h2>Všechny rodinné úkoly</h2></div></div>{visibleTasks.length === 0 ? <div className="empty">Zatím nemáte žádné úkoly.</div> : <div className="task-overview-list">{visibleTasks.map((task) => <article className="task-overview-row" key={task.id}><div><strong>{task.title}</strong><small><CategoryBadge category={task.category} /> +{task.xp} XP</small></div><button className="secondary compact" onClick={() => setEditingTask(task)}>Upravit</button></article>)}</div>}</section><AdventureMap points={adventurePoints} totalXp={stats?.total_xp ?? 0} level={stats?.level ?? 1} /><AdventureManager token={token} points={adventurePoints} onChange={refresh} /><AccountManager token={token} members={members} currentUserId={user.id} onRefresh={refresh} /></>}</div></div><MobileNav role="parent" /></main>;
}

function DashboardSkeleton() {
  return <div className="dashboard-skeleton"><div className="skeleton-row"><span /><span /><span /><span /></div><div className="skeleton-large" /><div className="skeleton-columns"><span /><span /></div></div>;
}

function AdventureMap({ points, totalXp, level }: { points: AdventurePoint[]; totalXp: number; level: number }) {
  const [selected, setSelected] = useState<AdventurePoint | null>(null);
  const orderedPoints = [...points].sort((a, b) => a.order_index - b.order_index);
  const routePoints = orderedPoints.map((point) => `${point.position_x},${point.position_y}`).join(' ');
  const activePoint = selected || orderedPoints.find((point) => point.status === 'current') || orderedPoints[orderedPoints.length - 1];
  const targetXp = Math.max(1000, ...orderedPoints.map((point) => point.required_xp));
  const progress = Math.min(100, Math.round((totalXp / targetXp) * 100));
  return <section className="adventure-map-panel" id="adventure">
    <header className="adventure-heading"><div><p className="eyebrow">DOBRODRUŽSTVÍ</p><h2>Objevuj svůj svět</h2><p className="muted">Plň úkoly, získej XP a odemkni nová místa na své cestě.</p></div><span className="adventure-level">Úroveň <strong>{level}</strong></span></header>
    {points.length === 0 ? <div className="child-empty"><span>🧭</span><strong>Mapa se teprve připravuje</strong><p>Rodiče brzy přidají první dobrodružný bod.</p></div> : <><div className="adventure-progress-card"><div><small>TVŮJ POKROK</small><strong>{totalXp} <em>XP</em></strong></div><div className="adventure-progress-track"><span style={{ width: `${progress}%` }} /></div><small>{totalXp} / {targetXp} XP</small></div><div className="adventure-map-canvas" aria-label="Mapa dobrodružství"><div className="map-cloud cloud-one" /><div className="map-cloud cloud-two" /><div className="map-mountain mountain-one" /><div className="map-mountain mountain-two" /><div className="map-lake" /><div className="map-trees"><span>♣</span><span>♣</span><span>♣</span><span>♣</span><span>♣</span></div><svg className="adventure-route" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polyline points={routePoints} /></svg>{orderedPoints.map((point) => <button key={point.id} className={`adventure-point ${point.status}`} style={{ left: `${point.position_x}%`, top: `${point.position_y}%` }} onClick={() => setSelected(point)} aria-label={`${point.title}, ${point.status}`}><span>{point.status === 'locked' ? '🔒' : point.status === 'completed' ? '✓' : point.icon}</span><small>{point.title}<b>{point.required_xp} XP</b></small></button>)}<div className="map-compass" aria-hidden="true">N</div></div><div className="adventure-legend"><span><i className="legend-dot completed" /> Dokončeno</span><span><i className="legend-dot current" /> Aktuální</span><span><i className="legend-dot locked" /> Zamčeno</span></div>{activePoint && <article className="adventure-feature-card"><span className="adventure-feature-icon">{activePoint.status === 'locked' ? '🔒' : activePoint.icon}</span><div><small>DALŠÍ ZASTÁVKA</small><h3>{activePoint.title}</h3><p>{activePoint.description || 'Dokonči další úkol a odemkni toto místo.'}</p></div><div className="adventure-reward"><small>ODMĚNA</small><strong>+{activePoint.reward_xp} XP</strong><span>✦</span></div></article>}{selected && <article className="adventure-detail"><button className="modal-close" onClick={() => setSelected(null)} aria-label="Zavřít">×</button><span className="adventure-detail-icon">{selected.status === 'locked' ? '🔒' : selected.icon}</span><h3>{selected.title}</h3><p>{selected.description || 'Další zastávka na tvé cestě.'}</p><small>{selected.status === 'locked' ? `🔒 Ještě potřebuješ ${Math.max(0, selected.required_xp - totalXp)} XP.` : selected.status === 'completed' ? '✅ Tento bod je dokončený.' : '🟢 Toto je tvůj aktuální bod.'}</small></article>}</>}</section>;
}

function AdventureManager({ points, token, onChange }: { points: AdventurePoint[]; token: string; onChange: () => void }) {
  const [editing, setEditing] = useState<AdventurePoint | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      const payload = { title: String(data.get('title')), description: String(data.get('description') || '') || null, icon: String(data.get('icon') || '🗺️'), image: String(data.get('image') || '') || null, position_x: Number(data.get('position_x') || 50), position_y: Number(data.get('position_y') || 50), required_xp: Number(data.get('required_xp') || 0), required_level: data.get('required_level') ? Number(data.get('required_level')) : null, reward_xp: Number(data.get('reward_xp') || 0), is_active: data.get('is_active') === 'on' };
      await request(editing ? `/adventure/points/${editing.id}` : '/adventure/points', { method: editing ? 'PATCH' : 'POST', body: JSON.stringify(payload) }, token);
      setOpen(false); setEditing(null); setError(''); onChange();
    } catch (err) { setError(err instanceof Error ? err.message : 'Bod se nepodařilo uložit.'); }
  };
  const remove = async (id: string) => { if (!window.confirm('Opravdu odstranit tento bod?')) return; await request(`/adventure/points/${id}`, { method: 'DELETE' }, token); onChange(); };
  const move = async (point: AdventurePoint, direction: -1 | 1) => { const target = [...points].sort((a, b) => a.order_index - b.order_index).findIndex((item) => item.id === point.id) + direction; if (target < 0 || target >= points.length) return; const ordered = [...points].sort((a, b) => a.order_index - b.order_index); [ordered[target], ordered[target - direction]] = [ordered[target - direction], ordered[target]]; await request('/adventure/reorder', { method: 'POST', body: JSON.stringify({ point_ids: ordered.map((item) => item.id) }) }, token); onChange(); };
  return <section className="panel adventure-manager" id="adventure"><div className="panel-heading"><div><p className="eyebrow">🗺️ SPRÁVA DOBRODRUŽSTVÍ</p><h2>Mapa pro děti</h2></div><button className="primary compact" onClick={() => { setEditing(null); setOpen(true); setError(''); }}>+ Přidat point</button></div>{open && <form className="adventure-form" onSubmit={save}><label>Název<input name="title" required minLength={2} defaultValue={editing?.title ?? ''} placeholder="Tajemná jeskyně" /></label><label>Popis<input name="description" defaultValue={editing?.description ?? ''} placeholder="Krátký popis výpravy" /></label><label>Ikona<input name="icon" defaultValue={editing?.icon ?? '🗺️'} /></label><label>Obrázek (URL)<input name="image" defaultValue={editing?.image ?? ''} placeholder="https://…" /></label><label>Požadované XP<input name="required_xp" type="number" min="0" defaultValue={editing?.required_xp ?? 0} /></label><label>Požadovaný level<input name="required_level" type="number" min="1" defaultValue={editing?.required_level ?? ''} /></label><label>Odměna XP<input name="reward_xp" type="number" min="0" defaultValue={editing?.reward_xp ?? 0} /></label><label>X pozice (%)<input name="position_x" type="number" min="0" max="100" defaultValue={editing?.position_x ?? 50} /></label><label>Y pozice (%)<input name="position_y" type="number" min="0" max="100" defaultValue={editing?.position_y ?? 50} /></label><label className="adventure-active"><input name="is_active" type="checkbox" defaultChecked={editing?.is_active ?? true} /> Aktivní</label>{error && <p className="error">{error}</p>}<div className="form-actions"><button type="button" className="secondary" onClick={() => setOpen(false)}>Zrušit</button><button type="submit" className="primary">Uložit point</button></div></form>}{points.length === 0 ? <div className="empty">Zatím nemáte žádné pointy.</div> : <div className="adventure-admin-list">{[...points].sort((a, b) => a.order_index - b.order_index).map((point, index) => <article className="adventure-admin-row" key={point.id}><span className="adventure-admin-icon">{point.icon}</span><div><strong>{index + 1}. {point.title}</strong><small>{point.required_xp} XP{point.required_level ? ` · úroveň ${point.required_level}` : ''} · {point.is_active ? 'Aktivní' : 'Skrytý'}</small></div><span className={`adventure-status ${point.status}`}>{point.status === 'completed' ? '✓ Dokončeno' : point.status === 'current' ? '● Aktuální' : '🔒 Zamčeno'}</span><div className="achievement-admin-actions"><button className="secondary compact" onClick={() => { setEditing(point); setOpen(true); setError(''); }}>Upravit</button><button className="secondary compact" onClick={() => move(point, -1)} disabled={index === 0}>↑</button><button className="secondary compact" onClick={() => move(point, 1)} disabled={index === points.length - 1}>↓</button><button className="danger compact" onClick={() => remove(point.id)}>Smazat</button></div></article>)}</div>}</section>;
}

function AchievementManager({ achievements, token, onChange }: { achievements: Achievement[]; token: string; onChange: () => void }) {
  const [editing, setEditing] = useState<Achievement | null>(null);
  const [open, setOpen] = useState(false);
  const save = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); const payload = { name: String(data.get('name')), icon: String(data.get('icon')), description: String(data.get('description')), requirement: String(data.get('requirement')), xp_reward: Number(data.get('xp_reward') || 0) }; await request(editing ? `/achievements/${editing.id}` : '/achievements', { method: editing ? 'PATCH' : 'POST', body: JSON.stringify(payload) }, token); setOpen(false); setEditing(null); onChange(); };
  const remove = async (id: string) => { if (!window.confirm('Opravdu odstranit tento achievement?')) return; await request(`/achievements/${id}`, { method: 'DELETE' }, token); onChange(); };
  return <section className="panel achievement-manager" id="achievements"><div className="panel-heading"><div><p className="eyebrow">Nastavení gamifikace</p><h2>Achievementy</h2></div><button className="primary compact" onClick={() => { setEditing(null); setOpen(true); }}>+ Nový achievement</button></div>{open && <form className="achievement-form" onSubmit={save}><input name="name" required minLength={2} defaultValue={editing?.name ?? ''} placeholder="Název" /><input name="icon" required defaultValue={editing?.icon ?? '🏆'} placeholder="Ikona" /><input name="description" required minLength={2} defaultValue={editing?.description ?? ''} placeholder="Popis" /><input name="requirement" required defaultValue={editing?.requirement ?? 'Splnit 10 úkolů'} placeholder="Podmínka" /><label>XP odměna<input name="xp_reward" type="number" min="0" defaultValue={editing?.xp_reward ?? 25} /></label><div className="form-actions"><button type="button" className="secondary" onClick={() => { setOpen(false); setEditing(null); }}>Zrušit</button><button type="submit" className="primary">{editing ? 'Uložit změny' : 'Vytvořit achievement'}</button></div></form>}{achievements.length === 0 ? <div className="empty">Zatím nemáte žádné achievementy.</div> : <div className="achievement-admin-list">{achievements.map((item) => <article className="achievement-admin-row" key={item.id}><span className="achievement-admin-icon">{item.icon}</span><div><strong>{item.name}</strong><small>{item.requirement} · +{item.xp_reward} XP</small></div><div className="achievement-admin-actions"><button className="secondary compact" onClick={() => { setEditing(item); setOpen(true); }}>Upravit</button><button className="danger compact" onClick={() => remove(item.id)}>Smazat</button></div></article>)}</div>}</section>;
}

function ChildDashboard({ user, token, onLogout }: { user: User; token: string; onLogout: () => void }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [familyName, setFamilyName] = useState('Naše rodina');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [showAvatarEditor, setShowAvatarEditor] = useState(false);
  const [avatar, setAvatar] = useState(user.avatar || '🧑‍🚀');
  const [categoryFilter, setCategoryFilter] = useState<'all' | TaskCategory>('all');
  const [adventurePoints, setAdventurePoints] = useState<AdventurePoint[]>(defaultAdventurePoints);

  const load = async () => {
    try {
      const [nextTasks, nextStats, nextAchievements, nextRewards, family, nextAdventurePoints] = await Promise.all([request<Task[]>('/tasks', {}, token), request<Stats>('/stats', {}, token), request<Achievement[]>('/achievements', {}, token), request<Reward[]>('/rewards', {}, token), request<{ name: string } | null>('/family', {}, token), request<AdventurePoint[]>('/adventure', {}, token)]);
      setTasks(nextTasks); setStats(nextStats); setAchievements(nextAchievements); setRewards(nextRewards); setAdventurePoints(nextAdventurePoints); if (family) setFamilyName(family.name);
    } catch (err) { setNotice(err instanceof Error ? err.message : 'Nepodařilo se načíst mise.'); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const finish = async (task: Task) => { try { await request(`/tasks/${task.id}/complete`, { method: 'POST', body: JSON.stringify({}) }, token); setNotice(`Mise „${task.title}“ odeslána rodičům ke schválení!`); load(); } catch (err) { setNotice(err instanceof Error ? err.message : 'Misi se nepodařilo dokončit.'); } };
  const redeem = async (reward: Reward) => { try { await request(`/rewards/${reward.id}/redeem`, { method: 'POST', body: JSON.stringify({}) }, token); setNotice(`Žádost o odměnu „${reward.name}“ čeká na schválení.`); } catch (err) { setNotice(err instanceof Error ? err.message : 'Odměnu se nepodařilo vyzvednout.'); } };
  const today = new Date().toISOString().slice(0, 10);
  const todayTasks = tasks.filter((task) => (!task.due_date || task.due_date.startsWith(today)) && (categoryFilter === 'all' || normalizeCategory(task.category) === categoryFilter));
  const completedToday = todayTasks.filter((task) => task.completions.some((item) => item.user_id === user.id && item.status === 'approved')).length;
  const nearest = achievements.filter((item) => !item.is_unlocked).sort((a, b) => achievementRatio(b) - achievementRatio(a))[0];
  const saveAvatar = async (nextAvatar: string) => { try { const updated = await request<User>('/auth/me', { method: 'PATCH', body: JSON.stringify({ avatar: nextAvatar }) }, token); setAvatar(updated.avatar || nextAvatar); setShowAvatarEditor(false); setNotice('Tvůj nový hrdina je připraven!'); } catch (err) { setNotice(err instanceof Error ? err.message : 'Avatar se nepodařilo uložit.'); } };
  const initials = user.full_name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase();
  const xpProgress = stats ? Math.min(100, Math.round((stats.xp_in_level / Math.max(1, stats.xp_for_next_level)) * 100)) : 0;
  const adventureProgress = stats ? stats.total_xp % 500 : 0;

  return <main className="child-shell" id="top"><DashboardSidebar user={user} familyName={familyName} onLogout={onLogout} /><div className="dashboard-main"><header className="mobile-header child-mobile-header"><a className="sidebar-brand" href="#top"><span className="logo small">✦</span><strong>FamilyQuest</strong></a><span className="child-family">{familyName}</span><button className="header-avatar" aria-label="Upravit profil" onClick={() => setShowAvatarEditor(true)}>{avatar || initials}</button></header><div className="child-content"><section className="child-hero" id="profile"><div className="hero-copy"><p className="eyebrow">Ahoj, dobrodruhu!</p><h1>{user.full_name.split(' ')[0]}, dnes to zvládneš. <span>✦</span></h1><p>Dokonči své mise a posuň se o krok blíž k další úrovni.</p></div><button className="hero-avatar hero-avatar-button" onClick={() => setShowAvatarEditor(true)} aria-label="Upravit svého hrdinu"><div className="avatar-glow" /><span>{avatar || initials}</span><small>LVL {stats?.level ?? 1}</small><em>Upravit hrdinu</em></button></section>{showAvatarEditor && <AvatarEditor currentAvatar={avatar} onClose={() => setShowAvatarEditor(false)} onSave={saveAvatar} />}{loading ? <DashboardSkeleton /> : <><section className="child-stats" id="stats"><div className="child-xp-card"><div className="child-card-label"><span>⚡</span><div><small>TVÉ XP</small><strong>{stats?.total_xp ?? 0} XP</strong></div><b>LVL {stats?.level ?? 1}</b></div><div className="child-progress"><span style={{ width: `${xpProgress}%` }} /></div><small className="xp-caption">{stats?.xp_in_level ?? 0} / {stats?.xp_for_next_level ?? 100} XP do další úrovně</small></div><div className="child-stat-tile"><span className="stat-emoji">🔥</span><small>SÉRIE</small><strong>{stats?.current_streak ?? 0} dní</strong><em>Jen tak dál!</em></div><div className="child-stat-tile"><span className="stat-emoji">🏆</span><small>ÚSPĚCHY</small><strong>{stats?.achievements_count ?? achievements.filter((item) => item.is_unlocked).length}</strong><em>Odemčených</em></div></section>{notice && <div className="child-notice">{notice}</div>}<div className="child-main-grid"><section className="missions" id="missions"><div className="child-section-heading"><div><p className="eyebrow">Dnešní dobrodružství</p><h2>Tvé mise <span>{todayTasks.length}</span></h2></div>  <span className="mission-date">DNES</span></div><div className="category-filters child-filters">{[['all','Vše'],['home','🏠 Doma'],['school','🎒 Škola']].map(([value,label]) => <button key={value} className={categoryFilter === value ? 'active' : ''} onClick={() => setCategoryFilter(value as 'all' | TaskCategory)}>{label}</button>)}</div><div className="daily-progress"><div><strong>Dnes</strong><span>{completedToday} / {todayTasks.length} úkolů</span></div><div className="daily-track"><span style={{ width: `${todayTasks.length ? (completedToday / todayTasks.length) * 100 : 100}%` }} /></div><small>{todayTasks.length ? Math.round((completedToday / todayTasks.length) * 100) : 100} % hotovo</small></div>{todayTasks.length === 0 ? <div className="child-empty"><span>🎉</span><strong>Dnes máš volno!</strong><p>Všechny mise jsou splněné.</p></div> : <div className="mission-grid">{todayTasks.map((task, index) => { const completion = task.completions.find((item) => item.user_id === user.id); const status = completion?.status ?? 'ready'; const icons = ['🧹', '📚', '🌱', '✨']; return <article className={`mission-card mission-${(index % 4) + 1} ${status}`} key={task.id}><div className="mission-icon">{icons[index % icons.length]}</div><div className="mission-body"><div className="mission-meta">  <CategoryBadge category={task.category} /><b>+{task.xp} XP</b></div><h3>{task.title}</h3>{task.description && <p>{task.description}</p>}<div className="mission-status">{status === 'pending' ? '🟡 Čeká na schválení' : status === 'approved' ? '🟢 Hotovo' : status === 'rejected' ? '🔴 Zkusit znovu' : '🔵 Čeká na splnění'}</div><button className="mission-action" disabled={status === 'pending' || status === 'approved'} onClick={() => finish(task)}>{status === 'pending' ? 'Čeká na schválení · · ·' : status === 'approved' ? 'Splněno ✓' : status === 'rejected' ? 'Zkusit znovu' : 'Splnit misi  →'}</button></div></article>; })}</div>}</section><aside className="child-side"><section className="motivation-card"><span className="motivation-spark">✦</span><h3>Každá mise se počítá!</h3><p>Ještě <strong>{Math.max(0, (stats?.xp_for_next_level ?? 100) - (stats?.xp_in_level ?? 0))} XP</strong> a jsi na další úrovni.</p><div className="motivation-line" /></section><section className="achievement-preview" id="achievements"><div className="preview-kicker">🏆 DALŠÍ ÚSPĚCH</div>{nearest ? <><h3>{nearest.icon} {nearest.name}</h3><p>{nearest.description}</p><div className="achievement-progress"><span style={{ width: `${Math.min(100, (nearest.progress / Math.max(1, Number(nearest.requirement?.match(/\d+/)?.[0] ?? 1))) * 100)}%` }} /></div><small>{nearest.progress} / {nearest.requirement?.match(/\d+/)?.[0] ?? 1} · Ještě krůček!</small></> : <><h3>🌟 Vše odemčeno!</h3><p>Jsi opravdový hrdina.</p></>}<a className="text-link" href="#achievements">Zobrazit achievementy →</a></section><AdventureMap points={adventurePoints} totalXp={stats?.total_xp ?? 0} level={stats?.level ?? 1} /><section className="reward-card" id="rewards"><div className="child-section-heading"><div><p className="eyebrow">Za odměnu</p><h2>Další poklad</h2></div><span className="chest">🎁</span></div>{rewards.length === 0 ? <p className="muted">Rodiče brzy přidají nové odměny.</p> : rewards.slice(0, 2).map((reward) => <div className="reward-row" key={reward.id}><span>🎁</span><div><strong>{reward.name}</strong><small>{reward.description ?? 'Odměna za skvělou práci'}</small></div><button onClick={() => redeem(reward)} disabled={(stats?.total_xp ?? 0) < reward.cost}>{reward.cost} XP</button></div>)}</section></aside></div></>}</div></div><MobileNav role="child" /></main>;
}

function AvatarEditor({ currentAvatar, onClose, onSave }: { currentAvatar: string; onClose: () => void; onSave: (avatar: string) => void }) {
  const avatars = ['🧑‍🚀', '🦸', '🧙', '🧚', '🦊', '🐼', '🐯', '🐸', '🦄', '🤖', '🐉', '🌟'];
  const [selected, setSelected] = useState(currentAvatar || avatars[0]);
  return <div className="avatar-modal-backdrop" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="avatar-modal" role="dialog" aria-modal="true" aria-labelledby="avatar-title"><button className="modal-close" onClick={onClose} aria-label="Zavřít">×</button><p className="eyebrow">Tvoje postava</p><h2 id="avatar-title">Vytvoř si svého hrdinu</h2><div className="avatar-preview">{selected}</div><p className="avatar-help">Vyber si ikonu, která tě bude provázet tvými misemi.</p><div className="avatar-options" role="radiogroup" aria-label="Výběr avatara">{avatars.map((item) => <button key={item} className={`avatar-option ${selected === item ? 'selected' : ''}`} onClick={() => setSelected(item)} aria-label={`Avatar ${item}`} aria-pressed={selected === item}>{item}</button>)}</div><button className="primary avatar-save" onClick={() => onSave(selected)}>Uložit mého hrdinu</button></section></div>;
}

function Stat({ label, value, icon, tone }: { label: string; value: string; icon: string; tone: string }) { return <div className="stat-card"><span className={`stat-icon ${tone}`}>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></div>; }
function TaskForm({ token, children, task, onDone }: { token: string; children: Member[]; task?: Task | null; onDone: () => void }) {
  const [error, setError] = useState('');
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); try { const payload = { title: data.get('title'), description: data.get('description') || null, category: data.get('category'), xp: Number(data.get('xp') || 10), assignee_ids: data.getAll('assignee_ids') }; await request(task ? `/tasks/${task.id}` : '/tasks', { method: task ? 'PATCH' : 'POST', body: JSON.stringify(payload) }, token); onDone(); } catch (err) { setError(err instanceof Error ? err.message : 'Úkol se nepodařilo uložit.'); } };
  return <form className="task-form" onSubmit={submit}><input name="title" required defaultValue={task?.title ?? ''} placeholder="Např. Uklidit pokoj" /><input name="description" defaultValue={task?.description ?? ''} placeholder="Popis (volitelné)" /><fieldset className="category-picker"><legend>Kategorie úkolu</legend><label className="category-option home"><input type="radio" name="category" value="home" defaultChecked={normalizeCategory(task?.category) === 'home'} required /><span>🏠</span><strong>DOMA</strong><small>Domácí povinnosti</small></label><label className="category-option school"><input type="radio" name="category" value="school" defaultChecked={normalizeCategory(task?.category) === 'school'} required /><span>🎒</span><strong>ŠKOLA</strong><small>Učení a domácí úkoly</small></label></fieldset><div className="form-inline"><label>XP<input name="xp" type="number" min="1" max="10000" defaultValue={task?.xp ?? 10} /></label><label>Komu<select name="assignee_ids" multiple required defaultValue={task?.assignments.map((assignment) => assignment.user_id) ?? []}>{children.map((child) => <option key={child.user_id} value={child.user_id}>{child.full_name}</option>)}</select></label></div>{error && <p className="error">{error}</p>}<button className="primary" type="submit">{task ? 'Uložit úkol' : 'Vytvořit úkol'}</button></form>;
}
function ChildForm({ token, onDone }: { token: string; onDone: () => void }) {
  const [error, setError] = useState('');
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = new FormData(event.currentTarget); try { await request('/family/children', { method: 'POST', body: JSON.stringify({ full_name: data.get('full_name'), email: data.get('email') || null, password: data.get('password') }) }, token); onDone(); } catch (err) { setError(err instanceof Error ? err.message : 'Dítě se nepodařilo přidat.'); } };
  return <form className="task-form" onSubmit={submit}><input name="full_name" required minLength={2} placeholder="Jméno dítěte" /><input name="email" type="email" required placeholder="E-mail dítěte" /><input name="password" type="password" required minLength={8} placeholder="Heslo pro přihlášení (8+ znaků)" />{error && <p className="error">{error}</p>}<button className="primary" type="submit">Přidat dítě</button></form>;
}

function MemberForm({ token, onDone }: { token: string; onDone: () => void }) {
  const [mode, setMode] = useState<'choose' | 'member' | 'invite'>('choose');
  const [role, setRole] = useState<'parent' | 'child'>('child');
  const [error, setError] = useState('');
  const [inviteToken, setInviteToken] = useState('');
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError('');
    const data = new FormData(event.currentTarget);
    try {
      const selectedRole = String(data.get('role') ?? role) as 'parent' | 'child';
      if (mode === 'invite' || selectedRole === 'parent') {
        const invite = await request<Invitation>('/family/invitations', { method: 'POST', body: JSON.stringify({ email: data.get('email'), role: selectedRole, full_name: data.get('full_name') || null }) }, token);
        setInviteToken(invite.token);
      } else {
        await request('/family/members', { method: 'POST', body: JSON.stringify({ role: selectedRole, full_name: data.get('full_name'), email: data.get('email') || null, password: data.get('password') }) }, token);
        onDone();
      }

    } catch (err) { setError(err instanceof Error ? err.message : 'Člena se nepodařilo přidat.'); }
  };
  return <div className="member-modal-backdrop" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) onDone(); }}><section className="member-modal" role="dialog" aria-modal="true" aria-labelledby="member-title"><button className="modal-close" onClick={onDone} aria-label="Zavřít">×</button><p className="eyebrow">Vaše rodina</p><h2 id="member-title">Přidat člena</h2>{mode === 'choose' ? <div className="member-choice"><button className="choice-card" onClick={() => setMode('member')}><strong>+ Přidat existujícího člena</strong><small>Vytvořit účet přímo v rodině</small></button><button className="choice-card" onClick={() => setMode('invite')}><strong>✉ Pozvat nového člena e-mailem</strong><small>Pošleme bezpečný odkaz na registraci</small></button></div> : <form className="task-form member-form" onSubmit={submit}><p className="member-description">{mode === 'invite' ? 'Pošleme pozvánku na e-mail. Nový člen se po registraci automaticky připojí do vaší rodiny.' : 'Vytvořte účet člena přímo v této rodině.'}</p><label>Role<select name="role" value={role} onChange={(event) => setRole(event.target.value as 'parent' | 'child')}><option value="child">Dítě</option><option value="parent">Rodič</option></select></label>{mode === 'invite' ? <label>E-mail<input name="email" type="email" required placeholder="jan@example.com" /></label> : <><input name="full_name" required minLength={2} placeholder="Jméno / přezdívka" /><input name="email" type="email" required={role === 'parent'} placeholder={role === 'parent' ? 'E-mail rodiče' : 'E-mail (volitelné)'} /><input name="password" type="password" required={role === 'child'} minLength={8} placeholder="Heslo pro přihlášení (8+ znaků)" /></>}{error && <p className="error">{error}</p>}{inviteToken ? <p className="notice">Pozvánka odeslána. Odkaz: <strong>{window.location.origin}/invite/{inviteToken}</strong></p> : <div className="form-actions"><button type="button" className="secondary" onClick={() => setMode('choose')}>Zpět</button><button className="primary" type="submit">{mode === 'invite' || role === 'parent' ? 'Pozvat do rodiny' : 'Přidat člena'}</button></div>}{inviteToken && <button className="primary" type="button" onClick={onDone}>Hotovo</button>}</form>}</section></div>;
}

function InviteScreen({ token, authToken, onLogin }: { token: string; authToken: string | null; onLogin: (token: string, user: User) => void }) {
  const [invitation, setInvitation] = useState<{ family_name: string; invited_email: string; role: string } | null>(null);
  const [error, setError] = useState('');
  const [loginMode, setLoginMode] = useState(false);
  useEffect(() => { request<typeof invitation>(`/family/invitations/${token}`).then(setInvitation).catch((err) => setError(err instanceof Error ? err.message : 'Pozvánku se nepodařilo načíst.')); }, [token]);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError('');
    const data = new FormData(event.currentTarget);
    try {
      let nextToken = authToken;
      if (!nextToken) {
        if (loginMode) nextToken = (await request<{ access_token: string }>('/auth/login', { method: 'POST', body: JSON.stringify({ email: data.get('email'), password: data.get('password') }) })).access_token;
        else nextToken = (await request<{ access_token: string }>(`/family/invitations/${token}/register`, { method: 'POST', body: JSON.stringify({ email: data.get('email'), full_name: data.get('full_name'), password: data.get('password') }) })).access_token;
      }
      await request(`/family/invitations/${token}/accept`, { method: 'POST' }, nextToken);
      onLogin(nextToken, await request<User>('/auth/me', {}, nextToken));
    } catch (err) { setError(err instanceof Error ? err.message : 'Pozvánku se nepodařilo přijmout.'); }
  };
  if (error && !invitation) return <main className="invite-page"><section className="panel invite-card"><p className="eyebrow">FamilyQuest</p><h1>Pozvánka není platná</h1><p className="error">{error}</p></section></main>;
  if (!invitation) return <div className="loading"><div className="loading-spinner">✦</div><span>Ověřuji pozvánku…</span></div>;
  return <main className="invite-page"><section className="panel invite-card"><p className="eyebrow">FamilyQuest pozvánka</p><h1>Byli jste pozváni do rodiny {invitation.family_name}.</h1><p className="muted">Připojíte se jako {invitation.role === 'parent' ? 'rodič' : 'dítě'} pod e-mailem {invitation.invited_email}.</p><form className="task-form" onSubmit={submit}>{!loginMode && !authToken && <input name="full_name" required minLength={2} placeholder="Jméno" />}{!authToken && <input name="email" type="email" defaultValue={invitation.invited_email} readOnly required />}{!authToken && <input name="password" type="password" minLength={8} required placeholder="Heslo" />}{error && <p className="error">{error}</p>}<button className="primary" type="submit">{authToken ? 'Přijmout pozvánku' : loginMode ? 'Přihlásit a připojit se' : 'Vytvořit účet a připojit se'}</button></form>{!authToken && <button className="link-button" onClick={() => setLoginMode(!loginMode)}>{loginMode ? 'Nemám účet, zaregistrovat se' : 'Už mám účet, přihlásit se'}</button>}</section></main>;
}

function AccountManager({ token, members, currentUserId, onRefresh }: { token: string; members: Member[]; currentUserId: string; onRefresh: () => void }) {
  const [selected, setSelected] = useState<Member | null>(null);
  const [error, setError] = useState('');
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!selected) return;
    const data = new FormData(event.currentTarget);
    try { await request(`/family/accounts/${selected.user_id}`, { method: 'PATCH', body: JSON.stringify({ full_name: data.get('full_name'), avatar: data.get('avatar') }) }, token); setSelected(null); onRefresh(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Účet se nepodařilo upravit.'); }
  };
  const changeStatus = async (member: Member) => {
    if (!window.confirm(`${member.is_active === false ? 'Aktivovat' : 'Deaktivovat'} účet ${member.full_name}?`)) return;
    try { await request(`/family/accounts/${member.user_id}/status`, { method: 'PATCH', body: JSON.stringify({ is_active: member.is_active === false }) }, token); onRefresh(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Stav účtu se nepodařilo změnit.'); }
  };
  const switchAccount = async (member: Member) => {
    if (window.confirm(`Přepnout na účet ${member.full_name}?`)) {
      try {
        const response = await request<{ access_token: string }>(`/auth/switch/${member.user_id}`, { method: 'POST' }, token);
        localStorage.setItem('familyquest_token', response.access_token);
        window.location.reload();
      }
      catch (err) { setError(err instanceof Error ? err.message : 'Přepnutí se nepodařilo.'); }
    }
  };
   return <section id="accounts" className="panel accounts-panel"><div className="panel-heading"><div><p className="eyebrow">Účty a profily</p><h2>👤 Správa účtů</h2></div><span className="panel-icon purple">◉</span></div><div className="account-list">{members.map((member) => <article className="account-row" key={member.user_id}><span className="user-avatar child-avatar">{member.avatar || (member.full_name ?? '?').charAt(0)}</span><div><strong>{member.full_name ?? member.email}</strong><small>{member.role === 'parent' ? '👑 Rodič' : '🧒 Dítě'} · {member.is_active === false ? '🔴 Deaktivovaný' : '🟢 Aktivní'}</small></div><div className="member-actions"><button className="secondary compact" onClick={() => { setSelected(member); setError(''); }}>Spravovat</button>{member.user_id !== currentUserId && member.is_active && member.role === 'child' && <button className="secondary compact" onClick={() => switchAccount(member)}>🔄 Přepnout</button>}{member.user_id !== currentUserId && <button className="danger compact" onClick={() => changeStatus(member)}>{member.is_active === false ? 'Aktivovat' : 'Deaktivovat'}</button>}</div></article>)}</div>{selected && <form className="task-form account-edit-form" onSubmit={save}><h3>Upravit profil: {selected.full_name}</h3><input name="full_name" required minLength={2} defaultValue={selected.full_name} placeholder="Jméno" /><input name="avatar" maxLength={20} defaultValue={selected.avatar ?? ''} placeholder="Avatar" />{error && <p className="error">{error}</p>}<div className="form-actions"><button type="button" className="secondary" onClick={() => setSelected(null)}>Zrušit</button><button className="primary" type="submit">Uložit profil</button></div></form>}</section>;
}
