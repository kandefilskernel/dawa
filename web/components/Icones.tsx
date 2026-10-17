// Icônes du portail (reprises de backend/portail/templates/portail/icones/).
import type { ReactNode } from "react";

function Trait({ children }: { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      {children}
    </svg>
  );
}

/** Logo Uzima (communication/icone/) : goutte verte et croix blanche sur fond clair, ou l'inverse sur le dégradé. */
export function Logo({ inverse = false }: { inverse?: boolean }) {
  return inverse ? (
    <svg viewBox="0 0 120 120" aria-hidden="true">
      <path d="M60 24c20 8 30 24 30 40 0 18-13 31-30 31S30 82 30 64c0-16 10-32 30-40z" fill="#FFFFFF" />
      <path d="M54 44h12v12h12v12H66v12H54V68H42V56h12z" fill="#10B981" />
      <circle cx="86" cy="30" r="9" fill="#FCD34D" />
    </svg>
  ) : (
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <path d="M32 11c11.5 4.6 17 13.8 17 23 0 10.3-7.4 17.8-17 17.8S15 44.3 15 34c0-9.2 5.6-18.4 17-23z" fill="#10B981" />
      <path d="M28.6 25h6.8v6.8h6.8v6.8h-6.8v6.8h-6.8v-6.8h-6.8v-6.8h6.8z" fill="#FFFFFF" />
      <circle cx="47" cy="15" r="5" fill="#F59E0B" />
    </svg>
  );
}

export const IconeTableau = () => (
  <Trait><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></Trait>
);
export const IconeReservations = () => (
  <Trait><path d="M6 7h12l-1 13H7z" /><path d="M9 7V5a3 3 0 0 1 6 0v2" /></Trait>
);
export const IconeStock = () => (
  <Trait><path d="M10.5 20.5 3.5 13.5a5 5 0 0 1 7-7l7 7a5 5 0 0 1-7 7z" /><path d="m8.5 8.5 7 7" /></Trait>
);
export const IconeQuestion = () => (
  <Trait><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5" /><path d="M12 15h.01" /></Trait>
);
export const IconeProfil = () => (
  <Trait><path d="M3 21V8l9-5 9 5v13" /><path d="M10 21v-6h4v6" /><path d="M12 8v4M10 10h4" /></Trait>
);
export const IconeCheck = () => <Trait><path d="M20 6 9 17l-5-5" /></Trait>;
export const IconeHorloge = () => <Trait><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Trait>;
export const IconeLune = () => <Trait><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></Trait>;
export const IconeTelephone = () => (
  <Trait><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z" /></Trait>
);
export const IconeSortie = () => (
  <Trait><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" /><path d="M10 17l-5-5 5-5" /><path d="M5 12h11" /></Trait>
);
export const IconeTendance = () => <Trait><path d="M3 3v18h18" /><path d="m7 14 4-4 3 3 5-6" /></Trait>;
