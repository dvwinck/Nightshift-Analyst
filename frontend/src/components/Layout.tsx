import { ReactNode } from "react";

import { useAuth } from "../hooks/useAuth";

type LayoutProps = {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
};

const Layout = ({ title = "Nightshift Analyst", actions, children }: LayoutProps) => {
  const { user, logout } = useAuth();

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">{title}</h1>
          <p className="page-subtitle">Narrative investigation dashboard</p>
        </div>
        <div className="header-actions">
          {actions}
          {user && (
            <div className="user-badge">
              <div className="user-info">
                <span className="user-name">{user.username}</span>
                <span className="user-email">{user.email}</span>
              </div>
              <button type="button" className="button button-secondary" onClick={logout}>
                Log out
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="page-content">{children}</main>
    </div>
  );
};

export default Layout;
