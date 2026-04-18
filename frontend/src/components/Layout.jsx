import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { checkHealth } from '../api/client';
import ChatWidget from './ChatWidget';
import { useTheme } from '../context/ThemeContext';

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

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';
  return (
    <button
      onClick={toggle}
      title={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        width: '100%',
        padding: '6px 8px',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-medium)',
        background: 'var(--bg-elevated)',
        color: 'var(--text-secondary)',
        cursor: 'pointer',
        fontSize: 12,
        fontFamily: 'inherit',
        transition: 'background 0.15s',
      }}
    >
      {isDark ? (
        <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
        </svg>
      ) : (
        <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
          <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
        </svg>
      )}
      {isDark ? 'Modo claro' : 'Modo oscuro'}
    </button>
  );
}

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

        <div className="ds-sidebar-footer" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <ThemeToggle />
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
