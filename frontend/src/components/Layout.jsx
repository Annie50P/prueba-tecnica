import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { checkHealth } from '../api/client';
import ChatWidget from './ChatWidget';

const NAV_ITEMS = [
  {
    to: '/',
    label: 'Dashboard',
    icon: (
      <svg className="ds-nav-icon" viewBox="0 0 20 20" fill="currentColor">
        <path d="M2 10a8 8 0 1116 0 8 8 0 01-16 0zm8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 10a3 3 0 01-2.25 2.906V13a1 1 0 11-2 0v-.094A3 3 0 017 10a3 3 0 013-3z" />
      </svg>
    ),
  },
  {
    to: '/clientes',
    label: 'Clientes',
    icon: (
      <svg className="ds-nav-icon" viewBox="0 0 20 20" fill="currentColor">
        <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
      </svg>
    ),
  },
  {
    to: '/agentes',
    label: 'Agentes',
    icon: (
      <svg className="ds-nav-icon" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    to: '/grafo',
    label: 'Grafo',
    icon: (
      <svg className="ds-nav-icon" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M17.707 9.293a1 1 0 010 1.414l-7 7a1 1 0 01-1.414 0l-7-7A.997.997 0 012 10V5a3 3 0 013-3h5c.256 0 .512.098.707.293l7 7zM5 6a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    to: '/analisis',
    label: 'Análisis ML',
    icon: (
      <svg className="ds-nav-icon" viewBox="0 0 20 20" fill="currentColor">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
      </svg>
    ),
  },
];

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/clientes': 'Clientes',
  '/agentes': 'Agentes',
  '/grafo': 'Grafo',
  '/analisis': 'Análisis ML',
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
  const isDetail = location.pathname.split('/').length > 2;
  const isGrafo = basePath === '/grafo';

  return (
    <div className="ds-shell">
      <aside className="ds-sidebar">
        <div className="ds-brand">
          <div className="ds-brand-icon">CP</div>
          <div>
            <div className="ds-brand-name">CallPattern</div>
            <div className="ds-brand-sub">Analytics Studio</div>
          </div>
        </div>

        <nav className="ds-nav">
          <div className="ds-nav-label">Menú</div>
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `ds-nav-link${isActive ? ' ds-nav-link-active' : ''}`
              }
            >
              {icon}
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="ds-sidebar-footer">
          <div className="ds-api-status">
            <span
              className="ds-api-dot"
              style={{ background: apiOk ? 'var(--state-success)' : 'var(--state-danger)' }}
            />
            <span>{apiOk ? 'API conectada' : 'API desconectada'}</span>
          </div>
        </div>
      </aside>

      <div className="ds-main">
        {!isGrafo && (
          <header className="ds-topbar">
            <span className="ds-topbar-breadcrumb">{pageTitle}</span>
            {isDetail && (
              <>
                <span className="ds-topbar-sep">/</span>
                <span className="ds-topbar-current">Detalle</span>
              </>
            )}
          </header>
        )}

        <main className={isGrafo ? '' : 'ds-content'} style={{ overflow: 'auto' }}>
          <div className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>

      <ChatWidget />
    </div>
  );
}
