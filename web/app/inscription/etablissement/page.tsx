"use client";
import { CHAMPS_COMPTE, FormulaireInscription, type ChampInscription } from "@/components/FormulaireInscription";

const CHAMPS: ChampInscription[] = [
  { nom: "nom", libelle: "Nom de l'établissement", requis: true, section: "L'établissement" },
  { nom: "type", libelle: "Type", type: "select", requis: true, choix: [
    ["hopital", "Hôpital"], ["clinique", "Clinique"], ["centre_sante", "Centre de santé"],
    ["laboratoire", "Laboratoire"], ["maternite", "Maternité"],
  ] },
  { nom: "numero_agrement", libelle: "Numéro d'autorisation de fonctionnement", requis: true,
    aide: "Délivré par la Division provinciale de la santé. Uzima le vérifie." },
  { nom: "telephone", libelle: "Téléphone", type: "tel", requis: true, autocomplete: "tel" },
  { nom: "adresse", libelle: "Adresse", requis: true, autocomplete: "street-address" },
  { nom: "quartier", libelle: "Quartier" },
  { nom: "services", libelle: "Services", aide: "Ex. pédiatrie, maternité, radiologie, analyses" },
  { nom: "urgences_24h", libelle: "Urgences ouvertes 24h/24", type: "checkbox", position: true },
  { nom: "fonction", libelle: "Votre fonction", requis: true, aide: "Ex. médecin directeur, administrateur" },
  ...CHAMPS_COMPTE,
];

export default function InscriptionEtablissement() {
  return (
    <FormulaireInscription titre="Inscrire un établissement de santé" chemin="compte/inscription/etablissement/"
      champs={CHAMPS} ici="à l'établissement" ou="l'établissement"
      intro="Hôpitaux, cliniques, centres de santé, laboratoires, maternités : votre établissement apparaîtra dans l'annuaire santé de l'app après vérification de vos justificatifs." />
  );
}
