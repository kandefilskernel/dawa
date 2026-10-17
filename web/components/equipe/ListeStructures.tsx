"use client";
// Liste des pharmacies ou des établissements : recherche, visibilité dans l'app, lien « nouveau mot de passe ».
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Flash, useFlash } from "@/components/Flash";
import { api } from "@/lib/api";
import type { LienMotDePasse, StructureListe } from "@/lib/equipe";
import { useDonnees } from "@/lib/useDonnees";

import { AvecMotif, useEquipe } from "./Cadre";

const FILTRES = [["", "Toutes"], ["visibles", "Visibles"], ["masquees", "Masquées"]] as const;

function CarteLien({ lien, onFermer }: { lien: LienMotDePasse; onFermer: () => void }) {
  return (
    <div className="carte" style={{ marginBottom: 14, borderColor: "var(--emeraude)" }}>
      <h2>Lien « nouveau mot de passe »</h2>
      <p className="aide">{lien.structure.nom} · compte {lien.identifiant}</p>
      <p>Envoyez ce lien <strong>uniquement au numéro officiel de la structure</strong>. Il est valable 24 heures et
        ne sert qu&apos;une fois. Vérifiez d&apos;abord l&apos;identité de la personne qui le demande (rappel au numéro
        enregistré).</p>
      <label htmlFor="lien">Lien</label>
      <input type="text" id="lien" value={lien.lien} readOnly onFocus={(e) => e.target.select()} />
      <div className="actions">
        {lien.whatsapp && <a className="btn" href={lien.whatsapp} target="_blank" rel="noopener">Envoyer par WhatsApp</a>}
        <a className="btn secondaire" href={`sms:${lien.structure.telephone}?body=${encodeURIComponent(lien.texte)}`}>
          Envoyer par SMS</a>
        <button className="btn secondaire" type="button" onClick={onFermer}>Fermer</button>
      </div>
      <p className="aide">Ce lien n&apos;est pas enregistré : en cas de doute, recréez-en un.</p>
    </div>
  );
}

export function ListeStructures({ genre }: { genre: "pharmacies" | "etablissements" }) {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const filtre = genre === "pharmacies" ? params.get("filtre") ?? "" : "";
  const { donnees, erreur, recharger } = useDonnees<Record<string, StructureListe[]>>(`equipe/${genre}/`, { q, filtre });
  const [recherche, setRecherche] = useState(q);
  const [lien, setLien] = useState<LienMotDePasse | null>(null);
  const { message, executer } = useFlash();
  const { rafraichir } = useEquipe();
  const feminin = genre === "pharmacies";

  function chercher(e: FormEvent) {
    e.preventDefault();
    const p = new URLSearchParams();
    if (recherche.trim()) p.set("q", recherche.trim());
    if (filtre) p.set("filtre", filtre);
    router.push(`?${p}`);
  }

  async function visibilite(s: StructureListe, action: "suspendre" | "reactiver", motif?: string) {
    const r = await executer(() => api<{ message: string }>(`equipe/${genre}/${s.id}/visibilite/`, {
      methode: "POST", donnees: { action, motif },
    }), (x) => x.message);
    if (r) { recharger(); rafraichir(); }
  }

  async function creerLien(utilisateurId: number) {
    const r = await executer(() => api<LienMotDePasse>(`equipe/comptes/${utilisateurId}/lien-mot-de-passe/`, { methode: "POST" }));
    if (r) { setLien(r); window.scrollTo({ top: 0, behavior: "smooth" }); }
  }

  const liste = donnees?.[genre];
  return (
    <>
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {lien && <CarteLien lien={lien} onFermer={() => setLien(null)} />}
      <form className="recherche" role="search" onSubmit={chercher}>
        <input type="search" value={recherche} onChange={(e) => setRecherche(e.target.value)}
          aria-label={feminin ? "Rechercher une pharmacie" : "Rechercher un établissement"}
          placeholder={feminin ? "Nom, quartier, téléphone, autorisation" : "Nom, quartier, autorisation"} />
        <button className="btn" type="submit">Rechercher</button>
      </form>
      {feminin && (
        <nav className="onglets" aria-label="Filtrer les pharmacies">
          {FILTRES.map(([code, libelle]) => (
            <Link key={code} href={`?${new URLSearchParams({ ...(q ? { q } : {}), ...(code ? { filtre: code } : {}) })}`}
              className={code === filtre ? "actif" : undefined}>{libelle}</Link>
          ))}
        </nav>
      )}
      {!liste ? <Chargement /> : liste.length ? liste.map((s) => (
        <article className="carte" key={s.id}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 8, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700 }}>{s.nom}</div>
              <div className="aide">
                {!feminin && `${s.type} · `}{s.quartier || s.adresse}{feminin && ` · ${s.telephone}`}
                {s.numero_agrement && ` · Aut. ${s.numero_agrement}`}
              </div>
            </div>
            {s.visible ? <span className="pastille p-ok">Visible</span>
              : <span className="pastille p-neutre">{feminin ? "Masquée" : "Masqué"}</span>}
            {s.kyc_verifie ? <span className="pastille p-ok">KYC vérifié</span> : <span className="pastille p-attente">KYC à faire</span>}
            {s.sponsorisee && <span className="pastille p-prete">Mise en avant</span>}
            {s.comptes.map((c) => c.statut === "suspendu" ? <span key={c.id} className="pastille p-refus" title={c.motif}>{feminin ? "Suspendue" : "Suspendu"}</span>
              : c.statut === "en_attente" ? <span key={c.id} className="pastille p-attente">Inscription à vérifier</span>
                : c.statut === "refuse" ? <span key={c.id} className="pastille p-refus">{feminin ? "Refusée" : "Refusé"}</span> : null)}
          </div>
          <div className="actions">
            <a className="btn secondaire" href={s.admin}>Modifier la fiche</a>
            {s.comptes.map((c) => (
              <form key={c.id} onSubmit={(e) => { e.preventDefault(); creerLien(c.utilisateur_id); }}>
                <button className="btn secondaire" type="submit" aria-label={`Lien mot de passe (compte ${c.identifiant})`}>
                  Lien mot de passe</button>
              </form>
            ))}
            {s.visible ? (
              <AvecMotif bouton="Suspendre" confirmer="Confirmer la suspension"
                libelle={feminin ? "Motif (montré à la pharmacie)" : "Motif"}
                placeholder={feminin ? "Ex. abonnement impayé, fermeture" : "Ex. autorisation expirée"}
                onValider={(m) => visibilite(s, "suspendre", m)} />
            ) : (
              <form onSubmit={(e) => { e.preventDefault(); visibilite(s, "reactiver"); }}>
                <button className="btn" type="submit">Rendre visible</button>
              </form>
            )}
          </div>
        </article>
      )) : <div className="carte vide"><p>{feminin ? "Aucune pharmacie trouvée." : "Aucun établissement trouvé."}</p></div>}
    </>
  );
}
