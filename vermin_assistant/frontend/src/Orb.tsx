type OrbProps = {
  active: boolean;
  intensity: number;
  label: string;
  peak: string;
};

export function Orb({ active, intensity, label, peak }: OrbProps) {
  const boost = 0.55 + intensity / 200;
  return (
    <div className="orb-stage" data-on={active} style={{ ["--orb-boost" as string]: String(boost) }}>
      <div className="orb-aura" />
      <div className="orb-ring orb-ring-a" />
      <div className="orb-ring orb-ring-b" />
      <div className="orb-ring orb-ring-c" />
      <div className="orb-core">
        <strong>{peak}</strong>
        <span>{label}</span>
      </div>
      <div className="orb-scan" />
    </div>
  );
}
