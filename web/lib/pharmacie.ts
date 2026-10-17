// Types des réponses de l'API du portail pharmacie (/api/web/pharmacie/…).

export type Medicament = {
  id: number;
  nom_commercial: string;
  dosage: string;
  dci: string;
  forme: string;
  ordonnance_requise: boolean;
  image: string | null;
  photo_possible: boolean;
};

export type Livreur = { id: number; nom: string; telephone: string; lien: string };

export type StatutReservation =
  | "en_attente" | "acceptee" | "prete" | "en_livraison" | "livree" | "retiree" | "refusee" | "annulee" | "expiree";

export type Reservation = {
  id: number;
  statut: StatutReservation;
  statut_libelle: string;
  expiree: boolean;
  est_active: boolean;
  transitions: StatutReservation[];
  cree_le: string;
  expire_le: string;
  nom: string;
  telephone: string;
  quantite: number;
  message_pharmacie: string;
  medicament: Medicament;
  est_livraison: boolean;
  adresse_livraison: string;
  position_livraison: { lat: number; lng: number } | null;
  frais_livraison: number | null;
  livreur: Livreur | null;
};

export type Resume = {
  pharmacie: { id: number; nom: string };
  nb_a_traiter: number;
  nb_questions: number;
  dossier_incomplet: boolean;
};

export type Tableau = {
  nb_en_attente: number;
  nb_en_cours: number;
  nb_disponibles: number;
  nb_ruptures: number;
  nb_a_confirmer: number;
  demande: { medicament_id: number; nom: string; dosage: string; image: string | null; nb: number }[];
  rayon_km: number;
  jours: number;
  dernieres: Reservation[];
  livreurs: Livreur[];
};

export type ListeReservations = {
  onglet: "a_traiter" | "en_cours" | "historique";
  nb_a_traiter: number;
  reservations: Reservation[];
  livreurs: Livreur[];
};

export type Stock = { disponible: boolean; prix: number | null; mis_a_jour_le: string };

export type ListeStock = {
  filtre: string;
  q: string;
  page: number;
  pages: number;
  nb_a_confirmer: number;
  lignes: { medicament: Medicament; stock: Stock | null; a_confirmer: boolean }[];
};

export type Fiche = {
  nom: string;
  numero_agrement: string;
  telephone: string;
  whatsapp: string;
  horaires: string;
  adresse: string;
  quartier: string;
};

export type Profil = {
  fiche: Fiche;
  gardes: { debut: string; fin: string; en_cours: boolean }[];
  livreurs: Livreur[];
  dossier_incomplet: boolean;
};

export type Question = {
  id: number;
  texte: string;
  cree_le: string;
  statut: "en_attente" | "repondue" | "orientee";
  statut_libelle: string;
  reponse: string;
  medicament: Medicament | null;
};

export type Abonnement = {
  id: number;
  formule: string;
  formule_libelle: string;
  mois: number;
  montant: number;
  reference: string;
  statut: string;
  statut_libelle: string;
  debut: string | null;
  fin: string | null;
};

export type PageAbonnement = {
  actif: Abonnement | null;
  en_attente: Abonnement | null;
  historique: Abonnement[];
  formules: { code: string; libelle: string; detail: string; prix: number }[];
  durees: number[];
  numero_paiement: string;
};

export type Grossiste = { id: number; nom: string; delai_livraison: string; minimum_commande: number };

export type Commande = {
  id: number;
  grossiste: { id: number; nom: string };
  cree_le: string;
  statut: "envoyee" | "confirmee" | "livree" | "annulee";
  statut_libelle: string;
  note: string;
  nb_produits: number;
  total: number;
  lignes?: { quantite: number; medicament: Medicament; conditionnement: string; prix_unitaire: number; sous_total: number }[];
  whatsapp?: string | null;
  actions?: ("recue" | "annuler")[];
};

export type PieceKyc = {
  id: number;
  statut: "en_attente" | "acceptee" | "rejetee";
  statut_libelle: string;
  envoyee_le: string;
  nom_original: string;
  motif: string;
};

export type DossierKyc = {
  lignes: { type: string; libelle: string; aide: string; obligatoire: boolean; piece: PieceKyc | null }[];
  manquantes: string[];
  verifie: boolean;
  a_verifier: number;
};

/** Libellé du bouton pour chaque étape d'une réservation. */
export const ACTIONS_RESERVATION: Partial<Record<StatutReservation, string>> = {
  acceptee: "Accepter",
  prete: "Marquer prête",
  retiree: "Client passé : retirée",
  livree: "Livrée au client",
};

/** Couleur de la pastille de statut. */
export function classeStatut(statut: StatutReservation): string {
  switch (statut) {
    case "en_attente": return "p-attente";
    case "acceptee": return "p-ok";
    case "prete": return "p-prete";
    case "refusee": return "p-refus";
    default: return "p-neutre";
  }
}
