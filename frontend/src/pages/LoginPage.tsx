import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { register } from "../api/auth";
import { ApiError } from "../api/client";
import { useAuth } from "../hooks/useAuth";

type Mode = "login" | "register";

const API_ERRORS: Record<string, string> = {
  REGISTER_USER_ALREADY_EXISTS: "That email or username is already taken.",
  LOGIN_BAD_CREDENTIALS: "Wrong email or password.",
};

const LoginPage = () => {
  const { login, isLoading, error } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const from =
    (location.state as { from?: { pathname?: string } } | undefined)?.from?.pathname ||
    "/play";
  const isRegister = mode === "register";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    try {
      if (isRegister) {
        await register({ email, username, password });
        await login({ username: email, password });
      } else {
        await login({ username: email, password });
      }
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(API_ERRORS[err.message] ?? err.message);
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    }
  };

  const switchMode = () => {
    setMode(isRegister ? "login" : "register");
    setFormError(null);
  };

  return (
    <div className="page-container login-page">
      <div className="card login-card">
        <h1 className="page-title">Nightshift: Analyst</h1>
        <p className="page-subtitle">
          {isRegister ? "Create your analyst account" : "Clock in to your console"}
        </p>
        <form className="form-column" onSubmit={handleSubmit}>
          <label className="form-field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="analyst@nightshift.io"
              autoComplete={isRegister ? "email" : "username"}
              required
            />
          </label>
          {isRegister && (
            <label className="form-field">
              <span>Username (3-50 characters)</span>
              <input
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="analyst"
                autoComplete="nickname"
                minLength={3}
                maxLength={50}
                required
              />
            </label>
          )}
          <label className="form-field">
            <span>{isRegister ? "Password (at least 8 characters)" : "Password"}</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              autoComplete={isRegister ? "new-password" : "current-password"}
              minLength={isRegister ? 8 : undefined}
              required
            />
          </label>
          <button className="button" type="submit" disabled={isLoading}>
            {isLoading ? "Working..." : isRegister ? "Create account" : "Sign in"}
          </button>
        </form>
        {(formError || error) && (
          <p className="form-error" role="alert">
            {formError || error}
          </p>
        )}
        <p className="form-helper">
          {isRegister ? "Already have an account? " : "Need an account? "}
          <button type="button" className="link-button" onClick={switchMode}>
            {isRegister ? "Sign in" : "Create one"}
          </button>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
