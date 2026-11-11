import type { VerminId } from "./targets";

type IconProps = { id: VerminId };

export function AnimalIcon({ id }: IconProps) {
  if (id === "mouse") return <MouseIcon />;
  if (id === "rat") return <RatIcon />;
  if (id === "cockroach") return <CockroachIcon />;
  if (id === "cricket") return <CricketIcon />;
  if (id === "mosquito") return <MosquitoIcon />;
  return <MothIcon />;
}

function MouseIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <mask id="vermin-mouse">
        <rect width="48" height="48" fill="white" />
        <circle cx="15" cy="14" r="3.2" />
        <circle cx="33" cy="14" r="3.2" />
        <circle cx="20" cy="29" r="1.5" />
        <circle cx="28" cy="29" r="1.5" />
      </mask>
      <g fill="currentColor" mask="url(#vermin-mouse)">
        <circle cx="15" cy="14" r="7" />
        <circle cx="33" cy="14" r="7" />
        <ellipse cx="24" cy="30" rx="12" ry="10" />
      </g>
      <path d="M14 38c-5 3-7 7-4 9" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function RatIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <mask id="vermin-rat">
        <rect width="48" height="48" fill="white" />
        <circle cx="16" cy="16" r="2.2" />
        <circle cx="18" cy="28" r="1.4" />
      </mask>
      <g fill="currentColor" mask="url(#vermin-rat)">
        <circle cx="16" cy="16" r="5" />
        <ellipse cx="22" cy="28" rx="14" ry="8" />
        <polygon points="30,22 44,28 30,34" />
      </g>
      <path d="M8 30c-5 3-6 8-2 11" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function CockroachIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M20 16 8 6M28 16l12-10" />
      <ellipse cx="24" cy="28" rx="8" ry="13" fill="currentColor" stroke="none" />
      <path d="M16 22 6 18M16 28H5M16 34 8 41M32 22l10-4M32 28h11M32 34l8 7" />
    </svg>
  );
}

function CricketIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M18 16c1-7 8-8 9 0" />
      <ellipse cx="20" cy="28" rx="6" ry="11" fill="currentColor" stroke="none" />
      <path d="M25 30h8l-2 10h8" strokeWidth="2.5" />
    </svg>
  );
}

function MosquitoIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M24 2v9M24 34v12" />
      <ellipse cx="24" cy="23" rx="2.4" ry="9" fill="currentColor" stroke="none" />
      <path d="M24 16c-10 2-14 9-7 13M24 16c10 2 14 9 7 13" />
    </svg>
  );
}

function MothIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 18c-9-8-18 0-13 12 4 8 10 6 13 1M26 18c9-8 18 0 13 12-4 8-10 6-13 1" />
      <ellipse cx="24" cy="28" rx="2.3" ry="10" fill="currentColor" stroke="none" />
      <path d="M21 14c0-5 2-7 3-4M27 14c0-5-2-7-3-4" />
    </svg>
  );
}
