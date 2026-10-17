// Mise en forme des montants, dates et pluriels, à la française (heure de Lubumbashi).

const FUSEAU = "Africa/Lubumbashi";

/** 12000 → « 12 000 FC » */
export function fc(montant: number | null | undefined): string {
  if (montant === null || montant === undefined) return "—";
  return `${new Intl.NumberFormat("fr-FR").format(montant).replace(/ | /g, " ")} FC`;
}

function date(valeur: string | Date): Date {
  return typeof valeur === "string" ? new Date(valeur) : valeur;
}

/** « 14:05 » */
export function heure(valeur: string | Date): string {
  return new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: FUSEAU }).format(date(valeur));
}

/** « 17/10/2026 » */
export function jour(valeur: string | Date): string {
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: FUSEAU })
    .format(date(valeur));
}

/** « 17/10 14:05 » */
export function jourHeure(valeur: string | Date): string {
  const d = date(valeur);
  const jm = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit", timeZone: FUSEAU }).format(d);
  return `${jm} ${heure(d)}`;
}

/** « samedi 17 octobre » */
export function jourLong(valeur: string | Date): string {
  return new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long", timeZone: FUSEAU })
    .format(date(valeur));
}

/** « il y a 5 min », « il y a 2 h », « il y a 3 j » */
export function depuis(valeur: string | Date, maintenant: Date = new Date()): string {
  const minutes = Math.max(0, Math.round((maintenant.getTime() - date(valeur).getTime()) / 60000));
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const heures = Math.floor(minutes / 60);
  if (heures < 24) return `il y a ${heures} h`;
  return `il y a ${Math.floor(heures / 24)} j`;
}

/** pluriel(2, "réservation") → « réservations » */
export function pluriel(nombre: number, mot: string, motPluriel = `${mot}s`): string {
  return nombre > 1 ? motPluriel : mot;
}

/** Garde uniquement les chiffres d'un numéro (pour wa.me et tel:). */
export function chiffres(numero: string): string {
  return numero.replace(/\D/g, "");
}

/** Lien WhatsApp avec un texte prérempli (numéro facultatif). */
export function lienWhatsapp(texte: string, numero = ""): string {
  return `https://wa.me/${chiffres(numero)}?text=${encodeURIComponent(texte)}`;
}
