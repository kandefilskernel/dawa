import type { Commande } from "@/lib/pharmacie";

export function PastilleCommande({ c }: { c: Pick<Commande, "statut" | "statut_libelle"> }) {
  const classe = { livree: "p-ok", annulee: "p-neutre", confirmee: "p-prete", envoyee: "p-attente" }[c.statut];
  return <span className={`pastille ${classe}`}>{c.statut_libelle}</span>;
}
