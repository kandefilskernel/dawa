"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Chargement } from "@/components/CarteConnexion";
import { Champ } from "@/components/Champ";
import { Flash, useFlash } from "@/components/Flash";
import { IconeLune } from "@/components/Icones";
import { Cadre, useResume } from "@/components/pharmacie/Cadre";
import { api, ErreurApi } from "@/lib/api";
import { heure, jourLong, lienWhatsapp } from "@/lib/format";
import type { Fiche, Livreur, Profil } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

const CHAMPS: { nom: keyof Fiche; libelle: string; aide?: string; type?: string }[] = [
  { nom: "telephone", libelle: "Téléphone", type: "tel" },
  { nom: "whatsapp", libelle: "WhatsApp", type: "tel" },
  { nom: "horaires", libelle: "Horaires d'ouverture", aide: "Ex. Lun–Sam 8h–20h, Dim 9h–13h" },
  { nom: "adresse", libelle: "Adresse" },
  { nom: "quartier", libelle: "Quartier" },
];

const COMMANDES_SMS = [
  ["DISPO doliprane 4500", "disponible, prix en dernier (facultatif)"],
  ["RUPTURE amoxicilline", "en rupture"],
  ["PRIX coartem 12000", "change le prix"],
  ["OK", "tout mon stock est à jour"],
];

function FormulaireFiche({ fiche, onEnregistree }: { fiche: Fiche; onEnregistree: (f: Fiche, m: string) => void }) {
  const [valeurs, setValeurs] = useState(fiche);
  const [erreurs, setErreurs] = useState<Record<string, string[]>>({});
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);

  async function enregistrer(e: FormEvent) {
    e.preventDefault();
    setEnvoi(true);
    setErreurs({});
    setErreur("");
    try {
      const r = await api<{ fiche: Fiche; message: string }>("pharmacie/profil/", { methode: "POST", donnees: valeurs });
      onEnregistree(r.fiche, r.message);
    } catch (err) {
      if (err instanceof ErreurApi) { setErreurs(err.champs); setErreur(err.message); } else setErreur("Enregistrement impossible.");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <form className="carte" onSubmit={enregistrer}>
      {erreur && !Object.keys(erreurs).length && <div className="erreur" style={{ marginBottom: 10 }}>{erreur}</div>}
      {CHAMPS.map((c) => (
        <Champ key={c.nom} nom={c.nom} libelle={c.libelle} aide={c.aide} type={c.type} erreurs={erreurs}
          valeur={valeurs[c.nom]} onChange={(v) => setValeurs({ ...valeurs, [c.nom]: v })} />
      ))}
      <button className="btn bloc" type="submit" disabled={envoi}>{envoi ? "Enregistrement…" : "Enregistrer"}</button>
      <p className="aide" style={{ marginTop: 12 }}>Pour changer le nom ou la position sur la carte, contactez l&apos;équipe Uzima.</p>
    </form>
  );
}

function Livreurs({ livreurs, nomPharmacie, onChange }: {
  livreurs: Livreur[];
  nomPharmacie: string;
  onChange: (m: { type: "success" | "error"; texte: string }) => void;
}) {
  const [nom, setNom] = useState("");
  const [telephone, setTelephone] = useState("");

  async function action(appel: () => Promise<unknown>, succes: string) {
    try {
      await appel();
      onChange({ type: "success", texte: succes });
      return true;
    } catch (e) {
      onChange({ type: "error", texte: e instanceof ErreurApi ? e.message : "L'action n'a pas abouti." });
      return false;
    }
  }

  async function ajouter(e: FormEvent) {
    e.preventDefault();
    const ok = await action(() => api("pharmacie/livreurs/", { methode: "POST", donnees: { nom, telephone } }),
      `${nom.trim()} ajouté : vos clients peuvent maintenant choisir la livraison.`);
    if (ok) { setNom(""); setTelephone(""); }
  }

  return (
    <div className="carte">
      {livreurs.length ? (
        <ul className="liste">
          {livreurs.map((l) => (
            <li key={l.id}>
              <span className="icone-carre">🛵</span>
              <div className="grow">
                <div className="nom">{l.nom}</div><div className="sous">{l.telephone}</div>
                <div className="sous" style={{ marginTop: 4 }}>Lien du livreur (partage de position pendant les courses) :{" "}
                  <a href={l.lien} target="_blank" rel="noopener">ouvrir</a> ·{" "}
                  <a href={lienWhatsapp(`Uzima – vos livraisons de ${nomPharmacie} : ${l.lien}`)} target="_blank" rel="noopener">
                    envoyer par WhatsApp</a>
                </div>
              </div>
              <button className="btn danger" type="button"
                onClick={() => action(() => api(`pharmacie/livreurs/${l.id}/retirer/`, { methode: "POST" }), "Livreur retiré.")}>
                Retirer
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="aide" style={{ marginTop: 0 }}>Aucun livreur : la livraison n&apos;est pas proposée aux clients.</p>
      )}
      <form onSubmit={ajouter} style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
        <input type="text" placeholder="Nom du livreur" aria-label="Nom du livreur" required style={{ flex: "1 1 140px" }}
          value={nom} onChange={(e) => setNom(e.target.value)} />
        <input type="tel" placeholder="Téléphone" aria-label="Téléphone du livreur" required style={{ flex: "1 1 140px" }}
          value={telephone} onChange={(e) => setTelephone(e.target.value)} />
        <button className="btn" type="submit">Ajouter</button>
      </form>
    </div>
  );
}

export default function PageProfil() {
  const { donnees, erreur, recharger, setDonnees } = useDonnees<Profil>("pharmacie/profil/");
  const { message, setMessage } = useFlash();
  const { resume } = useResume();
  const [sms, setSms] = useState("");

  async function essayerSms(e: FormEvent) {
    e.preventDefault();
    try {
      const r = await api<{ reponse: string }>("pharmacie/sms/", { methode: "POST", donnees: { texte: sms } });
      setMessage({ type: "info", texte: `Réponse Uzima : ${r.reponse}` });
    } catch (err) {
      setMessage({ type: "error", texte: err instanceof ErreurApi ? err.message : "Envoi impossible." });
    }
  }

  return (
    <Cadre titre="Ma pharmacie" intro="Ces informations sont affichées aux patients dans l'application." avecBandeau={false}>
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      {!donnees ? <Chargement /> : (
        <>
          <Link className="carte" href="/pharmacie/dossier"
            style={{ display: "flex", alignItems: "center", gap: 12, color: "inherit", marginBottom: 14 }}>
            <div style={{ flex: 1 }}><div style={{ fontWeight: 700 }}>Justificatifs (vérification Uzima)</div>
              <div className="aide">Autorisation d&apos;ouverture, carte de l&apos;Ordre, pièce d&apos;identité, photo de la façade.</div></div>
            {donnees.dossier_incomplet
              ? <span className="pastille p-attente">À compléter</span>
              : <span className="pastille p-ok">Envoyés</span>}
          </Link>

          <FormulaireFiche fiche={donnees.fiche}
            onEnregistree={(f, m) => { setDonnees({ ...donnees, fiche: f }); setMessage({ type: "success", texte: m }); }} />

          <Link className="carte" href="/pharmacie/abonnement"
            style={{ display: "flex", alignItems: "center", gap: 12, color: "inherit", marginTop: 14 }}>
            <span className="icone-carre" style={{ background: "var(--ambre-clair)", color: "var(--ambre-texte)" }}>★</span>
            <div className="grow"><div className="nom">Abonnement et mise en avant</div>
              <div className="sous">Apparaissez en tête des recherches de votre quartier.</div></div>
            <span aria-hidden="true">›</span>
          </Link>

          <div className="titre-section" id="livreurs"><div><h2>Livraison à moto</h2>
            <p>Avec au moins un livreur, vos clients peuvent choisir la livraison (frais calculés selon la distance).</p></div></div>
          <Livreurs livreurs={donnees.livreurs} nomPharmacie={resume?.pharmacie.nom ?? donnees.fiche.nom}
            onChange={(m) => { setMessage(m); recharger(); }} />

          <div className="titre-section"><div><h2>Mise à jour par SMS / WhatsApp</h2>
            <p>Sans smartphone ? Envoyez vos mises à jour depuis le numéro {donnees.fiche.telephone}.</p></div></div>
          <div className="carte">
            <ul className="liste">
              {COMMANDES_SMS.map(([commande, sens]) => (
                <li key={commande}><div className="grow"><div className="nom">{commande}</div><div className="sous">{sens}</div></div></li>
              ))}
            </ul>
            <p className="aide">Une commande par ligne, 10 lignes maximum par message.</p>
            <form onSubmit={essayerSms} style={{ marginTop: 12 }}>
              <label htmlFor="texte-sms">Essayer ici (les changements sont appliqués à votre stock)</label>
              <textarea id="texte-sms" rows={2} placeholder="DISPO doliprane 4500" value={sms} onChange={(e) => setSms(e.target.value)} />
              <button className="btn bloc" type="submit" style={{ marginTop: 8 }}>Envoyer</button>
            </form>
          </div>

          <div className="titre-section"><h2>Mes prochaines gardes</h2></div>
          <div className="carte">
            {donnees.gardes.length ? (
              <ul className="liste">
                {donnees.gardes.map((g) => (
                  <li key={g.debut}>
                    <span className="icone-carre" style={{ background: "var(--indigo-clair)", color: "var(--indigo)" }}><IconeLune /></span>
                    <div className="grow">
                      <div className="nom" style={{ textTransform: "capitalize" }}>{jourLong(g.debut)}</div>
                      <div className="sous">de {heure(g.debut)} au {jourLong(g.fin)} à {heure(g.fin)}</div>
                    </div>
                    {g.en_cours && <span className="pastille p-prete">En cours</span>}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="vide"><IconeLune /><p>Aucune garde planifiée.</p></div>
            )}
            <p className="aide" style={{ marginTop: 12 }}>
              Le planning des gardes est établi par l&apos;Ordre des pharmaciens et saisi par l&apos;équipe Uzima.
            </p>
          </div>
        </>
      )}
    </Cadre>
  );
}
