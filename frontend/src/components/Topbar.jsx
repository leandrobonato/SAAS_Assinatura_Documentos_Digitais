import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Topbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="topbar">
      <Link to="/documentos" className="topbar-logo">
        DocuFlow
      </Link>
      {user && (
        <div className="topbar-right">
          <span className={`badge ${user.plan === "pro" ? "badge-pro" : "badge-free"}`}>
            Plano {user.plan === "pro" ? "Pro" : "Gratuito"}
          </span>
          <span className="topbar-user">{user.name}</span>
          <button className="btn btn-secondary" onClick={handleLogout}>
            Sair
          </button>
        </div>
      )}
    </header>
  );
}
