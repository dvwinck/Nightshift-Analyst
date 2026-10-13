import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./hooks/useAuth";
import LoginPage from "./pages/LoginPage";
import TerminalPage from "./pages/TerminalPage";

const App = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/play" replace /> : <LoginPage />}
      />
      <Route
        path="/play"
        element={
          <ProtectedRoute>
            <TerminalPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="*"
        element={<Navigate to={isAuthenticated ? "/play" : "/login"} replace />}
      />
    </Routes>
  );
};

export default App;
