import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/documentos");
    } catch (err) {
      setError(errorMessage(err, "Não foi possível entrar."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <form className="card auth-card" onSubmit={handleSubmit}>
        <div className="auth-logo">DocuFlow</div>
        <p className="auth-subtitle">Entre para gerenciar seus documentos.</p>
        {error && <div className="alert alert-error">{error}</div>}
        <div className="field">
          <label htmlFor="email">E-mail</label>
          <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="password">Senha</label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
          {loading ? "Entrando…" : "Entrar"}
        </button>
        <p className="auth-switch">
          Não tem conta? <Link to="/registro">Criar conta gratuita</Link>
        </p>
      </form>
    </div>
  );
}
