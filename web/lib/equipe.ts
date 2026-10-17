// Types des réponses de l'API de l'espace équipe (/api/web/equipe/…).
import type { DossierKyc, PieceKyc } from "./pharmacie";

export type TableauEquipe = {
  identifiant: string;
  nb_demandes: number;
  pharmacies_visibles: number;
  abonnements_a_activer: number;
  abonnements_actifs: number;
  signalements_a_traiter: number;
};

export type Structure = {
  id: number;
  nom: string;
  numero_agrement: string;
  adresse: string;
  quartier: string;
  telephone: string;
  type: string;
  position: { lat: number; lng: number };
  position_a_verifier: boolean;
  admin: string;
};

export type CompteStructure = {
  id: number;
  utilisateur_id: number;
  identifiant: string;
  statut: "actif" | "en_attente" | "refuse" | "suspendu";
  statut_libelle: string;
  motif: string;
  fonction: string;
};

export type DossierEquipe = Omit<DossierKyc, "lignes"> & {
  lignes: (Omit<DossierKyc["lignes"][number], "piece"> & { piece: (PieceKyc & { document: string }) | null })[];
};

export type Demande = {
  genre: "pharmacie" | "etablissement";
  cree_le: string;
  compte: CompteStructure;
  structure: Structure;
  dossier: DossierEquipe;
};

export type StructureListe = Structure & {
  visible: boolean;
  kyc_verifie: boolean;
  sponsorisee?: boolean;
  comptes: CompteStructure[];
};

export type LienMotDePasse = {
  identifiant: string;
  structure: { nom: string; telephone: string };
  lien: string;
  texte: string;
  whatsapp: string;
};

export type AbonnementEquipe = {
  id: number;
  pharmacie: { id: number; nom: string };
  formule: string;
  mois: number;
  montant: number;
  reference: string;
  fin: string | null;
};

export type Signalement = {
  id: number;
  medicament: string | null;
  numero_lot: string;
  description: string;
  lieu: string;
  telephone: string;
  photo: string | null;
  cree_le: string;
  suite_donnee: string;
};
