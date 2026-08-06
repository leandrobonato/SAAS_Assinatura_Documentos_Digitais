import { useEffect, useRef, useState } from "react";
import { Document as PdfDocument, Page, pdfjs } from "react-pdf";
import { useParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import SignaturePad from "../components/SignaturePad";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

const PAGE_WIDTH = 680;

export default function PublicSign() {
  const { token } = useParams();
  const [view, setView] = useState(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
  const [numPages, setNumPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [typedName, setTypedName] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const padRef = useRef(null);

  useEffect(() => {
    let blobUrl = null;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const { data } = await api.get(`/public/sign/${token}`);
        setView(data);
        const pdfRes = await api.get(`/public/sign/${token}/document.pdf`, { responseType: "blob" });
        blobUrl = URL.createObjectURL(pdfRes.data);
        setPdfBlobUrl(blobUrl);
      } catch (err) {
        if (err?.response?.status === 404) setNotFound(true);
        else setError(errorMessage(err, "Não foi possível carregar o documento."));
      } finally {
        setLoading(false);
      }
    }

    load();
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [token]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!typedName.trim()) {
      setError("Informe seu nome completo.");
      return;
    }
    if (!agreed) {
      setError("Confirme que você concorda com a assinatura eletrônica deste documento.");
      return;
    }
    if (padRef.current.isEmpty()) {
      setError("Desenhe sua assinatura no quadro antes de confirmar.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await api.post(`/public/sign/${token}`, {
        signature_image: padRef.current.getDataUrl(),
        typed_name: typedName,
      });
      setDone(true);
    } catch (err) {
      setError(errorMessage(err, "Não foi possível registrar sua assinatura."));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="page-loading">Carregando…</div>;

  if (notFound) {
    return (
      <div className="center-page">
        <div className="card auth-card">
          <h2>Link inválido</h2>
          <p>Este link de assinatura não existe ou foi removido. Verifique o link recebido por e-mail.</p>
        </div>
      </div>
    );
  }

  if (done || view?.signer_status === "signed") {
    return (
      <div className="center-page">
        <div className="card auth-card">
          <div className="auth-logo">DocuFlow</div>
          <h2>Assinatura registrada!</h2>
          <p>Obrigado, {view?.signer_name}. Você receberá uma cópia por e-mail assim que todas as partes assinarem.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <header className="topbar">
        <span className="topbar-logo">DocuFlow</span>
      </header>
      <div className="sign-shell">
        <div className="pdf-viewer">
          {pdfBlobUrl && (
            <PdfDocument file={pdfBlobUrl} onLoadSuccess={({ numPages: n }) => setNumPages(n)} loading="Carregando PDF…">
              {Array.from({ length: numPages }, (_, pageIndex) => (
                <div key={pageIndex} className="pdf-page-wrap">
                  <Page pageNumber={pageIndex + 1} width={PAGE_WIDTH} renderTextLayer={false} renderAnnotationLayer={false} />
                  {view.fields
                    .filter((f) => f.page_number === pageIndex)
                    .map((field) => (
                      <div
                        key={field.id}
                        className="field-box"
                        style={{
                          left: `${field.x * 100}%`,
                          top: `${field.y * 100}%`,
                          width: `${field.width * 100}%`,
                          height: `${field.height * 100}%`,
                          borderColor: "#3552e0",
                          color: "#3552e0",
                          background: "#3552e022",
                        }}
                      >
                        Assine aqui
                      </div>
                    ))}
                  <span className="page-number-tag">Página {pageIndex + 1}</span>
                </div>
              ))}
            </PdfDocument>
          )}
        </div>

        <form className="card sign-panel" onSubmit={handleSubmit}>
          <h2>{view.document_title}</h2>
          <p className="hint">
            Olá, {view.signer_name}. Revise o documento e assine abaixo.
            {view.other_signers_pending.length > 0 && (
              <> Também aguardando: {view.other_signers_pending.join(", ")}.</>
            )}
          </p>

          {error && <div className="alert alert-error">{error}</div>}

          <div className="field">
            <label>Sua assinatura</label>
            <SignaturePad ref={padRef} />
            <button type="button" className="btn btn-secondary" onClick={() => padRef.current.clear()}>
              Limpar
            </button>
          </div>

          <div className="field">
            <label htmlFor="typedName">Nome completo</label>
            <input id="typedName" required value={typedName} onChange={(e) => setTypedName(e.target.value)} />
          </div>

          <label style={{ display: "flex", gap: 8, fontSize: 12, marginBottom: 16, color: "var(--color-text-muted)" }}>
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
            Concordo que esta assinatura eletrônica tem a mesma validade de uma assinatura manuscrita para este
            documento, e autorizo o registro do meu endereço IP e horário como prova de autenticidade.
          </label>

          <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
            {submitting ? "Assinando…" : "Confirmar assinatura"}
          </button>
        </form>
      </div>
    </div>
  );
}
