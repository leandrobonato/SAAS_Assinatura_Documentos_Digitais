import { useState } from "react";
import api, { errorMessage } from "../api";

export default function UploadModal({ onClose, onUploaded }) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError("Selecione um arquivo PDF.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title || file.name.replace(/\.pdf$/i, ""));
      const { data } = await api.post("/documents", formData);
      onUploaded(data);
    } catch (err) {
      setError(errorMessage(err, "Não foi possível enviar o arquivo."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="upload-modal-backdrop" onClick={onClose}>
      <form className="card upload-modal" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2 style={{ marginTop: 0 }}>Novo documento</h2>
        {error && <div className="alert alert-error">{error}</div>}
        <div className="field">
          <label htmlFor="title">Título</label>
          <input
            id="title"
            placeholder="Ex.: Contrato de prestação de serviço"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="file">Arquivo PDF</label>
          <input
            id="file"
            type="file"
            accept="application/pdf"
            required
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ flex: 1 }}>
            {loading ? "Enviando…" : "Enviar e continuar"}
          </button>
        </div>
      </form>
    </div>
  );
}
