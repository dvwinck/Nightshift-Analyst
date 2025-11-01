import {
  ReactNode,
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  fetchCurrentUser,
  login as loginRequest,
  LoginCredentials,
} from "../api/auth";
import { ApiError } from "../api/client";
import { User } from "../types";

type AuthContextValue = {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const TOKEN_STORAGE_KEY = "nightshift_analyst_token";
const USER_STORAGE_KEY = "nightshift_analyst_user";

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined
);

type AuthProviderProps = {
  children: ReactNode;
};

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const persistSession = useCallback((nextToken: string, nextUser: User) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, nextToken);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(nextUser));
    setToken(nextToken);
    setUser(nextUser);
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const loadUserProfile = useCallback(
    async (authToken: string) => {
      try {
        const profile = await fetchCurrentUser(authToken);
        persistSession(authToken, profile);
      } catch (err) {
        clearSession();
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("Unable to refresh user session");
        }
      }
    },
    [clearSession, persistSession]
  );

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    const storedUser = localStorage.getItem(USER_STORAGE_KEY);

    const bootstrap = async () => {
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        if (storedUser) {
          const parsed = JSON.parse(storedUser) as User;
          setToken(storedToken);
          setUser(parsed);
        }
      } catch {
        clearSession();
        setIsLoading(false);
        return;
      }

      await loadUserProfile(storedToken);
      setIsLoading(false);
    };

    bootstrap();
  }, [clearSession, loadUserProfile]);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await loginRequest(credentials);
        await loadUserProfile(response.access_token);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("Unexpected error. Please try again.");
        }
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [loadUserProfile]
  );

  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  const refreshUser = useCallback(async () => {
    if (!token) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await loadUserProfile(token);
    } finally {
      setIsLoading(false);
    }
  }, [loadUserProfile, token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(user && token),
      isLoading,
      error,
      login,
      logout,
      refreshUser,
    }),
    [error, isLoading, login, logout, refreshUser, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
