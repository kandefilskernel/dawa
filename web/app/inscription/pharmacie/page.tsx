"use client";
import { CHAMPS_COMPTE, FormulaireInscription, type ChampInscription } from "@/components/FormulaireInscription";

const CHAMPS: ChampInscription[] = [
  { nom: "nom", libelle: "Nom de la pharmacie", requis: true, section: "La pharmacie" },
  { nom: "numero_agrement", libelle: "Numéro d'autorisation d'ouverture", requis: true,
    aide: "Délivré par l'Inspection provinciale de la santé. Uzima le vérifie." },
  { nom: "telephone", libelle: "Téléphone", type: "tel", requis: true, autocomplete: "tel" },
  { nom: "whatsapp", libelle: "WhatsApp", type: "tel" },
  { nom: "adresse", libelle: "Adresse", requis: true, autocomplete: "street-address" },
  { nom: "quartier", libelle: "Quartier" },
  { nom: "commune", libelle: "Commune" },
  { nom: "horaires", libelle: "Horaires d'ouverture", aide: "Ex. Lun–Sam 8h–20h", position: true },
  ...CHAMPS_COMPTE,
];

export default function InscriptionPharmacie() {
  return (
    <FormulaireInscription titre="Inscrire ma pharmacie" chemin="compte/inscription/pharmacie/" champs={CHAMPS}
      intro="Votre pharmacie apparaîtra dans l'app Uzima après vérification par notre équipe."
      ici="à la pharmacie" ou="la pharmacie" />
  );
}
