"use client";
import { Chargement } from "@/components/CarteConnexion";
import { DossierKyc } from "@/components/DossierKyc";
import { Flash, useFlash } from "@/components/Flash";
import { Cadre, useResume } from "@/components/pharmacie/Cadre";
import type { DossierKyc as Dossier } from "@/lib/pharmacie";
import { useDonnees } from "@/lib/useDonnees";

export default function PageDossier() {
  const { donnees, erreur, setDonnees } = useDonnees<{ dossier: Dossier }>("pharmacie/dossier/");
  const { message, setMessage } = useFlash();
  const { rafraichir } = useResume();
  return (
    <Cadre titre="Justificatifs de la pharmacie" intro="Preuves que la pharmacie est enregistrée, vérifiées par l'équipe Uzima."
      avecBandeau={false}>
      <Flash message={message ?? (erreur ? { type: "error", texte: erreur } : null)} />
      <div className="carte">
        {!donnees ? <Chargement /> : (
          <DossierKyc dossier={donnees.dossier} chemin="pharmacie/dossier/"
            onChange={(d, m) => { setDonnees({ ...donnees, dossier: d }); setMessage({ type: "success", texte: m }); rafraichir(); }} />
        )}
      </div>
    </Cadre>
  );
}
