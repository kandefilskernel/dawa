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

export function Logo() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
      <path d="M12 3.6c4.4 1.8 6.6 5.3 6.6 8.8 0 4-2.9 6.8-6.6 6.8s-6.6-2.8-6.6-6.8c0-3.5 2.2-7 6.6-8.8z" fill="#10B981" />
      <path d="M10.8 8.6h2.4V11h2.4v2.4h-2.4v2.4h-2.4v-2.4H8.4V11h2.4z" fill="#FFFFFF" />
      <circle cx="18.4" cy="5" r="2" fill="#F59E0B" />
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
export const IconeTendance = () => <Trait><path d="M3 3v18h18" /><path d="m7 14 4-4 3 3 5-6" /></Trait>;
