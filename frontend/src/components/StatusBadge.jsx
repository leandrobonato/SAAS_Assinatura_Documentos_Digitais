const LABELS = {
  draft: "Rascunho",
  sent: "Aguardando assinatura",
  completed: "Concluído",
  pending: "Pendente",
  viewed: "Visualizado",
  signed: "Assinado",
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-status-${status}`}>{LABELS[status] || status}</span>;
}
