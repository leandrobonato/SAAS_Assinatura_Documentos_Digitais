import { useEffect, useMemo, useRef, useState } from "react";
import { Document as PdfDocument, Page, pdfjs } from "react-pdf";
import { useNavigate, useParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import StatusBadge from "../components/StatusBadge";
import Topbar from "../components/Topbar";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

const SIGNER_COLORS = ["#3552e0", "#1a9e6b", "#b5720a", "#c0324a", "#7c3aed", "#0891b2"];
const DEFAULT_FIELD_SIZE = { width: 0.22, height: 0.06 };
const PAGE_WIDTH = 720;

function colorForSigner(signers, signerId) {
  const idx = signers.findIndex((s) => s.id === signerId);
  return SIGNER_COLORS[idx % SIGNER_COLORS.length] || SIGNER_COLORS[0];
}

export default function DocumentEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [activeSignerId, setActiveSignerId] = useState(null);
  const [newSignerName, setNewSignerName] = useState("");
  const [newSignerEmail, setNewSignerEmail] = useState("");
  const [numPages, setNumPages] = useState(0);
  const [sending, setSending] = useState(false);
  const [audit, setAudit] = useState([]);
  const draggingField = useRef(null);

  useEffect(() => {
    let currentBlobUrl = null;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const { data } = await api.get(`/documents/${id}`);
        setDoc(data);
        if (data.signers.length) setActiveSignerId(data.signers[0].id);
        if (data.status !== "draft") {
          const auditRes = await api.get(`/documents/${id}/audit`);
          setAudit(auditRes.data);
        }
        const pdfPath = data.status === "completed" ? "final.pdf" : "original.pdf";
        const pdfRes = await api.get(`/documents/${id}/${pdfPath}`, { responseType: "blob" });
        currentBlobUrl = URL.createObjectURL(pdfRes.data);
        setPdfBlobUrl(currentBlobUrl);
      } catch (err) {
        setError(errorMessage(err, "Não foi possível carregar o documento."));
      } finally {
        setLoading(false);
      }
    }

    load();
    return () => {
      if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);
    };
  }, [id]);

  const isDraft = doc?.status === "draft";

  async function addSigner(e) {
    e.preventDefault();
    try {
      const { data } = await api.post(`/documents/${id}/signers`, { name: newSignerName, email: newSignerEmail });
      setDoc((d) => ({ ...d, signers: [...d.signers, data] }));
      setActiveSignerId(data.id);
      setNewSignerName("");
      setNewSignerEmail("");
    } catch (err) {
      setError(errorMessage(err, "Não foi possível adicionar o signatário."));
    }
  }

  async function removeSigner(signerId) {
    try {
      await api.delete(`/documents/${id}/signers/${signerId}`);
      setDoc((d) => ({
        ...d,
        signers: d.signers.filter((s) => s.id !== signerId),
        fields: d.fields.filter((f) => f.signer_id !== signerId),
      }));
      if (activeSignerId === signerId) setActiveSignerId(null);
    } catch (err) {
      setError(errorMessage(err, "Não foi possível remover o signatário."));
    }
  }

  async function syncFields(nextFields) {
    const payload = {
      fields: nextFields.map((f) => ({
        signer_id: f.signer_id,
        page_number: f.page_number,
        x: f.x,
        y: f.y,
        width: f.width,
        height: f.height,
      })),
    };
    try {
      const { data } = await api.put(`/documents/${id}/fields`, payload);
      setDoc((d) => ({ ...d, fields: data }));
    } catch (err) {
      setError(errorMessage(err, "Não foi possível salvar os campos de assinatura."));
    }
  }

  function handleDropOnPage(e, pageIndex) {
    e.preventDefault();
    const signerId = Number(e.dataTransfer.getData("text/signer-id")) || activeSignerId;
    if (!signerId) return;
    const rect = e.currentTarget.getBoundingClientRect();
    let x = (e.clientX - rect.left) / rect.width - DEFAULT_FIELD_SIZE.width / 2;
    let y = (e.clientY - rect.top) / rect.height - DEFAULT_FIELD_SIZE.height / 2;
    x = Math.min(Math.max(x, 0), 1 - DEFAULT_FIELD_SIZE.width);
    y = Math.min(Math.max(y, 0), 1 - DEFAULT_FIELD_SIZE.height);
    const nextFields = [...doc.fields, { signer_id: signerId, page_number: pageIndex, x, y, ...DEFAULT_FIELD_SIZE }];
    syncFields(nextFields);
  }

  function removeField(fieldId) {
    syncFields(doc.fields.filter((f) => f.id !== fieldId));
  }

  function startFieldDrag(e, field) {
    e.stopPropagation();
    const pageEl = e.currentTarget.closest(".pdf-page-wrap");
    draggingField.current = { field, rect: pageEl.getBoundingClientRect() };
  }

  function handlePageMouseMove(e) {
    if (!draggingField.current) return;
    const { field, rect } = draggingField.current;
    let x = (e.clientX - rect.left) / rect.width - field.width / 2;
    let y = (e.clientY - rect.top) / rect.height - field.height / 2;
    x = Math.min(Math.max(x, 0), 1 - field.width);
    y = Math.min(Math.max(y, 0), 1 - field.height);
    setDoc((d) => ({ ...d, fields: d.fields.map((f) => (f.id === field.id ? { ...f, x, y } : f)) }));
  }

  function handlePageMouseUp() {
    if (!draggingField.current) return;
    draggingField.current = null;
    syncFields(doc.fields);
  }

  async function handleSend() {
    setSending(true);
    setError("");
    try {
      const { data } = await api.post(`/documents/${id}/send`);
      setDoc(data);
      setNotice("Documento enviado! Os signatários receberão o link de assinatura por e-mail.");
    } catch (err) {
      setError(errorMessage(err, "Não foi possível enviar o documento."));
    } finally {
      setSending(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Excluir este rascunho? Esta ação não pode ser desfeita.")) return;
    try {
      await api.delete(`/documents/${id}`);
      navigate("/documentos");
    } catch (err) {
      setError(errorMessage(err, "Não foi possível excluir o documento."));
    }
  }

  async function downloadFinal() {
    try {
      const res = await api.get(`/documents/${id}/final.pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${doc.title || "documento"}-assinado.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(errorMessage(err, "Não foi possível baixar o PDF assinado."));
    }
  }

  const fieldsBySignerCount = useMemo(() => {
    const counts = {};
    (doc?.fields || []).forEach((f) => {
      counts[f.signer_id] = (counts[f.signer_id] || 0) + 1;
    });
    return counts;
  }, [doc]);

  if (loading) return <div className="page-loading">Carregando…</div>;
  if (!doc) return <div className="page-loading">{error || "Documento não encontrado."}</div>;

  return (
    <div>
      <Topbar />
      <div className="editor-shell">
        <aside className="card editor-sidebar">
          <h2>{doc.title}</h2>
          <p className="hint">
            <StatusBadge status={doc.status} />
          </p>

          {error && <div className="alert alert-error">{error}</div>}
          {notice && <div className="alert alert-success">{notice}</div>}

          <h2 style={{ marginTop: 18 }}>Signatários</h2>
          <p className="hint">
            {isDraft
              ? "Arraste um signatário até o documento para posicionar o campo de assinatura dele."
              : "Acompanhamento de assinatura."}
          </p>

          {doc.signers.map((signer) => (
            <div
              key={signer.id}
              className={`signer-chip ${activeSignerId === signer.id ? "active" : ""}`}
              draggable={isDraft}
              onClick={() => setActiveSignerId(signer.id)}
              onDragStart={(e) => e.dataTransfer.setData("text/signer-id", String(signer.id))}
            >
              <span className="signer-chip-swatch" style={{ background: colorForSigner(doc.signers, signer.id) }} />
              <span className="signer-chip-name">{signer.name}</span>
              {!isDraft ? (
                <StatusBadge status={signer.status} />
              ) : (
                <>
                  <span className="hint">{fieldsBySignerCount[signer.id] || 0} campo(s)</span>
                  <button className="signer-chip-remove" onClick={() => removeSigner(signer.id)} title="Remover">
                    ✕
                  </button>
                </>
              )}
            </div>
          ))}

          {isDraft && (
            <form className="add-signer-form" onSubmit={addSigner}>
              <input
                placeholder="Nome do signatário"
                required
                value={newSignerName}
                onChange={(e) => setNewSignerName(e.target.value)}
              />
              <input
                type="email"
                placeholder="E-mail"
                required
                value={newSignerEmail}
                onChange={(e) => setNewSignerEmail(e.target.value)}
              />
              <button className="btn btn-secondary" type="submit">
                + Adicionar signatário
              </button>
            </form>
          )}

          <div className="divider" />

          {isDraft ? (
            <div className="editor-actions">
              <button className="btn btn-primary" onClick={handleSend} disabled={sending}>
                {sending ? "Enviando…" : "Enviar para assinatura"}
              </button>
              <button className="btn btn-danger" onClick={handleDelete}>
                Excluir rascunho
              </button>
            </div>
          ) : (
            <div className="editor-actions">
              {doc.status === "completed" && (
                <button className="btn btn-primary" onClick={downloadFinal}>
                  Baixar PDF assinado
                </button>
              )}
              {doc.final_hash && (
                <p className="hint" style={{ wordBreak: "break-all" }}>
                  Hash SHA-256: {doc.final_hash}
                </p>
              )}
              {audit.length > 0 && (
                <>
                  <h2>Trilha de auditoria</h2>
                  <ul className="audit-list">
                    {audit.map((a, i) => (
                      <li key={i}>
                        <strong>{a.event}</strong> — {new Date(a.created_at + "Z").toLocaleString("pt-BR")}
                        {a.ip_address && <div className="hint">IP: {a.ip_address}</div>}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}
        </aside>

        <div className="pdf-viewer">
          {pdfBlobUrl && (
            <PdfDocument
              file={pdfBlobUrl}
              onLoadSuccess={({ numPages: n }) => setNumPages(n)}
              loading="Carregando PDF…"
            >
              {Array.from({ length: numPages }, (_, pageIndex) => (
                <div
                  key={pageIndex}
                  className="pdf-page-wrap"
                  onDragOver={(e) => isDraft && e.preventDefault()}
                  onDrop={(e) => isDraft && handleDropOnPage(e, pageIndex)}
                  onMouseMove={handlePageMouseMove}
                  onMouseUp={handlePageMouseUp}
                  onMouseLeave={handlePageMouseUp}
                >
                  <Page pageNumber={pageIndex + 1} width={PAGE_WIDTH} renderTextLayer={false} renderAnnotationLayer={false} />
                  {doc.fields
                    .filter((f) => f.page_number === pageIndex)
                    .map((field) => {
                      const color = colorForSigner(doc.signers, field.signer_id);
                      const signer = doc.signers.find((s) => s.id === field.signer_id);
                      return (
                        <div
                          key={field.id}
                          className="field-box"
                          style={{
                            left: `${field.x * 100}%`,
                            top: `${field.y * 100}%`,
                            width: `${field.width * 100}%`,
                            height: `${field.height * 100}%`,
                            borderColor: color,
                            color,
                            background: `${color}22`,
                          }}
                          onMouseDown={(e) => isDraft && startFieldDrag(e, field)}
                        >
                          {signer?.name || "Assinatura"}
                          {isDraft && (
                            <button className="remove-field" onClick={() => removeField(field.id)}>
                              ✕
                            </button>
                          )}
                        </div>
                      );
                    })}
                  <span className="page-number-tag">Página {pageIndex + 1}</span>
                </div>
              ))}
            </PdfDocument>
          )}
        </div>
      </div>
    </div>
  );
}
