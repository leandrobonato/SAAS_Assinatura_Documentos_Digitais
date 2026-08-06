import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import DocumentEditor from "./pages/DocumentEditor";
import Login from "./pages/Login";
import PublicSign from "./pages/PublicSign";
import Register from "./pages/Register";
import "./App.css";

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loading">Carregando…</div>;
  return <Navigate to={user ? "/documentos" : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Register />} />
      <Route path="/assinar/:token" element={<PublicSign />} />
      <Route
        path="/documentos"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/documentos/:id"
        element={
          <ProtectedRoute>
            <DocumentEditor />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
