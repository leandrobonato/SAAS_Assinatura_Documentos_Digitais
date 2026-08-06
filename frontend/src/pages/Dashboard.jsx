import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { errorMessage } from "../api";
import StatusBadge from "../components/StatusBadge";
import Topbar from "../components/Topbar";
import UploadModal from "../components/UploadModal";
import { useAuth } from "../context/AuthContext";

function formatDate(value) {
  if (!value) return null;
  return new Date(value + "Z").toLocaleString("pt-BR");
}

export default function Dashboard() {
  const { user, togglePlan } = useAuth();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [error, setError] = useState("");

  async function loadDocuments() {
    setLoading(true);
    try {
      const { data } = await api.get("/documents");
      setDocuments(data);
    } catch (err) {
      setError(errorMessage(err, "Não foi possível carregar seus documentos."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  const sentThisMonth = documents.filter((d) => {
    if (!d.sent_at) return false;
    const sentDate = new Date(d.sent_at + "Z");
    const now = new Date();
    return sentDate.getUTCMonth() === now.getUTCMonth() && sentDate.getUTCFullYear() === now.getUTCFullYear();
  }).length;

  return (
    <div>
      <Topbar />
      <div className="shell">
        <div className="dashboard-header">
          <div>
            <h1>Meus documentos</h1>
            <p>Envie um PDF, posicione os campos de assinatura e acompanhe quem já assinou.</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
            + Novo documento
          </button>
        </div>

        {user?.plan === "free" && (
          <div className="card plan-panel">
            <span>
              <strong>{sentThisMonth}/5</strong> envios usados este mês no plano gratuito.
            </span>
            <button className="btn btn-secondary" onClick={togglePlan} style={{ marginLeft: "auto" }}>
              Fazer upgrade para o Pro
            </button>
          </div>
        )}
        {user?.plan === "pro" && (
          <div className="card plan-panel">
            <span>Plano Pro ativo — envio em lote e lembretes automáticos habilitados.</span>
            <button className="btn btn-secondary" onClick={togglePlan} style={{ marginLeft: "auto" }}>
              Voltar para o plano gratuito
            </button>
          </div>
        )}

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <p>Carregando…</p>
        ) : documents.length === 0 ? (
          <div className="card empty-state">
            <p>Você ainda não enviou nenhum documento.</p>
            <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
              Enviar o primeiro documento
            </button>
          </div>
        ) : (
          <div className="doc-grid">
            {documents.map((doc) => (
              <div key={doc.id} className="card doc-card" onClick={() => navigate(`/documentos/${doc.id}`)}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <span className="doc-card-title">{doc.title}</span>
                  <StatusBadge status={doc.status} />
                </div>
                <span className="doc-card-meta">
                  Criado em {formatDate(doc.created_at)}
                  {doc.completed_at && <> · Concluído em {formatDate(doc.completed_at)}</>}
                </span>
                {doc.signers.length > 0 && (
                  <div className="doc-card-signers">
                    {doc.signers.map((s) => (
                      <StatusBadge key={s.id} status={s.status} />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={(doc) => navigate(`/documentos/${doc.id}`)}
        />
      )}
    </div>
  );
}
