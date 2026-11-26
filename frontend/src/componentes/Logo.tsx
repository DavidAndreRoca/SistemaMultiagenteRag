// Ícono del sistema: un documento con una marca de verificación. Es decorativo: el nombre del
// sistema siempre va al lado como texto.
export function Logo({ tamano = 32 }: { tamano?: number }) {
  return (
    <svg
      className="logo"
      width={tamano}
      height={tamano}
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
    >
      <rect width="32" height="32" rx="8" fill="#0f766e" />
      <path d="M10 7h9l5 5v13a1 1 0 0 1-1 1H10a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z" fill="#ffffff" />
      <path d="M19 7v5h5" fill="none" stroke="#0f766e" strokeWidth="1.5" />
      <path
        d="M12.5 19l2.6 2.6 5-5.2"
        fill="none"
        stroke="#0f766e"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
