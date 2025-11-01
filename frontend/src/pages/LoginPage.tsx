import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../hooks/useAuth";

const LoginPage = () => {
  const { login, isLoading, error } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const from =
    (location.state as { from?: { pathname?: string } } | undefined)?.from?.pathname ||
    "/cases";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    try {
      await login({ username, password });
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
      } else {
        setFormError("Unable to sign in. Please try again.");
      }
    }
  };

  return (
    <div className="page-container login-page">
      <div className="card login-card">
        <h1 className="page-title">Nightshift Analyst</h1>
        <p className="page-subtitle">Log in to track narrative investigations</p>
        <form className="form-column" onSubmit={handleSubmit}>
          <label className="form-field">
            <span>Email or Username</span>
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="analyst@nightshift.io"
              autoComplete="username"
              required
            />
          </label>
          <label className="form-field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </label>
          <button className="button" type="submit" disabled={isLoading}>
            {isLoading ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {(formError || error) && (
          <p className="form-error" role="alert">
            {formError || error}
          </p>
        )}
        <p className="form-helper">
          Need an account? Use the `/api/v1/auth/register` endpoint to create one.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
