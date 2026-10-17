// Champ de formulaire avec libellé, aide et erreurs renvoyées par l'API.
import type { InputHTMLAttributes } from "react";

export function Champ({ nom, libelle, aide, erreurs, valeur, onChange, ...attributs }: {
  nom: string;
  libelle: string;
  aide?: string;
  erreurs?: Record<string, string[]>;
  valeur: string;
  onChange: (v: string) => void;
} & Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "name">) {
  return (
    <div className="champ">
      <label htmlFor={`id_${nom}`}>{libelle}</label>
      <input id={`id_${nom}`} name={nom} value={valeur} onChange={(e) => onChange(e.target.value)} {...attributs}
        type={attributs.type ?? "text"} />
      {aide && <div className="aide">{aide}</div>}
      {erreurs?.[nom]?.map((e) => <div className="erreur" key={e}>{e}</div>)}
    </div>
  );
}
