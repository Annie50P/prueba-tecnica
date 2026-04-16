import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { checkHealth } from '../api/client';
import ChatWidget from './ChatWidget';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/clientes', label: 'Clientes' },
  { to: '/agentes', label: 'Agentes' },
  { to: '/grafo', label: 'Grafo' },
  { to: '/analisis', label: 'Analisis' },
];

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/clientes': 'Clientes',
  '/agentes': 'Agentes',
  '/grafo': 'Explorador de Grafo',
  '/analisis': 'Analisis Avanzado',
};

export default function Layout() {
  const location = useLocation();

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 30_000,
  });

  const apiOk = !!health;
  const basePath = '/' + (location.pathname.split('/')[1] || '');
  const pageTitle = PAGE_TITLES[basePath] || '';
  const isDetailPage = location.pathname.split('/').length > 2;
  const detailPrefix = isDetailPage && pageTitle ? `${pageTitle} / ` : '';

  return (
    <div className="poll-app">
      <div className="poll-shell">
        <aside className="poll-sidebar">
          <div className="flex items-center gap-3">
            <span className="poll-brand-mark">PC</span>
            <div>
              <p className="poll-brand-title">PollClass</p>
              <p className="poll-brand-subtitle">Call Pattern Studio</p>
            </div>
          </div>

          <nav className="poll-nav">
            {NAV_ITEMS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `poll-nav-link ${isActive ? 'poll-nav-link-active' : ''}`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="poll-meta">
            <p>{apiOk ? 'API conectada' : 'API desconectada'}</p>
            <p>localhost:8001</p>
          </div>
        </aside>

        <div className="poll-main">
          {basePath !== '/grafo' && (
            <header className="poll-topbar">
              {detailPrefix}
              {isDetailPage ? 'Detalle' : pageTitle}
            </header>
          )}

          <main className="poll-content overflow-auto">
            <div className="page-enter">
              <Outlet />
            </div>
          </main>
        </div>
      </div>

      <ChatWidget />
    </div>
  );
}
